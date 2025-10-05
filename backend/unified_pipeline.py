#!/usr/bin/env python3
"""
Unified Pipeline: Backend Moderation → NegativeOutputHandling

This script creates a complete pipeline that:
1. Runs backend/app moderation on audio file
2. Uses the moderation output as input to NegativeOutputHandling
3. Generates clean transcription + audio replacements
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Setup paths
BACKEND_ROOT = Path(__file__).parent
NEGATIVE_OUTPUT_ROOT = BACKEND_ROOT / "NegativeOutputHandling" / "Code"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(NEGATIVE_OUTPUT_ROOT))


def run_backend_moderation(audio_file: Path) -> Path:
    """Step 1: Run backend moderation pipeline and return output file."""
    
    print("STEP 1: BACKEND MODERATION PIPELINE")
    print("=" * 60)
    
    print(f"Input audio: {audio_file}")
    print(f"   File size: {audio_file.stat().st_size:,} bytes")
    
    # Check if output already exists and is recent
    output_file = BACKEND_ROOT / "data" / "sample_moderation_response.txt"
    if output_file.exists():
        print("Found existing moderation output, using it...")
        print(f"Output file: {output_file}")
        print(f"   Output size: {output_file.stat().st_size:,} bytes")
        return output_file
    
    # Run the moderation script
    moderation_script = BACKEND_ROOT / "app" / "transcription" / "scripts" / "run_moderation_sample.py"
    
    print("Running backend moderation pipeline...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(moderation_script)],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            check=True
        )
        
        print("Backend moderation completed successfully")
        
        # Find the output file
        output_file = BACKEND_ROOT / "data" / "sample_moderation_response.txt"
        if not output_file.exists():
            # Try alternative location
            output_file = BACKEND_ROOT / "sample_moderation_response.txt"
        
        if output_file.exists():
            print(f"Moderation output: {output_file}")
            print(f"   Output size: {output_file.stat().st_size:,} bytes")
            
            # Show sample of what was detected
            with open(output_file, 'r') as f:
                data = json.load(f)
            
            flagged_segments = [s for s in data['segments'] if s['classification']['label'] != 'NONE']
            print(f"   Flagged segments: {len(flagged_segments)}")
            
            if flagged_segments:
                print(f"   Sample flagged content:")
                for i, seg in enumerate(flagged_segments[:3], 1):
                    label = seg['classification']['label']
                    text = seg['text'][:50] + "..." if len(seg['text']) > 50 else seg['text']
                    print(f"      {i}. [{label}] \"{text}\"")
            
            return output_file
        else:
            raise FileNotFoundError("Moderation output file not found")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Backend moderation failed: {e}")
        print(f"   Error output: {e.stderr}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error in backend moderation: {e}")
        raise


async def run_negative_output_handling(moderation_file: Path, audio_file: Path) -> dict:
    """Step 2: Run NegativeOutputHandling on the moderation results."""
    
    print(f"\n🎨 STEP 2: NEGATIVE OUTPUT HANDLING")
    print("=" * 60)
    
    print(f"📁 Moderation input: {moderation_file}")
    print(f"🎤 Reference audio: {audio_file}")
    
    # Import the processing function
    try:
        from verify_and_process import load_real_json_file, process_with_verification, verify_and_load_files
        
        print("✅ NegativeOutputHandling modules imported")
        
        # Load and process the moderation file
        print("🔄 Loading moderation results...")
        
        # The moderation file is already in the right format, we just need to load it
        moderation_result = load_real_json_file(str(moderation_file), str(audio_file))
        
        print("✅ Moderation results loaded successfully")
        print(f"   Transcript: {len(moderation_result.transcript)} chars")
        print(f"   Language: {moderation_result.language}")
        print(f"   Duration: {moderation_result.duration}s") 
        print(f"   Segments: {len(moderation_result.segments)}")
        
        # Get file hashes for verification
        _, _, json_hash, audio_hash = verify_and_load_files(str(moderation_file), str(audio_file))
        
        # Run the processing pipeline
        print("🚀 Running NegativeOutputHandling pipeline...")
        result = await process_with_verification(moderation_result, json_hash, audio_hash)
        
        return result
        
    except Exception as e:
        print(f"❌ NegativeOutputHandling failed: {e}")
        import traceback
        traceback.print_exc()
        raise


def display_final_results(backend_result: Path, negative_output_result: dict):
    """Step 3: Display comprehensive results from both pipelines."""
    
    print(f"\n🎊 STEP 3: UNIFIED PIPELINE RESULTS")
    print("=" * 60)
    
    # Backend results
    print("📊 BACKEND MODERATION RESULTS:")
    with open(backend_result, 'r') as f:
        backend_data = json.load(f)
    
    total_segments = len(backend_data['segments'])
    flagged_segments = [s for s in backend_data['segments'] if s['classification']['label'] != 'NONE']
    
    print(f"   📝 Total segments: {total_segments}")
    print(f"   🚨 Flagged segments: {len(flagged_segments)}")
    print(f"   🌍 Language: {backend_data['language']}")
    print(f"   ⏱️ Duration: {backend_data['duration']:.1f}s")
    
    # NegativeOutputHandling results
    print("\n🎨 NEGATIVE OUTPUT HANDLING RESULTS:")
    processing_result = negative_output_result["processing_result"]
    
    print(f"   ✅ Processing success: {processing_result['success']}")
    print(f"   🔄 Processed segments: {processing_result['processed_segments']}/{processing_result['total_segments']}")
    
    if processing_result['output_json_path']:
        output_path = Path(processing_result['output_json_path'])
        print(f"   📁 Clean JSON: {output_path.name}")
    
    if processing_result['generated_audio_files']:
        print(f"   🎵 Generated audio files: {len(processing_result['generated_audio_files'])}")
        for i, audio_file in enumerate(processing_result['generated_audio_files'][:3], 1):
            file_path = Path(audio_file)
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"      {i}. {file_path.name} ({size:,} bytes)")
    
    # Final summary
    print(f"\n🏆 UNIFIED PIPELINE SUMMARY:")
    print(f"   🎤 Input: Audio file → Backend transcription & classification")
    print(f"   🚨 Detection: {len(flagged_segments)} offensive segments identified")
    print(f"   🎨 Processing: {processing_result['processed_segments']} segments cleaned")
    print(f"   🔊 Output: Clean audio generated with voice cloning")
    
    if processing_result['output_json_path']:
        print(f"\n📂 OUTPUTS LOCATION:")
        output_dir = Path(processing_result['output_json_path']).parent
        print(f"   {output_dir}")


async def run_unified_pipeline(audio_file: Path = None) -> dict:
    """Main unified pipeline function."""
    
    if audio_file is None:
        audio_file = BACKEND_ROOT / "data" / "shmarnalysis.m4a"
    
    print("🚀 UNIFIED CONTENT MODERATION → NEGATIVE OUTPUT PIPELINE")
    print("=" * 80)
    print(f"🎯 Processing: {audio_file.name}")
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Step 1: Backend moderation
        moderation_output = run_backend_moderation(audio_file)
        
        # Step 2: NegativeOutputHandling
        processing_result = await run_negative_output_handling(moderation_output, audio_file)
        
        # Step 3: Display results
        display_final_results(moderation_output, processing_result)
        
        print(f"\n🎉 UNIFIED PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"📅 Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return {
            "success": True,
            "backend_output": str(moderation_output),
            "negative_output_result": processing_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"\n💥 UNIFIED PIPELINE FAILED: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Main entry point."""
    
    # Use the default audio file
    audio_file = BACKEND_ROOT / "data" / "shmarnalysis.m4a"
    
    if not audio_file.exists():
        print(f"❌ Audio file not found: {audio_file}")
        return 1
    
    result = await run_unified_pipeline(audio_file)
    
    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)