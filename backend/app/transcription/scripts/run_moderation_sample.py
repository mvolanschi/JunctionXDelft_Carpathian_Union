#!/usr/bin/env python3
"""Smoke test: run the moderation pipeline with mocked segments but the real classifier.

This script creates a short silent WAV matching the timeline of the mock segments,
invokes the actual Groq-backed hate-speech classifier, and writes the
expected JSON payload to `backend/sample_moderation_response.txt`.
"""

from __future__ import annotations

import base64
import json
import sys
import wave
from pathlib import Path
from typing import List

# Make sure 'backend' is on sys.path so 'app' is importable when running this script
CURRENT_FILE = Path(__file__).resolve()

def _find_backend_root() -> Path:
    for p in CURRENT_FILE.parents:
        if p.name == "backend":
            return p
    # Fallback: assume layout .../backend/app/transcription/scripts
    return CURRENT_FILE.parents[4]

BACKEND_ROOT = _find_backend_root()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.transcription.transcription import Segment, TranscriptionResult
from app.moderation_pipeline import AudioModerationPipeline, ModerationResult
from app.classification_model.hate_speech_classifier import HateSpeechClassifier


class StubTranscriptionService:
    def __init__(self, segments: List[Segment], *, duration: float = 0.0) -> None:
        self._result = TranscriptionResult(
            text=" ".join(s.text for s in segments),
            language="en",
            segments=segments,
            duration=duration or (segments[-1].end if segments else 0.0),
            model_name="stub-model",
        )

    def transcribe(self, audio_path, options=None):
        return self._result


# We'll use the real classifier for the smoke test. The script will fail early with
# a helpful message if the classifier cannot be instantiated (for example when
# the GROQ_API_KEY is not set).


def _write_silent_wav(path: Path, duration_s: float, sample_rate: int = 16000) -> None:
    total_frames = int(duration_s * sample_rate)
    silence_frame = (0).to_bytes(2, byteorder="little", signed=True)

    with wave.open(path.as_posix(), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(silence_frame * total_frames)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root

    # Create mock segments: a few normal segments and two flagged ones
    segments = [
        Segment(index=0, start=0.0, end=1.0, text="Hello everyone, welcome.", speaker="S1"),
        Segment(index=1, start=1.0, end=2.0, text="This is an extremist call to arms.", speaker="S2"),
        Segment(index=2, start=2.0, end=3.0, text="I like this project.", speaker="S1"),
        Segment(index=3, start=3.0, end=4.0, text="They are a disease and must be removed.", speaker="S2"),
        Segment(index=4, start=4.0, end=5.0, text="Thanks and goodbye.", speaker="S1"),
    ]

    # Write a small silent WAV that matches the duration
    input_wav = backend_root / "moderation_input.wav"
    _write_silent_wav(input_wav, duration_s=5.0)

    # Stub transcription service; classification is performed with the real Groq model.
    stub_transcription = StubTranscriptionService(segments, duration=5.0)

    try:
        real_classifier = HateSpeechClassifier()
    except Exception:
        print(
            "Failed to initialize the real HateSpeechClassifier. Ensure GROQ_API_KEY is set (export or backend/.env) and dependencies are installed.",
            file=sys.stderr,
        )
        raise

    pipeline = AudioModerationPipeline(
        transcription_service=stub_transcription,
        classifier=real_classifier,
    )

    result: ModerationResult = pipeline.run(input_wav)

    # Build payload similar to API
    segments_payload = []
    for seg in result.segments:
        segments_payload.append(
            {
                "index": seg.index,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "speaker": seg.speaker,
                "classification": {
                    "label": seg.classification.label,
                    "rationale": seg.classification.rationale,
                    "spans": [
                        {"quote": s.quote, "char_start": s.char_start, "char_end": s.char_end}
                        for s in getattr(seg.classification, "spans", [])
                    ],
                    "safety": getattr(seg.classification, "safety", {}),
                },
            }
        )

    payload = {
        "transcript": result.transcript,
        "language": result.language,
        "duration": result.duration,
        "segments": segments_payload,
    }

    audio_suffix = input_wav.suffix.lstrip(".") or "wav"
    payload["audio"] = {
        "filename": input_wav.name,
        "content_type": f"audio/{audio_suffix}",
        "data_base64": base64.b64encode(result.audio_bytes).decode("ascii"),
    }

    out_file = backend_root / "sample_moderation_response.txt"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote example API response to: {out_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
