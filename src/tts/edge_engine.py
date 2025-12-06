import edge_tts
import logging
from typing import List
from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)

class EdgeTTSProvider(TTSProvider):
    """Implementation of TTSProvider using edge-tts"""
    
    async def generate_audio(self, text: str, output_path: str, voice_id: str) -> str:
        """
        Generate audio using Microsoft Edge's online TTS service.
        """
        try:
            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"Error generating audio with Edge TTS: {e}")
            raise

    async def get_voices(self) -> List[VoiceConfig]:
        """Return list of available voices from edge-tts"""
        try:
            voices = await edge_tts.list_voices()
            voice_configs = []
            for v in voices:
                voice_configs.append(VoiceConfig(
                    voice_id=v['ShortName'],
                    name=v['FriendlyName'],
                    gender=v['Gender'],
                    language=v['Locale']
                ))
            return voice_configs
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []
