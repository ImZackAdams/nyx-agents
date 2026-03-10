from __future__ import annotations

from dataclasses import dataclass
import os
import queue
from threading import Thread
import warnings
from typing import Callable, Protocol


os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

VALID_BACKENDS = {"auto", "hf", "echo"}
TokenCallback = Callable[[str], None]


@dataclass(frozen=True)
class ProviderConfig:
    backend: str = "auto"
    model_path: str | None = None
    max_new_tokens: int = 48
    device: str = "auto"
    quantize_4bit: bool = True
    do_sample: bool = False


class LLMProvider(Protocol):
    runtime_summary: str
    load_warnings: list[str]

    def generate(self, prompt: str, *, on_token: TokenCallback | None = None) -> str:
        ...


class EchoProvider:
    """Placeholder provider for local testing."""

    def __init__(self) -> None:
        self.runtime_summary = "Using echo backend"
        self.load_warnings: list[str] = []

    def generate(self, prompt: str, *, on_token: TokenCallback | None = None) -> str:
        del prompt
        response = "FINAL: (echo provider) No model configured."
        if on_token is not None:
            on_token(response)
        return response


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

        # Lazy import keeps base CLI usage light unless the model is actually needed.
        try:
            import torch
            import transformers
            from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
        except ImportError as exc:
            raise RuntimeError(
                "Missing model dependencies. Install torch, transformers, and accelerate."
            ) from exc

        self.torch = torch
        self.TextIteratorStreamer = TextIteratorStreamer
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

        model_kwargs: dict[str, object] = {
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

    def generate(self, prompt: str, *, on_token: TokenCallback | None = None) -> str:
        inputs = self._tokenize_prompt(prompt)
        generate_kwargs = self._generate_kwargs()

        if on_token is None:
            outputs = self._run_generation(inputs, generate_kwargs)
            generated = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            ).strip()
            return _normalize_generated_text(generated)

        streamer = self.TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
            timeout=0.1,
        )
        stream_kwargs = dict(generate_kwargs)
        stream_kwargs["streamer"] = streamer

        error_holder: dict[str, Exception] = {}
        worker = Thread(
            target=self._run_generation_thread,
            args=(inputs, stream_kwargs, error_holder),
            daemon=True,
        )
        worker.start()

        chunks: list[str] = []
        iterator = iter(streamer)
        while True:
            try:
                chunk = next(iterator)
            except queue.Empty:
                if worker.is_alive():
                    continue
                break
            except StopIteration:
                break

            if chunk:
                chunks.append(chunk)
                on_token(chunk)

        worker.join()
        if "exception" in error_holder:
            exc = error_holder["exception"]
            self._handle_generation_error(exc)
            raise exc

        return _normalize_generated_text("".join(chunks))

    def _tokenize_prompt(self, prompt: str) -> object:
        return self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        ).to(self.device)

    def _generate_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.do_sample,
            "repetition_penalty": 1.05,
            "use_cache": True,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if self.do_sample:
            kwargs["temperature"] = 0.7
            kwargs["top_p"] = 0.9
        return kwargs

    def _run_generation(self, inputs: object, generate_kwargs: dict[str, object]) -> object:
        try:
            with self.torch.inference_mode():
                return self.model.generate(
                    **inputs,
                    **generate_kwargs,
                )
        except Exception as exc:
            self._handle_generation_error(exc)
            raise

    def _run_generation_thread(
        self,
        inputs: object,
        generate_kwargs: dict[str, object],
        error_holder: dict[str, Exception],
    ) -> None:
        try:
            self._run_generation(inputs, generate_kwargs)
        except Exception as exc:  # pragma: no cover - exercised through generate()
            error_holder["exception"] = exc

    def _handle_generation_error(self, exc: Exception) -> None:
        if not isinstance(exc, RuntimeError):
            return
        message = str(exc).lower()
        if "out of memory" in message and self.device.type == "cuda":
            self.torch.cuda.empty_cache()
            raise RuntimeError(
                "Model ran out of GPU memory during generation. Retry with "
                "`--device cpu`, disable `--quantize-4bit`, or lower `--max-new-tokens`."
            ) from exc


def build_provider(config: ProviderConfig) -> LLMProvider:
    backend = (config.backend or "auto").strip().lower()
    if backend not in VALID_BACKENDS:
        allowed = ", ".join(sorted(VALID_BACKENDS))
        raise ValueError(f"backend must be one of: {allowed}")

    if backend == "echo":
        return EchoProvider()

    if backend == "hf":
        if not config.model_path:
            raise RuntimeError("The Hugging Face backend requires --model-path or LILBOT_MODEL_PATH.")
        return LocalHFProvider(
            config.model_path,
            device=config.device,
            max_new_tokens=config.max_new_tokens,
            quantize_4bit=config.quantize_4bit,
            do_sample=config.do_sample,
        )

    if config.model_path:
        return LocalHFProvider(
            config.model_path,
            device=config.device,
            max_new_tokens=config.max_new_tokens,
            quantize_4bit=config.quantize_4bit,
            do_sample=config.do_sample,
        )
    return EchoProvider()


def _normalize_generated_text(generated: str) -> str:
    text = generated.strip()

    for marker in ("<|assistant|>", "<|user|>", "<|system|>"):
        text = text.replace(marker, "").strip()

    if not text:
        text = "(empty response)"

    if not text.startswith(("FINAL:", "TOOL:")):
        text = f"FINAL: {text}"
    return text
