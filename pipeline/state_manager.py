"""
Pipeline State Manager
Tracks pipeline progress per novel/chapter. Enables resumption from any stage.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import novel_path

logger = logging.getLogger(__name__)


PIPELINE_STAGES = [
    "ingestor",
    "normalizer",
    "scene_extractor",
    "entity_resolver",
    "speaker_annotator",
    "script_reviewer",
    "prompt_builder",
    "image_generator",
    "audio_generator",
    "composer",
]


def _state_path(book_slug: str) -> Path:
    return Path(novel_path(book_slug, "db", "pipeline_state.json"))


def load_state(book_slug: str) -> dict:
    """Load pipeline state for a novel."""
    path = _state_path(book_slug)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "book_slug": book_slug,
        "chapters": {},
        "global_stages": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": "",
    }


def save_state(book_slug: str, state: dict) -> None:
    """Save pipeline state."""
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _state_path(book_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def mark_stage_complete(
    book_slug: str, stage: str, chapter_id: int | None = None
) -> None:
    """Mark a stage as complete for a chapter or globally."""
    state = load_state(book_slug)

    if chapter_id is not None:
        ch_key = str(chapter_id)
        if ch_key not in state["chapters"]:
            state["chapters"][ch_key] = {}
        state["chapters"][ch_key][stage] = {
            "status": "complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        state["global_stages"][stage] = {
            "status": "complete",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    save_state(book_slug, state)
    logger.debug(f"State — {stage} complete (ch{chapter_id or 'global'}).")


def is_stage_complete(
    book_slug: str, stage: str, chapter_id: int | None = None
) -> bool:
    """Check if a stage is already complete."""
    state = load_state(book_slug)

    if chapter_id is not None:
        ch_key = str(chapter_id)
        ch_stages = state.get("chapters", {}).get(ch_key, {})
        return ch_stages.get(stage, {}).get("status") == "complete"

    return state.get("global_stages", {}).get(stage, {}).get("status") == "complete"


def should_skip_stage(stage: str, from_stage: str | None) -> bool:
    """Check if a stage should be skipped due to --from-stage flag."""
    if from_stage is None:
        return False

    if from_stage not in PIPELINE_STAGES:
        logger.warning(f"Unknown stage '{from_stage}', running all stages.")
        return False

    from_idx = PIPELINE_STAGES.index(from_stage)
    current_idx = PIPELINE_STAGES.index(stage)
    return current_idx < from_idx


def get_pipeline_status(book_slug: str) -> dict:
    """Get a summary of pipeline progress for UI display."""
    state = load_state(book_slug)
    summary = {
        "book_slug": book_slug,
        "global_stages": {},
        "chapter_progress": {},
    }

    for stage in PIPELINE_STAGES:
        summary["global_stages"][stage] = (
            state.get("global_stages", {}).get(stage, {}).get("status", "pending")
        )

    for ch_key, ch_stages in state.get("chapters", {}).items():
        ch_summary = {}
        for stage in PIPELINE_STAGES:
            ch_summary[stage] = ch_stages.get(stage, {}).get("status", "pending")
        summary["chapter_progress"][ch_key] = ch_summary

    return summary
