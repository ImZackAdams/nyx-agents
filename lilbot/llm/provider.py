from __future__ import annotations

import os
import warnings
from typing import Protocol


os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class EchoProvider:
    """Placeholder provider for local testing."""

    def generate(self, prompt: str) -> str:
        return "FINAL: (echo provider) No model configured."


class LocalHFProvider:
    """
    Local HuggingFace model provider.
    Expects a local model path containing tokenizer + model files.
    """

    DEFAULT_MAX_INPUT_TOKENS = 2048

    def __init__(
        self,
        model_path: str,
        max_new_tokens: int = 200,
        device: str = "auto",
        quantize_4bit: bool = False,
        do_sample: bool = False,
    ):
        self.model_path = os.path.abspath(model_path)
        self.max_new_tokens = max(1, int(max_new_tokens))
        self.device_pref = (device or "auto").strip().lower()
        if self.device_pref not in {"auto", "cpu", "cuda"}:
            raise ValueError("device must be one of: auto, cpu, cuda")
        self.quantize_4bit = quantize_4bit
        self.do_sample = do_sample
        self.load_warnings: list[str] = []
        self.runtime_summary = ""

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

        # Lazy import to keep base deps minimal unless used.
        try:
            import torch
            import transformers
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Missing model dependencies. Install torch, transformers, and accelerate."
            ) from exc

        self.torch = torch
        self.transformers_version = getattr(transformers, "__version__", "unknown")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                use_fast=True,
            )
        except KeyError as exc:
            raise RuntimeError(self._unsupported_model_message(exc)) from exc
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        use_cuda = self._should_use_cuda()
        self.device = torch.device("cuda" if use_cuda else "cpu")
        if use_cuda and hasattr(torch.backends, "cuda") and hasattr(torch.backends.cuda, "matmul"):
            torch.backends.cuda.matmul.allow_tf32 = True

        model_kwargs = {
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        if use_cuda:
            model_kwargs["torch_dtype"] = torch.float16
            model_kwargs["device_map"] = "auto"

        quant_config = self._build_quantization_config(torch)
        if quant_config is not None:
            model_kwargs["quantization_config"] = quant_config

        self.model = self._load_model(AutoModelForCausalLM, dict(model_kwargs))

        # If accelerate offloads parts to CPU, .to() is not allowed.
        if not hasattr(self.model, "hf_device_map"):
            self.model.to(self.device)
        self.model.eval()

        if (
            getattr(self.model.generation_config, "pad_token_id", None) is None
            and self.tokenizer.pad_token_id is not None
        ):
            self.model.generation_config.pad_token_id = self.tokenizer.pad_token_id

        self.max_input_tokens = self._resolve_max_input_tokens()
        self.runtime_summary = self._build_runtime_summary()

    def _should_use_cuda(self) -> bool:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="CUDA initialization: .*")
            warnings.filterwarnings("ignore", message="Can't initialize NVML")
            cuda_available = bool(self.torch.cuda.is_available())
        if self.device_pref == "cpu":
            return False
        if self.device_pref == "cuda" and not cuda_available:
            raise RuntimeError("CUDA was requested but is not available.")
        return cuda_available

    def _build_quantization_config(self, torch: object) -> object | None:
        if not self.quantize_4bit:
            return None
        if self.device.type != "cuda":
            self.load_warnings.append(
                "4-bit quantization requires CUDA; continuing without quantization."
            )
            return None
        try:
            import bitsandbytes  # noqa: F401
            from transformers import BitsAndBytesConfig
        except ImportError:
            self.load_warnings.append(
                "bitsandbytes is not installed; continuing without 4-bit quantization."
            )
            return None

        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

    def _load_model(self, auto_model: object, model_kwargs: dict[str, object]) -> object:
        quantization_config = model_kwargs.get("quantization_config")
        try:
            return auto_model.from_pretrained(self.model_path, **model_kwargs)
        except KeyError as exc:
            raise RuntimeError(self._unsupported_model_message(exc)) from exc
        except Exception as exc:
            if quantization_config is None:
                raise

            self.load_warnings.append(
                f"4-bit quantization failed ({exc}); retrying with full precision."
            )
            retry_kwargs = dict(model_kwargs)
            retry_kwargs.pop("quantization_config", None)
            return auto_model.from_pretrained(self.model_path, **retry_kwargs)

    def _resolve_max_input_tokens(self) -> int:
        limits = [self.DEFAULT_MAX_INPUT_TOKENS]
        for value in (
            getattr(self.model.config, "max_position_embeddings", None),
            getattr(self.tokenizer, "model_max_length", None),
        ):
            if isinstance(value, int) and 0 < value < 100_000:
                limits.append(value)
        return min(limits)

    def _unsupported_model_message(self, exc: Exception) -> str:
        return (
            f"Installed transformers {self.transformers_version} is too old for this model "
            f"({exc}). Upgrade dependencies from requirements.txt and retry."
        )

    def _build_runtime_summary(self) -> str:
        model_name = os.path.basename(self.model_path.rstrip(os.sep))
        summary = [
            f"Loaded {model_name} on {self.device.type}",
            "sample" if self.do_sample else "greedy",
            f"max_new_tokens={self.max_new_tokens}",
        ]
        if self.quantize_4bit and self.device.type == "cuda":
            summary.append("4-bit")

        device_map = getattr(self.model, "hf_device_map", None)
        if self.device.type == "cpu":
            self.load_warnings.append(
                "Model is running on CPU; expect high latency. A working CUDA setup or a smaller model "
                "will improve response time significantly."
            )
        elif isinstance(device_map, dict):
            offloaded = {
                str(target)
                for target in device_map.values()
                if not isinstance(target, int) and not str(target).startswith("cuda")
            }
            if offloaded:
                self.load_warnings.append(
                    "Model is partially offloaded to CPU/disk; latency will be high. "
                    "Enable 4-bit quantization or use a smaller model for faster replies."
                )

        return " | ".join(summary)

    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        ).to(self.device)

        generate_kwargs = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.do_sample,
            "repetition_penalty": 1.05,
            "use_cache": True,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if self.do_sample:
            generate_kwargs["temperature"] = 0.7
            generate_kwargs["top_p"] = 0.9

        try:
            with self.torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    **generate_kwargs,
                )
        except RuntimeError as exc:
            message = str(exc).lower()
            if "out of memory" in message and self.device.type == "cuda":
                self.torch.cuda.empty_cache()
                raise RuntimeError(
                    "Model ran out of GPU memory during generation. Retry with "
                    "`--device cpu`, disable `--quantize-4bit`, or lower `--max-new-tokens`."
                ) from exc
            raise

        generated = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()

        # Remove common chat markers if they slip through.
        for marker in ("<|assistant|>", "<|user|>", "<|system|>"):
            generated = generated.replace(marker, "").strip()

        if not generated:
            generated = "(empty response)"

        # Ensure required format if model doesn't follow instructions
        if not generated.startswith(("FINAL:", "TOOL:")):
            generated = f"FINAL: {generated}"
        return generated
