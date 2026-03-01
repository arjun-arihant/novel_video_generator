"""
Stage 8: Audio Queue Builder
Generates three separate Wan2GP TTS queue files per chapter:
  Pass A — qwen3_tts_voicedesign: new character voice design
  Pass B — qwen3_tts_customvoice: narrator + fallback-voice characters
  Pass C — qwen3_tts_base: character dialogue with voice cloning
"""
import json
import logging
from pathlib import Path

from config import (
    novel_path,
    NARRATOR_VOICE_ID,
    FALLBACK_VOICE_ID,
    MAX_NEW_CHARACTERS_PER_CHAPTER,
)

logger = logging.getLogger(__name__)

TTS_BASE_PARAMS = {
    "image_mode": 0,
    "resolution": "832x480",
    "video_length": 0,
    "duration_seconds": 30,
    "batch_size": 1,
    "seed": -1,
    "repeat_generation": 1,
    "multi_prompts_gen_type": 2,
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
    "override_profile": -1,
    "override_attention": "",
    "temperature": 0.9,
    "top_k": 50,
    "mode": "",
    "activated_loras": [],
    "settings_version": 2.52,
}


def _tts_task(task_id: int, overrides: dict) -> dict:
    params = dict(TTS_BASE_PARAMS)
    params.update(overrides)
    return {"id": task_id, "params": params}


def _audio_output_path(book_slug: str, chapter_id: int, scene_id: int, seq_index: int) -> str:
    path = Path(
        novel_path(
            book_slug, "audio", f"ch{chapter_id}",
            f"seq_{scene_id:03d}_{seq_index:03d}.wav",
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def build_audio_queues(book_slug: str, chapter_id: int) -> tuple[str, str, str]:
    """
    Build all three TTS queues for a chapter.
    Returns (pass_a_path, pass_b_path, pass_c_path).
    """
    q_dir = Path(novel_path(book_slug, "queues"))
    q_dir.mkdir(parents=True, exist_ok=True)

    pass_a_path = str(q_dir / f"audio_queue_ch{chapter_id}_pass_a.json")
    pass_b_path = str(q_dir / f"audio_queue_ch{chapter_id}_pass_b.json")
    pass_c_path = str(q_dir / f"audio_queue_ch{chapter_id}_pass_c.json")

    if Path(pass_a_path).exists() and Path(pass_b_path).exists() and Path(pass_c_path).exists():
        logger.debug(f"Stage 8 — Audio queue files for ch{chapter_id} exist, skipping.")
        return pass_a_path, pass_b_path, pass_c_path

    prompts_path = novel_path(book_slug, "prompts", f"prompts_ch{chapter_id}.json")
    prompts_data = json.loads(Path(prompts_path).read_text(encoding="utf-8"))

    char_db_path = novel_path(book_slug, "db", "character_db.json")
    char_db = json.loads(Path(char_db_path).read_text(encoding="utf-8"))
    characters = char_db.get("characters", {})

    # Gather all new characters needing voice design (no ref wav on disk yet)
    new_char_dialogue_counts: dict[str, int] = {}

    for scene in prompts_data["scenes"]:
        for entry in scene["tts_entries"]:
            if entry["type"] == "dialogue":
                speaker = entry["speaker"]
                if speaker not in new_char_dialogue_counts:
                    ref_file = characters.get(speaker, {}).get(
                        "voice_profile", {}
                    ).get("voice_reference_file", "")
                    if not Path(ref_file).exists():
                        new_char_dialogue_counts[speaker] = 0
                if speaker in new_char_dialogue_counts:
                    new_char_dialogue_counts[speaker] += 1

    # Apply character cap: top N by dialogue count get voice design, rest get fallback
    sorted_new = sorted(new_char_dialogue_counts.items(), key=lambda x: -x[1])
    top_n = [name for name, _ in sorted_new[:MAX_NEW_CHARACTERS_PER_CHAPTER]]
    fallback_chars = {name for name, _ in sorted_new[MAX_NEW_CHARACTERS_PER_CHAPTER:]}

    # Mark fallback in character_db
    if fallback_chars:
        for name in fallback_chars:
            if name in characters:
                characters[name]["used_fallback_voice"] = True
        Path(char_db_path).write_text(
            json.dumps(char_db, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ── Pass A: Voice Design ──────────────────────────────────────────────────
    pass_a: list[dict] = []
    designed_chars: set[str] = set()

    for task_id, char_name in enumerate(top_n, start=1):
        char = characters.get(char_name, {})
        voice_profile = char.get("voice_profile", {})
        ref_wav_path = voice_profile.get("voice_reference_file", "")

        # Pick a neutral intro line from first dialogue occurrence
        intro_text = f"Hello. My name is {char_name}. I've been looking forward to meeting you."
        for scene in prompts_data["scenes"]:
            for entry in scene["tts_entries"]:
                if entry.get("speaker") == char_name and entry["type"] == "dialogue":
                    intro_text = entry["text"]
                    break

        Path(ref_wav_path).parent.mkdir(parents=True, exist_ok=True)

        pass_a.append(_tts_task(task_id, {
            "prompt": intro_text,
            "alt_prompt": voice_profile.get("voice_design_prompt", ""),
            "model_mode": "auto",
            "output_filename": str(ref_wav_path),
            "model_type": "qwen3_tts_voicedesign",
        }))
        designed_chars.add(char_name)

    # ── Pass B: Narrator / Custom Voice ───────────────────────────────────────
    pass_b: list[dict] = []
    task_id_b = 1

    for scene in prompts_data["scenes"]:
        for entry in scene["tts_entries"]:
            scene_id = entry["scene_id"]
            seq_index = entry["seq_index"]
            output_wav = _audio_output_path(book_slug, chapter_id, scene_id, seq_index)

            if entry["type"] == "narration":
                pass_b.append(_tts_task(task_id_b, {
                    "prompt": entry["text"],
                    "alt_prompt": entry.get("alt_prompt", "calm, measured narrator"),
                    "model_mode": NARRATOR_VOICE_ID,
                    "output_filename": output_wav,
                    "model_type": "qwen3_tts_customvoice",
                }))
                task_id_b += 1

            elif entry["type"] == "dialogue" and entry.get("speaker") in fallback_chars:
                # Fallback-voice character lines → custom voice pass
                emotion = entry.get("emotion", "neutral")
                pass_b.append(_tts_task(task_id_b, {
                    "prompt": entry["text"],
                    "alt_prompt": f"{NARRATOR_VOICE_ID} voice, {emotion} tone",
                    "model_mode": FALLBACK_VOICE_ID,
                    "output_filename": output_wav,
                    "model_type": "qwen3_tts_customvoice",
                }))
                task_id_b += 1

    # ── Pass C: Character Dialogue / Voice Cloning ────────────────────────────
    pass_c: list[dict] = []
    task_id_c = 1

    for scene in prompts_data["scenes"]:
        for entry in scene["tts_entries"]:
            if entry["type"] != "dialogue":
                continue
            speaker = entry.get("speaker", "")
            if speaker in fallback_chars:
                continue  # already handled in pass B

            scene_id = entry["scene_id"]
            seq_index = entry["seq_index"]
            output_wav = _audio_output_path(book_slug, chapter_id, scene_id, seq_index)

            char = characters.get(speaker, {})
            voice_profile = char.get("voice_profile", {})
            ref_file = voice_profile.get("voice_reference_file", "")

            pass_c.append(_tts_task(task_id_c, {
                "prompt": entry["text"],
                "alt_prompt": entry.get("alt_prompt", entry.get("emotion", "neutral")),
                "model_mode": "auto",
                "audio_prompt_type": "A",
                "audio_guide": str(ref_file),
                "output_filename": output_wav,
                "model_type": "qwen3_tts_base",
            }))
            task_id_c += 1

    # Write queue files
    Path(pass_a_path).write_text(
        json.dumps(pass_a, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    Path(pass_b_path).write_text(
        json.dumps(pass_b, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    Path(pass_c_path).write_text(
        json.dumps(pass_c, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info(
        f"Stage 8 — Audio queues written: "
        f"Pass A ({len(pass_a)} voice designs), "
        f"Pass B ({len(pass_b)} narrator/fallback), "
        f"Pass C ({len(pass_c)} character dialogue)."
    )
    return pass_a_path, pass_b_path, pass_c_path
