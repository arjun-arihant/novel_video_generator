"""Input validation for chapter and scene data."""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_chapter(chapter_data: Dict[str, Any]) -> None:
    """
    Validate chapter JSON structure.
    
    Supports two formats:
    - Format 1: 'chapter_number', 'title', 'content'
    - Format 2: 'id', 'title', 'paragraphs'

    Args:
        chapter_data: Chapter data dictionary

    Raises:
        ValidationError: If validation fails
    """
    # Check for 'title' which is common to both formats
    if 'title' not in chapter_data:
        raise ValidationError("Missing required field: title")
    
    # Normalize chapter_number field
    if 'chapter_number' not in chapter_data and 'id' not in chapter_data:
        raise ValidationError("Missing required field: chapter_number or id")
    
    chapter_num = chapter_data.get('chapter_number', chapter_data.get('id'))
    
    # Normalize content field
    if 'content' in chapter_data:
        content = chapter_data['content']
    elif 'paragraphs' in chapter_data:
        content = chapter_data['paragraphs']
    else:
        raise ValidationError("Missing required field: content or paragraphs")
    
    # Accept both string and list formats
    if isinstance(content, str):
        if len(content.strip()) == 0:
            raise ValidationError("Chapter content is empty")
        logger.info(
            f"Validated chapter {chapter_num}: "
            f"{len(content.split())} words"
        )
    elif isinstance(content, list):
        if len(content) == 0:
            raise ValidationError("Chapter content is empty")
        logger.info(
            f"Validated chapter {chapter_num}: "
            f"{len(content)} paragraphs"
        )
    else:
        raise ValidationError("'content' or 'paragraphs' must be a string or list")


def validate_scenes(scenes_data: List[Dict[str, Any]]) -> None:
    """
    Validate scenes JSON structure.

    Args:
        scenes_data: List of scene dictionaries

    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(scenes_data, list):
        raise ValidationError("Scenes data must be a list")

    if len(scenes_data) == 0:
        raise ValidationError("Scenes list is empty")

    for i, scene in enumerate(scenes_data):
        if "visual_description" not in scene:
            raise ValidationError(
                f"Scene {i} missing required field: visual_description"
            )

        if "characters" not in scene:
            logger.warning("Scene %d missing characters field, defaulting to empty list.", i)
            scene["characters"] = []

        # Check for content: either 'sequence' (new) or 'text_segment'/'narration' (legacy)
        has_content = (
            "sequence" in scene
            or "text_segment" in scene
            or "narration" in scene
        )
        if not has_content:
             logger.warning("Scene %d missing content field, defaulting to empty sequence.", i)
             scene["sequence"] = []

        if not isinstance(scene['characters'], list):
            raise ValidationError(
                f"Scene {i}: 'characters' must be a list"
            )

        if 'dialogues' in scene and not isinstance(scene['dialogues'], list):
            raise ValidationError(
                f"Scene {i}: 'dialogues' must be a list when provided"
            )

    logger.info(f"Validated {len(scenes_data)} scenes")


def validate_file_exists(file_path: Any) -> None:
    """
    Validate that a file exists.

    Args:
        file_path: Path object or string

    Raises:
        ValidationError: If file doesn't exist
    """
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        raise ValidationError(f"File not found: {path}")

    if not path.is_file():
        raise ValidationError(f"Not a file: {path}")
