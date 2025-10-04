from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

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
    segments: List[ClassifiedSegment]
    audio_bytes: bytes


class AudioModerationPipeline:
    """Run transcription/diarization plus hate-speech classification."""

    def __init__(
        self,
        *,
        transcription_service: Optional[TranscriptionService] = None,
        classifier: Optional[HateSpeechClassifier] = None,
        default_asr_confidence: float = 0.85,
    ) -> None:
        self._transcription_service = transcription_service or TranscriptionService(get_settings())
        self._classifier = classifier or HateSpeechClassifier()
        self._default_asr_confidence = default_asr_confidence

    def run(
        self,
        audio_path: str | Path,
        *,
        options: Optional[TranscriptionOptions] = None,
    ) -> ModerationResult:
        """Process *audio_path* and return the annotated transcript and audio payload."""

        resolved_audio = Path(audio_path).expanduser().resolve()
        transcription_result = self._transcription_service.transcribe(resolved_audio, options=options)

        classified_segments: List[ClassifiedSegment] = []

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

        audio_bytes = resolved_audio.read_bytes()

        return ModerationResult(
            transcript=transcription_result.text,
            language=transcription_result.language,
            duration=transcription_result.duration,
            segments=classified_segments,
            audio_bytes=audio_bytes,
        )

    def _classify_segment(self, segment: Segment) -> ClassificationOutput:
        input_payload = ClassificationInput(
            segment_text=segment.text,
            segment_start=segment.start,
            segment_end=segment.end,
            asr_mean_confidence=self._default_asr_confidence,
        )
        return self._classifier.classify(input_payload)