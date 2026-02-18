"""TTS manager with dialogue pacing, silence gaps, and voice mixing support."""

import asyncio
import logging
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..common import load_config
from ..consistency.store import ConsistencyStore
from .base import TTSProvider, VoiceConfig
from .kokoro_engine import KokoroTTSProvider

logger = logging.getLogger(__name__)

# Kokoro optimal range: 100-200 tokens. We chunk at ~180 words (~200 tokens).
MAX_CHUNK_WORDS = 180
# Silence gap in seconds between narration and dialogue segments
SILENCE_GAP_NARRATION = 0.6  # longer pause before/after narration
SILENCE_GAP_DIALOGUE = 0.3   # shorter pause between dialogue lines
SAMPLE_RATE = 24000  # Kokoro outputs 24kHz WAV


def _generate_silence_wav(duration_seconds: float, output_path: Path) -> None:
    """Generate a silent WAV file of given duration."""
    num_samples = int(SAMPLE_RATE * duration_seconds)
    data_size = num_samples * 2  # 16-bit mono = 2 bytes per sample
    with open(output_path, "wb") as f:
        # WAV header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))      # chunk size
        f.write(struct.pack("<H", 1))       # PCM
        f.write(struct.pack("<H", 1))       # mono
        f.write(struct.pack("<I", SAMPLE_RATE))
        f.write(struct.pack("<I", SAMPLE_RATE * 2))  # byte rate
        f.write(struct.pack("<H", 2))       # block align
        f.write(struct.pack("<H", 16))      # bits per sample
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)        # silence


def _chunk_text(text: str, max_words: int = MAX_CHUNK_WORDS) -> List[str]:
    """Split text into chunks of max_words, breaking at sentence boundaries."""
    sentences = []
    current = []
    for word in text.split():
        current.append(word)
        # Break at sentence-ending punctuation
        if word.endswith((".", "!", "?", '."', '!"', '?"', ".'", "!'", "?'")):
            sentences.append(" ".join(current))
            current = []
    if current:
        sentences.append(" ".join(current))

    chunks = []
    current_chunk: List[str] = []
    current_words = 0

    for sentence in sentences:
        word_count = len(sentence.split())
        if current_words + word_count > max_words and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_words = 0
        current_chunk.append(sentence)
        current_words += word_count

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks if chunks else [text]


class TTSManager:
    """Manages TTS providers with dialogue pacing and voice mixing."""

    def __init__(self, config_path: Optional[Path] = None):
        self.providers: Dict[str, TTSProvider] = {}
        self.voice_configs: Dict[str, VoiceConfig] = {}
        self.store = ConsistencyStore()

        try:
            config = load_config(config_path)
            self._load_voices(config)
        except FileNotFoundError:
            logger.warning("Voice config not found, using defaults")
            self._load_default_voices()

        try:
            self.providers["kokoro"] = KokoroTTSProvider()
            logger.info("Kokoro TTS provider initialized")
        except Exception as e:
            logger.error("Failed to initialize Kokoro TTS: %s", e)
            raise

    def _load_voices(self, config: Dict) -> None:
        for char_type, voice_data in config.get("voices", {}).items():
            self.voice_configs[char_type] = VoiceConfig(
                name=voice_data["name"],
                provider=voice_data.get("provider", "kokoro"),
                speed=voice_data.get("speed", 1.0),
            )

    def _load_default_voices(self) -> None:
        self.voice_configs["narrator"] = VoiceConfig(name="am_puck", provider="kokoro")

    def get_voice_for_character(self, character: str) -> VoiceConfig:
        """Get voice config for a character, checking DB first, then presets."""
        # Check character DB
        char_data = self.store.get_character(character)
        if char_data and char_data.get("voice_id"):
            return VoiceConfig(
                name=char_data["voice_id"],
                provider="kokoro",
                speed=char_data.get("voice_speed", 1.0),
            )
        # Check voice presets
        if character in self.voice_configs:
            return self.voice_configs[character]
        # Default narrator
        return self.voice_configs.get("narrator", VoiceConfig(name="am_puck", provider="kokoro"))

    def get_voice_mix_for_character(self, character: str) -> Optional[List[str]]:
        """Get voice mix list if character has one assigned."""
        char_data = self.store.get_character(character)
        if char_data:
            mix = char_data.get("voice_mix", [])
            return mix if len(mix) >= 2 else None
        return None

    async def _generate_segment(
        self,
        text: str,
        output_path: Path,
        character: str = "narrator",
    ) -> Optional[str]:
        """Generate audio for a text segment, using voice mix if available."""
        voice_mix = self.get_voice_mix_for_character(character)
        provider = self.providers.get("kokoro")
        if not provider:
            return None

        if voice_mix and isinstance(provider, KokoroTTSProvider):
            char_data = self.store.get_character(character)
            speed = char_data.get("voice_speed", 1.0) if char_data else 1.0
            return await provider.generate_with_mix(text, output_path, voice_mix, speed)
        else:
            voice_config = self.get_voice_for_character(character)
            return await provider.generate_audio(text, output_path, voice_config)

    async def _generate_chunked(
        self,
        text: str,
        output_path: Path,
        character: str = "narrator",
        temp_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """Generate audio with auto-chunking for optimal Kokoro quality.

        Splits text at sentence boundaries into 100-200 token chunks,
        generates each, then concatenates with ffmpeg.
        """
        chunks = _chunk_text(text)
        if len(chunks) <= 1:
            return await self._generate_segment(text, output_path, character)

        if temp_dir is None:
            temp_dir = output_path.parent / "_chunks"
        temp_dir.mkdir(parents=True, exist_ok=True)

        chunk_files = []
        for idx, chunk in enumerate(chunks):
            chunk_path = temp_dir / f"chunk_{idx:03d}.wav"
            result = await self._generate_segment(chunk, chunk_path, character)
            if result:
                chunk_files.append(chunk_path)

        if not chunk_files:
            return None

        if len(chunk_files) == 1:
            import shutil
            shutil.copy2(chunk_files[0], output_path)
            return str(output_path)

        return self._concat_files(chunk_files, output_path)

    async def generate_scene_audio(
        self,
        narration: str,
        dialogues: List[Dict[str, str]],
        output_path: Union[str, Path],
        default_voice: str = "narrator",
    ) -> Optional[str]:
        """Generate scene audio with dialogue pacing and silence gaps.

        Generates narration and dialogue segments separately with per-character
        voices, inserts silence gaps between segments for natural pacing.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            segments: List[Path] = []
            seg_idx = 0

            # Narration
            if narration and narration.strip():
                narr_path = temp_path / f"seg_{seg_idx:03d}_narration.wav"
                result = await self._generate_chunked(
                    narration, narr_path, default_voice, temp_path / "narr_chunks"
                )
                if result:
                    segments.append(narr_path)
                    seg_idx += 1

                    # Silence gap after narration
                    if dialogues:
                        silence = temp_path / f"seg_{seg_idx:03d}_silence.wav"
                        _generate_silence_wav(SILENCE_GAP_NARRATION, silence)
                        segments.append(silence)
                        seg_idx += 1

            # Dialogues
            for d_idx, dialogue in enumerate(dialogues):
                speaker = dialogue.get("speaker") or default_voice
                line = dialogue.get("line", "")
                if not line or not line.strip():
                    continue

                dlg_path = temp_path / f"seg_{seg_idx:03d}_dlg_{speaker}.wav"
                result = await self._generate_chunked(
                    line, dlg_path, speaker, temp_path / f"dlg_chunks_{d_idx}"
                )
                if result:
                    segments.append(dlg_path)
                    seg_idx += 1

                    # Silence gap between dialogue lines
                    if d_idx < len(dialogues) - 1:
                        silence = temp_path / f"seg_{seg_idx:03d}_silence.wav"
                        _generate_silence_wav(SILENCE_GAP_DIALOGUE, silence)
                        segments.append(silence)
                        seg_idx += 1

            if not segments:
                logger.warning("No audio segments generated for scene")
                return None

            return self._concatenate_files(segments, output_path)

    async def generate_story_audio(
        self,
        sequence: List[Dict[str, str]],
        output_path: Union[str, Path],
        default_voice: str = "narrator",
    ) -> Optional[str]:
        """Generate full scene audio from a chronological sequence of narration/dialogue.

        sequence elements:
          - {'type': 'narration', 'text': '...'}
          - {'type': 'dialogue', 'speaker': 'Name', 'text': '...'}
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not sequence:
            return None

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            segments: List[Path] = []
            seg_idx = 0

            for item in sequence:
                text = item.get("text", "").strip()
                if not text:
                    continue

                itype = item.get("type", "narration")
                speaker = item.get("speaker", default_voice) if itype == "dialogue" else default_voice

                # Generate audio segment
                seg_path = temp_path / f"seg_{seg_idx:03d}_{itype}.wav"
                
                # Use chunked generation for long text
                result = await self._generate_chunked(
                    text, seg_path, speaker, temp_path / f"chunk_{seg_idx}"
                )

                if result:
                    segments.append(seg_path)
                    
                    # Add silence based on type
                    gap_duration = SILENCE_GAP_DIALOGUE if itype == "dialogue" else SILENCE_GAP_NARRATION
                    silence_path = temp_path / f"seg_{seg_idx:03d}_silence.wav"
                    _generate_silence_wav(gap_duration, silence_path)
                    segments.append(silence_path)
                    
                    seg_idx += 1

            if not segments:
                return None

            return self._concatenate_files(segments, output_path)

    @staticmethod
    def _concatenate_files(files: List[Path], output_path: Path) -> Optional[str]:
        """Concatenate WAV files using ffmpeg."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for fp in files:
                f.write(f"file '{fp.as_posix()}'\n")
            concat_file = Path(f.name)

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        concat_file.unlink(missing_ok=True)

        if result.returncode != 0:
            logger.error("FFmpeg concat error: %s", result.stderr[-300:])
            return None

        logger.info("Concatenated %d segments → %s", len(files), output_path)
        return str(output_path)

    async def generate_batch_audio(
        self,
        scenes: List[Dict],
        output_dir: Union[str, Path],
        max_concurrent: int = 3,
        default_voice: str = "narrator",
    ) -> List[Optional[str]]:
        """Generate audio for a batch of scenes with concurrency control.

        Supports both new 'sequence' format and legacy 'narration/dialogues' format.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_one(idx: int, scene: Dict) -> Optional[str]:
            async with semaphore:
                try:
                    path = output_dir / f"scene_{idx:03d}.wav"
                    logger.info("Generating audio for scene %d...", idx)
                    
                    if "sequence" in scene:
                        return await self.generate_story_audio(
                            scene["sequence"], path, default_voice
                        )
                    else:
                        narration = scene.get("narration") or scene.get("text_segment", "")
                        dialogues = scene.get("dialogues", [])
                        return await self.generate_scene_audio(
                            narration, dialogues, path, default_voice
                        )
                except Exception as e:
                    logger.error("Failed to generate audio for scene %d: %s", idx, e)
                    return None

        tasks = [generate_one(i, scene) for i, scene in enumerate(scenes)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if not isinstance(r, Exception) else None for r in results]
