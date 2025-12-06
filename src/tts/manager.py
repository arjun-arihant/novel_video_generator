import os
import logging
import yaml
from typing import Dict, Optional
from .base import TTSProvider, VoiceConfig
from .edge_engine import EdgeTTSProvider
from .google_engine import GoogleTTSProvider

logger = logging.getLogger(__name__)

class TTSManager:
    def __init__(self, config_path: str = "configs/voices.yaml"):
        self.providers: Dict[str, TTSProvider] = {}
        self.voice_configs: Dict[str, VoiceConfig] = {}
        self.load_config(config_path)
        
        # Initialize providers
        try:
            self.providers['google'] = GoogleTTSProvider()
        except Exception as e:
            logger.warning(f"Google TTS not available: {e}")
            
        try:
            self.providers['edge'] = EdgeTTSProvider()
        except Exception as e:
            logger.warning(f"Edge TTS not available: {e}")

    def load_config(self, path: str):
        if not os.path.exists(path):
            logger.warning(f"Voice config not found at {path}")
            return
            
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
            
        for char_type, config in data.get('voices', {}).items():
            self.voice_configs[char_type] = VoiceConfig(
                name=config['name'],
                provider=config.get('provider', 'google'),
                rate=config.get('rate', 1.0),
                pitch=config.get('pitch', 0.0)
            )

    async def generate_narration(self, text: str, output_path: str, character: str = "narrator"):
        config = self.voice_configs.get(character)
        if not config:
            # Default fallback
            config = VoiceConfig(name="en-US-Neural2-D", provider="google")
            
        provider = self.providers.get(config.provider)
        if not provider:
            # Fallback to whatever is available
            if self.providers:
                provider = list(self.providers.values())[0]
            else:
                logger.error("No TTS providers available")
                return None
            
        return await provider.generate_audio(text, output_path, config)
