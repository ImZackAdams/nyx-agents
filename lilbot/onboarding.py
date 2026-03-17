"""User-facing onboarding and diagnostics helpers for Lilbot."""

from __future__ import annotations

from collections.abc import Callable
from importlib import metadata
from pathlib import Path
import sys
import warnings

from lilbot.config import (
    LilbotConfig,
    discover_default_model,
    is_complete_model_path,
    read_user_config_file,
    save_user_config,
)


def render_doctor_report(config: LilbotConfig) -> str:
    """Render a setup and environment diagnostics report."""

    user_config = read_user_config_file(config.user_config_path)
    discovered_model = discover_default_model()

    lines = ["Lilbot doctor", ""]
    lines.extend(
        [
            "Configuration",
            f"- config_file: {config.user_config_path}",
            f"- config_status: {_describe_user_config_state(user_config)}",
            f"- workspace_root: {config.workspace_root}",
            f"- backend: {config.backend}",
            f"- device_preference: {config.device}",
            f"- quantize_4bit: {'enabled' if config.quantize_4bit else 'disabled'}",
            f"- max_new_tokens: {config.max_new_tokens}",
            f"- max_steps: {config.max_steps}",
            f"- model: {config.model or '(not configured)'}",
            f"- model_status: {_describe_model_status(config.model)}",
        ]
    )
    if discovered_model and discovered_model != config.model:
        lines.append(f"- auto_discovered_model: {discovered_model}")

    lines.append("")
    lines.extend(
        [
            "Python",
            f"- executable: {sys.executable}",
            f"- version: {sys.version.split()[0]}",
        ]
    )

    package_lines, package_state = _package_diagnostics()
    lines.append("")
    lines.append("Packages")
    lines.extend(package_lines)

    cuda_lines, cuda_state = _cuda_diagnostics()
    lines.append("")
    lines.append("CUDA")
    lines.extend(cuda_lines)

    next_steps = _doctor_next_steps(
        config,
        user_config=user_config,
        package_state=package_state,
        cuda_state=cuda_state,
    )
    lines.append("")
    lines.append("Next steps")
    lines.extend(f"- {step}" for step in next_steps)

    return "\n".join(lines)


def run_init_wizard(
    config: LilbotConfig,
    *,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> str:
    """Interactively collect and persist Lilbot defaults."""

    existing = read_user_config_file(config.user_config_path)
    output_func("Lilbot setup")
    output_func("Press Enter to keep the value in brackets. Type `none` to clear optional values.")

    if existing.exists:
        should_overwrite = _prompt_bool(
            "A Lilbot config already exists. Overwrite it",
            default=False,
            input_func=input_func,
        )
        if not should_overwrite:
            return f"Kept existing Lilbot config at {config.user_config_path}"

    workspace_root = _prompt_directory(
        "Workspace root",
        default=str(config.workspace_root),
        input_func=input_func,
        output_func=output_func,
    )
    model_path = _prompt_text(
        "Local model path",
        default=config.model,
        allow_clear=True,
        input_func=input_func,
    )
    if model_path and not is_complete_model_path(model_path):
        output_func(
            "Warning: that path does not look like a complete local Hugging Face checkpoint yet."
        )

    device = _prompt_choice(
        "Preferred device",
        options=("auto", "cpu", "cuda"),
        default=config.device,
        input_func=input_func,
        output_func=output_func,
    )

    if device == "cpu":
        quantize_4bit = False
        output_func("4-bit quantization is disabled for CPU mode.")
    else:
        quantize_4bit = _prompt_bool(
            "Enable 4-bit quantization when supported",
            default=config.quantize_4bit,
            input_func=input_func,
        )

    max_new_tokens = _prompt_int(
        "Max new tokens per model step",
        default=config.max_new_tokens,
        input_func=input_func,
        output_func=output_func,
    )
    max_steps = _prompt_int(
        "Max reasoning steps",
        default=config.max_steps,
        input_func=input_func,
        output_func=output_func,
    )
    shell_timeout_seconds = _prompt_int(
        "Shell timeout in seconds",
        default=config.shell_timeout_seconds,
        input_func=input_func,
        output_func=output_func,
    )

    values = {
        "backend": config.backend,
        "device": device,
        "max_new_tokens": max_new_tokens,
        "temperature": config.temperature,
        "quantize_4bit": quantize_4bit,
        "max_steps": max_steps,
        "workspace_root": workspace_root,
        "shell_timeout_seconds": shell_timeout_seconds,
    }
    if model_path:
        values["model"] = model_path

    path = save_user_config(values, config.user_config_path)
    return "\n".join(
        [
            f"Saved Lilbot config to {path}",
            "Next steps:",
            "- Run `lilbot doctor` to verify the environment.",
            "- Run `lilbot` to start the interactive assistant.",
        ]
    )


def _describe_user_config_state(user_config) -> str:
    if user_config.error:
        return f"invalid ({user_config.error})"
    if user_config.exists:
        return "loaded"
    return "not found"


def _describe_model_status(model_path: str | None) -> str:
    if not model_path:
        discovered = discover_default_model()
        if discovered:
            return "not explicitly configured; a bundled model is auto-discoverable"
        return "missing"
    if is_complete_model_path(model_path):
        return "valid local checkpoint"
    candidate = Path(model_path).expanduser()
    if candidate.exists():
        return "path exists, but it does not look like a complete local checkpoint"
    return "path does not exist"


def _package_diagnostics() -> tuple[list[str], dict[str, bool]]:
    package_names = ("torch", "transformers", "accelerate", "bitsandbytes")
    lines: list[str] = []
    state: dict[str, bool] = {}
    for name in package_names:
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            lines.append(f"- {name}: missing")
            state[name] = False
        else:
            lines.append(f"- {name}: {version}")
            state[name] = True
    return lines, state


def _cuda_diagnostics() -> tuple[list[str], dict[str, object]]:
    try:
        import torch
    except ImportError:
        return ["- torch is not installed, so CUDA could not be checked"], {"available": False}

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="CUDA initialization: .*")
        warnings.filterwarnings("ignore", message="Can't initialize NVML")
        available = bool(torch.cuda.is_available())

    lines = [f"- torch.cuda.is_available(): {available}"]
    state: dict[str, object] = {"available": available}

    if not available:
        lines.append("- device_count: 0")
        return lines, state

    count = int(torch.cuda.device_count())
    state["device_count"] = count
    lines.append(f"- device_count: {count}")
    for index in range(count):
        try:
            name = torch.cuda.get_device_name(index)
        except Exception as exc:  # pragma: no cover - defensive
            name = f"unavailable ({exc})"
        lines.append(f"- device_{index}: {name}")
    return lines, state


def _doctor_next_steps(
    config: LilbotConfig,
    *,
    user_config,
    package_state: dict[str, bool],
    cuda_state: dict[str, object],
) -> list[str]:
    steps: list[str] = []

    if user_config.error:
        steps.append("Fix the invalid config file or rerun `lilbot init` to rewrite it.")
    if not user_config.exists:
        steps.append("Run `lilbot init` to save your preferred model, device, and workspace.")
    if not package_state.get("torch") or not package_state.get("transformers"):
        steps.append("Install the model runtime with `pip install -e \".[hf]\"`.")
    if config.quantize_4bit and not package_state.get("bitsandbytes"):
        steps.append("Install 4-bit support with `pip install -e \".[hf,quantization]\"`.")
    if config.device == "cuda" and not cuda_state.get("available"):
        steps.append("CUDA is not available to this Python environment. Use `--device cpu` or fix the GPU environment.")
    if not config.model:
        steps.append("Set a local model path with `lilbot init` or pass `--model /path/to/model`.")
    elif not is_complete_model_path(config.model):
        steps.append("Point Lilbot at a complete local Hugging Face checkpoint before running inference.")
    if not steps:
        steps.append("Run `lilbot` to start the interactive assistant.")
        steps.append("Use `lilbot repo summarize .` to try a deterministic command path.")
    return steps


def _prompt_text(
    label: str,
    *,
    default: str | None = None,
    allow_clear: bool = False,
    input_func: Callable[[str], str] = input,
) -> str | None:
    suffix = f" [{default}]" if default else ""
    raw = input_func(f"{label}{suffix}: ").strip()
    if not raw:
        return default.strip() if isinstance(default, str) and default.strip() else None
    if allow_clear and raw.lower() == "none":
        return None
    return raw


def _prompt_directory(
    label: str,
    *,
    default: str,
    input_func: Callable[[str], str],
    output_func: Callable[[str], None],
) -> str:
    while True:
        value = _prompt_text(label, default=default, input_func=input_func)
        if value is None:
            output_func("Please provide an existing directory.")
            continue
        candidate = Path(value).expanduser()
        if candidate.is_dir():
            return str(candidate.resolve())
        output_func("That directory does not exist. Please enter an existing directory.")


def _prompt_choice(
    label: str,
    *,
    options: tuple[str, ...],
    default: str,
    input_func: Callable[[str], str],
    output_func: Callable[[str], None],
) -> str:
    option_text = "/".join(options)
    while True:
        value = _prompt_text(
            f"{label} ({option_text})",
            default=default,
            input_func=input_func,
        )
        if value in options:
            return value
        output_func(f"Please choose one of: {option_text}.")


def _prompt_bool(
    label: str,
    *,
    default: bool,
    input_func: Callable[[str], str] = input,
) -> bool:
    suffix = "Y/n" if default else "y/N"
    raw = input_func(f"{label} [{suffix}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def _prompt_int(
    label: str,
    *,
    default: int,
    input_func: Callable[[str], str],
    output_func: Callable[[str], None],
) -> int:
    while True:
        raw = _prompt_text(label, default=str(default), input_func=input_func)
        if raw is None:
            return default
        try:
            parsed = int(raw)
        except ValueError:
            output_func("Please enter a whole number.")
            continue
        if parsed <= 0:
            output_func("Please enter a positive integer.")
            continue
        return parsed
