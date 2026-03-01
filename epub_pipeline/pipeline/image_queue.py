"""
Stage 7: Image Queue Builder
Generates Wan2GP z_image queue JSON for all scenes in a chapter.
"""
import hashlib
import json
import logging
from pathlib import Path

from config import novel_path, IMAGE_RESOLUTION, IMAGE_LORAS, IMAGE_INFERENCE_STEPS, IMAGE_NEGATIVE_PROMPT

logger = logging.getLogger(__name__)


def _compute_seed(label: str) -> int:
    """Deterministic seed from sha256. Safe across Python sessions (unlike hash())."""
    return int(hashlib.sha256(label.encode()).hexdigest(), 16) % 2_147_483_647


def _image_task(task_id: int, prompt: str, seed: int, output_filename: str) -> dict:
    return {
        "id": task_id,
        "params": {
            "image_mode": 1,
            "prompt": prompt,
            "alt_prompt": "",
            "negative_prompt": IMAGE_NEGATIVE_PROMPT,
            "resolution": IMAGE_RESOLUTION,
            "video_length": 1,           # 1 = still image output
            "duration_seconds": 0,
            "pause_seconds": 0,
            "batch_size": 1,
            "seed": seed,
            "force_fps": "",
            "num_inference_steps": IMAGE_INFERENCE_STEPS,
            "guidance_scale": 0,
            "guidance2_scale": 5,
            "guidance3_scale": 5,
            "switch_threshold": 0,
            "switch_threshold2": 0,
            "guidance_phases": 1,
            "model_switch_phase": 1,
            "alt_guidance_scale": 1,
            "audio_guidance_scale": 4,
            "audio_scale": 1,
            "flow_shift": 5,
            "sample_solver": "",
            "embedded_guidance_scale": 6,
            "repeat_generation": 1,
            "multi_prompts_gen_type": 0,
            "multi_images_gen_type": 0,
            "skip_steps_cache_type": "",
            "skip_steps_multiplier": 1.75,
            "skip_steps_start_step_perc": 0,
            "loras_multipliers": "",
            "image_prompt_type": "",
            "image_start": None,
            "image_end": None,
            "model_mode": None,
            "video_source": None,
            "keep_frames_video_source": "",
            "input_video_strength": 1.0,
            "video_guide_outpainting": "",
            "video_prompt_type": "",
            "image_refs": None,
            "frames_positions": None,
            "video_guide": None,
            "image_guide": None,
            "keep_frames_video_guide": "",
            "denoising_strength": 1.0,
            "masking_strength": 1.0,
            "video_mask": None,
            "image_mask": None,
            "control_net_weight": 1,
            "control_net_weight2": 1,
            "control_net_weight_alt": 1,
            "motion_amplitude": 1.0,
            "mask_expand": 0,
            "audio_guide": None,
            "audio_guide2": None,
            "custom_guide": None,
            "audio_source": None,
            "audio_prompt_type": "",
            "speakers_locations": "0:45 55:100",
            "sliding_window_size": 81,
            "sliding_window_overlap": 5,
            "sliding_window_color_correction_strength": 0,
            "sliding_window_overlap_noise": 0,
            "sliding_window_discard_last_frames": 0,
            "image_refs_relative_size": 50,
            "remove_background_images_ref": 1,
            "temporal_upsampling": "",
            "spatial_upsampling": "",
            "film_grain_intensity": 0,
            "film_grain_saturation": 0.5,
            "MMAudio_setting": 0,
            "MMAudio_prompt": "",
            "MMAudio_neg_prompt": "",
            "RIFLEx_setting": 0,
            "NAG_scale": 1,
            "NAG_tau": 3.5,
            "NAG_alpha": 0.5,
            "slg_switch": 0,
            "slg_layers": [9],
            "slg_start_perc": 10,
            "slg_end_perc": 90,
            "apg_switch": 0,
            "cfg_star_switch": 0,
            "cfg_zero_step": -1,
            "prompt_enhancer": "",
            "min_frames_if_references": 1,
            "override_profile": -1,
            "override_attention": "",
            "temperature": 0.8,
            "top_p": 0.9,
            "top_k": 50,
            "self_refiner_setting": 0,
            "self_refiner_plan": [],
            "self_refiner_f_uncertainty": 0,
            "self_refiner_certain_percentage": 0.999,
            "output_filename": output_filename,
            "mode": "",
            "activated_loras": IMAGE_LORAS,
            "custom_settings": None,
            "model_type": "z_image",
            "settings_version": 2.52,
            "base_model_type": "z_image",
        },
    }


def build_image_queue(book_slug: str, chapter_id: int) -> str:
    """
    Build Wan2GP image queue for all scenes in a chapter.
    Returns path to image_queue_ch{N}.json.
    """
    out_path = novel_path(book_slug, "queues", f"image_queue_ch{chapter_id}.json")
    if Path(out_path).exists():
        logger.debug(f"Stage 7 — image_queue_ch{chapter_id}.json exists, skipping.")
        return out_path

    prompts_path = novel_path(book_slug, "prompts", f"prompts_ch{chapter_id}.json")
    prompts_data = json.loads(Path(prompts_path).read_text(encoding="utf-8"))

    queue = []
    for task_id, scene in enumerate(prompts_data["scenes"], start=1):
        scene_id = scene["scene_id"]
        prompt = scene["image_prompt"]

        # Seed strategy: single-character scenes use character seed; others use scene seed
        # We re-read canonical scenes to get characters_present count
        canonical_path = novel_path(
            book_slug, "chapters", "scenes", f"scenes_canonical_ch{chapter_id}.json"
        )
        canonical_data = json.loads(Path(canonical_path).read_text(encoding="utf-8"))
        scene_data = next(
            (s for s in canonical_data["scenes"] if s["scene_id"] == scene_id), {}
        )
        chars = scene_data.get("characters_present", [])

        if len(chars) == 1:
            seed = _compute_seed(chars[0])
        else:
            seed = _compute_seed(f"{chapter_id}_{scene_id}")

        output_filename = str(
            Path(novel_path(book_slug, "images", f"ch{chapter_id}", f"scene_{scene_id:03d}.png"))
        )
        # Ensure output directory exists
        Path(output_filename).parent.mkdir(parents=True, exist_ok=True)

        queue.append(_image_task(task_id, prompt, seed, output_filename))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        f"Stage 7 — image_queue_ch{chapter_id}.json written ({len(queue)} tasks)."
    )
    return out_path
