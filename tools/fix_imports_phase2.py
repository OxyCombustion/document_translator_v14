#!/usr/bin/env python3
"""
Fix import paths after Phase 2 package reorganization.

This script updates all import statements in moved packages to reflect their new locations
in the vertical pipeline architecture.
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict
import sys

# Package name mappings (old location -> new location)
PACKAGE_MAPPINGS = {
    # Extraction pipeline (7 packages)
    'extraction_v14_P1': 'pipelines.extraction.packages.extraction_v14_P1',
    'detection_v14_P14': 'pipelines.extraction.packages.detection_v14_P14',
    'docling_agents_v14_P17': 'pipelines.extraction.packages.docling_agents_v14_P17',
    'docling_agents_v14_P8': 'pipelines.extraction.packages.docling_agents_v14_P8',
    'specialized_extraction_v14_P15': 'pipelines.extraction.packages.specialized_extraction_v14_P15',
    'extraction_comparison_v14_P12': 'pipelines.extraction.packages.extraction_comparison_v14_P12',
    'extraction_utilities_v14_P18': 'pipelines.extraction.packages.extraction_utilities_v14_P18',

    # RAG ingestion pipeline (4 packages)
    'rag_v14_P2': 'pipelines.rag_ingestion.packages.rag_v14_P2',
    'rag_extraction_v14_P16': 'pipelines.rag_ingestion.packages.rag_extraction_v14_P16',
    'semantic_processing_v14_P4': 'pipelines.rag_ingestion.packages.semantic_processing_v14_P4',
    'analysis_validation_v14_P19': 'pipelines.rag_ingestion.packages.analysis_validation_v14_P19',

    # Data management pipeline (4 packages)
    'curation_v14_P3': 'pipelines.data_management.packages.curation_v14_P3',
    'database_v14_P6': 'pipelines.data_management.packages.database_v14_P6',
    'metadata_v14_P13': 'pipelines.data_management.packages.metadata_v14_P13',
    'relationship_detection_v14_P5': 'pipelines.data_management.packages.relationship_detection_v14_P5',

    # Shared foundation (6 packages)
    'common': 'pipelines.shared.packages.common',
    'infrastructure_v14_P10': 'pipelines.shared.packages.infrastructure_v14_P10',
    'cli_v14_P7': 'pipelines.shared.packages.cli_v14_P7',
    'specialized_utilities_v14_P20': 'pipelines.shared.packages.specialized_utilities_v14_P20',
    'analysis_tools_v14_P9': 'pipelines.shared.packages.analysis_tools_v14_P9',
    'processing_utilities_v14_P11': 'pipelines.shared.packages.processing_utilities_v14_P11',
}

def find_python_files(base_dir: Path) -> List[Path]:
    """Find all Python files in pipeline packages."""
    python_files = []
    for pipeline_dir in base_dir.glob('pipelines/*/packages/*'):
        if pipeline_dir.is_dir():
            python_files.extend(pipeline_dir.glob('**/*.py'))
    return python_files

def analyze_imports(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Analyze import statements in a file.

    Returns:
        List of (line_number, original_line, package_name) tuples
    """
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                # Match "from X import Y" or "import X"
                from_match = re.match(r'^(\s*)from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import', line)
                import_match = re.match(r'^(\s*)import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', line)

                if from_match:
                    package = from_match.group(2).split('.')[0]
                    if package in PACKAGE_MAPPINGS:
                        imports.append((line_num, line.rstrip(), package))
                elif import_match:
                    package = import_match.group(2).split('.')[0]
                    if package in PACKAGE_MAPPINGS:
                        imports.append((line_num, line.rstrip(), package))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return imports

def fix_import_line(line: str, old_package: str, new_package: str) -> str:
    """Fix a single import line by replacing old package path with new one."""
    # Handle "from old_package..." patterns
    pattern1 = f'from\\s+{re.escape(old_package)}'
    replacement1 = f'from {new_package}'
    line = re.sub(pattern1, replacement1, line)

    # Handle "import old_package..." patterns
    pattern2 = f'import\\s+{re.escape(old_package)}'
    replacement2 = f'import {new_package}'
    line = re.sub(pattern2, replacement2, line)

    return line

def fix_file_imports(file_path: Path, dry_run: bool = True) -> int:
    """
    Fix all imports in a single file.

    Returns:
        Number of lines fixed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

    fixed_count = 0
    new_lines = []

    for line in lines:
        new_line = line
        for old_pkg, new_pkg in PACKAGE_MAPPINGS.items():
            if old_pkg in line and ('import' in line):
                fixed_line = fix_import_line(line, old_pkg, new_pkg)
                if fixed_line != line:
                    fixed_count += 1
                    new_line = fixed_line
                    break
        new_lines.append(new_line)

    if not dry_run and fixed_count > 0:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return 0

    return fixed_count

def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description='Fix imports after Phase 2 reorganization')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    print(f"Scanning for Python files in {base_dir}/pipelines/...")

    python_files = find_python_files(base_dir)
    print(f"Found {len(python_files)} Python files to check")

    total_files_with_changes = 0
    total_lines_fixed = 0

    for file_path in python_files:
        # First analyze to see if changes are needed
        imports_to_fix = analyze_imports(file_path)

        if imports_to_fix:
            # Fix the file
            fixed_count = fix_file_imports(file_path, dry_run=args.dry_run)

            if fixed_count > 0:
                total_files_with_changes += 1
                total_lines_fixed += fixed_count

                rel_path = file_path.relative_to(base_dir)
                status = "[DRY RUN]" if args.dry_run else "[FIXED]"
                print(f"{status} {rel_path}: {fixed_count} import(s) updated")

                if args.verbose:
                    for line_num, original_line, package in imports_to_fix:
                        print(f"  Line {line_num}: {original_line}")

    print(f"\n{'=' * 70}")
    print(f"Summary:")
    print(f"  Files with import changes: {total_files_with_changes}")
    print(f"  Total import lines updated: {total_lines_fixed}")
    if args.dry_run:
        print(f"\nThis was a dry run. Use --fix to apply changes.")
    else:
        print(f"\nAll changes have been applied.")
    print(f"{'=' * 70}")

    return 0 if total_files_with_changes == 0 else total_lines_fixed

if __name__ == '__main__':
    sys.exit(main())
