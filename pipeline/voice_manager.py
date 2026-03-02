"""
Voice Manager
Bridges character_db.json voice profiles with Alexandria's TTSEngine voice config format.
Handles voice assignment, persistence across chapters, and config generation.
"""
import json
import logging
from pathlib import Path

from pipeline.config import novel_path, NARRATOR_VOICE, NARRATOR_STYLE

logger = logging.getLogger(__name__)

# Pre-trained voices available in Qwen3-TTS CustomVoice
CUSTOM_VOICE_PRESETS = [
    "Aiden", "Dylan", "Eric", "Ono_anna", "Ryan",
    "Serena", "Sohee", "Uncle_fu", "Vivian",
]


def build_voice_config(book_slug: str) -> dict:
    """
    Generate Alexandria-compatible voice config from annotated scripts.

    Scans all annotated/reviewed scripts to find unique speaker names,
    then assigns each a unique voice preset. This matches Alexandria's
    approach where voice config is keyed by the script's UPPERCASE speaker
    names (e.g. 'CHEN MOBAI', not 'Chen Mobai').

    Returns dict mapping speaker_name → VoiceConfigItem-compatible dict.
    """
    config_path = Path(novel_path(book_slug, "db", "voice_config.json"))
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))

    config = {
        "NARRATOR": {
            "type": "custom",
            "voice": NARRATOR_VOICE,
            "character_style": NARRATOR_STYLE,
            "default_style": NARRATOR_STYLE,
            "seed": "-1",
        }
    }

    # Scan all annotated/reviewed scripts for speaker names
    speakers = _collect_speakers_from_scripts(book_slug)

    # Assign a unique voice preset to each speaker (excluding NARRATOR)
    preset_index = 0
    for speaker in sorted(speakers):
        if speaker == "NARRATOR" or speaker in config:
            continue

        voice = CUSTOM_VOICE_PRESETS[preset_index % len(CUSTOM_VOICE_PRESETS)]
        preset_index += 1
        config[speaker] = {
            "type": "custom",
            "voice": voice,
            "character_style": "",
            "default_style": "",
            "seed": "-1",
        }

    _save_config(config, config_path)
    logger.info(f"Voice manager — Generated config for {len(config)} speakers.")
    return config


def _collect_speakers_from_scripts(book_slug: str) -> set[str]:
    """Scan all annotated/reviewed scripts and collect unique speaker names."""
    speakers = set()
    scenes_dir = Path(novel_path(book_slug, "chapters", "scenes"))

    if not scenes_dir.exists():
        return speakers

    # Check reviewed scripts first, then annotated
    for pattern in ["reviewed_script_ch*.json", "annotated_script_ch*.json"]:
        for script_path in sorted(scenes_dir.glob(pattern)):
            try:
                data = json.loads(script_path.read_text(encoding="utf-8"))

                # Handle nested list structure (batched review output)
                if data and isinstance(data[0], list):
                    data = [e for batch in data for e in batch if isinstance(e, dict)]

                for entry in data:
                    if isinstance(entry, dict):
                        speaker = entry.get("speaker", "")
                        if speaker:
                            speakers.add(speaker)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Voice manager — Failed to read {script_path.name}: {e}")

    return speakers


def _narrator_only_config() -> dict:
    return {
        "NARRATOR": {
            "type": "custom",
            "voice": NARRATOR_VOICE,
            "character_style": NARRATOR_STYLE,
            "default_style": NARRATOR_STYLE,
            "seed": "-1",
        }
    }


def _save_config(config: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def update_voice_config(book_slug: str, updates: dict) -> dict:
    """
    Update specific voice entries in the config.
    Used by the web UI when user changes voice assignments.
    """
    config_path = Path(novel_path(book_slug, "db", "voice_config.json"))
    config = build_voice_config(book_slug)  # ensures it exists

    config.update(updates)
    _save_config(config, config_path)
    logger.info(f"Voice manager — Updated {len(updates)} voice entries.")
    return config
