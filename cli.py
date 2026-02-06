"""Unified CLI for novel video generator pipeline."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from src.common import setup_logging, validate_chapter, validate_scenes, ensure_output_dir
from src.parser.openrouter_parser import SceneExtractor
from src.image.generator import ImageGenerator
from src.tts.manager import TTSManager
from src.video.composer import VideoComposer
from src.consistency.store import ConsistencyStore
from src.consistency.voice_assigner import assign_voice

logger = logging.getLogger(__name__)


def load_json(file_path: Path):
    """Load and parse JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, file_path: Path) -> None:
    """Save data to JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def extract_scenes(args: argparse.Namespace) -> int:
    """Extract scenes from chapter."""
    logger.info("Extracting scenes from: %s", args.chapter)

    chapter_data = load_json(args.chapter)
    validate_chapter(chapter_data)

    if "id" in chapter_data and "chapter_number" not in chapter_data:
        chapter_data["chapter_number"] = chapter_data["id"]
    if "paragraphs" in chapter_data and "content" not in chapter_data:
        chapter_data["content"] = chapter_data["paragraphs"]

    extractor = SceneExtractor()
    chapter_text = "\n".join(chapter_data["content"])

    response = extractor.extract_scenes(chapter_text)
    scenes = response.get("scenes", [])

    if not scenes:
        logger.error("No scenes extracted")
        return 1

    output_path = args.output or Path(
        f"data/scenes/ch{chapter_data['chapter_number']:04d}_scenes.json"
    )
    save_json(scenes, output_path)

    logger.info("Extracted %s scenes to: %s", len(scenes), output_path)
    return 0


async def generate_images(args: argparse.Namespace) -> int:
    """Generate images for scenes."""
    logger.info("Generating images from: %s", args.scenes)

    scenes = load_json(args.scenes)
    validate_scenes(scenes)

    output_dir = args.output or Path("data/images")
    ensure_output_dir(output_dir)

    generator = ImageGenerator()

    for i, scene in enumerate(scenes):
        output_path = output_dir / f"scene_{i:03d}.png"

        if output_path.exists() and not args.force:
            logger.info("Skipping scene %s (already exists)", i)
            continue

        logger.info("Generating image for scene %s/%s...", i, len(scenes))
        prompt = scene["visual_description"]

        success = generator.generate(prompt, str(output_path))

        if not success:
            logger.error("Failed to generate image for scene %s", i)
            if not args.continue_on_error:
                return 1

    logger.info("Generated images in: %s", output_dir)
    return 0


async def generate_audio(args: argparse.Namespace) -> int:
    """Generate audio for scenes."""
    logger.info("Generating audio from: %s", args.scenes)

    scenes = load_json(args.scenes)
    validate_scenes(scenes)

    output_dir = args.output or Path("data/audio")
    ensure_output_dir(output_dir)

    tts_manager = TTSManager()
    store = ConsistencyStore()
    used = []
    characters = assign_voice(store.list_characters(), used)
    for name, data in characters.items():
        tts_manager.register_character_voice(name, data.get("voice_preset", ""))

    results = await tts_manager.generate_batch_audio(
        scenes,
        output_dir,
        max_concurrent=args.concurrent,
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
        audio_path = audio_dir / f"scene_{i:03d}.mp3"

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


async def run_full_pipeline(args: argparse.Namespace) -> int:
    """Run the complete pipeline."""
    logger.info("Running full pipeline for: %s", args.chapter)

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

    logger.info("=" * 60)
    logger.info("STEP 1: Extracting scenes")
    logger.info("=" * 60)
    extract_args = argparse.Namespace(chapter=args.chapter, output=scenes_path)
    if await extract_scenes(extract_args) != 0:
        return 1

    logger.info("=" * 60)
    logger.info("STEP 2: Generating images")
    logger.info("=" * 60)
    image_args = argparse.Namespace(
        scenes=scenes_path,
        output=images_dir,
        force=False,
        continue_on_error=True,
    )
    if await generate_images(image_args) != 0:
        return 1

    logger.info("=" * 60)
    logger.info("STEP 3: Generating audio")
    logger.info("=" * 60)
    audio_args = argparse.Namespace(
        scenes=scenes_path,
        output=audio_dir,
        concurrent=3,
        continue_on_error=True,
    )
    if await generate_audio(audio_args) != 0:
        return 1

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


def main() -> None:
    """Main CLI entry point."""
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

    args = parser.parse_args()

    setup_logging(level=args.log_level)

    commands = {
        "extract": extract_scenes,
        "images": generate_images,
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
