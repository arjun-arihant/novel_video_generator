"""TTS manager for orchestrating audio generation."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..common import load_config
from .base import TTSProvider, VoiceConfig
from .gemini_engine import GeminiTTSProvider

logger = logging.getLogger(__name__)


class TTSManager:
    """Manages TTS providers and voice configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize TTS manager.

        Args:
            config_path: Path to voice configuration file
        """
        self.providers: Dict[str, TTSProvider] = {}
        self.voice_configs: Dict[str, VoiceConfig] = {}

        # Load voice configuration
        try:
            config = load_config(config_path)
            self._load_voices(config)
        except FileNotFoundError:
            logger.warning("Voice config not found, using defaults")
            self._load_default_voices()

        # Initialize Gemini TTS provider
        try:
            self.providers['gemini'] = GeminiTTSProvider()
            logger.info("Gemini TTS provider initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini TTS: {e}")
            raise

    def _load_voices(self, config: Dict) -> None:
        """Load voice configurations from config dict."""
        for char_type, voice_data in config.get('voices', {}).items():
            self.voice_configs[char_type] = VoiceConfig(
                name=voice_data['name'],
                provider=voice_data.get('provider', 'gemini'),
                rate=voice_data.get('rate', 1.0),
                pitch=voice_data.get('pitch', 0.0)
            )
        logger.info(f"Loaded {len(self.voice_configs)} voice configurations")

    def _load_default_voices(self) -> None:
        """Load default voice configurations."""
        self.voice_configs['narrator'] = VoiceConfig(
            name="Puck",
            provider="gemini"
        )

    def get_voice_config(self, character: str = "narrator") -> VoiceConfig:
        """
        Get voice configuration for a character.

        Args:
            character: Character name

        Returns:
            Voice configuration
        """
        return self.voice_configs.get(
            character,
            self.voice_configs.get('narrator', VoiceConfig(name="Puck", provider="gemini"))
        )

    async def generate_scene_audio(
        self,
        text: str,
        output_path: Union[str, Path],
        character: str = "narrator"
    ) -> Optional[str]:
        """
        Generate audio for a single scene.

        Args:
            text: Text to convert to speech
            output_path: Path where audio file will be saved
            character: Character name for voice selection

        Returns:
            Path to saved audio file, or None if generation failed
        """
        voice_config = self.get_voice_config(character)
        provider = self.providers.get(voice_config.provider)

        if not provider:
            logger.error(f"Provider '{voice_config.provider}' not available")
            return None

        return await provider.generate_audio(text, output_path, voice_config)

    async def generate_batch_audio(
        self,
        scenes: List[Dict],
        output_dir: Union[str, Path],
        max_concurrent: int = 3
    ) -> List[Optional[str]]:
        """
        Generate audio for multiple scenes concurrently.

        Args:
            scenes: List of scene dictionaries with 'text_segment' field
            output_dir: Directory where audio files will be saved
            max_concurrent: Maximum number of concurrent generations

        Returns:
            List of paths to saved audio files (None for failed generations)
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(idx: int, scene: Dict) -> Optional[str]:
            async with semaphore:
                text = scene.get('text_segment', '')
                if not text:
                    logger.warning(f"Scene {idx} has no text_segment")
                    return None

                output_path = output_dir / f"scene_{idx:03d}.mp3"
                logger.info(f"Generating audio for scene {idx}...")

                return await self.generate_scene_audio(text, output_path)

        tasks = [generate_with_limit(i, scene) for i, scene in enumerate(scenes)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to None
        return [
            result if not isinstance(result, Exception) else None
            for result in results
        ]
