"""
Stage 4: State Manager
Manages character_db.json + location_db.json per novel.
LLM Pass 2: Baseline extraction for new characters + new locations (batched).
LLM Pass 3: Delta detection for existing characters (batched per chapter).
"""
import json
import logging
import re
from pathlib import Path

from config import novel_path
from llm.client import call_llm
from llm.prompts import (
    CHARACTER_BASELINE_SYSTEM,
    CHARACTER_BASELINE_USER,
    CHARACTER_DELTA_SYSTEM,
    CHARACTER_DELTA_USER,
    LOCATION_BASELINE_SYSTEM,
    LOCATION_BASELINE_USER,
)

logger = logging.getLogger(__name__)

CHAR_DB_VERSION = 1
LOC_DB_VERSION = 1


# ─── DB Loading / Saving ──────────────────────────────────────────────────────

def _load_char_db(book_slug: str) -> dict:
    path = Path(novel_path(book_slug, "db", "character_db.json"))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": CHAR_DB_VERSION, "characters": {}}


def _save_char_db(book_slug: str, db: dict) -> None:
    path = Path(novel_path(book_slug, "db", "character_db.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_loc_db(book_slug: str) -> dict:
    path = Path(novel_path(book_slug, "db", "location_db.json"))
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema_version": LOC_DB_VERSION, "locations": {}}


def _save_loc_db(book_slug: str, db: dict) -> None:
    path = Path(novel_path(book_slug, "db", "location_db.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name)
    return re.sub(r"-+", "-", name).strip("-")


def _scenes_to_text(scenes: list[dict]) -> str:
    """Flatten scenes into readable text for LLM context."""
    lines = []
    for s in scenes:
        lines.append(f"[Scene {s['scene_id']}: {s.get('location_name', '')}]")
        lines.append(s.get("visual_description", ""))
        for item in s.get("sequence", []):
            if item["type"] == "narration":
                lines.append(f"  Narration: {item['text']}")
            else:
                lines.append(f"  {item.get('speaker', '')}: \"{item['text']}\"")
    return "\n".join(lines)


def _build_new_char_entry(canonical_name: str, chapter_id: int, profile: dict) -> dict:
    char_slug = _slugify(canonical_name)
    return {
        "canonical_name": canonical_name,
        "first_appearance_chapter": chapter_id,
        "base_visual_prompt": profile.get("base_visual_prompt", ""),
        "personality_baseline": profile.get("personality_baseline", ""),
        "voice_profile": {
            "voice_type": "designed",
            "voice_reference_file": novel_path("__SLUG__", "voices", f"{char_slug}_ref.wav"),
            "voice_design_prompt": profile.get("voice_design_prompt", ""),
        },
        "current_state": {
            "clothing": "",
            "injury": None,
            "emotional_arc": "neutral",
            "age_offset_years": 0,
        },
        "appearance_history": [],
        "used_fallback_voice": False,
    }


# ─── Pass 2: Baseline Extraction ──────────────────────────────────────────────

def _extract_baselines(
    book_slug: str, new_chars: list[str], new_locs: list[str],
    relevant_scenes: list[dict], chapter_id: int,
) -> tuple[dict, dict]:
    """
    LLM Pass 2: Extract baseline visual prompts for new characters and locations.
    Returns (char_profiles_dict, loc_profiles_dict).
    """
    scenes_text = _scenes_to_text(relevant_scenes)
    char_profiles: dict = {}
    loc_profiles: dict = {}

    if new_chars:
        logger.info(
            f"Stage 4 Pass 2 — Extracting baselines for {len(new_chars)} new characters..."
        )
        result = call_llm(
            system_prompt=CHARACTER_BASELINE_SYSTEM,
            user_prompt=CHARACTER_BASELINE_USER.format(
                character_names_json=json.dumps(new_chars, ensure_ascii=False),
                scenes_text=scenes_text,
            ),
            book_slug=book_slug,
            call_label=f"char_baseline_ch{chapter_id}",
            expect_json=True,
        )
        char_profiles = result.get("characters", {})

    if new_locs:
        logger.info(
            f"Stage 4 Pass 2 — Extracting baselines for {len(new_locs)} new locations..."
        )
        result = call_llm(
            system_prompt=LOCATION_BASELINE_SYSTEM,
            user_prompt=LOCATION_BASELINE_USER.format(
                location_names_json=json.dumps(new_locs, ensure_ascii=False),
                scenes_text=scenes_text,
            ),
            book_slug=book_slug,
            call_label=f"loc_baseline_ch{chapter_id}",
            expect_json=True,
        )
        loc_profiles = result.get("locations", {})

    return char_profiles, loc_profiles


# ─── Pass 3: Delta Detection ───────────────────────────────────────────────────

def _detect_deltas(
    book_slug: str, existing_chars: list[str], char_db: dict,
    scenes: list[dict], chapter_id: int,
) -> dict:
    """
    LLM Pass 3: Detect permanent changes for existing characters in this chapter.
    Returns dict mapping canonical_name → changes dict.
    """
    if not existing_chars:
        return {}

    current_states = {
        name: char_db["characters"][name]["current_state"]
        for name in existing_chars
        if name in char_db["characters"]
    }
    scenes_text = _scenes_to_text(scenes)

    logger.info(
        f"Stage 4 Pass 3 — Delta detection for {len(existing_chars)} existing characters..."
    )
    result = call_llm(
        system_prompt=CHARACTER_DELTA_SYSTEM,
        user_prompt=CHARACTER_DELTA_USER.format(
            current_states_json=json.dumps(current_states, indent=2, ensure_ascii=False),
            scenes_text=scenes_text,
            chapter_id=chapter_id,
        ),
        book_slug=book_slug,
        call_label=f"char_delta_ch{chapter_id}",
        expect_json=True,
    )
    return result.get("changes", {})


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def update_state_for_chapter(book_slug: str, chapter_id: int) -> None:
    """
    Run Stage 4 for one chapter:
    - Detect new vs existing characters and locations
    - LLM Pass 2: baseline extraction for new entities
    - LLM Pass 3: delta detection for existing characters
    - Update and persist character_db + location_db
    """
    canonical_path = Path(
        novel_path(book_slug, "chapters", "scenes", f"scenes_canonical_ch{chapter_id}.json")
    )
    if not canonical_path.exists():
        raise FileNotFoundError(
            f"scenes_canonical_ch{chapter_id}.json not found. Run Stage 3 first."
        )

    scenes_data = json.loads(canonical_path.read_text(encoding="utf-8"))
    scenes = scenes_data.get("scenes", [])

    char_db = _load_char_db(book_slug)
    loc_db = _load_loc_db(book_slug)

    known_chars = set(char_db["characters"].keys())
    known_locs = set(loc_db["locations"].keys())

    # Collect all characters and locations appearing in this chapter
    chapter_chars: set[str] = set()
    chapter_locs: set[str] = set()
    for scene in scenes:
        for c in scene.get("characters_present", []):
            if c:
                chapter_chars.add(c)
        loc = scene.get("location_name", "").strip()
        if loc:
            chapter_locs.add(loc)
        for item in scene.get("sequence", []):
            sp = item.get("speaker", "").strip()
            if sp:
                chapter_chars.add(sp)

    new_chars = sorted(chapter_chars - known_chars)
    existing_chars = sorted(chapter_chars & known_chars)
    new_locs = sorted(chapter_locs - known_locs)

    # Pass 2: baselines for new entities
    if new_chars or new_locs:
        char_profiles, loc_profiles = _extract_baselines(
            book_slug, new_chars, new_locs, scenes, chapter_id
        )

        for name in new_chars:
            profile = char_profiles.get(name, {})
            entry = _build_new_char_entry(name, chapter_id, profile)
            # Fix the placeholder slug in voice_reference_file
            entry["voice_profile"]["voice_reference_file"] = novel_path(
                book_slug, "voices", f"{_slugify(name)}_ref.wav"
            )
            char_db["characters"][name] = entry
            logger.info(f"Stage 4 — Added character: {name}")

        for loc_name in new_locs:
            profile = loc_profiles.get(loc_name, {})
            loc_db["locations"][loc_name] = {
                "canonical_name": loc_name,
                "first_appearance_chapter": chapter_id,
                "base_visual_prompt": profile.get("base_visual_prompt", ""),
                "architecture_style": profile.get("architecture_style", ""),
                "atmosphere": profile.get("atmosphere", ""),
            }
            logger.info(f"Stage 4 — Added location: {loc_name}")

    # Pass 3: deltas for existing characters
    if existing_chars:
        changes = _detect_deltas(book_slug, existing_chars, char_db, scenes, chapter_id)
        for name, char_changes in changes.items():
            if name not in char_db["characters"]:
                continue
            state = char_db["characters"][name]["current_state"]
            history = char_db["characters"][name]["appearance_history"]
            applied = {}
            for field, value in char_changes.items():
                if field in state:
                    applied[field] = {"from": state[field], "to": value}
                    state[field] = value
                else:
                    # Allow new fields (e.g. injury descriptions)
                    applied[field] = {"from": None, "to": value}
                    state[field] = value
            if applied:
                history.append({"chapter": chapter_id, "changes": applied})
                logger.info(f"Stage 4 — Applied {len(applied)} changes to {name}.")

    _save_char_db(book_slug, char_db)
    _save_loc_db(book_slug, loc_db)
    logger.info(f"Stage 4 — State updated for chapter {chapter_id}.")
