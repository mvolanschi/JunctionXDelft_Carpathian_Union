# Setup Instructions - FREE Open Source Models

## 1. Install Dependencies
```bash
pip install -r ../../requirements.txt
```

## 2. Set API Keys (FREE!)
Set these environment variables in PowerShell:

```powershell
# Groq API Key (FREE - get from https://console.groq.com/)
$env:GROQ_API_KEY="your-groq-api-key-here"

# Hugging Face API Key (OPTIONAL - free tier, get from https://huggingface.co/settings/tokens)  
$env:HUGGINGFACE_API_KEY="your-hf-api-key-here"
```

## 3. Run the Processor
```bash
python simple_speech_processor.py
```

## FREE API Key Setup

### Groq (Required - FREE!)
1. Go to https://console.groq.com/
2. Sign up with email (completely free)
3. Get your API key from the dashboard
4. Set: `$env:GROQ_API_KEY="gsk_..."`
5. **Free tier**: 6,000 tokens/minute with Llama 3.1 70B!

### Hugging Face (Optional - FREE!)
1. Go to https://huggingface.co/settings/tokens
2. Sign up/login (free)
3. Create a token (read access)
4. Set: `$env:HUGGINGFACE_API_KEY="hf_..."`
5. **Benefits**: Faster TTS, no rate limits

## Usage

The processor will:
1. Use Claude 3.5 to intelligently rewrite offensive content
2. Use ElevenLabs to generate new audio with voice cloning
3. Process your transcription and save clean results

## Input Format

Same as before - use `example_input.json` as a template.