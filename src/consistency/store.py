"""Rich consistency store for characters and locations.

Tracks detailed character profiles (appearance, clothing, voice) and
location descriptions for consistent image/audio generation across scenes.
Supports per-chapter appearance evolution.
"""

import hashlib
import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default character schema — LLM should fill all fields; missing ones get auto-populated
_CHARACTER_SCHEMA = {
    "name": "",
    "aliases": [],
    "gender": "",
    "age_range": "",          # e.g. "17-18", "mid-30s", "elderly"
    "build": "",              # e.g. "slender", "athletic", "stocky"
    "height": "",             # e.g. "average", "tall", "short"
    "skin_tone": "",          # e.g. "fair", "tan", "dark"
    "hair_color": "",
    "hair_style": "",         # e.g. "long flowing", "short cropped", "tied in bun"
    "eye_color": "",
    "clothing": "",           # current outfit description
    "distinguishing_features": "",  # scars, tattoos, accessories
    "disposition": "",        # e.g. "smug", "stern", "gentle"
    "personality": "",
    "role": "",               # protagonist, antagonist, side character
    "voice_id": "",           # Kokoro voice ID (e.g. "am_puck")
    "voice_mix": [],          # list of voice IDs if using mixed voice
    "voice_speed": 1.0,
    "voice_notes": "",        # LLM reasoning for voice choice
    # Evolution tracking: chapter_id → changed fields
    "appearance_history": {},
}

_LOCATION_SCHEMA = {
    "name": "",
    "description": "",
    "architecture_style": "",  # e.g. "traditional Chinese", "futuristic", "rustic"
    "mood": "",                # e.g. "tense", "serene", "chaotic"
    "lighting": "",            # e.g. "bright daylight", "dim interior", "moonlit"
    "time_of_day": "",         # e.g. "morning", "afternoon", "night"
    "weather": "",             # e.g. "clear", "overcast", "rainy"
    "key_objects": [],         # notable items in the location
    "color_palette": "",       # dominant colors for visual consistency
}


class ConsistencyStore:
    """Persist rich character and location data for consistent generation."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path("data/consistency")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.characters_path = self.base_dir / "characters.json"
        self.locations_path = self.base_dir / "locations.json"
        self.characters: Dict[str, Dict] = self._load(self.characters_path)
        self.locations: Dict[str, Dict] = self._load(self.locations_path)

    # ── Persistence ──────────────────────────────────────────────

    def _load(self, path: Path) -> Dict[str, Dict]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: Path, data: Dict[str, Dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── Characters ───────────────────────────────────────────────

    def upsert_characters(self, characters: List[Dict], chapter_id: str = "") -> None:
        """Update character DB with new data, merging without overwriting existing non-empty fields."""
        for char in characters:
            name = char.get("name")
            if not name:
                continue

            if name not in self.characters:
                base = deepcopy(_CHARACTER_SCHEMA)
                base.update({k: v for k, v in char.items() if v})
                self.characters[name] = base
            else:
                existing = self.characters[name]
                # Track appearance changes per chapter
                if chapter_id:
                    changed = {}
                    appearance_fields = [
                        "clothing", "hair_style", "hair_color",
                        "distinguishing_features", "disposition",
                    ]
                    for field in appearance_fields:
                        new_val = char.get(field, "")
                        old_val = existing.get(field, "")
                        if new_val and new_val != old_val:
                            changed[field] = new_val
                    if changed:
                        history = existing.get("appearance_history", {})
                        history[chapter_id] = changed
                        existing["appearance_history"] = history

                # Merge: only overwrite empty or missing fields
                for k, v in char.items():
                    if v and (not existing.get(k) or k in (
                        "clothing", "disposition", "distinguishing_features"
                    )):
                        existing[k] = v

        self._save(self.characters_path, self.characters)
        logger.info("Character DB updated: %d entries", len(self.characters))

    def get_character(self, name: str) -> Optional[Dict]:
        return self.characters.get(name)

    def list_characters(self) -> Dict[str, Dict]:
        return self.characters

    def get_all_assigned_voices(self) -> List[str]:
        """Return list of voice_ids already assigned to characters."""
        voices = []
        for char in self.characters.values():
            vid = char.get("voice_id")
            if vid:
                voices.append(vid)
        return voices

    def update_character_voice(
        self, name: str, voice_id: str,
        voice_mix: Optional[List[str]] = None,
        voice_speed: float = 1.0,
        voice_notes: str = "",
    ) -> None:
        """Set voice assignment for a character."""
        if name not in self.characters:
            self.characters[name] = deepcopy(_CHARACTER_SCHEMA)
            self.characters[name]["name"] = name
        self.characters[name]["voice_id"] = voice_id
        self.characters[name]["voice_mix"] = voice_mix or []
        self.characters[name]["voice_speed"] = voice_speed
        self.characters[name]["voice_notes"] = voice_notes
        self._save(self.characters_path, self.characters)
        logger.info("Voice assigned: %s → %s", name, voice_id)

    def get_character_image_descriptor(self, name: str, chapter_id: str = "") -> str:
        """Build a formatted appearance string for image prompts.

        If chapter_id is provided, apply appearance evolution overrides.
        Returns e.g.: "Chen Mobai (male, ~17, slender, fair skin, black hair in short style,
        dark eyes, white cultivation robes, jade smartphone, smug expression)"
        """
        char = self.characters.get(name)
        if not char:
            return name

        # Start with base appearance
        parts = [char.get("name", name)]
        descriptors = []

        if char.get("gender"):
            descriptors.append(char["gender"])
        if char.get("age_range"):
            descriptors.append(f"~{char['age_range']}")
        if char.get("build"):
            descriptors.append(f"{char['build']} build")
        if char.get("height"):
            descriptors.append(char["height"])
        if char.get("skin_tone"):
            descriptors.append(f"{char['skin_tone']} skin")

        hair = ""
        if char.get("hair_color"):
            hair = char["hair_color"]
        if char.get("hair_style"):
            hair = f"{hair} hair in {char['hair_style']}" if hair else char["hair_style"]
        elif hair:
            hair = f"{hair} hair"
        if hair:
            descriptors.append(hair)

        if char.get("eye_color"):
            descriptors.append(f"{char['eye_color']} eyes")

        # Apply chapter-specific overrides
        clothing = char.get("clothing", "")
        disposition = char.get("disposition", "")
        features = char.get("distinguishing_features", "")

        if chapter_id:
            history = char.get("appearance_history", {})
            overrides = history.get(chapter_id, {})
            if overrides.get("clothing"):
                clothing = overrides["clothing"]
            if overrides.get("disposition"):
                disposition = overrides["disposition"]
            if overrides.get("distinguishing_features"):
                features = overrides["distinguishing_features"]

        if clothing:
            descriptors.append(clothing)
        if features:
            descriptors.append(features)
        if disposition:
            descriptors.append(f"{disposition} expression")

        if descriptors:
            return f"{parts[0]} ({', '.join(descriptors)})"
        return parts[0]

    # ── Locations ────────────────────────────────────────────────

    def upsert_locations(self, locations: List[Dict]) -> None:
        """Update location DB with new data."""
        for loc in locations:
            name = loc.get("name")
            if not name:
                continue
            if name not in self.locations:
                base = deepcopy(_LOCATION_SCHEMA)
                base.update({k: v for k, v in loc.items() if v})
                self.locations[name] = base
            else:
                existing = self.locations[name]
                for k, v in loc.items():
                    if v and not existing.get(k):
                        existing[k] = v
        self._save(self.locations_path, self.locations)
        logger.info("Location DB updated: %d entries", len(self.locations))

    def get_location(self, name: str) -> Optional[Dict]:
        return self.locations.get(name)

    def get_location_image_descriptor(self, name: str) -> str:
        """Build a formatted location string for image prompts."""
        loc = self.locations.get(name)
        if not loc:
            return name
        parts = [loc.get("name", name)]
        descriptors = []
        if loc.get("architecture_style"):
            descriptors.append(loc["architecture_style"])
        if loc.get("lighting"):
            descriptors.append(loc["lighting"])
        if loc.get("time_of_day"):
            descriptors.append(loc["time_of_day"])
        if loc.get("weather"):
            descriptors.append(loc["weather"])
        if loc.get("mood"):
            descriptors.append(f"{loc['mood']} atmosphere")
        if loc.get("color_palette"):
            descriptors.append(f"dominant colors: {loc['color_palette']}")
        if descriptors:
            return f"{parts[0]} ({', '.join(descriptors)})"
        return parts[0]

    def list_locations(self) -> Dict[str, Dict]:
        return self.locations

    # ── Utility ──────────────────────────────────────────────────

    @staticmethod
    def character_seed(name: str) -> int:
        """Deterministic seed from character name for consistent WanGP generation."""
        return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) % (2**31)

    def export_for_llm(self) -> Dict[str, Any]:
        """Export a compact summary of characters/locations for LLM context."""
        chars_summary = {}
        for name, data in self.characters.items():
            chars_summary[name] = {
                k: v for k, v in data.items()
                if k not in ("appearance_history",) and v
            }
        locs_summary = {
            name: {k: v for k, v in data.items() if v}
            for name, data in self.locations.items()
        }
        return {"characters": chars_summary, "locations": locs_summary}
