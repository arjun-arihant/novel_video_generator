"""Image generation using WanGP CLI (headless mode).

Generates images by creating temporary JSON settings files and
invoking WanGP's CLI: python wgp.py --process settings.json --output-dir <dir>
Supports deterministic seed pinning for character consistency.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..common import retry_with_backoff
from ..consistency.store import ConsistencyStore

logger = logging.getLogger(__name__)

# Base settings template derived from z_image_settings.json
_BASE_SETTINGS = {
    "image_mode": 1,
    "alt_prompt": "",
    "negative_prompt": "",
    "resolution": "1920x1088",
    "video_length": 1,
    "batch_size": 1,
    "num_inference_steps": 8,
    "repeat_generation": 1,
    "multi_prompts_gen_type": 0,
    "multi_images_gen_type": 0,
    "loras_multipliers": "",
    "image_prompt_type": "",
    "video_prompt_type": "",
    "audio_prompt_type": "",
    "temporal_upsampling": "",
    "spatial_upsampling": "",
    "film_grain_intensity": 0,
    "film_grain_saturation": 0.5,
    "RIFLEx_setting": 0,
    "NAG_scale": 1,
    "NAG_tau": 3.5,
    "NAG_alpha": 0.5,
    "override_profile": -1,
    "override_attention": "",
    "output_filename": "",
    "mode": "",
    "activated_loras": [
        "z-image-anime-2.5D-01.safetensors"
    ],
    "type": "WanGP v10.9 by DeepBeepMeep - Z-Image Turbo 6B",
    "settings_version": 2.52,
    "model_filename": "https://huggingface.co/DeepBeepMeep/Z-Image/resolve/main/ZImageTurbo_quanto_bf16_int8.safetensors",
    "model_type": "z_image",
}


class ImageGenerator:
    """Generates images using WanGP CLI in headless mode."""

    def __init__(
        self,
        wangp_path: Optional[str] = None,
        conda_env: str = "wan2gp",
        profile: int = 4,
        attention: str = "sdpa",
        timeout: int = 300,
    ):
        self.wangp_dir = Path(wangp_path or os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP"))
        self.conda_env = conda_env
        self.profile = profile
        self.attention = attention
        self.timeout = timeout

        wgp_script = self.wangp_dir / "wgp.py"
        if not wgp_script.exists():
            raise FileNotFoundError(
                f"WanGP not found at {self.wangp_dir}. "
                f"Set WANGP_PATH env variable to your WanGP installation directory."
            )
        logger.info("WanGP found at: %s", self.wangp_dir)

    def _build_settings(self, prompt: str, output_filename: str = "", seed: Optional[int] = None) -> dict:
        """Build a settings dict for WanGP --process."""
        # Try to load user settings from project root, otherwise use defaults
        user_settings_path = Path("z_image_settings.json").resolve()
        if user_settings_path.exists():
            try:
                with open(user_settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                logger.info("Loaded user image settings from %s", user_settings_path)
            except Exception as e:
                logger.warning("Failed to load %s, using defaults: %s", user_settings_path, e)
                settings = dict(_BASE_SETTINGS)
        else:
            settings = dict(_BASE_SETTINGS)

        settings["prompt"] = prompt
        if output_filename:
            settings["output_filename"] = output_filename
        
        if seed is not None:
            settings["seed"] = seed
        elif settings.get("seed", -1) == -1:
            # If user set -1 or default is -1/missing, generate random seed
            import random
            settings["seed"] = random.randint(0, 2**31 - 1)
            
        return settings

    def generate(
        self,
        prompt: str,
        output_path: Union[str, Path],
        seed: Optional[int] = None,
    ) -> bool:
        """Generate an image from a text prompt via WanGP CLI."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._generate_with_retry(prompt, output_path, seed)
            return True
        except Exception as e:
            logger.error("Failed to generate image after retries: %s", e)
            return False

    def generate_for_scene(
        self,
        scene: Dict,
        output_path: Union[str, Path],
        store: Optional[ConsistencyStore] = None,
    ) -> bool:
        """Generate image for a scene with character seed pinning.

        Derives a deterministic seed from the primary character in the scene
        so the same character gets visually consistent generations.
        """
        prompt = scene.get("visual_description", "")
        if not prompt:
            logger.warning("Scene has no visual_description, skipping")
            return False

        # Use first character's seed for consistency, or random
        seed = None
        characters = scene.get("characters", [])
        if characters and store:
            primary_char = characters[0]
            seed = store.character_seed(primary_char)
            # Add scene id to seed so different scenes of same character differ slightly
            scene_id = scene.get("id", 0)
            seed = (seed + scene_id * 7919) % (2**31)
            logger.info("Seed for %s (scene %s): %d", primary_char, scene_id, seed)

        return self.generate(prompt, output_path, seed=seed)

    @retry_with_backoff(max_attempts=3, min_wait=5, max_wait=60)
    def _generate_with_retry(
        self,
        prompt: str,
        output_path: Path,
        seed: Optional[int],
    ) -> None:
        """Generate image with retry logic."""
        enhanced_prompt = self._enhance_prompt(prompt)
        logger.info("Generating image: %s...", enhanced_prompt[:80])

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            settings = self._build_settings(enhanced_prompt, seed=seed)
            settings_file = temp_path / "settings.json"
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

            output_dir = temp_path / "output"
            output_dir.mkdir()

            # Determine command based on configuration
            conda_activate = os.getenv("CONDA_ACTIVATE_PATH")
            if conda_activate and Path(conda_activate).exists():
                # Method 1: Explicit activation script (Most robust on Windows)
                cmd = (
                    f'call "{conda_activate}" {self.conda_env} && '
                    f'python wgp.py '
                    f'--process "{settings_file}" '
                    f'--output-dir "{output_dir}" '
                    f'--profile {self.profile} '
                    f'--attention {self.attention}'
                )
            else:
                # Method 2: 'conda run' (Requires conda in PATH)
                cmd = (
                    f'conda run -n {self.conda_env} '
                    f'python wgp.py '
                    f'--process "{settings_file}" '
                    f'--output-dir "{output_dir}" '
                    f'--profile {self.profile} '
                    f'--attention {self.attention}'
                )

            logger.debug("Running WanGP: %s", cmd)

            result = subprocess.run(
                cmd,
                # shell=True is needed for 'call' and 'conda' to work
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.wangp_dir),
                timeout=self.timeout,
            )

            if result.returncode != 0:
                logger.error("WanGP stderr: %s", result.stderr[-500:] if result.stderr else "")
                raise RuntimeError(
                    f"WanGP exited with code {result.returncode}: "
                    f"{result.stderr[-200:] if result.stderr else 'no stderr'}"
                )

            generated_files = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg"))
            if not generated_files:
                wangp_output = self.wangp_dir / "outputs"
                if wangp_output.exists():
                    generated_files = sorted(
                        wangp_output.glob("*.png"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    )

            if not generated_files:
                raise RuntimeError("WanGP produced no image files")

            source_image = generated_files[0]
            shutil.copy2(source_image, output_path)
            logger.info("Image saved to %s (seed=%s)", output_path, seed)

    @staticmethod
    def _enhance_prompt(prompt: str) -> str:
        """Enhance prompt with style tags if not already present."""
        style_suffix = (
            ", detailed cinematic manhua webtoon style, "
            "clean line art, vibrant colors, soft depth of field, "
            "4k resolution, consistent character design"
        )
        if "manhua" not in prompt.lower() and "consistent character" not in prompt.lower():
            return f"{prompt}{style_suffix}"
        return prompt
