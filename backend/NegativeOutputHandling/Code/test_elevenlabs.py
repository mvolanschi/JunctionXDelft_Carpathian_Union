#!/usr/bin/env python3
"""
Test script for ElevenLabs voice generation with reference voice.
This script:
1. Loads data with offensive content
2. Rewrites offensive parts using content rewriter
3. Clones voice from reference audio
4. Generates one rewritten sentence with ElevenLabs cloned voice
"""

import json
import os
import sys
import asyncio
from pathlib import Path
from advanced_voice_generator import AdvancedVoiceGenerator, create_voice_config
from content_rewriter import GroqContentRewriter

def load_sample_data():
    """Load sample transcription data."""
    try:
        # Load the expanded transcription with rewritten content
        data_file = Path("../Data/example_jsons/expanded_input_transcription.json")
        
        if not data_file.exists():
            print(f"❌ Sample data file not found: {data_file}")
            return None
            
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ Loaded sample data with {len(data.get('segments', []))} segments")
        return data
        
    except Exception as e:
        print(f"❌ Error loading sample data: {e}")
        return None

async def rewrite_offensive_content(data, content_rewriter):
    """Find and rewrite offensive content in segments."""
    if not data or 'segments' not in data:
        return None
    
    for segment in data['segments']:
        # Look for segments with offensive parts
        if segment.get('offensive_parts') and len(segment['offensive_parts']) > 0:
            print(f"📝 Found segment with offensive content:")
            print(f"   Speaker: {segment['speaker_id']}")
            print(f"   Original: {segment['text']}")
            
            # Get context for better rewriting
            context = f"This is a professional meeting. Speaker: {data.get('speakers', {}).get(segment['speaker_id'], 'Unknown')}"
            
            # Rewrite the entire text that contains offensive content
            original_text = segment['text']
            
            try:
                print("🔄 Rewriting offensive content...")
                rewritten_text = await content_rewriter.rewrite_offensive_text(
                    original_text, 
                    context
                )
                
                print(f"   Rewritten: {rewritten_text}")
                
                return {
                    'speaker_id': segment['speaker_id'],
                    'original_text': original_text,
                    'rewritten_text': rewritten_text,
                    'start_time': segment.get('start', 0),
                    'end_time': segment.get('end', 0),
                    'offensive_parts': segment['offensive_parts']
                }
                
            except Exception as e:
                print(f"❌ Error rewriting content: {e}")
                # Fallback to simple replacement
                rewritten_text = original_text.replace("fucked", "broken").replace("shit", "poor")
                print(f"   Fallback rewritten: {rewritten_text}")
                
                return {
                    'speaker_id': segment['speaker_id'],
                    'original_text': original_text,
                    'rewritten_text': rewritten_text,
                    'start_time': segment.get('start', 0),
                    'end_time': segment.get('end', 0),
                    'offensive_parts': segment['offensive_parts']
                }
    
    print("ℹ️ No offensive content found in segments")
    return None

async def test_elevenlabs_generation():
    """Test ElevenLabs voice generation with reference audio."""
    print("🧪 ElevenLabs Voice Generation Test")
    print("=" * 50)
    
    # Check if reference audio exists
    reference_audio_path = Path("../Data/reference_audio/reading-from-descartes-discourse-on-method-20113.mp3")
    
    if not reference_audio_path.exists():
        print(f"❌ Reference audio not found: {reference_audio_path}")
        return False
    
    print(f"🎤 Reference audio: {reference_audio_path.name}")
    
    # Load sample data
    sample_data = load_sample_data()
    if not sample_data:
        return False
    
    # Initialize content rewriter (try GroqContentRewriter, fallback to simple replacement)
    content_rewriter = None
    try:
        # Try to load API keys
        config_file = Path("../config/api_keys.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                groq_api_key = config_data.get('groq_api_key')
                if groq_api_key:
                    content_rewriter = GroqContentRewriter(groq_api_key)
                    print("✅ Using GroqContentRewriter")
    except Exception as e:
        print(f"⚠️ Could not initialize GroqContentRewriter: {e}")
    
    # Fallback to simple content rewriter if needed
    if not content_rewriter:
        print("ℹ️ Using fallback simple content rewriter")
        class SimpleContentRewriter:
            async def rewrite_offensive_text(self, text: str, context: str) -> str:
                replacements = {
                    "completely fucked": "completely broken",
                    "fucking": "really",
                    "shit": "poor", 
                    "damn": "very",
                    "crap": "junk",
                    "fucked": "broken"
                }
                result = text
                for bad, good in replacements.items():
                    result = result.replace(bad, good)
                return result
        content_rewriter = SimpleContentRewriter()
    
    # Find and rewrite offensive content
    target_segment = await rewrite_offensive_content(sample_data, content_rewriter)
    if not target_segment:
        print("❌ No suitable segment found for testing")
        return False
    
    # Create output directory for test
    output_dir = Path("../Data/generated_audio/test_elevenlabs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"test_segment_{target_segment['speaker_id']}.mp3"
    
    try:
        print(f"\n🎵 Initializing ElevenLabs voice generator...")
        print(f"🎯 Step 3: Cloning voice from reference audio...")
        
        # Load ElevenLabs API key from config
        api_key = None
        try:
            config_file = Path("../config/api_keys.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                    api_key = config_data.get('elevenlabs_api_key')
        except Exception as e:
            print(f"⚠️ Could not load API key: {e}")
            return False
        
        if not api_key:
            print("❌ ElevenLabs API key not found in config")
            return False
        
        # Create voice configuration
        voice_config = create_voice_config(
            elevenlabs_api_key=api_key,
            backend='elevenlabs',
            quality='high'
        )
        
        # Initialize the advanced voice generator with reference audio
        voice_generator = AdvancedVoiceGenerator(
            reference_audio_path=str(reference_audio_path),
            config=voice_config
        )
        
        print(f"� Step 4: Generating audio for rewritten sentence...")
        print(f"📝 Text: '{target_segment['rewritten_text'][:80]}{'...' if len(target_segment['rewritten_text']) > 80 else ''}'")
        print(f"📊 Length: {len(target_segment['rewritten_text'])} characters")
        
        # Generate the audio using ElevenLabs with cloned voice
        success = voice_generator.generate_audio(
            text=target_segment['rewritten_text'],
            output_path=str(output_file)
        )
        
        if success and output_file.exists():
            file_size = output_file.stat().st_size
            print(f"\n🎉 SUCCESS! Test completed successfully!")
            print("=" * 50)
            print(f"📁 Output file: {output_file}")
            print(f"📏 File size: {file_size:,} bytes")
            print(f"🎭 Speaker: {target_segment['speaker_id']}")
            print(f"📝 Original: {target_segment['original_text'][:100]}{'...' if len(target_segment['original_text']) > 100 else ''}")
            print(f"✏️  Rewritten: {target_segment['rewritten_text'][:100]}{'...' if len(target_segment['rewritten_text']) > 100 else ''}")
            
            # Show offensive parts that were cleaned
            if target_segment.get('offensive_parts'):
                print("🧹 Cleaned offensive content:")
                for i, part in enumerate(target_segment['offensive_parts'][:3], 1):  # Show max 3
                    print(f"   {i}. '{part.get('text', 'N/A')}' (severity: {part.get('severity', 'unknown')})")
            
            # Try to play the audio (optional)
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(str(output_file))
                print(f"\n🔊 Playing generated audio...")
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)
                
                print("✅ Playback completed!")
                
            except ImportError:
                print("\nℹ️ Install pygame to auto-play the generated audio: pip install pygame")
            except Exception as e:
                print(f"\nℹ️ Could not play audio automatically: {e}")
            
            return True
        else:
            print("❌ Audio generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    print("🚀 ElevenLabs Voice Cloning & Content Rewriting Test")
    print("=" * 60)
    print("This test will:")
    print("1. 📁 Load data with offensive content")
    print("2. ✏️  Rewrite offensive parts using AI/fallback")
    print("3. 🎤 Clone voice from reference audio")
    print("4. 🔊 Generate rewritten sentence with cloned voice")
    print("=" * 60)
    
    print(f"📂 Working directory: {os.getcwd()}")
    
    # Check if we're in the right directory
    if not Path("../Data").exists():
        print("❌ Please run this script from the NegativeOutputHandling/Code directory")
        sys.exit(1)
    
    # Run the async test
    success = await test_elevenlabs_generation()
    
    if success:
        print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
        print("Check the generated audio file in ../Data/generated_audio/test_elevenlabs/")
    else:
        print("\n💥 Test failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())