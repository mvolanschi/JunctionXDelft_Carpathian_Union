# NegativeOutputHandler - Speech Processing Module

A complete pipeline for cleaning offensive content from speech transcriptions and regenerating audio with voice cloning.

## 🚀 Quick Start

```python
from speech_processor import process_transcription

# Process a complete transcription
result = await process_transcription(
    input_json_path="input_transcription.json",
    reference_audio_path="reference_voice.mp3",
  output_dir="output/"
)

if result.success:
    print(f"✅ Generated clean JSON: {result.output_json_path}")
    print(f"🔊 Generated {len(result.generated_audio_files)} audio files")
```

## 📁 Module Structure

### Core Files
- **`speech_processor.py`** - Main processing module with complete pipeline
- **`run_speech_processor.py`** - Usage example and demonstration
- **`content_rewriter.py`** - AI-powered content rewriting (Groq + fallback)
- **`advanced_voice_generator.py`** - ElevenLabs voice cloning and generation
- **`models.py`** - Data models and structures
- **`utils.py`** - Utility functions

### Configuration
- **Dependencies** – managed via the shared `../../requirements.txt`
- **`SETUP.md`** - Setup instructions
- **`../config/api_keys.json`** - API key configuration

## 🔄 Processing Pipeline

1. **📁 Load Input JSON** - Loads transcription with offensive content markers
2. **✏️ Rewrite Content** - Uses AI/fallback to clean offensive language
3. **🎤 Clone Voice** - Creates voice clone from reference audio (once)
4. **🔊 Generate Audio** - Creates new audio files for all cleaned segments
5. **💾 Save Output** - Exports clean JSON + organized audio files (optional when
  ``persist_outputs=False`` for in-memory API responses)

## 📊 Input/Output Format

### Input JSON Structure
```json
{
  "speakers": {
    "speaker_1": "John Doe",
    "speaker_2": "Jane Smith"
  },
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "speaker_id": "speaker_1", 
      "text": "This is completely fucked up!",
      "offensive_parts": [
        {
          "text": "fucked up",
          "severity": "high",
          "start": 3.1,
          "end": 4.8
        }
      ]
    }
  ]
}
```

### Output JSON Structure
```json
{
  "speakers": { "..." },
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "speaker_id": "speaker_1",
      "original_text": "This is completely fucked up!",
      "text": "This is completely messed up!",
      "was_rewritten": true,
      "generated_audio_file": "generated_audio_20241004_123456/speaker_1_segment_001.mp3",
      "offensive_parts": [...]
    }
  ],
  "processing_info": {
    "timestamp": "20241004_123456",
    "total_segments": 12,
    "rewritten_segments": 8,
    "generated_audio_files": 8
  }
}
```

## ⚙️ Configuration

### API Keys Required
- **ElevenLabs API Key** - For high-quality voice cloning
- **Groq API Key** (optional) - For advanced content rewriting

### Setup API Keys
1. Add to environment variables:
   ```bash
   set GROQ_API_KEY=your_groq_api_key_here
   ```

2. Or add to `../config/api_keys.json`:
   ```json
   {
     "elevenlabs_api_key": "your_elevenlabs_key",
     "groq_api_key": "your_groq_key"
   }
   ```

## 🎯 Usage Examples

### Basic Processing
```python
import asyncio
from speech_processor import process_transcription

async def main():
    result = await process_transcription(
        input_json_path="meeting_transcript.json",
        reference_audio_path="speaker_voice_sample.mp3",
        output_dir="cleaned_output/"
    )
    
    if result.success:
        print(f"Processed {result.processed_segments} segments")
        print(f"Output: {result.output_json_path}")

asyncio.run(main())
```

### Advanced Usage with Custom Configuration
```python
from speech_processor import SpeechProcessor

processor = SpeechProcessor(
    input_json_path="input.json",
    reference_audio_path="reference.mp3", 
    output_dir="output/",
  config_path="custom_config.json",
  persist_outputs=True  # Set to False for in-memory API responses
)

result = await processor.process_complete()
```

## 📋 Requirements

- Python 3.8+
- ElevenLabs API account
- Groq API account (optional, has fallback)
- Audio files in supported formats (MP3, WAV)

## 🔧 Installation

```bash
pip install -r ../../requirements.txt
```

## 🎉 Features

- ✅ **Complete Pipeline** - End-to-end processing
- ✅ **Voice Cloning** - High-quality ElevenLabs integration  
- ✅ **Smart Content Rewriting** - AI-powered + fallback
- ✅ **Batch Processing** - Handles multiple segments efficiently
- ✅ **Organized Output** - Clean file structure and naming
- ✅ **Error Handling** - Robust error recovery and reporting
- ✅ **Easy Integration** - Simple API for external use

## 📞 Support

For issues or questions, check the generated output files and error messages. The module provides detailed logging and error reporting.