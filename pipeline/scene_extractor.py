"""
Stage 3: Scene Extractor (LLM Pass 1)
Splits normalized chapter text into visual scenes using LLM.
Produces scenes_raw_ch{N}.json with visual descriptions, characters, dialogue.
"""
import json
import logging
from pathlib import Path

from pipeline.config import novel_path, MIN_CHAPTER_WORD_COUNT
from llm.client import call_llm
from llm.prompts import SCENE_EXTRACTION_SYSTEM, SCENE_EXTRACTION_USER

logger = logging.getLogger(__name__)


def extract_scenes(book_slug: str, chapter_id: int) -> dict:
    """
    Extract scenes from a normalized chapter via LLM.

    Returns the scenes data dict.
    """
    out_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"scenes_raw_ch{chapter_id}.json"
    ))
    if out_path.exists():
        logger.debug(f"Stage 3 — scenes_raw_ch{chapter_id}.json exists, skipping.")
        return json.loads(out_path.read_text(encoding="utf-8"))

    norm_path = Path(novel_path(
        book_slug, "chapters", "normalized", f"chapter_{chapter_id}.json"
    ))
    norm_data = json.loads(norm_path.read_text(encoding="utf-8"))
    chapter_text = norm_data["text"]
    word_count = norm_data.get("word_count", len(chapter_text.split()))

    if word_count < MIN_CHAPTER_WORD_COUNT:
        logger.warning(
            f"Stage 3 — Chapter {chapter_id} has only {word_count} words "
            f"(min: {MIN_CHAPTER_WORD_COUNT}). Saving as single scene."
        )
        scenes_data = {
            "schema_version": 1,
            "chapter_id": chapter_id,
            "chapter_title": norm_data.get("title", ""),
            "scenes": [{
                "scene_id": 1,
                "location_name": "Unknown",
                "characters_present": [],
                "visual_description": "A scene from the story.",
                "mood": "neutral",
                "text": chapter_text,
                "sequence": [{"type": "narration", "speaker": "NARRATOR", "text": chapter_text}],
            }],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(scenes_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return scenes_data

    result = call_llm(
        system_prompt=SCENE_EXTRACTION_SYSTEM,
        user_prompt=SCENE_EXTRACTION_USER.format(chapter_text=chapter_text),
        book_slug=book_slug,
        call_label=f"scene_extraction_ch{chapter_id}",
        expect_json=True,
        max_tokens=8192,
    )

    # Normalize result structure
    if isinstance(result, list):
        scenes = result
        chapter_title = norm_data.get("title", "")
    else:
        scenes = result.get("scenes", [])
        chapter_title = result.get("chapter_title", norm_data.get("title", ""))

    # Validate and fix scene_ids
    for i, scene in enumerate(scenes):
        scene.setdefault("scene_id", i + 1)
        scene.setdefault("location_name", "Unknown")
        scene.setdefault("characters_present", [])
        scene.setdefault("visual_description", "")
        scene.setdefault("mood", "neutral")
        scene.setdefault("text", "")
        scene.setdefault("sequence", [])

    scenes_data = {
        "schema_version": 1,
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "scenes": scenes,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(scenes_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info(
        f"Stage 3 — Extracted {len(scenes)} scenes from chapter {chapter_id}"
    )
    return scenes_data
