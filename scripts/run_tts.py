import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import sys
# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.tts.manager import TTSManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_chapter(chapter_path: str, output_dir: str, provider_name: str):
    """
    Process a single chapter JSON file and generate audio for each paragraph.
    """
    chapter_path = Path(chapter_path)
    if not chapter_path.exists():
        logger.error(f"Chapter file not found: {chapter_path}")
        return

    # Load chapter data
    with open(chapter_path, 'r', encoding='utf-8') as f:
        chapter_data = json.load(f)

    chapter_id = chapter_data.get('id', 'unknown')
    paragraphs = chapter_data.get('paragraphs', [])
    
    logger.info(f"Processing chapter {chapter_id} with {len(paragraphs)} paragraphs")

    # Setup output directory
    output_dir = Path(output_dir) / f"chapter_{chapter_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize TTS Manager
    tts_manager = TTSManager()
    provider = tts_manager.get_provider(provider_name)
    
    # Get voice (using default narrator for now)
    voice_id = tts_manager.get_voice_id("narrator", provider_name)
    logger.info(f"Using voice: {voice_id}")

    # Generate audio for each paragraph
    tasks = []
    for i, text in enumerate(paragraphs):
        if not text.strip():
            continue
            
        output_file = output_dir / f"p{i:04d}.mp3"
        logger.info(f"Generating audio for paragraph {i}...")
        
        # Create task for async execution
        tasks.append(provider.generate_audio(text, str(output_file), voice_id))

    # Run all tasks
    # Note: edge-tts might have concurrency limits, but let's try gathering
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check results
    success_count = 0
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"Failed to generate audio: {res}")
        else:
            success_count += 1
            
    logger.info(f"Completed. Generated {success_count}/{len(tasks)} audio files in {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Generate TTS audio for a chapter")
    parser.add_argument("--chapter", required=True, help="Path to chapter JSON file")
    parser.add_argument("--out", default="data/audio", help="Output directory")
    parser.add_argument("--provider", default="gemini", help="TTS provider to use (gemini)")
    
    args = parser.parse_args()
    
    asyncio.run(process_chapter(args.chapter, args.out, args.provider))

if __name__ == "__main__":
    main()
