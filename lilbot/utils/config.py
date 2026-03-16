"""Runtime configuration for Lilbot."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_ALLOWED_LOG_ROOTS = (Path("/var/log"), Path("/private/var/log"))
MODEL_WEIGHT_SUFFIXES = (".safetensors", ".bin")
MODEL_WEIGHT_INDEXES = ("model.safetensors.index.json", "pytorch_model.bin.index.json")
TOKENIZER_FILES = ("tokenizer.json", "tokenizer.model", "tokenizer_config.json")
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


def _coerce_positive_int(value: int | str | None, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _coerce_bool(value: bool | str | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_complete_model_path(path: str | Path | None) -> bool:
    """Return True when a directory looks like a complete local HF checkpoint."""

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


def discover_default_model_path() -> str | None:
    """Find the first bundled local model shipped with the repository."""

    package_root = Path(__file__).resolve().parents[1]
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
class LilbotConfig:
    model_path: str | None
    device: str
    max_new_tokens: int
    max_steps: int
    quantize_4bit: bool
    workspace_root: Path
    shell_timeout_seconds: int
    shell_max_output_chars: int
    file_max_chars: int
    directory_entry_limit: int
    repo_file_limit: int
    repo_reference_limit: int
    log_line_limit: int
    verbose_agent: bool
    allowed_log_roots: tuple[Path, ...] = DEFAULT_ALLOWED_LOG_ROOTS
    ignored_directories: frozenset[str] = DEFAULT_IGNORED_DIRECTORIES

    @classmethod
    def from_sources(
        cls,
        *,
        model_path: str | None = None,
        device: str | None = None,
        max_new_tokens: int | None = None,
        max_steps: int | None = None,
        quantize_4bit: bool | None = None,
        workspace_root: str | None = None,
        shell_timeout_seconds: int | None = None,
        verbose_agent: bool = True,
    ) -> "LilbotConfig":
        root_text = workspace_root or os.getenv("LILBOT_WORKSPACE_ROOT") or os.getcwd()
        resolved_root = Path(root_text).expanduser().resolve()
        resolved_model_path = (
            (model_path or os.getenv("LILBOT_MODEL_PATH") or "").strip() or discover_default_model_path()
        )
        return cls(
            model_path=resolved_model_path,
            device=(device or os.getenv("LILBOT_DEVICE") or "auto").strip().lower(),
            max_new_tokens=_coerce_positive_int(
                max_new_tokens if max_new_tokens is not None else os.getenv("LILBOT_MAX_NEW_TOKENS"),
                192,
            ),
            max_steps=_coerce_positive_int(
                max_steps if max_steps is not None else os.getenv("LILBOT_MAX_STEPS"),
                4,
            ),
            quantize_4bit=_coerce_bool(
                quantize_4bit if quantize_4bit is not None else os.getenv("LILBOT_QUANTIZE_4BIT"),
                True,
            ),
            workspace_root=resolved_root,
            shell_timeout_seconds=_coerce_positive_int(
                shell_timeout_seconds
                if shell_timeout_seconds is not None
                else os.getenv("LILBOT_SHELL_TIMEOUT"),
                8,
            ),
            shell_max_output_chars=_coerce_positive_int(
                os.getenv("LILBOT_SHELL_OUTPUT_LIMIT"),
                6000,
            ),
            file_max_chars=_coerce_positive_int(
                os.getenv("LILBOT_FILE_CHAR_LIMIT"),
                6000,
            ),
            directory_entry_limit=_coerce_positive_int(
                os.getenv("LILBOT_DIRECTORY_ENTRY_LIMIT"),
                200,
            ),
            repo_file_limit=_coerce_positive_int(
                os.getenv("LILBOT_REPO_FILE_LIMIT"),
                400,
            ),
            repo_reference_limit=_coerce_positive_int(
                os.getenv("LILBOT_REPO_REFERENCE_LIMIT"),
                40,
            ),
            log_line_limit=_coerce_positive_int(
                os.getenv("LILBOT_LOG_LINE_LIMIT"),
                400,
            ),
            verbose_agent=verbose_agent,
        )

    def resolve_workspace_path(self, path: str | Path, *, must_exist: bool = False) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate
        resolved = candidate.resolve(strict=False)

        if resolved != self.workspace_root and self.workspace_root not in resolved.parents:
            raise ValueError(
                f"{path!s} is outside the workspace root {self.workspace_root}"
            )
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
