"""
Stage 7: Prompt Builder
Generates visual prompts (for Wan2GP images) and TTS prompts from canonical scenes.
Also builds character_db.json for voice assignment.
"""
import json
import logging
from pathlib import Path

from pipeline.config import novel_path
from llm.client import call_llm
from llm.prompts import VISUAL_PROMPT_REFINEMENT_SYSTEM, VISUAL_PROMPT_REFINEMENT_USER

logger = logging.getLogger(__name__)


def _build_character_db(book_slug: str, chapter_ids: list[int]) -> dict:
    """
    Build or update a unified character database from all canonical scenes.
    Tracks character appearances and prepares voice profile stubs.
    """
    db_path = Path(novel_path(book_slug, "db", "character_db.json"))
    if db_path.exists():
        db = json.loads(db_path.read_text(encoding="utf-8"))
    else:
        db = {"characters": {}}

    for cid in chapter_ids:
        canon_path = Path(novel_path(
            book_slug, "chapters", "scenes", f"scenes_canonical_ch{cid}.json"
        ))
        if not canon_path.exists():
            continue

        data = json.loads(canon_path.read_text(encoding="utf-8"))
        for scene in data.get("scenes", []):
            for char_name in scene.get("characters_present", []):
                if not char_name or char_name == "NARRATOR":
                    continue

                if char_name not in db["characters"]:
                    db["characters"][char_name] = {
                        "name": char_name,
                        "first_appearance": {"chapter": cid, "scene": scene["scene_id"]},
                        "appearances": [],
                        "dialogue_count": 0,
                        "voice_profile": {
                            "type": "custom",
                            "voice": "Aiden",
                            "character_style": "",
                            "voice_design_prompt": "",
                            "voice_reference_file": "",
                        },
                    }

                char_entry = db["characters"][char_name]
                char_entry["appearances"].append(
                    {"chapter": cid, "scene": scene["scene_id"]}
                )

            # Count dialogue lines
            for entry in scene.get("sequence", []):
                if entry.get("type") == "dialogue":
                    speaker = entry.get("speaker", "")
                    if speaker and speaker != "NARRATOR" and speaker in db["characters"]:
                        db["characters"][speaker]["dialogue_count"] += 1

    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(
        json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Stage 7 — Character DB: {len(db['characters'])} characters tracked.")
    return db


def _build_visual_prompts(
    book_slug: str, chapter_id: int, scenes_data: dict, char_db: dict
) -> list[dict]:
    """Build visual prompts for each scene, optionally refined by LLM (Pass 4)."""
    prompts_path = Path(novel_path(
        book_slug, "prompts", f"visual_prompts_ch{chapter_id}.json"
    ))
    if prompts_path.exists():
        return json.loads(prompts_path.read_text(encoding="utf-8"))

    scenes = scenes_data.get("scenes", [])

    # Build character description reference
    char_descs = {}
    for name, info in char_db.get("characters", {}).items():
        style = info.get("voice_profile", {}).get("character_style", "")
        char_descs[name] = style or f"A character named {name}"

    # Prepare scene summaries for LLM
    scene_summaries = []
    for scene in scenes:
        scene_summaries.append({
            "scene_id": scene["scene_id"],
            "location": scene.get("location_name", "Unknown"),
            "characters": scene.get("characters_present", []),
            "description": scene.get("visual_description", ""),
            "mood": scene.get("mood", "neutral"),
        })

    try:
        result = call_llm(
            system_prompt=VISUAL_PROMPT_REFINEMENT_SYSTEM,
            user_prompt=VISUAL_PROMPT_REFINEMENT_USER.format(
                character_descriptions_json=json.dumps(char_descs, ensure_ascii=False),
                scenes_json=json.dumps(scene_summaries, indent=2, ensure_ascii=False),
            ),
            book_slug=book_slug,
            call_label=f"visual_prompt_refinement_ch{chapter_id}",
            expect_json=True,
            max_tokens=4096,
        )
        prompts = result.get("prompts", [])
    except Exception as e:
        logger.warning(f"Stage 7 — Visual prompt refinement failed: {e}. Using raw descriptions.")
        prompts = [
            {
                "scene_id": s["scene_id"],
                "visual_prompt": s.get("visual_description", "A scene from the story."),
                "negative_prompt": "blurry, low quality, watermark, text, ugly, deformed",
            }
            for s in scenes
        ]

    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    prompts_path.write_text(
        json.dumps(prompts, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Stage 7 — Built {len(prompts)} visual prompts for ch{chapter_id}")
    return prompts


def _build_tts_entries_from_scenes(book_slug: str, chapter_id: int, scenes_data: dict) -> dict:
    """
    Fallback: Build TTS entries from scene data with generic instruct.
    Only used when no Alexandria annotated/reviewed script exists.
    """
    scenes = scenes_data.get("scenes", [])
    all_entries = []
    seq_global = 0

    for scene in scenes:
        scene_id = scene["scene_id"]
        for i, item in enumerate(scene.get("sequence", [])):
            entry_type = item.get("type", "narration")
            speaker = item.get("speaker", "NARRATOR")
            text = item.get("text", "").strip()

            if not text:
                continue

            if entry_type == "narration":
                instruct = f"Calm, measured narration. {scene.get('mood', 'neutral')} atmosphere."
            else:
                instruct = f"In-character dialogue delivery. {scene.get('mood', 'neutral')} mood."

            all_entries.append({
                "scene_id": scene_id,
                "seq_index": i,
                "global_index": seq_global,
                "type": entry_type,
                "speaker": speaker,
                "text": text,
                "instruct": instruct,
            })
            seq_global += 1

    return {
        "chapter_id": chapter_id,
        "entries": all_entries,
        "total_entries": len(all_entries),
    }


def _build_tts_entries(book_slug: str, chapter_id: int, scenes_data: dict) -> dict:
    """
    Build TTS entry list from Alexandria's reviewed/annotated script.

    Prefers the reviewed script (post-LLM-correction) over the raw annotated
    script. Each entry carries the LLM-generated `instruct` field that
    describes emotion, tone, and delivery for the TTS engine.

    Falls back to generic scene-based instruct if no annotated script exists.
    """
    tts_path = Path(novel_path(
        book_slug, "prompts", f"tts_entries_ch{chapter_id}.json"
    ))
    if tts_path.exists():
        return json.loads(tts_path.read_text(encoding="utf-8"))

    # Try to read Alexandria's reviewed script first, then annotated
    reviewed_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"reviewed_script_ch{chapter_id}.json"
    ))
    annotated_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"annotated_script_ch{chapter_id}.json"
    ))

    script = None
    if reviewed_path.exists():
        script = json.loads(reviewed_path.read_text(encoding="utf-8"))
        logger.info(f"Stage 7 — Using reviewed script for ch{chapter_id} TTS entries.")
    elif annotated_path.exists():
        script = json.loads(annotated_path.read_text(encoding="utf-8"))
        logger.info(f"Stage 7 — Using annotated script for ch{chapter_id} TTS entries.")

    if not script:
        logger.warning(
            f"Stage 7 — No Alexandria script for ch{chapter_id}. "
            f"Falling back to generic instruct from scene data."
        )
        result = _build_tts_entries_from_scenes(book_slug, chapter_id, scenes_data)
        tts_path.parent.mkdir(parents=True, exist_ok=True)
        tts_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return result

    # Flatten if the script is a nested list (batched review output)
    if script and isinstance(script[0], list):
        script = [entry for batch in script for entry in batch]

    # Build entries from Alexandria's {speaker, text, instruct} format
    entries = []
    for i, entry in enumerate(script):
        speaker = entry.get("speaker", "NARRATOR")
        text = entry.get("text", "").strip()
        instruct = entry.get("instruct", "")

        if not text:
            continue

        # Determine type from speaker
        entry_type = "narration" if speaker == "NARRATOR" else "dialogue"

        entries.append({
            "scene_id": 0,  # Not tied to visual scenes
            "seq_index": i,
            "global_index": i,
            "type": entry_type,
            "speaker": speaker,
            "text": text,
            "instruct": instruct,
        })

    result = {
        "chapter_id": chapter_id,
        "entries": entries,
        "total_entries": len(entries),
    }

    tts_path.parent.mkdir(parents=True, exist_ok=True)
    tts_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        f"Stage 7 — Built {len(entries)} TTS entries for ch{chapter_id} "
        f"(Alexandria instruct)"
    )
    return result


def build_prompts(book_slug: str, chapter_ids: list[int]) -> None:
    """
    Main entry point for Stage 7.
    Builds character DB, visual prompts (Pass 4), and TTS entries.
    """
    # Build/update character database
    char_db = _build_character_db(book_slug, chapter_ids)

    for cid in chapter_ids:
        canon_path = Path(novel_path(
            book_slug, "chapters", "scenes", f"scenes_canonical_ch{cid}.json"
        ))
        if not canon_path.exists():
            logger.warning(f"Stage 7 — No canonical scenes for ch{cid}, skipping.")
            continue

        scenes_data = json.loads(canon_path.read_text(encoding="utf-8"))

        # Build visual prompts (LLM Pass 4)
        _build_visual_prompts(book_slug, cid, scenes_data, char_db)

        # Build TTS entries
        _build_tts_entries(book_slug, cid, scenes_data)
