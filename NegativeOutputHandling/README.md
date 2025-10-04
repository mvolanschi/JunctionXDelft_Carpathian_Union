# Speech Processing System

A comprehensive framework for processing multi-speaker transcriptions to remove offensive content and regenerate clean audio with voice matching.

## 🚀 Quick Start

### Run from Code directory
```bash
cd Code

# Option 1: Modular Architecture (recommended)
python main.py

# Option 2: Monolithic Version
python simple_speech_processor.py
```

## 📁 Project Structure

```
NegativeOutputHandling/
├── 📁 Data/                          # All data files and outputs
│   ├── example_jsons/                # Input transcription files
│   ├── generated_audio/              # Generated audio outputs (by run)
│   └── output_transcriptions/        # Processed transcriptions (by run)
│
└── 📁 Code/                          # All source code and documentation
    ├── main.py                       # Modular entry point ⭐
    ├── simple_speech_processor.py    # Monolithic version
    ├── models.py                     # Data structures
    ├── content_rewriter.py           # AI content filtering
    ├── voice_generator.py            # Voice synthesis
    ├── processor.py                  # Processing coordination
    ├── utils.py                      # Utilities
    └── requirements.txt             # Dependencies
```

## 🎯 Features

✅ **AI-Powered Content Rewriting** - Uses Groq's Llama 3.1-8b-instant model  
✅ **Voice Matching** - Analyzes and recreates similar voice characteristics  
✅ **Run-Based Organization** - Each execution creates timestamped folders  
✅ **Dual Architecture** - Both modular and monolithic versions available  
✅ **Clean Data Separation** - Code and data completely separated  

## 🔧 How It Works

1. **Input**: Multi-speaker transcription JSON with flagged offensive content
2. **Processing**: AI rewrites offensive language while preserving meaning
3. **Voice Generation**: Creates new audio matching original speaker characteristics
4. **Output**: Clean transcription + generated audio files in timestamped run folders

## 🏗️ Architecture

### Modular Design (main.py)
- **`models.py`** - Data classes and interfaces
- **`content_rewriter.py`** - AI content filtering with Groq
- **`voice_generator.py`** - Voice analysis and synthesis  
- **`processor.py`** - Processing coordination
- **`utils.py`** - File I/O and utilities

### Benefits
- 🔌 Easy to extend with new AI models
- 🧪 Better testability
- 📖 Improved maintainability  
- 🔄 Backward compatible with monolithic version

## 📊 Data Organization

All data is organized by timestamped runs:
- **Audio**: `Data/generated_audio/run_YYYYMMDD_HHMMSS/`
- **Transcriptions**: `Data/output_transcriptions/run_YYYYMMDD_HHMMSS/`

This allows easy tracking and correlation of outputs from each execution.

## 🛠️ Setup

1. **Environment**: Requires Python 3.11+ with virtual environment in `Code/venv/`
2. **Dependencies**: `pip install -r requirements.txt` 
3. **API Key**: Set `GROQ_API_KEY` environment variable (free at https://console.groq.com/)

## 💡 Usage Examples

### Content Processing Only
```bash
cd Code
echo "1\nn" | python main.py  # Option 1, no voice generation
```

### Full Voice Generation
```bash
cd Code  
echo "1\ny" | python main.py  # Option 1, with voice generation
```

## 🎵 Voice Generation

The system supports multiple TTS engines:
- **pyttsx3** (primary) - Built-in Windows voices with pitch/rate adjustment
- **gTTS** (fallback) - Google Text-to-Speech for natural voice generation

Voice matching analyzes:
- Fundamental frequency (pitch)  
- Spectral characteristics
- MFCC features for timbre matching

## 📈 Development

This project demonstrates:
- Clean separation of concerns
- Modular architecture principles
- AI integration best practices
- Professional project organization