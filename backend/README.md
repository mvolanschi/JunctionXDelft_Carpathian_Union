# Meeting Transcription Backend

This service exposes a simple HTTP API for uploading speech audio (meetings, calls, interviews) and obtaining high-quality transcripts powered by the optimized [faster-whisper](https://github.com/SYSTRAN/faster-whisper) runtime for Whisper models.

## Features

- `POST /transcriptions` endpoint accepts common audio formats (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.flac`, `.webm`).
- Lazy Whisper model loading keeps startup fast while reusing the model across requests.
- Configurable decoding options through query parameters and environment variables.
- Detailed segment metadata (timestamps, language, duration) for downstream analytics.

## Prerequisites

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your `PATH`.
- Adequate CPU or GPU resources for the selected Whisper model (default: `base`).

> **Heads-up**: faster-whisper bundles CTranslate2 under the hood. It auto-detects CPU/GPU acceleration, but you can force the device (e.g. `cpu`, `cuda`, `auto`, `metal`) via `WHISPER_DEVICE` and choose the precision (`WHISPER_COMPUTE_TYPE`, e.g. `int8`, `float16`).

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
FLASK_APP=app.main:app flask run --host 0.0.0.0 --port 8000 --debug
```

Browse to <http://localhost:8000/health> for a quick readiness probe.

### Environment configuration

Create a copy of `.env.example` named `.env` and tweak the values to match your setup. The application automatically loads this file on startup (courtesy of `python-dotenv`), so the variables below can live there instead of cluttering your shell profile.

| Variable | Default | Purpose |
| --- | --- | --- |
| `WHISPER_MODEL_NAME` | `base` | Whisper checkpoint to load (`tiny`, `small`, `medium`, `large-v3`, …). |
| `WHISPER_DEFAULT_LANGUAGE` | `None` | Force a specific language without auto-detection. |
| `WHISPER_TEMPERATURE` | `0.0` | Sampling temperature used during decoding. |
| `WHISPER_INITIAL_PROMPT` | `None` | Priming text handed to Whisper for custom jargon. |
| `WHISPER_BEAM_SIZE` | `5` | Beam width for beam-search decoding. |
| `WHISPER_BEST_OF` | `5` | Number of candidate beams to retain. |
| `WHISPER_DEVICE` | `None` | Override the device selection for faster-whisper (`cpu`, `cuda`, `auto`, `metal`). |
| `WHISPER_COMPUTE_TYPE` | `None` | Precision mode for faster-whisper (`int8`, `int8_float16`, `float16`, `float32`, …). |
| `DIARIZATION_ENABLED` | `false` | Turn on pyannote speaker diarization and annotate each segment with a speaker label. |
| `DIARIZATION_MODEL_ID` | `pyannote/speaker-diarization-3.1` | Hugging Face model identifier to use for diarization. |
| `DIARIZATION_AUTH_TOKEN` | `None` | Hugging Face access token used to download the diarization pipeline (falls back to `HUGGINGFACE_TOKEN`). |
| `DIARIZATION_MIN_OVERLAP` | `0.15` | Minimum overlap (seconds) required before a speaker label is assigned to a segment. |

### Basic request example

```bash
curl -X POST \
  -F "file=@/path/to/meeting.wav" \
  -F "language=en" \
  "http://localhost:8000/transcriptions"
```

The response contains the full transcript as well as segment-level timestamps and metadata.

## Testing

```bash
pytest
```

The test suite covers the Whisper service wrapper and the HTTP surface via dependency injection and lightweight fakes, so it runs quickly without loading heavy models.

### Local CLI transcription

Need to sanity-check an audio file outside the HTTP API? Use the helper script to run the same transcription pipeline locally and dump the transcript to a `.txt` file.

```bash
python -m scripts.transcribe_file /path/to/audio.mp3 --include-segments
```

- By default the transcript is written alongside the audio file as `<audio>.txt`; pass `-o /path/to/output.txt` to control the destination.
- The script respects the same environment variables documented above, and you can override decoding parameters at runtime (e.g. `--language`, `--translate`, `--beam-size`).
- Add `--include-segments` to append timestamped segments for deeper inspection.

### Speaker diarization

Set `DIARIZATION_ENABLED=true` and supply a Hugging Face access token (via `DIARIZATION_AUTH_TOKEN` or `HUGGINGFACE_TOKEN`) to enable the built-in [pyannote.audio](https://github.com/pyannote/pyannote-audio) diarization pipeline. When enabled, each transcription segment includes a `speaker` label and the CLI outputs dialog-style lines.

> **Tip:** Because the diarization model loads alongside Whisper, keep both services warm in long-running processes to avoid repeated initialisation overhead. For CPU-only environments you may prefer a smaller diarization checkpoint or increase `DIARIZATION_MIN_OVERLAP` to reduce speaker jitter.
