"""EPUB parsing utilities."""

from pathlib import Path
from typing import List

from ebooklib import epub
import ebooklib
from bs4 import BeautifulSoup


def extract_chapters(epub_path: Path) -> List[str]:
    """Extract chapters from an EPUB file as plain text strings."""
    book = epub.read_epub(str(epub_path))
    chapters: List[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator=" ").strip()
        if text:
            chapters.append(text)
    return chapters
