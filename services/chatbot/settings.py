import json
from dataclasses import asdict, dataclass
from pathlib import Path


SETTINGS_PATH = Path("data/bot_settings.json")

# This module defines the RuntimeSettings dataclass, which encapsulates various configuration 
# options for the chatbot's behavior.

# Basically this is just a script to retrieve the settings for the chatbot, and to save any 
# changes to those settings. It's not a very fun script, and is pretty boring overall.

@dataclass
class RuntimeSettings:
    thread_context_mode: str = "recency"
    thread_context_k: int = 5
    class_context_k: int = 5
    max_context_chars: int = 12000
    response_verbosity: str = "detailed"
    enforce_academic_integrity: bool = True
    discord_debug: bool = False
    debug_context_preview_chars: int = 1200


def _normalize_mode(value: object) -> str:
    mode = str(value or "recency").strip().lower()
    return mode if mode in {"recency", "semantic"} else "recency"


def _normalize_verbosity(value: object) -> str:
    verbosity = str(value or "detailed").strip().lower()
    return verbosity if verbosity in {"concise", "normal", "detailed"} else "detailed"


def _normalize_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, normalized))


def _coerce_settings(data: dict | None) -> RuntimeSettings:
    data = data or {}
    return RuntimeSettings(
        thread_context_mode=_normalize_mode(data.get("thread_context_mode")),
        thread_context_k=_normalize_int(data.get("thread_context_k"), default=5, minimum=0, maximum=25),
        class_context_k=_normalize_int(data.get("class_context_k"), default=5, minimum=0, maximum=25),
        max_context_chars=_normalize_int(data.get("max_context_chars"), default=12000, minimum=1000, maximum=50000),
        response_verbosity=_normalize_verbosity(data.get("response_verbosity")),
        enforce_academic_integrity=bool(data.get("enforce_academic_integrity", True)),
        discord_debug=bool(data.get("discord_debug", False)),
        debug_context_preview_chars=_normalize_int(
            data.get("debug_context_preview_chars"),
            default=1200,
            minimum=200,
            maximum=4000,
        ),
    )


def save_settings(settings: RuntimeSettings) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def load_settings() -> RuntimeSettings:
    if not SETTINGS_PATH.exists():
        settings = RuntimeSettings()
        save_settings(settings)
        return settings

    try:
        raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        settings = RuntimeSettings()
        save_settings(settings)
        return settings

    settings = _coerce_settings(raw)
    save_settings(settings)
    return settings
