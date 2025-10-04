#!/usr/bin/env python
"""Minimal hard-coded transcription script for quick local smoke tests."""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings  # noqa: E402
from app.transcription import TranscriptionService  # noqa: E402

# 👉 Update these paths to point at a real .m4a input on your machine.
AUDIO_PATH = PROJECT_ROOT / "harvard.wav"
OUTPUT_PATH = PROJECT_ROOT / "sample_audio_transcript.txt"


def main() -> int:
    if not AUDIO_PATH.exists():
        print(f"❌ Expected audio file at {AUDIO_PATH}. Update AUDIO_PATH before running.")
        return 1

    settings = get_settings()
    service = TranscriptionService(settings)

    print(f"🎧 Transcribing {AUDIO_PATH} with model '{settings.model_name}'...")
    result = service.transcribe(AUDIO_PATH)

    lines: list[str] = []
    if result.text.strip():
        lines.append(result.text.strip())

    if result.segments:
        lines.append("")
        lines.append("Segments:")
        for segment in result.segments:
            speaker = segment.speaker or "SPEAKER_UNKNOWN"
            lines.append(f"[{segment.start:0.2f}s-{segment.end:0.2f}s] {speaker}: {segment.text}")

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✅ Transcript saved to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
