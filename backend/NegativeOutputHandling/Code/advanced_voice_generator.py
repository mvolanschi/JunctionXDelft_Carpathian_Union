"""
Advanced Voice Generator with Voice Cloning Support
Supports multiple backends: ElevenLabs, Coqui TTS, and fallback to enhanced pyttsx3
"""

import os
import asyncio
from pathlib import Path
import tempfile
from typing import Optional, Dict, Any
import json
import requests

class AdvancedVoiceGenerator:
    # Class-level variables for voice reuse across instances
    _shared_voice_id = None
    _shared_client = None
    _voice_cloned = False
    
    def __init__(self, reference_audio_path: str = None, config: Dict[str, Any] = None):
        self.reference_audio_path = reference_audio_path
        self.config = config or {}
        self.voice_id = None  # For ElevenLabs cloned voice
        
        # Load configuration
        self.elevenlabs_api_key = self.config.get('elevenlabs_api_key') or os.getenv('ELEVENLABS_API_KEY')
        self.preferred_backend = self.config.get('backend', 'auto')  # 'elevenlabs', 'coqui', 'pyttsx3', 'auto'
        
    def setup_elevenlabs_voice(self) -> bool:
        """Clone voice using ElevenLabs API (once per session)"""
        if not self.elevenlabs_api_key:
            print("   ⚠️ ElevenLabs API key not found")
            return False
            
        if not self.reference_audio_path or not os.path.exists(self.reference_audio_path):
            print("   ⚠️ Reference audio file not found")
            return False
        
        # Check if voice already cloned and reuse it
        if AdvancedVoiceGenerator._voice_cloned and AdvancedVoiceGenerator._shared_voice_id:
            self.voice_id = AdvancedVoiceGenerator._shared_voice_id
            print(f"   ♻️ Reusing cloned voice: {self.voice_id[:8]}... (saves credits!)")
            return True
            
        try:
            from elevenlabs import ElevenLabs
            
            client = ElevenLabs(api_key=self.elevenlabs_api_key)
            AdvancedVoiceGenerator._shared_client = client
            
            print(f"   🎤 Cloning voice from: {os.path.basename(self.reference_audio_path)} (ONCE for all audio)")
            
            # Clone the voice using Instant Voice Cloning API
            with open(self.reference_audio_path, 'rb') as audio_file:
                voice = client.voices.ivc.create(
                    name=f"session_voice_{int(__import__('time').time())}",
                    description="Single voice clone for entire session",
                    files=[audio_file]
                )
            
            # Store voice globally for reuse
            AdvancedVoiceGenerator._shared_voice_id = voice.voice_id
            AdvancedVoiceGenerator._voice_cloned = True
            self.voice_id = voice.voice_id
            
            print(f"   ✅ Voice cloned successfully! ID: {self.voice_id[:8]}... (will reuse for ALL sentences)")
            return True
            
        except Exception as e:
            print(f"   ❌ ElevenLabs voice cloning failed: {e}")
            return False
    
    def generate_with_elevenlabs(self, text: str, output_path: str) -> bool:
        """Generate audio using ElevenLabs cloned voice"""
        try:
            from elevenlabs import ElevenLabs
            
            if not self.voice_id:
                if not self.setup_elevenlabs_voice():
                    return False
            
            print(f"   🎵 Generating with ElevenLabs (voice: {self.voice_id[:8]}...) - {len(text)} chars")
            
            # Try to use existing voice instead of cloned if credits are low
            client = ElevenLabs(api_key=self.elevenlabs_api_key)
            
            # Generate audio with cloned voice
            audio_generator = client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",  # High quality model
                output_format="mp3_44100_128"
            )
            
            # Save the audio
            with open(output_path, 'wb') as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            print(f"   ✅ ElevenLabs audio generated: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            print(f"   ❌ ElevenLabs generation failed: {e}")
            return False
    
    def setup_coqui_tts(self) -> bool:
        """Setup Coqui TTS with voice cloning"""
        try:
            # Check if TTS is installed
            try:
                import TTS
                from TTS.api import TTS
            except ImportError:
                print("   📦 Installing Coqui TTS...")
                import subprocess
                subprocess.check_call(["pip", "install", "TTS"])
                import TTS
                from TTS.api import TTS
            
            # Initialize XTTS model for voice cloning
            print("   🤖 Loading Coqui XTTS model (this may take a moment)...")
            self.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            print("   ✅ Coqui TTS model loaded successfully")
            return True
            
        except Exception as e:
            print(f"   ❌ Coqui TTS setup failed: {e}")
            return False
    
    def generate_with_coqui(self, text: str, output_path: str) -> bool:
        """Generate audio using Coqui TTS voice cloning"""
        try:
            if not hasattr(self, 'tts_model'):
                if not self.setup_coqui_tts():
                    return False
            
            print(f"   🎵 Generating with Coqui TTS voice cloning...")
            
            # Generate with voice cloning
            self.tts_model.tts_to_file(
                text=text,
                file_path=output_path,
                speaker_wav=self.reference_audio_path,
                language="en"
            )
            
            print(f"   ✅ Coqui TTS audio generated: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            print(f"   ❌ Coqui TTS generation failed: {e}")
            return False
    
    def generate_with_enhanced_pyttsx3(self, text: str, output_path: str) -> bool:
        """Enhanced pyttsx3 as fallback (same as before but with better voice selection)"""
        try:
            import pyttsx3
            import librosa
            import numpy as np
            
            # Analyze reference audio (reuse existing logic)
            characteristics = self._analyze_reference_audio()
            
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            # Enhanced voice selection logic
            best_voice = self._select_best_voice(voices, characteristics)
            
            if best_voice:
                engine.setProperty('voice', best_voice.id)
                engine.setProperty('rate', characteristics.get('rate', 180))
                engine.setProperty('volume', characteristics.get('volume', 0.9))
                
                engine.save_to_file(text, output_path)
                engine.runAndWait()
                
                print(f"   ✅ Enhanced pyttsx3 audio generated: {os.path.basename(output_path)}")
                return True
            
            return False
            
        except Exception as e:
            print(f"   ❌ Enhanced pyttsx3 failed: {e}")
            return False
    
    def generate_audio(self, text: str, output_path: str) -> bool:
        """
        Generate audio using the best available method
        Priority: ElevenLabs > Coqui TTS > Enhanced pyttsx3
        """
        
        if self.preferred_backend == 'elevenlabs' or self.preferred_backend == 'auto':
            if self.elevenlabs_api_key:
                print(f"   🎤 Trying ElevenLabs voice cloning...")
                if self.generate_with_elevenlabs(text, output_path):
                    return True
                print(f"   ⚠️ ElevenLabs failed, trying next method...")
        
        if self.preferred_backend == 'coqui' or self.preferred_backend == 'auto':
            if self.reference_audio_path:
                print(f"   🎤 Trying Coqui TTS voice cloning...")
                if self.generate_with_coqui(text, output_path):
                    return True
                print(f"   ⚠️ Coqui TTS failed, trying next method...")
        
        if self.preferred_backend == 'pyttsx3' or self.preferred_backend == 'auto':
            print(f"   🎤 Falling back to enhanced pyttsx3...")
            return self.generate_with_enhanced_pyttsx3(text, output_path)
        
        print(f"   ❌ All voice generation methods failed")
        return False
    
    def _analyze_reference_audio(self) -> Dict[str, Any]:
        """Analyze reference audio (reuse existing implementation)"""
        try:
            import librosa
            import numpy as np
            
            if not self.reference_audio_path or not os.path.exists(self.reference_audio_path):
                return {'pitch': 150, 'rate': 180, 'volume': 0.9, 'gender': 'unknown'}
            
            # Load reference audio
            audio, sr = librosa.load(self.reference_audio_path, sr=22050)
            
            # Use the same autocorrelation pitch detection as before
            def autocorr_pitch_detection(signal, sr):
                # Simplified version of the robust pitch detection
                frame_size = int(0.05 * sr)
                hop_size = int(0.025 * sr)
                f0_values = []
                
                for start in range(0, len(signal) - frame_size, hop_size):
                    frame = signal[start:start + frame_size]
                    windowed = frame * np.hamming(len(frame))
                    
                    if np.max(np.abs(windowed)) > 0:
                        windowed = windowed / np.max(np.abs(windowed))
                        
                        autocorr = np.correlate(windowed, windowed, mode='full')
                        autocorr = autocorr[len(autocorr)//2:]
                        
                        min_lag = int(sr / 400)
                        max_lag = int(sr / 50)
                        
                        if max_lag < len(autocorr):
                            search_range = autocorr[min_lag:max_lag]
                            if len(search_range) > 0:
                                peak_lag = np.argmax(search_range) + min_lag
                                f0 = sr / peak_lag
                                
                                peak_value = autocorr[peak_lag]
                                max_value = autocorr[0]
                                
                                if max_value > 0 and peak_value / max_value > 0.3:
                                    if 50 <= f0 <= 400:
                                        f0_values.append(f0)
                
                return f0_values
            
            f0_values = autocorr_pitch_detection(audio, sr)
            
            if len(f0_values) > 5:
                avg_pitch = np.median(f0_values)
            else:
                avg_pitch = 150
            
            # Gender detection
            gender = "male" if avg_pitch < 160 else "female"
            
            # Speech rate estimation
            estimated_rate = max(120, min(250, 200 - (avg_pitch - 150) * 0.3))
            
            return {
                'pitch': float(avg_pitch),
                'rate': int(estimated_rate),
                'volume': 0.9,
                'gender': gender
            }
            
        except Exception as e:
            print(f"   ⚠️ Reference analysis failed: {e}")
            return {'pitch': 150, 'rate': 180, 'volume': 0.9, 'gender': 'unknown'}
    
    def _select_best_voice(self, voices, characteristics):
        """Select best voice from available system voices (fallback logic)"""
        target_gender = characteristics.get('gender', 'unknown')
        
        # Filter by gender
        gender_filtered = []
        for voice in voices:
            voice_name = voice.name.lower()
            if target_gender == 'male':
                if any(keyword in voice_name for keyword in ['david', 'mark', 'male', 'man']):
                    gender_filtered.append(voice)
            elif target_gender == 'female':
                if any(keyword in voice_name for keyword in ['zira', 'hazel', 'female', 'woman']):
                    gender_filtered.append(voice)
        
        # If no gender-specific voices found, use any available
        if not gender_filtered:
            gender_filtered = voices
        
        # Return the first suitable voice
        return gender_filtered[0] if gender_filtered else voices[0] if voices else None
    
    @classmethod
    def cleanup_session_voice(cls):
        """Clean up the shared cloned voice at the end of session"""
        try:
            if cls._shared_client and cls._shared_voice_id and cls._voice_cloned:
                print(f"🧹 Cleaning up session voice: {cls._shared_voice_id[:8]}...")
                cls._shared_client.voices.delete(cls._shared_voice_id)
                print(f"   ✅ Session voice deleted successfully")
                cls._shared_voice_id = None
                cls._voice_cloned = False
                cls._shared_client = None
        except Exception as e:
            print(f"   ⚠️ Could not delete session voice: {e}")

def create_voice_config(
    elevenlabs_api_key: str = None,
    backend: str = 'auto',
    quality: str = 'high'
) -> Dict[str, Any]:
    """Create configuration for voice generation"""
    return {
        'elevenlabs_api_key': elevenlabs_api_key,
        'backend': backend,  # 'elevenlabs', 'coqui', 'pyttsx3', 'auto'
        'quality': quality   # 'high', 'medium', 'fast'
    }

# Example usage and configuration
if __name__ == "__main__":
    # Test the advanced voice generator
    config = create_voice_config(backend='auto')
    
    reference_audio = "../Data/reference_audio/reading-from-descartes-discourse-on-method-20113.mp3"
    
    if os.path.exists(reference_audio):
        generator = AdvancedVoiceGenerator(reference_audio, config)
        
        test_text = "Hello, this is a test of the advanced voice cloning system."
        output_file = "test_advanced_voice.wav"
        
        success = generator.generate_audio(test_text, output_file)
        
        if success:
            print(f"✅ Test successful! Generated: {output_file}")
        else:
            print("❌ Test failed")
    else:
        print("❌ Reference audio not found for testing")