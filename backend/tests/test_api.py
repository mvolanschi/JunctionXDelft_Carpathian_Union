from __future__ import annotations

import io
from typing import Optional, Tuple

from app.main import create_app
from app.transcription import Segment, TranscriptionOptions, TranscriptionResult


class DummyTranscriptionService:
    def __init__(self) -> None:
        self.calls: list[Tuple[str, Optional[TranscriptionOptions]]] = []

    def transcribe(self, audio_path: str, *, options: Optional[TranscriptionOptions] = None) -> TranscriptionResult:
        self.calls.append((audio_path, options))
        return TranscriptionResult(
            text="hello world",
            language="en",
            duration=1.2,
            model_name="dummy",
            segments=[Segment(index=0, start=0.0, end=1.2, text="hello world")],
        )


def test_transcriptions_endpoint_returns_transcript(tmp_path) -> None:
    service = DummyTranscriptionService()
    app = create_app(service=service)

    with app.test_client() as client:
        data = {
            "file": (io.BytesIO(b"sample-bytes"), "meeting.wav"),
            "language": "en",
            "translate": "false",
        }
        resp = client.post("/transcriptions", data=data, content_type="multipart/form-data")

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["transcript"] == "hello world"
    assert payload["metadata"]["language"] == "en"
    assert payload["metadata"]["model"] == "dummy"
    assert payload["segments"][0]["start"] == 0.0
    assert service.calls, "Service should receive transcription workload"


def test_transcriptions_endpoint_blocks_invalid_extension() -> None:
    app = create_app(service=DummyTranscriptionService())

    with app.test_client() as client:
        data = {
            "file": (io.BytesIO(b"fake"), "clip.txt"),
        }
        resp = client.post("/transcriptions", data=data, content_type="multipart/form-data")

    assert resp.status_code == 415
    assert resp.get_json()["error"].startswith("Unsupported audio format")
