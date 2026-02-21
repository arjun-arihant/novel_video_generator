"""Library Manager for Novel Video Generator.

Manages the 'Novel Ecosystem' - a structured file system for novels.
Each novel has its own directory directly under data/ with all associated files.

Directory Structure:
data/
  {novel_title}/
    metadata.json
    source/
      original.epub
    chapters/
      ch001.json
      ch002.json
    consistency/
      characters.json
      locations.json
    processing/
      ch001/
        extraction/
        images/
        audio/
        voice_samples/
        video/
        logs/
    exports/
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from src.core.epub_parser import EpubParser

# Setup
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


class LibraryManager:
    """Manages the novel library with title-based identification."""

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convert a name to a safe folder/filename."""
        return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')

    def _get_novel_dir(self, title: str) -> Path:
        """Get the directory path for a novel by its title."""
        safe_title = self._safe_filename(title)
        return DATA_DIR / safe_title

    def get_library(self) -> List[Dict]:
        """Scans the library and returns a list of novels."""
        novels = []
        
        for folder in DATA_DIR.iterdir():
            # Skip non-directories and special folders
            if not folder.is_dir():
                continue
            if folder.name in ('uploads', 'consistency'):
                continue
            
            meta_path = folder / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        novels.append(json.load(f))
                except Exception as e:
                    logger.error(f"Failed to load metadata for {folder}: {e}")
        
        # Sort by recently modified/created
        novels.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return novels

    def create_novel_from_epub(self, epub_path: str) -> Dict:
        """
        Ingests an EPUB, creates the novel directory structure, and extracts chapters.
        Returns the novel metadata.
        
        Args:
            epub_path: Path to the EPUB file to ingest
            
        Returns:
            Dictionary containing novel metadata
            
        Raises:
            ValueError: If a novel with the same title already exists
        """
        parser = EpubParser(epub_path)
        book_data = parser.parse()
        
        safe_title = self._safe_filename(book_data['title'])
        novel_dir = DATA_DIR / safe_title
        
        # Check for existing novel with same title
        if novel_dir.exists():
            raise ValueError(f"A novel with title '{book_data['title']}' already exists")
        
        # Create Structure
        (novel_dir / "source").mkdir(parents=True, exist_ok=True)
        (novel_dir / "chapters").mkdir(parents=True, exist_ok=True)
        (novel_dir / "consistency").mkdir(parents=True, exist_ok=True)
        (novel_dir / "processing").mkdir(parents=True, exist_ok=True)
        (novel_dir / "exports").mkdir(parents=True, exist_ok=True)

        # Copy Source EPUB
        shutil.copy(epub_path, novel_dir / "source" / "original.epub")

        # Initialize empty consistency files
        with open(novel_dir / "consistency" / "characters.json", 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)
        with open(novel_dir / "consistency" / "locations.json", 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2)

        # Save Chapters
        chapter_manifest = []
        for i, chapter in enumerate(book_data['chapters']):
            chapter_id = f"ch{str(i+1).zfill(4)}"
            chapter_filename = f"{chapter_id}.json"
            chapter_path = novel_dir / "chapters" / chapter_filename
            
            # Save Text Content
            with open(chapter_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": chapter_id,
                    "title": chapter['title'],
                    "content": chapter['content'],
                    "order": i + 1
                }, f, indent=2, ensure_ascii=False)
            
            chapter_processing_dir = novel_dir / "processing" / chapter_id
            (chapter_processing_dir / "extraction").mkdir(parents=True, exist_ok=True)
            (chapter_processing_dir / "images").mkdir(parents=True, exist_ok=True)
            (chapter_processing_dir / "audio").mkdir(parents=True, exist_ok=True)
            (chapter_processing_dir / "voice_samples").mkdir(parents=True, exist_ok=True)
            (chapter_processing_dir / "video").mkdir(parents=True, exist_ok=True)
            (chapter_processing_dir / "logs").mkdir(parents=True, exist_ok=True)

            chapter_manifest.append({
                "id": chapter_id,
                "title": chapter['title'],
                "path": str(chapter_path),
                "processing_dir": str(chapter_processing_dir),
                "preview": chapter['content'][:100] + "..." if len(chapter['content']) > 100 else chapter['content']
            })

        # Create Metadata
        metadata = {
            "title": book_data['title'],
            "author": book_data['author'],
            "created_at": datetime.now().isoformat(),
            "chapter_count": len(chapter_manifest),
            "directory": str(novel_dir),
            "source_epub": str((novel_dir / "source" / "original.epub")),
        }
        
        with open(novel_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        logger.info(f"Created novel '{book_data['title']}' with {len(chapter_manifest)} chapters")
        return metadata

    def get_novel(self, title: str) -> Optional[Dict]:
        """
        Retrieves novel metadata by title.
        
        Args:
            title: The novel title (will be sanitized for folder matching)
            
        Returns:
            Dictionary with novel metadata, or None if not found
        """
        safe_title = self._safe_filename(title)
        novel_dir = DATA_DIR / safe_title
        
        if not novel_dir.exists():
            # Try to find by scanning metadata (for titles with different casing)
            for folder in DATA_DIR.iterdir():
                if not folder.is_dir():
                    continue
                meta_path = folder / "metadata.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            if meta.get('title', '').lower() == title.lower():
                                return meta
                    except Exception:
                        continue
            return None
        
        meta_path = novel_dir / "metadata.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def update_novel_title(self, current_title: str, new_title: str) -> Optional[Dict]:
        """Update a novel's title, renaming its directory and updating metadata."""
        if current_title == new_title:
            return self.get_novel(current_title)
            
        old_dir = self._get_novel_dir(current_title)
        new_dir = self._get_novel_dir(new_title)
        
        if not old_dir.exists():
            raise ValueError(f"Novel '{current_title}' not found")
            
        if new_dir.exists():
            raise ValueError(f"A novel with title '{new_title}' already exists")
            
        # Update metadata before renaming
        meta_path = old_dir / "metadata.json"
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata['title'] = new_title
                metadata['updated_at'] = datetime.now().isoformat()
                
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to update metadata.json: {e}")
                raise ValueError(f"Failed to update metadata: {e}")
        
        # Rename directory
        try:
            old_dir.rename(new_dir)
            return self.get_novel(new_title)
        except Exception as e:
            logger.error(f"Failed to rename directory from {old_dir} to {new_dir}: {e}")
            raise ValueError(f"Failed to rename directory: {e}")

    def get_chapters(self, title: str) -> List[Dict]:
        """
        Retrieves list of chapters for a novel.
        
        Args:
            title: The novel title
            
        Returns:
            List of chapter metadata dictionaries
        """
        novel = self.get_novel(title)
        if not novel:
            return []
            
        novel_dir = Path(novel['directory'])
        chapters_dir = novel_dir / "chapters"
        
        chapters = []
        if chapters_dir.exists():
            for f in sorted(chapters_dir.glob("*.json")):
                try:
                    with open(f, 'r', encoding='utf-8') as cf:
                        data = json.load(cf)
                        content = data.get("content", "")
                        chapter_id = data.get("id")
                        
                        if isinstance(content, list):
                            first_chunk = content[0] if content else ""
                            preview_text = first_chunk[:150] + "..." if len(first_chunk) > 150 else first_chunk
                        else:
                            preview_text = content[:150] + "..." if len(content) > 150 else content
                            
                        # Determine processing status indicators
                        status = "pending"
                        has_scenes = False
                        has_images = False
                        has_audio = False
                        has_video = False
                        
                        proc_dir = novel_dir / "processing" / chapter_id
                        
                        if proc_dir.exists():
                            # Scenes
                            if (proc_dir / "scenes.json").exists():
                                has_scenes = True
                                status = "extracted"
                            
                            # Images
                            if (proc_dir / "images").exists() and any((proc_dir / "images").iterdir()):
                                has_images = True
                                
                            # Audio 
                            if (proc_dir / "audio").exists() and any((proc_dir / "audio").iterdir()):
                                has_audio = True
                                
                            # Video
                            video_path = proc_dir / f"{chapter_id}.mp4"
                            if video_path.exists() or (proc_dir / "video").exists() and any((proc_dir / "video").glob("*.mp4")):
                                has_video = True
                                status = "completed"

                        chapters.append({
                            "id": chapter_id,
                            "title": data.get("title"),
                            "order": data.get("order"),
                            "path": str(f.resolve()),
                            "preview": preview_text,
                            "status": status,
                            "progress": {
                                "scenes": has_scenes,
                                "images": has_images,
                                "audio": has_audio,
                                "video": has_video
                            }
                        })
                except Exception as e:
                    logger.error("Failed to load chapter %s: %s", f, e)
                    continue
        
        return sorted(chapters, key=lambda x: x['order'])

    def get_chapter_content(self, title: str, chapter_id: str) -> Optional[Dict]:
        """
        Retrieves full content of a specific chapter.
        
        Args:
            title: The novel title
            chapter_id: The chapter ID (e.g., 'ch001')
            
        Returns:
            Dictionary with chapter content, or None if not found
        """
        novel = self.get_novel(title)
        if not novel:
            return None
            
        novel_dir = Path(novel['directory'])
        chapter_path = novel_dir / "chapters" / f"{chapter_id}.json"
        
        if chapter_path.exists():
            with open(chapter_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def resolve_chapter_processing_dir(self, title: str, chapter_id: str) -> Optional[Path]:
        """
        Return processing directory for chapter in a novel.
        
        Args:
            title: The novel title
            chapter_id: The chapter ID (e.g., 'ch001')
            
        Returns:
            Path to the chapter's processing directory
        """
        novel = self.get_novel(title)
        if not novel:
            return None
        novel_dir = Path(novel['directory'])
        return novel_dir / "processing" / chapter_id

    def get_consistency_dir(self, title: str) -> Optional[Path]:
        """
        Get the consistency directory for a novel.
        
        Args:
            title: The novel title
            
        Returns:
            Path to the novel's consistency directory
        """
        novel = self.get_novel(title)
        if not novel:
            return None
        novel_dir = Path(novel['directory'])
        return novel_dir / "consistency"

    def delete_novel(self, title: str) -> bool:
        """
        Deletes a novel and all its associated data from the library.
        
        Args:
            title: The novel title
            
        Returns:
            True if successful, False if novel not found
        """
        novel = self.get_novel(title)
        if not novel:
            return False
        
        novel_dir = Path(novel['directory'])
        if not novel_dir.exists():
            return False
        
        try:
            shutil.rmtree(novel_dir)
            logger.info(f"Deleted novel '{novel.get('title', title)}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete novel '{title}': {e}")
            raise

    def update_novel_title(self, old_title: str, new_title: str) -> Optional[Dict]:
        """
        Updates the title of a novel and renames its directory.
        
        Args:
            old_title: Current novel title
            new_title: New title for the novel
            
        Returns:
            Updated metadata dictionary, or None if novel not found
            
        Raises:
            ValueError: If new title is empty or already exists
        """
        novel = self.get_novel(old_title)
        if not novel:
            return None
        
        if not new_title or not new_title.strip():
            raise ValueError("Title cannot be empty")
        
        new_title = new_title.strip()
        old_dir = Path(novel['directory'])
        
        # Create new directory name with updated title
        safe_title = self._safe_filename(new_title)
        new_dir = DATA_DIR / safe_title
        
        try:
            # If directory name would change, rename it
            if old_dir != new_dir:
                if new_dir.exists():
                    raise ValueError(f"A novel with title '{new_title}' already exists")
                shutil.move(str(old_dir), str(new_dir))
            
            # Update metadata
            novel['title'] = new_title
            novel['directory'] = str(new_dir)
            novel['updated_at'] = datetime.now().isoformat()
            
            with open(new_dir / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(novel, f, indent=2)
            
            logger.info(f"Updated novel title: '{old_title}' -> '{new_title}'")
            return novel
            
        except Exception as e:
            logger.error(f"Failed to update novel title '{old_title}': {e}")
            raise

    def novel_exists(self, title: str) -> bool:
        """Check if a novel with the given title exists."""
        return self.get_novel(title) is not None
