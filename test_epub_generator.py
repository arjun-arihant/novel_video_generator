
import zipfile
import os

epub_name = 'test_novel.epub'

# Create mimetype
with open('mimetype', 'w') as f:
    f.write('application/epub+zip')

# Create META-INF/container.xml
os.makedirs('META-INF', exist_ok=True)
with open('META-INF/container.xml', 'w') as f:
    f.write('''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
   <rootfiles>
      <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
   </rootfiles>
</container>''')

# Create OEBPS/content.opf
os.makedirs('OEBPS', exist_ok=True)
with open('OEBPS/content.opf', 'w') as f:
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookID" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>Test Novel</dc:title>
        <dc:creator opf:role="aut">Test Author</dc:creator>
        <dc:language>en</dc:language>
        <dc:identifier id="BookID" opf:scheme="UUID">urn:uuid:12345</dc:identifier>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        <item id="chapter1" href="chapter1.html" media-type="application/xhtml+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>''')

# Create OEBPS/toc.ncx
with open('OEBPS/toc.ncx', 'w') as f:
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:12345"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle>
        <text>Test Novel</text>
    </docTitle>
    <navMap>
        <navPoint id="navPoint-1" playOrder="1">
            <navLabel>
                <text>Chapter 1</text>
            </navLabel>
            <content src="chapter1.html"/>
        </navPoint>
    </navMap>
</ncx>''')

# Create OEBPS/chapter1.html
with open('OEBPS/chapter1.html', 'w') as f:
    f.write('''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter 1</title>
</head>
<body>
    <h1>Chapter 1: The Beginning</h1>
    <p>This is the first paragraph of the test novel.</p>
    <p>It was a dark and stormy night.</p>
</body>
</html>''')

# Zip it up
with zipfile.ZipFile(epub_name, 'w') as zipf:
    zipf.write('mimetype', compress_type=zipfile.ZIP_STORED)
    zipf.write('META-INF/container.xml', compress_type=zipfile.ZIP_DEFLATED)
    zipf.write('OEBPS/content.opf', compress_type=zipfile.ZIP_DEFLATED)
    zipf.write('OEBPS/toc.ncx', compress_type=zipfile.ZIP_DEFLATED)
    zipf.write('OEBPS/chapter1.html', compress_type=zipfile.ZIP_DEFLATED)

# Cleanup
os.remove('mimetype')
os.remove('META-INF/container.xml')
os.rmdir('META-INF')
os.remove('OEBPS/content.opf')
os.remove('OEBPS/toc.ncx')
os.remove('OEBPS/chapter1.html')
os.rmdir('OEBPS')

print(f"Created {epub_name}")
