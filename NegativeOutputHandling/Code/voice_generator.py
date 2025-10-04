"""
Voice generation classes for audio synthesis.
"""

from abc import ABC, abstractmethod
from pathlib import Path
import shutil
from models import VoiceGenerator
from advanced_voice_generator import AdvancedVoiceGenerator, create_voice_config


class VoiceCloneGenerator(VoiceGenerator):
    def __init__(self):
        """Initialize voice cloning system using reference audio."""
        self.voice_profiles = {}  # Store analyzed voice characteristics per speaker
        
        # Set up reference audio path
        self.reference_audio_dir = Path("../Data/reference_audio")
        self.reference_audio_file = self._find_reference_audio()
        
        # Clear existing files from base directories
        self._clear_existing_files()
        
        # Create run folder with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_name = f"run_{timestamp}"
        self.run_folder = Path(f"../Data/generated_audio/{self.run_name}")
        self.run_folder.mkdir(parents=True, exist_ok=True)
        
        # Create output transcriptions folder structure
        self.transcription_folder = Path(f"../Data/output_transcriptions/{self.run_name}")
        self.transcription_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Created run folders:")
        print(f"   🎵 Audio: {self.run_folder}")
        print(f"   📄 Transcriptions: {self.transcription_folder}")
    
    def _clear_existing_files(self):
        """Clear all existing files from the base output directories."""
        base_audio_dir = Path("../Data/generated_audio")
        base_transcription_dir = Path("../Data/output_transcriptions")
        
        # Clear audio directory
        if base_audio_dir.exists():
            for item in base_audio_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        # Clear transcription directory
        if base_transcription_dir.exists():
            for item in base_transcription_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
    
    def _find_reference_audio(self) -> Path:
        """Find the reference audio file in the reference_audio directory."""
        if not self.reference_audio_dir.exists():
            print(f"⚠️ Reference audio directory not found: {self.reference_audio_dir}")
            return None
        
        # Look for common audio file extensions
        audio_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
        for ext in audio_extensions:
            audio_files = list(self.reference_audio_dir.glob(f'*{ext}'))
            if audio_files:
                reference_file = audio_files[0]  # Use first found file
                print(f"🎤 Found reference audio: {reference_file.name}")
                return reference_file
        
        print(f"⚠️ No reference audio file found in {self.reference_audio_dir}")
        return None
    
    def _get_elevenlabs_api_key(self):
        """Get ElevenLabs API key from environment or config."""
        import os
        
        # Try environment variable first
        api_key = os.getenv('ELEVENLABS_API_KEY')
        if api_key:
            return api_key
            
        # Try loading from config file
        config_file = Path("../config/api_keys.json")
        if config_file.exists():
            try:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('elevenlabs_api_key')
            except:
                pass
        
        # No API key found - will fallback to other methods
        return None
    
    def get_transcription_path(self, filename: str = "output_transcription.json") -> Path:
        """Get the path for saving transcription in the run folder."""
        return self.transcription_folder / filename
        
    async def analyze_original_voice(self, audio_file: Path, speaker_segments: list) -> dict:
        """Analyze original voice characteristics for each speaker."""
        print(f"🎤 Analyzing original voice characteristics from {audio_file.name}...")
        
        try:
            import librosa
            import numpy as np
            
            # Load the original audio file
            audio, sr = librosa.load(audio_file, sr=None)
            
            voice_profile = {}
            
            for segment in speaker_segments:
                speaker_id = segment.speaker_id
                start_time = segment.time_range.start
                end_time = segment.time_range.end
                
                # Extract audio segment for this speaker
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                speaker_audio = audio[start_sample:end_sample]
                
                if len(speaker_audio) > 0:
                    # Analyze voice characteristics
                    voice_features = self._extract_voice_features(speaker_audio, sr)
                    
                    if speaker_id not in voice_profile:
                        voice_profile[speaker_id] = []
                    voice_profile[speaker_id].append(voice_features)
                    
            # Average the features for each speaker
            for speaker_id in voice_profile:
                if voice_profile[speaker_id]:
                    avg_features = self._average_features(voice_profile[speaker_id])
                    self.voice_profiles[speaker_id] = avg_features
                    print(f"   📊 Analyzed voice profile for {speaker_id}")
                    
            return self.voice_profiles
            
        except ImportError:
            print("   ⚠️ librosa not installed. Install with: pip install librosa")
            return {}
        except Exception as e:
            print(f"   ⚠️ Voice analysis failed: {e}")
            return {}
    
    def _extract_voice_features(self, audio, sr):
        """Extract voice characteristics like pitch, tone, etc."""
        try:
            import librosa
            import numpy as np
            
            # Extract fundamental frequency (pitch)
            pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            avg_pitch = np.mean(pitch_values) if pitch_values else 0
            
            # Extract spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            avg_spectral_centroid = np.mean(spectral_centroids)
            
            # Extract MFCC features (voice timbre)
            mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            avg_mfccs = np.mean(mfccs, axis=1)
            
            return {
                'pitch': avg_pitch,
                'spectral_centroid': avg_spectral_centroid,
                'mfccs': avg_mfccs.tolist(),
                'duration': len(audio) / sr
            }
            
        except Exception as e:
            print(f"Feature extraction failed: {e}")
            return {'pitch': 0, 'spectral_centroid': 0, 'mfccs': [], 'duration': 0}
    
    def _average_features(self, feature_list):
        """Average multiple feature extractions for a speaker."""
        import numpy as np
        
        if not feature_list:
            return {}
            
        avg_features = {
            'pitch': np.mean([f['pitch'] for f in feature_list if f['pitch'] > 0]),
            'spectral_centroid': np.mean([f['spectral_centroid'] for f in feature_list]),
            'mfccs': np.mean([f['mfccs'] for f in feature_list if f['mfccs']], axis=0).tolist() if any(f['mfccs'] for f in feature_list) else [],
            'total_duration': sum([f['duration'] for f in feature_list])
        }
        
        return avg_features
    
    async def generate_audio(self, text: str, speaker_id: str, original_audio_file: Path) -> Path:
        """Generate new audio for edited text using voice cloning."""
        print(f"🎤 Generating voice-matched audio for {speaker_id}: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Create output filename for this specific segment in run folder
        import time
        timestamp = int(time.time() * 1000)  # milliseconds for uniqueness
        
        output_file = self.run_folder / f"segment_{timestamp}.wav"
        
        # Check if we have voice profile for this speaker
        if speaker_id not in self.voice_profiles:
            print(f"   ⚠️ No voice profile found for {speaker_id}, using default voice")
            return await self._generate_default_voice(text, output_file)
        
        voice_profile = self.voice_profiles[speaker_id]
        print(f"   📊 Using voice profile - Pitch: {voice_profile.get('pitch', 0):.1f}Hz")
        
        # Generate voice-matched audio
        success = await self._generate_voice_matched_audio(text, voice_profile, output_file)
        
        if success and output_file.exists():
            print(f"   ✅ Generated: {output_file.name}")
            return output_file
        else:
            print(f"   ❌ Generation failed")
            return original_audio_file
    
    async def _generate_voice_matched_audio(self, text: str, voice_profile: dict, audio_file: Path) -> bool:
        """Generate voice-matched audio using available TTS systems."""
        try:
            print("   🔄 Generating voice-matched TTS...")
            
            # Try pyttsx3 first (built-in)
            try:
                import pyttsx3
                
                engine = pyttsx3.init()
                
                # Adjust voice properties based on analyzed profile
                voices = engine.getProperty('voices')
                if voices and voice_profile:
                    target_pitch = voice_profile.get('pitch', 0)
                    if target_pitch > 180:  # Higher pitch, likely female voice
                        for voice in voices:
                            if any(keyword in voice.name.lower() for keyword in ['female', 'zira', 'hazel']):
                                engine.setProperty('voice', voice.id)
                                break
                    else:  # Lower pitch, likely male voice
                        for voice in voices:
                            if any(keyword in voice.name.lower() for keyword in ['male', 'david', 'mark']):
                                engine.setProperty('voice', voice.id)
                                break
                
                # Adjust speech rate based on original characteristics
                rate = engine.getProperty('rate')
                engine.setProperty('rate', max(150, min(250, rate)))
                
                # Generate audio to the specified output file
                engine.save_to_file(text, str(audio_file))
                engine.runAndWait()
                
                if audio_file.exists():
                    print(f"   ✅ Generated voice-matched audio: {audio_file.name}")
                    return True
                    
            except Exception as e:
                print(f"   ⚠️ pyttsx3 failed: {e}")
            
            # Fallback: Try gTTS (Google Text-to-Speech)
            try:
                from gtts import gTTS
                
                tts = gTTS(text=text, lang='en', slow=False)
                # Generate to output file (gTTS creates .mp3, so we change extension)
                output_mp3 = audio_file.with_suffix('.mp3') 
                tts.save(str(output_mp3))
                
                print(f"   ✅ Generated audio with gTTS: {output_mp3.name}")
                return True
                
            except Exception as e:
                print(f"   ⚠️ gTTS failed: {e}")
            
            return False
            
        except Exception as e:
            print(f"   ❌ Voice generation failed: {e}")
            return False
    
    async def _generate_with_reference_voice(self, text: str, output_file: Path) -> bool:
        """Generate speech using advanced voice cloning and reference audio analysis."""
        try:
            print(f"   🔄 Advanced voice cloning with reference analysis...")
            
            # Method 1: Try Advanced Voice Generator with voice cloning
            try:
                # Create configuration for advanced voice generation
                config = create_voice_config(
                    elevenlabs_api_key=self._get_elevenlabs_api_key(),
                    backend='auto',  # Try ElevenLabs, then Coqui, then enhanced pyttsx3
                    quality='high'
                )
                
                # Initialize advanced voice generator
                advanced_gen = AdvancedVoiceGenerator(
                    reference_audio_path=str(self.reference_audio_file),
                    config=config
                )
                
                # Generate audio using advanced voice cloning
                if advanced_gen.generate_audio(text, str(output_file)):
                    print(f"   ✅ Advanced voice cloning successful: {output_file.name}")
                    return True
                
            except Exception as e:
                print(f"   ⚠️ Advanced voice cloning failed: {e}")
            
            # Method 2: Fallback to enhanced analysis with pyttsx3
            print(f"   🔄 Falling back to enhanced voice analysis...")
            
            # Analyze reference audio to determine voice characteristics
            voice_characteristics = await self._analyze_reference_audio()
            
            # Enhanced pyttsx3 with voice matching based on reference analysis
            try:
                print(f"   🎭 Matching voice characteristics to reference...")
                import pyttsx3
                
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                
                if voices:
                    selected_voice = self._select_best_matching_voice(voices, voice_characteristics)
                    engine.setProperty('voice', selected_voice['id'])
                    
                    # Enhanced speech parameters for more realistic output
                    rate = voice_characteristics.get('rate', 180)
                    # Make rate more natural and closer to human speech
                    natural_rate = max(150, min(200, rate))
                    engine.setProperty('rate', natural_rate)
                    
                    # Adjust volume for clarity
                    engine.setProperty('volume', 0.95)
                    
                    print(f"   🎤 Selected voice: {selected_voice['name']} ({selected_voice['gender']})")
                    print(f"   ⚙️ Rate: {natural_rate}, Volume: 0.95, Gender: {voice_characteristics.get('gender', 'unknown')}")
                
                engine.save_to_file(text, str(output_file))
                engine.runAndWait()
                
                print(f"   ✅ Generated realistic voice-matched audio: {output_file.name}")
                return True
                
            except Exception as e:
                print(f"   ⚠️ Enhanced pyttsx3 failed: {e}, trying spectral matching...")
            
            # Method 2: Spectral matching approach using librosa and torch
            try:
                print(f"   🎭 Attempting spectral voice matching...")
                
                # Generate base TTS first
                base_tts_file = output_file.with_suffix('.tmp.wav')
                
                # Create basic TTS
                from gtts import gTTS
                tts = gTTS(text=text, lang='en', slow=False)
                tts.save(str(base_tts_file))
                
                # Apply spectral matching to make it sound more like reference
                success = await self._apply_spectral_matching(base_tts_file, output_file, voice_characteristics)
                
                # Clean up temp file
                if base_tts_file.exists():
                    base_tts_file.unlink()
                
                if success:
                    print(f"   ✅ Generated spectrally-matched audio: {output_file.name}")
                    return True
                else:
                    raise Exception("Spectral matching failed")
                    
            except Exception as e:
                print(f"   ⚠️ Spectral matching failed: {e}, using enhanced TTS...")
            
            # Method 3: Fallback to enhanced gTTS with pitch adjustment
            try:
                print(f"   � Using enhanced gTTS with voice characteristics...")
                
                from gtts import gTTS
                tts = gTTS(text=text, lang='en', slow=False)
                
                # Save to temporary file for processing
                temp_file = output_file.with_suffix('.tmp.wav')
                tts.save(str(temp_file))
                
                # Apply pitch and speed adjustments based on reference
                await self._apply_voice_adjustments(temp_file, output_file, voice_characteristics)
                
                # Clean up temp file
                if temp_file.exists():
                    temp_file.unlink()
                
                print(f"   ✅ Generated enhanced TTS with voice adjustments: {output_file.name}")
                return True
                
            except Exception as e:
                print(f"   ⚠️ Enhanced gTTS failed: {e}, using basic TTS...")
            
            # Method 4: Basic fallback with reference characteristics info
            try:
                gender = voice_characteristics.get('gender', 'unknown')
                pitch = voice_characteristics.get('pitch', 'unknown')
                print(f"   ⚠️ Using basic gTTS (detected: {gender} voice, {pitch:.1f}Hz pitch)")
                from gtts import gTTS
                
                # Use slower speech for male voices to sound more natural
                use_slow = gender == 'male'
                tts = gTTS(text=text, lang='en', slow=use_slow)
                tts.save(str(output_file))
                
                print(f"   ⚠️ Generated basic TTS with {gender} voice characteristics: {output_file.name}")
                return True
                
            except Exception as e:
                print(f"   ❌ All TTS methods failed: {e}")
                return False
                
        except Exception as e:
            print(f"   ❌ Reference voice generation failed: {e}")
            return False
    
    async def _analyze_reference_audio(self) -> dict:
        """Analyze reference audio to extract voice characteristics."""
        try:
            import librosa
            import numpy as np
            
            # Load reference audio
            audio, sr = librosa.load(self.reference_audio_file, sr=22050)
            
            # Extract features with robust fundamental frequency detection
            # 1. Fundamental frequency (pitch) - using autocorrelation for accurate f0 detection
            try:
                def autocorr_pitch_detection(signal, sr, min_f0=50, max_f0=400):
                    """Use autocorrelation to find the fundamental frequency, avoiding harmonics."""
                    # Pre-emphasize signal to enhance pitch periodicity
                    preemphasized = np.append(signal[0], signal[1:] - 0.97 * signal[:-1])
                    
                    # Window size for analysis (50ms windows with 25ms overlap)
                    frame_size = int(0.05 * sr)  # 50ms
                    hop_size = int(0.025 * sr)   # 25ms
                    
                    f0_values = []
                    
                    for start in range(0, len(preemphasized) - frame_size, hop_size):
                        frame = preemphasized[start:start + frame_size]
                        
                        # Apply Hamming window
                        windowed = frame * np.hamming(len(frame))
                        
                        # Normalize to prevent overflow
                        if np.max(np.abs(windowed)) > 0:
                            windowed = windowed / np.max(np.abs(windowed))
                        
                        # Autocorrelation
                        autocorr = np.correlate(windowed, windowed, mode='full')
                        autocorr = autocorr[len(autocorr)//2:]
                        
                        # Define lag range for expected f0
                        min_lag = int(sr / max_f0)  # 400Hz -> minimum lag
                        max_lag = int(sr / min_f0)  # 50Hz -> maximum lag
                        
                        if max_lag < len(autocorr):
                            # Look for maximum in the valid lag range
                            search_range = autocorr[min_lag:max_lag]
                            
                            if len(search_range) > 0:
                                # Find the peak
                                peak_lag = np.argmax(search_range) + min_lag
                                
                                # Convert lag to frequency
                                f0 = sr / peak_lag
                                
                                # Additional validation: check if this is a strong periodic signal
                                peak_value = autocorr[peak_lag]
                                max_value = autocorr[0]  # Value at zero lag
                                
                                # Require minimum periodicity strength
                                if max_value > 0 and peak_value / max_value > 0.3:  # At least 30% correlation
                                    if min_f0 <= f0 <= max_f0:
                                        f0_values.append(f0)
                    
                    return f0_values
                
                # Get fundamental frequency using autocorrelation
                f0_values = autocorr_pitch_detection(audio, sr)
                
                if len(f0_values) > 5:  # Need at least some good estimates
                    # Remove outliers using robust statistics
                    f0_array = np.array(f0_values)
                    median_f0 = np.median(f0_array)
                    mad = np.median(np.abs(f0_array - median_f0))  # Median Absolute Deviation
                    
                    # Filter using median ± 2*MAD (robust outlier detection)
                    if mad > 0:
                        lower_bound = median_f0 - 3 * mad
                        upper_bound = median_f0 + 3 * mad
                        filtered_f0 = f0_array[(f0_array >= lower_bound) & (f0_array <= upper_bound)]
                    else:
                        filtered_f0 = f0_array
                    
                    if len(filtered_f0) > 0:
                        avg_pitch = np.median(filtered_f0)  # Use median for robustness
                        print(f"   🎵 Autocorr F0: {avg_pitch:.1f}Hz (from {len(filtered_f0)}/{len(f0_values)} estimates)")
                    else:
                        avg_pitch = median_f0
                        print(f"   🎵 Autocorr F0 (fallback): {avg_pitch:.1f}Hz")
                else:
                    print(f"   ⚠️ Insufficient autocorr samples ({len(f0_values)}), trying YIN backup...")
                    # Fallback to YIN, but be more careful
                    f0 = librosa.yin(audio, fmin=50, fmax=300, sr=sr, frame_length=1024)
                    valid_f0 = f0[(f0 > 50) & (f0 < 300)]
                    
                    if len(valid_f0) > 10:
                        avg_pitch = np.median(valid_f0)
                        print(f"   🎵 YIN F0: {avg_pitch:.1f}Hz (from {len(valid_f0)} estimates)")
                    else:
                        avg_pitch = 150  # Default neutral pitch
                        print(f"   ⚠️ All methods failed, using default: {avg_pitch}Hz")
                    
            except Exception as e:
                print(f"   ⚠️ Pitch detection error: {e}, using fallback")
                avg_pitch = 150
            
            # 2. Speech rate estimation (zero crossing rate as proxy)
            zcr = librosa.feature.zero_crossing_rate(audio)[0]
            avg_zcr = np.mean(zcr)
            
            # 3. Spectral characteristics
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            avg_spectral_centroid = np.mean(spectral_centroids)
            
            # Convert to practical TTS parameters
            # Map pitch to speech rate (lower pitch = slower rate typically)
            estimated_rate = max(120, min(250, 200 - (avg_pitch - 150) * 0.3))
            
            # Improved gender detection based on proper pitch ranges
            # Male: 85-180Hz (typically 85-155Hz), Female: 165-265Hz (typically 185-265Hz)
            if avg_pitch < 160:  # Clearly male range
                gender = "male"
            elif avg_pitch > 185:  # Clearly female range  
                gender = "female"
            else:  # Overlap range 160-185Hz
                # Use spectral centroid and other features for disambiguation
                # Lower spectral centroid typically indicates male voice
                if avg_spectral_centroid < 2000 and avg_zcr < 0.1:
                    gender = "male"
                elif avg_spectral_centroid > 2500 or avg_zcr > 0.15:
                    gender = "female"
                else:
                    # When in doubt with borderline values, lean towards the pitch
                    gender = "male" if avg_pitch < 172 else "female"
            
            characteristics = {
                'pitch': float(avg_pitch),
                'rate': int(estimated_rate),
                'volume': 0.9,
                'spectral_centroid': float(avg_spectral_centroid),
                'gender': gender,
                'zcr': float(avg_zcr)
            }
            
            print(f"   🔍 Analyzed reference: Gender={gender}, Pitch={avg_pitch:.1f}Hz, SpectralCentroid={avg_spectral_centroid:.1f}Hz, Rate={estimated_rate}")
            print(f"   📊 Analysis details: ZCR={avg_zcr:.3f}, F0Method=Autocorr")
            return characteristics
            
        except Exception as e:
            print(f"   ⚠️ Reference analysis failed: {e}, using defaults")
            return {
                'pitch': 150,
                'rate': 180,
                'volume': 0.9,
                'gender': 'unknown',
                'spectral_centroid': 2000,
                'zcr': 0.05
            }
    
    def _select_best_matching_voice(self, voices: list, characteristics: dict) -> dict:
        """Select the best matching voice from available system voices."""
        try:
            gender = characteristics.get('gender', 'unknown')
            
            # Enhanced voice filtering by gender with better keywords
            if gender == 'male':
                # Look for male voices with better quality indicators
                preferred_voices = [v for v in voices if any(keyword in v.name.lower() 
                                  for keyword in ['male', 'man', 'david', 'mark', 'james', 'john', 'michael', 'ryan', 'sean', 'george'])]
                # Also look for voices without explicit female indicators
                if not preferred_voices:
                    preferred_voices = [v for v in voices if not any(keyword in v.name.lower() 
                                      for keyword in ['female', 'woman', 'zira', 'helen', 'mary', 'susan', 'eva'])]
            elif gender == 'female':
                preferred_voices = [v for v in voices if any(keyword in v.name.lower() 
                                  for keyword in ['female', 'woman', 'mary', 'susan', 'helen', 'sarah', 'zira', 'eva'])]
            else:
                preferred_voices = voices
            
            # If no gender-specific voices found, use all voices
            if not preferred_voices:
                preferred_voices = voices
            
            # Select first preferred voice or first available
            selected = preferred_voices[0] if preferred_voices else voices[0]
            
            return {
                'id': selected.id,
                'name': selected.name,
                'gender': gender
            }
            
        except Exception as e:
            print(f"   ⚠️ Voice selection failed: {e}, using first available")
            return {
                'id': voices[0].id if voices else None,
                'name': voices[0].name if voices else "Default",
                'gender': 'unknown'
            }
    
    async def _apply_spectral_matching(self, input_file: Path, output_file: Path, characteristics: dict) -> bool:
        """Apply spectral matching to make TTS sound more like reference."""
        try:
            import librosa
            import soundfile as sf
            import numpy as np
            
            # Load the generated TTS audio
            audio, sr = librosa.load(input_file, sr=22050)
            
            # Apply pitch shifting based on reference characteristics
            target_pitch = characteristics.get('pitch', 150)
            
            # Estimate current pitch and shift accordingly
            current_pitches, magnitudes = librosa.piptrack(y=audio, sr=sr)
            current_pitch_values = []
            for t in range(current_pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = current_pitches[index, t]
                if pitch > 0:
                    current_pitch_values.append(pitch)
            
            if current_pitch_values:
                avg_current_pitch = np.mean(current_pitch_values)
                pitch_shift_steps = 12 * np.log2(target_pitch / avg_current_pitch)
                
                # Apply pitch shift (limit to reasonable range)
                pitch_shift_steps = np.clip(pitch_shift_steps, -12, 12)
                modified_audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_shift_steps)
            else:
                modified_audio = audio
            
            # Save the modified audio
            sf.write(output_file, modified_audio, sr)
            return True
            
        except Exception as e:
            print(f"   ⚠️ Spectral matching error: {e}")
            # Copy original file as fallback
            import shutil
            shutil.copy2(input_file, output_file)
            return False
    
    async def _apply_voice_adjustments(self, input_file: Path, output_file: Path, characteristics: dict) -> bool:
        """Apply basic voice adjustments like pitch and speed."""
        try:
            import librosa
            import soundfile as sf
            import numpy as np
            
            # Load audio
            audio, sr = librosa.load(input_file, sr=22050)
            
            # Apply speed adjustment based on estimated rate
            target_rate = characteristics.get('rate', 180)
            speed_factor = target_rate / 180.0  # 180 is baseline
            speed_factor = np.clip(speed_factor, 0.7, 1.5)  # Reasonable limits
            
            if abs(speed_factor - 1.0) > 0.1:  # Only adjust if significant difference
                modified_audio = librosa.effects.time_stretch(audio, rate=speed_factor)
            else:
                modified_audio = audio
            
            # Apply slight pitch adjustment
            target_pitch = characteristics.get('pitch', 150)
            if target_pitch < 160:  # Lower pitch for male-sounding voice
                pitch_shift = -2  # Lower by 2 semitones
            elif target_pitch > 200:  # Higher pitch for female-sounding voice
                pitch_shift = 1   # Raise by 1 semitone
            else:
                pitch_shift = 0
            
            if pitch_shift != 0:
                modified_audio = librosa.effects.pitch_shift(modified_audio, sr=sr, n_steps=pitch_shift)
            
            # Save the modified audio
            sf.write(output_file, modified_audio, sr)
            return True
            
        except Exception as e:
            print(f"   ⚠️ Voice adjustment error: {e}")
            # Copy original file as fallback
            import shutil
            shutil.copy2(input_file, output_file)
            return False
    
    async def _generate_default_voice(self, text: str, audio_file: Path) -> Path:
        """Generate audio with default voice when no profile available."""
        await self._generate_voice_matched_audio(text, {}, audio_file)
        return audio_file
        
    async def generate_audio_for_changed_sentence(self, text: str, speaker_id: str, audio_file: Path, segment_id: str) -> Path:
        """Generate audio specifically for a changed sentence with unique identifier."""
        print(f"🎤 Generating audio for CHANGED sentence [{speaker_id}]: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Extract segment base info and sentence number
        if '_sentence_' in segment_id:
            segment_base = segment_id.rsplit('_sentence_', 1)[0]
            sentence_num = segment_id.rsplit('_sentence_', 1)[1]
        else:
            segment_base = segment_id
            sentence_num = "1"
            
        # Create segment-specific subfolder
        safe_segment_base = segment_base.replace(':', '_').replace('.', '_')
        segment_folder = self.run_folder / f"segment_{safe_segment_base}"
        segment_folder.mkdir(parents=True, exist_ok=True)
        
        # Create filename within the segment folder
        output_file = segment_folder / f"sentence_{sentence_num}.wav"
        
        # Check generation priority: reference audio > voice profile > default
        if self.reference_audio_file and self.reference_audio_file.exists():
            print(f"   🎭 Using reference voice from: {self.reference_audio_file.name}")
            success = await self._generate_with_reference_voice(text, output_file)
        elif speaker_id not in self.voice_profiles:
            print(f"   ⚠️ No voice profile found for {speaker_id}, using default voice")
            success = await self._generate_voice_matched_audio(text, {}, output_file)
        else:
            voice_profile = self.voice_profiles[speaker_id]
            print(f"   📋 Using voice profile - Pitch: {voice_profile.get('pitch', 0):.1f}Hz")
            success = await self._generate_voice_matched_audio(text, voice_profile, output_file)
        
        if success and output_file.exists():
            print(f"   ✅ Generated: {segment_folder.name}/{output_file.name}")
            return output_file
        else:
            print(f"   ❌ Generation failed")
            return audio_file


class SimpleVoiceGenerator(VoiceGenerator):
    """Simple voice generator with reference audio support"""
    def __init__(self):
        """Initialize simple voice generator with run folder structure."""
        # Set up reference audio path
        self.reference_audio_dir = Path("../Data/reference_audio")
        self.reference_audio_file = self._find_reference_audio()
        
        # Clear existing files from base directories
        self._clear_existing_files()
        
        # Create run folder with timestamp (for consistency)
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_name = f"run_{timestamp}"
        
        # Create output transcriptions folder structure
        self.transcription_folder = Path(f"../Data/output_transcriptions/{self.run_name}")
        self.transcription_folder.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created transcription folder: {self.transcription_folder}")
    
    def _clear_existing_files(self):
        """Clear all existing files from the base output directories."""
        base_audio_dir = Path("../Data/generated_audio")
        base_transcription_dir = Path("../Data/output_transcriptions")
        
        # Clear audio directory
        if base_audio_dir.exists():
            for item in base_audio_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        
        # Clear transcription directory
        if base_transcription_dir.exists():
            for item in base_transcription_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
    
    def get_transcription_path(self, filename: str = "output_transcription.json") -> Path:
        """Get the path for saving transcription in the run folder."""
        return self.transcription_folder / filename
    
    async def generate_audio(self, text: str, speaker_id: str, audio_file: Path) -> Path:
        print(f"🔇 Voice generation disabled - would create audio for: '{text[:30]}...'")
        return audio_file
        
    async def generate_audio_for_changed_sentence(self, text: str, speaker_id: str, audio_file: Path, segment_id: str) -> Path:
        """Generate audio specifically for a changed sentence with unique identifier."""
        # Extract segment base info for consistent folder structure messaging
        if '_sentence_' in segment_id:
            segment_base = segment_id.rsplit('_sentence_', 1)[0]
            sentence_num = segment_id.rsplit('_sentence_', 1)[1]
            safe_segment_base = segment_base.replace(':', '_').replace('.', '_')
            print(f"🔇 Voice disabled - would create: segment_{safe_segment_base}/sentence_{sentence_num}.wav")
        else:
            print(f"🔇 Voice generation disabled for CHANGED sentence [{speaker_id}]: '{text[:30]}...'")
        return audio_file