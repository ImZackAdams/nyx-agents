"""User-facing onboarding and diagnostics helpers for Lilbot."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import metadata
import importlib
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
from lilbot.tools import build_default_tool_registry


@dataclass(frozen=True)
class SelfTestCheck:
    """A single self-test result row."""

    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class SelfTestResult:
    """Structured result for the Lilbot self-test command."""

    checks: tuple[SelfTestCheck, ...]

    @property
    def failures(self) -> int:
        return sum(1 for check in self.checks if check.status == "FAIL")

    @property
    def warnings(self) -> int:
        return sum(1 for check in self.checks if check.status == "WARN")

    @property
    def passes(self) -> int:
        return sum(1 for check in self.checks if check.status == "PASS")

    @property
    def exit_code(self) -> int:
        return 1 if self.failures else 0

    @property
    def overall_status(self) -> str:
        if self.failures:
            return "FAIL"
        if self.warnings:
            return "WARN"
        return "PASS"


def run_self_test(config: LilbotConfig) -> SelfTestResult:
    """Run a lightweight runtime validation without loading the full model."""

    checks = [
        _self_test_config(config),
        _self_test_model(config),
        _self_test_required_imports(),
    ]

    required_imports_ok = checks[-1].status != "FAIL"
    checks.append(_self_test_optional_quantization(config))
    checks.append(_self_test_cuda(config))
    checks.append(_self_test_tool_execution(config))

    if not required_imports_ok:
        checks.append(
            SelfTestCheck(
                name="notes",
                status="WARN",
                detail="Model runtime imports are incomplete, so Lilbot can only use deterministic commands until the runtime is installed.",
            )
        )

    return SelfTestResult(checks=tuple(checks))


def render_self_test_report(result: SelfTestResult) -> str:
    """Render a human-readable report for the Lilbot self-test."""

    lines = ["Lilbot self-test", ""]
    for check in result.checks:
        lines.append(f"[{check.status}] {check.name}: {check.detail}")

    lines.extend(
        [
            "",
            "Summary",
            f"- status: {result.overall_status}",
            f"- passes: {result.passes}",
            f"- warnings: {result.warnings}",
            f"- failures: {result.failures}",
        ]
    )

    next_steps = _self_test_next_steps(result)
    if next_steps:
        lines.append("")
        lines.append("Next steps")
        lines.extend(f"- {step}" for step in next_steps)

    return "\n".join(lines)


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
    if not (config.model or discover_default_model()):
        output_func(
            "Note: Lilbot needs a local model path for chat and free-form AI queries. "
            "If you leave it blank, only deterministic commands will be ready."
        )

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
    ai_ready = bool(model_path or discover_default_model())
    if ai_ready:
        return "\n".join(
            [
                f"Saved Lilbot config to {path}",
                "Next steps:",
                "- Run `lilbot doctor` to verify the environment.",
                "- Run `lilbot self-test` for a one-command health check.",
                "- Run `lilbot` to start the interactive assistant.",
            ]
        )
    return "\n".join(
        [
            f"Saved Lilbot config to {path}",
            "Lilbot is not ready for AI chat yet because no local model is configured.",
            "Next steps:",
            "- Rerun `lilbot init` and enter a local model path, or pass `--model /path/to/model`.",
            "- Run `lilbot doctor` to review the current environment.",
            "- Deterministic commands like `lilbot repo summarize .` and `lilbot explain-command ...` still work now.",
        ]
    )


def _self_test_config(config: LilbotConfig) -> SelfTestCheck:
    workspace_exists = config.workspace_root.is_dir()
    if config.user_config_error:
        return SelfTestCheck(
            name="config",
            status="FAIL",
            detail=f"Config file is invalid: {config.user_config_error}",
        )
    if not workspace_exists:
        return SelfTestCheck(
            name="config",
            status="FAIL",
            detail=f"Workspace root does not exist: {config.workspace_root}",
        )

    if config.user_config_loaded:
        source = f"user config loaded from {config.user_config_path}"
    else:
        source = f"using defaults or environment values; config file path is {config.user_config_path}"
    return SelfTestCheck(
        name="config",
        status="PASS",
        detail=f"Workspace root is available at {config.workspace_root}; {source}.",
    )


def _self_test_model(config: LilbotConfig) -> SelfTestCheck:
    if config.model and is_complete_model_path(config.model):
        return SelfTestCheck(
            name="model",
            status="PASS",
            detail=f"Found a valid local checkpoint at {config.model}.",
        )
    discovered = discover_default_model()
    if discovered and is_complete_model_path(discovered):
        return SelfTestCheck(
            name="model",
            status="PASS",
            detail=f"Auto-discovered a valid local checkpoint at {discovered}.",
        )
    if config.model:
        return SelfTestCheck(
            name="model",
            status="FAIL",
            detail=f"Configured model path is not a complete local checkpoint: {config.model}",
        )
    return SelfTestCheck(
        name="model",
        status="FAIL",
        detail="No local model is configured or auto-discoverable.",
    )


def _self_test_required_imports() -> SelfTestCheck:
    packages = ("torch", "transformers", "accelerate")
    versions: list[str] = []
    missing: list[str] = []

    for package_name in packages:
        module, version = _import_package_version(package_name)
        if module is None or version is None:
            missing.append(package_name)
        else:
            versions.append(f"{package_name}={version}")

    if missing:
        return SelfTestCheck(
            name="imports",
            status="FAIL",
            detail=(
                "Missing required runtime packages: "
                + ", ".join(missing)
                + ". Install them with `python -m pip install torch transformers accelerate`."
            ),
        )
    return SelfTestCheck(
        name="imports",
        status="PASS",
        detail="Imported runtime packages successfully: " + ", ".join(versions),
    )


def _self_test_optional_quantization(config: LilbotConfig) -> SelfTestCheck:
    module, version = _import_package_version("bitsandbytes")
    if module is not None and version is not None:
        return SelfTestCheck(
            name="quantization",
            status="WARN" if config.quantize_4bit else "PASS",
            detail=(
                f"bitsandbytes is available ({version}), but self-test does not prove that the current checkpoint fits in GPU memory."
                if config.quantize_4bit
                else f"bitsandbytes is available ({version})."
            ),
        )
    if config.quantize_4bit:
        return SelfTestCheck(
            name="quantization",
            status="WARN",
            detail="4-bit quantization is requested, but bitsandbytes is not installed.",
        )
    return SelfTestCheck(
        name="quantization",
        status="PASS",
        detail="4-bit quantization is disabled, so bitsandbytes is optional.",
    )


def _self_test_cuda(config: LilbotConfig) -> SelfTestCheck:
    try:
        import torch
    except ImportError:
        return SelfTestCheck(
            name="cuda",
            status="WARN",
            detail="Torch is not installed, so CUDA could not be checked.",
        )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="CUDA initialization: .*")
        warnings.filterwarnings("ignore", message="Can't initialize NVML")
        available = bool(torch.cuda.is_available())

    if available:
        count = int(torch.cuda.device_count())
        device_names = []
        for index in range(count):
            try:
                device_names.append(torch.cuda.get_device_name(index))
            except Exception:  # pragma: no cover - defensive
                device_names.append(f"cuda:{index}")
        return SelfTestCheck(
            name="cuda",
            status="PASS",
            detail=f"CUDA is available with {count} device(s): {', '.join(device_names)}",
        )

    if config.device == "cuda":
        return SelfTestCheck(
            name="cuda",
            status="FAIL",
            detail="CUDA was requested, but this Python environment cannot see a GPU.",
        )
    if config.device == "auto":
        return SelfTestCheck(
            name="cuda",
            status="WARN",
            detail="CUDA is not available here, so Lilbot will run on CPU in this environment.",
        )
    return SelfTestCheck(
        name="cuda",
        status="PASS",
        detail="CUDA is not available, but the current config already prefers CPU mode.",
    )


def _self_test_tool_execution(config: LilbotConfig) -> SelfTestCheck:
    try:
        registry = build_default_tool_registry(config)
        observation = registry.execute("list_directory", {"path": "."})
    except Exception as exc:  # pragma: no cover - defensive
        return SelfTestCheck(
            name="tooling",
            status="FAIL",
            detail=f"Failed to build the tool registry or run a deterministic tool: {exc}",
        )

    if observation.startswith("Directory listing for "):
        return SelfTestCheck(
            name="tooling",
            status="PASS",
            detail="Successfully ran the `list_directory` tool against the workspace root.",
        )
    return SelfTestCheck(
        name="tooling",
        status="FAIL",
        detail=f"Deterministic tool returned an unexpected result: {observation}",
    )


def _self_test_next_steps(result: SelfTestResult) -> list[str]:
    steps: list[str] = []
    for check in result.checks:
        if check.name == "config" and check.status == "FAIL":
            steps.append("Fix the config issue or rerun `lilbot init` to save a valid setup.")
        elif check.name == "model" and check.status == "FAIL":
            steps.append("Point Lilbot at a complete local model with `lilbot init` or `--model /path/to/model`.")
            steps.append(
                "Deterministic commands still work without a model, but chat and free-form queries need a local checkpoint."
            )
        elif check.name == "imports" and check.status == "FAIL":
            steps.append(
                "Install the model runtime in this environment with `python -m pip install torch transformers accelerate`."
            )
        elif check.name == "quantization" and check.status == "WARN":
            if "not installed" in check.detail:
                steps.append(
                    "Install 4-bit support with `python -m pip install bitsandbytes` if you want GPU quantization."
                )
            else:
                steps.append(
                    "Validate GPU loading with `lilbot --device cuda --quantize-4bit \"hello\"`; `--device auto` may fall back to CPU when the model does not fit."
                )
        elif check.name == "cuda" and check.status == "FAIL":
            steps.append("Use `--device cpu` or fix CUDA visibility in the active Python environment.")
        elif check.name == "cuda" and check.status == "WARN":
            steps.append("If you expected GPU usage, confirm that your current Python environment can see CUDA.")
        elif check.name == "tooling" and check.status == "FAIL":
            steps.append("Verify that the configured workspace root exists and is readable.")

    if not steps and result.overall_status == "PASS":
        steps.append("Run `lilbot` to start the interactive assistant.")
        steps.append("Use `lilbot doctor` when you want a more detailed environment report.")
    return steps


def _import_package_version(package_name: str) -> tuple[object | None, str | None]:
    try:
        module = importlib.import_module(package_name)
        version = metadata.version(package_name)
    except (ImportError, metadata.PackageNotFoundError):
        return None, None
    return module, version


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
        steps.append(
            "Install the model runtime in this environment with `python -m pip install torch transformers accelerate`."
        )
    if config.quantize_4bit and not package_state.get("bitsandbytes"):
        steps.append(
            "Install 4-bit support in this environment with `python -m pip install bitsandbytes`."
        )
    elif config.quantize_4bit and package_state.get("bitsandbytes") and cuda_state.get("available") and config.model:
        steps.append(
            "CUDA and bitsandbytes are available, but that does not guarantee this checkpoint fits in VRAM. Validate with `lilbot --device cuda --quantize-4bit \"hello\"`."
        )
        steps.append(
            "If `--device auto` falls back to CPU, try a smaller checkpoint or increase GPU headroom with `LILBOT_GPU_HEADROOM_MB` tuning only after confirming the model is close to fitting."
        )
    if config.device == "cuda" and not cuda_state.get("available"):
        steps.append("CUDA is not available to this Python environment. Use `--device cpu` or fix the GPU environment.")
    if not config.model:
        steps.append("Set a local model path with `lilbot init` or pass `--model /path/to/model`.")
        steps.append(
            "You can still use deterministic commands like `lilbot doctor`, `lilbot repo summarize .`, and `lilbot explain-command ...` without a model."
        )
    elif not is_complete_model_path(config.model):
        steps.append("Point Lilbot at a complete local Hugging Face checkpoint before running inference.")
    if not steps:
        steps.append("Run `lilbot self-test` for a quick pass/warn/fail validation.")
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
