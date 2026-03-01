"""
Stage 6: Prompt Builder
Pure Python — no LLM calls.
Composes image prompts and TTS prompts from DB state and scene data.
"""
import json
import logging
from pathlib import Path

from config import novel_path

logger = logging.getLogger(__name__)

# ─── Modifier Dictionaries ────────────────────────────────────────────────────

TIME_OF_DAY_MODIFIERS = {
    "morning":   "soft warm golden light, long shadows, early morning atmosphere",
    "afternoon": "bright daylight, clear sharp shadows, midday natural lighting",
    "evening":   "warm orange-pink sunset hues, long shadows, dusk atmosphere",
    "night":     "dark dramatic shadows, cool moonlight or artificial light pools",
    "unknown":   "diffused neutral lighting",
}

MOOD_MODIFIERS = {
    "tense":     "dramatic lighting, high contrast, oppressive visual weight",
    "happy":     "bright warm tones, open composition, uplifting visual clarity",
    "sad":       "desaturated tones, soft diffuse light, heavy visual silence",
    "angry":     "harsh lighting, deep shadows, saturated reds, aggressive angles",
    "fearful":   "deep shadows, extreme contrast, claustrophobic framing",
    "excited":   "dynamic composition, vibrant colors, energetic visual rhythm",
    "tender":    "soft diffuse light, warm gentle tones, intimate closeness",
    "mysterious":"low-key lighting, veiled details, cool atmospheric haze",
    "peaceful":  "balanced light, muted palette, calm expansive framing",
}

NARRATOR_STYLE = "calm, measured, slightly serious narrator"
MAX_IMAGE_PROMPT_WORDS = 200


def _truncate_prompt(prompt: str, max_words: int = MAX_IMAGE_PROMPT_WORDS) -> str:
    words = prompt.split()
    if len(words) <= max_words:
        return prompt
    return " ".join(words[:max_words])


def _build_image_prompt(
    scene: dict, char_db: dict, loc_db: dict
) -> str:
    """Compose a full image generation prompt for a scene."""
    parts = []

    # Characters and their current visual state
    characters = scene.get("characters_present", [])
    for char_name in characters:
        char = char_db.get("characters", {}).get(char_name)
        if not char:
            continue
        base = char.get("base_visual_prompt", "")
        state = char.get("current_state", {})
        state_mods = []
        if state.get("clothing"):
            state_mods.append(f"wearing {state['clothing']}")
        if state.get("injury"):
            state_mods.append(state["injury"])
        if state_mods:
            parts.append(f"{base}, {', '.join(state_mods)}")
        else:
            parts.append(base)

    # Scene visual description
    visual = scene.get("visual_description", "").strip()
    if visual:
        parts.append(visual)

    # Location
    loc_name = scene.get("location_name", "")
    loc = loc_db.get("locations", {}).get(loc_name)
    if loc:
        parts.append(loc.get("base_visual_prompt", ""))

    # Time of day modifier
    tod = scene.get("time_of_day", "unknown")
    parts.append(TIME_OF_DAY_MODIFIERS.get(tod, TIME_OF_DAY_MODIFIERS["unknown"]))

    # Mood modifier
    mood = scene.get("mood", "").lower()
    mood_mod = MOOD_MODIFIERS.get(mood, "")
    if mood_mod:
        parts.append(mood_mod)

    prompt = ", ".join(p for p in parts if p.strip())
    return _truncate_prompt(prompt)


def _build_tts_entry(
    item: dict,
    scene_id: int,
    seq_index: int,
    char_db: dict,
    narrator_style: str = NARRATOR_STYLE,
) -> dict:
    """Build a TTS prompt metadata entry for one sequence item."""
    item_type = item.get("type", "narration")
    emotion = item.get("emotion", "neutral")
    text = item.get("text", "")

    if item_type == "narration":
        return {
            "type": "narration",
            "scene_id": scene_id,
            "seq_index": seq_index,
            "text": text,
            "emotion": emotion,
            "voice_type": "customvoice",
            "alt_prompt": f"{narrator_style}, {emotion} tone",
        }
    else:
        speaker = item.get("speaker", "")
        char = char_db.get("characters", {}).get(speaker, {})
        voice_profile = char.get("voice_profile", {})
        voice_type = voice_profile.get("voice_type", "fallback")

        return {
            "type": "dialogue",
            "scene_id": scene_id,
            "seq_index": seq_index,
            "speaker": speaker,
            "text": text,
            "emotion": emotion,
            "voice_type": voice_type,
            "voice_reference_file": voice_profile.get("voice_reference_file", ""),
            "voice_design_prompt": voice_profile.get("voice_design_prompt", ""),
            "alt_prompt": emotion,  # emotion only for base model
        }


def build_prompts_for_chapter(book_slug: str, chapter_id: int) -> str:
    """
    Build all image + TTS prompts for a chapter and write prompts_ch{N}.json.
    Returns the output path.
    """
    out_path = novel_path(book_slug, "prompts", f"prompts_ch{chapter_id}.json")
    if Path(out_path).exists():
        logger.debug(f"Stage 6 — prompts_ch{chapter_id}.json exists, skipping.")
        return out_path

    canonical_path = novel_path(
        book_slug, "chapters", "scenes", f"scenes_canonical_ch{chapter_id}.json"
    )
    char_db = json.loads(
        Path(novel_path(book_slug, "db", "character_db.json")).read_text(encoding="utf-8")
    )
    loc_db = json.loads(
        Path(novel_path(book_slug, "db", "location_db.json")).read_text(encoding="utf-8")
    )
    scenes_data = json.loads(Path(canonical_path).read_text(encoding="utf-8"))

    output_scenes = []
    for scene in scenes_data.get("scenes", []):
        scene_id = scene["scene_id"]
        image_prompt = _build_image_prompt(scene, char_db, loc_db)
        tts_entries = []
        for idx, item in enumerate(scene.get("sequence", [])):
            tts_entries.append(_build_tts_entry(item, scene_id, idx, char_db))

        output_scenes.append({
            "scene_id": scene_id,
            "image_prompt": image_prompt,
            "tts_entries": tts_entries,
        })

    result = {
        "schema_version": 1,
        "chapter_id": chapter_id,
        "scenes": output_scenes,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Stage 6 — Built prompts for chapter {chapter_id}.")
    return out_path
