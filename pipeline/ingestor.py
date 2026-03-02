"""
Stage 1: EPUB Ingestor
Parses an EPUB file and extracts chapter content as raw HTML.
Each chapter is saved as a separate JSON file.
"""
import json
import logging
import re
from pathlib import Path

import ebooklib
from ebooklib import epub

from pipeline.config import novel_path, ensure_novel_dirs

logger = logging.getLogger(__name__)


def _slugify(title: str) -> str:
    """Convert a book title into a filesystem-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:80] or "untitled"


def _is_chapter_content(item) -> bool:
    """Check if an EPUB item is likely a chapter (not TOC, cover, etc.)."""
    href = getattr(item, "file_name", "") or ""
    lower = href.lower()
    skip_patterns = [
        "toc", "nav", "cover", "title", "copyright", "contents",
        "about", "dedication", "epigraph", "frontmatter", "backmatter",
    ]
    return not any(pat in lower for pat in skip_patterns)


def _extract_title(book: epub.EpubBook) -> str:
    """Extract the book title from EPUB metadata."""
    title = book.get_metadata("DC", "title")
    if title:
        return str(title[0][0])
    return "Untitled"


def ingest_epub(epub_path: str) -> tuple[str, list[int]]:
    """
    Parse an EPUB and save raw chapter HTML to disk.

    Returns:
        (book_slug, chapter_ids) — the slug and list of chapter IDs extracted.
    """
    epub_path = str(Path(epub_path).resolve())
    if not Path(epub_path).exists():
        raise FileNotFoundError(f"EPUB not found: {epub_path}")

    book = epub.read_epub(epub_path, options={"ignore_ncx": True})
    title = _extract_title(book)
    book_slug = _slugify(title)

    ensure_novel_dirs(book_slug)

    # Save book metadata
    meta = {
        "title": title,
        "slug": book_slug,
        "source_epub": epub_path,
        "authors": [str(a[0]) for a in book.get_metadata("DC", "creator")] or ["Unknown"],
    }
    meta_path = Path(novel_path(book_slug, "db", "book_meta.json"))
    if not meta_path.exists():
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    # Extract chapters from spine order
    spine_ids = [item_id for item_id, _ in book.spine]
    items_by_id = {item.get_id(): item for item in book.get_items()}

    chapter_ids = []
    chapter_id = 1

    for spine_id in spine_ids:
        item = items_by_id.get(spine_id)
        if item is None:
            continue
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        if not _is_chapter_content(item):
            continue

        raw_html = item.get_content().decode("utf-8", errors="replace")

        # Skip very short content (empty chapters, section breaks)
        if len(raw_html.strip()) < 100:
            continue

        out_path = Path(novel_path(book_slug, "chapters", "raw", f"chapter_{chapter_id}.json"))
        if not out_path.exists():
            chapter_data = {
                "chapter_id": chapter_id,
                "source_file": getattr(item, "file_name", ""),
                "raw_html": raw_html,
            }
            out_path.write_text(
                json.dumps(chapter_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info(f"Stage 1 — Saved chapter {chapter_id} ({len(raw_html)} bytes)")
        else:
            logger.debug(f"Stage 1 — chapter_{chapter_id}.json exists, skipping.")

        chapter_ids.append(chapter_id)
        chapter_id += 1

    logger.info(f"Stage 1 — Ingested '{title}' → {len(chapter_ids)} chapters (slug: {book_slug})")
    return book_slug, chapter_ids
