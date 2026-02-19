"""LLM-driven voice design for Qwen3.

Analyzes character profiles and generates vocal descriptions (gender, tone, pitch)
for Qwen3's voice cloning/design feature.
"""

import json
import logging
from typing import Dict, List, Optional

from ..llm.openrouter_client import OpenRouterClient
from .store import ConsistencyStore

logger = logging.getLogger(__name__)

def assign_voices_with_llm(
    store: ConsistencyStore,
    client: Optional[OpenRouterClient] = None,
) -> Dict[str, Dict]:
    """Use the LLM to design voices for characters that don't have one yet.
    
    Generates 'voice_design_params' (gender, description) which Qwen3 uses to 
    synthesize a unique voice.
    """
    characters = store.list_characters()
    if not characters:
        logger.info("No characters in DB, skipping voice assignment")
        return characters

    # Find characters that need voice assignment
    # We look for missing 'voice_sample_path' AND missing 'voice_design_params'
    needs_assignment = {}
    for name, data in characters.items():
        if not data.get("voice_sample_path") and not data.get("voice_design_params"):
             needs_assignment[name] = data

    if not needs_assignment:
        logger.info("All characters already have voices assigned/designed")
        return characters

    # Build character descriptions for LLM
    char_descriptions = []
    for name, data in needs_assignment.items():
        desc = (
            f"  {name}: gender={data.get('gender', 'unknown')}, "
            f"age={data.get('age_range', 'unknown')}, "
            f"personality={data.get('personality', 'unknown')}, "
            f"role={data.get('role', 'unknown')}, "
            f"appearance={data.get('description', '')}"
        )
        char_descriptions.append(desc)

    system = (
        "You are a casting director for an audio drama. "
        "Design a unique vocal profile for each character based on their description. "
        "Return strict JSON only."
    )
    user = (
        "Design a voice for each character below.\n\n"
        "CHARACTERS:\n"
        f"{chr(10).join(char_descriptions)}\n\n"
        "Return JSON with format:\n"
        "{\n"
        '  "assignments": [\n'
        '    {\n'
        '      "name": "Character Name",\n'
        '      "gender": "male|female",\n'
        '      "vocal_description": "A deep, gravelly voice with a slow pace... (max 20 words)",\n'
        '      "reason": "Matches their stoic warrior personality"\n'
        '    }\n'
        "  ]\n"
        "}\n"
    )

    if client is None:
        client = OpenRouterClient()

    try:
        response = client.generate_json(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        assignments = response.get("assignments", [])
        for entry in assignments:
            name = entry.get("name", "")
            if not name or name not in characters:
                continue

            gender = entry.get("gender", "male").lower()
            description = entry.get("vocal_description", "Standard voice")
            
            # Update store with design params
            # We treat this as the "voice_id" being qwen3_designed_<name>
            store.update_character_voice(
                name=name,
                voice_id=f"qwen3_{name}",
                voice_design_params={
                    "gender": gender,
                    "description": description
                },
                voice_notes=entry.get("reason", "")
            )
            logger.info("Voice designed: %s -> %s / %s", name, gender, description)

    except Exception as e:
        logger.error("LLM voice design failed: %s", e)
        # Fallback: just set gender based on explicit field
        for name, data in needs_assignment.items():
            g = data.get("gender", "male")
            store.update_character_voice(
                name=name,
                voice_id=f"qwen3_{name}",
                voice_design_params={
                    "gender": g, 
                    "description": f"Standard {g} voice"
                }
            )

    return store.list_characters()
