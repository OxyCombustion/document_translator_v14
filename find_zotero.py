#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zotero Installation Finder
Locates Zotero data directory on Linux systems.

Author: Claude Code
Date: 2025-11-20
"""

import sys
import os
from pathlib import Path

# UTF-8 setup
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except: pass

print("=" * 80)
print("ZOTERO INSTALLATION FINDER")
print("=" * 80)
print()

# Common Zotero locations on Linux
search_paths = [
    Path.home() / "Zotero",
    Path.home() / ".zotero" / "zotero",
    Path.home() / "snap" / "zotero-snap" / "common" / ".zotero" / "zotero",
    Path("/home") / os.getenv("USER", "") / "Zotero",
]

print("Searching common Zotero locations...")
print()

found_installations = []

for search_path in search_paths:
    if search_path.exists():
        print(f"✓ Checking: {search_path}")

        # Check for database
        db_path = search_path / "zotero.sqlite"
        db_bak_path = search_path / "zotero.sqlite.bak"
        storage_path = search_path / "storage"

        has_db = db_path.exists()
        has_backup = db_bak_path.exists()
        has_storage = storage_path.exists()

        if has_db or has_backup or has_storage:
            found_installations.append({
                'path': search_path,
                'database': db_path if has_db else None,
                'backup': db_bak_path if has_backup else None,
                'storage': storage_path if has_storage else None,
                'complete': has_db and has_storage
            })

            print(f"  → Database: {'✅' if has_db else '❌'} {db_path if has_db else 'Not found'}")
            print(f"  → Backup:   {'✅' if has_backup else '❌'} {db_bak_path if has_backup else 'Not found'}")
            print(f"  → Storage:  {'✅' if has_storage else '❌'} {storage_path if has_storage else 'Not found'}")

            if has_storage:
                storage_items = list(storage_path.iterdir())[:5]
                print(f"  → Storage items: {len(list(storage_path.iterdir()))} total")
                if storage_items:
                    print(f"     First few: {', '.join([item.name for item in storage_items[:3]])}")
            print()
    else:
        print(f"✗ Not found: {search_path}")

print()
print("=" * 80)
print("RESULTS")
print("=" * 80)
print()

if found_installations:
    print(f"Found {len(found_installations)} Zotero installation(s):")
    print()

    for i, install in enumerate(found_installations, 1):
        status = "✅ COMPLETE" if install['complete'] else "⚠️  PARTIAL"
        print(f"{i}. {status}")
        print(f"   Path: {install['path']}")
        print(f"   Database: {install['database'] or 'Missing'}")
        print(f"   Backup: {install['backup'] or 'Not created yet'}")
        print(f"   Storage: {install['storage'] or 'Missing'}")
        print()

    # Recommend best installation
    complete_installs = [i for i in found_installations if i['complete']]
    if complete_installs:
        recommended = complete_installs[0]
        print("RECOMMENDED:")
        print(f"  Use: {recommended['path']}")
        print()
        print("To test Zotero integration, use this path in your code:")
        print(f"  zotero_data_dir = Path('{recommended['path']}')")
        print()
else:
    print("❌ No Zotero installations found in common locations.")
    print()
    print("Please check:")
    print("  1. Is Zotero installed?")
    print("  2. Where is your Zotero data directory located?")
    print("  3. In Zotero: Edit → Preferences → Advanced → Files and Folders")
    print("     to find your data directory location")
    print()
