"""
Stage 2: LLM Scene Extraction (Pass 1)
One LLM call per chapter → scenes_raw_ch{N}.json. Idempotent.
"""
import json
import logging
from pathlib import Path

from config import novel_path
from llm.client import call_llm, LLMParseError
from llm.prompts import SCENE_EXTRACTION_SYSTEM, SCENE_EXTRACTION_USER

logger = logging.getLogger(__name__)

VALID_EMOTIONS = {
    "neutral", "happy", "sad", "angry", "fearful",
    "panicked", "tender", "tense", "excited",
}
VALID_TOD = {"morning", "afternoon", "evening", "night", "unknown"}


def _validate_scene_structure(scenes_data: dict, chapter_id: int) -> list[str]:
    """Basic structural validation before writing. Returns list of warnings."""
    warnings = []
    scenes = scenes_data.get("scenes", [])
    count = len(scenes)
    if count < 4 or count > 8:
        warnings.append(f"Chapter {chapter_id}: scene count {count} outside 4–8 range.")
    for s in scenes:
        if not s.get("visual_description", "").strip():
            warnings.append(f"Chapter {chapter_id} scene {s.get('scene_id')}: empty visual_description.")
        for item in s.get("sequence", []):
            if item.get("type") == "dialogue" and not item.get("speaker"):
                warnings.append(
                    f"Chapter {chapter_id} scene {s.get('scene_id')}: dialogue missing speaker."
                )
            if item.get("emotion", "neutral") not in VALID_EMOTIONS:
                warnings.append(
                    f"Chapter {chapter_id} scene {s.get('scene_id')}: "
                    f"invalid emotion '{item.get('emotion')}'."
                )
    return warnings


def extract_chapter_scenes(book_slug: str, chapter: dict) -> str:
    """
    Extract scenes from a normalized chapter via one LLM call.
    Returns path to scenes_raw_ch{N}.json.
    """
    chapter_id = chapter["chapter_id"]
    out_path = novel_path(
        book_slug, "chapters", "scenes", f"scenes_raw_ch{chapter_id}.json"
    )

    if Path(out_path).exists():
        logger.debug(f"Stage 2 — scenes_raw_ch{chapter_id}.json exists, skipping.")
        return out_path

    # Join paragraphs into a single string for the prompt
    text = "\n\n".join(chapter["paragraphs"])

    user_prompt = SCENE_EXTRACTION_USER.format(
        chapter_id=chapter_id,
        chapter_title=chapter.get("title", ""),
        chapter_text=text,
    )

    logger.info(f"Stage 2 — Extracting scenes for chapter {chapter_id} via LLM...")
    raw_result = call_llm(
        system_prompt=SCENE_EXTRACTION_SYSTEM,
        user_prompt=user_prompt,
        book_slug=book_slug,
        call_label=f"scene_extraction_ch{chapter_id}",
        expect_json=True,
    )

    # Ensure required top-level fields
    if "scenes" not in raw_result:
        raise LLMParseError(f"Chapter {chapter_id}: LLM response missing 'scenes' key.")

    raw_result["schema_version"] = 1
    raw_result["chapter_id"] = chapter_id

    warnings = _validate_scene_structure(raw_result, chapter_id)
    for w in warnings:
        logger.warning(f"  ⚠ {w}")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(raw_result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        f"Stage 2 — Chapter {chapter_id}: {len(raw_result['scenes'])} scenes extracted."
    )
    return out_path


def extract_all_chapters(book_slug: str, chapters: list[dict]) -> list[str]:
    """Extract scenes for all chapters. `chapters` is list of normalized chapter dicts."""
    paths = []
    for chapter in chapters:
        paths.append(extract_chapter_scenes(book_slug, chapter))
    return paths
