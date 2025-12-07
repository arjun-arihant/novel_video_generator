"""Base classes for TTS providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


@dataclass
class VoiceConfig:
    """Configuration for a TTS voice."""
    name: str
    provider: str = "gemini"
    rate: float = 1.0
    pitch: float = 0.0


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    async def generate_audio(
        self,
        text: str,
        output_path: Union[str, Path],
        voice_config: VoiceConfig
    ) -> Optional[str]:
        """
        Generate audio from text and save to output_path.

        Args:
            text: Text to convert to speech
            output_path: Path where audio file will be saved
            voice_config: Voice configuration

        Returns:
            Path to saved audio file, or None if generation failed
        """
        pass
