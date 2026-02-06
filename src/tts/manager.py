"""TTS manager for orchestrating audio generation."""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..common import load_config
from .base import TTSProvider, VoiceConfig
from .want2gp_engine import Want2GPTTSProvider

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

        try:
            config = load_config(config_path)
            self._load_voices(config)
        except FileNotFoundError:
            logger.warning("Voice config not found, using defaults")
            self._load_default_voices()

        try:
            self.providers["want2gp"] = Want2GPTTSProvider()
            logger.info("Want2GP TTS provider initialized")
        except Exception as e:
            logger.error("Failed to initialize Want2GP TTS: %s", e)
            raise

    def _load_voices(self, config: Dict) -> None:
        for char_type, voice_data in config.get("voices", {}).items():
            self.voice_configs[char_type] = VoiceConfig(
                name=voice_data["name"],
                provider=voice_data.get("provider", "want2gp"),
                rate=voice_data.get("rate", 1.0),
                pitch=voice_data.get("pitch", 0.0),
            )
        logger.info("Loaded %s voice configurations", len(self.voice_configs))

    def _load_default_voices(self) -> None:
        self.voice_configs["narrator"] = VoiceConfig(
            name="narrator_f_1",
            provider="want2gp",
        )

    def get_voice_config(self, character: str = "narrator") -> VoiceConfig:
        return self.voice_configs.get(
            character,
            self.voice_configs.get("narrator", VoiceConfig(name="narrator_f_1", provider="want2gp")),
        )

    def register_character_voice(self, character: str, preset_key: str) -> None:
        """Register a character-specific voice preset."""
        preset = self.voice_configs.get(preset_key)
        if not preset:
            logger.warning("Voice preset '%s' not found for %s", preset_key, character)
            return
        self.voice_configs[character] = VoiceConfig(
            name=preset.name,
            provider=preset.provider,
            rate=preset.rate,
            pitch=preset.pitch,
        )

    async def generate_scene_audio(
        self,
        text: str,
        output_path: Union[str, Path],
        character: str = "narrator",
    ) -> Optional[str]:
        voice_config = self.get_voice_config(character)
        provider = self.providers.get(voice_config.provider)

        if not provider:
            logger.error("Provider '%s' not available", voice_config.provider)
            return None

        return await provider.generate_audio(text, output_path, voice_config)

    async def generate_scene_audio_from_segments(
        self,
        narration: str,
        dialogues: List[Dict[str, str]],
        output_path: Union[str, Path],
        default_voice: str = "narrator",
    ) -> Optional[str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            segments: List[Path] = []

            if narration:
                narration_path = temp_path / "segment_000.mp3"
                if await self.generate_scene_audio(narration, narration_path, default_voice):
                    segments.append(narration_path)

            for idx, dialogue in enumerate(dialogues):
                speaker = dialogue.get("speaker") or default_voice
                line = dialogue.get("line", "")
                if not line:
                    continue
                segment_path = temp_path / f"segment_{idx + 1:03d}.mp3"
                if await self.generate_scene_audio(line, segment_path, speaker):
                    segments.append(segment_path)

            if not segments:
                logger.warning("No audio segments generated for scene")
                return None

            concat_file = temp_path / "concat.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                for segment in segments:
                    f.write(f"file '{segment.as_posix()}'\n")

            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("FFmpeg concat error: %s", result.stderr)
                return None

            return str(output_path)

    async def generate_batch_audio(
        self,
        scenes: List[Dict],
        output_dir: Union[str, Path],
        max_concurrent: int = 3,
        default_voice: str = "narrator",
    ) -> List[Optional[str]]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_limit(idx: int, scene: Dict) -> Optional[str]:
            async with semaphore:
                narration = scene.get("narration") or scene.get("text_segment", "")
                dialogues = scene.get("dialogues", [])
                output_path = output_dir / f"scene_{idx:03d}.mp3"
                logger.info("Generating audio for scene %s...", idx)
                return await self.generate_scene_audio_from_segments(
                    narration,
                    dialogues,
                    output_path,
                    default_voice=default_voice,
                )

        tasks = [generate_with_limit(i, scene) for i, scene in enumerate(scenes)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [result if not isinstance(result, Exception) else None for result in results]
