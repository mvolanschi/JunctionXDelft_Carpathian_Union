from __future__ import annotations

import wave
from pathlib import Path
from typing import List

from app.moderation_pipeline import AudioModerationPipeline, ModerationResult
from app.transcription.transcription import Segment, TranscriptionResult
from app.classification_model.hate_speech_classifier import ClassificationInput, ClassificationOutput


class StubTranscriptionService:
    def __init__(self, segments: List[Segment], *, duration: float = 0.0) -> None:
        self._result = TranscriptionResult(
            text=" ".join(segment.text for segment in segments),
            language="en",
            segments=segments,
            duration=duration or (segments[-1].end if segments else 0.0),
            model_name="stub",
        )

    def transcribe(self, audio_path: Path, options=None) -> TranscriptionResult:
        return self._result


class StubClassifier:
    def __init__(self, labels: List[str]) -> None:
        self._labels = labels
        self.calls: List[ClassificationInput] = []

    def classify(self, input_data: ClassificationInput) -> ClassificationOutput:
        self.calls.append(input_data)
        label = self._labels[len(self.calls) - 1]
        return ClassificationOutput(
            label=label,
            rationale=f"classified as {label}",
            spans=[],
            safety={"used_asr_confidence_rule": False, "notes": ""},
        )


def _write_silent_wav(path: Path, *, duration_s: float, sample_rate: int = 16000) -> None:
    total_frames = int(duration_s * sample_rate)
    silence_frame = (0).to_bytes(2, byteorder="little", signed=True)

    with wave.open(path.as_posix(), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(silence_frame * total_frames)


def test_pipeline_classifies_and_returns_audio(tmp_path):
    input_path = tmp_path / "input.wav"
    _write_silent_wav(input_path, duration_s=2.0)

    segments = [
        Segment(index=0, start=0.0, end=1.0, text="Hello there", speaker="SPEAKER_00"),
        Segment(index=1, start=1.0, end=2.0, text="Bad words", speaker="SPEAKER_01"),
    ]
    transcription_service = StubTranscriptionService(segments, duration=2.0)
    classifier = StubClassifier(["NONE", "HATE"])

    pipeline = AudioModerationPipeline(
        transcription_service=transcription_service,
        classifier=classifier,
    )

    result = pipeline.run(input_path)

    assert isinstance(result, ModerationResult)
    assert len(result.segments) == 2
    assert result.segments[1].label == "HATE"
    assert result.audio_bytes == input_path.read_bytes()


def test_pipeline_handles_all_clear_segments(tmp_path):
    input_path = tmp_path / "input.wav"
    _write_silent_wav(input_path, duration_s=1.0)

    segments = [
        Segment(index=0, start=0.0, end=1.0, text="All good", speaker=None),
    ]
    transcription_service = StubTranscriptionService(segments, duration=1.0)
    classifier = StubClassifier(["NONE"])

    pipeline = AudioModerationPipeline(
        transcription_service=transcription_service,
        classifier=classifier,
    )

    result = pipeline.run(input_path)

    assert len(result.segments) == 1
    assert result.segments[0].label == "NONE"
    assert result.audio_bytes == input_path.read_bytes()


if __name__ == "__main__":  # pragma: no cover - direct execution helper
    import pytest

    raise SystemExit(pytest.main([__file__]))
