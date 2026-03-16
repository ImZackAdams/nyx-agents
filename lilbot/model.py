"""Local model loading for Lilbot."""

from __future__ import annotations

import os
import warnings

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

from lilbot.utils.config import LilbotConfig


DISABLED_TRANSFORMERS_OPTIONAL_PACKAGES = frozenset({"pandas", "pyarrow", "sklearn"})


class LocalModel:
    """Thin wrapper around a local Hugging Face causal language model."""

    DEFAULT_MAX_INPUT_TOKENS = 4096

    def __init__(
        self,
        model_path: str,
        *,
        device: str = "auto",
        max_new_tokens: int = 192,
        quantize_4bit: bool = False,
    ) -> None:
        self.model_path = os.path.abspath(model_path)
        self.device_pref = (device or "auto").strip().lower()
        self.max_new_tokens = max(1, int(max_new_tokens))
        self.quantize_4bit = bool(quantize_4bit)
        self.quantization_active = False
        self.runtime_summary = ""
        self.load_warnings: list[str] = []

        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

        try:
            import torch
            import transformers

            _disable_optional_transformers_packages(transformers)
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Local model dependencies are missing. Install them with `pip install -e \".[hf]\"`."
            ) from exc

        self.torch = torch
        self.transformers_version = getattr(transformers, "__version__", "unknown")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                use_fast=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load the tokenizer from {self.model_path}: {exc}"
            ) from exc

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.uses_chat_template = bool(getattr(self.tokenizer, "chat_template", None))

        use_cuda = self._should_use_cuda()
        self.device = torch.device("cuda" if use_cuda else "cpu")

        model_kwargs: dict[str, object] = {
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
        if use_cuda:
            model_kwargs["torch_dtype"] = torch.float16
            model_kwargs["device_map"] = "auto"

        quantization_config = self._build_quantization_config()
        if quantization_config is not None:
            model_kwargs["quantization_config"] = quantization_config

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
        self.runtime_summary = self._runtime_summary()

    def generate(self, prompt: str) -> str:
        rendered_prompt = _render_prompt_with_chat_template(self.tokenizer, prompt)
        inputs = self.tokenizer(
            rendered_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_input_tokens,
        ).to(self.device)

        try:
            with self.torch.inference_mode():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,
                    repetition_penalty=1.05,
                    use_cache=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                )
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() and self.device.type == "cuda":
                self.torch.cuda.empty_cache()
                raise RuntimeError(
                    "The model ran out of GPU memory. Retry with `--device cpu`, use a smaller model, "
                    "or disable `--quantize-4bit`."
                ) from exc
            raise

        generated = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()
        return generated or "FINAL: (empty response)"

    def _should_use_cuda(self) -> bool:
        if self.device_pref not in {"auto", "cpu", "cuda"}:
            raise ValueError("device must be one of: auto, cpu, cuda")

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="CUDA initialization: .*")
            warnings.filterwarnings("ignore", message="Can't initialize NVML")
            cuda_available = bool(self.torch.cuda.is_available())

        if self.device_pref == "cpu":
            return False
        if self.device_pref == "cuda" and not cuda_available:
            raise RuntimeError("CUDA was requested but is not available.")
        return cuda_available

    def _build_quantization_config(self) -> object | None:
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
                "bitsandbytes is not installed; continuing without 4-bit quantization. "
                "Install it with `pip install -e \".[hf,quantization]\"`."
            )
            return None

        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=self.torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

    def _load_model(self, auto_model: object, model_kwargs: dict[str, object]) -> object:
        quantization_config = model_kwargs.get("quantization_config")
        try:
            model = auto_model.from_pretrained(self.model_path, **model_kwargs)
        except Exception as exc:
            if quantization_config is None:
                raise RuntimeError(
                    f"Unable to load the model from {self.model_path}: {exc}"
                ) from exc

            self.load_warnings.append(
                f"4-bit quantization failed ({exc}); retrying without quantization."
            )
            retry_kwargs = dict(model_kwargs)
            retry_kwargs.pop("quantization_config", None)
            try:
                model = auto_model.from_pretrained(self.model_path, **retry_kwargs)
            except Exception as retry_exc:
                raise RuntimeError(
                    f"Unable to load the model from {self.model_path}: {retry_exc}"
                ) from retry_exc
            return model

        self.quantization_active = quantization_config is not None
        return model

    def _resolve_max_input_tokens(self) -> int:
        limits = [self.DEFAULT_MAX_INPUT_TOKENS]
        for value in (
            getattr(self.model.config, "max_position_embeddings", None),
            getattr(self.tokenizer, "model_max_length", None),
        ):
            if isinstance(value, int) and 0 < value < 100_000:
                limits.append(value)
        return min(limits)

    def _runtime_summary(self) -> str:
        model_name = os.path.basename(self.model_path.rstrip(os.sep))
        summary = [f"Loaded {model_name} on {self.device.type}", f"max_new_tokens={self.max_new_tokens}"]
        if self.quantization_active:
            summary.append("4-bit")
        if self.uses_chat_template:
            summary.append("chat-template")
        return " | ".join(summary)


def build_model(config: LilbotConfig) -> LocalModel:
    if not config.model_path:
        raise RuntimeError(
            "No local model path is configured. Set LILBOT_MODEL_PATH or pass --model-path."
        )
    model = LocalModel(
        config.model_path,
        device=config.device,
        max_new_tokens=config.max_new_tokens,
        quantize_4bit=config.quantize_4bit,
    )
    return model


def _disable_optional_transformers_packages(transformers_module: object) -> None:
    try:
        import_utils = transformers_module.utils.import_utils
        utils_module = transformers_module.utils
    except AttributeError:
        return

    original = getattr(import_utils, "_is_package_available", None)
    if not callable(original):
        return

    def _patched_is_package_available(
        package_name: str,
        return_version: bool = False,
    ) -> tuple[bool, str | None]:
        if package_name in DISABLED_TRANSFORMERS_OPTIONAL_PACKAGES:
            return (False, "N/A") if return_version else (False, None)
        return original(package_name, return_version=return_version)

    import_utils._is_package_available = _patched_is_package_available
    utils_module.is_pandas_available = lambda: False
    utils_module.is_sklearn_available = lambda: False


def _render_prompt_with_chat_template(tokenizer: object, prompt: str) -> str:
    """Render a prompt for chat-tuned local models when a tokenizer template exists."""

    text = str(prompt)
    if not text.strip():
        return text

    if any(marker in text for marker in ("<|system|>", "<|user|>", "<|assistant|>")):
        return text

    apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
    chat_template = getattr(tokenizer, "chat_template", None)
    if not callable(apply_chat_template) or not chat_template:
        return text

    try:
        rendered = apply_chat_template(
            [{"role": "user", "content": text}],
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        return text

    return str(rendered) if rendered else text
