from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Optional

import numpy as np
import torch

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

    model_id = settings.diarization_model_id
    logger.info("Loading diarization pipeline '%s'", model_id)
    token = settings.diarization_auth_token

    if not token:
        return Pipeline.from_pretrained(model_id)

    try:
        return Pipeline.from_pretrained(model_id, token=token)
    except TypeError as exc:
        # pyannote < 3.2 expects `use_auth_token` instead of the new `token` keyword.
        if "unexpected keyword argument 'token'" not in str(exc):
            raise
        logger.info(
            "Diarization pipeline rejected 'token' argument; retrying with legacy 'use_auth_token'"
        )
        return Pipeline.from_pretrained(model_id, use_auth_token=token)


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
            waveform_input = _load_waveform_for_pyannote(resolved_path)
            diarization_result = pipeline(waveform_input)
        finally:
            if cleanup_path is not None and cleanup_path.exists():
                try:
                    cleanup_path.unlink()
                except OSError:
                    logger.debug("Unable to remove temporary file '%s'", cleanup_path, exc_info=True)

        turns: List[SpeakerTurn] = []
        annotation = getattr(diarization_result, "speaker_diarization", diarization_result)

        try:
            track_iter = annotation.itertracks(yield_label=True)
        except AttributeError:
            try:
                track_iter = annotation.itertracks()
            except AttributeError as exc:  # pragma: no cover - incompatible pyannote version
                raise RuntimeError(
                    "Unexpected diarization output without 'itertracks'."
                ) from exc
            else:
                track_iter = ((segment, None, speaker) for segment, speaker in track_iter)

        for segment, _, speaker in track_iter:
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
        "-sample_fmt",
        "s16",
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


def _load_waveform_for_pyannote(audio_path: Path) -> dict[str, Any]:
    """Return a pyannote-compatible mapping that carries waveform data."""

    with wave.open(str(audio_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        num_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        num_frames = wav_file.getnframes()
        audio_bytes = wav_file.readframes(num_frames)

    if sample_width == 2:
        dtype = np.int16
        scale = 32768.0
    elif sample_width == 4:
        dtype = np.int32
        scale = 2147483648.0
    else:
        raise RuntimeError(
            f"Unsupported PCM sample width {sample_width * 8} bits for '{audio_path.name}'."
        )

    waveform = np.frombuffer(audio_bytes, dtype=dtype)
    if num_channels > 1:
        waveform = waveform.reshape(-1, num_channels).T
        waveform = waveform.mean(axis=0, keepdims=True)
    else:
        waveform = waveform.reshape(1, -1)

    tensor = torch.from_numpy(waveform.astype(np.float32) / scale)

    return {
        "waveform": tensor,
        "sample_rate": sample_rate,
        "uri": audio_path.stem,
    }
