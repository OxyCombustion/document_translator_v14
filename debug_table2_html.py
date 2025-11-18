#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Table 2 HTML - Try HTML Export Instead of Markdown
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
print("DEBUGGING TABLE 2 HTML EXPORT FROM DOCLING")
print("=" * 80)

pdf_path = Path("test_data/Ch-04_Heat_Transfer_subset.pdf")

print(f"\nConverting: {pdf_path}")

converter = DocumentConverter()
result = converter.convert(pdf_path)

if hasattr(result, 'document') and hasattr(result.document, 'tables'):
    tables = result.document.tables

    print(f"\n✅ Found {len(tables)} tables")

    for i, table in enumerate(tables, 1):
        print(f"\n{'='*80}")
        print(f"TABLE {i}")
        print(f"{'='*80}")

        # Try both markdown AND html
        print("\nTrying .export_to_markdown():")
        try:
            markdown = table.export_to_markdown()
            print(f"  Length: {len(markdown)} chars")
            if markdown:
                print(f"  First 200 chars: {markdown[:200]}")
            else:
                print(f"  ❌ EMPTY MARKDOWN")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        print("\nTrying .export_to_html():")
        try:
            html = table.export_to_html()
            print(f"  Length: {len(html)} chars")
            if html:
                print(f"  First 500 chars: {html[:500]}")
            else:
                print(f"  ❌ EMPTY HTML")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # Check table object structure
        print("\nTable object attributes:")
        print(f"  Type: {type(table)}")
        print(f"  Dir: {[attr for attr in dir(table) if not attr.startswith('_')][:20]}")

        # Check for data
        if hasattr(table, 'data'):
            print(f"  Has .data: {table.data}")
        if hasattr(table, 'cells'):
            print(f"  Has .cells: {table.cells}")
        if hasattr(table, 'grid'):
            print(f"  Has .grid: {table.grid}")

else:
    print("❌ No tables found")

print("\n" + "=" * 80)
