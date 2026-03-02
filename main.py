"""
main.py — Novel Video Generator Pipeline Entry Point
EPUB → Scenes → Images → Audio → Video

10-Stage Pipeline:
 1. ingestor         — Parse EPUB
 2. normalizer       — Clean HTML → text
 3. scene_extractor  — LLM Pass 1: Scene splitting
 4. entity_resolver  — Character canonicalization
 5. speaker_annotator — LLM Pass 2: Speaker annotation (Alexandria)
 6. script_reviewer  — LLM Pass 3: Script review (Alexandria)
 7. prompt_builder   — Visual prompts (LLM Pass 4) + TTS entries
 8. image_generator  — Wan2GP images
 9. audio_generator  — Qwen3-TTS audio (Alexandria)
10. composer         — FFmpeg video
"""
import argparse
import logging
import sys

from rich.console import Console
from rich.panel import Panel

from pipeline.config import MIN_CHAPTER_WORD_COUNT
from pipeline.state_manager import (
    PIPELINE_STAGES,
    mark_stage_complete,
    is_stage_complete,
    should_skip_stage,
)

console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("ebooklib").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


# ── Startup Dependency Check ────────────────────────────────────────────────

# Packages that MUST be importable at startup (lightweight, no GPU)
_CORE_PACKAGES = [
    ("openai",     "openai",          "LLM client"),
    ("ebooklib",   "ebooklib",        "EPUB parsing"),
    ("bs4",        "beautifulsoup4",  "HTML parsing"),
    ("lxml",       "lxml",            "XML parsing"),
    ("rich",       "rich",            "CLI display"),
    ("dotenv",     "python-dotenv",   "Env config"),
]

# Packages needed for TTS/GPU — checked by importability only (not a cold import)
_GPU_PACKAGES = [
    ("torch",      "torch (see README for CUDA install)",  "GPU compute"),
    ("soundfile",  "soundfile",       "Audio I/O"),
    ("pydub",      "pydub",           "Audio processing"),
]


def check_dependencies():
    """Verify all critical packages are installed before pipeline runs."""
    missing = []
    broken = []

    # Check core packages
    for import_name, pip_name, desc in _CORE_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append((pip_name, desc))

    # Check GPU packages
    for import_name, pip_name, desc in _GPU_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append((pip_name, desc))

    # Check qwen-tts: use pip metadata instead of importing
    # (importing it pulls in transformers+torch and can fail for version reasons)
    try:
        from importlib.metadata import distribution
        distribution("qwen-tts")
    except Exception:
        missing.append(("qwen-tts", "TTS model"))

    if missing:
        console.print("[bold red]✗ Missing required packages:[/bold red]\n")
        for pip_name, desc in missing:
            console.print(f"  [red]• {pip_name}[/red]  ({desc})")
        console.print(
            "\n[bold]Install with:[/bold]\n"
            "  [cyan]pip install torch --index-url https://download.pytorch.org/whl/cu128[/cyan]\n"
            "  [cyan]pip install -r requirements.txt[/cyan]"
        )
        sys.exit(1)

    # Extra check: torch must have CUDA
    import torch
    if not torch.cuda.is_available():
        console.print(
            "[yellow]⚠ PyTorch is installed but CUDA is not available. "
            "TTS and image generation require GPU.[/yellow]\n"
            "[yellow]  Install CUDA version: pip install torch --index-url "
            "https://download.pytorch.org/whl/cu128[/yellow]"
        )


def _header(name: str, phase: str):
    console.print(Panel(f"[bold]{name}[/bold]", subtitle=phase, style="blue"))


def _pause(stage: str, interactive: bool):
    if interactive:
        console.print(f"\n[yellow]▸ Stage '{stage}' complete. Press Enter to continue...[/yellow]")
        input()


def run_pipeline(
    epub_path: str,
    chapter_filter: int | None = None,
    interactive: bool = False,
    from_stage: str | None = None,
):
    """Execute the full EPUB-to-Video pipeline."""

    # ── Stage 1: Ingestor ─────────────────────────────────────────────────────
    if not should_skip_stage("ingestor", from_stage):
        _header("Stage 1 — EPUB Ingestion", "Parsing book structure")
        from pipeline.ingestor import ingest_epub
        book_slug, chapter_ids = ingest_epub(epub_path)
        mark_stage_complete(book_slug, "ingestor")
        _pause("ingestor", interactive)
    else:
        # Need to figure out book_slug from existing data
        from pipeline.ingestor import ingest_epub
        book_slug, chapter_ids = ingest_epub(epub_path)

    # Apply chapter filter
    if chapter_filter is not None:
        if chapter_filter in chapter_ids:
            chapter_ids = [chapter_filter]
        else:
            console.print(f"[red]Chapter {chapter_filter} not found. Available: {chapter_ids}[/red]")
            return

    console.print(f"[bold]Book: {book_slug} | Chapters: {chapter_ids}[/bold]\n")

    # ── Stage 2: Normalizer ───────────────────────────────────────────────────
    if not should_skip_stage("normalizer", from_stage):
        _header("Stage 2 — Text Normalization", "HTML → clean text")
        from pipeline.normalizer import normalize_chapter

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "normalizer", cid):
                normalize_chapter(book_slug, cid)
                mark_stage_complete(book_slug, "normalizer", cid)

        _pause("normalizer", interactive)

    # ── Stage 3: Scene Extractor (LLM Pass 1) ────────────────────────────────
    if not should_skip_stage("scene_extractor", from_stage):
        _header("Stage 3 — Scene Extraction", "LLM Pass 1: Splitting into visual scenes")
        from pipeline.scene_extractor import extract_scenes

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "scene_extractor", cid):
                extract_scenes(book_slug, cid)
                mark_stage_complete(book_slug, "scene_extractor", cid)

        _pause("scene_extractor", interactive)

    # ── Stage 4: Entity Resolver ──────────────────────────────────────────────
    if not should_skip_stage("entity_resolver", from_stage):
        _header("Stage 4 — Entity Resolution", "Canonicalizing character and location names")
        from pipeline.entity_resolver import resolve_entities

        if not is_stage_complete(book_slug, "entity_resolver"):
            resolve_entities(book_slug, chapter_ids)
            mark_stage_complete(book_slug, "entity_resolver")

        _pause("entity_resolver", interactive)

    # ── Stage 5: Speaker Annotator (LLM Pass 2) ──────────────────────────────
    if not should_skip_stage("speaker_annotator", from_stage):
        _header("Stage 5 — Speaker Annotation", "LLM Pass 2: Annotating dialogue with speakers")
        from pipeline.speaker_annotator import annotate_speakers

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "speaker_annotator", cid):
                annotate_speakers(book_slug, cid)
                mark_stage_complete(book_slug, "speaker_annotator", cid)

        _pause("speaker_annotator", interactive)

    # ── Stage 6: Script Reviewer (LLM Pass 3) ────────────────────────────────
    if not should_skip_stage("script_reviewer", from_stage):
        _header("Stage 6 — Script Review", "LLM Pass 3: Fixing annotation errors")
        from pipeline.speaker_annotator import review_script

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "script_reviewer", cid):
                review_script(book_slug, cid)
                mark_stage_complete(book_slug, "script_reviewer", cid)

        _pause("script_reviewer", interactive)

    # ── Stage 7: Prompt Builder (LLM Pass 4) ──────────────────────────────────
    if not should_skip_stage("prompt_builder", from_stage):
        _header("Stage 7 — Prompt Building", "Visual prompts (LLM Pass 4) + TTS entries")
        from pipeline.prompt_builder import build_prompts

        if not is_stage_complete(book_slug, "prompt_builder"):
            build_prompts(book_slug, chapter_ids)
            mark_stage_complete(book_slug, "prompt_builder")

        _pause("prompt_builder", interactive)

    # ── Stage 8: Image Generation (Wan2GP) ────────────────────────────────────
    if not should_skip_stage("image_generator", from_stage):
        _header("Stage 8 — Image Generation", "Wan2GP AI image generation")
        from pipeline.image_queue import build_image_queue
        from pipeline.image_generator import generate_images

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "image_generator", cid):
                build_image_queue(book_slug, cid)
                generate_images(book_slug, cid)
                mark_stage_complete(book_slug, "image_generator", cid)

        _pause("image_generator", interactive)

    # ── Stage 9: Audio Generation (Qwen3-TTS) ────────────────────────────────
    if not should_skip_stage("audio_generator", from_stage):
        _header("Stage 9 — Audio Generation", "Qwen3-TTS voice synthesis")
        from pipeline.voice_manager import build_voice_config
        from pipeline.audio_generator import generate_chapter_audio, shutdown_engine

        voice_config = build_voice_config(book_slug)

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "audio_generator", cid):
                generate_chapter_audio(book_slug, cid, voice_config)
                mark_stage_complete(book_slug, "audio_generator", cid)

        shutdown_engine()  # Free GPU memory
        _pause("audio_generator", interactive)

    # ── Stage 10: Video Composition ───────────────────────────────────────────
    if not should_skip_stage("composer", from_stage):
        _header("Stage 10 — Video Composition", "FFmpeg compositing")
        from pipeline.composer import compose_chapter
        from pipeline.validator import validate_chapter_assets

        for cid in chapter_ids:
            if not is_stage_complete(book_slug, "composer", cid):
                validation = validate_chapter_assets(book_slug, cid)
                if not validation["valid"]:
                    console.print(
                        f"[yellow]⚠ Chapter {cid} has missing assets: "
                        f"{', '.join(validation['warnings'])}[/yellow]"
                    )
                    console.print("[yellow]  Composing with available assets...[/yellow]")

                result = compose_chapter(book_slug, cid)
                if result:
                    mark_stage_complete(book_slug, "composer", cid)

    console.print(Panel(
        "[bold green]✓ Pipeline complete![/bold green]",
        subtitle=f"{book_slug} — {len(chapter_ids)} chapter(s)",
        style="green",
    ))


def main():
    check_dependencies()

    parser = argparse.ArgumentParser(
        description="Novel Video Generator — EPUB to Video Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Stages: ingestor, normalizer, scene_extractor, entity_resolver,
        speaker_annotator, script_reviewer, prompt_builder,
        image_generator, audio_generator, composer

Examples:
  python main.py --epub book.epub
  python main.py --epub book.epub --chapter 1
  python main.py --epub book.epub --from-stage audio_generator
  python main.py --web-ui
        """,
    )
    parser.add_argument("--epub", type=str, help="Path to the EPUB file")
    parser.add_argument("--chapter", type=int, default=None, help="Process only this chapter")
    parser.add_argument("--interactive", action="store_true", help="Pause between stages")
    parser.add_argument("--from-stage", type=str, default=None, help="Resume from this stage")
    parser.add_argument("--web-ui", action="store_true", help="Launch interactive web UI")

    args = parser.parse_args()

    if args.web_ui:
        _launch_web_ui()
        return

    if not args.epub:
        parser.error("--epub is required (or use --web-ui)")
        return

    run_pipeline(
        epub_path=args.epub,
        chapter_filter=args.chapter,
        interactive=args.interactive,
        from_stage=args.from_stage,
    )


def _launch_web_ui():
    """Launch the Alexandria-based web UI."""
    import uvicorn
    from pipeline.config import WEB_UI_HOST, WEB_UI_PORT

    # Add app/ to path
    app_dir = str(__import__("pathlib").Path(__file__).parent / "app")
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)

    console.print(Panel(
        f"[bold]Novel Video Generator — Web UI[/bold]\n"
        f"Open [link=http://{WEB_UI_HOST}:{WEB_UI_PORT}]"
        f"http://{WEB_UI_HOST}:{WEB_UI_PORT}[/link] in your browser",
        style="blue",
    ))

    uvicorn.run(
        "app:app",
        host=WEB_UI_HOST,
        port=WEB_UI_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
