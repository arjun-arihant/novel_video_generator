"""
Stage 0: EPUB Ingestion
EPUB → raw_book.json per novel. Idempotent.
"""
import json
import re
import logging
from datetime import date
from pathlib import Path

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from config import novel_path, ensure_novel_dirs, MIN_CHAPTER_WORD_COUNT

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """Convert a title to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _extract_text(html: str) -> str:
    """Strip HTML tags and return raw text."""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n")


def _word_count(text: str) -> int:
    return len(text.split())


_SKIP_TITLES = re.compile(
    r"^(table of contents|toc|copyright|index|about the|dedication|"
    r"acknowledgements?|foreword|preface|prologue notes?|appendix|glossary|"
    r"bibliography|references?|cover|title page|also by)$",
    re.IGNORECASE,
)


def _is_content_chapter(title: str, text: str) -> bool:
    """Heuristic: skip TOC, copyright, preambles.
    - Skip if title matches known boilerplate patterns
    - Skip if word count is below threshold
    - Skip if text has suspiciously high ratio of short lines (TOC-style)
    """
    if _SKIP_TITLES.match(title.strip()):
        return False
    wc = _word_count(text)
    if wc < MIN_CHAPTER_WORD_COUNT:
        return False
    # TOC heuristic: if >60% of lines are under 80 chars, it's likely a TOC/index
    lines = [l for l in text.splitlines() if l.strip()]
    if lines:
        short_lines = sum(1 for l in lines if len(l.strip()) < 80)
        if short_lines / len(lines) > 0.8 and wc > 1000:
            return False
    return True


def ingest(epub_path: str) -> tuple[str, str]:
    """
    Parse an EPUB and write raw_book.json + novel_meta.json.

    Returns:
        (book_slug, raw_book_path)
    """
    book = epub.read_epub(epub_path)

    # Extract metadata
    title_list = book.get_metadata("DC", "title")
    author_list = book.get_metadata("DC", "creator")
    title = title_list[0][0] if title_list else Path(epub_path).stem
    author = author_list[0][0] if author_list else "Unknown"
    book_slug = _slugify(title)

    raw_book_path = novel_path(book_slug, "chapters", "raw", "raw_book.json")

    if Path(raw_book_path).exists():
        logger.info("Stage 0 — raw_book.json already exists, skipping ingestion.")
        return book_slug, raw_book_path

    ensure_novel_dirs(book_slug)

    # Extract chapters from EPUB spine order
    chapters = []
    chapter_id = 0
    skipped = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        raw_html = item.get_content().decode("utf-8", errors="replace")
        text = _extract_text(raw_html).strip()

        if not text:
            continue

        # Try to find a heading for the chapter title
        soup = BeautifulSoup(raw_html, "lxml")
        heading = soup.find(["h1", "h2", "h3"])
        chapter_title = heading.get_text(strip=True) if heading else f"Chapter {chapter_id + 1}"

        if not _is_content_chapter(chapter_title, text):
            skipped.append({"title": chapter_title, "word_count": _word_count(text)})
            logger.debug(f"Skipping '{chapter_title}' ({_word_count(text)} words)")
            continue

        chapter_id += 1
        chapters.append({
            "chapter_id": chapter_id,
            "title": chapter_title,
            "raw_text": text,
        })

    raw_book = {
        "schema_version": 1,
        "title": title,
        "author": author,
        "book_slug": book_slug,
        "chapters": chapters,
        "skipped_items": skipped,
    }

    Path(raw_book_path).write_text(
        json.dumps(raw_book, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Stage 0 — Ingested {chapter_id} chapters, skipped {len(skipped)} items.")

    # Write novel_meta.json
    meta_path = novel_path(book_slug, "novel_meta.json")
    if not Path(meta_path).exists():
        meta = {
            "schema_version": 1,
            "title": title,
            "author": author,
            "book_slug": book_slug,
            "total_chapters": chapter_id,
            "date_added": date.today().isoformat(),
            "source_epub": Path(epub_path).name,
        }
        Path(meta_path).write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return book_slug, raw_book_path
