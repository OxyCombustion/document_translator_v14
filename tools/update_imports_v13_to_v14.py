#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Import Update Script: V13→V14 Migration

Automatically updates import statements from v13 to v14 package structure.
Removes sys.path manipulation and updates import paths.

Usage:
    python tools/update_imports_v13_to_v14.py --dry-run     # Preview changes
    python tools/update_imports_v13_to_v14.py               # Execute changes
    python tools/update_imports_v13_to_v14.py --validate    # Validate only

Author: Claude Code
Date: 2025-11-15
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
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class ImportUpdater:
    """Update v13 imports to v14 package structure."""

    def __init__(self, mapping_file: Path, dry_run: bool = False):
        self.mapping_file = mapping_file
        self.dry_run = dry_run
        self.stats = {
            'files_processed': 0,
            'imports_updated': 0,
            'syspath_removed': 0,
            'files_modified': 0,
            'syntax_errors': 0
        }

        # Load mapping
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.mappings = data['mappings']

    def find_files_with_v13_imports(self, root_dir: Path) -> List[Path]:
        """Find all Python files with v13 imports."""
        files = []
        for py_file in root_dir.rglob('*.py'):
            # Skip __pycache__ and .git directories
            if '__pycache__' in str(py_file) or '.git' in str(py_file):
                continue

            # Skip this script itself!
            if py_file.name == 'update_imports_v13_to_v14.py':
                continue

            # Check if file contains v13 imports
            try:
                content = py_file.read_text(encoding='utf-8')
                if 'from agents.' in content or 'import agents' in content:
                    files.append(py_file)
                elif 'sys.path.insert' in content or 'sys.path.append' in content:
                    files.append(py_file)
            except Exception as e:
                print(f"⚠️  Error reading {py_file}: {e}")

        return files

    def update_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Update imports in a single file.

        Returns:
            (modified, changes) - whether file was modified and list of changes made
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            changes = []

            # Remove sys.path manipulation
            content, syspath_changes = self._remove_syspath_manipulation(content)
            changes.extend(syspath_changes)

            # Update v13 imports
            content, import_changes = self._update_v13_imports(content)
            changes.extend(import_changes)

            modified = content != original_content

            if modified and not self.dry_run:
                # Write updated content
                file_path.write_text(content, encoding='utf-8')
                self.stats['files_modified'] += 1

            if changes:
                self.stats['files_processed'] += 1

            return modified, changes

        except Exception as e:
            print(f"❌ Error updating {file_path}: {e}")
            return False, []

    def _remove_syspath_manipulation(self, content: str) -> Tuple[str, List[str]]:
        """Remove sys.path.insert() and sys.path.append() lines."""
        changes = []
        lines = content.split('\n')
        new_lines = []
        skip_next_empty = False

        for i, line in enumerate(lines):
            # Check for sys.path manipulation (but not in comments or documentation)
            if ('sys.path.insert' in line or 'sys.path.append' in line) and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                changes.append(f"Removed sys.path manipulation: {line.strip()}")
                self.stats['syspath_removed'] += 1
                skip_next_empty = True
                continue

            # Skip comment about adding parent directory
            if skip_next_empty and not line.strip():
                skip_next_empty = False
                continue

            # Skip comment lines about sys.path
            if ('# Add parent directory to path' in line or '# Fallback for direct execution' in line):
                changes.append(f"Removed comment: {line.strip()}")
                continue

            new_lines.append(line)
            skip_next_empty = False

        return '\n'.join(new_lines), changes

    def _update_v13_imports(self, content: str) -> Tuple[str, List[str]]:
        """Update v13 import statements to v14."""
        changes = []

        for old_path, mapping in self.mappings.items():
            new_path = mapping['new_path']

            # Pattern 1: from agents.X import Y
            pattern1 = rf'from {re.escape(old_path)} import (.+)'
            if re.search(pattern1, content):
                old_import = re.search(pattern1, content).group(0)
                new_import = old_import.replace(old_path, new_path)
                content = re.sub(pattern1, f'from {new_path} import \\1', content)
                changes.append(f"Updated: {old_import} → {new_import}")
                self.stats['imports_updated'] += 1

            # Pattern 2: import agents.X
            pattern2 = rf'import {re.escape(old_path)}'
            if re.search(pattern2, content):
                old_import = re.search(pattern2, content).group(0)
                new_import = old_import.replace(old_path, new_path)
                content = re.sub(pattern2, f'import {new_path}', content)
                changes.append(f"Updated: {old_import} → {new_import}")
                self.stats['imports_updated'] += 1

        return content, changes

    def validate_syntax(self, file_path: Path) -> bool:
        """Validate Python syntax of updated file."""
        try:
            import py_compile
            py_compile.compile(str(file_path), doraise=True)
            return True
        except py_compile.PyCompileError as e:
            print(f"❌ Syntax error in {file_path}: {e}")
            self.stats['syntax_errors'] += 1
            return False

    def process_all_files(self, root_dir: Path) -> None:
        """Process all files with v13 imports."""
        print("\n" + "="*70)
        print("Import Update: V13→V14 Migration")
        if self.dry_run:
            print("Mode: DRY RUN (no files will be modified)")
        print("="*70 + "\n")

        # Find files
        files = self.find_files_with_v13_imports(root_dir)
        print(f"Found {len(files)} files to process\n")

        # Process each file
        for file_path in files:
            rel_path = file_path.relative_to(root_dir)
            modified, changes = self.update_file(file_path)

            if changes:
                print(f"\n📝 {rel_path}")
                for change in changes:
                    print(f"   {change}")

                # Validate syntax if modified
                if modified and not self.dry_run:
                    if self.validate_syntax(file_path):
                        print(f"   ✅ Syntax validated")
                    else:
                        print(f"   ❌ Syntax validation failed")

        # Print summary
        print("\n" + "="*70)
        print("Summary")
        print("="*70)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files modified: {self.stats['files_modified']}")
        print(f"Imports updated: {self.stats['imports_updated']}")
        print(f"sys.path removed: {self.stats['syspath_removed']}")
        print(f"Syntax errors: {self.stats['syntax_errors']}")
        print("="*70 + "\n")

        if self.dry_run:
            print("🔍 This was a dry run. Use without --dry-run to apply changes.")
        elif self.stats['syntax_errors'] == 0:
            print("✅ All updates completed successfully!")
        else:
            print("⚠️  Some files have syntax errors. Review and fix before committing.")


def main():
    parser = argparse.ArgumentParser(
        description='Update v13 imports to v14 package structure'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Only validate syntax of existing files'
    )

    args = parser.parse_args()

    # Paths
    root_dir = Path(__file__).parent.parent
    mapping_file = root_dir / 'tools' / 'import_mapping_v13_to_v14.json'

    # Create updater
    updater = ImportUpdater(mapping_file, dry_run=args.dry_run or args.validate)

    # Process files
    updater.process_all_files(root_dir)

    return 0 if updater.stats['syntax_errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
