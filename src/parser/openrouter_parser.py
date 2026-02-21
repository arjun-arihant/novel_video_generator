"""Enriched scene extraction using OpenRouter.

Extracts scenes with rich character profiles (auto-populates missing appearance fields),
location descriptions, and scene transition metadata. Enriches visual descriptions with
character DB data for consistent image generation.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from ..consistency.store import ConsistencyStore
from ..llm.openrouter_client import OpenRouterClient

logger = logging.getLogger(__name__)

# Image style template appended to every visual description
IMAGE_STYLE_TAG = (
    ", detailed cinematic manhua webtoon style, clean line art, vibrant colors, "
    "soft depth of field"
)


class SceneExtractor:
    """Extracts visual scenes from chapter text with rich character/location data."""

    def __init__(self, model_name: Optional[str] = None, consistency_dir: Optional[Any] = None) -> None:
        self.client = OpenRouterClient(model=model_name)
        # Each novel needs its own consistency store
        if consistency_dir is None:
            raise ValueError("consistency_dir is required - each novel needs its own consistency store")
        self.store = ConsistencyStore(consistency_dir)

    def extract_scenes(
        self,
        chapter_text: Union[str, List[str]],
        max_scenes: int = 8,
        chapter_id: str = "",
        prior_context: str = "",
    ) -> Dict[str, Any]:
        """Extract scenes, rich character profiles, and locations from chapter text.

        The LLM auto-populates ALL appearance fields even if the novel doesn't
        mention them, ensuring consistent image generation.
        """
        if isinstance(chapter_text, str):
            chunks = [chapter_text[:50000]]
        else:
            chunks = chapter_text
            
        existing_db = self.store.export_for_llm()

        system = (
            "You are a professional storyboard artist and screenwriter for an animated adaptation "
            "of a fantasy/cultivation novel. You take chapters and break them down into visually "
            "distinct scenes."
        )
        
        context_block = ""
        if prior_context:
            context_block = f"PREVIOUS CHAPTER CONTEXT:\n{prior_context}\n\n"

        user_template = (
            f"{context_block}"
            f"Break this chapter into 3 to {{max_scenes}} scenes for illustration and narration.\n\n"
            "Return JSON with three keys: scenes, characters, locations.\n\n"
            "## scenes\n"
            "Array of scene objects:\n"
            "- id (int)\n"
            "- title (string)\n"
            "- visual_description (string) — A 2-4 line concise description of ONLY what is physically visible in this specific single camera frame. Do NOT describe impossible perspectives (e.g., a front closeup of a face while also detailing the phone screen they look at, or a tight shot that also describes the entire 360-degree room and outside scenery). Instead of using proper nouns or names, describe subjects and locations entirely through their physical traits and clothing using the existing database. Do NOT refer to previous scenes or external context. Every prompt must be 100% self-sufficient and independent. Example: 'A brightly lit classroom with wooden desks. A teenage boy with messy black hair wearing a white uniform sits by the window reading a book.'\n"
            "- atmospheric_lighting (string) — e.g. 'dim distinct shadows', 'god rays', 'neon glow'\n"
            "- composition_notes (string) — e.g. 'wide shot', 'dutch angle', 'close up on face'\n"
            "- narrative_detail (string) — specific small details relevant to the story\n"
            "- sequence (array of objects): The exact narrative flow, including BOTH narration and dialogue in order.\n"
            "   Each sequence item has:\n"
            "   - type (string): either 'narration' or 'dialogue'\n"
            "   - text (string): the actual paragraph or spoken line\n"
            "   - speaker (string): character name if dialogue, or 'narrator' if narration\n"
            "- characters (array of character names in this scene)\n"
            "- locations (array of location names in this scene)\n"
            "- time_of_day (string) — morning/afternoon/evening/night\n"
            "- weather (string) — clear/rain/snow/fog/etc\n"
            "- mood (string)\n\n"
            "CRITICAL:\n"
            "1. You MUST cover EVERY line of the original text. Do not summarize or skip.\n"
            "2. Ensure the sequence perfectly matches the flow of the chapter chunk.\n"
            "3. The sequence should interleave narration blocks and dialogue blocks naturally.\n\n"
            "## characters\n"
            "Array of UNIQUE character profiles appearing in this chunk (use existing if possible):\n"
            "- name (string)\n"
            "- age (string)\n"
            "- gender (string)\n"
            "- appearance (string) — physical traits\n"
            "- clothing (string) — what they are wearing in this chapter\n"
            "- disposition (string) — their current emotional state\n"
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
            "- visual_description should be unique for every scene to avoid repetition in generated videos.\n\n"
            "EXISTING CHARACTER/LOCATION DATABASE:\n{existing_db}\n\n"
            "CHAPTER TEXT CHUNK:\n{chunk_text}"
        )

        all_scenes = []
        all_characters = []
        all_locations = []
        
        # Max scenes per chunk logic
        scenes_per_chunk = max(3, max_scenes // len(chunks)) if len(chunks) > 0 else max_scenes
        
        current_scene_id = 1

        for i, chunk in enumerate(chunks):
            logger.info("Extracting from chunk %d/%d (%d words)", i+1, len(chunks), len(chunk.split()))
            
            # Format the prompt for this specific chunk
            chunk_user_prompt = user_template.format(
                context_block=context_block,
                max_scenes=scenes_per_chunk,
                existing_db=existing_db,
                chunk_text=chunk
            )
            
            response = self.client.generate_json(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": chunk_user_prompt},
                ],
                max_tokens=16384,
            )
            
            chunk_scenes = response.get("scenes", [])
            for scene in chunk_scenes:
                scene["id"] = current_scene_id  # Enforce sequential IDs across chunks
                current_scene_id += 1
                all_scenes.append(scene)
                
            all_characters.extend(response.get("characters", []))
            all_locations.extend(response.get("locations", []))

        # Deduplicate characters
        unique_characters = []
        seen_chars = set()
        for char in all_characters:
            if char.get("name") not in seen_chars:
                unique_characters.append(char)
                seen_chars.add(char.get("name"))
                
        # Deduplicate locations
        unique_locations = []
        seen_locs = set()
        for loc in all_locations:
            if loc.get("name") not in seen_locs:
                unique_locations.append(loc)
                seen_locs.add(loc.get("name"))

        # Update consistency store with deductive sets
        self.store.upsert_characters(unique_characters, chapter_id=chapter_id)
        self.store.upsert_locations(unique_locations)
        logger.info(
            "Extracted %d scenes, %d characters, %d locations across %d chunks",
            len(all_scenes), len(unique_characters), len(unique_locations), len(chunks)
        )

        return {"scenes": all_scenes, "characters": unique_characters, "locations": unique_locations}

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

            # Scene transition consistency
            if prev_scene:
                transition = scene.get("transition_from_previous", "")
                prev_lighting = prev_scene.get("lighting", "")
                cur_lighting = scene.get("lighting", "")
                if transition and "moments later" in transition.lower() and prev_lighting:
                    if not cur_lighting:
                        scene["lighting"] = prev_lighting
                    visual = f"{visual}, consistent lighting with previous frame"

            # Add time of day and mood
            time_of_day = scene.get("time_of_day", "")
            mood = scene.get("mood", "")
            
            # Construct natural prompt without excessive weighting
            visual_parts = [visual]
            
            # Atmospheric lighting
            lighting = scene.get("atmospheric_lighting", "") or scene.get("lighting", "")
            if lighting:
                visual_parts.append(f"lighting: {lighting}")
                
            # Composition
            composition = scene.get("composition_notes", "")
            if composition:
                visual_parts.append(composition)
                
            # Details
            narrative = scene.get("narrative_detail", "")
            if narrative:
                visual_parts.append(narrative)
                
            if time_of_day:
                visual_parts.append(time_of_day)
            if mood:
                visual_parts.append(f"{mood} atmosphere")

            # Join all parts naturally
            visual = ", ".join(visual_parts)

            # Append style tag
            visual = f"{visual}{IMAGE_STYLE_TAG}"

            scene["visual_description"] = visual
            prev_scene = scene
            enriched.append(scene)

        logger.info("Enriched %d scene prompts with character/location descriptors", len(enriched))
        return enriched
