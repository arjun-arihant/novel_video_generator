"""
Asset Validator
Verifies generated assets (images, audio, prompts) exist and are valid.
"""
import json
import logging
from pathlib import Path

from pipeline.config import novel_path

logger = logging.getLogger(__name__)


def validate_chapter_assets(book_slug: str, chapter_id: int) -> dict:
    """
    Validate that all required assets exist for a chapter.

    Returns a dict with validation results.
    """
    results = {
        "chapter_id": chapter_id,
        "valid": True,
        "missing_images": [],
        "missing_audio": [],
        "warnings": [],
    }

    # Check canonical scenes exist
    canon_path = Path(novel_path(
        book_slug, "chapters", "scenes", f"scenes_canonical_ch{chapter_id}.json"
    ))
    if not canon_path.exists():
        results["valid"] = False
        results["warnings"].append(f"Missing canonical scenes for ch{chapter_id}")
        return results

    scenes_data = json.loads(canon_path.read_text(encoding="utf-8"))
    scenes = scenes_data.get("scenes", [])

    # Check images
    for scene in scenes:
        scene_id = scene["scene_id"]
        img_path = Path(novel_path(
            book_slug, "images", f"ch{chapter_id}", f"scene_{scene_id:03d}.jpg"
        ))
        if not img_path.exists():
            results["missing_images"].append(str(img_path))

    # Check audio segments
    tts_path = Path(novel_path(
        book_slug, "prompts", f"tts_entries_ch{chapter_id}.json"
    ))
    if tts_path.exists():
        tts_data = json.loads(tts_path.read_text(encoding="utf-8"))
        for entry in tts_data.get("entries", []):
            audio_path = Path(novel_path(
                book_slug, "audio", f"ch{chapter_id}",
                f"seq_{entry['scene_id']:03d}_{entry['seq_index']:03d}.wav",
            ))
            if not audio_path.exists():
                results["missing_audio"].append(str(audio_path))

    if results["missing_images"]:
        results["warnings"].append(
            f"{len(results['missing_images'])} missing images"
        )
    if results["missing_audio"]:
        results["warnings"].append(
            f"{len(results['missing_audio'])} missing audio segments"
        )

    results["valid"] = not results["missing_images"] and not results["missing_audio"]

    if results["valid"]:
        logger.info(f"Validator — Chapter {chapter_id} assets complete.")
    else:
        logger.warning(
            f"Validator — Chapter {chapter_id} has issues: "
            + "; ".join(results["warnings"])
        )

    return results
