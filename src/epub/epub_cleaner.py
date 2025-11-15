import json
import logging
from pathlib import Path
from typing import List, Dict
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import ftfy
from tqdm import tqdm

logger = logging.getLogger("epub_cleaner")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Boilerplate patterns to filter out
BOILERPLATE_PATTERNS = [
    "translator's note", "translated by", "all rights reserved",
    "chapter sponsored by", "powered by", "visit", "www.",
    "discord", "patreon", "support the author"
]

def is_boilerplate(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in BOILERPLATE_PATTERNS)

def clean_text(text: str) -> str:
    """Fix encoding issues and normalize whitespace/quotes"""
    text = ftfy.fix_text(text)
    # Normalize quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    # Normalize whitespace
    text = " ".join(text.split())
    return text.strip()

def html_to_paragraphs(html_content: str) -> List[str]:
    """Extract clean paragraphs from HTML"""
    soup = BeautifulSoup(html_content, "xml")
    
    # Remove junk tags
    for tag in soup(["script", "style", "iframe", "footer", "nav"]):
        tag.decompose()
    
    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if not text or len(text) < 10:  # Skip very short fragments
            continue
        if is_boilerplate(text):
            continue
        paragraphs.append(clean_text(text))
    
    return paragraphs

def extract_chapters(epub_path: str) -> List[Dict]:
    """Extract all chapters from EPUB"""
    book = epub.read_epub(epub_path)
    items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    
    chapters = []
    for idx, item in enumerate(items):
        content = item.get_content().decode("utf-8", errors="replace")
        paragraphs = html_to_paragraphs(content)
        
        if not paragraphs:  # Skip empty chapters
            continue
        
        # Try to get title from HTML
        soup = BeautifulSoup(content, "xml")
        title_tag = soup.find(["h1", "h2"])
        title = clean_text(title_tag.get_text()) if title_tag else f"Chapter {idx + 1}"
        
        chapters.append({
            "id": idx,
            "title": title,
            "paragraphs": paragraphs,
            "word_count": sum(len(p.split()) for p in paragraphs)
        })
    
    return chapters

def process_epub(epub_path: str, output_dir: str):
    """Process EPUB and save cleaned chapters as JSON"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    epub_name = Path(epub_path).stem
    logger.info(f"Processing: {epub_path}")
    
    chapters = extract_chapters(epub_path)
    
    for chapter in tqdm(chapters, desc="Saving chapters"):
        filename = f"chapter{chapter['id']:04d}.json"
        with open(output_path / filename, "w", encoding="utf-8") as f:
            json.dump(chapter, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved {len(chapters)} chapters to {output_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("epub", help="Path to EPUB file")
    parser.add_argument("--out", default="data/chapters", help="Output directory")
    args = parser.parse_args()
    
    process_epub(args.epub, args.out)