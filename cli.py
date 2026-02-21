"""Unified CLI for novel video generator pipeline.

Enriched pipeline: extract → enrich characters → assign voices → generate images → generate audio → compose video
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.common import setup_logging, validate_chapter, validate_scenes, ensure_output_dir
from src.parser.openrouter_parser import SceneExtractor
from src.image.generator import ImageGenerator
from src.tts.manager import TTSManager
from src.video.composer import VideoComposer
from src.consistency.store import ConsistencyStore
from src.consistency.voice_assigner import assign_voices_with_llm
from src.core.library_manager import LibraryManager

logger = logging.getLogger(__name__)


def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Commands ──────────────────────────────────────────────────


async def extract_scenes(args: argparse.Namespace) -> int:
    """Extract scenes from chapter with rich character/location data."""
    logger.info("Extracting scenes from: %s", args.chapter)

    # Require novel title for consistency store
    if not args.novel:
        logger.error("--novel argument is required to specify the novel for consistency data")
        return 1

    manager = LibraryManager()
    consistency_dir = manager.get_consistency_dir(args.novel)
    if not consistency_dir:
        logger.error("Novel '%s' not found. Please upload it first.", args.novel)
        return 1

    chapter_data = load_json(args.chapter)
    validate_chapter(chapter_data)

    if "id" in chapter_data and "chapter_number" not in chapter_data:
        chapter_data["chapter_number"] = chapter_data["id"]
    if "paragraphs" in chapter_data and "content" not in chapter_data:
        chapter_data["content"] = chapter_data["paragraphs"]

    # Handle chapter_number that may be int or string like "ch129"
    raw_chapter_num = chapter_data.get('chapter_number', chapter_data.get('id', '001'))
    if isinstance(raw_chapter_num, str):
        # Extract numeric part if it's like "ch129"
        import re
        match = re.search(r'\d+', raw_chapter_num)
        if match:
            chapter_num = int(match.group())
        else:
            chapter_num = 1
    else:
        chapter_num = int(raw_chapter_num)
    
    chapter_id = f"ch{chapter_num:04d}"
    max_scenes = getattr(args, "max_scenes", 8)

    extractor = SceneExtractor(consistency_dir=consistency_dir)
    
    # Content could be a string (old) or list of strings (new chunk format)
    chapter_text = chapter_data.get("content", chapter_data.get("paragraphs", ""))

    # Step 1: Extract scenes with rich character/location profiles
    response = extractor.extract_scenes(
        chapter_text,
        max_scenes=max_scenes,
        chapter_id=chapter_id,
    )
    scenes = response.get("scenes", [])

    if not scenes:
        logger.error("No scenes extracted")
        return 1

    # Step 2: Voice assignment (LLM-driven)
    logger.info("Assigning voices to characters...")
    store = extractor.store
    assign_voices_with_llm(store)

    # Step 3: Enrich scene prompts with character/location descriptors
    logger.info("Enriching scene visual descriptions...")
    scenes = extractor.enrich_scene_prompts(scenes, chapter_id=chapter_id)

    output_path = args.output or Path(
        f"data/{args.novel}/scenes/ch{chapter_num:04d}_scenes.json"
    )
    save_json(scenes, output_path)

    # Save enriched data summary
    db_summary = store.export_for_llm()
    db_path = output_path.parent / f"ch{chapter_num:04d}_character_db.json"
    save_json(db_summary, db_path)

    logger.info("Extracted %s scenes -> %s", len(scenes), output_path)
    logger.info("Character DB -> %s", db_path)
    logger.info(
        "Characters: %s",
        ", ".join(
            f"{n} ({d.get('voice_id', '?')})"
            for n, d in store.list_characters().items()
        ),
    )
    return 0


async def generate_images(args: argparse.Namespace) -> int:
    """Generate images for scenes with character seed pinning."""
    logger.info("Generating images from: %s", args.scenes)

    # Require novel title for consistency store
    if not args.novel:
        logger.error("--novel argument is required to specify the novel for consistency data")
        return 1

    manager = LibraryManager()
    consistency_dir = manager.get_consistency_dir(args.novel)
    if not consistency_dir:
        logger.error("Novel '%s' not found. Please upload it first.", args.novel)
        return 1

    scenes = load_json(args.scenes)
    validate_scenes(scenes)

    output_dir = args.output or Path(f"data/{args.novel}/images")
    ensure_output_dir(output_dir)

    generator = ImageGenerator()
    store = ConsistencyStore(consistency_dir)

    for i, scene in enumerate(scenes):
        output_path = output_dir / f"scene_{i:03d}.png"

        if output_path.exists() and not args.force:
            logger.info("Skipping scene %s (already exists)", i)
            continue

        logger.info("Generating image for scene %s/%s...", i + 1, len(scenes))
        success = generator.generate_for_scene(scene, str(output_path), store=store)

        if not success:
            logger.error("Failed to generate image for scene %s", i)
            if not args.continue_on_error:
                return 1

    logger.info("Generated images in: %s", output_dir)
    return 0


async def generate_audio(args: argparse.Namespace) -> int:
    """Generate audio for scenes with per-character voices and dialogue pacing."""
    logger.info("Generating audio from: %s", args.scenes)

    scenes = load_json(args.scenes)
    validate_scenes(scenes)

    output_dir = args.output or Path(f"data/{args.novel}/audio")
    ensure_output_dir(output_dir)

    tts_manager = TTSManager()

    results = await tts_manager.generate_chapter_audio(
        scenes,
        output_dir,
        default_voice="narrator",
    )

    failed = sum(1 for r in results if r is None)
    if failed > 0:
        logger.warning("%s/%s audio files failed to generate", failed, len(scenes))
        if not args.continue_on_error:
            return 1

    logger.info("Generated audio in: %s", output_dir)
    return 0


async def build_video(args: argparse.Namespace) -> int:
    """Build final video from scenes, images, and audio."""
    logger.info("Building video...")

    scenes = load_json(args.scenes)
    validate_scenes(scenes)

    images_dir = args.images or Path(f"data/{args.novel}/images")
    audio_dir = args.audio or Path(f"data/{args.novel}/audio")
    output_path = args.output or Path(f"data/{args.novel}/videos/output.mp4")

    for i in range(len(scenes)):
        image_path = images_dir / f"scene_{i:03d}.png"
        audio_path = audio_dir / f"scene_{i:03d}.wav"

        if not image_path.exists():
            logger.error("Missing image: %s", image_path)
            return 1
        if not audio_path.exists():
            logger.error("Missing audio: %s", audio_path)
            return 1

    composer = VideoComposer()
    success = composer.create_video(
        scenes,
        str(images_dir),
        str(audio_dir),
        str(output_path),
    )

    if success:
        logger.info("Video created: %s", output_path)
        return 0

    logger.error("Video creation failed")
    return 1


async def test_image(args: argparse.Namespace) -> int:
    """Generate a single test image with a custom prompt."""
    logger.info("Generating test image for prompt: '%s'", args.prompt)
    
    output_path = args.output or Path("test_image.png")
    
    # Create a dummy scene object
    scene = {
        "visual_description": args.prompt,
        "time_of_day": "day", 
        "lighting": "natural",
        "mood": "neutral"
    }

    generator = ImageGenerator()
    success = generator.generate_for_scene(scene, str(output_path))
    
    if success:
        logger.info("SUCCESS: Image generated at %s", output_path.absolute())
        return 0
    else:
        logger.error("FAILURE: Image generation failed")
        return 1

async def reingest_epub(args: argparse.Namespace) -> int:
    """Reingest an EPUB to generate fresh chunked chapter JSONs, deleting the old ones."""
    logger.info("Reingesting EPUB for novel: %s", args.novel)
    
    manager = LibraryManager()
    novel = manager.get_novel(args.novel)
    
    if not novel:
        logger.error("Novel '%s' not found. Please upload it first.", args.novel)
        return 1
        
    source_epub = novel.get("source_epub")
    if not source_epub or not Path(source_epub).exists():
        logger.error("Source EPUB for '%s' not found at %s. Cannot reingest.", args.novel, source_epub)
        return 1
        
    novel_dir = Path(novel["directory"])
    chapters_dir = novel_dir / "chapters"
    
    logger.info("Deleting existing chapters inside %s...", chapters_dir)
    if chapters_dir.exists():
        import shutil
        shutil.rmtree(chapters_dir)
        
    chapters_dir.mkdir(parents=True, exist_ok=True)
    
    # We load library_manager.create_novel_from_epub, but since we already have the folder
    # We just need to rerun the parsing and saving chapter logic without deleting the consistency DB
    logger.info("Parsing EPUB: %s", source_epub)
    from src.core.epub_parser import EpubParser
    parser = EpubParser(source_epub)
    book_data = parser.parse()
    
    chapter_manifest = []
    for i, chapter in enumerate(book_data['chapters']):
        chapter_id = f"ch{str(i+1).zfill(3)}"
        chapter_filename = f"{chapter_id}.json"
        chapter_path = chapters_dir / chapter_filename
        
        # Save Text Content
        with open(chapter_path, 'w', encoding='utf-8') as f:
            json.dump({
                "id": chapter_id,
                "title": chapter['title'],
                "content": chapter['content'],
                "order": i + 1
            }, f, indent=2, ensure_ascii=False)
            
        chapter_manifest.append({
            "id": chapter_id,
            "title": chapter['title'],
            "path": str(chapter_path)
        })
        
    # Update Metadata Chapter Count
    novel["chapter_count"] = len(chapter_manifest)
    with open(novel_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(novel, f, indent=2)

    logger.info("Reingested %d chapters successfully for '%s'.", len(chapter_manifest), args.novel)
    return 0


async def run_full_pipeline(args: argparse.Namespace) -> int:
    """Run the complete enriched pipeline."""
    logger.info("Running enriched pipeline for: %s", args.chapter)

    # Require novel title for consistency store
    if not args.novel:
        logger.error("--novel argument is required to specify the novel for consistency data")
        return 1

    manager = LibraryManager()
    consistency_dir = manager.get_consistency_dir(args.novel)
    if not consistency_dir:
        logger.error("Novel '%s' not found. Please upload it first.", args.novel)
        return 1

    chapter_data = load_json(args.chapter)

    if "id" in chapter_data and "chapter_number" not in chapter_data:
        chapter_data["chapter_number"] = chapter_data["id"]

    raw_chapter_num = chapter_data.get('chapter_number', chapter_data.get('id', '001'))
    if isinstance(raw_chapter_num, str):
        import re
        match = re.search(r'\d+', raw_chapter_num)
        if match:
            chapter_num = int(match.group())
        else:
            chapter_num = 1
    else:
        chapter_num = int(raw_chapter_num)

    work_dir = args.output or Path(f"data/{args.novel}/pipeline_ch{chapter_num:04d}")
    ensure_output_dir(work_dir)

    scenes_path = work_dir / "scenes.json"
    images_dir = work_dir / "images"
    audio_dir = work_dir / "audio"
    video_path = work_dir / f"chapter_{chapter_num:04d}.mp4"

    # Step 1: Extract + enrich + voice assign
    logger.info("=" * 60)
    logger.info("STEP 1: Extracting scenes + enriching character DB + assigning voices")
    logger.info("=" * 60)
    max_scenes = getattr(args, "max_scenes", 8)
    extract_args = argparse.Namespace(
        chapter=args.chapter, output=scenes_path, max_scenes=max_scenes, novel=args.novel,
    )
    if await extract_scenes(extract_args) != 0:
        return 1

    # Step 2: Generate images with seed pinning
    logger.info("=" * 60)
    logger.info("STEP 2: Generating images (with character seed pinning)")
    logger.info("=" * 60)
    image_args = argparse.Namespace(
        scenes=scenes_path,
        output=images_dir,
        force=False,
        continue_on_error=True,
        novel=args.novel,
    )
    if await generate_images(image_args) != 0:
        return 1

    # Step 3: Generate audio with dialogue pacing
    logger.info("=" * 60)
    logger.info("STEP 3: Generating audio (dialogue pacing + silence gaps)")
    logger.info("=" * 60)
    audio_args = argparse.Namespace(
        scenes=scenes_path,
        output=audio_dir,
        concurrent=3,
        continue_on_error=True,
    )
    if await generate_audio(audio_args) != 0:
        return 1

    # Step 4: Compose video
    logger.info("=" * 60)
    logger.info("STEP 4: Building video")
    logger.info("=" * 60)
    video_args = argparse.Namespace(
        scenes=scenes_path,
        images=images_dir,
        audio=audio_dir,
        output=video_path,
    )
    if await build_video(video_args) != 0:
        return 1

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE: %s", video_path)
    logger.info("=" * 60)
    return 0


# ── Argument parsing ─────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Novel Video Generator - Convert text chapters to narrated videos",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract scenes from chapter")
    extract_parser.add_argument("chapter", type=Path, help="Path to chapter JSON file")
    extract_parser.add_argument("-o", "--output", type=Path, help="Output scenes JSON path")
    extract_parser.add_argument("--max-scenes", type=int, default=8, help="Maximum scenes to extract")
    extract_parser.add_argument("-n", "--novel", type=str, required=True, help="Novel title for consistency data")

    images_parser = subparsers.add_parser("images", help="Generate images for scenes")
    images_parser.add_argument("scenes", type=Path, help="Path to scenes JSON file")
    images_parser.add_argument("-o", "--output", type=Path, help="Output directory for images")
    images_parser.add_argument("-f", "--force", action="store_true", help="Regenerate existing images")
    images_parser.add_argument("--continue-on-error", action="store_true", help="Continue if some images fail")
    images_parser.add_argument("-n", "--novel", type=str, required=True, help="Novel title for consistency data")

    audio_parser = subparsers.add_parser("audio", help="Generate audio for scenes")
    audio_parser.add_argument("scenes", type=Path, help="Path to scenes JSON file")
    audio_parser.add_argument("-o", "--output", type=Path, help="Output directory for audio")
    audio_parser.add_argument("-c", "--concurrent", type=int, default=3, help="Max concurrent generations")
    audio_parser.add_argument("--continue-on-error", action="store_true", help="Continue if some audio fails")
    audio_parser.add_argument("-n", "--novel", type=str, required=True, help="Novel title for data storage")

    video_parser = subparsers.add_parser("video", help="Build video from scenes, images, and audio")
    video_parser.add_argument("scenes", type=Path, help="Path to scenes JSON file")
    video_parser.add_argument("--images", type=Path, help="Directory containing images")
    video_parser.add_argument("--audio", type=Path, help="Directory containing audio")
    video_parser.add_argument("-o", "--output", type=Path, help="Output video path")
    video_parser.add_argument("-n", "--novel", type=str, required=True, help="Novel title for data storage")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run full pipeline")
    pipeline_parser.add_argument("chapter", type=Path, help="Path to chapter JSON file")
    pipeline_parser.add_argument("-o", "--output", type=Path, help="Working directory for pipeline")
    pipeline_parser.add_argument("--max-scenes", type=int, default=8, help="Max scenes to extract")
    pipeline_parser.add_argument("-n", "--novel", type=str, required=True, help="Novel title for consistency data")

    test_image_parser = subparsers.add_parser("image-gen", help="Generate single test image")
    test_image_parser.add_argument("prompt", type=str, help="Image prompt description")
    test_image_parser.add_argument("-o", "--output", type=Path, help="Output image path")

    reingest_parser = subparsers.add_parser("reingest-epub", help="Reingest the source EPUB to update chunking")
    reingest_parser.add_argument("-n", "--novel", type=str, required=True, help="Novel title to reingest")

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    commands = {
        "extract": extract_scenes,
        "images": generate_images,
        "image-gen": test_image,
        "audio": generate_audio,
        "video": build_video,
        "pipeline": run_full_pipeline,
        "reingest-epub": reingest_epub,
    }

    try:
        exit_code = asyncio.run(commands[args.command](args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
