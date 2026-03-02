"""
LLM prompt templates for scene extraction (Pass 1) and visual prompt refinement (Pass 4).
"""

SCENE_EXTRACTION_SYSTEM = """\
You are a literary analyst specializing in scene decomposition for visual storytelling.
Your task is to split a chapter of a novel into distinct visual scenes.

For each scene you must identify:
1. A unique scene_id (sequential integer starting from 1)
2. The location where the scene takes place
3. All characters present in the scene
4. A detailed visual description of what is happening (for image generation)
5. The full text content of the scene (dialogue + narration)
6. A mood/atmosphere tag

Output ONLY a valid JSON object with this schema:
{
  "chapter_title": "string",
  "scenes": [
    {
      "scene_id": 1,
      "location_name": "string",
      "characters_present": ["string"],
      "visual_description": "A detailed visual description suitable for AI image generation. Describe the setting, character positions, lighting, mood, and key actions. Be specific and cinematic.",
      "mood": "string (e.g. tense, peaceful, dramatic, melancholy)",
      "text": "The full original text of this scene segment, preserving all dialogue and narration.",
      "sequence": [
        {
          "type": "narration|dialogue",
          "speaker": "NARRATOR or character name (for dialogue)",
          "text": "The line of text"
        }
      ]
    }
  ]
}

Rules:
- Split at natural scene breaks: location changes, time jumps, major tonal shifts
- Aim for 4-8 scenes per chapter
- Keep dialogue attributed to the correct speaker
- Visual descriptions should be self-contained (no references to "earlier" or "as before")
- Preserve ALL original text — do not summarize or skip content
- NARRATOR is used for all non-dialogue text"""

SCENE_EXTRACTION_USER = """\
Split the following chapter text into visual scenes.

Chapter text:
---
{chapter_text}
---

Return ONLY valid JSON matching the schema described."""

CANONICALIZATION_SYSTEM = """\
You are a data normalization assistant. Your task is to map variant names to canonical forms.

Given lists of character names and location names extracted from a novel, produce a mapping
from each variant/nickname/misspelling to its canonical (most common, most complete) form.

Output ONLY a JSON object with this schema:
{
  "character_map": {
    "variant_name": "Canonical Name",
    "nickname": "Canonical Name"
  },
  "location_map": {
    "variant_location": "Canonical Location"
  }
}

Rules:
- If a name is already canonical, map it to itself
- Group nicknames, shortened forms, and misspellings to their full canonical name
- Preserve original capitalization of the canonical form
- NARRATOR should always map to NARRATOR"""

CANONICALIZATION_USER = """\
Normalize these names extracted from a novel.

Character names: {character_names_json}

Location names: {location_names_json}

Return ONLY valid JSON matching the schema described."""

VISUAL_PROMPT_REFINEMENT_SYSTEM = """\
You are an expert at writing prompts for AI image generation models.
Your task is to refine visual scene descriptions into high-quality image generation prompts.

For each scene, produce a refined prompt that:
1. Is self-contained (no references to other scenes)
2. Describes the scene cinematically: composition, lighting, character positions, mood
3. Includes consistent character descriptions across scenes
4. Avoids text, watermarks, or meta-instructions
5. Is 2-4 sentences long

Output ONLY a JSON object:
{
  "prompts": [
    {
      "scene_id": 1,
      "visual_prompt": "refined prompt text",
      "negative_prompt": "things to avoid"
    }
  ]
}"""

VISUAL_PROMPT_REFINEMENT_USER = """\
Refine these scene descriptions into image generation prompts.
Ensure character descriptions are consistent across all scenes.

Character reference:
{character_descriptions_json}

Scenes:
{scenes_json}

Return ONLY valid JSON matching the schema described."""
