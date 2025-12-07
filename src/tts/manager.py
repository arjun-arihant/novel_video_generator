import os
import logging
import yaml
from typing import Dict, Optional
from .base import TTSProvider, VoiceConfig

logger = logging.getLogger(__name__)

class TTSManager:
    def __init__(self, config_path: str = "configs/voices.yaml"):
        self.providers: Dict[str, TTSProvider] = {}
        self.voice_configs: Dict[str, VoiceConfig] = {}
        self.load_config(config_path)
        
        # Initialize Gemini TTS provider
        try:
            from .gemini_engine import GeminiTTSProvider
            self.providers['gemini'] = GeminiTTSProvider()
            logger.info("Gemini TTS provider initialized.")
        except Exception as e:
            logger.error(f"Gemini TTS not available: {e}")
            raise

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

    def get_provider(self, provider_name: str) -> Optional[TTSProvider]:
        return self.providers.get(provider_name)
    
    def get_voice_id(self, character: str, provider: str) -> VoiceConfig:
        config = self.voice_configs.get(character)
        if config:
            return config
        # Fallback config
        return VoiceConfig(name="default", provider=provider)

    async def generate_narration(self, text: str, output_path: str, character: str = "narrator"):
        config = self.voice_configs.get(character)
        if not config:
            # Default fallback
            config = VoiceConfig(name="Puck", provider="gemini")
            
        provider = self.providers.get(config.provider)
        if not provider:
            # Fallback to whatever is available
            if self.providers:
                provider = list(self.providers.values())[0]
            else:
                logger.error("No TTS providers available")
                return None
            
        return await provider.generate_audio(text, output_path, config)
