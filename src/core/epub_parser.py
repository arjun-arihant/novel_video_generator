import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
import re
import logging
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Minimum word count for a valid chapter (not TOC or placeholder)
MIN_CHAPTER_WORDS = 300


class EpubParser:
    def __init__(self, epub_path):
        self.epub_path = Path(epub_path)
        self.ns = {'n': 'urn:oasis:names:tc:opendocument:xmlns:container', 
                   'opf': 'http://www.idpf.org/2007/opf',
                   'dc': 'http://purl.org/dc/elements/1.1/'}

    def _is_table_of_contents(self, text: str, title: str = "") -> bool:
        """Detect if content is a Table of Contents page.
        
        Args:
            text: The chapter text content
            title: The chapter title
            
        Returns:
            True if the content appears to be a TOC, False otherwise
        """
        # Check title patterns
        toc_title_patterns = ['table of contents', 'contents', 'toc', 
                              'index', '目录', '目錄']
        title_lower = title.lower().strip()
        if title_lower in toc_title_patterns:
            return True
        
        # Check if title contains TOC-related words
        for pattern in toc_title_patterns:
            if pattern in title_lower:
                return True
        
        # Check content patterns - TOC typically has many "Chapter X:" entries
        # but very little actual narrative content
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        if not lines:
            return False
        
        # Count chapter reference patterns
        chapter_ref_patterns = [
            r'^(chapter|ch\.?|chap\.?)\s*\d+',  # "Chapter 1", "Ch. 2", "Chap 3"
            r'^\d+\.\s+',  # "1. Title", "2. Title"
            r'^第\s*\d+\s*[章节回]',  # Chinese chapter patterns "第1章", "第2节"
        ]
        
        chapter_refs = 0
        for line in lines:
            for pattern in chapter_ref_patterns:
                if re.match(pattern, line.lower()):
                    chapter_refs += 1
                    break
        
        # If many chapter references but low word count per line, likely TOC
        total_words = len(text.split())
        avg_words_per_line = total_words / max(len(lines), 1)
        
        # TOC detection heuristics:
        # 1. Many chapter references (>= 3)
        # 2. Low average words per line (< 10) - TOC entries are typically short
        # 3. Total word count is relatively low for a chapter
        if chapter_refs >= 3 and avg_words_per_line < 10:
            logger.debug(f"TOC detected: {chapter_refs} chapter refs, "
                        f"avg {avg_words_per_line:.1f} words/line")
            return True
        
        # Additional check: if most lines are very short and there are many of them
        short_lines = sum(1 for line in lines if len(line.split()) <= 8)
        if len(lines) >= 5 and short_lines / len(lines) >= 0.8 and chapter_refs >= 2:
            logger.debug(f"TOC detected: {short_lines}/{len(lines)} short lines, "
                        f"{chapter_refs} chapter refs")
            return True
        
        return False

    def _chunk_text(self, text: str, target_words: int = 400) -> list[str]:
        """Split text into chunks of roughly target_words, preserving paragraph boundaries.
        
        Args:
            text: Raw chapter text with \n\n delimited paragraphs
            target_words: Target word count per chunk (approx 2-3 mins narration)
            
        Returns:
            List of text chunks
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk_paragraphs = []
        current_word_count = 0
        
        for p in paragraphs:
            words = len(p.split())
            
            # If a single paragraph is larger than target_words, it becomes its own chunk
            if words >= target_words and not current_chunk_paragraphs:
                chunks.append(p)
                continue
                
            if current_word_count + words > target_words and current_chunk_paragraphs:
                chunks.append('\n\n'.join(current_chunk_paragraphs))
                current_chunk_paragraphs = []
                current_word_count = 0
                
            current_chunk_paragraphs.append(p)
            current_word_count += words
            
        if current_chunk_paragraphs:
            chunks.append('\n\n'.join(current_chunk_paragraphs))
            
        return chunks

    def parse(self):
        """
        Parses the EPUB file and returns a dictionary with metadata and chapters.
        Structure:
        {
            "title": str,
            "author": str,
            "chapters": [
                {
                    "id": str,
                    "title": str,
                    "content": str (cleaned text),
                    "file_name": str
                },
                ...
            ]
        }
        """
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {self.epub_path}")

        with zipfile.ZipFile(self.epub_path, 'r') as zf:
            # 1. Find OPF file path from container.xml
            container_xml = zf.read('META-INF/container.xml')
            root = ET.fromstring(container_xml)
            opf_path = root.find('.//n:rootfile', self.ns).attrib['full-path']
            opf_dir = Path(opf_path).parent

            # 2. Parse OPF file
            opf_content = zf.read(opf_path)
            opf_root = ET.fromstring(opf_content)
            
            # Metadata
            metadata = opf_root.find('opf:metadata', self.ns)
            title = metadata.find('dc:title', self.ns).text if metadata.find('dc:title', self.ns) is not None else "Unknown Title"
            author = metadata.find('dc:creator', self.ns).text if metadata.find('dc:creator', self.ns) is not None else "Unknown Author"

            # Manifest (id -> href)
            manifest = {item.attrib['id']: item.attrib['href'] for item in opf_root.find('opf:manifest', self.ns)}

            # Spine (order of reading)
            spine = [item.attrib['idref'] for item in opf_root.find('opf:spine', self.ns)]

            # 3. Extract Chapters
            chapters = []
            for i, item_id in enumerate(spine):
                if item_id not in manifest:
                    continue
                
                href = manifest[item_id]
                # specific to standard epubs, paths are relative to OPF
                file_path = (opf_dir / href).as_posix() # Normalized zip path
                
                # Normalize path logic for zip (sometimes simple join works, sometimes need to be careful with leading /)
                # zipfile expects paths without leading / usually, or relative to root.
                # Simplification: assume simple relative path. relative to root? No, relative to OPF directory.
                # Actually standard zip paths dont have ./ usually. 
                # Let's try to resolve it relative to OPF dir.
                
                try:
                    content_bytes = zf.read(file_path)
                except KeyError:
                    # Sometimes manifest hrefs are URL encoded or have path issues. 
                    # Try simple lookup if simple path fails (rare in valid epubs but possible)
                    print(f"Warning: Could not read {file_path}, skipping.")
                    continue

                soup = BeautifulSoup(content_bytes, 'html.parser')
                
                # Get Title (h1, h2, or filename)
                chapter_title = None
                header = soup.find(['h1', 'h2', 'h3'])
                if header:
                    chapter_title = header.get_text(strip=True)
                
                if not chapter_title:
                     # Fallback to internal checking or title tags
                     title_tag = soup.find('title')
                     if title_tag:
                         chapter_title = title_tag.get_text(strip=True)
                
                if not chapter_title:
                    chapter_title = f"Chapter {i+1}"

                # Get Clean Text
                # Remove script, style
                for element in soup(['script', 'style']):
                    element.decompose()
                
                text = soup.get_text(separator='\n\n')
                
                # Simple cleanup
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                clean_text = '\n\n'.join(lines)
                
                # Skip tiny files (often covers, empty pages)
                if len(clean_text) < 100: 
                    logger.debug(f"Skipping tiny file: {href} ({len(clean_text)} chars)")
                    continue
                
                # Skip Table of Contents pages
                if self._is_table_of_contents(clean_text, chapter_title):
                    logger.info(f"Skipping Table of Contents: {chapter_title} ({href})")
                    continue
                
                # Skip chapters with insufficient content (less than MIN_CHAPTER_WORDS)
                word_count = len(clean_text.split())
                if word_count < MIN_CHAPTER_WORDS:
                    logger.debug(f"Skipping short content: {chapter_title} "
                                f"({word_count} words, minimum: {MIN_CHAPTER_WORDS})")
                    continue
                    
                chunks = self._chunk_text(clean_text)

                chapters.append({
                    "id": str(i+1), # sequential ID for internal use
                    "title": chapter_title,
                    "content": chunks,
                    "file_name": href
                })

        return {
            "title": title,
            "author": author,
            "chapters": chapters
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        parser = EpubParser(sys.argv[1])
        print(json.dumps(parser.parse(), indent=2))
