#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Table 2 Markdown - See What Docling Provides

Directly calls Docling to inspect the markdown it provides for Table 2.
"""

import sys
import os

# UTF-8 setup
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

from docling.document_converter import DocumentConverter
from pathlib import Path

print("=" * 80)
print("DEBUGGING TABLE 2 MARKDOWN FROM DOCLING")
print("=" * 80)

# Use subset PDF
pdf_path = Path("test_data/Ch-04_Heat_Transfer_subset.pdf")

print(f"\nConverting: {pdf_path}")
print("This will show what markdown Docling actually provides...")

# Run Docling conversion
converter = DocumentConverter()
result = converter.convert(pdf_path)

# Extract tables
if hasattr(result, 'document') and hasattr(result.document, 'tables'):
    tables = result.document.tables

    print(f"\n✅ Found {len(tables)} tables")

    for i, table in enumerate(tables, 1):
        print(f"\n{'='*80}")
        print(f"TABLE {i}")
        print(f"{'='*80}")

        # Get page and bbox
        page_num = "?"
        bbox = "?"
        if hasattr(table, 'prov') and table.prov:
            for prov in table.prov:
                if hasattr(prov, 'page_no'):
                    page_num = prov.page_no
                if hasattr(prov, 'bbox'):
                    bbox = prov.bbox

        print(f"Page: {page_num}")
        print(f"Bbox: {bbox}")

        # Get markdown
        try:
            markdown = table.export_to_markdown()
            print(f"\nMarkdown length: {len(markdown)} chars")
            print(f"Markdown lines: {len(markdown.splitlines())} lines")
            print(f"\nFull Markdown:")
            print("-" * 80)
            print(markdown)
            print("-" * 80)

            # Show line-by-line breakdown
            print(f"\nLine-by-Line Breakdown:")
            for line_num, line in enumerate(markdown.splitlines(), 1):
                print(f"  Line {line_num}: {repr(line)}")

        except Exception as e:
            print(f"❌ Error getting markdown: {e}")
            import traceback
            traceback.print_exc()

else:
    print("❌ No tables found in result.document.tables")

print("\n" + "=" * 80)
print("DEBUG COMPLETE")
print("=" * 80)
