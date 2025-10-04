from __future__ import annotations

from pathlib import Path

from app.config import TranscriptionSettings
from dataclasses import dataclass
from typing import Iterator, Tuple

from app.diarization import SpeakerTurn
from app.transcription import Segment, TranscriptionOptions, TranscriptionService


@dataclass
class FakeInfo:
    duration: float
    language: str | None


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[Tuple[str, dict[str, object]]] = []

    class _Segment:
        def __init__(self, start: float, end: float, text: str) -> None:
            self.start = start
            self.end = end
            self.text = text

    def transcribe(self, audio_path: str, **kwargs: object) -> Tuple[Iterator[object], FakeInfo]:
        self.calls.append((audio_path, kwargs))
        segments = [
            self._Segment(0.0, 1.5, "Hello"),
            self._Segment(1.5, 2.7, "world"),
        ]
        info = FakeInfo(duration=2.7, language="en")
        return iter(segments), info


def test_transcription_service_loads_model_once(tmp_path: Path) -> None:
    fake_model = FakeModel()
    loader_calls: list[str] = []

    def loader(settings_: TranscriptionSettings) -> FakeModel:
        loader_calls.append(settings_.model_name)
        return fake_model

    settings = TranscriptionSettings(model_name="tiny", temperature=0.0)
    service = TranscriptionService(settings=settings, model_factory=loader)

    first = service.transcribe(tmp_path / "first.wav")
    second = service.transcribe(tmp_path / "second.wav", options=TranscriptionOptions(language="en"))

    assert len(loader_calls) == 1
    assert fake_model.calls[0][0].endswith("first.wav")
    assert fake_model.calls[1][0].endswith("second.wav")
    assert first.text == "Hello world"
    assert first.language == "en"
    assert first.duration == 2.7
    assert len(first.segments) == 2
    assert first.segments[0] == Segment(index=0, start=0.0, end=1.5, text="Hello", speaker=None)
    assert second.language == "en"


def test_transcription_service_assigns_speakers(tmp_path: Path) -> None:
    fake_model = FakeModel()

    def loader(settings_: TranscriptionSettings) -> FakeModel:
        return fake_model

    class FakeDiarizer:
        def __init__(self, settings: TranscriptionSettings) -> None:
            self.calls: list[str] = []

        def diarize(self, audio_path: str | Path) -> list[SpeakerTurn]:
            self.calls.append(str(audio_path))
            return [
                SpeakerTurn(speaker="SPEAKER_00", start=0.0, end=1.6),
                SpeakerTurn(speaker="SPEAKER_01", start=1.6, end=3.0),
            ]

    settings = TranscriptionSettings(diarization_enabled=True, diarization_min_overlap=0.0)

    diarization_factory_calls: list[str] = []
    diarizer_instances: list[FakeDiarizer] = []

    def diarization_factory(settings_: TranscriptionSettings) -> FakeDiarizer:
        diarization_factory_calls.append(settings_.model_name)
        instance = FakeDiarizer(settings_)
        diarizer_instances.append(instance)
        return instance

    service = TranscriptionService(
        settings=settings,
        model_factory=loader,
        diarization_factory=diarization_factory,
    )

    result = service.transcribe(tmp_path / "example.wav")

    assert diarization_factory_calls == [settings.model_name]
    assert [segment.speaker for segment in result.segments] == ["SPEAKER_00", "SPEAKER_01"]
    assert diarizer_instances[0].calls[0].endswith("example.wav")
