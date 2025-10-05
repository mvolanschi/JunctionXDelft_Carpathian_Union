#!/usr/bin/env python3
"""
VERIFICATION VERSION - Process Real ModerationResult JSON with detailed logging

This script processes the actual classified_audio.json file from the backend
using shmarnalysis.m4a as the reference audio for voice cloning.
With extensive verification logging to ensure files are being used correctly.
"""

import asyncio
import json
import base64
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# Import the speech processor
import sys
sys.path.append(str(Path(__file__).parent))
from speech_processor import SpeechProcessor


# Data structures matching the real JSON
@dataclass
class EvidenceSpan:
    quote: str
    char_start: int
    char_end: int

@dataclass
class SafetyInfo:
    used_asr_confidence_rule: bool
    notes: str

@dataclass
class ClassificationOutput:
    label: str
    rationale: str
    spans: List[EvidenceSpan]
    safety: SafetyInfo

@dataclass 
class ClassifiedSegment:
    index: int
    start: float
    end: float
    text: str
    speaker: Optional[str]
    classification: ClassificationOutput

@dataclass
class AudioInfo:
    filename: str
    content_type: str
    data_base64: str

@dataclass
class ModerationResult:
    transcript: str
    language: Optional[str] 
    duration: Optional[float]
    segments: List[ClassifiedSegment]
    audio: AudioInfo


def verify_and_load_files(json_path: str, audio_path: str) -> tuple[dict, bytes, str, str]:
    """Load and verify both input files with detailed logging."""
    
    print("🔍 DETAILED FILE VERIFICATION")
    print("=" * 60)
    
    # Verify JSON file
    json_path_obj = Path(json_path)
    print(f"📁 JSON File Verification:")
    print(f"   Path: {json_path}")
    print(f"   Exists: {json_path_obj.exists()}")
    print(f"   Size: {json_path_obj.stat().st_size:,} bytes" if json_path_obj.exists() else "   Size: N/A")
    
    if not json_path_obj.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    
    # Load and verify JSON content
    with open(json_path, 'r', encoding='utf-8') as f:
        json_content = f.read()
    
    json_hash = hashlib.md5(json_content.encode()).hexdigest()
    print(f"   Content hash: {json_hash}")
    print(f"   First 100 chars: {json_content[:100]}...")
    
    json_data = json.loads(json_content)
    print(f"   ✅ Valid JSON with {len(json_data.get('segments', []))} segments")
    print(f"   Transcript preview: \"{json_data.get('transcript', '')[:80]}...\"")
    
    # Verify audio file
    audio_path_obj = Path(audio_path)
    print(f"\n🎤 Audio File Verification:")
    print(f"   Path: {audio_path}")
    print(f"   Exists: {audio_path_obj.exists()}")
    print(f"   Size: {audio_path_obj.stat().st_size:,} bytes" if audio_path_obj.exists() else "   Size: N/A")
    
    if not audio_path_obj.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Load and verify audio content
    audio_bytes = audio_path_obj.read_bytes()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()
    print(f"   Content hash: {audio_hash}")
    print(f"   File header: {audio_bytes[:16].hex()}")
    print(f"   ✅ Audio loaded successfully")
    
    print(f"\n🎯 VERIFICATION SUMMARY:")
    print(f"   JSON segments: {len(json_data.get('segments', []))}")
    print(f"   JSON hash: {json_hash[:16]}...")
    print(f"   Audio size: {len(audio_bytes):,} bytes") 
    print(f"   Audio hash: {audio_hash[:16]}...")
    print()
    
    return json_data, audio_bytes, json_hash, audio_hash


def load_real_json_file(json_path: str, audio_path: str) -> ModerationResult:
    """Load the real classified_audio.json and create ModerationResult with verification."""
    
    print(f"📁 Loading with verification...")
    
    # Load and verify files
    json_data, audio_bytes, json_hash, audio_hash = verify_and_load_files(json_path, audio_path)
    
    # Encode audio as base64
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    print(f"✅ Files loaded and verified:")
    print(f"   JSON: {len(json_data.get('segments', []))} segments (hash: {json_hash[:8]})")
    print(f"   Audio: {len(audio_bytes):,} bytes → {len(audio_base64):,} base64 chars (hash: {audio_hash[:8]})")
    
    # Convert JSON segments to ClassifiedSegment objects
    segments = []
    offensive_count = 0
    for seg_data in json_data['segments']:
        # Extract classification info
        classification_data = seg_data['classification']
        
        # Count offensive content
        if classification_data['label'] in ["HATE", "PROFANITY", "EXTREMIST", "BOTH"]:
            offensive_count += 1
        
        # Convert spans
        spans = []
        for span_data in classification_data.get('spans', []):
            spans.append(EvidenceSpan(
                quote=span_data['quote'],
                char_start=span_data['char_start'],
                char_end=span_data['char_end']
            ))
        
        # Create safety info
        safety = SafetyInfo(
            used_asr_confidence_rule=classification_data['safety']['used_asr_confidence_rule'],
            notes=classification_data['safety']['notes']
        )
        
        # Create classification
        classification = ClassificationOutput(
            label=classification_data['label'],
            rationale=classification_data['rationale'],
            spans=spans,
            safety=safety
        )
        
        # Create segment
        segment = ClassifiedSegment(
            index=seg_data['index'],
            start=seg_data['start'],
            end=seg_data['end'],
            text=seg_data['text'],
            speaker=seg_data.get('speaker'),
            classification=classification
        )
        
        segments.append(segment)
    
    # Create audio info
    audio_info = AudioInfo(
        filename=Path(audio_path).name,
        content_type="audio/m4a",
        data_base64=audio_base64
    )
    
    # Create ModerationResult
    moderation_result = ModerationResult(
        transcript=json_data['transcript'],
        language=json_data.get('language'),
        duration=json_data.get('duration'),
        segments=segments,
        audio=audio_info
    )
    
    print(f"✅ ModerationResult created:")
    print(f"   Transcript: {len(moderation_result.transcript)} chars")
    print(f"   Language: {moderation_result.language}")
    print(f"   Duration: {moderation_result.duration}s")
    print(f"   Segments: {len(moderation_result.segments)} ({offensive_count} flagged)")
    print(f"   Audio: {moderation_result.audio.filename} ({len(moderation_result.audio.data_base64)} base64 chars)")
    print()
    
    return moderation_result


async def process_with_verification(
    moderation_result: ModerationResult,
    json_hash: str,
    audio_hash: str,
    output_dir: str = r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\NegativeOutputHandling\Data\real_processing_output"
) -> dict:
    """Process ModerationResult with detailed verification logging."""
    
    print("🔥 NegativeOutputHandler - Processing with Verification")
    print("=" * 70)
    
    # Verify we're using the right data
    print("🔍 INPUT VERIFICATION:")
    print(f"   📁 Using JSON hash: {json_hash}")
    print(f"   🎤 Using audio hash: {audio_hash}")
    
    # Display input analysis with exact offensive content
    print(f"\n📊 DETAILED INPUT ANALYSIS:")
    print(f"   💬 Full transcript: {len(moderation_result.transcript)} characters")
    print(f"      Preview: \"{moderation_result.transcript[:100]}...\"")
    print(f"   🌍 Language: {moderation_result.language or 'Unknown'}")
    print(f"   ⏱️ Duration: {moderation_result.duration or 0:.1f}s")
    print(f"   🎵 Audio: {moderation_result.audio.filename} ({len(base64.b64decode(moderation_result.audio.data_base64)):,} bytes)")
    print(f"   📝 Total segments: {len(moderation_result.segments)}")
    
    # Analyze segments for offensive content with exact quotes
    offensive_segments = [
        seg for seg in moderation_result.segments 
        if seg.classification.label in ["HATE", "PROFANITY", "EXTREMIST", "BOTH"]
    ]
    print(f"   🚨 Flagged segments: {len(offensive_segments)}")
    
    # Show exact offensive content being processed
    if offensive_segments:
        print(f"\n   🎯 EXACT OFFENSIVE CONTENT TO BE PROCESSED:")
        for i, seg in enumerate(offensive_segments, 1):
            print(f"      {i}. Segment {seg.index} ({seg.start:.1f}s-{seg.end:.1f}s)")
            print(f"         Label: {seg.classification.label}")
            print(f"         Text: \"{seg.text}\"")
            print(f"         Rationale: {seg.classification.rationale}")
            if seg.classification.spans:
                print(f"         Evidence spans: {len(seg.classification.spans)}")
                for span in seg.classification.spans:
                    print(f"           - \"{span.quote}\" (chars {span.char_start}-{span.char_end})")
            print()
    
    # Step 1: Save audio from base64 as reference for voice cloning
    print("🎤 Step 1: Extracting reference audio for voice cloning...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Decode and verify audio data
    audio_data = base64.b64decode(moderation_result.audio.data_base64)
    audio_verify_hash = hashlib.md5(audio_data).hexdigest()
    
    print(f"   🔍 Audio verification:")
    print(f"      Original hash: {audio_hash}")
    print(f"      Decoded hash:  {audio_verify_hash}")
    print(f"      Match: {'✅ YES' if audio_hash == audio_verify_hash else '❌ NO'}")
    
    temp_audio_path = output_path / f"temp_reference_audio_{audio_hash[:8]}.m4a"
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_data)
    print(f"   ✅ Reference audio saved: {temp_audio_path.name} ({len(audio_data):,} bytes)")
    
    # Step 2: Convert ModerationResult to our internal format  
    print("\n🔄 Step 2: Converting to processing format...")
    converted_data = _convert_moderation_to_json(moderation_result)
    
    print(f"   📊 Converted data:")
    print(f"      Segments: {len(converted_data['segments'])}")
    print(f"      Speakers: {list(converted_data['speakers'].keys())}")
    
    # Count offensive parts in converted data
    total_offensive = sum(len(seg.get('offensive_parts', [])) for seg in converted_data['segments'])
    print(f"      Offensive parts: {total_offensive}")
    
    # Save converted data as temp JSON for processing
    temp_json_path = output_path / f"temp_input_{json_hash[:8]}.json"
    with open(temp_json_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✅ Conversion complete: {temp_json_path.name}")
    
    # Step 3: Initialize speech processor with verified files
    print(f"\n⚙️ Step 3: Initializing speech processor...")
    print(f"   📁 Input JSON: {temp_json_path}")
    print(f"   🎤 Reference audio: {temp_audio_path}")
    print(f"   📂 Output dir: {output_dir}")
    
    # Create absolute config path 
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config" / "api_keys.json"
    print(f"   🔍 Looking for config at: {config_path}")
    
    processor = SpeechProcessor(
        input_json_path=str(temp_json_path),
        reference_audio_path=str(temp_audio_path),
        output_dir=output_dir,
        config_path=str(config_path)
    )
    
    # Step 4: Run processing pipeline
    print(f"\n🚀 Step 4: Running verified processing pipeline...")
    result = await processor.process_complete()
    
    # Step 5: Verify and return results
    enhanced_result = {
        "verification": {
            "json_hash": json_hash,
            "audio_hash": audio_hash,
            "files_verified": True
        },
        "original_moderation": {
            "transcript": moderation_result.transcript,
            "language": moderation_result.language,
            "duration": moderation_result.duration,
            "total_segments": len(moderation_result.segments),
            "offensive_segments": len(offensive_segments),
            "exact_offensive_content": [
                {
                    "index": seg.index,
                    "text": seg.text,
                    "label": seg.classification.label,
                    "rationale": seg.classification.rationale
                }
                for seg in offensive_segments
            ]
        },
        "processing_result": {
            "success": result.success,
            "processed_segments": result.processed_segments,
            "total_segments": result.total_segments,
            "output_json_path": str(result.output_json_path) if result.output_json_path else None,
            "generated_audio_files": [str(f) for f in result.generated_audio_files],
            "errors": result.errors
        }
    }
    
    # Cleanup temporary files
    temp_audio_path.unlink(missing_ok=True)
    temp_json_path.unlink(missing_ok=True)
    
    # Display detailed results
    print(f"\n📋 DETAILED PROCESSING RESULTS:")
    if result.success:
        print(f"   🎉 SUCCESS! Verified processing of real data")
        print(f"   🔍 Input verification: JSON {json_hash[:8]}, Audio {audio_hash[:8]}")
        print(f"   📊 Original: {len(moderation_result.segments)} segments ({len(offensive_segments)} flagged)")
        print(f"   ✅ Processed: {result.processed_segments}/{result.total_segments} segments")
        print(f"   📁 Output JSON: {Path(result.output_json_path).name}")
        print(f"   🔊 Generated audio: {len(result.generated_audio_files)} files")
        
        # Show which specific segments were processed
        print(f"\n   🎯 VERIFIED PROCESSING OF THESE EXACT SEGMENTS:")
        for seg in offensive_segments:
            print(f"      • Segment {seg.index}: \"{seg.text[:60]}...\" [{seg.classification.label}]")
        
        # List generated audio files
        if result.generated_audio_files:
            print(f"\n   🎵 Generated clean audio files:")
            for i, audio_file in enumerate(result.generated_audio_files, 1):
                file_size = audio_file.stat().st_size if audio_file.exists() else 0
                print(f"      {i}. {audio_file.name} ({file_size:,} bytes)")
    else:
        print(f"   ❌ FAILED! Could not process verified input")
        for error in result.errors:
            print(f"      • {error}")
    
    return enhanced_result


def _convert_moderation_to_json(moderation_result: ModerationResult) -> dict:
    """Convert ModerationResult to our internal JSON format."""
    
    # Create speakers mapping from segments
    speakers = {}
    for segment in moderation_result.segments:
        if segment.speaker and segment.speaker not in speakers:
            speakers[segment.speaker] = f"Speaker {segment.speaker.replace('_', ' ').title()}"
    
    # Convert segments to our format
    converted_segments = []
    for segment in moderation_result.segments:
        
        # Create offensive_parts from classification if flagged
        offensive_parts = []
        if segment.classification.label in ["HATE", "PROFANITY", "EXTREMIST", "BOTH"]:
            
            # Use evidence spans if available, otherwise use full segment
            if segment.classification.spans:
                for span in segment.classification.spans:
                    offensive_parts.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": span.quote,
                        "severity": _map_label_to_severity(segment.classification.label),
                        "rationale": segment.classification.rationale,
                        "char_start": span.char_start,
                        "char_end": span.char_end
                    })
            else:
                # Fallback: treat entire segment as offensive
                offensive_parts.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "severity": _map_label_to_severity(segment.classification.label),
                    "rationale": segment.classification.rationale
                })
        
        converted_segment = {
            "start": segment.start,
            "end": segment.end,
            "speaker_id": segment.speaker or f"speaker_{segment.index}",
            "text": segment.text,
            "offensive_parts": offensive_parts
        }
        converted_segments.append(converted_segment)
    
    return {
        "speakers": speakers,
        "segments": converted_segments,
        "metadata": {
            "original_transcript": moderation_result.transcript,
            "language": moderation_result.language,
            "duration": moderation_result.duration,
            "audio_filename": moderation_result.audio.filename,
            "source": "classified_audio_json_verified"
        }
    }


def _map_label_to_severity(label: str) -> str:
    """Map classification labels to severity levels."""
    severity_map = {
        "HATE": "high",
        "PROFANITY": "medium",
        "EXTREMIST": "high", 
        "BOTH": "high"
    }
    return severity_map.get(label, "low")


async def main():
    """Main function to process the real classified_audio.json file with verification."""
    
    try:
        # Define file paths
        json_file = r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\data\classified_audio,json"
        audio_file = r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\data\shmarnalysis.m4a"
        
        print("🚀 VERIFICATION RUN - Processing Real Classified Audio Data")
        print("=" * 80)
        print(f"📁 JSON file: {Path(json_file).name}")
        print(f"🎤 Audio file: {Path(audio_file).name}")
        print()
        
        # Load the real data with verification
        moderation_result = load_real_json_file(json_file, audio_file)
        
        # Get file hashes for verification tracking
        _, _, json_hash, audio_hash = verify_and_load_files(json_file, audio_file)
        
        # Process it with our enhanced pipeline
        result = await process_with_verification(moderation_result, json_hash, audio_hash)
        
        print("\n" + "=" * 80)
        if result["processing_result"]["success"]:
            print(f"🎊 VERIFICATION COMPLETE - 100% SUCCESS!")
            print(f"✅ Confirmed using: JSON {json_hash[:16]}, Audio {audio_hash[:16]}")
            print(f"✅ Processed {result['original_moderation']['offensive_segments']} offensive segments")
            print(f"✅ Generated {len(result['processing_result']['generated_audio_files'])} clean audio files")
            print("📂 Check the output directory for all generated files!")
        else:
            print(f"💥 VERIFICATION FAILED - Processing unsuccessful")
            
    except Exception as e:
        print(f"\n💥 Error during verification: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())