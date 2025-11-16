#!/usr/bin/env python3
"""Check Docling DocumentConverter API."""
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
methods = [m for m in dir(converter) if not m.startswith('_') and callable(getattr(converter, m))]

print("Available methods on DocumentConverter:")
for m in sorted(methods):
    print(f"  - {m}")
