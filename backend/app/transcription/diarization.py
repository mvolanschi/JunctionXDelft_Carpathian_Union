from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Optional

from .config import TranscriptionSettings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SpeakerTurn:
    speaker: str
    start: float
    end: float


def _load_pyannote_pipeline(settings: TranscriptionSettings) -> Any:
    try:
        from pyannote.audio import Pipeline  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only when dependency missing
        raise RuntimeError(
            "The 'pyannote.audio' package (and its Torch dependencies) are required for diarization. "
            "Install them via 'pip install pyannote.audio torch torchaudio'."
        ) from exc

    kwargs: dict[str, Any] = {}
    if settings.diarization_auth_token:
        kwargs["use_auth_token"] = settings.diarization_auth_token

    model_id = settings.diarization_model_id
    logger.info("Loading diarization pipeline '%s'", model_id)
    return Pipeline.from_pretrained(model_id, **kwargs)


class DiarizationService:
    """Thin wrapper around an underlying diarization pipeline with lazy loading."""

    def __init__(
        self,
        settings: TranscriptionSettings,
        pipeline_factory: Callable[[TranscriptionSettings], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._pipeline_factory = pipeline_factory or _load_pyannote_pipeline
        self._pipeline: Any | None = None
        self._lock = threading.Lock()

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        with self._lock:
            if self._pipeline is None:
                self._pipeline = self._pipeline_factory(self._settings)
        return self._pipeline

    def diarize(self, audio_path: str | Path) -> List[SpeakerTurn]:
        pipeline = self._ensure_pipeline()

        resolved_path: Path | None = None
        cleanup_path: Path | None = None
        try:
            resolved_path, cleanup_path = _prepare_audio_for_diarization(Path(audio_path))
            diarization_result = pipeline(str(resolved_path))
        finally:
            if cleanup_path is not None and cleanup_path.exists():
                try:
                    cleanup_path.unlink()
                except OSError:
                    logger.debug("Unable to remove temporary file '%s'", cleanup_path, exc_info=True)

        turns: List[SpeakerTurn] = []
        for segment, _, speaker in diarization_result.itertracks(yield_label=True):
            turns.append(
                SpeakerTurn(
                    speaker=str(speaker),
                    start=float(segment.start),
                    end=float(segment.end),
                )
            )

        turns.sort(key=lambda item: (item.start, item.end))
        return turns


def assign_speakers_to_segments(
    segments: List["Segment"],
    speaker_turns: Iterable[SpeakerTurn],
    *,
    min_overlap_seconds: float = 0.0,
) -> None:
    """Annotate segments in-place with the speaker that overlaps the most."""

    turns = list(speaker_turns)
    if not turns:
        return

    def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    for segment in segments:
        best_label: Optional[str] = None
        best_overlap = 0.0

        for turn in turns:
            overlap = _overlap(segment.start, segment.end, turn.start, turn.end)
            if overlap > best_overlap:
                best_overlap = overlap
                best_label = turn.speaker

        if best_label is not None and best_overlap >= min_overlap_seconds:
            segment.speaker = best_label
        else:
            segment.speaker = None


if TYPE_CHECKING:  # pragma: no cover - static typing only
    from .transcription import Segment


def _prepare_audio_for_diarization(audio_path: Path) -> tuple[Path, Path | None]:
    """Return an audio path suitable for pyannote and an optional temporary file to clean up."""

    if audio_path.suffix.lower() in {".wav", ".flac", ".ogg", ".opus"}:
        return audio_path, None

    fd, temp_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    temp_file = Path(temp_path)

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(audio_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        temp_file.as_posix(),
    ]

    try:
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:  # pragma: no cover - depends on system setup
        raise RuntimeError(
            "ffmpeg is required for diarization but was not found on the PATH. Install ffmpeg and try again."
        ) from exc
    except subprocess.CalledProcessError as exc:  # pragma: no cover - depends on external tool
        raise RuntimeError(
            f"ffmpeg failed to convert '{audio_path}' for diarization: {exc.stderr.decode(errors='ignore')}"
        ) from exc

    return temp_file, temp_file
