"""Scene extraction using OpenRouter."""

import logging
from typing import Any, Dict, List, Optional

from ..consistency.store import ConsistencyStore
from ..llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)


class SceneExtractor:
    """Extracts visual scenes from chapter text using OpenRouter."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.client = OpenRouterClient(model=model_name)
        self.store = ConsistencyStore()

    def extract_scenes(self, chapter_text: str, max_scenes: int = 8) -> Dict[str, Any]:
        """Extract scenes and entity profiles from chapter text."""
        truncated_text = chapter_text[:50000]
        existing_characters = list(self.store.list_characters().values())
        existing_locations = list(self.store.list_locations().values())

        system = (
            "You are a screenplay assistant that outputs strict JSON. "
            "Extract scenes and ensure character/location consistency. "
            "Always return valid JSON with keys: scenes, characters, locations."
        )
        user = (
            "Break the chapter into 3 to {max_scenes} scenes. "
            "Return JSON with:\n"
            "- scenes: list of objects with fields: "
            "id (int), title, visual_description, text_segment, narration, "
            "dialogues (list of {speaker, line}), characters (list of names), "
            "locations (list of names), estimated_duration (seconds).\n"
            "- characters: list of unique character profiles with fields: "
            "name, physical_description, vocal_description, personality_notes, "
            "gender (optional), voice_tags (optional).\n"
            "- locations: list of unique locations with fields: "
            "name, description, mood.\n\n"
            "Guidelines:\n"
            "- narration covers non-dialogue text.\n"
            "- dialogues should contain exact spoken lines.\n"
            "- Include enough visual detail for illustration.\n"
            "- Use consistent character/location descriptions, reuse existing data if relevant.\n"
            "- If a character/location matches existing entries, keep the same name.\n\n"
            "Existing characters:\n{characters}\n\n"
            "Existing locations:\n{locations}\n\n"
            "Chapter text:\n{chapter_text}"
        ).format(
            max_scenes=max_scenes,
            characters=existing_characters,
            locations=existing_locations,
            chapter_text=truncated_text,
        )

        response = self.client.generate_json(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        scenes = response.get("scenes", [])
        characters = response.get("characters", [])
        locations = response.get("locations", [])
        self.store.upsert_characters(characters)
        self.store.upsert_locations(locations)
        logger.info("Extracted %s scenes", len(scenes))
        return {"scenes": scenes, "characters": characters, "locations": locations}
