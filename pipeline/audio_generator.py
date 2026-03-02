"""
Stage 10: Audio Generator
Generates TTS audio using Alexandria's TTSEngine directly (no subprocess, no queue files).
Supports CustomVoice, VoiceDesign, Clone, and LoRA voice types.
"""
import json
import logging
import sys
from pathlib import Path

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console

from pipeline.config import novel_path, TTS_DEVICE, TTS_LANGUAGE, TTS_PARALLEL_WORKERS, TTS_COMPILE_CODEC

logger = logging.getLogger(__name__)
console = Console()

# Lazy-loaded TTSEngine singleton
_engine = None


def _get_engine():
    """Get or create the TTSEngine singleton."""
    global _engine
    if _engine is not None:
        return _engine

    # Add app/ to path so tts.py can be imported
    app_dir = str(Path(__file__).parent.parent / "app")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    from tts import TTSEngine

    config = {
        "tts": {
            "mode": "local",
            "device": TTS_DEVICE,
            "language": TTS_LANGUAGE,
            "parallel_workers": TTS_PARALLEL_WORKERS,
            "compile_codec": TTS_COMPILE_CODEC,
            "sub_batch_enabled": True,
            "sub_batch_min_size": 4,
            "sub_batch_ratio": 5,
            "sub_batch_max_chars": 3000,
        }
    }

    console.print("[bold blue]Loading Qwen3-TTS engine...[/bold blue]")
    _engine = TTSEngine(config)
    return _engine


def _audio_output_path(
    book_slug: str, chapter_id: int, scene_id: int, seq_index: int
) -> str:
    """Generate output path for a single audio segment."""
    path = Path(novel_path(
        book_slug, "audio", f"ch{chapter_id}",
        f"seq_{scene_id:03d}_{seq_index:03d}.wav",
    ))
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def generate_chapter_audio(
    book_slug: str, chapter_id: int, voice_config: dict
) -> int:
    """
    Generate all audio for a chapter using Alexandria's TTSEngine.

    Args:
        book_slug: Novel identifier.
        chapter_id: Chapter to generate.
        voice_config: Dict mapping speaker_name → voice config.

    Returns:
        Number of audio files generated.
    """
    tts_path = Path(novel_path(
        book_slug, "prompts", f"tts_entries_ch{chapter_id}.json"
    ))
    if not tts_path.exists():
        logger.error(f"Stage 10 — No TTS entries for ch{chapter_id}.")
        return 0

    tts_data = json.loads(tts_path.read_text(encoding="utf-8"))
    entries = tts_data.get("entries", [])

    if not entries:
        logger.warning(f"Stage 10 — No TTS entries for ch{chapter_id}, skipping.")
        return 0

    # Check which entries already have audio
    pending = []
    for entry in entries:
        out_path = _audio_output_path(
            book_slug, chapter_id, entry["scene_id"], entry["seq_index"]
        )
        if not Path(out_path).exists():
            entry["_output_path"] = out_path
            pending.append(entry)

    if not pending:
        logger.info(f"Stage 10 — All audio for ch{chapter_id} already exists.")
        return len(entries)

    engine = _get_engine()

    console.print(
        f"[bold blue]▶ Stage 10 — Generating audio for chapter {chapter_id} "
        f"({len(pending)} segments)[/bold blue]"
    )

    generated = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_bar = progress.add_task(
            f"TTS ch{chapter_id}", total=len(pending)
        )

        for entry in pending:
            speaker = entry["speaker"]
            text = entry["text"]
            instruct = entry.get("instruct", "")
            out_path = entry["_output_path"]

            try:
                # Ensure the speaker exists in voice_config, fall back to NARRATOR
                if speaker not in voice_config:
                    logger.warning(
                        f"No voice config for '{speaker}', using NARRATOR fallback."
                    )
                    speaker = "NARRATOR"

                # Pass instruct directly to Alexandria's generate_voice.
                # The TTS engine handles default_style from voice_config as
                # a fallback when instruct is empty — no manual prepend needed.
                success = engine.generate_voice(
                    text, instruct, speaker, voice_config, out_path
                )

                if success:
                    generated += 1
                else:
                    logger.warning(
                        f"TTS returned False for {speaker} "
                        f"(scene {entry['scene_id']}, seq {entry['seq_index']})"
                    )

            except Exception as e:
                logger.error(
                    f"Stage 10 — Failed to generate audio for "
                    f"{speaker} (scene {entry['scene_id']}, seq {entry['seq_index']}): {e}"
                )

            progress.update(task_bar, advance=1)

    console.print(
        f"[green]✓ Chapter {chapter_id} audio — "
        f"{generated}/{len(pending)} segments generated.[/green]"
    )
    return generated


def shutdown_engine() -> None:
    """Release TTS engine and free GPU memory."""
    global _engine
    if _engine is not None:
        del _engine
        _engine = None
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("TTS engine shutdown, GPU memory released.")
