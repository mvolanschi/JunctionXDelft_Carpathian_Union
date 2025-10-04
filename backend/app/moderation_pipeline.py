from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from app.transcription import (
    Segment,
    TranscriptionOptions,
    TranscriptionService,
    get_settings,
)

from app.classification_model.hate_speech_classifier import (
    ClassificationInput,
    ClassificationOutput,
    EvidenceSpan,
    HateSpeechClassifier,
)

try:  # pragma: no cover - optional dependency resolution
    from pydub import AudioSegment
except ImportError:  # pragma: no cover - handled at runtime
    AudioSegment = None

logger = logging.getLogger(__name__)

FlagInterval = Tuple[float, float]


@dataclass(slots=True)
class ClassifiedSegment:
    """Single transcript segment enriched with moderation metadata."""

    index: int
    start: float
    end: float
    text: str
    speaker: Optional[str]
    classification: ClassificationOutput

    @property
    def label(self) -> str:
        return self.classification.label

    @property
    def rationale(self) -> str:
        return self.classification.rationale

    @property
    def spans(self) -> List[EvidenceSpan]:
        return self.classification.spans


@dataclass(slots=True)
class ModerationResult:
    """Aggregate outcome of the moderation pipeline."""

    transcript: str
    language: Optional[str]
    duration: Optional[float]
    model: str
    segments: List[ClassifiedSegment]
    sanitized_audio_path: Optional[Path]
    removed_intervals: List[FlagInterval] = field(default_factory=list)

    @property
    def has_redacted_audio(self) -> bool:
        return bool(self.sanitized_audio_path and self.removed_intervals)


class AudioModerationPipeline:
    """Run transcription/diarization plus hate-speech classification and audio redaction."""

    DEFAULT_REMOVAL_LABELS = frozenset({"HATE", "EXTREMIST", "BOTH"})

    def __init__(
        self,
        *,
        transcription_service: Optional[TranscriptionService] = None,
        classifier: Optional[HateSpeechClassifier] = None,
        removal_labels: Optional[Iterable[str]] = None,
        default_asr_confidence: float = 0.85,
    ) -> None:
        self._transcription_service = transcription_service or TranscriptionService(get_settings())
        self._classifier = classifier or HateSpeechClassifier()
        self._removal_labels = frozenset(removal_labels) if removal_labels else self.DEFAULT_REMOVAL_LABELS
        self._default_asr_confidence = default_asr_confidence

    def run(
        self,
        audio_path: str | Path,
        *,
        options: Optional[TranscriptionOptions] = None,
        output_path: Optional[Path] = None,
    ) -> ModerationResult:
        """Process *audio_path* and return the annotated transcript plus optional redacted audio."""

        resolved_audio = Path(audio_path).expanduser().resolve()
        transcription_result = self._transcription_service.transcribe(resolved_audio, options=options)

        classified_segments: List[ClassifiedSegment] = []
        removal_intervals: List[FlagInterval] = []

        for segment in transcription_result.segments:
            classification = self._classify_segment(segment)
            classified_segment = ClassifiedSegment(
                index=segment.index,
                start=segment.start,
                end=segment.end,
                text=segment.text,
                speaker=segment.speaker,
                classification=classification,
            )
            classified_segments.append(classified_segment)

            if classification.label in self._removal_labels:
                removal_intervals.append((segment.start, segment.end))

        sanitized_audio = None
        if removal_intervals:
            sanitized_audio = self._redact_audio(resolved_audio, removal_intervals, output_path=output_path)

        return ModerationResult(
            transcript=transcription_result.text,
            language=transcription_result.language,
            duration=transcription_result.duration,
            model=transcription_result.model_name,
            segments=classified_segments,
            sanitized_audio_path=sanitized_audio,
            removed_intervals=self._merge_intervals(removal_intervals),
        )

    def _classify_segment(self, segment: Segment) -> ClassificationOutput:
        input_payload = ClassificationInput(
            segment_text=segment.text,
            segment_start=segment.start,
            segment_end=segment.end,
            asr_mean_confidence=self._default_asr_confidence,
        )
        return self._classifier.classify(input_payload)

    def _redact_audio(
        self,
        audio_path: Path,
        intervals: Sequence[FlagInterval],
        *,
        output_path: Optional[Path] = None,
    ) -> Path:
        if AudioSegment is None:  # pragma: no cover - optional dependency guard
            raise RuntimeError(
                "Audio redaction requires the 'pydub' package. Install it via 'pip install pydub'."
            )

        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)

        merged = self._merge_intervals(intervals)
        keep_ranges = self._invert_intervals(merged, duration_ms)

        if not keep_ranges:
            logger.info("All segments removed; emitting empty audio track for %s", audio_path.name)
            redacted_audio = AudioSegment.silent(duration=0)
        else:
            redacted_audio = AudioSegment.empty()
            for start_ms, end_ms in keep_ranges:
                redacted_audio += audio[start_ms:end_ms]

        if output_path is None:
            suffix = audio_path.suffix or ".wav"
            fd, temp_name = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            output_path = Path(temp_name)
        else:
            output_path = output_path.expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)

        export_format = output_path.suffix.lstrip(".") or "wav"
        redacted_audio.export(output_path, format=export_format)
        return output_path

    @staticmethod
    def _merge_intervals(intervals: Sequence[FlagInterval]) -> List[FlagInterval]:
        if not intervals:
            return []

        sorted_intervals = sorted((max(0.0, start), max(start, end)) for start, end in intervals)
        merged: List[FlagInterval] = []
        current_start, current_end = sorted_intervals[0]

        for start, end in sorted_intervals[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                merged.append((current_start, current_end))
                current_start, current_end = start, end

        merged.append((current_start, current_end))
        return merged

    @staticmethod
    def _invert_intervals(intervals: Sequence[FlagInterval], duration_ms: int) -> List[Tuple[int, int]]:
        if duration_ms <= 0:
            return []

        keep: List[Tuple[int, int]] = []
        cursor_ms = 0

        for start_sec, end_sec in intervals:
            start_ms = max(0, int(start_sec * 1000))
            end_ms = max(start_ms, int(end_sec * 1000))

            if start_ms > cursor_ms:
                keep.append((cursor_ms, min(start_ms, duration_ms)))

            cursor_ms = max(cursor_ms, min(end_ms, duration_ms))
            if cursor_ms >= duration_ms:
                break

        if cursor_ms < duration_ms:
            keep.append((cursor_ms, duration_ms))

        # Filter any zero-length slices that could occur due to rounding
        return [(start, end) for start, end in keep if end > start]