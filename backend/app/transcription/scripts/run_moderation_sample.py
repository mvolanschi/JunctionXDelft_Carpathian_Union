#!/usr/bin/env python3
"""Fixed version of run_moderation_sample.py that forces CPU usage and handles errors.

This script invokes the full transcription + classification pipeline against
`backend/data/shmarnalysis.m4a` and writes the expected JSON payload to
`backend/sample_moderation_response.txt`.
"""

from __future__ import annotations

import base64
import json
import os
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

# Force CPU usage to avoid CUDA issues
os.environ["WHISPER_DEVICE"] = "cpu"
os.environ["WHISPER_COMPUTE_TYPE"] = "int8"
os.environ["DIARIZATION_ENABLED"] = "false"  # Disable diarization to avoid pyannote issues

from app.moderation_pipeline import AudioModerationPipeline, ModerationResult


def main() -> int:
    print("🚀 Running Moderation Sample (CPU mode)")
    print("=" * 50)
    
    # Use the correct path to the backend directory
    backend_root = BACKEND_ROOT
    input_audio = backend_root / "data/shmarnalysis.m4a"

    if not input_audio.exists():
        print(f"❌ Expected audio file at {input_audio}")
        print("Please place 'shmarnalysis.m4a' in the backend/data directory.")
        return 1

    print(f"🎤 Input audio: {input_audio}")
    print(f"   File size: {input_audio.stat().st_size:,} bytes")

    try:
        print("⚙️ Initializing moderation pipeline (CPU mode)...")
        pipeline = AudioModerationPipeline()
        print("✅ Pipeline initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize the moderation pipeline: {e}")
        print("Ensure transcription models and dependencies are configured.")
        import traceback
        traceback.print_exc()
        return 1

    try:
        print("🔄 Running moderation pipeline...")
        result: ModerationResult = pipeline.run(input_audio)
        print("✅ Pipeline completed successfully")
        
        print(f"📊 Results:")
        print(f"   Transcript length: {len(result.transcript)} characters") 
        print(f"   Language: {result.language}")
        print(f"   Duration: {result.duration:.1f}s")
        print(f"   Segments: {len(result.segments)}")
        
    except Exception as e:
        print(f"❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    try:
        print("📝 Building API payload...")
        
        # Build payload similar to API
        segments_payload = []
        flagged_count = 0
        
        for seg in result.segments:
            classification_data = {
                "label": seg.classification.label,
                "rationale": seg.classification.rationale,
                "spans": [
                    {"quote": s.quote, "char_start": s.char_start, "char_end": s.char_end}
                    for s in getattr(seg.classification, "spans", [])
                ],
                "safety": getattr(seg.classification, "safety", {}),
            }
            
            if seg.classification.label != "NONE":
                flagged_count += 1
            
            segments_payload.append({
                "index": seg.index,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "speaker": seg.speaker,
                "classification": classification_data,
            })

        print(f"   🚨 Flagged segments: {flagged_count}")

        payload = {
            "transcript": result.transcript,
            "language": result.language,
            "duration": result.duration,
            "segments": segments_payload,
        }

        # Add audio data
        audio_suffix = input_audio.suffix.lstrip(".") or "wav"
        payload["audio"] = {
            "filename": input_audio.name,
            "content_type": f"audio/{audio_suffix}",
            "data_base64": base64.b64encode(result.audio_bytes).decode("ascii"),
        }

        # Write output
        out_file = backend_root / "sample_moderation_response.txt"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print(f"✅ Wrote API response to: {out_file}")
        print(f"   Output size: {out_file.stat().st_size:,} bytes")
        
        # Show sample of flagged content
        if flagged_count > 0:
            print(f"\n🎯 Sample of flagged content:")
            flagged_segments = [s for s in result.segments if s.classification.label != "NONE"]
            for i, seg in enumerate(flagged_segments[:3], 1):
                print(f"   {i}. [{seg.classification.label}] \"{seg.text[:60]}...\"")

        return 0
        
    except Exception as e:
        print(f"❌ Failed to build/write output: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    print(f"\n🏁 Script completed with exit code: {exit_code}")
    raise SystemExit(exit_code)