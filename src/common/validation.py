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

    Args:
        chapter_data: Chapter data dictionary

    Raises:
        ValidationError: If validation fails
    """
    required_fields = ['chapter_number', 'title', 'content']

    for field in required_fields:
        if field not in chapter_data:
            raise ValidationError(f"Missing required field: {field}")

    if not isinstance(chapter_data['content'], list):
        raise ValidationError("'content' must be a list of paragraphs")

    if len(chapter_data['content']) == 0:
        raise ValidationError("Chapter content is empty")

    logger.info(
        f"Validated chapter {chapter_data['chapter_number']}: "
        f"{len(chapter_data['content'])} paragraphs"
    )


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

    required_scene_fields = [
        'visual_description',
        'text_segment',
        'characters',
        'estimated_duration'
    ]

    for i, scene in enumerate(scenes_data):
        for field in required_scene_fields:
            if field not in scene:
                raise ValidationError(
                    f"Scene {i} missing required field: {field}"
                )

        if not isinstance(scene['characters'], list):
            raise ValidationError(
                f"Scene {i}: 'characters' must be a list"
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
