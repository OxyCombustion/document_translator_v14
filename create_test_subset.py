#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create subset PDF with only pages 2, 7, 8, and 32 for faster testing.

Pages contain:
- Page 2: Tables
- Page 7: Tables
- Page 8: Tables
- Page 32: Tables
"""

import sys
import os
import fitz  # PyMuPDF
from pathlib import Path

# UTF-8 setup
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

# Paths
source_pdf = Path("test_data/Ch-04_Heat_Transfer.pdf")
output_pdf = Path("test_data/Ch-04_Heat_Transfer_subset.pdf")

# Pages to extract (0-indexed)
pages_to_extract = [1, 6, 7, 31]  # Pages 2, 7, 8, 32 in PDF numbering

print(f"Creating subset PDF from: {source_pdf}")
print(f"Extracting pages: {[p+1 for p in pages_to_extract]} (PDF numbering)")

# Open source document
doc = fitz.open(source_pdf)

# Create new document with selected pages
new_doc = fitz.open()

for page_num in pages_to_extract:
    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    print(f"  ✅ Copied page {page_num + 1}")

# Save subset PDF
new_doc.save(output_pdf)
new_doc.close()
doc.close()

print(f"\n✅ Subset PDF created: {output_pdf}")
print(f"   Pages: 4 (from original {len(pages_to_extract)} pages)")
print(f"   Size: {output_pdf.stat().st_size / 1024:.1f} KB")
