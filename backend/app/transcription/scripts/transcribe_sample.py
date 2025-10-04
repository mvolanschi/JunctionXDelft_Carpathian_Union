#!/usr/bin/env python
"""Minimal hard-coded transcription script for quick local smoke tests."""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()


def _discover_backend_root() -> Path:
    for parent in CURRENT_FILE.parents:
        if (parent / "app").is_dir():
            return parent
    # Fallback: assume standard layout .../backend/app/transcription/scripts
    return CURRENT_FILE.parents[2]


BACKEND_ROOT = _discover_backend_root()
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.transcription import TranscriptionService, get_settings  # noqa: E402

# 👉 Update these paths to point at a real .m4a input on your machine.
AUDIO_PATH = BACKEND_ROOT / "harvard.wav"
OUTPUT_PATH = BACKEND_ROOT / "sample_audio_transcript.txt"


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
