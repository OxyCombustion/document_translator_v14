#!/usr/bin/env python3
"""
Import Path Migration Script for v14 Package Reorganization

This script updates all import statements to reflect the new package structure
where packages are organized into pipeline-specific subdirectories.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import shutil
from datetime import datetime

# Package to pipeline mapping
PACKAGE_PIPELINE_MAP = {
    # Extraction
    'detection_v14_P14': 'extraction',
    'docling_agents_v14_P17': 'extraction',
    'docling_agents_v14_P8': 'extraction',
    'extraction_comparison_v14_P12': 'extraction',
    'extraction_utilities_v14_P18': 'extraction',
    'extraction_v14_P1': 'extraction',
    'specialized_extraction_v14_P15': 'extraction',
    
    # RAG Ingestion
    'analysis_validation_v14_P19': 'rag_ingestion',
    'rag_extraction_v14_P16': 'rag_ingestion',
    'rag_v14_P2': 'rag_ingestion',
    'semantic_processing_v14_P4': 'rag_ingestion',
    
    # Data Management
    'curation_v14_P3': 'data_management',
    'database_v14_P6': 'data_management',
    'metadata_v14_P13': 'data_management',
    'relationship_detection_v14_P5': 'data_management',
    
    # Shared
    'analysis_tools_v14_P9': 'shared',
    'cli_v14_P7': 'shared',
    'common': 'shared',
    'infrastructure_v14_P10': 'shared',
    'processing_utilities_v14_P11': 'shared',
    'specialized_utilities_v14_P20': 'shared',
}

class ImportMigrator:
    def __init__(self, root_dir: Path, dry_run: bool = True, backup: bool = True):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.backup = backup
        self.changes_made = []
        self.errors = []
        
        # Build regex patterns for each package
        package_names = '|'.join(re.escape(pkg) for pkg in PACKAGE_PIPELINE_MAP.keys())
        
        # Pattern 1: from package.module import ...
        self.from_import_pattern = re.compile(
            rf'^(\s*from\s+)({package_names})(\.[\w.]*)?(\s+import\s+.*)$',
            re.MULTILINE
        )
        
        # Pattern 2: import package.module
        self.direct_import_pattern = re.compile(
            rf'^(\s*import\s+)({package_names})(\.[\w.]*)?(\s*)$',
            re.MULTILINE
        )
    
    def get_new_import_path(self, package_name: str) -> str:
        """Get the new import path for a package"""
        pipeline = PACKAGE_PIPELINE_MAP.get(package_name)
        if not pipeline:
            return package_name
        return f"pipelines.{pipeline}.packages.{package_name}"
    
    def update_from_import(self, match) -> str:
        """Update 'from package import ...' statements"""
        prefix = match.group(1)  # 'from '
        package = match.group(2)  # package name
        module_path = match.group(3) or ''  # .module.submodule
        import_clause = match.group(4)  # ' import Something'
        
        new_path = self.get_new_import_path(package)
        return f"{prefix}{new_path}{module_path}{import_clause}"
    
    def update_direct_import(self, match) -> str:
        """Update 'import package' statements"""
        prefix = match.group(1)  # 'import '
        package = match.group(2)  # package name
        module_path = match.group(3) or ''  # .module.submodule
        suffix = match.group(4)  # whitespace/newline
        
        new_path = self.get_new_import_path(package)
        return f"{prefix}{new_path}{module_path}{suffix}"
    
    def process_file(self, file_path: Path) -> Tuple[bool, int]:
        """
        Process a single Python file and update imports.
        Returns: (was_modified, num_changes)
        """
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # Update from imports
            content, from_count = self.from_import_pattern.subn(
                self.update_from_import, content
            )
            
            # Update direct imports
            content, direct_count = self.direct_import_pattern.subn(
                self.update_direct_import, content
            )
            
            total_changes = from_count + direct_count
            
            if total_changes > 0:
                if not self.dry_run:
                    # Backup original if requested
                    if self.backup:
                        backup_path = file_path.with_suffix('.py.bak')
                        shutil.copy2(file_path, backup_path)
                    
                    # Write updated content
                    file_path.write_text(content, encoding='utf-8')
                
                self.changes_made.append({
                    'file': str(file_path),
                    'changes': total_changes,
                    'from_imports': from_count,
                    'direct_imports': direct_count
                })
                
                return True, total_changes
            
            return False, 0
            
        except Exception as e:
            self.errors.append({
                'file': str(file_path),
                'error': str(e)
            })
            return False, 0
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files excluding venv and .git"""
        python_files = []
        
        for py_file in self.root_dir.rglob('*.py'):
            # Skip venv and .git directories
            if 'venv' in py_file.parts or '.git' in py_file.parts:
                continue
            python_files.append(py_file)
        
        return python_files
    
    def migrate(self) -> Dict:
        """Run the migration process"""
        print(f"{'DRY RUN: ' if self.dry_run else ''}Starting import migration...")
        print(f"Root directory: {self.root_dir}")
        print(f"Backup enabled: {self.backup}")
        print()
        
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files to process")
        print()
        
        modified_count = 0
        total_changes = 0
        
        for py_file in python_files:
            was_modified, num_changes = self.process_file(py_file)
            if was_modified:
                modified_count += 1
                total_changes += num_changes
                print(f"{'[DRY RUN] ' if self.dry_run else ''}Updated: {py_file.relative_to(self.root_dir)} ({num_changes} changes)")
        
        print()
        print(f"{'DRY RUN ' if self.dry_run else ''}Summary:")
        print(f"  Files processed: {len(python_files)}")
        print(f"  Files modified: {modified_count}")
        print(f"  Total import changes: {total_changes}")
        
        if self.errors:
            print(f"  Errors encountered: {len(self.errors)}")
            print("\nErrors:")
            for error in self.errors:
                print(f"  {error['file']}: {error['error']}")
        
        return {
            'files_processed': len(python_files),
            'files_modified': modified_count,
            'total_changes': total_changes,
            'changes': self.changes_made,
            'errors': self.errors
        }
    
    def generate_report(self, results: Dict, output_file: Path):
        """Generate a detailed migration report"""
        timestamp = datetime.now().isoformat()
        
        report = f"""# Import Migration Report
Generated: {timestamp}
Mode: {'DRY RUN' if self.dry_run else 'ACTUAL'}

## Summary
- Files processed: {results['files_processed']}
- Files modified: {results['files_modified']}
- Total import changes: {results['total_changes']}
- Errors: {len(results['errors'])}

## Modified Files
"""
        for change in results['changes']:
            report += f"\n### {change['file']}\n"
            report += f"- Total changes: {change['changes']}\n"
            report += f"- From imports: {change['from_imports']}\n"
            report += f"- Direct imports: {change['direct_imports']}\n"
        
        if results['errors']:
            report += "\n## Errors\n"
            for error in results['errors']:
                report += f"\n### {error['file']}\n"
                report += f"Error: {error['error']}\n"
        
        output_file.write_text(report, encoding='utf-8')
        print(f"\nDetailed report written to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Migrate import paths for v14 package reorganization'
    )
    parser.add_argument(
        '--root-dir',
        type=Path,
        default=Path(__file__).parent,
        help='Root directory of the project (default: current directory)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Preview changes without modifying files (default: True)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the migration (overrides --dry-run)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Do not create .bak files (not recommended)'
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path('IMPORT_MIGRATION_REPORT.md'),
        help='Path to output report file'
    )
    
    args = parser.parse_args()
    
    # If --execute is specified, turn off dry-run
    dry_run = not args.execute
    backup = not args.no_backup
    
    if not dry_run:
        confirm = input(
            "⚠️  WARNING: This will modify Python files. "
            "Have you committed your changes? (yes/no): "
        )
        if confirm.lower() != 'yes':
            print("Migration cancelled.")
            return 1
    
    migrator = ImportMigrator(
        root_dir=args.root_dir,
        dry_run=dry_run,
        backup=backup
    )
    
    results = migrator.migrate()
    migrator.generate_report(results, args.report)
    
    if dry_run:
        print("\n✓ Dry run complete. Use --execute to apply changes.")
    else:
        print("\n✓ Migration complete!")
    
    return 0 if not results['errors'] else 1

if __name__ == '__main__':
    sys.exit(main())
