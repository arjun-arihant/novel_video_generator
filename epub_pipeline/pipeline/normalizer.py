"""
Stage 1: Text Normalization
Clean raw chapter text → normalized_ch{N}.json. Idempotent per chapter.
"""
import json
import re
import logging
from pathlib import Path

from config import novel_path

logger = logging.getLogger(__name__)

# Curly quote normalization map
_QUOTE_MAP = str.maketrans({
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote / apostrophe
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2013": "-",  # en dash
    "\u2014": "—",  # em dash (keep as-is would be fine, but normalize to ASCII em)
    "\u2026": "...", # ellipsis
})

_LONE_NUMBER_RE = re.compile(r"^\s*\d+\s*$", re.MULTILINE)
_EXCESSIVE_BLANK_RE = re.compile(r"\n{3,}")
_BROKEN_HYPHEN_RE = re.compile(r"-\n(\w)")  # "some-\nword" → "someword"
_TRAILING_SPACE_RE = re.compile(r"[ \t]+\n")


def _normalize_text(raw_text: str) -> list[str]:
    """
    Clean raw chapter text and return a list of paragraph strings.
    Each paragraph is a non-empty block of text separated by blank lines.
    """
    text = raw_text.translate(_QUOTE_MAP)
    text = _BROKEN_HYPHEN_RE.sub(r"\1", text)        # fix broken hyphenated words
    text = _LONE_NUMBER_RE.sub("", text)              # remove lone page numbers
    text = _TRAILING_SPACE_RE.sub("\n", text)         # remove trailing spaces
    text = _EXCESSIVE_BLANK_RE.sub("\n\n", text)      # collapse multiple blank lines
    text = text.strip()

    # Split into paragraphs on double newlines
    raw_paragraphs = text.split("\n\n")
    paragraphs = []
    for p in raw_paragraphs:
        # Merge orphaned single lines (rejoin lines within a paragraph)
        merged = " ".join(line.strip() for line in p.splitlines() if line.strip())
        if merged:
            paragraphs.append(merged)

    return paragraphs


def normalize_chapter(book_slug: str, chapter: dict) -> str:
    """
    Normalize a single chapter dict from raw_book.json.

    Returns the path to the written normalized JSON file.
    """
    chapter_id = chapter["chapter_id"]
    out_path = novel_path(book_slug, "chapters", "normalized", f"normalized_ch{chapter_id}.json")

    if Path(out_path).exists():
        logger.debug(f"Stage 1 — normalized_ch{chapter_id}.json exists, skipping.")
        return out_path

    paragraphs = _normalize_text(chapter["raw_text"])

    normalized = {
        "schema_version": 1,
        "chapter_id": chapter_id,
        "title": chapter.get("title", ""),
        "paragraphs": paragraphs,
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(f"Stage 1 — Normalized chapter {chapter_id} → {len(paragraphs)} paragraphs.")
    return out_path


def normalize_all(book_slug: str, raw_book: dict) -> list[str]:
    """Normalize all chapters. Returns list of output paths."""
    paths = []
    for chapter in raw_book["chapters"]:
        paths.append(normalize_chapter(book_slug, chapter))
    return paths
