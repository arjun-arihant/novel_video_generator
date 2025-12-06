import argparse
import json
import logging
import os
from pathlib import Path
import sys
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.image.generator import ImageGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_scenes(scenes_path: str, output_dir: str):
    scenes_path = Path(scenes_path)
    if not scenes_path.exists():
        logger.error(f"Scenes file not found: {scenes_path}")
        return

    # Load scenes
    with open(scenes_path, 'r', encoding='utf-8') as f:
        scenes = json.load(f)

    # Extract chapter ID from filename (e.g., scenes_1.json -> 1)
    chapter_id = scenes_path.stem.replace("scenes_", "")
    
    logger.info(f"Generating images for {len(scenes)} scenes in chapter {chapter_id}...")

    # Setup output directory
    output_dir = Path(output_dir) / f"chapter_{chapter_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    generator = ImageGenerator()

    for i, scene in enumerate(scenes):
        prompt = scene.get("visual_description")
        if not prompt:
            logger.warning(f"Scene {i} has no visual description. Skipping.")
            continue
            
        output_file = output_dir / f"scene_{i:03d}.png"
        
        if output_file.exists():
            logger.info(f"Image {output_file} already exists. Skipping.")
            continue
            
        try:
            generator.generate_image(prompt, str(output_file))
        except Exception as e:
            logger.error(f"Failed to generate image for scene {i}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate images for extracted scenes")
    parser.add_argument("--scenes", required=True, help="Path to scenes JSON file")
    parser.add_argument("--out", default="data/images", help="Output directory")
    
    args = parser.parse_args()
    
    process_scenes(args.scenes, args.out)

if __name__ == "__main__":
    main()
