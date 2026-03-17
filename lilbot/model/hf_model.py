"""Hugging Face local model backend."""

from __future__ import annotations

import os
import warnings

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("USE_TF", "0")

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
    ) -> None:
        if not model_name:
            raise RuntimeError(
                "No local model is configured. Pass --model or set LILBOT_MODEL."
            )

        try:
            import torch
            import transformers

            _disable_optional_transformers_packages(transformers)
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Local model dependencies are missing. Install them with "
                "`pip install -r requirements.txt` or `pip install -e .[hf]`."
            ) from exc

        self.torch = torch
        self.model_name = model_name
        self.max_new_tokens = max(1, int(max_new_tokens))
        self.temperature = max(0.0, float(temperature))
        self.device = self._resolve_device(device)

        tokenizer_kwargs = {
            "local_files_only": True,
            "trust_remote_code": True,
            "use_fast": True,
        }
        model_kwargs: dict[str, object] = {
            "local_files_only": True,
            "trust_remote_code": True,
        }

        if self.device.type == "cuda":
            model_kwargs["torch_dtype"] = torch.float16

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, **tokenizer_kwargs)
            self.model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load local model '{model_name}'. "
                "Lilbot requires a local checkpoint or a model already cached offline. "
                f"Original error: {exc}"
            ) from exc

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.uses_chat_template = bool(getattr(self.tokenizer, "chat_template", None))
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

        generation_kwargs: dict[str, object] = {
            "max_new_tokens": self.max_new_tokens,
            "do_sample": self.temperature > 0.0,
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
        summary = [
            f"Loaded local Hugging Face model: {self.model_name}",
            f"device={self.device.type}",
            f"max_new_tokens={self.max_new_tokens}",
            f"temperature={self.temperature:.2f}",
        ]
        if self.uses_chat_template:
            summary.append("chat-template")
        return " | ".join(summary)


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
