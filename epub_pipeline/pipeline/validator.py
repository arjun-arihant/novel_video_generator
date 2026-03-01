"""
Stage 5: Validation Pass
Checks all canonical scene files against character_db and location_db.
Logs all issues; never crashes the pipeline.
"""
import json
import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table

from config import novel_path, MIN_SCENES_PER_CHAPTER, MAX_SCENES_PER_CHAPTER

logger = logging.getLogger(__name__)
console = Console()

VALID_EMOTIONS = {
    "neutral", "happy", "sad", "angry", "fearful",
    "panicked", "tender", "tense", "excited",
}


def _load_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def validate_chapter(
    book_slug: str,
    chapter_id: int,
    char_db: dict,
    loc_db: dict,
) -> list[dict]:
    """
    Validate a single chapter's canonical scene file.
    Returns list of issue dicts: {chapter, scene, field, message}.
    """
    canonical_path = novel_path(
        book_slug, "chapters", "scenes", f"scenes_canonical_ch{chapter_id}.json"
    )
    data = _load_json(canonical_path)
    if not data:
        return [{"chapter": chapter_id, "scene": "-", "field": "file", "message": "scenes_canonical file missing"}]

    scenes = data.get("scenes", [])
    issues = []

    # Scene count check
    count = len(scenes)
    if count < MIN_SCENES_PER_CHAPTER or count > MAX_SCENES_PER_CHAPTER:
        issues.append({
            "chapter": chapter_id, "scene": "-", "field": "scene_count",
            "message": f"Scene count {count} outside {MIN_SCENES_PER_CHAPTER}–{MAX_SCENES_PER_CHAPTER} range",
        })

    known_chars = set(char_db.get("characters", {}).keys())
    known_locs = set(loc_db.get("locations", {}).keys())

    for scene in scenes:
        sid = scene.get("scene_id", "?")

        # Empty visual_description
        if not scene.get("visual_description", "").strip():
            issues.append({
                "chapter": chapter_id, "scene": sid,
                "field": "visual_description", "message": "Empty visual_description",
            })

        # Characters not in DB
        for char in scene.get("characters_present", []):
            if char and char not in known_chars:
                issues.append({
                    "chapter": chapter_id, "scene": sid,
                    "field": "characters_present",
                    "message": f"Character '{char}' missing from character_db",
                })

        # Location not in DB
        loc = scene.get("location_name", "").strip()
        if loc and loc not in known_locs:
            issues.append({
                "chapter": chapter_id, "scene": sid,
                "field": "location_name",
                "message": f"Location '{loc}' missing from location_db",
            })

        # Sequence checks
        for idx, item in enumerate(scene.get("sequence", [])):
            item_type = item.get("type")
            if item_type == "dialogue" and not item.get("speaker", "").strip():
                issues.append({
                    "chapter": chapter_id, "scene": sid,
                    "field": f"sequence[{idx}].speaker",
                    "message": "Dialogue item missing speaker",
                })
            emotion = item.get("emotion", "")
            if emotion not in VALID_EMOTIONS:
                issues.append({
                    "chapter": chapter_id, "scene": sid,
                    "field": f"sequence[{idx}].emotion",
                    "message": f"Invalid emotion '{emotion}'",
                })

    return issues


def validate_all(book_slug: str, chapter_ids: list[int]) -> dict[int, list[dict]]:
    """
    Validate all chapters. Prints a Rich table summary.
    Returns dict mapping chapter_id → list of issues.
    """
    char_db = _load_json(novel_path(book_slug, "db", "character_db.json"))
    loc_db = _load_json(novel_path(book_slug, "db", "location_db.json"))

    all_issues: dict[int, list[dict]] = {}
    flagged_chapters = []

    for cid in chapter_ids:
        issues = validate_chapter(book_slug, cid, char_db, loc_db)
        all_issues[cid] = issues
        if issues:
            flagged_chapters.append(cid)

    total_issues = sum(len(v) for v in all_issues.values())

    if total_issues == 0:
        console.print(
            "[bold green]✓ Validation passed — no issues found across all chapters.[/bold green]"
        )
        return all_issues

    table = Table(
        title=f"[bold yellow]Validation Issues ({total_issues} total)[/bold yellow]",
        show_lines=True,
    )
    table.add_column("Chapter", style="cyan", justify="center")
    table.add_column("Scene", style="magenta", justify="center")
    table.add_column("Field", style="yellow")
    table.add_column("Issue", style="red")

    for cid in sorted(all_issues.keys()):
        for issue in all_issues[cid]:
            table.add_row(
                str(issue["chapter"]),
                str(issue["scene"]),
                issue["field"],
                issue["message"],
            )

    console.print(table)
    console.print(
        f"[yellow]⚠ {len(flagged_chapters)} chapter(s) flagged for review: "
        f"{flagged_chapters}[/yellow]"
    )
    return all_issues
