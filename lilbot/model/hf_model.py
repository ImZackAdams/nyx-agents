"""Hugging Face local model backend."""

from __future__ import annotations

import os
import warnings

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from lilbot.model.base import BaseModel


DISABLED_TRANSFORMERS_OPTIONAL_PACKAGES = frozenset({"pandas", "pyarrow", "sklearn"})


class HuggingFaceLocalModel(BaseModel):
    """Load a local Hugging Face causal LM directly in Python."""

    DEFAULT_MAX_INPUT_TOKENS = 4096

    def __init__(
        self,
        model_name: str | None,
        *,
        device: str = "auto",
        max_new_tokens: int = 256,
        temperature: float = 0.0,
        quantize_4bit: bool = True,
    ) -> None:
        if not model_name:
            raise RuntimeError(
                "No local model is configured. Run `lilbot init` to save one, "
                "pass `--model /path/to/model`, or set `LILBOT_MODEL`. "
                "Deterministic commands like `lilbot doctor` still work without a model."
            )

        try:
            import torch
            import transformers

            _disable_optional_transformers_packages(transformers)
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Local model dependencies are missing. Install them with "
                "`python -m pip install torch transformers accelerate`."
            ) from exc

        self.torch = torch
        self.transformers_version = getattr(transformers, "__version__", "unknown")
        self.model_name = model_name
        self.max_new_tokens = max(1, int(max_new_tokens))
        self.temperature = max(0.0, float(temperature))
        self.quantize_4bit = bool(quantize_4bit)
        self.quantization_active = False
        self.device_pref = (device or "auto").strip().lower()
        self.device = self._resolve_device(device)
        self.load_warnings: list[str] = []

        tokenizer_kwargs = {
            "local_files_only": True,
            "trust_remote_code": True,
            "use_fast": True,
        }
        model_kwargs: dict[str, object] = {
            "local_files_only": True,
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }

        if self.device.type == "cuda":
            model_kwargs[_select_dtype_kwarg(self.transformers_version)] = torch.float16
            model_kwargs["device_map"] = "auto"
            max_memory = self._build_max_memory_map()
            if max_memory is not None:
                model_kwargs["max_memory"] = max_memory

        quantization_config = self._build_quantization_config()
        if quantization_config is not None:
            model_kwargs["quantization_config"] = quantization_config

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, **tokenizer_kwargs)
            self.model = self._load_model(AutoModelForCausalLM, dict(model_kwargs))
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load local model '{model_name}'. "
                "Lilbot requires a local checkpoint or a model already cached offline. "
                f"Original error: {exc}"
            ) from exc

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.uses_chat_template = bool(getattr(self.tokenizer, "chat_template", None))
        try:
            if not hasattr(self.model, "hf_device_map"):
                self.model.to(self.device)
        except RuntimeError as exc:
            if self._should_fallback_to_cpu(exc):
                self.torch.cuda.empty_cache()
                self.load_warnings.append(
                    "CUDA ran out of memory during model load; falling back to CPU because --device auto was used."
                )
                self.device = self.torch.device("cpu")
                self.quantization_active = False
                self.model.to(device=self.device, dtype=self.torch.float32)
            elif "out of memory" in str(exc).lower() and self.device.type == "cuda":
                self.torch.cuda.empty_cache()
                raise RuntimeError(
                    "The model ran out of GPU memory while loading. Retry with --device cpu or use a smaller local checkpoint."
                ) from exc
            else:
                raise
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

        generation_kwargs: dict[str, object] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.temperature > 0.0,
            "use_cache": True,
            "repetition_penalty": 1.05,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        if self.temperature > 0.0:
            generation_kwargs["temperature"] = self.temperature

        try:
            with self.torch.inference_mode():
                outputs = self.model.generate(**inputs, **generation_kwargs)
        except RuntimeError as exc:
            if "out of memory" in str(exc).lower() and self.device.type == "cuda":
                self.torch.cuda.empty_cache()
                raise RuntimeError(
                    "The model ran out of GPU memory. Retry with --device cpu or use a smaller local checkpoint."
                ) from exc
            raise

        generated = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()
        return generated or "FINAL: (empty response)"

    def _build_quantization_config(self) -> object | None:
        if not self.quantize_4bit:
            return None
        if self.device.type != "cuda":
            self._warn_once(
                "4-bit quantization requires CUDA; continuing without quantization."
            )
            return None

        try:
            import bitsandbytes  # noqa: F401
            from transformers import BitsAndBytesConfig
        except ImportError:
            self._warn_once(
                "bitsandbytes is not installed; continuing without 4-bit quantization. "
                "Install it with `python -m pip install bitsandbytes`."
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
            model = auto_model.from_pretrained(self.model_name, **model_kwargs)
        except Exception as exc:
            if quantization_config is not None:
                lowered = str(exc).lower()
                if "out of memory" in lowered and self.device_pref == "auto":
                    self._warn_once(
                        "4-bit quantization failed due to GPU memory pressure; "
                        "falling back to CPU because --device auto was used."
                    )
                    return self._load_model_on_cpu(auto_model, warning_message=None)
                if "out of memory" in lowered and self.device_pref == "cuda":
                    raise RuntimeError(
                        "4-bit GPU loading ran out of memory. Free GPU memory, use a smaller checkpoint, "
                        "or retry with --device cpu."
                    ) from exc
                self._warn_once(
                    f"4-bit quantization failed ({exc}); retrying without quantization. "
                    "This may use much more GPU memory."
                )
                retry_kwargs = dict(model_kwargs)
                retry_kwargs.pop("quantization_config", None)
                try:
                    model = auto_model.from_pretrained(self.model_name, **retry_kwargs)
                except Exception as retry_exc:
                    if self._should_fallback_to_cpu(retry_exc):
                        return self._load_model_on_cpu(auto_model)
                    raise retry_exc
                self.quantization_active = False
                return model
            if self._should_fallback_to_cpu(exc):
                return self._load_model_on_cpu(auto_model)
            raise

        self.quantization_active = quantization_config is not None
        return model

    def _load_model_on_cpu(
        self,
        auto_model: object,
        *,
        warning_message: str | None = (
            "CUDA ran out of memory during model load; falling back to CPU because --device auto was used."
        ),
    ) -> object:
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()
        if warning_message:
            self._warn_once(warning_message)
        self.device = self.torch.device("cpu")
        self.quantization_active = False
        return auto_model.from_pretrained(
            self.model_name,
            local_files_only=True,
            trust_remote_code=True,
            low_cpu_mem_usage=True,
        )

    def _resolve_device(self, device: str):
        normalized = (device or "auto").strip().lower()
        if normalized not in {"auto", "cpu", "cuda"}:
            raise RuntimeError("device must be one of: auto, cpu, cuda")

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="CUDA initialization: .*")
            warnings.filterwarnings("ignore", message="Can't initialize NVML")
            cuda_available = bool(self.torch.cuda.is_available())

        if normalized == "cpu":
            return self.torch.device("cpu")
        if normalized == "cuda" and not cuda_available:
            raise RuntimeError("CUDA was requested but is not available.")
        return self.torch.device("cuda" if cuda_available else "cpu")

    def _should_fallback_to_cpu(self, exc: Exception) -> bool:
        return (
            self.device_pref == "auto"
            and self.device.type == "cuda"
            and "out of memory" in str(exc).lower()
        )

    def _resolve_max_input_tokens(self) -> int:
        limits = [self.DEFAULT_MAX_INPUT_TOKENS]
        for value in (
            getattr(self.model.config, "max_position_embeddings", None),
            getattr(self.tokenizer, "model_max_length", None),
        ):
            if isinstance(value, int) and 0 < value < 100_000:
                limits.append(value)
        return min(limits)

    def _build_max_memory_map(self) -> dict[object, int] | None:
        try:
            gpu_index = (
                int(self.device.index)
                if getattr(self.device, "index", None) is not None
                else int(self.torch.cuda.current_device())
            )
            free_bytes, total_bytes = self.torch.cuda.mem_get_info(gpu_index)
        except Exception:
            return None

        headroom_mb = _read_positive_int_env("LILBOT_GPU_HEADROOM_MB", default=1024)
        headroom_bytes = headroom_mb * 1024 * 1024
        usable_bytes = max(0, min(int(free_bytes), int(total_bytes)) - headroom_bytes)
        if usable_bytes <= 0:
            return None

        cpu_offload_gb = _read_positive_int_env("LILBOT_CPU_OFFLOAD_GB", default=48)
        cpu_offload_bytes = cpu_offload_gb * 1024 * 1024 * 1024
        return {gpu_index: usable_bytes, "cpu": cpu_offload_bytes}

    def _runtime_summary(self) -> str:
        summary = [
            f"Loaded local Hugging Face model: {self.model_name}",
            f"device={self.device.type}",
            f"max_new_tokens={self.max_new_tokens}",
            f"temperature={self.temperature:.2f}",
        ]
        if self.quantization_active:
            summary.append("4-bit")
        if _model_uses_cpu_offload(self.model):
            summary.append("cpu-offload")
        if self.uses_chat_template:
            summary.append("chat-template")
        return " | ".join(summary)

    def _warn_once(self, message: str) -> None:
        if message not in self.load_warnings:
            self.load_warnings.append(message)


def _render_prompt_with_chat_template(tokenizer: object, prompt: str) -> str:
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
    ):
        if package_name in DISABLED_TRANSFORMERS_OPTIONAL_PACKAGES:
            return (False, "N/A") if return_version else (False, None)
        return original(package_name, return_version=return_version)

    import_utils._is_package_available = _patched_is_package_available
    utils_module.is_pandas_available = lambda: False
    utils_module.is_sklearn_available = lambda: False


def _model_uses_cpu_offload(model: object) -> bool:
    device_map = getattr(model, "hf_device_map", None)
    if not isinstance(device_map, dict):
        return False
    return any(str(target).startswith("cpu") or str(target).startswith("disk") for target in device_map.values())


def _read_positive_int_env(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _select_dtype_kwarg(transformers_version: str) -> str:
    raw = str(transformers_version).strip()
    try:
        major = int(raw.split(".", 1)[0])
    except (TypeError, ValueError):
        return "torch_dtype"
    return "dtype" if major >= 5 else "torch_dtype"
