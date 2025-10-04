"""
Main speech processing functionality.
"""

from pathlib import Path
from models import Transcription, TranscriptionSegment
from content_rewriter import ContentRewriter
from voice_generator import VoiceGenerator


class SpeechProcessor:
    def __init__(self, content_rewriter: ContentRewriter, voice_generator: VoiceGenerator):
        self.content_rewriter = content_rewriter
        self.voice_generator = voice_generator
    
    async def process_transcription(self, transcription: Transcription, audio_file: Path) -> Transcription:
        """Process transcription to remove offensive content."""
        
        changed_segments = []  # Track which segments actually changed
        
        for segment in transcription.segments:
            if not segment.offensive_parts:
                # Mark clean segments as unchanged
                segment.was_modified = False
                continue
                
            # Store original text for comparison
            original_text = segment.text
            
            # Get context from surrounding segments
            context = self._get_context(segment, transcription)
            
            # Process all offensive parts for this segment
            updated_text = segment.text
            
            # Sort offensive parts by position (start time) to process in order
            sorted_offensive_parts = sorted(segment.offensive_parts, 
                                           key=lambda x: x.time_range.start, reverse=True)
            
            # Process from end to beginning to avoid position shifts
            for offensive_part in sorted_offensive_parts:
                rewritten = await self.content_rewriter.rewrite_offensive_text(
                    offensive_part.original_text, 
                    context
                )
                offensive_part.rewritten_text = rewritten
                
                # Update the main text
                updated_text = updated_text.replace(
                    offensive_part.original_text, 
                    rewritten
                )
            
            # Check if text actually changed
            text_changed = updated_text != original_text
            segment.was_modified = text_changed
            
            # Update segment text
            segment.text = updated_text
            
            # Show before/after comparison
            print(f"\n🔄 Speaker {segment.speaker_id}:")
            print(f"   BEFORE: {original_text}")
            print(f"   AFTER:  {segment.text}")
            
            # Only generate audio for segments that actually changed
            if text_changed:
                changed_segments.append(segment)
                
                # Split the segment into individual sentences and generate audio for each
                sentences = self._split_into_sentences(segment.text)
                original_sentences = self._split_into_sentences(original_text)
                
                segment.generated_audio_files = []  # Store multiple audio files
                
                # Generate audio for each sentence that was changed
                for i, (original_sentence, new_sentence) in enumerate(zip(original_sentences, sentences)):
                    # Only generate audio if this specific sentence changed
                    if original_sentence.strip() != new_sentence.strip() and new_sentence.strip():
                        print(f"   🎵 Generating audio for changed sentence {i+1}: '{new_sentence[:50]}{'...' if len(new_sentence) > 50 else ''}'")
                        
                        generated_audio = await self.voice_generator.generate_audio_for_changed_sentence(
                            new_sentence.strip(), 
                            segment.speaker_id, 
                            audio_file,
                            segment_id=f"{segment.speaker_id}_{segment.time_range.start}_{segment.time_range.end}_sentence_{i+1}"
                        )
                        segment.generated_audio_files.append(generated_audio)
                    else:
                        print(f"   ℹ️ Sentence {i+1} unchanged, skipping audio generation")
                
                # For backward compatibility, store first audio file in the original field
                if segment.generated_audio_files:
                    segment.generated_audio_file = segment.generated_audio_files[0]
                    
            else:
                print(f"   ℹ️ No actual changes made - skipping audio generation")
        
        # Print summary of changed vs unchanged segments
        total_segments = len(transcription.segments)
        changed_count = len(changed_segments)
        unchanged_count = total_segments - changed_count
        
        print(f"\n📊 Processing Summary:")
        print(f"   • Total segments: {total_segments}")
        print(f"   • Changed segments (audio generated): {changed_count}")
        print(f"   • Unchanged segments (no audio needed): {unchanged_count}")
        
        return transcription
    
    def _get_context(self, target_segment: TranscriptionSegment, transcription: Transcription) -> str:
        """Get surrounding context for better rewriting."""
        context_parts = []
        
        for segment in transcription.segments:
            time_diff = abs(segment.time_range.start - target_segment.time_range.start)
            if time_diff <= 10.0 and segment != target_segment:  # 10 second window
                context_parts.append(segment.text)
        
        return " ".join(context_parts)
        
    def _split_into_sentences(self, text: str) -> list:
        """Split text into individual sentences."""
        import re
        
        # Split on sentence endings (., !, ?) followed by space or end of string
        # This is a simple approach - could be enhanced with more sophisticated NLP
        sentences = re.split(r'[.!?]+\s*', text.strip())
        
        # Filter out empty sentences and add back the punctuation
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Add back appropriate punctuation if it was removed
                if not sentence.endswith(('.', '!', '?')):
                    # Try to determine original punctuation from context
                    if '?' in text:
                        sentence += '?'
                    elif '!' in text:
                        sentence += '!'
                    else:
                        sentence += '.'
                result.append(sentence)
        
        # If no sentences were found, return the original text as one sentence
        if not result and text.strip():
            result = [text.strip()]
            
        return result