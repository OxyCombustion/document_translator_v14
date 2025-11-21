#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Zotero Database Access
Demonstrates reading from Windows Zotero database mounted via network.

Author: Claude Code
Date: 2025-11-20
"""

import sys
import os

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except: pass

from pathlib import Path
import sqlite3

print("=" * 80)
print("ZOTERO DATABASE ACCESS TEST")
print("=" * 80)
print()

# Configuration
ZOTERO_MOUNT = Path.home() / "windows_zotero"
ZOTERO_DB = ZOTERO_MOUNT / "zotero.sqlite"

# Verify mount
print("Checking Zotero mount...")
if not ZOTERO_MOUNT.exists():
    print(f"❌ Mount point not found: {ZOTERO_MOUNT}")
    print("   Please run the mount command first")
    sys.exit(1)
print(f"✅ Mount point exists: {ZOTERO_MOUNT}")

# Verify database
if not ZOTERO_DB.exists():
    print(f"❌ Database not found: {ZOTERO_DB}")
    sys.exit(1)

db_size_mb = ZOTERO_DB.stat().st_size / (1024 * 1024)
print(f"✅ Database found: {ZOTERO_DB}")
print(f"   Size: {db_size_mb:.1f} MB")
print()

# Connect to database (read-only)
print("Connecting to Zotero database (read-only)...")
try:
    conn = sqlite3.connect(f"file:{ZOTERO_DB}?mode=ro", uri=True)
    cursor = conn.cursor()
    print("✅ Connected successfully")
    print()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

# Query basic statistics
print("=" * 80)
print("ZOTERO LIBRARY STATISTICS")
print("=" * 80)
print()

try:
    # Count total items
    cursor.execute("SELECT COUNT(*) FROM items WHERE itemID NOT IN (SELECT itemID FROM deletedItems)")
    total_items = cursor.fetchone()[0]
    print(f"Total items: {total_items:,}")

    # Count by item type
    cursor.execute("""
        SELECT itemTypes.typeName, COUNT(*) as count
        FROM items
        JOIN itemTypes ON items.itemTypeID = itemTypes.itemTypeID
        WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
        GROUP BY itemTypes.typeName
        ORDER BY count DESC
        LIMIT 10
    """)

    print()
    print("Top 10 item types:")
    for type_name, count in cursor.fetchall():
        print(f"  {type_name:20s}: {count:,}")

    # Count attachments
    cursor.execute("""
        SELECT COUNT(*) FROM items
        JOIN itemAttachments ON items.itemID = itemAttachments.itemID
        WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
    """)
    total_attachments = cursor.fetchone()[0]
    print()
    print(f"Total attachments: {total_attachments:,}")

    # Sample recent items
    cursor.execute("""
        SELECT items.itemID,
               itemDataValues.value as title,
               datetime(items.dateAdded, 'unixepoch') as added
        FROM items
        JOIN itemData ON items.itemID = itemData.itemID
        JOIN fields ON itemData.fieldID = fields.fieldID
        JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
        WHERE fields.fieldName = 'title'
          AND items.itemID NOT IN (SELECT itemID FROM deletedItems)
        ORDER BY items.dateAdded DESC
        LIMIT 5
    """)

    print()
    print("5 most recently added items:")
    for item_id, title, added in cursor.fetchall():
        title_short = title[:60] + "..." if len(title) > 60 else title
        print(f"  [{item_id}] {title_short}")
        print(f"      Added: {added}")

    print()
    print("=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print()
    print("✅ Zotero database is accessible and readable")
    print(f"✅ Found {total_items:,} items in your library")
    print()
    print("Next steps:")
    print("  1. Use ZoteroIntegrationAgent to extract metadata")
    print("  2. Link PDFs to bibliographic information")
    print("  3. Enrich document metadata for RAG pipeline")
    print()

except Exception as e:
    print(f"❌ Query failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
