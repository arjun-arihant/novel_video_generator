import os
import json
import shutil
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from src.core.epub_parser import EpubParser

# Setup
DATA_DIR = Path("data")
NOVELS_DIR = DATA_DIR / "novels"
NOVELS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

class LibraryManager:
    """
    Manages the 'Novel Ecosystem' - a structured file system for novels.
    Directory Structure:
    data/novels/
      [novel_id]_[safe_title]/
        source/ (original epub)
        chapters/ (json text)
        workspace/ (scenes.json, characters.json)
        assets/ (images, audio, video)
        exports/
    """

    @staticmethod
    def _safe_filename(name: str) -> str:
        return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')

    def get_library(self) -> List[Dict]:
        """Scans the library and returns a list of novels."""
        novels = []
        if not NOVELS_DIR.exists():
            return []

        for folder in NOVELS_DIR.iterdir():
            if folder.is_dir():
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
        """
        parser = EpubParser(epub_path)
        book_data = parser.parse()
        
        novel_id = str(uuid.uuid4())[:8]
        safe_title = self._safe_filename(book_data['title'])
        novel_dir = NOVELS_DIR / f"{novel_id}_{safe_title}"
        
        # Create Structure
        (novel_dir / "source").mkdir(parents=True, exist_ok=True)
        (novel_dir / "chapters").mkdir(parents=True, exist_ok=True)
        (novel_dir / "workspace").mkdir(parents=True, exist_ok=True)
        (novel_dir / "assets").mkdir(parents=True, exist_ok=True)
        (novel_dir / "exports").mkdir(parents=True, exist_ok=True)

        # Move Source
        shutil.copy(epub_path, novel_dir / "source" / Path(epub_path).name)

        # Save Chapters
        chapter_manifest = []
        for i, chapter in enumerate(book_data['chapters']):
            chapter_id = f"ch{str(i+1).zfill(3)}"
            chapter_filename = f"{chapter_id}.json"
            chapter_path = novel_dir / "chapters" / chapter_filename
            
            # Save Text Content
            with open(chapter_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "id": chapter_id,
                    "title": chapter['title'],
                    "content": chapter['content'],
                    "order": i + 1
                }, f, indent=2)
            
            chapter_manifest.append({
                "id": chapter_id,
                "title": chapter['title'],
                "path": str(chapter_path),
                "preview": chapter['content'][:100] + "..."
            })

        # Create Metadata
        metadata = {
            "id": novel_id,
            "title": book_data['title'],
            "author": book_data['author'],
            "created_at": datetime.now().isoformat(),
            "chapter_count": len(chapter_manifest),
            "directory": str(novel_dir)
        }
        
        with open(novel_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        return metadata

    def get_novel(self, novel_id: str) -> Optional[Dict]:
        """Retrieves novel metadata by ID."""
        for folder in NOVELS_DIR.iterdir():
            if folder.name.startswith(f"{novel_id}_"):
                meta_path = folder / "metadata.json"
                if meta_path.exists():
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
        return None

    def get_chapters(self, novel_id: str) -> List[Dict]:
        """Retrieves list of chapters for a novel."""
        novel = self.get_novel(novel_id)
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
                        chapters.append({
                            "id": data.get("id"),
                            "title": data.get("title"),
                            "order": data.get("order"),
                            "path": str(f.resolve()),
                            "preview": data.get("content", "")[:150] + "..."
                        })
                except Exception:
                    continue
        
        return sorted(chapters, key=lambda x: x['order'])

    def get_chapter_content(self, novel_id: str, chapter_id: str) -> Optional[Dict]:
        """Retrieves full content of a specific chapter."""
        novel = self.get_novel(novel_id)
        if not novel:
            return None
            
        novel_dir = Path(novel['directory'])
        chapter_path = novel_dir / "chapters" / f"{chapter_id}.json"
        
        if chapter_path.exists():
            with open(chapter_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
