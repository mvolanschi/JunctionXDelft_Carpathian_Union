#!/usr/bin/env python3
"""
Speech Processor for ModerationResult Integration.
    # Display input analysis
    print("📊 INPUT ANALYSIS:")
    print(f"   💬 Full transcript: {len(moderation_result.transcript)} characters")
    print(f"   🌍 Language: {moderation_result.language or 'Unknown'}")
    print(f"   ⏱️ Duration: {moderation_result.duration or 0:.1f}s")
    print(f"   🎵 Audio file: {moderation_result.audio.filename} ({moderation_result.audio.content_type})")
    print(f"   📝 Segments: {len(moderation_result.segments)} total")
    
    # Analyze segments for offensive content (updated labels)
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
    print()rocesses ModerationResult from the backend moderation pipeline:
1. Takes ModerationResult with classified segments as input
2. Extracts audio bytes for voice cloning reference
3. Rewrites offensive content based on classification results
4. Generates clean audio for flagged segments using cloned voice
5. Outputs enhanced ModerationResult + audio files
"""

import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from speech_processor import SpeechProcessor


# Real ModerationResult structure (normally imported from backend)
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


async def process_moderation_result(
    moderation_result: ModerationResult,
    output_dir: str = "../Data/enhanced_output"
) -> dict:
    """
    Process ModerationResult to clean offensive content and regenerate audio.
    
    Args:
        moderation_result: Result from backend moderation pipeline
        output_dir: Directory for output files
        
    Returns:
        Enhanced processing result with clean content and audio
    """
    print("🔥 NegativeOutputHandler - Processing ModerationResult")
    print("=" * 60)
    
    # Display input analysis
    print("📊 INPUT ANALYSIS:")
    print(f"   💬 Full transcript: {len(moderation_result.transcript)} characters")
    print(f"   🌍 Language: {moderation_result.language or 'Unknown'}")
    print(f"   ⏱️ Duration: {moderation_result.duration or 0:.1f}s")
    print(f"   🎵 Audio size: {len(moderation_result.audio_bytes):,} bytes")
    print(f"   📝 Segments: {len(moderation_result.segments)} total")
    
    # Analyze segments for offensive content
    offensive_segments = [
        seg for seg in moderation_result.segments 
        if seg.classification.label in ["HATE", "EXTREMIST", "BOTH", "OFFENSIVE"]
    ]
    print(f"   � Offensive segments: {len(offensive_segments)}")
    print()
    
    # Step 1: Save audio from base64 as reference for voice cloning
    print("🎤 Step 1: Preparing audio reference for voice cloning...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Decode base64 audio data and save to temporary file for voice cloning
    import base64
    audio_data = base64.b64decode(moderation_result.audio.data_base64)
    
    # Use original filename extension or default to the content type
    original_ext = Path(moderation_result.audio.filename).suffix
    if not original_ext:
        ext_map = {
            "audio/wav": ".wav",
            "audio/mp3": ".mp3", 
            "audio/m4a": ".m4a",
            "audio/mpeg": ".mp3"
        }
        original_ext = ext_map.get(moderation_result.audio.content_type, ".wav")
    
    temp_audio_path = output_path / f"temp_reference_audio{original_ext}"
    with open(temp_audio_path, 'wb') as f:
        f.write(audio_data)
    print(f"   ✅ Reference audio saved: {temp_audio_path} ({len(audio_data):,} bytes)")
    
    # Step 2: Convert ModerationResult to our internal format  
    print("� Step 2: Converting ModerationResult to processing format...")
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
        print(f"\n🎉 ENHANCED PROCESSING SUCCESS!")
        print(f"   📊 Original segments: {len(moderation_result.segments)} ({len(offensive_segments)} offensive)")
        print(f"   ✅ Processed segments: {result.processed_segments}/{result.total_segments}")
        print(f"   📁 Enhanced JSON: {result.output_json_path}")
        print(f"   🔊 Generated audio: {len(result.generated_audio_files)} files")
        print(f"   🌍 Language context: {moderation_result.language or 'Auto-detected'}")
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
        print(f"\n❌ ENHANCED PROCESSING FAILED!")
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
            "source": "moderation_pipeline"
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


async def demo_with_real_json():
    """Demo using the real JSON structure provided."""
    
    print("\n" + "=" * 60)
    print("🧪 Demo: Processing Real ModerationResult JSON Structure")
    
    # Load reference audio and encode as base64 for realistic demo
    reference_audio_path = Path("../Data/reference_audio/reading-from-descartes-discourse-on-method-20113.mp3")
    if not reference_audio_path.exists():
        print("⚠️ Reference audio not found, skipping demo")
        return
    
    audio_bytes = reference_audio_path.read_bytes()
    import base64
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    print(f"✅ Loaded reference audio: {len(audio_bytes):,} bytes")
    
    # Create realistic segments based on the provided JSON
    segments = [
        ClassifiedSegment(
            index=3,
            start=11.08,
            end=15.28,
            text="Attendance is decent, but scheduling this stuff can be fucking annoying when volunteers cancel",
            speaker="SPEAKER_00",
            classification=ClassificationOutput(
                label="PROFANITY",
                rationale="Contains profanity without targeting a protected class.",
                spans=[EvidenceSpan(quote="fucking annoying", char_start=44, char_end=58)],
                safety=SafetyInfo(used_asr_confidence_rule=False, notes="")
            )
        ),
        ClassifiedSegment(
            index=7,
            start=25.88,
            end=28.64,
            text="I hate those damn Romanians, taking our jobs and all.",
            speaker="SPEAKER_00",
            classification=ClassificationOutput(
                label="HATE",
                rationale="Contains derogatory language targeting Romanians, a protected class, with accusations of job theft.",
                spans=[EvidenceSpan(quote="I hate those damn Romanians, taking our jobs and all", char_start=0, char_end=43)],
                safety=SafetyInfo(used_asr_confidence_rule=False, notes="")
            )
        ),
        ClassifiedSegment(
            index=9,
            start=30.96,
            end=33.72,
            text="All they do is lay on the couch and take benefits.",
            speaker="SPEAKER_00",
            classification=ClassificationOutput(
                label="HATE",
                rationale="Contains derogatory language towards individuals receiving benefits, implying they are lazy and undeserving.",
                spans=[EvidenceSpan(quote="lay on the couch and take benefits", char_start=15, char_end=41)],
                safety=SafetyInfo(used_asr_confidence_rule=False, notes="")
            )
        ),
        ClassifiedSegment(
            index=15,
            start=49.68,
            end=51.24,
            text="Anyway, I should head out.",
            speaker="SPEAKER_00",
            classification=ClassificationOutput(
                label="NONE",
                rationale="Contains no profanity, hate speech, or extremist content.",
                spans=[],
                safety=SafetyInfo(used_asr_confidence_rule=False, notes="")
            )
        )
    ]
    
    mock_result = ModerationResult(
        transcript="Attendance is decent, but scheduling this stuff can be fucking annoying when volunteers cancel. I hate those damn Romanians, taking our jobs and all. All they do is lay on the couch and take benefits. Anyway, I should head out.",
        language="en",
        duration=53.93,
        segments=segments,
        audio=AudioInfo(
            filename="sample_audio_rec.m4a",
            content_type="audio/m4a",
            data_base64=audio_base64[:100] + "..."  # Truncated for demo
        )
    )
    
    # For demo, use actual audio file instead of truncated base64
    mock_result.audio.data_base64 = audio_base64
    
    # Process the realistic result
    enhanced_result = await process_moderation_result(mock_result)
    
    if enhanced_result["processing_result"]["success"]:
        print(f"\n🎉 Real JSON demo completed successfully!")
    else:
        print(f"\n❌ Real JSON demo failed!")


if __name__ == "__main__":
    async def main():
        try:
            # Run ModerationResult processing demo with real JSON structure
            await demo_with_real_json()
            
        except KeyboardInterrupt:
            print("\n🛑 Processing interrupted by user")
        except Exception as e:
            print(f"\n💥 Unexpected error: {e}")
    
    asyncio.run(main())