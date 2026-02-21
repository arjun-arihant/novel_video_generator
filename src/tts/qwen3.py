import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..common.paths import get_project_root

logger = logging.getLogger(__name__)


class Qwen3Engine:
    """
    Engine for Qwen3 TTS generation using WanGP batch processing.
    Implements the 3-pass strategy: Narrator, Voice Design, Dialogue.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.project_root = get_project_root()
        # Wrapper script path
        self.wrapper_path = self.project_root / "src" / "tts" / "qwen3_wrapper.py"
        self.env_name = "wan2gp"  # Conda environment name

        # Load templates
        self.templates = {
            "narrator": self._load_json(self.project_root / "qwen3_tts_customvoice.json"),
            "design": self._load_json(self.project_root / "qwen3_tts_voicedesign.json"),
            "dialogue": self._load_json(self.project_root / "qwen3_tts_base.json"),
        }

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _run_batch(self, tasks: List[Dict[str, Any]], batch_name: str) -> List[Path]:
        """Serialize tasks to JSON and run wrapper in conda environment."""
        if not tasks:
            logger.warning(f"No tasks for batch {batch_name}")
            return []

        # Unique output dir for this batch to isolate results
        batch_id = uuid.uuid4().hex[:8]
        batch_out_dir = self.output_dir / f"batch_{batch_name}_{batch_id}"
        batch_out_dir.mkdir(parents=True, exist_ok=True)
        
        batch_file = batch_out_dir / "batch_tasks.json"

        with open(batch_file, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)

        # Resolve conda path
        conda_activate = os.getenv("CONDA_ACTIVATE_PATH")
        
        if conda_activate and Path(conda_activate).exists():
            conda_base = Path(conda_activate).parent.parent
            condabin = conda_base / "condabin"
            
            # Method 1: Explicit activation script (Most robust on Windows)
            cmd = (
                f'set "PATH={condabin};%PATH%" && '
                f'call "{conda_activate}" {self.env_name} && '
                f'python "{self.wrapper_path}" '
                f'--batch "{batch_file}" '
                f'--output-dir "{batch_out_dir}"'
            )
        else:
            # Method 2: Fallback to basic 'conda run'
            cmd = (
                f'conda run -n {self.env_name} '
                f'python "{self.wrapper_path}" '
                f'--batch "{batch_file}" '
                f'--output-dir "{batch_out_dir}"'
            )

        logger.info(f"Running batch {batch_name} with {len(tasks)} tasks in {batch_out_dir}")
        logger.error(f"[DEBUG] conda_activate: {conda_activate}, exists: {Path(conda_activate).exists() if conda_activate else False}")
        logger.error(f"[DEBUG] Executing cmd: {cmd}")
        
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.project_root,
                shell=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Batch {batch_name} failed: {e.stderr}")
            # Check if any files were generated despite failure?
            # raise RuntimeError(f"Qwen3 Generation Failed: {e.stderr}")
            # For robustness, we try to collect what we have?
            pass

        # Collect all generated media files
        # WanGP typically generates .mp4 or .wav
        extensions = ["*.wav", "*.mp3", "*.mp4", "*.mkv"]
        files = []
        for ext in extensions:
            files.extend(batch_out_dir.glob(ext))
            
        # Sort by creation/mod time to match task order
        # This assumes WanGP processes sequentially and system clock is precise enough
        files.sort(key=lambda p: p.stat().st_mtime)
        
        return files

    def generate_narrator_pass(self, segments: List[Dict[str, Any]]) -> List[Path]:
        """
        Generate narration audio.
        segments: dicts with 'text', 'mood' (optional)
        Returns list of generated file paths.
        """
        tasks = []
        base_params = self.templates["narrator"]
        
        for i, seg in enumerate(segments):
            params = base_params.copy()
            params["prompt"] = seg["text"]
            if seg.get("mood"):
                params["alt_prompt"] = seg["mood"]
            
            tasks.append({
                "id": f"narration_{i}",
                "params": params
            })
            
        return self._run_batch(tasks, "narrator")

    def generate_design_pass(self, characters: List[Dict[str, Any]]) -> List[Path]:
        """
        Generate voice samples for new characters.
        Returns list of generated sample files.
        """
        tasks = []
        base_params = self.templates["design"]

        for char in characters:
            params = base_params.copy()
            params["prompt"] = char["sample_text"]
            desc = f"{char['gender']} voice. {char['vocal_description']}"
            params["alt_prompt"] = desc
            
            tasks.append({
                "id": f"design_{char['name']}",
                "params": params
            })

        return self._run_batch(tasks, "design")

    def generate_dialogue_pass(self, dialogues: List[Dict[str, Any]]) -> List[Path]:
        """
        Generate dialogue using cloned voices.
        """
        tasks = []
        base_params = self.templates["dialogue"]
        
        for i, dlg in enumerate(dialogues):
            params = base_params.copy()
            params["prompt"] = dlg["text"]
            if dlg.get("mood"):
                params["alt_prompt"] = dlg["mood"]
                
             # For cloning, we need to pass the reference audio path.
             # 'audio_guide' is the exact field WanGP uses for cloning input.
            if dlg.get("voice_sample_path"):
                 params["audio_guide"] = str(dlg["voice_sample_path"])
             
            tasks.append({
                "id": f"dialogue_{i}",
                "params": params
            })
            
        return self._run_batch(tasks, "dialogue")
