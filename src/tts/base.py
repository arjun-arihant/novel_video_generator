from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class VoiceConfig:
    name: str
    provider: str = "gemini"
    rate: float = 1.0
    pitch: float = 0.0

class TTSProvider(ABC):
    @abstractmethod
    async def generate_audio(self, text: str, output_path: str, voice_config: VoiceConfig) -> Optional[str]:
        """
        Generate audio from text and save to output_path.
        """
        pass
