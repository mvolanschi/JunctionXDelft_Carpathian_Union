#!/usr/bin/env python3
"""Smoke test: run the moderation pipeline on a real audio clip.

This script invokes the full transcription + classification pipeline against
`backend/sample_audio_rec.m4a` and writes the expected JSON payload to
`backend/sample_moderation_response.txt`.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

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

from app.moderation_pipeline import AudioModerationPipeline, ModerationResult


def main() -> int:
    repo_root = Path(__file__).resolve().parents[3]
    backend_root = repo_root
    input_audio = backend_root / "shmarnalysis.m4a"

    if not input_audio.exists():
        print(
            f"Expected audio file at {input_audio}. Please place 'shmarnalysis.m4a' in the backend directory.",
            file=sys.stderr,
        )
        return 1

    try:
        pipeline = AudioModerationPipeline()
    except Exception:
        print(
            "Failed to initialize the moderation pipeline. Ensure transcription models, GROQ_API_KEY, and dependencies are configured.",
            file=sys.stderr,
        )
        raise

    result: ModerationResult = pipeline.run(input_audio)

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

    audio_suffix = input_audio.suffix.lstrip(".") or "wav"
    payload["audio"] = {
        "filename": input_audio.name,
        "content_type": f"audio/{audio_suffix}",
        "data_base64": base64.b64encode(result.audio_bytes).decode("ascii"),
    }

    out_file = backend_root / "sample_moderation_response.txt"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Wrote example API response to: {out_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
