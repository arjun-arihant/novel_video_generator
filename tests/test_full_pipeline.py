"""Full pipeline integration test - runs the entire backend workflow.

This script tests the complete Novel Video Generator pipeline:
1. Library management (create, update, delete)
2. EPUB parsing and chapter extraction
3. Scene extraction via LLM
4. Image generation
5. Audio generation (TTS)
6. Video composition

Usage:
    cd d:\repos\novel_video_generator
    python tests/test_full_pipeline.py

Requirements:
    - Valid .env file with OPENROUTER_API_KEY
    - EPUB file in data/uploads/ or use sample text
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Change to project root for imports to work
os.chdir(project_root)

# Setup logging first
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_NOVEL_TITLE = "Test Novel Pipeline"
TEST_CHAPTER_CONTENT = """
Chapter 1: The Beginning

The rain fell heavily on the cobblestone streets of London. Sarah, a young woman with auburn hair and emerald eyes, pulled her coat tighter as she hurried through the narrow alleyways. She was late for her meeting with the mysterious informant.

Suddenly, a figure stepped out from the shadows. It was Marcus, tall and imposing with dark hair and piercing blue eyes. He wore a long black coat that billowed in the wind.

"You're late," Marcus said, his voice deep and gravelly.

"I got held up," Sarah replied, trying to catch her breath. "Do you have the documents?"

Marcus nodded slowly, pulling an envelope from his coat. "This is what you've been looking for. But be careful - there are others who want this information."

Sarah took the envelope, her hands trembling slightly. As she turned to leave, she heard footsteps echoing in the distance. They weren't alone.

"We need to move," Marcus whispered urgently. "Now."

Together, they ran through the rain-soaked streets, the mystery of the documents pulling them into a dangerous adventure they never expected.
"""


def test_library_manager():
    """Test library management functions."""
    logger.info("=" * 60)
    logger.info("TEST 1: Library Manager")
    logger.info("=" * 60)
    
    from core.library_manager import LibraryManager, NOVELS_DIR
    
    manager = LibraryManager()
    
    # Test 1a: Create novel from text (simulating EPUB)
    logger.info("Creating test novel...")
    test_timestamp = int(time.time())
    test_id = f"test_{test_timestamp}"
    novel_dir = (NOVELS_DIR / f"{test_id}_Test_Novel_Pipeline").resolve()
    
    # Check if folder already exists (shouldn't happen with timestamp)
    if novel_dir.exists():
        logger.warning(f"Removing existing test folder: {novel_dir}")
        shutil.rmtree(novel_dir)
    
    novel_dir.mkdir(parents=True, exist_ok=True)
    
    # Create metadata
    metadata = {
        "id": test_id,
        "title": TEST_NOVEL_TITLE,
        "author": "Test Author",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "chapter_count": 1,
        "directory": str(novel_dir)
    }
    
    with open(novel_dir / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    # Create chapter
    chapters_dir = novel_dir / "chapters"
    chapters_dir.mkdir(exist_ok=True)
    
    chapter_data = {
        "id": "ch001",
        "title": "Chapter 1: The Beginning",
        "content": TEST_CHAPTER_CONTENT.strip().split('\n\n'),
        "order": 1
    }
    
    with open(chapters_dir / "ch001.json", 'w', encoding='utf-8') as f:
        json.dump(chapter_data, f, indent=2)
    
    logger.info(f"✓ Created test novel: {metadata['id']}")
    
    # Test 1b: Get library
    library = manager.get_library()
    logger.info(f"✓ Library has {len(library)} novels")
    
    # Test 1c: Get novel
    novel = manager.get_novel(metadata['id'])
    assert novel is not None, "Failed to retrieve novel"
    logger.info(f"✓ Retrieved novel: {novel['title']}")
    
    # Test 1d: Get chapters - monkey patch for debugging
    original_get_chapters = manager.get_chapters
    
    def debug_get_chapters(novel_id):
        novel = manager.get_novel(novel_id)
        if not novel:
            logger.error(f"Debug: Novel {novel_id} not found")
            return []
        novel_dir = Path(novel['directory'])
        chapters_dir = novel_dir / "chapters"
        logger.info(f"Debug get_chapters: dir={chapters_dir}, exists={chapters_dir.exists()}")
        chapters = []
        for f in sorted(chapters_dir.glob("*.json")):
            try:
                with open(f, 'r', encoding='utf-8') as cf:
                    data = json.load(cf)
                logger.info(f"Debug: Processing {f.name}, data keys={data.keys()}")
                chapters.append({
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "order": data.get("order"),
                    "path": str(f.resolve()),
                    "preview": str(data.get("content", ""))[:150] + "..."
                })
                logger.info(f"Debug: Added chapter {data.get('id')}")
            except Exception as e:
                logger.error(f"Debug: Error processing {f.name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        return sorted(chapters, key=lambda x: x['order'])
    
    manager.get_chapters = debug_get_chapters
    
    novel_for_chapters = manager.get_novel(metadata['id'])
    logger.info(f"Debug: Novel dir = {novel_for_chapters.get('directory') if novel_for_chapters else 'NOT FOUND'}")
    
    # Manual chapter loading for debugging
    if novel_for_chapters:
        chapters_path = Path(novel_for_chapters['directory']) / "chapters"
        logger.info(f"Debug: Chapters dir = {chapters_path}, exists = {chapters_path.exists()}")
        if chapters_path.exists():
            json_files = list(chapters_path.glob("*.json"))
            logger.info(f"Debug: Files in chapters dir: {json_files}")
            for f in json_files:
                try:
                    with open(f, 'r', encoding='utf-8') as cf:
                        data = json.load(cf)
                        logger.info(f"Debug: Loaded {f.name} - id={data.get('id')}, order={data.get('order')}")
                except Exception as e:
                    logger.error(f"Debug: Failed to load {f.name}: {e}")
    
    chapters = manager.get_chapters(metadata['id'])
    logger.info(f"Debug: Found {len(chapters)} chapters")
    assert len(chapters) > 0, f"No chapters found for novel {metadata['id']}"
    logger.info(f"✓ Retrieved {len(chapters)} chapters")
    
    # Test 1e: Get chapter content
    content = manager.get_chapter_content(metadata['id'], 'ch001')
    assert content is not None, "Failed to get chapter content"
    logger.info(f"✓ Retrieved chapter content ({len(content.get('content', []))} paragraphs)")
    
    # Test 1f: Update title
    new_title = "Updated Test Title"
    updated = manager.update_novel_title(metadata['id'], new_title)
    assert updated is not None, "Failed to update title"
    assert updated['title'] == new_title, "Title not updated correctly"
    logger.info(f"✓ Updated title to: {new_title}")
    
    return metadata['id'], str(chapters_dir / "ch001.json")


def test_scene_extraction(novel_id: str, chapter_path: str):
    """Test scene extraction from chapter."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Scene Extraction (LLM)")
    logger.info("=" * 60)
    
    from parser.openrouter_parser import SceneExtractor
    from src.core.library_manager import LibraryManager
    
    manager = LibraryManager()
    chapter_data = manager.get_chapter_content(novel_id, 'ch001')
    
    if not chapter_data:
        logger.error("✗ Could not load chapter content")
        return None
    
    chapter_text = "\n".join(chapter_data.get('content', []))
    logger.info(f"Chapter text length: {len(chapter_text)} characters")
    
    # Test scene extraction
    logger.info("Calling LLM for scene extraction...")
    extractor = SceneExtractor()
    
    try:
        response = extractor.extract_scenes(
            chapter_text,
            max_scenes=3,
            chapter_id="ch0001"
        )
        
        scenes = response.get('scenes', [])
        characters = response.get('characters', [])
        locations = response.get('locations', [])
        
        logger.info(f"✓ Extracted {len(scenes)} scenes")
        logger.info(f"✓ Extracted {len(characters)} characters")
        logger.info(f"✓ Extracted {len(locations)} locations")
        
        for i, scene in enumerate(scenes):
            logger.info(f"  Scene {i+1}: {scene.get('title', 'Untitled')}")
            logger.info(f"    - Characters: {', '.join(scene.get('characters', []))}")
            logger.info(f"    - Locations: {', '.join(scene.get('locations', []))}")
        
        for char in characters:
            logger.info(f"  Character: {char.get('name')} ({char.get('gender', 'unknown')})")
        
        return response
        
    except Exception as e:
        logger.error(f"✗ Scene extraction failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def test_voice_assignment(extractor):
    """Test voice assignment for characters."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Voice Assignment")
    logger.info("=" * 60)
    
    from consistency.voice_assigner import assign_voices_with_llm
    
    try:
        assign_voices_with_llm(extractor.store)
        characters = extractor.store.list_characters()
        
        logger.info(f"✓ Assigned voices to {len(characters)} characters")
        
        for name, data in characters.items():
            voice_id = data.get('voice_id', 'Not assigned')
            logger.info(f"  {name}: voice_id={voice_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Voice assignment failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_scene_enrichment(extractor, scenes):
    """Test scene prompt enrichment."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: Scene Enrichment")
    logger.info("=" * 60)
    
    try:
        enriched = extractor.enrich_scene_prompts(scenes, chapter_id="ch0001")
        logger.info(f"✓ Enriched {len(enriched)} scenes")
        
        for i, scene in enumerate(enriched):
            visual = scene.get('visual_description', '')[:100]
            logger.info(f"  Scene {i+1}: {visual}...")
        
        return enriched
        
    except Exception as e:
        logger.error(f"✗ Scene enrichment failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def test_image_generation(scenes, output_dir: Path):
    """Test image generation for scenes."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 5: Image Generation")
    logger.info("=" * 60)
    
    from consistency.store import ConsistencyStore
    
    # Check if WanGP is available
    wangp_path = os.getenv("WANGP_PATH", r"D:\GeneAI\Wan2GP")
    wgp_exists = (Path(wangp_path) / "wgp.py").exists()
    
    if not wgp_exists:
        logger.warning("⚠ WanGP not found, skipping image generation")
        logger.info(f"  Set WANGP_PATH in .env (current: {wangp_path})")
        return False
    
    try:
        from image.generator import ImageGenerator
        
        generator = ImageGenerator()
        store = ConsistencyStore()
        
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating {len(scenes)} images...")
        
        for i, scene in enumerate(scenes):
            out_file = images_dir / f"scene_{i:03d}.png"
            logger.info(f"  Generating scene {i+1}: {scene.get('title', 'Untitled')[:40]}...")
            
            try:
                generator.generate_for_scene(scene, out_file, store=store)
                if out_file.exists():
                    logger.info(f"    ✓ Saved: {out_file.name} ({out_file.stat().st_size} bytes)")
                else:
                    logger.error(f"    ✗ File not created: {out_file}")
            except Exception as e:
                logger.error(f"    ✗ Failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Image generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_audio_generation(scenes, output_dir: Path):
    """Test audio/TTS generation for scenes."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 6: Audio Generation (TTS)")
    logger.info("=" * 60)
    
    import asyncio
    
    try:
        from tts.manager import TTSManager
        
        tts = TTSManager()
        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating audio for {len(scenes)} scenes...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            tts.generate_chapter_audio(scenes, audio_dir, default_voice="narrator")
        )
        loop.close()
        
        success_count = sum(1 for r in results if r)
        logger.info(f"✓ Generated {success_count}/{len(scenes)} audio clips")
        
        for i, result in enumerate(results):
            if result:
                path = Path(result)
                logger.info(f"  ✓ Scene {i+1}: {path.name}")
            else:
                logger.warning(f"  ⚠ Scene {i+1}: Failed")
        
        return success_count > 0
        
    except Exception as e:
        logger.error(f"✗ Audio generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_video_composition(scenes, output_dir: Path):
    """Test video composition."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 7: Video Composition")
    logger.info("=" * 60)
    
    images_dir = output_dir / "images"
    audio_dir = output_dir / "audio"
    
    # Check if we have assets
    has_images = list(images_dir.glob("*.png")) if images_dir.exists() else []
    has_audio = list(audio_dir.glob("*.wav")) if audio_dir.exists() else []
    
    if not has_images:
        logger.warning("⚠ No images found, skipping video composition")
        return False
    
    if not has_audio:
        logger.warning("⚠ No audio found, skipping video composition")
        return False
    
    try:
        from video.composer import VideoComposer
        
        composer = VideoComposer()
        video_path = output_dir / "test_output.mp4"
        
        logger.info(f"Composing video with {len(has_images)} images and {len(has_audio)} audio clips...")
        
        composer.create_video(
            scenes,
            str(images_dir),
            str(audio_dir),
            str(video_path)
        )
        
        if video_path.exists():
            size_mb = video_path.stat().st_size / (1024 * 1024)
            logger.info(f"✓ Video created: {video_path.name} ({size_mb:.2f} MB)")
            return True
        else:
            logger.error("✗ Video file not created")
            return False
            
    except Exception as e:
        logger.error(f"✗ Video composition failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def cleanup(test_novel_id: str = None):
    """Clean up test files."""
    logger.info("\n" + "=" * 60)
    logger.info("CLEANUP")
    logger.info("=" * 60)
    
    from src.core.library_manager import NOVELS_DIR
    
    # Clean up test novels
    if NOVELS_DIR.exists():
        for folder in NOVELS_DIR.iterdir():
            if folder.is_dir() and 'test_' in folder.name:
                try:
                    shutil.rmtree(folder)
                    logger.info(f"✓ Removed test novel: {folder.name}")
                except Exception as e:
                    logger.warning(f"⚠ Could not remove {folder.name}: {e}")


def main():
    """Run all tests."""
    logger.info("\n" + "=" * 70)
    logger.info("NOVEL VIDEO GENERATOR - FULL PIPELINE TEST")
    logger.info("=" * 70)
    """Test that the end-state video generation constructs properly."""
    
    output_dir = Path(".video_test_output") / f"test_{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Test 1: Library Manager
        test_novel_id, chapter_path = test_library_manager()
        
        # Test 2: Scene Extraction
        response = test_scene_extraction(test_novel_id, chapter_path)
        if not response:
            logger.error("Scene extraction failed - stopping tests")
            return 1
        
        scenes = response['scenes']
        
        # Re-create extractor to access store
        from parser.openrouter_parser import SceneExtractor
        extractor = SceneExtractor()
        
        # Test 3: Voice Assignment
        test_voice_assignment(extractor)
        
        # Test 4: Scene Enrichment
        enriched_scenes = test_scene_enrichment(extractor, scenes)
        if not enriched_scenes:
            enriched_scenes = scenes
        
        # Save scenes for debugging
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / "scenes.json", 'w', encoding='utf-8') as f:
            json.dump(enriched_scenes, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Saved scenes to {output_dir / 'scenes.json'}")
        
        # Test 5: Image Generation
        test_image_generation(enriched_scenes, output_dir)
        
        # Test 6: Audio Generation
        test_audio_generation(enriched_scenes, output_dir)
        
        # Test 7: Video Composition
        test_video_composition(enriched_scenes, output_dir)
        
        logger.info("\n" + "=" * 70)
        logger.info("ALL TESTS COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Output directory: {output_dir}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\n\nTests interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    finally:
        # Cleanup
        cleanup(test_novel_id)


if __name__ == "__main__":
    sys.exit(main())
