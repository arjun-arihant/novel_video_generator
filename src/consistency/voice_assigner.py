"""Assign voice presets to characters based on descriptions."""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

MALE_PRESETS = [
    "narrator_male_1",
    "narrator_male_2",
    "narrator_male_3",
    "narrator_male_4",
    "narrator_male_5",
]
FEMALE_PRESETS = [
    "narrator_female_1",
    "narrator_female_2",
    "narrator_female_3",
    "narrator_female_4",
    "narrator_female_5",
]


def assign_voice(characters: Dict[str, Dict], used_voices: List[str]) -> Dict[str, Dict]:
    """Assign a voice preset to each character if missing."""
    for name, data in characters.items():
        if data.get("voice_preset"):
            continue
        gender = (data.get("gender") or "").lower()
        voice_notes = (data.get("vocal_description") or "").lower()
        candidates = FEMALE_PRESETS if "female" in gender or "woman" in gender or "girl" in voice_notes else MALE_PRESETS
        choice = next((v for v in candidates if v not in used_voices), None)
        if not choice:
            choice = next((v for v in MALE_PRESETS + FEMALE_PRESETS if v not in used_voices), None)
        if not choice:
            choice = (MALE_PRESETS + FEMALE_PRESETS)[0]
        data["voice_preset"] = choice
        used_voices.append(choice)
        logger.info("Assigned voice %s to %s", choice, name)
    return characters
