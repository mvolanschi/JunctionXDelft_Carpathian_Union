"""
Data models for speech processing system.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
from abc import ABC, abstractmethod


@dataclass
class TimeRange:
    start: float
    end: float


@dataclass 
class OffensiveSegment:
    time_range: TimeRange
    original_text: str
    severity: str  # "low", "medium", "high"
    rewritten_text: Optional[str] = None


@dataclass
class TranscriptionSegment:
    time_range: TimeRange
    speaker_id: str
    text: str
    offensive_parts: List[OffensiveSegment] = None
    generated_audio_file: Path = None  # Path to regenerated audio for this segment (backward compatibility)
    generated_audio_files: List[Path] = None  # Multiple audio files for individual changed sentences
    was_modified: bool = False  # Track if this segment was actually changed
    
    def __post_init__(self):
        if self.offensive_parts is None:
            self.offensive_parts = []
        if self.generated_audio_files is None:
            self.generated_audio_files = []


@dataclass
class Transcription:
    segments: List[TranscriptionSegment]
    speakers: Dict[str, str]  # speaker_id -> speaker_name


# Abstract interfaces
class VoiceGenerator(ABC):
    @abstractmethod
    async def generate_audio(self, text: str, speaker_id: str, audio_file: Path) -> Path:
        pass
        
    @abstractmethod
    async def generate_audio_for_changed_sentence(self, text: str, speaker_id: str, audio_file: Path, segment_id: str) -> Path:
        """Generate audio specifically for a changed sentence with unique identifier."""
        pass