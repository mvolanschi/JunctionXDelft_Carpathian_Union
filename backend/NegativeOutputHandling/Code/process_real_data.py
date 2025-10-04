#!/usr/bin/env python3
"""
Process Real ModerationResult JSON with NegativeOutputHandler

This script processes the actual classified_audio.json file from the backend
using shmarnalysis.m4a as the reference audio for voice cloning.
"""

import asyncio
import json
import base64
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


def load_real_json_file(json_path: str, audio_path: str) -> ModerationResult:
    """Load the real classified_audio.json and create ModerationResult."""
    
    print(f"📁 Loading JSON: {json_path}")
    print(f"🎤 Loading audio: {audio_path}")
    
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load audio file and encode as base64
    audio_path_obj = Path(audio_path)
    if not audio_path_obj.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    audio_bytes = audio_path_obj.read_bytes()
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    print(f"✅ JSON loaded: {len(data.get('segments', []))} segments")
    print(f"✅ Audio loaded: {len(audio_bytes):,} bytes")
    
    # Convert JSON segments to ClassifiedSegment objects
    segments = []
    for seg_data in data['segments']:
        # Extract classification info
        classification_data = seg_data['classification']
        
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
        filename=audio_path_obj.name,
        content_type="audio/m4a",  # Based on the .m4a extension
        data_base64=audio_base64
    )
    
    # Create ModerationResult
    moderation_result = ModerationResult(
        transcript=data['transcript'],
        language=data.get('language'),
        duration=data.get('duration'),
        segments=segments,
        audio=audio_info
    )
    
    return moderation_result


async def process_moderation_result(
    moderation_result: ModerationResult,
    output_dir: str = "../../backend/NegativeOutputHandling/Data/real_processing_output"
) -> dict:
    """Process ModerationResult to clean offensive content and regenerate audio."""
    
    print("🔥 NegativeOutputHandler - Processing Real ModerationResult")
    print("=" * 60)
    
    # Display input analysis
    print("📊 INPUT ANALYSIS:")
    print(f"   💬 Full transcript: {len(moderation_result.transcript)} characters")
    print(f"   🌍 Language: {moderation_result.language or 'Unknown'}")
    print(f"   ⏱️ Duration: {moderation_result.duration or 0:.1f}s")
    print(f"   🎵 Audio file: {moderation_result.audio.filename} ({moderation_result.audio.content_type})")
    print(f"   📝 Segments: {len(moderation_result.segments)} total")
    
    # Analyze segments for offensive content
    offensive_segments = [
        seg for seg in moderation_result.segments 
        if seg.classification.label in ["HATE", "PROFANITY", "EXTREMIST", "BOTH"]
    ]
    print(f"   🚨 Flagged segments: {len(offensive_segments)}")
    
    # Show breakdown by classification
    label_counts = {}
    for seg in moderation_result.segments:
        label = seg.classification.label
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("   📋 Classification breakdown:")
    for label, count in sorted(label_counts.items()):
        emoji = "🚨" if label in ["HATE", "PROFANITY", "EXTREMIST"] else "✅"
        print(f"      {emoji} {label}: {count}")
    
    # Show specific offensive segments
    if offensive_segments:
        print("\n   🎯 Flagged content preview:")
        for i, seg in enumerate(offensive_segments[:3], 1):  # Show first 3
            print(f"      {i}. [{seg.classification.label}] \"{seg.text[:60]}{'...' if len(seg.text) > 60 else ''}\"")
        if len(offensive_segments) > 3:
            print(f"      ... and {len(offensive_segments) - 3} more flagged segments")
    
    print()
    
    # Step 1: Save audio from base64 as reference for voice cloning
    print("🎤 Step 1: Preparing audio reference for voice cloning...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Decode base64 audio data and save to temporary file for voice cloning
    audio_data = base64.b64decode(moderation_result.audio.data_base64)
    temp_audio_path = output_path / f"temp_reference_audio.m4a"
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_data)
    print(f"   ✅ Reference audio saved: {temp_audio_path} ({len(audio_data):,} bytes)")
    
    # Step 2: Convert ModerationResult to our internal format  
    print("🔄 Step 2: Converting ModerationResult to processing format...")
    converted_data = _convert_moderation_to_json(moderation_result)
    
    # Save converted data as temp JSON for processing
    temp_json_path = output_path / "temp_input.json"
    with open(temp_json_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, indent=2, ensure_ascii=False)
    
    # Step 3: Initialize speech processor
    print("⚙️ Step 3: Initializing speech processor...")
    processor = SpeechProcessor(
        input_json_path=str(temp_json_path),
        reference_audio_path=str(temp_audio_path),
        output_dir=output_dir
    )
    
    # Step 4: Run processing pipeline
    print("🚀 Step 4: Running enhanced processing pipeline...")
    result = await processor.process_complete()
    
    # Step 5: Analyze and return results
    enhanced_result = {
        "original_moderation": {
            "transcript": moderation_result.transcript,
            "language": moderation_result.language,
            "duration": moderation_result.duration,
            "total_segments": len(moderation_result.segments),
            "offensive_segments": len(offensive_segments)
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
    
    # Display results
    if result.success:
        print(f"\n🎉 REAL DATA PROCESSING SUCCESS!")
        print(f"   📊 Original segments: {len(moderation_result.segments)} ({len(offensive_segments)} flagged)")
        print(f"   ✅ Processed segments: {result.processed_segments}/{result.total_segments}")
        print(f"   📁 Enhanced JSON: {result.output_json_path}")
        print(f"   🔊 Generated audio: {len(result.generated_audio_files)} files")
        print(f"   🌍 Language: {moderation_result.language or 'Auto-detected'}")
        print(f"   ⏱️ Original duration: {moderation_result.duration or 0:.1f}s")
        
        # List generated audio files
        if result.generated_audio_files:
            print(f"\n🎵 Generated clean audio files:")
            for i, audio_file in enumerate(result.generated_audio_files[:3], 1):  # Show first 3
                file_size = audio_file.stat().st_size if audio_file.exists() else 0
                print(f"   {i}. {audio_file.name} ({file_size:,} bytes)")
            if len(result.generated_audio_files) > 3:
                print(f"   ... and {len(result.generated_audio_files) - 3} more files")
    else:
        print(f"\n❌ REAL DATA PROCESSING FAILED!")
        for error in result.errors:
            print(f"   • {error}")
    
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
            "source": "classified_audio_json"
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
    """Main function to process the real classified_audio.json file."""
    
    try:
        # Define file paths
        json_file = r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\data\classified_audio,json"
        audio_file = r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\data\shmarnalysis.m4a"
        
        print("🚀 Processing Real Classified Audio Data")
        print("=" * 50)
        print(f"📁 JSON file: {json_file}")
        print(f"🎤 Audio file: {audio_file}")
        print()
        
        # Load the real data
        moderation_result = load_real_json_file(json_file, audio_file)
        
        # Process it with our enhanced pipeline
        result = await process_moderation_result(moderation_result)
        
        if result["processing_result"]["success"]:
            print(f"\n🎊 COMPLETE SUCCESS!")
            print("Check the output directory for cleaned JSON and audio files!")
        else:
            print(f"\n💥 Processing failed - see errors above")
            
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())