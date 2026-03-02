"""
Stage 2: HTML Normalizer
Converts raw chapter HTML into clean, readable plain text.
"""
import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

from pipeline.config import novel_path

logger = logging.getLogger(__name__)


def _clean_text(html: str) -> str:
    """Convert HTML to clean plain text."""
    soup = BeautifulSoup(html, "lxml")

    # Remove script and style elements
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()

    # Handle headings — preserve as section markers
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        tag.replace_with(f"\n\n### {tag.get_text(strip=True)}\n\n")

    # Handle paragraphs and divs
    for tag in soup.find_all(["p", "div"]):
        tag.insert_before("\n")
        tag.insert_after("\n")

    # Handle line breaks
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # Handle emphasis
    for em in soup.find_all(["em", "i"]):
        text = em.get_text()
        em.replace_with(f"*{text}*")

    for strong in soup.find_all(["strong", "b"]):
        text = strong.get_text()
        strong.replace_with(f"**{text}**")

    text = soup.get_text()

    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)           # collapse horizontal whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)         # max 2 consecutive newlines
    text = re.sub(r"^\s+", "", text, flags=re.MULTILINE)  # strip leading whitespace per line

    # Remove common EPUB artifacts
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)  # control chars
    text = text.replace("\xa0", " ")                # non-breaking spaces

    return text.strip()


def _extract_chapter_title(text: str) -> str:
    """Extract chapter title from the first heading or first line."""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("### "):
            return line.replace("### ", "").strip()
        if line and len(line) < 100:
            return line
    return "Untitled Chapter"


def normalize_chapter(book_slug: str, chapter_id: int) -> str:
    """
    Normalize a raw chapter HTML file into clean text.

    Returns the cleaned text content.
    """
    raw_path = Path(novel_path(book_slug, "chapters", "raw", f"chapter_{chapter_id}.json"))
    out_path = Path(novel_path(book_slug, "chapters", "normalized", f"chapter_{chapter_id}.json"))

    if out_path.exists():
        logger.debug(f"Stage 2 — Normalized chapter {chapter_id} exists, skipping.")
        data = json.loads(out_path.read_text(encoding="utf-8"))
        return data["text"]

    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    raw_html = raw_data["raw_html"]

    clean = _clean_text(raw_html)
    title = _extract_chapter_title(clean)
    word_count = len(clean.split())

    normalized = {
        "chapter_id": chapter_id,
        "title": title,
        "word_count": word_count,
        "text": clean,
    }

    out_path.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        f"Stage 2 — Normalized chapter {chapter_id}: "
        f"'{title}' ({word_count} words)"
    )
    return clean
