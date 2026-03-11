from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "lilbot"
FALLBACK_APP_DIRNAME = ".lilbot"
MODEL_ENV_NAMES = ("LILBOT_MODEL_PATH", "TEXT_MODEL_PATH")
MODEL_WEIGHT_SUFFIXES = (".safetensors", ".bin")
MODEL_WEIGHT_INDEXES = ("model.safetensors.index.json", "pytorch_model.bin.index.json")
TOKENIZER_FILES = ("tokenizer.json", "tokenizer.model", "tokenizer_config.json")


def app_data_dir() -> Path:
    override = os.getenv("LILBOT_HOME")
    if override:
        return Path(override).expanduser().resolve()

    candidate = _platform_app_data_dir()
    if _can_prepare_directory(candidate):
        return candidate.resolve()
    return (Path.cwd() / FALLBACK_APP_DIRNAME).resolve()


def _platform_app_data_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / APP_NAME


def _can_prepare_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    return path.is_dir()


def default_memory_db_path() -> Path:
    return app_data_dir() / "memory" / "memory_store.db"


def default_legacy_memory_json_path() -> Path:
    return app_data_dir() / "memory" / "memory_store.json"


def default_session_dir() -> Path:
    return app_data_dir() / "sessions"


def default_model_dir() -> Path:
    return app_data_dir() / "models" / "default"


def configured_model_path() -> str | None:
    for env_name in MODEL_ENV_NAMES:
        raw_value = os.getenv(env_name)
        if raw_value and raw_value.strip():
            return str(Path(raw_value).expanduser())
    return None


def is_complete_model_path(path: str | Path | None) -> bool:
    if path is None:
        return False

    candidate = Path(path).expanduser()
    if not candidate.exists() or not candidate.is_dir():
        return False

    if not (candidate / "config.json").is_file():
        return False

    has_tokenizer = any((candidate / filename).is_file() for filename in TOKENIZER_FILES)
    if not has_tokenizer:
        return False

    if any((candidate / filename).is_file() for filename in MODEL_WEIGHT_INDEXES):
        return True

    for suffix in MODEL_WEIGHT_SUFFIXES:
        if any(candidate.glob(f"*{suffix}")):
            return True
    return False


def resolve_default_model_path() -> str | None:
    explicit_path = configured_model_path()
    if explicit_path is not None:
        return explicit_path

    for candidate in _model_search_candidates():
        if is_complete_model_path(candidate):
            return str(candidate.resolve())
    return None


def _model_search_candidates() -> tuple[Path, ...]:
    package_root = Path(__file__).resolve().parent
    return (
        default_model_dir(),
        package_root / "models" / "falcon3_10b_instruct",
        Path.cwd() / "lilbot" / "models" / "falcon3_10b_instruct",
    )


def ensure_app_directories() -> list[Path]:
    directories = [
        app_data_dir(),
        default_session_dir(),
        default_model_dir(),
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return directories
