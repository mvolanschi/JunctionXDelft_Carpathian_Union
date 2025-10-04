from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Load environment variables from a local .env file if present. This runs once at import time.
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def _get_bool(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


@dataclass(slots=True)
class TranscriptionSettings:
    """Configuration values for the Whisper transcription pipeline."""

    model_name: str = os.getenv("WHISPER_MODEL_NAME", "base")
    default_language: Optional[str] = os.getenv("WHISPER_DEFAULT_LANGUAGE") or None
    temperature: float = float(os.getenv("WHISPER_TEMPERATURE", "0.0"))
    initial_prompt: Optional[str] = os.getenv("WHISPER_INITIAL_PROMPT") or None
    beam_size: int = int(os.getenv("WHISPER_BEAM_SIZE", "5"))
    best_of: int = int(os.getenv("WHISPER_BEST_OF", "5"))
    device: Optional[str] = os.getenv("WHISPER_DEVICE") or None
    compute_type: Optional[str] = os.getenv("WHISPER_COMPUTE_TYPE") or None
    diarization_enabled: bool = _get_bool("DIARIZATION_ENABLED", "false")
    diarization_model_id: str = os.getenv(
        "DIARIZATION_MODEL_ID", "pyannote/speaker-diarization-3.1"
    )
    diarization_auth_token: Optional[str] = (
        os.getenv("DIARIZATION_AUTH_TOKEN")
        or os.getenv("HUGGINGFACE_TOKEN")
        or os.getenv("HF_HOME_TOKEN")
        or None
    )
    diarization_min_overlap: float = float(os.getenv("DIARIZATION_MIN_OVERLAP", "0.15"))


def get_settings() -> TranscriptionSettings:
    """Return shared application settings.

    This indirection exists so tests can monkeypatch the settings factory if needed.
    """

    return TranscriptionSettings()
