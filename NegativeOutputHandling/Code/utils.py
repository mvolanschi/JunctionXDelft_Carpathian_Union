"""
Utility functions for loading and saving transcriptions.
"""

import json
from pathlib import Path
from models import Transcription, TranscriptionSegment, TimeRange, OffensiveSegment


def load_transcription(file_path: Path) -> Transcription:
    """Load transcription from JSON file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    segments = []
    for seg_data in data['segments']:
        time_range = TimeRange(seg_data['start'], seg_data['end'])
        
        offensive_parts = []
        for off_data in seg_data.get('offensive_parts', []):
            off_time = TimeRange(off_data['start'], off_data['end'])
            offensive_parts.append(OffensiveSegment(
                time_range=off_time,
                original_text=off_data['text'],
                severity=off_data['severity']
            ))
        
        segments.append(TranscriptionSegment(
            time_range=time_range,
            speaker_id=seg_data['speaker_id'],
            text=seg_data['text'],
            offensive_parts=offensive_parts
        ))
    
    return Transcription(
        segments=segments,
        speakers=data['speakers']
    )


def save_transcription(transcription: Transcription, file_path: Path):
    """Save processed transcription to JSON file."""
    data = {
        'speakers': transcription.speakers,
        'segments': []
    }
    
    for segment in transcription.segments:
        seg_data = {
            'start': segment.time_range.start,
            'end': segment.time_range.end,
            'speaker_id': segment.speaker_id,
            'text': segment.text,
            'offensive_parts': [
                {
                    'start': off.time_range.start,
                    'end': off.time_range.end,
                    'original_text': off.original_text,
                    'rewritten_text': off.rewritten_text,
                    'severity': off.severity
                }
                for off in segment.offensive_parts
            ]
        }
        data['segments'].append(seg_data)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def get_available_files():
    """Get list of available transcription files."""
    example_dir = Path("../Data/example_jsons")
    files = []
    
    if example_dir.exists():
        for file_path in example_dir.glob("*.json"):
            files.append((file_path, f"{file_path.name} (from example_jsons)"))
    
    # Also check for files in current directory
    for file_path in Path(".").glob("*input*.json"):
        files.append((file_path, f"{file_path.name} (realistic meeting with offensive content)"))
    
    return files