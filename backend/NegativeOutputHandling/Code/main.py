"""
Main entry point for the speech processing system.
"""

import os
import asyncio
from pathlib import Path

from content_rewriter import GroqContentRewriter
from voice_generator import VoiceCloneGenerator, SimpleVoiceGenerator
from processor import SpeechProcessor
from utils import load_transcription, save_transcription, get_available_files


async def main():
    """Main processing function."""
    # Get API keys
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    if not groq_api_key:
        print("Please set GROQ_API_KEY environment variable (free at https://console.groq.com/)")
        return
    
    print("🤖 Using Groq (Llama 3.1) for intelligent content rewriting")
    
    # Ask user to select transcription file
    print("\n📁 Available transcription files:")
    print("   1. input_transcription.json (realistic meeting with offensive content)")
    print("   2. expanded_input_transcription.json (same content - alternative file)")
    
    choice = input("\nSelect transcription file (1-2): ").strip()
    transcription_files = {
        "1": "../Data/example_jsons/input_transcription.json",
        "2": "../Data/example_jsons/expanded_input_transcription.json"
    }
    
    transcription_file = transcription_files.get(choice, "example_jsons/input_transcription.json")
    print(f"📄 Using: {transcription_file}")
    
    # Ask user if they want voice recreation
    enable_voice = input("\n🎤 Enable voice recreation? (y/n): ").lower().strip() == 'y'
    
    # Load transcription
    transcription = load_transcription(Path(transcription_file))
    audio_file = Path("input_audio.wav")
    
    if enable_voice:
        print("🎤 Voice recreation: ENABLED - Will analyze and recreate voices")
        content_rewriter = GroqContentRewriter(groq_api_key)
        voice_generator = VoiceCloneGenerator()
        processor = SpeechProcessor(content_rewriter, voice_generator)
        
        # Analyze original audio if voice recreation is enabled
        if audio_file.exists():
            await voice_generator.analyze_original_voice(audio_file, transcription.segments)
        else:
            print("   ⚠️ input_audio.wav not found - voice analysis skipped")
    else:
        print("🎤 Voice recreation: ENABLED with reference audio - Will use reference voice")
        content_rewriter = GroqContentRewriter(groq_api_key)
        voice_generator = SimpleVoiceGenerator()
        processor = SpeechProcessor(content_rewriter, voice_generator)
    
    # Process
    print("📝 Processing transcription with offensive content...")
    processed = await processor.process_transcription(transcription, audio_file)
    
    # Save results to run-specific folder
    transcription_path = voice_generator.get_transcription_path()
    save_transcription(processed, transcription_path)
    
    # Print summary
    total_segments = len(processed.segments)
    flagged_segments = sum(1 for seg in processed.segments if seg.offensive_parts)
    changed_segments = sum(1 for seg in processed.segments if hasattr(seg, 'was_modified') and seg.was_modified)
    unchanged_segments = total_segments - changed_segments
    total_offensive_parts = sum(len(seg.offensive_parts) for seg in processed.segments)
    
    print(f"\n✅ Processing complete!")
    print(f"📊 Summary:")
    print(f"   • Total segments: {total_segments}")
    print(f"   • Segments with offensive content: {flagged_segments}")
    print(f"   • Segments actually changed: {changed_segments}")
    print(f"   • Segments unchanged (clean): {unchanged_segments}")
    print(f"   • Total offensive parts rewritten: {total_offensive_parts}")
    print(f"   • Results saved to: {transcription_path}")
    
    # Show generated audio files for changed sentences only
    generated_files = []
    for seg in processed.segments:
        # Collect from both single file and multiple files fields
        if hasattr(seg, 'generated_audio_files') and seg.generated_audio_files:
            for audio_file in seg.generated_audio_files:
                if audio_file and audio_file.exists():
                    generated_files.append(audio_file)
        elif hasattr(seg, 'generated_audio_file') and seg.generated_audio_file and seg.generated_audio_file.exists():
            generated_files.append(seg.generated_audio_file)
            
    if generated_files:
        # Get run folder from first generated file (now it might be nested in segment folders)
        first_file = generated_files[0]
        if first_file.parent.name.startswith('segment_'):
            run_folder = first_file.parent.parent  # Go up two levels: sentence -> segment -> run
            run_name = run_folder.name
        else:
            run_folder = first_file.parent
            run_name = run_folder.name
        
        print(f"\n🎵 Generated audio files (ORGANIZED by segment):")
        
        # Group files by segment folder
        segment_groups = {}
        for audio_file in generated_files:
            if audio_file.parent.name.startswith('segment_'):
                segment_name = audio_file.parent.name
                if segment_name not in segment_groups:
                    segment_groups[segment_name] = []
                segment_groups[segment_name].append(audio_file)
            else:
                # Fallback for old structure
                if 'unsorted' not in segment_groups:
                    segment_groups['unsorted'] = []
                segment_groups['unsorted'].append(audio_file)
        
        # Display organized by segment
        for segment_name, files in segment_groups.items():
            print(f"   📁 {segment_name}:")
            for audio_file in files:
                print(f"      🔊 {audio_file.name}")
        
        print(f"\n📂 Run folder: generated_audio/{run_name}/")
        print(f"   📊 Contains {len(generated_files)} individual sentence audio files")
        print(f"   🗂️ Organized in {len(segment_groups)} segment folders")
        print(f"   ✨ Each file represents ONE changed sentence")
        print(f"   ℹ️ Unchanged sentences within segments are skipped")
        print(f"\n💡 Next steps:")
        print(f"   1. Each segment folder contains only its changed sentences")
        print(f"   2. Unchanged sentences can use original audio")
        print(f"   3. Use audio editing to replace only the specific changed sentences")
    else:
        print(f"\n🔇 No audio files generated (voice synthesis disabled or failed)")
    
    # Clean up any cloned voices at the end
    try:
        from advanced_voice_generator import AdvancedVoiceGenerator
        AdvancedVoiceGenerator.cleanup_session_voice()
    except Exception:
        pass  # Cleanup is optional


if __name__ == "__main__":
    asyncio.run(main())