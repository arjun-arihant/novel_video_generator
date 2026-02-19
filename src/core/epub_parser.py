import zipfile
import xml.etree.ElementTree as ET
import json
import uuid
import re
from pathlib import Path
from bs4 import BeautifulSoup

class EpubParser:
    def __init__(self, epub_path):
        self.epub_path = Path(epub_path)
        self.ns = {'n': 'urn:oasis:names:tc:opendocument:xmlns:container', 
                   'opf': 'http://www.idpf.org/2007/opf',
                   'dc': 'http://purl.org/dc/elements/1.1/'}

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
                
                # Skip tiny files (often covers, TOCs, empty pages)
                if len(clean_text) < 100: 
                    continue

                chapters.append({
                    "id": str(i+1), # sequential ID for internal use
                    "title": chapter_title,
                    "content": clean_text,
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
