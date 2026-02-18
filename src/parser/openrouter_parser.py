"""Enriched scene extraction using OpenRouter.

Extracts scenes with rich character profiles (auto-populates missing appearance fields),
location descriptions, and scene transition metadata. Enriches visual descriptions with
character DB data for consistent image generation.
"""

import logging
from typing import Any, Dict, List, Optional

from ..consistency.store import ConsistencyStore
from ..llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

# Image style template appended to every visual description
IMAGE_STYLE_TAG = (
    ", detailed cinematic manhua webtoon style, clean line art, vibrant colors, "
    "soft depth of field, 4k resolution, consistent character design"
)


class SceneExtractor:
    """Extracts visual scenes from chapter text with rich character/location data."""

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.client = OpenRouterClient(model=model_name)
        self.store = ConsistencyStore()

    def extract_scenes(
        self,
        chapter_text: str,
        max_scenes: int = 8,
        chapter_id: str = "",
        prior_context: str = "",
    ) -> Dict[str, Any]:
        """Extract scenes, rich character profiles, and locations from chapter text.

        The LLM auto-populates ALL appearance fields even if the novel doesn't
        mention them, ensuring consistent image generation.
        """
        truncated_text = chapter_text[:50000]
        existing_db = self.store.export_for_llm()

        system = (
            "You are a screenplay assistant, cinematographer, and character designer. "
            "Output strict JSON. Do NOT wrap in markdown code fences."
        )
        
        context_block = ""
        if prior_context:
            context_block = f"PREVIOUS CHAPTER CONTEXT:\n{prior_context}\n\n"

        user = (
            f"{context_block}"
            f"Break this chapter into 3 to {max_scenes} scenes for illustration and narration.\n\n"
            "Return JSON with three keys: scenes, characters, locations.\n\n"
            "## scenes\n"
            "Array of objects:\n"
            "- id (int)\n"
            "- title (string)\n"
            "- visual_description (string) — detailed scene for illustration. Focus on the action and setting.\n"
            "- atmospheric_lighting (string) — e.g. 'dim distinct shadows', 'god rays', 'neon glow'\n"
            "- composition_notes (string) — e.g. 'wide shot', 'dutch angle', 'close up on face'\n"
            "- narrative_detail (string) — specific small details relevant to the story\n"
            "- sequence (array of objects) — chronological text segments. Each object MUST be:\n"
            "    - { 'type': 'narration', 'text': '...', 'mood': '...' } — 'mood' field for narrator prosody\n"
            "    - { 'type': 'dialogue', 'speaker': 'Name', 'text': '...', 'mood': '...' } — 'mood' field for voice Acting\n"
            "- characters (array of character names in this scene)\n"
            "- locations (array of location names in this scene)\n"
            "- time_of_day (string) — morning/afternoon/evening/night\n"
            "- lighting (string)\n"
            "- mood (string)\n\n"
            "CRITICAL:\n"
            "1. You MUST cover EVERY line of the original text. Do not summarize or skip.\n"
            "2. Preservation: 'he said', 'she yelled' must be in 'narration' segments placed strictly between dialogue segments.\n"
            "3. Visuals: 'visual_description' must be rich, consistent, and independent of the text sequence. Use 'atmospheric_lighting' and 'composition_notes' to guide the image generator.\n"
            "4. Output valid JSON only."
            "- estimated_duration (int) — seconds\n"
            "- transition_from_previous (string) — how this scene connects to the previous "
            "(e.g. 'moments later', 'same time different location', 'time skip'). Empty for scene 1.\n\n"
            "## characters\n"
            "Array of UNIQUE character profiles. CRITICAL: You MUST fill in ALL appearance fields "
            "even if the novel doesn't describe them. Invent plausible appearance details based on "
            "the character's role, personality, and cultural context. This is essential for "
            "consistent image generation.\n\n"
            "Fields per character:\n"
            "- name (string)\n"
            "- aliases (array of strings)\n"
            "- gender (string) — male/female\n"
            "- age_range (string) — e.g. '17-18', 'mid-30s'\n"
            "- build (string) — e.g. 'slender', 'athletic', 'stocky'\n"
            "- height (string) — e.g. 'average', 'tall'\n"
            "- skin_tone (string) — e.g. 'fair', 'tan', 'olive'\n"
            "- hair_color (string)\n"
            "- hair_style (string) — e.g. 'short cropped', 'long flowing', 'tied in bun'\n"
            "- eye_color (string)\n"
            "- clothing (string) — DETAILED current outfit\n"
            "- distinguishing_features (string) — scars, accessories, items carried\n"
            "- disposition (string) — current mood/expression\n"
            "- personality (string)\n"
            "- role (string) — protagonist, antagonist, side character, minor\n"
            "- vocal_description (string) — how their voice sounds\n\n"
            "## locations\n"
            "Array of UNIQUE location profiles:\n"
            "- name (string)\n"
            "- description (string) — physical description\n"
            "- architecture_style (string)\n"
            "- mood (string)\n"
            "- lighting (string)\n"
            "- time_of_day (string)\n"
            "- weather (string)\n"
            "- key_objects (array of strings)\n"
            "- color_palette (string) — dominant colors\n\n"
            "IMPORTANT:\n"
            "- If a character exists in the database below, keep their existing appearance "
            "but update clothing/disposition if changed in this chapter.\n"
            "- For NEW characters, invent ALL appearance details — do NOT leave any field empty.\n"
            "- narration should NOT include dialogue lines.\n"
            "- visual_description should be rich enough to generate an illustration.\n\n"
            f"EXISTING CHARACTER/LOCATION DATABASE:\n{existing_db}\n\n"
            f"CHAPTER TEXT:\n{truncated_text}"
        )

        response = self.client.generate_json(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=16384,
        )

        scenes = response.get("scenes", [])
        characters = response.get("characters", [])
        locations = response.get("locations", [])

        # Update consistency store
        self.store.upsert_characters(characters, chapter_id=chapter_id)
        self.store.upsert_locations(locations)
        logger.info(
            "Extracted %d scenes, %d characters, %d locations",
            len(scenes), len(characters), len(locations),
        )

        return {"scenes": scenes, "characters": characters, "locations": locations}

    def enrich_scene_prompts(
        self,
        scenes: List[Dict],
        chapter_id: str = "",
    ) -> List[Dict]:
        """Inject character/location descriptors into scene visual descriptions.

        Replaces character names with full appearance descriptions from the DB
        and appends consistent style tags + location context.
        """
        enriched = []
        prev_scene = None

        for scene in scenes:
            visual = scene.get("visual_description", "")

            # Inject character descriptors
            scene_characters = scene.get("characters", [])
            for char_name in scene_characters:
                descriptor = self.store.get_character_image_descriptor(
                    char_name, chapter_id=chapter_id
                )
                if descriptor != char_name:
                    # Replace first occurrence of bare name with full descriptor
                    visual = visual.replace(char_name, descriptor, 1)

            # Inject location descriptors
            scene_locations = scene.get("locations", [])
            location_context = []
            for loc_name in scene_locations:
                loc_desc = self.store.get_location_image_descriptor(loc_name)
                if loc_desc != loc_name:
                    location_context.append(loc_desc)

            if location_context:
                visual = f"{visual}. Setting: {'; '.join(location_context)}"

            # Scene transition consistency
            if prev_scene:
                transition = scene.get("transition_from_previous", "")
                prev_lighting = prev_scene.get("lighting", "")
                cur_lighting = scene.get("lighting", "")
                if transition and "moments later" in transition.lower() and prev_lighting:
                    if not cur_lighting:
                        scene["lighting"] = prev_lighting
                    visual = f"{visual}. Lighting consistent with previous scene: {prev_lighting}"

            # Add time of day and mood
            time_of_day = scene.get("time_of_day", "")
            mood = scene.get("mood", "")
            
            # Construct weighted prompt
            # Base visual (high weight)
            visual_parts = [f"({visual}:1.3)"]
            
            # Atmospheric lighting (medium weight)
            lighting = scene.get("atmospheric_lighting", "") or scene.get("lighting", "")
            if lighting:
                visual_parts.append(f"({lighting}:1.1)")
                
            # Composition (medium weight)
            composition = scene.get("composition_notes", "")
            if composition:
                visual_parts.append(f"({composition}:1.1)")
                
            # Details (normal weight)
            narrative = scene.get("narrative_detail", "")
            if narrative:
                visual_parts.append(narrative)
                
            if time_of_day:
                visual_parts.append(time_of_day)
            if mood:
                visual_parts.append(f"{mood} atmosphere")

            # Join all parts
            visual = ", ".join(visual_parts)

            # Append style tag
            visual = f"{visual}{IMAGE_STYLE_TAG}"

            scene["visual_description"] = visual
            prev_scene = scene
            enriched.append(scene)

        logger.info("Enriched %d scene prompts with character/location descriptors", len(enriched))
        return enriched
