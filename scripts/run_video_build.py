import argparse
import json
import logging
import os
from pathlib import Path
import sys
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.video.composer import VideoComposer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_video(scenes_path: str, audio_dir: str, image_dir: str, output_dir: str):
    scenes_path = Path(scenes_path)
    if not scenes_path.exists():
        logger.error(f"Scenes file not found: {scenes_path}")
        return

    # Load scenes
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes = json.load(f)

    chapter_id = scenes_path.stem.replace("scenes_", "")
    
    # Setup output
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"video_{chapter_id}.mp4"

    composer = VideoComposer()
    
    # Note: We expect audio files to be named scene_000.mp3, etc.
    # The pipeline script will need to ensure this.
    
    composer.create_video(scenes, audio_dir, image_dir, str(output_path))

def main():
    parser = argparse.ArgumentParser(description="Assemble video from scenes, images, and audio")
    parser.add_argument("--scenes", required=True, help="Path to scenes JSON file")
    parser.add_argument("--audio", required=True, help="Directory containing audio files")
    parser.add_argument("--images", required=True, help="Directory containing image files")
    parser.add_argument("--out", default="outputs", help="Output directory")
    
    args = parser.parse_args()
    
    process_video(args.scenes, args.audio, args.images, args.out)

if __name__ == "__main__":
    main()
