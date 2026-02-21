"""TTS manager using Qwen3 (WanGP) engine exclusively."""

import asyncio
import logging
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..common import load_config
from ..consistency.store import ConsistencyStore
from .qwen3 import Qwen3Engine
from ..common.paths import get_project_root

logger = logging.getLogger(__name__)

# Silence gap in seconds between narration and dialogue segments
SILENCE_GAP_NARRATION = 0.6  # longer pause before/after narration
SILENCE_GAP_DIALOGUE = 0.3   # shorter pause between dialogue lines
SAMPLE_RATE = 24000  # WAV sample rate

def _generate_silence_wav(duration_seconds: float, output_path: Path) -> None:
    """Generate a silent WAV file of given duration."""
    num_samples = int(SAMPLE_RATE * duration_seconds)
    data_size = num_samples * 2  # 16-bit mono = 2 bytes per sample
    output_path.parent.mkdir(parents=True, exist_ok=True)
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


class TTSManager:
    """Manages TTS using Qwen3 Multi-Pass strategy."""

    def __init__(self, base_dir: Optional[Path] = None, config_path: Optional[Path] = None):
        """Initialize TTSManager.
        
        Args:
            base_dir: Path to the consistency store directory. If not provided,
                      uses default path data/consistency/.
            config_path: Optional path to config file (unused, kept for compatibility).
        """
        # Use default consistency directory if not provided
        if base_dir is None:
            base_dir = get_project_root() / ".consistency"
        self.store = ConsistencyStore(base_dir)
        
        # Initialize Qwen3 Engine
        try:
            qwen_out = get_project_root() / ".cache" / "qwen3_raw"
            self.qwen3_engine = Qwen3Engine(qwen_out)
            logger.info("Qwen3 Engine initialized")
        except Exception as e:
            logger.error("Failed to initialize Qwen3 Engine: %s", e)
            self.qwen3_engine = None

    @staticmethod
    def _concatenate_files(files: List[Path], output_path: Path) -> Optional[str]:
        """Concatenate WAV files using ffmpeg filter_complex to handle mismatched sample rates."""
        cmd = ["ffmpeg", "-y"]
        filter_str = ""
        
        # Add all inputs
        for i, fp in enumerate(files):
            cmd.extend(["-i", str(fp)])
            filter_str += f"[{i}:a]"
            
        # Add filter complex
        filter_str += f"concat=n={len(files)}:v=0:a=1[outa]"
        cmd.extend(["-filter_complex", filter_str, "-map", "[outa]", str(output_path)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("FFmpeg filter_complex concat error: %s", result.stderr[-300:])
            return None

        logger.info("Concatenated %d segments -> %s", len(files), output_path)
        return str(output_path)

    async def generate_chapter_audio(
        self,
        scenes: List[Dict],
        output_dir: Union[str, Path],
        default_voice: str = "narrator"
    ) -> List[Optional[str]]:
        """
        Generate audio for a full chapter using Qwen3 3-pass batch strategy.
        1. Collect all narration and dialogue.
        2. Narrator Pass (Batch).
        3. Voice Design Pass (Batch for new characters).
        4. Dialogue Pass (Batch).
        5. Stitch per scene.
        """
        if not self.qwen3_engine:
            logger.error("Qwen3 Engine not available. Cannot generate audio.")
            return [None] * len(scenes)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Collect Segments
        narrator_segments = [] # List of {text, mood, scene_idx, seg_idx}
        dialogue_segments = [] # List of {text, mood, speaker, scene_idx, seg_idx}
        characters_needed = set()
        
        for s_idx, scene in enumerate(scenes):
            # Parse sequence
            sequence = scene.get("sequence")
            # If no sequence, construct from text/dialogues legacy format
            if sequence is None:
                sequence = []
                narr = scene.get("narration", "")
                if narr:
                    sequence.append({"type": "narration", "text": narr})
                for d in scene.get("dialogues", []):
                    sequence.append({"type": "dialogue", "text": d["line"], "speaker": d["speaker"]})
                scene["sequence"] = sequence
            
            for seq_idx, item in enumerate(sequence):
                text = item.get("text", "").strip()
                if not text: continue
                
                if item.get("type") == "dialogue":
                    speaker = item.get("speaker", default_voice)
                    characters_needed.add(speaker)
                    dialogue_segments.append({
                        "text": text,
                        "mood": item.get("mood", ""),
                        "speaker": speaker,
                        "scene_idx": s_idx,
                        "seq_idx": seq_idx
                    })
                else:
                    narrator_segments.append({
                        "text": text,
                        "mood": item.get("mood", ""),
                        "scene_idx": s_idx,
                        "seq_idx": seq_idx
                    })

        # 2. Voice Design Pass
        chars_to_design = []
        for char_name in characters_needed:
            char_data = self.store.get_character(char_name) or {}
            if not char_data.get("voice_sample_path"):
                gender = char_data.get("gender", "male") 
                desc = char_data.get("voice_notes") or "Standard voice"
                sample_text = "I am ready."
                for d in dialogue_segments:
                    if d["speaker"] == char_name:
                        sample_text = d["text"][:100]
                        break
                
                chars_to_design.append({
                    "name": char_name,
                    "gender": gender,
                    "vocal_description": desc,
                    "sample_text": sample_text
                })

        if chars_to_design:
            logger.info(f"Designing voices for: {[c['name'] for c in chars_to_design]}")
            sample_files = self.qwen3_engine.generate_design_pass(chars_to_design)
            
            for char_def, sample_path in zip(chars_to_design, sample_files):
                self.store.update_character_voice(
                    name=char_def["name"],
                    voice_id=f"qwen3_{char_def['name']}",
                    voice_design_params={"gender": char_def["gender"], "description": char_def["vocal_description"]},
                    voice_sample_path=str(sample_path)
                )

        # 3. Narrator Pass
        logger.info(f"Generating {len(narrator_segments)} narration segments...")
        narrator_files = self.qwen3_engine.generate_narrator_pass(narrator_segments)
        
        # 4. Dialogue Pass
        for d in dialogue_segments:
            char_data = self.store.get_character(d["speaker"])
            if char_data:
                 # Prefer voice sample path, fall back to whatever is available
                 d["voice_sample_path"] = char_data.get("voice_sample_path")
        
        logger.info(f"Generating {len(dialogue_segments)} dialogue segments...")
        dialogue_files = self.qwen3_engine.generate_dialogue_pass(dialogue_segments)

        # 5. Assemble / Stitch
        audio_map = {}
        
        for seg, fpath in zip(narrator_segments, narrator_files):
            audio_map[(seg["scene_idx"], seg["seq_idx"])] = fpath
            
        for seg, fpath in zip(dialogue_segments, dialogue_files):
            audio_map[(seg["scene_idx"], seg["seq_idx"])] = fpath
            
        scene_outputs = []
        for s_idx in range(len(scenes)):
            scene = scenes[s_idx]
            sequence = scene.get("sequence", [])
            
            current_scene_segments = []
            for seq_idx, item in enumerate(sequence):
                fpath = audio_map.get((s_idx, seq_idx))
                if fpath:
                    current_scene_segments.append(fpath)
                    # Add silence
                    itype = item.get("type", "narration")
                    gap = SILENCE_GAP_DIALOGUE if itype == "dialogue" else SILENCE_GAP_NARRATION
                    
                    silence_path = output_dir / f"silence_{gap}.wav"
                    if not silence_path.exists():
                        _generate_silence_wav(gap, silence_path)
                    current_scene_segments.append(silence_path)
            
            if current_scene_segments:
                out_file = output_dir / f"scene_{s_idx:03d}.wav"
                result = self._concatenate_files(current_scene_segments, out_file)
                scene_outputs.append(result)
            else:
                scene_outputs.append(None)
                
        return scene_outputs
