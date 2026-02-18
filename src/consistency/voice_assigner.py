"""LLM-driven voice assignment for characters.

Uses OpenRouter to analyze character profiles and select the best
Kokoro voice (en-us / en-gb only) for each character. Can suggest
voice mixes for unique characters.
"""

import json
import logging
from typing import Dict, List, Optional

from ..llm.openrouter_client import OpenRouterClient
from .store import ConsistencyStore

logger = logging.getLogger(__name__)

# All en-US and en-GB Kokoro voices available for assignment
AVAILABLE_VOICES = {
    # American English
    "af_heart": {"gender": "F", "lang": "en-US", "desc": "Warm, conversational, natural breathiness, young adult, ~177 WPM, flagship"},
    "af_bella": {"gender": "F", "lang": "en-US", "desc": "Intimate, slightly husky, modern personality, ~168 WPM"},
    "af_nicole": {"gender": "F", "lang": "en-US", "desc": "Whisper-soft, deeply intimate, ASMR/relaxation, very slow ~117 WPM"},
    "af_aoede": {"gender": "F", "lang": "en-US", "desc": "Clear and melodic, balanced tone, good for narration"},
    "af_kore": {"gender": "F", "lang": "en-US", "desc": "Clean, neutral, suitable for assistants"},
    "af_sarah": {"gender": "F", "lang": "en-US", "desc": "Clear, friendly, educator tone, ~173 WPM"},
    "af_alloy": {"gender": "F", "lang": "en-US", "desc": "Versatile general-purpose, balanced neutral tone"},
    "af_nova": {"gender": "F", "lang": "en-US", "desc": "Natural, approachable, good for guides, ~193 WPM"},
    "af_jessica": {"gender": "F", "lang": "en-US", "desc": "Bright, energetic young adult, fast ~206 WPM"},
    "af_river": {"gender": "F", "lang": "en-US", "desc": "Soft and flowing, gentle smooth delivery"},
    "af_sky": {"gender": "F", "lang": "en-US", "desc": "Polished, blends professional clarity with warmth, ~183 WPM"},
    "am_fenrir": {"gender": "M", "lang": "en-US", "desc": "Energetic, clear, ideal for explainers, ~173 WPM"},
    "am_michael": {"gender": "M", "lang": "en-US", "desc": "Warm, conversational, well-suited for narration, ~157 WPM"},
    "am_puck": {"gender": "M", "lang": "en-US", "desc": "Energetic, youthful, great for gaming/modern, ~176 WPM"},
    # am_adam removed per user request (bad quality)
    "am_echo": {"gender": "M", "lang": "en-US", "desc": "Mid-range, balanced delivery, general-purpose"},
    "am_eric": {"gender": "M", "lang": "en-US", "desc": "Clear, neutral, straightforward narration"},
    "am_liam": {"gender": "M", "lang": "en-US", "desc": "Friendly, conversational, approachable tone"},
    "am_onyx": {"gender": "M", "lang": "en-US", "desc": "Rich, sophisticated, deep voice with authority"},
    "am_santa": {"gender": "M", "lang": "en-US", "desc": "Novelty/character voice, distinctive older quality"},
    # British English
    "bf_emma": {"gender": "F", "lang": "en-GB", "desc": "Warm, professional, friendly British, ~185 WPM"},
    "bf_isabella": {"gender": "F", "lang": "en-GB", "desc": "Warm, articulate, polished yet intimate, ~185 WPM"},
    "bf_alice": {"gender": "F", "lang": "en-GB", "desc": "Refined, elegant British female"},
    "bf_lily": {"gender": "F", "lang": "en-GB", "desc": "Sweet, gentle, warm articulate delivery, ~184 WPM"},
    "bm_fable": {"gender": "M", "lang": "en-GB", "desc": "Refined, velvety, natural storytelling cadence"},
    "bm_george": {"gender": "M", "lang": "en-GB", "desc": "Classic British, mature, great for narration, ~165 WPM"},
    "bm_daniel": {"gender": "M", "lang": "en-GB", "desc": "Crisp, articulate, professional with warmth, ~194 WPM"},
    "bm_lewis": {"gender": "M", "lang": "en-GB", "desc": "Traditional British, measured steady delivery"},
}

# Reserved: narrator always uses this voice
NARRATOR_VOICE = "am_puck"


def assign_voices_with_llm(
    store: ConsistencyStore,
    client: Optional[OpenRouterClient] = None,
) -> Dict[str, Dict]:
    """Use the LLM to assign Kokoro voices to characters that don't have one yet.

    Already-assigned voices are preserved. Only unassigned characters get new voices.
    Returns the updated characters dict.
    """
    characters = store.list_characters()
    if not characters:
        logger.info("No characters in DB, skipping voice assignment")
        return characters

    # Find characters that need voice assignment
    needs_assignment = {
        name: data for name, data in characters.items()
        if not data.get("voice_id")
    }
    if not needs_assignment:
        logger.info("All characters already have voices assigned")
        return characters

    already_used = store.get_all_assigned_voices()
    already_used.append(NARRATOR_VOICE)  # reserve narrator voice

    # Build voice catalog for LLM (exclude already-used voices)
    voice_catalog = []
    for vid, info in AVAILABLE_VOICES.items():
        status = "TAKEN" if vid in already_used else "available"
        voice_catalog.append(
            f"  {vid} | {info['gender']} | {info['lang']} | {info['desc']} | {status}"
        )

    # Build character descriptions for LLM
    char_descriptions = []
    for name, data in needs_assignment.items():
        desc = (
            f"  {name}: gender={data.get('gender', 'unknown')}, "
            f"age={data.get('age_range', 'unknown')}, "
            f"personality={data.get('personality', 'unknown')}, "
            f"disposition={data.get('disposition', 'unknown')}, "
            f"role={data.get('role', 'unknown')}"
        )
        char_descriptions.append(desc)

    system = (
        "You are a voice casting director. Assign the best Kokoro TTS voice to each character. "
        "Return strict JSON only."
    )
    user = (
        "Assign a voice to each character below from the available Kokoro voices.\n\n"
        "RULES:\n"
        "- Match voice gender to character gender\n"
        "- Match voice personality/tone to character personality\n"
        "- Prefer 'available' voices over 'TAKEN' ones\n"
        "- For unique characters, you may suggest a voice_mix of 2 voices (both must be same gender)\n"
        "- voice_speed: 0.8 for elderly/calm, 1.0 normal, 1.2 for energetic/young\n"
        "- Each character must get a DIFFERENT voice\n\n"
        "VOICES:\n"
        f"{chr(10).join(voice_catalog)}\n\n"
        "CHARACTERS NEEDING VOICES:\n"
        f"{chr(10).join(char_descriptions)}\n\n"
        "Return JSON with format:\n"
        "{\n"
        '  "assignments": [\n'
        '    {"name": "...", "voice_id": "...", "voice_mix": [], "voice_speed": 1.0, "reason": "..."}\n'
        "  ]\n"
        "}\n"
        "voice_mix should be empty [] for standard voice, or [\"voice1\", \"voice2\"] for a blend."
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
            voice_id = entry.get("voice_id", "")
            if not name or not voice_id:
                continue
            if voice_id not in AVAILABLE_VOICES:
                logger.warning("LLM picked invalid voice '%s' for %s, skipping", voice_id, name)
                continue
            store.update_character_voice(
                name=name,
                voice_id=voice_id,
                voice_mix=entry.get("voice_mix", []),
                voice_speed=entry.get("voice_speed", 1.0),
                voice_notes=entry.get("reason", ""),
            )
            logger.info("Voice assigned: %s → %s (%s)", name, voice_id, entry.get("reason", ""))

    except Exception as e:
        logger.error("LLM voice assignment failed: %s", e)
        _fallback_assignment(store, needs_assignment, already_used)

    return store.list_characters()


def _fallback_assignment(
    store: ConsistencyStore,
    characters: Dict[str, Dict],
    already_used: List[str],
) -> None:
    """Fallback: assign voices by gender round-robin if LLM fails."""
    male_voices = [v for v, i in AVAILABLE_VOICES.items()
                   if i["gender"] == "M" and v not in already_used]
    female_voices = [v for v, i in AVAILABLE_VOICES.items()
                     if i["gender"] == "F" and v not in already_used]
    m_idx, f_idx = 0, 0

    for name, data in characters.items():
        if data.get("voice_id"):
            continue
        gender = (data.get("gender") or "").lower()
        if "female" in gender or "woman" in gender or "girl" in gender:
            if f_idx < len(female_voices):
                store.update_character_voice(name, female_voices[f_idx])
                f_idx += 1
            elif m_idx < len(male_voices):
                store.update_character_voice(name, male_voices[m_idx])
                m_idx += 1
        else:
            if m_idx < len(male_voices):
                store.update_character_voice(name, male_voices[m_idx])
                m_idx += 1
            elif f_idx < len(female_voices):
                store.update_character_voice(name, female_voices[f_idx])
                f_idx += 1
    logger.info("Fallback voice assignment completed")
