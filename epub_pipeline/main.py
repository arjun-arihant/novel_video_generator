"""
main.py — EPUB to Video Pipeline Entry Point
Usage: python main.py --epub path/to/book.epub [--chapter N] [--interactive] [--from-stage STAGE]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

# Ensure epub_pipeline dir is on path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.ingestor import ingest
from pipeline.normalizer import normalize_all
from pipeline.extractor import extract_all_chapters
from pipeline.entity_resolver import resolve_entities
from pipeline.state_manager import update_state_for_chapter
from pipeline.validator import validate_all
from pipeline.prompt_builder import build_prompts_for_chapter
from pipeline.image_queue import build_image_queue
from pipeline.audio_queue import build_audio_queues
from pipeline.generator import generate_images, generate_audio
from pipeline.composer import compose_chapter
from config import novel_path

console = Console()

STAGE_ORDER = [
    "ingestor",
    "normalizer",
    "extractor",
    "entity_resolver",
    "state_manager",
    "validator",
    "prompt_builder",
    "image_queue",
    "audio_queue",
    "generator",
    "composer",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
# Reduce noise from external libraries
logging.getLogger("ebooklib").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def _stage_header(name: str, phase: str) -> None:
    console.print(
        Panel(
            f"[bold]{name}[/bold]",
            subtitle=phase,
            style="bold blue",
            expand=False,
        )
    )


def _interactive_pause(stage: str, interactive: bool) -> None:
    if not interactive:
        return
    Confirm.ask(
        f"\n[yellow]⏸  Paused after '{stage}'. Press Enter to continue...[/yellow]",
        default=True,
    )


def _should_skip_stage(stage_name: str, from_stage: str | None) -> bool:
    """Return True if this stage should be skipped due to --from-stage."""
    if from_stage is None:
        return False
    if stage_name == from_stage:
        return False
    try:
        return STAGE_ORDER.index(stage_name) < STAGE_ORDER.index(from_stage)
    except ValueError:
        return False


def _load_raw_book(book_slug: str) -> dict:
    raw_path = novel_path(book_slug, "chapters", "raw", "raw_book.json")
    return json.loads(Path(raw_path).read_text(encoding="utf-8"))


def _load_normalized_chapter(book_slug: str, chapter_id: int) -> dict:
    path = novel_path(book_slug, "chapters", "normalized", f"normalized_ch{chapter_id}.json")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_pipeline(
    epub_path: str,
    chapter_filter: int | None = None,
    interactive: bool = False,
    from_stage: str | None = None,
) -> None:
    console.print(
        Panel(
            "[bold white]EPUB -> VIDEO PIPELINE[/bold white]\n"
            f"[dim]Book: {epub_path}[/dim]",
            style="bold magenta",
        )
    )

    # ═══════════════════════════════════════════════════════
    # PHASE A — EXTRACTION
    # ═══════════════════════════════════════════════════════
    console.print("\n[bold cyan]=== PHASE A - EXTRACTION ===[/bold cyan]")

    # Stage 0: Ingest
    if not _should_skip_stage("ingestor", from_stage):
        _stage_header("Stage 0: EPUB Ingestion", "Phase A")
        book_slug, _ = ingest(epub_path)
        console.print(f"[green]✓ Book slug: {book_slug}[/green]")
    else:
        # Derive slug from existing raw_book.json if skipping
        # We still need the slug for all downstream stages
        book_slug, _ = ingest(epub_path)  # idempotent — won't re-process

    raw_book = _load_raw_book(book_slug)
    all_chapters = raw_book["chapters"]

    # Filter to specific chapter if requested
    if chapter_filter is not None:
        chapters = [c for c in all_chapters if c["chapter_id"] == chapter_filter]
        if not chapters:
            console.print(
                f"[red]✗ Chapter {chapter_filter} not found in book.[/red]"
            )
            sys.exit(1)
    else:
        chapters = all_chapters

    chapter_ids = [c["chapter_id"] for c in chapters]

    # Stage 1: Normalize
    if not _should_skip_stage("normalizer", from_stage):
        _stage_header("Stage 1: Normalization", "Phase A")
        normalize_all(book_slug, {"chapters": chapters})
        console.print(f"[green]✓ Normalized {len(chapters)} chapter(s).[/green]")

    # Stage 2: Extract scenes (LLM)
    if not _should_skip_stage("extractor", from_stage):
        _stage_header("Stage 2: Scene Extraction (LLM)", "Phase A")
        normalized_chapters = [
            _load_normalized_chapter(book_slug, cid) for cid in chapter_ids
        ]
        extract_all_chapters(book_slug, normalized_chapters)
        console.print(f"[green]✓ Scenes extracted for {len(chapters)} chapter(s).[/green]")

    _interactive_pause("extraction", interactive)

    # ═══════════════════════════════════════════════════════
    # PHASE B — CANONICALIZATION + STATE
    # ═══════════════════════════════════════════════════════
    console.print("\n[bold cyan]=== PHASE B - CANONICALIZATION + STATE ===[/bold cyan]")

    # Stage 3: Entity resolver (one LLM call for whole book)
    if not _should_skip_stage("entity_resolver", from_stage):
        _stage_header("Stage 3: Entity Resolver (LLM)", "Phase B")
        resolve_entities(book_slug, chapter_ids)
        console.print("[green]✓ Canonical maps built and scenes_canonical written.[/green]")

    # Stage 4: State manager (per chapter, in order)
    if not _should_skip_stage("state_manager", from_stage):
        _stage_header("Stage 4: State Manager (LLM)", "Phase B")
        for cid in chapter_ids:
            console.print(f"  [dim]Processing chapter {cid}...[/dim]")
            update_state_for_chapter(book_slug, cid)
        console.print("[green]✓ character_db and location_db updated.[/green]")

    # Stage 5: Validation pass
    if not _should_skip_stage("validator", from_stage):
        _stage_header("Stage 5: Validation", "Phase B")
        validate_all(book_slug, chapter_ids)

    _interactive_pause("canonicalization + state", interactive)

    # ═══════════════════════════════════════════════════════
    # PHASE C — GENERATION (per chapter)
    # ═══════════════════════════════════════════════════════
    console.print("\n[bold cyan]=== PHASE C - GENERATION ===[/bold cyan]")

    for cid in chapter_ids:
        console.print(f"\n[bold]--- Chapter {cid} ---[/bold]")

        # Stage 6: Build prompts
        if not _should_skip_stage("prompt_builder", from_stage):
            _stage_header(f"Stage 6: Prompt Builder — Ch{cid}", "Phase C")
            build_prompts_for_chapter(book_slug, cid)

        # Stage 7: Build image queue
        if not _should_skip_stage("image_queue", from_stage):
            _stage_header(f"Stage 7: Image Queue — Ch{cid}", "Phase C")
            build_image_queue(book_slug, cid)

        # Stage 8: Build audio queues
        if not _should_skip_stage("audio_queue", from_stage):
            _stage_header(f"Stage 8: Audio Queues — Ch{cid}", "Phase C")
            build_audio_queues(book_slug, cid)

        # Stage 9+: Generate images and audio via Wan2GP
        if not _should_skip_stage("generator", from_stage):
            generate_images(book_slug, cid)
            generate_audio(book_slug, cid)

        # Stage 13: Compose chapter video
        if not _should_skip_stage("composer", from_stage):
            _stage_header(f"Stage 13: Video Composition — Ch{cid}", "Phase C")
            out_path = compose_chapter(book_slug, cid)
            if out_path:
                console.print(f"[bold green]✓ Output: {out_path}[/bold green]")

    console.print(
        Panel(
            "[bold green]Pipeline complete![/bold green]",
            style="bold green",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="epub_pipeline",
        description="Convert an EPUB ebook into narrated chapter videos.",
    )
    parser.add_argument("--epub", required=True, help="Path to the EPUB file.")
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Process only this chapter number (for testing).",
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="Pause after each major phase for user confirmation.",
    )
    parser.add_argument(
        "--from-stage",
        metavar="STAGE",
        choices=STAGE_ORDER,
        default=None,
        help=(
            "Resume from a specific stage. "
            f"Valid stages: {', '.join(STAGE_ORDER)}"
        ),
    )
    args = parser.parse_args()

    epub_path = str(Path(args.epub).resolve())
    if not Path(epub_path).exists():
        console.print(f"[red]✗ EPUB not found: {epub_path}[/red]")
        sys.exit(1)

    run_pipeline(
        epub_path=epub_path,
        chapter_filter=args.chapter,
        interactive=args.interactive,
        from_stage=args.from_stage,
    )


if __name__ == "__main__":
    main()
