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

    chapter_data = load_json(args.chapter)
    validate_chapter(chapter_data)

    if "id" in chapter_data and "chapter_number" not in chapter_data:
        chapter_data["chapter_number"] = chapter_data["id"]
    if "paragraphs" in chapter_data and "content" not in chapter_data:
        chapter_data["content"] = chapter_data["paragraphs"]

    chapter_id = f"ch{chapter_data['chapter_number']:04d}"
    max_scenes = getattr(args, "max_scenes", 8)

    extractor = SceneExtractor()
    chapter_text = "\n".join(chapter_data["content"])

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
        f"data/scenes/ch{chapter_data['chapter_number']:04d}_scenes.json"
    )
    save_json(scenes, output_path)

    # Save enriched data summary
    db_summary = store.export_for_llm()
    db_path = output_path.parent / f"ch{chapter_data['chapter_number']:04d}_character_db.json"
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

    scenes = load_json(args.scenes)
    validate_scenes(scenes)

    output_dir = args.output or Path("data/images")
    ensure_output_dir(output_dir)

    generator = ImageGenerator()
    store = ConsistencyStore()

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

    output_dir = args.output or Path("data/audio")
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

    images_dir = args.images or Path("data/images")
    audio_dir = args.audio or Path("data/audio")
    output_path = args.output or Path("data/videos/output.mp4")

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


async def run_full_pipeline(args: argparse.Namespace) -> int:
    """Run the complete enriched pipeline."""
    logger.info("Running enriched pipeline for: %s", args.chapter)

    chapter_data = load_json(args.chapter)

    if "id" in chapter_data and "chapter_number" not in chapter_data:
        chapter_data["chapter_number"] = chapter_data["id"]

    chapter_num = chapter_data["chapter_number"]

    work_dir = args.output or Path(f"data/pipeline_ch{chapter_num:04d}")
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
        chapter=args.chapter, output=scenes_path, max_scenes=max_scenes,
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

    images_parser = subparsers.add_parser("images", help="Generate images for scenes")
    images_parser.add_argument("scenes", type=Path, help="Path to scenes JSON file")
    images_parser.add_argument("-o", "--output", type=Path, help="Output directory for images")
    images_parser.add_argument("-f", "--force", action="store_true", help="Regenerate existing images")
    images_parser.add_argument("--continue-on-error", action="store_true", help="Continue if some images fail")

    audio_parser = subparsers.add_parser("audio", help="Generate audio for scenes")
    audio_parser.add_argument("scenes", type=Path, help="Path to scenes JSON file")
    audio_parser.add_argument("-o", "--output", type=Path, help="Output directory for audio")
    audio_parser.add_argument("-c", "--concurrent", type=int, default=3, help="Max concurrent generations")
    audio_parser.add_argument("--continue-on-error", action="store_true", help="Continue if some audio fails")

    video_parser = subparsers.add_parser("video", help="Build video from scenes, images, and audio")
    video_parser.add_argument("scenes", type=Path, help="Path to scenes JSON file")
    video_parser.add_argument("--images", type=Path, help="Directory containing images")
    video_parser.add_argument("--audio", type=Path, help="Directory containing audio")
    video_parser.add_argument("-o", "--output", type=Path, help="Output video path")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run full pipeline")
    pipeline_parser.add_argument("chapter", type=Path, help="Path to chapter JSON file")
    pipeline_parser.add_argument("-o", "--output", type=Path, help="Working directory for pipeline")
    pipeline_parser.add_argument("--max-scenes", type=int, default=8, help="Max scenes to extract")

    test_image_parser = subparsers.add_parser("image-gen", help="Generate single test image")
    test_image_parser.add_argument("prompt", type=str, help="Image prompt description")
    test_image_parser.add_argument("-o", "--output", type=Path, help="Output image path")

    args = parser.parse_args()
    setup_logging(level=args.log_level)

    commands = {
        "extract": extract_scenes,
        "images": generate_images,
        "image-gen": test_image,
        "audio": generate_audio,
        "video": build_video,
        "pipeline": run_full_pipeline,
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
