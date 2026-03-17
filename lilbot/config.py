"""Runtime configuration and safe path resolution for Lilbot."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_ALLOWED_LOG_ROOTS = (Path("/var/log"), Path("/private/var/log"))
DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)
MODEL_WEIGHT_SUFFIXES = (".safetensors", ".bin")
MODEL_WEIGHT_INDEXES = ("model.safetensors.index.json", "pytorch_model.bin.index.json")
TOKENIZER_FILES = ("tokenizer.json", "tokenizer.model", "tokenizer_config.json")
DEFAULT_USER_CONFIG_FILENAME = "config.json"
USER_CONFIG_ENV_VAR = "LILBOT_CONFIG_PATH"


def _coerce_positive_int(value: int | str | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _coerce_non_negative_float(value: float | str | None, default: float) -> float:
    try:
        parsed = float(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0.0 else default


def _coerce_bool(value: bool | str | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_complete_model_path(path: str | Path | None) -> bool:
    """Return True when a directory looks like a usable local HF checkpoint."""

    if path is None:
        return False

    candidate = Path(path).expanduser()
    if not candidate.exists() or not candidate.is_dir():
        return False
    if not (candidate / "config.json").is_file():
        return False
    if not any((candidate / filename).is_file() for filename in TOKENIZER_FILES):
        return False
    if any((candidate / filename).is_file() for filename in MODEL_WEIGHT_INDEXES):
        return True
    return any(candidate.glob(f"*{suffix}") for suffix in MODEL_WEIGHT_SUFFIXES)


def discover_default_model() -> str | None:
    """Find the first bundled local checkpoint under lilbot/models."""

    package_root = Path(__file__).resolve().parent
    search_roots = (
        package_root / "models",
        Path.cwd() / "lilbot" / "models",
    )

    for root in search_roots:
        if is_complete_model_path(root):
            return str(root.resolve())
        if not root.is_dir():
            continue
        for candidate in sorted(root.iterdir()):
            if is_complete_model_path(candidate):
                return str(candidate.resolve())
    return None


@dataclass(frozen=True)
class UserConfigFile:
    """On-disk user configuration state."""

    path: Path
    values: dict[str, Any]
    exists: bool
    error: str | None = None


def default_user_config_path() -> Path:
    """Return the per-user Lilbot config path."""

    override = os.getenv(USER_CONFIG_ENV_VAR)
    if override:
        return Path(override).expanduser()

    xdg_root = os.getenv("XDG_CONFIG_HOME")
    base_root = Path(xdg_root).expanduser() if xdg_root else Path.home() / ".config"
    return base_root / "lilbot" / DEFAULT_USER_CONFIG_FILENAME


def read_user_config_file(path: str | Path | None = None) -> UserConfigFile:
    """Read the persistent Lilbot config file if it exists."""

    config_path = Path(path).expanduser() if path is not None else default_user_config_path()
    if not config_path.exists():
        return UserConfigFile(path=config_path, values={}, exists=False)

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        return UserConfigFile(
            path=config_path,
            values={},
            exists=True,
            error=f"Could not read config file: {exc}",
        )

    try:
        parsed = json.loads(raw_text or "{}")
    except json.JSONDecodeError as exc:
        return UserConfigFile(
            path=config_path,
            values={},
            exists=True,
            error=f"Invalid JSON in config file: {exc}",
        )

    if not isinstance(parsed, dict):
        return UserConfigFile(
            path=config_path,
            values={},
            exists=True,
            error="Config file must contain a JSON object.",
        )

    return UserConfigFile(path=config_path, values=dict(parsed), exists=True)


def save_user_config(values: dict[str, Any], path: str | Path | None = None) -> Path:
    """Persist user-facing Lilbot settings to disk."""

    config_path = Path(path).expanduser() if path is not None else default_user_config_path()
    serialized = json.dumps(values, indent=2, sort_keys=True)
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(serialized + "\n", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Could not write Lilbot config to {config_path}: {exc}") from exc
    return config_path


def _coerce_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class LilbotConfig:
    """Central runtime configuration for Lilbot."""

    backend: str
    model: str | None
    device: str
    max_new_tokens: int
    temperature: float
    quantize_4bit: bool
    max_steps: int
    workspace_root: Path
    verbose: bool
    shell_timeout_seconds: int
    shell_max_output_chars: int
    file_preview_chars: int
    directory_entry_limit: int
    repo_file_limit: int
    repo_reference_limit: int
    log_tail_lines: int
    log_sample_chars: int
    user_config_path: Path
    user_config_loaded: bool = False
    user_config_error: str | None = None
    allowed_log_roots: tuple[Path, ...] = DEFAULT_ALLOWED_LOG_ROOTS
    ignored_directories: frozenset[str] = DEFAULT_IGNORED_DIRECTORIES

    @classmethod
    def from_sources(
        cls,
        *,
        backend: str | None = None,
        model: str | None = None,
        device: str | None = None,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
        quantize_4bit: bool | None = None,
        max_steps: int | None = None,
        workspace_root: str | None = None,
        shell_timeout_seconds: int | None = None,
        verbose: bool = False,
    ) -> "LilbotConfig":
        user_config = read_user_config_file()
        stored_values = user_config.values

        root_text = (
            workspace_root
            or os.getenv("LILBOT_WORKSPACE_ROOT")
            or _coerce_text(stored_values.get("workspace_root"))
            or os.getcwd()
        )
        resolved_root = Path(root_text).expanduser().resolve()
        resolved_model = (
            _coerce_text(model)
            or _coerce_text(os.getenv("LILBOT_MODEL"))
            or _coerce_text(stored_values.get("model"))
            or discover_default_model()
        )
        return cls(
            backend=(
                _coerce_text(backend)
                or _coerce_text(os.getenv("LILBOT_BACKEND"))
                or _coerce_text(stored_values.get("backend"))
                or "hf"
            ).strip().lower(),
            model=resolved_model,
            device=(
                _coerce_text(device)
                or _coerce_text(os.getenv("LILBOT_DEVICE"))
                or _coerce_text(stored_values.get("device"))
                or "auto"
            ).strip().lower(),
            max_new_tokens=_coerce_positive_int(
                max_new_tokens
                if max_new_tokens is not None
                else os.getenv("LILBOT_MAX_NEW_TOKENS", stored_values.get("max_new_tokens")),
                192,
            ),
            temperature=_coerce_non_negative_float(
                temperature
                if temperature is not None
                else os.getenv("LILBOT_TEMPERATURE", stored_values.get("temperature")),
                0.0,
            ),
            quantize_4bit=_coerce_bool(
                quantize_4bit
                if quantize_4bit is not None
                else os.getenv("LILBOT_QUANTIZE_4BIT", stored_values.get("quantize_4bit")),
                True,
            ),
            max_steps=_coerce_positive_int(
                max_steps
                if max_steps is not None
                else os.getenv("LILBOT_MAX_STEPS", stored_values.get("max_steps")),
                4,
            ),
            workspace_root=resolved_root,
            verbose=bool(verbose),
            shell_timeout_seconds=_coerce_positive_int(
                shell_timeout_seconds
                if shell_timeout_seconds is not None
                else os.getenv("LILBOT_SHELL_TIMEOUT", stored_values.get("shell_timeout_seconds")),
                8,
            ),
            shell_max_output_chars=_coerce_positive_int(
                os.getenv("LILBOT_SHELL_OUTPUT_LIMIT", stored_values.get("shell_max_output_chars")),
                6000,
            ),
            file_preview_chars=_coerce_positive_int(
                os.getenv("LILBOT_FILE_PREVIEW_CHARS", stored_values.get("file_preview_chars")),
                6000,
            ),
            directory_entry_limit=_coerce_positive_int(
                os.getenv("LILBOT_DIRECTORY_ENTRY_LIMIT", stored_values.get("directory_entry_limit")),
                200,
            ),
            repo_file_limit=_coerce_positive_int(
                os.getenv("LILBOT_REPO_FILE_LIMIT", stored_values.get("repo_file_limit")),
                500,
            ),
            repo_reference_limit=_coerce_positive_int(
                os.getenv("LILBOT_REPO_REFERENCE_LIMIT", stored_values.get("repo_reference_limit")),
                20,
            ),
            log_tail_lines=_coerce_positive_int(
                os.getenv("LILBOT_LOG_TAIL_LINES", stored_values.get("log_tail_lines")),
                400,
            ),
            log_sample_chars=_coerce_positive_int(
                os.getenv("LILBOT_LOG_SAMPLE_CHARS", stored_values.get("log_sample_chars")),
                160,
            ),
            user_config_path=user_config.path,
            user_config_loaded=user_config.exists and user_config.error is None,
            user_config_error=user_config.error,
        )

    def resolve_workspace_path(self, path: str | Path, *, must_exist: bool = False) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        resolved = candidate.resolve(strict=False)

        if resolved != self.workspace_root and self.workspace_root not in resolved.parents:
            raise ValueError(f"{path!s} is outside the workspace root {self.workspace_root}")
        if must_exist and not resolved.exists():
            raise ValueError(f"{resolved} does not exist")
        return resolved

    def resolve_log_path(self, path: str | Path) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        resolved = candidate.resolve(strict=False)

        if resolved == self.workspace_root or self.workspace_root in resolved.parents:
            return resolved
        if any(resolved == root or root in resolved.parents for root in self.allowed_log_roots):
            return resolved
        raise ValueError(
            f"{path!s} is outside the workspace root and outside the allowed log directories"
        )

    def display_path(self, path: Path) -> str:
        try:
            relative = path.relative_to(self.workspace_root)
        except ValueError:
            return str(path)
        return "." if not relative.parts else f"./{relative.as_posix()}"

    def to_user_config_dict(self) -> dict[str, Any]:
        """Return the user-facing settings that should be persisted."""

        values: dict[str, Any] = {
            "backend": self.backend,
            "device": self.device,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "quantize_4bit": self.quantize_4bit,
            "max_steps": self.max_steps,
            "workspace_root": str(self.workspace_root),
            "shell_timeout_seconds": self.shell_timeout_seconds,
        }
        if self.model:
            values["model"] = self.model
        return values
