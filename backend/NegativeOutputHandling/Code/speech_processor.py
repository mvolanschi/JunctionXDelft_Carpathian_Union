#!/usr/bin/env python3
"""
Main Speech Processing Module for NegativeOutputHandler

This module provides a complete pipeline for:
1. Loading input JSON with offensive content
2. Rewriting all offensive parts using AI content rewriter
3. Cloning voice from reference audio
4. Re-recording all offensive sentences with cloned voice
5. Outputting cleaned JSON + generated audio files

Usage:
    from speech_processor import SpeechProcessor
    
    processor = SpeechProcessor(
        input_json_path="input.json",
        reference_audio_path="reference.mp3",
        output_dir="output/"
    )
    
    result = await processor.process_complete()
"""

import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from content_rewriter import GroqContentRewriter
from advanced_voice_generator import AdvancedVoiceGenerator, create_voice_config


@dataclass
class ProcessingResult:
    """Result of the complete speech processing pipeline."""
    success: bool
    output_json_path: Optional[Path] = None
    generated_audio_files: List[Path] = None
    processed_segments: int = 0
    total_segments: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.generated_audio_files is None:
            self.generated_audio_files = []
        if self.errors is None:
            self.errors = []


class SpeechProcessor:
    """Main speech processing class for cleaning offensive content and regenerating audio."""
    
    def __init__(
        self,
        input_json_path: str,
        reference_audio_path: str,
        output_dir: str = "output",
        config_path: str = "../config/api_keys.json"
    ):
        """
        Initialize the speech processor.
        
        Args:
            input_json_path: Path to input JSON with transcription data
            reference_audio_path: Path to reference audio for voice cloning
            output_dir: Directory to save output files
            config_path: Path to API keys configuration file
        """
        self.input_json_path = Path(input_json_path)
        self.reference_audio_path = Path(reference_audio_path)
        self.output_dir = Path(output_dir)
        self.config_path = Path(config_path)
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.content_rewriter = None
        self.voice_generator = None
        self.input_data = None
        
    async def initialize(self) -> bool:
        """Initialize content rewriter and voice generator."""
        print("🔧 Initializing Speech Processor...")
        
        # Initialize content rewriter
        if not await self._init_content_rewriter():
            return False
            
        # Initialize voice generator
        if not await self._init_voice_generator():
            return False
            
        return True
    
    async def _init_content_rewriter(self) -> bool:
        """Initialize the content rewriter (Groq or fallback)."""
        try:
            # Try environment variable first
            groq_api_key = os.getenv('GROQ_API_KEY')
            
            # Try config file if no env var
            if not groq_api_key and self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    groq_api_key = config_data.get('groq_api_key')
            
            if groq_api_key and groq_api_key.strip():
                self.content_rewriter = GroqContentRewriter(groq_api_key)
                print("✅ Initialized GroqContentRewriter")
                return True
            else:
                # Fallback to simple rewriter
                print("⚠️ No Groq API key found, using fallback rewriter")
                self._init_fallback_rewriter()
                return True
                
        except Exception as e:
            print(f"❌ Error initializing content rewriter: {e}")
            self._init_fallback_rewriter()
            return True
    
    def _init_fallback_rewriter(self):
        """Initialize simple fallback content rewriter."""
        class SimpleFallbackRewriter:
            async def rewrite_offensive_text(self, text: str, context: str) -> str:
                replacements = {
                    "completely fucked": "completely broken",
                    "fucking around": "wasting time",
                    "like they're on crack": "very erratically", 
                    "total clusterfuck": "total mess",
                    "shit-tier garbage": "terrible quality",
                    "didn't give a shit": "didn't care",
                    "get our shit together": "get organized",
                    "go down the toilet": "fail completely",
                    "fucking": "really",
                    "fucked": "broken", 
                    "shit": "poor",
                    "damn": "very",
                    "crap": "junk",
                    "screw this": "forget this"
                }
                result = text
                for bad, good in replacements.items():
                    result = result.replace(bad, good)
                return result
        
        self.content_rewriter = SimpleFallbackRewriter()
        print("✅ Initialized fallback content rewriter")
    
    async def _init_voice_generator(self) -> bool:
        """Initialize the voice generator with ElevenLabs."""
        try:
            # Load ElevenLabs API key
            elevenlabs_api_key = None
            
            print(f"🔍 Config path: {self.config_path}")
            print(f"🔍 Config exists: {self.config_path.exists()}")
            
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    elevenlabs_api_key = config_data.get('elevenlabs_api_key')
                    print(f"🔍 Found API key: {elevenlabs_api_key[:10] if elevenlabs_api_key else 'None'}...")
            
            if not elevenlabs_api_key:
                print("❌ ElevenLabs API key not found")
                return False
            
            # Check reference audio exists
            if not self.reference_audio_path.exists():
                print(f"❌ Reference audio not found: {self.reference_audio_path}")
                return False
            
            # Create voice configuration
            voice_config = create_voice_config(
                elevenlabs_api_key=elevenlabs_api_key,
                backend='elevenlabs',
                quality='high'
            )
            
            # Initialize voice generator
            self.voice_generator = AdvancedVoiceGenerator(
                reference_audio_path=str(self.reference_audio_path),
                config=voice_config
            )
            
            print(f"✅ Initialized voice generator with reference: {self.reference_audio_path.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing voice generator: {e}")
            return False
    
    async def load_input_data(self) -> bool:
        """Load and validate input JSON data."""
        try:
            if not self.input_json_path.exists():
                print(f"❌ Input JSON not found: {self.input_json_path}")
                return False
            
            with open(self.input_json_path, 'r', encoding='utf-8') as f:
                self.input_data = json.load(f)
            
            # Validate structure
            if 'segments' not in self.input_data:
                print("❌ Input JSON missing 'segments' field")
                return False
            
            segments_count = len(self.input_data['segments'])
            offensive_count = sum(1 for seg in self.input_data['segments'] 
                                if seg.get('offensive_parts'))
            
            print(f"✅ Loaded input data: {segments_count} segments, {offensive_count} with offensive content")
            return True
            
        except Exception as e:
            print(f"❌ Error loading input data: {e}")
            return False
    
    async def process_complete(self) -> ProcessingResult:
        """
        Complete processing pipeline:
        1. Load input JSON
        2. Rewrite all offensive content 
        3. Clone voice from reference audio
        4. Generate audio for all rewritten segments
        5. Save cleaned JSON and audio files
        """
        print("🚀 Starting Complete Speech Processing Pipeline")
        print("=" * 60)
        
        result = ProcessingResult(success=False)
        
        try:
            # Step 1: Initialize components
            if not await self.initialize():
                result.errors.append("Failed to initialize components")
                return result
            
            # Step 2: Load input data
            if not await self.load_input_data():
                result.errors.append("Failed to load input data")
                return result
            
            result.total_segments = len(self.input_data['segments'])
            
            # Step 3: Process all segments
            print(f"\n📝 Step 1: Processing {result.total_segments} segments...")
            processed_data = await self._process_all_segments()
            
            # Step 4: Generate audio for rewritten segments
            print(f"\n🎤 Step 2: Generating audio for rewritten segments...")
            audio_files = await self._generate_audio_for_segments(processed_data)
            
            # Step 5: Save output JSON and update with audio file paths
            print(f"\n💾 Step 3: Saving output files...")
            output_json_path = await self._save_output_json(processed_data, audio_files)
            
            # Success!
            result.success = True
            result.output_json_path = output_json_path
            result.generated_audio_files = audio_files
            result.processed_segments = len([s for s in processed_data['segments'] if s.get('was_rewritten')])
            
            print(f"\n🎉 SUCCESS! Processing completed:")
            print(f"   📁 Output JSON: {result.output_json_path}")
            print(f"   🔊 Generated {len(result.generated_audio_files)} audio files")
            print(f"   📊 Processed {result.processed_segments}/{result.total_segments} segments")
            
            return result
            
        except Exception as e:
            error_msg = f"Processing failed: {e}"
            print(f"❌ {error_msg}")
            result.errors.append(error_msg)
            return result
    
    async def _process_all_segments(self) -> Dict:
        """Process all segments to rewrite offensive content."""
        processed_data = self.input_data.copy()
        rewritten_count = 0
        
        for i, segment in enumerate(processed_data['segments']):
            segment_id = f"segment_{i}"
            print(f"   Processing {segment_id}... ", end="")
            
            # Check if segment has offensive content
            if not segment.get('offensive_parts'):
                print("✓ Clean")
                segment['was_rewritten'] = False
                continue
            
            # Rewrite offensive content
            try:
                original_text = segment['text']
                context = f"Professional meeting. Speaker: {processed_data.get('speakers', {}).get(segment['speaker_id'], 'Unknown')}"
                
                rewritten_text = await self.content_rewriter.rewrite_offensive_text(
                    original_text, context
                )
                
                # Update segment
                segment['original_text'] = original_text
                segment['text'] = rewritten_text
                segment['was_rewritten'] = True
                
                rewritten_count += 1
                print(f"✓ Rewritten ({len(rewritten_text)} chars)")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                segment['was_rewritten'] = False
        
        print(f"   📊 Rewritten {rewritten_count} segments with offensive content")
        return processed_data
    
    async def _generate_audio_for_segments(self, processed_data: Dict) -> List[Path]:
        """Generate audio files for all rewritten segments."""
        audio_files = []
        
        # Create audio output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_output_dir = self.output_dir / f"generated_audio_{timestamp}"
        audio_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get segments that were rewritten
        rewritten_segments = [
            (i, seg) for i, seg in enumerate(processed_data['segments']) 
            if seg.get('was_rewritten')
        ]
        
        if not rewritten_segments:
            print("   ℹ️ No segments need audio generation")
            return audio_files
        
        print(f"   🎵 Generating audio for {len(rewritten_segments)} rewritten segments...")
        
        for segment_idx, segment in rewritten_segments:
            try:
                # Create audio file name
                speaker_id = segment['speaker_id']
                audio_filename = f"{speaker_id}_segment_{segment_idx:03d}.mp3"
                audio_path = audio_output_dir / audio_filename
                
                print(f"      🔊 {audio_filename}... ", end="")
                
                # Generate audio
                success = self.voice_generator.generate_audio(
                    text=segment['text'],
                    output_path=str(audio_path)
                )
                
                if success and audio_path.exists():
                    # Update segment with audio file path
                    segment['generated_audio_file'] = str(audio_path.relative_to(self.output_dir))
                    audio_files.append(audio_path)
                    
                    file_size = audio_path.stat().st_size
                    print(f"✓ ({file_size:,} bytes)")
                else:
                    print("❌ Failed")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        return audio_files
    
    async def _save_output_json(self, processed_data: Dict, audio_files: List[Path]) -> Path:
        """Save the processed data to output JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json_path = self.output_dir / f"cleaned_transcription_{timestamp}.json"
        
        # Add processing metadata
        processed_data['processing_info'] = {
            'timestamp': timestamp,
            'original_file': str(self.input_json_path),
            'reference_audio': str(self.reference_audio_path),
            'total_segments': len(processed_data['segments']),
            'rewritten_segments': len([s for s in processed_data['segments'] if s.get('was_rewritten')]),
            'generated_audio_files': len(audio_files),
            'processor_version': '1.0'
        }
        
        # Save to file
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        return output_json_path


# Convenience functions for easy usage
async def process_transcription(
    input_json_path: str,
    reference_audio_path: str,
    output_dir: str = "output"
) -> ProcessingResult:
    """
    Convenience function to process a transcription file.
    
    Args:
        input_json_path: Path to input JSON with transcription
        reference_audio_path: Path to reference audio for voice cloning  
        output_dir: Output directory for results
        
    Returns:
        ProcessingResult with success status and file paths
    """
    processor = SpeechProcessor(
        input_json_path=input_json_path,
        reference_audio_path=reference_audio_path,
        output_dir=output_dir
    )
    
    return await processor.process_complete()


if __name__ == "__main__":
    # Example usage
    async def main():
        result = await process_transcription(
            input_json_path="../Data/example_jsons/expanded_input_transcription.json",
            reference_audio_path="../Data/reference_audio/reading-from-descartes-discourse-on-method-20113.mp3",
            output_dir="../Data/output"
        )
        
        if result.success:
            print(f"\n✅ Processing completed successfully!")
            print(f"📁 Output JSON: {result.output_json_path}")
            print(f"🔊 Generated {len(result.generated_audio_files)} audio files")
        else:
            print(f"\n❌ Processing failed:")
            for error in result.errors:
                print(f"   • {error}")
    
    asyncio.run(main())