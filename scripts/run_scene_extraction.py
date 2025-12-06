import argparse
import json
import logging
import os
from pathlib import Path
import sys
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.parser.gemini_parser import SceneExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_chapter(chapter_path: str, output_dir: str):
    chapter_path = Path(chapter_path)
    if not chapter_path.exists():
        logger.error(f"Chapter file not found: {chapter_path}")
        return

    # Load chapter data
    with open(chapter_path, 'r', encoding='utf-8') as f:
        chapter_data = json.load(f)

    chapter_id = chapter_data.get('id', 'unknown')
    # Combine paragraphs into full text
    full_text = "\n\n".join(chapter_data.get('paragraphs', []))
    
    logger.info(f"Extracting scenes for chapter {chapter_id}...")

    extractor = SceneExtractor()
    try:
        scenes = extractor.extract_scenes(full_text)
        
        # Save scenes
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"scenes_{chapter_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(scenes, f, indent=2)
            
        logger.info(f"Successfully extracted {len(scenes)} scenes to {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to extract scenes: {e}")

def main():
    parser = argparse.ArgumentParser(description="Extract scenes from a chapter using Gemini")
    parser.add_argument("--chapter", required=True, help="Path to chapter JSON file")
    parser.add_argument("--out", default="data/scenes", help="Output directory")
    
    args = parser.parse_args()
    
    process_chapter(args.chapter, args.out)

if __name__ == "__main__":
    main()
