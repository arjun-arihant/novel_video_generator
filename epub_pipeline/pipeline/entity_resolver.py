"""
Stage 3: Entity Resolver
Collects all raw names from scenes_raw files → one book-wide LLM call → canonical maps.
Applies maps to produce scenes_canonical_ch{N}.json. scenes_raw files are NEVER modified.
"""
import copy
import json
import logging
from pathlib import Path

from config import novel_path
from llm.client import call_llm, LLMParseError
from llm.prompts import CANONICALIZATION_SYSTEM, CANONICALIZATION_USER

logger = logging.getLogger(__name__)


def _load_raw_scenes(book_slug: str, chapter_ids: list[int]) -> dict[int, dict]:
    """Load all scenes_raw files. Returns mapping chapter_id → data."""
    result = {}
    for cid in chapter_ids:
        path = novel_path(book_slug, "chapters", "scenes", f"scenes_raw_ch{cid}.json")
        if Path(path).exists():
            result[cid] = json.loads(Path(path).read_text(encoding="utf-8"))
    return result


def _collect_raw_names(all_scenes: dict[int, dict]) -> tuple[list[str], list[str]]:
    """Walk all scenes and collect unique character names and location names."""
    chars: set[str] = set()
    locs: set[str] = set()
    for _, data in all_scenes.items():
        for scene in data.get("scenes", []):
            for c in scene.get("characters_present", []):
                if c:
                    chars.add(c.strip())
            loc = scene.get("location_name", "").strip()
            if loc:
                locs.add(loc)
            for item in scene.get("sequence", []):
                speaker = item.get("speaker", "").strip()
                if speaker:
                    chars.add(speaker)
    return sorted(chars), sorted(locs)


def _apply_map(text: str, canon_map: dict[str, str]) -> str:
    return canon_map.get(text, text)


def _apply_canonical_map_to_scene(scene: dict, char_map: dict, loc_map: dict) -> dict:
    """Return a deep copy of the scene with all names canonicalized."""
    s = copy.deepcopy(scene)
    s["characters_present"] = [
        _apply_map(c, char_map) for c in s.get("characters_present", [])
    ]
    s["location_name"] = _apply_map(s.get("location_name", ""), loc_map)
    for item in s.get("sequence", []):
        if item.get("speaker"):
            item["speaker"] = _apply_map(item["speaker"], char_map)
    return s


def resolve_entities(book_slug: str, chapter_ids: list[int]) -> None:
    """
    Main entry point for Stage 3.
    - Checks idempotency per chapter (skips if all scenes_canonical files exist)
    - Collects raw names → LLM canonicalization → saves canonical maps
    - Writes scenes_canonical_ch{N}.json for every chapter
    """
    # Check if all canonical files already exist
    all_exist = all(
        Path(novel_path(book_slug, "chapters", "scenes", f"scenes_canonical_ch{cid}.json")).exists()
        for cid in chapter_ids
    )
    if all_exist:
        logger.info("Stage 3 — All scenes_canonical files exist, skipping entity resolution.")
        return

    char_map_path = Path(novel_path(book_slug, "db", "character_canonical_map.json"))
    loc_map_path = Path(novel_path(book_slug, "db", "location_canonical_map.json"))

    # Load or build canonical maps
    if char_map_path.exists() and loc_map_path.exists():
        char_map = json.loads(char_map_path.read_text(encoding="utf-8"))
        loc_map = json.loads(loc_map_path.read_text(encoding="utf-8"))
        logger.info("Stage 3 — Loaded existing canonical maps.")
    else:
        all_scenes = _load_raw_scenes(book_slug, chapter_ids)
        raw_chars, raw_locs = _collect_raw_names(all_scenes)

        logger.info(
            f"Stage 3 — Collected {len(raw_chars)} character names, "
            f"{len(raw_locs)} location names. Calling LLM for canonicalization..."
        )

        result = call_llm(
            system_prompt=CANONICALIZATION_SYSTEM,
            user_prompt=CANONICALIZATION_USER.format(
                character_names_json=json.dumps(raw_chars, ensure_ascii=False),
                location_names_json=json.dumps(raw_locs, ensure_ascii=False),
            ),
            book_slug=book_slug,
            call_label="entity_canonicalization",
            expect_json=True,
        )

        char_map = result.get("character_map", {})
        loc_map = result.get("location_map", {})

        char_map_path.parent.mkdir(parents=True, exist_ok=True)
        char_map_path.write_text(
            json.dumps(char_map, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        loc_map_path.write_text(
            json.dumps(loc_map, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(
            f"Stage 3 — Canonical maps saved: {len(char_map)} chars, {len(loc_map)} locs."
        )

    # Apply maps and write scenes_canonical files
    all_scenes = _load_raw_scenes(book_slug, chapter_ids)
    for cid, data in all_scenes.items():
        out_path = Path(
            novel_path(book_slug, "chapters", "scenes", f"scenes_canonical_ch{cid}.json")
        )
        if out_path.exists():
            logger.debug(f"Stage 3 — scenes_canonical_ch{cid}.json exists, skipping.")
            continue

        canonical_data = {
            "schema_version": 1,
            "chapter_id": cid,
            "scenes": [
                _apply_canonical_map_to_scene(s, char_map, loc_map)
                for s in data.get("scenes", [])
            ],
        }
        out_path.write_text(
            json.dumps(canonical_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Stage 3 — scenes_canonical_ch{cid}.json written.")
