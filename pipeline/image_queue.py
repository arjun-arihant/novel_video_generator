"""
Stage 8: Image Queue Builder
Builds Wan2GP queue ZIP files from visual prompts for image generation.
"""
import json
import logging
import zipfile
from pathlib import Path

from pipeline.config import (
    novel_path,
    IMAGE_RESOLUTION,
    IMAGE_LORAS,
    IMAGE_INFERENCE_STEPS,
    IMAGE_NEGATIVE_PROMPT,
    IMAGE_VIDEO_LENGTH,
)

logger = logging.getLogger(__name__)

IMAGE_BASE_PARAMS = {
    "image_mode": 1,
    "alt_prompt": "",
    "negative_prompt": "",
    "resolution": IMAGE_RESOLUTION,
    "video_length": IMAGE_VIDEO_LENGTH,
    "duration_seconds": 0,
    "pause_seconds": 0,
    "batch_size": 1,
    "seed": -1,
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
    "keep_frames_video_source": "",
    "input_video_strength": 1.0,
    "video_guide_outpainting": "",
    "video_prompt_type": "",
    "keep_frames_video_guide": "",
    "denoising_strength": 1.0,
    "masking_strength": 1.0,
    "control_net_weight": 1,
    "control_net_weight2": 1,
    "control_net_weight_alt": 1,
    "motion_amplitude": 1.0,
    "mask_expand": 0,
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
    "mode": "",
    "activated_loras": IMAGE_LORAS,
    "model_type": "z_image",
    "settings_version": 2.52,
    "base_model_type": "z_image"
}


def build_image_queue(book_slug: str, chapter_id: int) -> str:
    """
    Build a Wan2GP image generation queue from visual prompts.

    Returns path to the queue ZIP file.
    """
    queue_zip_path = Path(novel_path(
        book_slug, "queues", f"image_queue_ch{chapter_id}.zip"
    ))
    if queue_zip_path.exists():
        logger.debug(f"Stage 8 — Image queue for ch{chapter_id} exists, skipping.")
        return str(queue_zip_path)

    prompts_path = Path(novel_path(
        book_slug, "prompts", f"visual_prompts_ch{chapter_id}.json"
    ))
    if not prompts_path.exists():
        logger.error(f"Stage 8 — No visual prompts for ch{chapter_id}.")
        return ""

    prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
    queue = []

    for prompt_data in prompts:
        scene_id = prompt_data["scene_id"]
        visual_prompt = prompt_data.get("visual_prompt", "")
        negative_prompt = prompt_data.get("negative_prompt", IMAGE_NEGATIVE_PROMPT)

        # We just want the base name without extension, Wan2GP will add .jpg
        output_filename = f"scene_{scene_id:03d}"

        # Ensure output directory exists regardless
        out_path = Path(novel_path(book_slug, "images", f"ch{chapter_id}"))
        out_path.mkdir(parents=True, exist_ok=True)

        params = dict(IMAGE_BASE_PARAMS)
        params.update({
            "prompt": visual_prompt,
            "negative_prompt": negative_prompt,
            "output_filename": output_filename,
        })
        
        # We need to filter out `null` objects properly matching Wan2GP's spec, but
        # providing nulls explicitly if they exist in the sample payload just to be safe.
        for null_key in ["image_start", "image_end", "model_mode", "video_source", "image_refs", 
                         "frames_positions", "video_guide", "image_guide", "video_mask", "image_mask", 
                         "audio_guide", "audio_guide2", "custom_guide", "audio_source", "custom_settings"]:
            params[null_key] = None

        queue.append({"id": scene_id, "params": params})

    queue_zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON into a temporary file or directly to the ZIP
    json_data = json.dumps(queue, indent=2, ensure_ascii=False)
    
    with zipfile.ZipFile(str(queue_zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("queue.json", json_data)

    logger.info(f"Stage 8 — Image queue ZIP for ch{chapter_id}: {len(queue)} tasks.")
    return str(queue_zip_path)
