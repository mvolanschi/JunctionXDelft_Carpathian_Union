# Data Directory Structure

This directory contains essential data files for the NegativeOutputHandler speech processing module.

## 📁 Folder Structure

### `example_jsons/`
Sample input JSON files for testing and demonstration:
- `expanded_input_transcription.json` - Complete sample with offensive content markers
- `input_transcription.json` - Basic input format example

### `reference_audio/`
Reference audio files for voice cloning:
- `reading-from-descartes-discourse-on-method-20113.mp3` - Primary reference voice sample

### `enhanced_output/`
Output from the latest ModerationResult processing run:
- `cleaned_transcription_*.json` - Processed clean transcription
- `generated_audio_*/` - Generated clean audio files

## 🧹 Cleaned Up

The following directories have been removed as they contained old/duplicate test data:
- ~~`generated_audio/`~~ - Old test outputs
- ~~`processed_output/`~~ - Legacy processing outputs  
- ~~`output_transcriptions/`~~ - Empty legacy folder
- ~~`negative_output_results/`~~ - Duplicate results

## 💡 Usage

- **Input**: Use files from `example_jsons/` for testing
- **Reference**: Use `reference_audio/` for voice cloning
- **Output**: Results are saved to `enhanced_output/` or custom output directories