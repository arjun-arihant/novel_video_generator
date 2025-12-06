import argparse
import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
import sys
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.parser.gemini_parser import SceneExtractor
from src.image.generator import ImageGenerator
from src.tts.manager import TTSManager
from src.video.composer import VideoComposer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pipeline(chapter_path: str, output_base: str):
    chapter_path = Path(chapter_path)
    if not chapter_path.exists():
        logger.error(f"Chapter file not found: {chapter_path}")
        return

    # Load chapter data
    with open(chapter_path, 'r', encoding='utf-8') as f:
        chapter_data = json.load(f)
    chapter_id = chapter_data.get('id', 'unknown')
    
    # Setup directories
    output_base = Path(output_base)
    scenes_dir = output_base / "scenes"
    images_dir = output_base / "images" / f"chapter_{chapter_id}"
    audio_dir = output_base / "audio" / f"chapter_{chapter_id}"
    video_dir = output_base / "videos"
    
    scenes_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    # 1. Scene Extraction
    scenes_file = scenes_dir / f"scenes_{chapter_id}.json"
    if scenes_file.exists():
        logger.info(f"Scenes file already exists: {scenes_file}")
        with open(scenes_file, 'r', encoding='utf-8') as f:
            scenes = json.load(f)
    else:
        logger.info("Extracting scenes...")
        full_text = "\n\n".join(chapter_data.get('paragraphs', []))
        extractor = SceneExtractor()
        scenes = extractor.extract_scenes(full_text)
        with open(scenes_file, 'w', encoding='utf-8') as f:
            json.dump(scenes, f, indent=2)

    # 2. Image Generation
    logger.info("Generating images...")
    img_generator = ImageGenerator()
    for i, scene in enumerate(scenes):
        img_path = images_dir / f"scene_{i:03d}.png"
        if img_path.exists():
            continue
            
        prompt = scene.get("visual_description")
        if prompt:
            try:
                img_generator.generate_image(prompt, str(img_path))
            except Exception as e:
                logger.error(f"Failed to generate image for scene {i}: {e}")

    # 3. TTS Generation
    logger.info("Generating audio...")
    tts_manager = TTSManager()
    provider = tts_manager.get_provider("edge")
    voice_id = tts_manager.get_voice_id("narrator")
    
    tts_tasks = []
    for i, scene in enumerate(scenes):
        audio_path = audio_dir / f"scene_{i:03d}.mp3"
        if audio_path.exists():
            continue
            
        # Use text_segment from scene, or fallback to visual description if text is missing (unlikely)
        text = scene.get("text_segment", "")
        if not text:
            logger.warning(f"No text for scene {i}")
            continue
            
        tts_tasks.append(provider.generate_audio(text, str(audio_path), voice_id))
        
    if tts_tasks:
        await asyncio.gather(*tts_tasks)

    # 4. Video Assembly
    logger.info("Assembling video...")
    composer = VideoComposer()
    output_video = video_dir / f"video_{chapter_id}.mp4"
    composer.create_video(scenes, str(audio_dir), str(images_dir), str(output_video))
    
    logger.info(f"Pipeline complete! Video saved to {output_video}")

def main():
    parser = argparse.ArgumentParser(description="Run full video generation pipeline")
    parser.add_argument("--chapter", required=True, help="Path to chapter JSON file")
    parser.add_argument("--out", default="data", help="Base output directory")
    
    args = parser.parse_args()
    
    asyncio.run(run_pipeline(args.chapter, args.out))

if __name__ == "__main__":
    main()
