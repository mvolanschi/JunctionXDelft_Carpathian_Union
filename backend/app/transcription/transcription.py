from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

from .config import TranscriptionSettings
from .diarization import DiarizationService, assign_speakers_to_segments

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Segment:
    index: int
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    language: Optional[str]
    segments: List[Segment]
    duration: Optional[float]
    model_name: str


@dataclass(slots=True)
class TranscriptionOptions:
    language: Optional[str] = None
    translate: bool = False
    temperature: Optional[float] = None
    initial_prompt: Optional[str] = None
    beam_size: Optional[int] = None
    best_of: Optional[int] = None


def _load_whisper_model(settings: TranscriptionSettings) -> Any:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only when dependency missing
        raise RuntimeError(
            "The 'faster-whisper' package is required for transcription. Install it via 'pip install faster-whisper'."
        ) from exc

    kwargs: dict[str, Any] = {}
    if settings.device:
        kwargs["device"] = settings.device
    if settings.compute_type:
        kwargs["compute_type"] = settings.compute_type

    return WhisperModel(settings.model_name, **kwargs)


class TranscriptionService:
    """Thin wrapper around Whisper that adds lazy-loading and structured results."""

    def __init__(
        self,
        settings: TranscriptionSettings,
        model_factory: Callable[[TranscriptionSettings], Any] | None = None,
        diarization_factory: Callable[[TranscriptionSettings], DiarizationService] | None = None,
    ) -> None:
        self._settings = settings
        self._model_factory = model_factory or _load_whisper_model
        self._model: Any | None = None
        self._lock = threading.Lock()
        self._diarization_factory = diarization_factory or (lambda cfg: DiarizationService(cfg))
        self._diarization_service: DiarizationService | None = None
        self._diarization_lock = threading.Lock()

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model

        with self._lock:
            if self._model is None:
                logger.info("Loading Whisper model '%s'", self._settings.model_name)
                self._model = self._model_factory(self._settings)
        return self._model

    def _ensure_diarization_service(self) -> DiarizationService | None:
        if not self._settings.diarization_enabled:
            return None

        if self._diarization_service is not None:
            return self._diarization_service

        with self._diarization_lock:
            if self._diarization_service is None:
                try:
                    self._diarization_service = self._diarization_factory(self._settings)
                except RuntimeError as exc:  # pragma: no cover - depends on optional dependency
                    logger.warning("Unable to initialize diarization: %s", exc)
                    self._settings.diarization_enabled = False
                    return None

        return self._diarization_service

    def transcribe(
        self,
        audio_path: str | Path,
        *,
        options: TranscriptionOptions | None = None,
    ) -> TranscriptionResult:
        opts = options or TranscriptionOptions()
        kwargs: dict[str, Any] = {
            "task": "translate" if opts.translate else "transcribe",
            "temperature": opts.temperature if opts.temperature is not None else self._settings.temperature,
            "beam_size": opts.beam_size if opts.beam_size is not None else self._settings.beam_size,
            "best_of": opts.best_of if opts.best_of is not None else self._settings.best_of,
        }

        language = opts.language or self._settings.default_language
        if language:
            kwargs["language"] = language

        initial_prompt = opts.initial_prompt or self._settings.initial_prompt
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt

        model = self._ensure_model()
        logger.debug("Starting Whisper transcription with options: %s", kwargs)
        segments_iter, info = model.transcribe(
            str(audio_path),
            **kwargs,
        )

        segments: List[Segment] = []
        for idx, segment in enumerate(segments_iter):
            segments.append(
                Segment(
                    index=idx,
                    start=float(segment.start),
                    end=float(segment.end),
                    text=str(segment.text).strip(),
                )
            )

        diarizer = self._ensure_diarization_service()
        if diarizer is not None:
            try:
                speaker_turns = diarizer.diarize(audio_path)
            except Exception as exc:  # pragma: no cover - depends on external dependency
                logger.warning("Diarization failed: %s", exc, exc_info=True)
            else:
                assign_speakers_to_segments(
                    segments,
                    speaker_turns,
                    min_overlap_seconds=self._settings.diarization_min_overlap,
                )

        duration = getattr(info, "duration", None)
        if duration is None and segments:
            duration = segments[-1].end

        detected_language = getattr(info, "language", None)
        if not detected_language:
            detected_language = kwargs.get("language")

        full_text_parts = [part for part in (segment.text.strip() for segment in segments) if part]

        return TranscriptionResult(
            text=" ".join(full_text_parts).strip(),
            language=detected_language,
            segments=segments,
            duration=duration,
            model_name=self._settings.model_name,
        )

    async def transcribe_async(
        self,
        audio_path: str | Path,
        *,
        options: TranscriptionOptions | None = None,
    ) -> TranscriptionResult:
        return await asyncio.to_thread(self.transcribe, audio_path, options=options)
