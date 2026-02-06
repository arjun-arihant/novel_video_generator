"""Consistency store for characters and locations."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ConsistencyStore:
    """Persist characters and locations for consistent generation."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or Path("data/consistency")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.characters_path = self.base_dir / "characters.json"
        self.locations_path = self.base_dir / "locations.json"
        self.characters = self._load(self.characters_path)
        self.locations = self._load(self.locations_path)

    def _load(self, path: Path) -> Dict[str, Dict]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: Path, data: Dict[str, Dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def upsert_characters(self, characters: List[Dict]) -> None:
        for char in characters:
            name = char.get("name")
            if not name:
                continue
            existing = self.characters.get(name, {})
            existing.update({k: v for k, v in char.items() if v})
            self.characters[name] = existing
        self._save(self.characters_path, self.characters)
        logger.info("Updated character database with %s entries", len(characters))

    def upsert_locations(self, locations: List[Dict]) -> None:
        for loc in locations:
            name = loc.get("name")
            if not name:
                continue
            existing = self.locations.get(name, {})
            existing.update({k: v for k, v in loc.items() if v})
            self.locations[name] = existing
        self._save(self.locations_path, self.locations)
        logger.info("Updated location database with %s entries", len(locations))

    def get_character(self, name: str) -> Optional[Dict]:
        return self.characters.get(name)

    def get_location(self, name: str) -> Optional[Dict]:
        return self.locations.get(name)

    def list_characters(self) -> Dict[str, Dict]:
        return self.characters

    def list_locations(self) -> Dict[str, Dict]:
        return self.locations
