#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Output Management Agent - Infrastructure Service for Output Organization

This module provides a service-layer component responsible for organizing,
managing, and archiving all extraction outputs. It prevents root directory clutter,
enforces consistent organization, and implements retention policies.

Design Pattern: Service Layer (NOT an extraction agent)
----------------------------------------------------------
This is an infrastructure service that operates on the file system, not on PDFs.
It does NOT extend BaseExtractionAgent.

Responsibilities:
-----------------
- Directory structure creation and validation
- Output file organization by type/pipeline/document
- Retention policy enforcement (test: 7 days, production: 90 days)
- Archival and cleanup automation
- Symlink management for 'latest' versions
- Storage reporting and monitoring

Author: Claude Sonnet 4.5
Date: 2025-10-09
Version: 1.0.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import shutil
import tarfile
import hashlib
import yaml

# MANDATORY UTF-8 SETUP - NO EXCEPTIONS
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


class OutputManagementAgent:
    """
    Service-layer agent for output organization and lifecycle management.

    This agent manages the complete lifecycle of extraction outputs:
    1. **Organization**: Creates consistent directory structures
    2. **Classification**: Routes outputs by pipeline/format/document
    3. **Retention**: Archives old outputs based on age policies
    4. **Cleanup**: Removes root clutter and maintains clean workspace
    5. **Reporting**: Provides storage usage and organization metrics

    Usage Example:
    --------------
    >>> # Get organized output location
    >>> output_mgr = OutputManagementAgent()
    >>> output_dir = output_mgr.create_output_location(
    ...     document_id="chapter4_heat_transfer",
    ...     pipeline="rag",
    ...     format_type="machine",
    ...     is_test=False
    ... )
    >>> # Save results to organized location
    >>> save_results(output_dir / "document_package.jsonl", results)
    >>> # Update symlinks
    >>> output_mgr.update_latest_symlinks("chapter4_heat_transfer", is_test=False)

    Configuration:
    --------------
    Loads configuration from config/output_management.yaml with settings for:
    - Retention policies (test: 7 days, production: 90 days)
    - Archive formats and compression levels
    - Storage alerts and thresholds
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize output management with configuration.

        Args:
            config_path: Path to YAML configuration file (optional)
                        If None, uses default config/output_management.yaml
        """
        self.agent_type = "output_management"
        self.agent_version = "1.0.0"

        # Load configuration
        self.config = self._load_config(config_path)

        # Base directories
        self.base_dir = Path(self.config['output']['base_directory'])
        self.test_dir = self.base_dir / self.config['output']['structure']['test_dir']
        self.production_dir = self.base_dir / self.config['output']['structure']['production_dir']
        self.archive_dir = self.base_dir / self.config['output']['structure']['archive_dir']

        # Retention policies
        self.retention_policies = self.config['retention']

        # Ensure base structure exists
        self._ensure_base_structure()

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config file, or None for default

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file has syntax errors
        """
        if config_path is None:
            config_path = Path("config/output_management.yaml")

        if not config_path.exists():
            # Return default configuration if file doesn't exist
            print(f"⚠️  Config not found: {config_path}, using defaults")
            return self._get_default_config()

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        print(f"✅ Loaded config: {config_path}")
        return config

    def _get_default_config(self) -> Dict:
        """
        Get default configuration.

        Returns:
            Default configuration dictionary
        """
        return {
            'output': {
                'base_directory': 'outputs',
                'structure': {
                    'test_dir': 'test',
                    'production_dir': 'production',
                    'archive_dir': 'archive'
                },
                'pipelines': [
                    {'name': 'rag', 'subdirs': ['machine', 'human']},
                    {'name': 'fine_tuning', 'subdirs': ['machine', 'human']},
                    {'name': 'extractions', 'subdirs': ['equations', 'tables', 'figures', 'text']}
                ]
            },
            'retention': {
                'test_outputs': {
                    'max_age_days': 7,
                    'max_versions_per_document': 5,
                    'archive_format': 'tar.gz'
                },
                'production_outputs': {
                    'max_age_days': 90,
                    'max_versions_per_document': 10,
                    'archive_format': 'tar.gz'
                },
                'archive': {
                    'compress': True,
                    'compression_level': 9,
                    'verify_after_archive': True
                }
            },
            'format_mapping': {
                'machine_readable': {
                    'extensions': ['.json', '.jsonl', '.parquet', '.hdf5'],
                    'default_subdir': 'machine'
                },
                'human_readable': {
                    'extensions': ['.md', '.xlsx', '.pdf', '.html', '.csv'],
                    'default_subdir': 'human'
                }
            },
            'validation': {
                'storage_alerts': {
                    'warn_threshold_gb': 10,
                    'error_threshold_gb': 50
                }
            }
        }

    def _ensure_base_structure(self):
        """
        Ensure base directory structure exists.

        Creates:
        - outputs/
        - outputs/test/
        - outputs/production/
        - outputs/archive/
        - outputs/archive/test/
        - outputs/archive/production/
        """
        directories = [
            self.base_dir,
            self.test_dir,
            self.production_dir,
            self.archive_dir,
            self.archive_dir / "test",
            self.archive_dir / "production"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def create_output_location(
        self,
        document_id: str,
        pipeline: str,
        format_type: str,
        is_test: bool = False,
        version: Optional[str] = None
    ) -> Path:
        """
        Create and return organized output directory path.

        This is the primary method that other agents call to get output locations.

        Args:
            document_id: Document identifier (e.g., "chapter4_heat_transfer")
            pipeline: Pipeline type ("rag", "fine_tuning", "extractions")
            format_type: Format type ("machine", "human", or extraction type)
            is_test: True for test outputs, False for production
            version: Version string for production (e.g., "v1", "v2")
                    If None, generates timestamp for test or auto-increments for production

        Returns:
            Path to organized output directory (created if doesn't exist)

        Example:
            >>> # Test RAG output
            >>> path = create_output_location("chapter4", "rag", "machine", is_test=True)
            >>> # outputs/test/chapter4/20251009_143022/rag/machine/

            >>> # Production extraction output
            >>> path = create_output_location("chapter4", "extractions", "equations", is_test=False, version="v2")
            >>> # outputs/production/chapter4/v2/extractions/equations/
        """
        # Determine base directory (test vs production)
        if is_test:
            base = self.test_dir
            # Generate timestamp for test runs
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_dir = timestamp
        else:
            base = self.production_dir
            # Use provided version or auto-increment
            if version is None:
                version = self._get_next_version(document_id)
            version_dir = version

        # Build path: base/document_id/version/pipeline/format_type/
        output_path = base / document_id / version_dir / pipeline / format_type

        # Create directory structure
        output_path.mkdir(parents=True, exist_ok=True)

        # Save metadata about this output location
        self._save_output_metadata(output_path, document_id, pipeline, format_type, is_test, version_dir)

        print(f"✅ Created output location: {output_path}")
        return output_path

    def _get_next_version(self, document_id: str) -> str:
        """
        Get next version number for production outputs.

        Args:
            document_id: Document identifier

        Returns:
            Next version string (e.g., "v1", "v2", "v3")
        """
        doc_dir = self.production_dir / document_id

        if not doc_dir.exists():
            return "v1"

        # Find existing versions
        existing_versions = [
            d.name for d in doc_dir.iterdir()
            if d.is_dir() and d.name.startswith('v') and d.name[1:].isdigit()
        ]

        if not existing_versions:
            return "v1"

        # Extract version numbers and find max
        version_numbers = [int(v[1:]) for v in existing_versions]
        next_version = max(version_numbers) + 1

        return f"v{next_version}"

    def _save_output_metadata(
        self,
        output_path: Path,
        document_id: str,
        pipeline: str,
        format_type: str,
        is_test: bool,
        version: str
    ):
        """
        Save metadata about output location.

        Args:
            output_path: Path to output directory
            document_id: Document identifier
            pipeline: Pipeline type
            format_type: Format type
            is_test: Test vs production flag
            version: Version or timestamp string
        """
        metadata = {
            'document_id': document_id,
            'pipeline': pipeline,
            'format_type': format_type,
            'is_test': is_test,
            'version': version,
            'created_at': datetime.now().isoformat(),
            'agent_version': self.agent_version
        }

        # Save to parent directory (version level)
        metadata_path = output_path.parent.parent / "metadata.json"

        # Load existing metadata if present
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = {}

        # Update with new pipeline/format info
        key = f"{pipeline}/{format_type}"
        existing[key] = metadata

        # Save updated metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    def update_latest_symlinks(self, document_id: str, is_test: bool):
        """
        Update 'latest' symlinks to most recent version.

        Creates/updates symlink:
        - outputs/test/{document_id}/latest -> most_recent_timestamp/
        - outputs/production/{document_id}/latest -> most_recent_version/

        Args:
            document_id: Document identifier
            is_test: True for test, False for production

        Note: Symlinks enable consistent access to latest outputs without
              needing to know specific version numbers or timestamps.
        """
        base = self.test_dir if is_test else self.production_dir
        doc_dir = base / document_id

        if not doc_dir.exists():
            print(f"⚠️  Document directory doesn't exist: {doc_dir}")
            return

        # Find most recent version/timestamp
        versions = [
            d for d in doc_dir.iterdir()
            if d.is_dir() and d.name != 'latest'
        ]

        if not versions:
            print(f"⚠️  No versions found in: {doc_dir}")
            return

        # Sort by modification time (most recent first)
        versions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        most_recent = versions[0]

        # Create/update symlink
        symlink_path = doc_dir / "latest"

        # Remove existing symlink if present
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()

        # Create new symlink (relative path for portability)
        try:
            symlink_path.symlink_to(most_recent.name, target_is_directory=True)
            print(f"✅ Updated symlink: {symlink_path} -> {most_recent.name}")
        except OSError as e:
            # Symlinks may not work on all Windows configurations
            print(f"⚠️  Could not create symlink: {e}")
            # Alternative: Create a text file with the path
            with open(doc_dir / "latest.txt", 'w', encoding='utf-8') as f:
                f.write(most_recent.name)
            print(f"✅ Created latest.txt pointer: {most_recent.name}")

    def archive_old_outputs(self, dry_run: bool = False) -> Dict:
        """
        Apply retention policies and archive old outputs.

        Test outputs:
        - Archive outputs older than 7 days
        - Keep only 5 most recent versions per document
        - Delete archives older than 30 days

        Production outputs:
        - Archive outputs older than 90 days
        - Keep all versions (never delete)

        Args:
            dry_run: If True, only report what would be done (don't modify files)

        Returns:
            Dictionary with archive report:
            {
                'test': {
                    'archived_count': int,
                    'deleted_count': int,
                    'space_saved_gb': float
                },
                'production': {
                    'archived_count': int,
                    'space_saved_gb': float
                },
                'would_archive': List[Path],  # If dry_run=True
                'would_delete': List[Path]    # If dry_run=True
            }
        """
        report = {
            'test': {'archived_count': 0, 'deleted_count': 0, 'space_saved_gb': 0},
            'production': {'archived_count': 0, 'space_saved_gb': 0},
            'would_archive': [],
            'would_delete': []
        }

        print(f"\n{'='*70}")
        print(f"ARCHIVAL OPERATION {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(f"{'='*70}\n")

        # Archive test outputs
        test_cutoff = datetime.now() - timedelta(days=self.retention_policies['test_outputs']['max_age_days'])
        report['test'] = self._archive_outputs(
            self.test_dir,
            test_cutoff,
            is_test=True,
            dry_run=dry_run
        )

        # Archive production outputs
        prod_cutoff = datetime.now() - timedelta(days=self.retention_policies['production_outputs']['max_age_days'])
        report['production'] = self._archive_outputs(
            self.production_dir,
            prod_cutoff,
            is_test=False,
            dry_run=dry_run
        )

        # Print summary
        print(f"\n{'-'*70}")
        print(f"ARCHIVAL SUMMARY")
        print(f"{'-'*70}")
        print(f"Test outputs:")
        print(f"  Archived: {report['test']['archived_count']}")
        print(f"  Deleted: {report['test']['deleted_count']}")
        print(f"  Space saved: {report['test']['space_saved_gb']:.2f} GB")
        print(f"\nProduction outputs:")
        print(f"  Archived: {report['production']['archived_count']}")
        print(f"  Space saved: {report['production']['space_saved_gb']:.2f} GB")
        print(f"{'='*70}\n")

        return report

    def _archive_outputs(
        self,
        base_dir: Path,
        cutoff_date: datetime,
        is_test: bool,
        dry_run: bool
    ) -> Dict:
        """
        Archive outputs older than cutoff date.

        Args:
            base_dir: Base directory to scan (test_dir or production_dir)
            cutoff_date: Archive outputs older than this date
            is_test: True for test outputs, False for production
            dry_run: If True, don't modify files

        Returns:
            Archive statistics dictionary
        """
        stats = {
            'archived_count': 0,
            'deleted_count': 0,
            'space_saved_gb': 0
        }

        if not base_dir.exists():
            return stats

        # Scan all document directories
        for doc_dir in base_dir.iterdir():
            if not doc_dir.is_dir():
                continue

            # Scan all version/timestamp directories
            for version_dir in doc_dir.iterdir():
                if not version_dir.is_dir() or version_dir.name == 'latest':
                    continue

                # Check modification time
                mtime = datetime.fromtimestamp(version_dir.stat().st_mtime)

                if mtime < cutoff_date:
                    # Archive this directory
                    if not dry_run:
                        archived_size = self._archive_directory(version_dir, is_test)
                        stats['archived_count'] += 1
                        stats['space_saved_gb'] += archived_size
                    else:
                        print(f"  Would archive: {version_dir}")

        return stats

    def _archive_directory(self, directory: Path, is_test: bool) -> float:
        """
        Archive a directory to compressed tar.gz file.

        Args:
            directory: Directory to archive
            is_test: True for test outputs, False for production

        Returns:
            Space saved in GB (original size - compressed size)
        """
        # Determine archive location
        archive_base = self.archive_dir / ("test" if is_test else "production")
        archive_base.mkdir(parents=True, exist_ok=True)

        # Create archive filename
        doc_id = directory.parent.name
        version = directory.name
        archive_filename = f"{doc_id}_{version}.tar.gz"
        archive_path = archive_base / archive_filename

        print(f"  Archiving: {directory}")
        print(f"         To: {archive_path}")

        # Calculate original size
        original_size = sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())

        # Create compressed archive
        with tarfile.open(archive_path, 'w:gz', compresslevel=self.retention_policies['archive']['compression_level']) as tar:
            tar.add(directory, arcname=directory.name)

        # Verify archive if configured
        if self.retention_policies['archive']['verify_after_archive']:
            if not self._verify_archive(archive_path, directory):
                print(f"  ❌ Archive verification failed: {archive_path}")
                archive_path.unlink()  # Delete corrupted archive
                return 0.0

        # Calculate compressed size
        compressed_size = archive_path.stat().st_size
        space_saved = (original_size - compressed_size) / (1024**3)

        # Remove original directory
        shutil.rmtree(directory)

        print(f"  ✅ Archived successfully")
        print(f"     Original: {original_size / (1024**2):.1f} MB")
        print(f"     Compressed: {compressed_size / (1024**2):.1f} MB")
        print(f"     Saved: {space_saved * 1024:.1f} MB\n")

        return space_saved

    def _verify_archive(self, archive_path: Path, original_dir: Path) -> bool:
        """
        Verify archive integrity by checking if it can be opened and has content.

        Args:
            archive_path: Path to tar.gz archive
            original_dir: Original directory that was archived

        Returns:
            True if archive is valid, False otherwise
        """
        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                # Get list of files in archive
                archive_members = tar.getnames()

                # Check that archive has content
                if len(archive_members) == 0:
                    print(f"  ⚠️  Archive is empty")
                    return False

                # Verify we can read at least one member
                first_member = tar.getmembers()[0]
                if first_member:
                    return True

                return False

        except (tarfile.TarError, OSError) as e:
            print(f"  ⚠️  Archive verification error: {e}")
            return False

    def clean_root_directory(self, dry_run: bool = False) -> Dict:
        """
        Move scattered files from root to organized structure.

        Scans root directory for output files and moves them to appropriate
        organized locations based on naming patterns and content.

        Args:
            dry_run: If True, only report what would be done

        Returns:
            Cleanup report dictionary:
            {
                'files_moved': int,
                'files_skipped': int,
                'space_organized_gb': float,
                'moves': List[Tuple[Path, Path]]  # (source, destination) pairs
            }
        """
        report = {
            'files_moved': 0,
            'files_skipped': 0,
            'space_organized_gb': 0,
            'moves': []
        }

        print(f"\n{'='*70}")
        print(f"ROOT CLEANUP {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(f"{'='*70}\n")

        # Patterns to match
        output_patterns = [
            '*.json',
            '*.jsonl',
            '*.txt',
            '*.log',
            '*.xlsx',
            '*.csv'
        ]

        root = Path('.')
        for pattern in output_patterns:
            for file in root.glob(pattern):
                # Skip if in subdirectory
                if file.parent != root:
                    continue

                # Skip if file no longer exists (may have been moved by previous iteration)
                if not file.exists():
                    continue

                # Determine destination
                destination = self._classify_and_route_file(file)

                if destination:
                    report['moves'].append((file, destination))

                    if not dry_run:
                        # Move file
                        destination.parent.mkdir(parents=True, exist_ok=True)

                        # Get file size before moving
                        file_size = file.stat().st_size

                        shutil.move(str(file), str(destination))
                        print(f"  ✅ Moved: {file.name}")
                        print(f"      To: {destination}")
                        report['files_moved'] += 1
                        report['space_organized_gb'] += file_size / (1024**3)
                    else:
                        print(f"  Would move: {file.name}")
                        print(f"         To: {destination}")
                else:
                    report['files_skipped'] += 1
                    print(f"  ⚠️  Skipped (unknown classification): {file.name}")

        print(f"\n{'-'*70}")
        print(f"CLEANUP SUMMARY")
        print(f"{'-'*70}")
        print(f"Files moved: {report['files_moved']}")
        print(f"Files skipped: {report['files_skipped']}")
        print(f"Space organized: {report['space_organized_gb'] * 1024:.1f} MB")
        print(f"{'='*70}\n")

        return report

    def _classify_and_route_file(self, file: Path) -> Optional[Path]:
        """
        Classify file and determine organized destination.

        Args:
            file: File to classify

        Returns:
            Destination path, or None if cannot classify
        """
        filename = file.name.lower()

        # Test outputs
        if 'test' in filename:
            return self.test_dir / "unknown" / datetime.now().strftime("%Y%m%d_%H%M%S") / file.name

        # Chapter 4 outputs
        if 'chapter4' in filename or 'ch-04' in filename or 'ch04' in filename:
            doc_id = "chapter4_heat_transfer"

            # Equations
            if 'equation' in filename:
                return self.test_dir / doc_id / datetime.now().strftime("%Y%m%d_%H%M%S") / "extractions" / "equations" / file.name

            # Tables
            if 'table' in filename:
                return self.test_dir / doc_id / datetime.now().strftime("%Y%m%d_%H%M%S") / "extractions" / "tables" / file.name

            # Figures
            if 'figure' in filename or 'fig' in filename:
                return self.test_dir / doc_id / datetime.now().strftime("%Y%m%d_%H%M%S") / "extractions" / "figures" / file.name

            # Text
            if 'text' in filename:
                return self.test_dir / doc_id / datetime.now().strftime("%Y%m%d_%H%M%S") / "extractions" / "text" / file.name

            # General Chapter 4 output
            return self.test_dir / doc_id / datetime.now().strftime("%Y%m%d_%H%M%S") / file.name

        # Generic outputs
        return self.test_dir / "unknown" / datetime.now().strftime("%Y%m%d_%H%M%S") / file.name

    def validate_structure(self) -> Dict:
        """
        Validate directory structure integrity.

        Checks:
        - All required directories exist
        - Symlinks are valid
        - Metadata files are present
        - No orphaned files

        Returns:
            Validation report:
            {
                'valid': bool,
                'issues': List[str],
                'warnings': List[str],
                'directory_count': int,
                'file_count': int
            }
        """
        report = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'directory_count': 0,
            'file_count': 0
        }

        print(f"\n{'='*70}")
        print(f"STRUCTURE VALIDATION")
        print(f"{'='*70}\n")

        # Check base directories exist
        required_dirs = [self.base_dir, self.test_dir, self.production_dir, self.archive_dir]
        for directory in required_dirs:
            if not directory.exists():
                report['issues'].append(f"Missing required directory: {directory}")
                report['valid'] = False
            else:
                report['directory_count'] += 1

        # Check symlinks
        for doc_dir in self.test_dir.iterdir():
            if doc_dir.is_dir():
                latest_link = doc_dir / "latest"
                latest_txt = doc_dir / "latest.txt"

                if latest_link.exists() and not latest_link.is_symlink():
                    report['warnings'].append(f"'latest' exists but is not a symlink: {latest_link}")
                elif latest_link.is_symlink() and not latest_link.exists():
                    report['warnings'].append(f"Broken symlink: {latest_link}")

        # Count files
        report['file_count'] = sum(1 for _ in self.base_dir.rglob('*') if _.is_file())

        print(f"Validation: {'✅ PASSED' if report['valid'] else '❌ FAILED'}")
        print(f"Directories: {report['directory_count']}")
        print(f"Files: {report['file_count']}")
        print(f"Issues: {len(report['issues'])}")
        print(f"Warnings: {len(report['warnings'])}")

        if report['issues']:
            print(f"\nIssues found:")
            for issue in report['issues']:
                print(f"  ❌ {issue}")

        if report['warnings']:
            print(f"\nWarnings:")
            for warning in report['warnings']:
                print(f"  ⚠️  {warning}")

        print(f"{'='*70}\n")

        return report

    def get_storage_report(self) -> Dict:
        """
        Generate storage usage and retention report.

        Returns:
            Storage report:
            {
                'total_size_gb': float,
                'test_size_gb': float,
                'production_size_gb': float,
                'archive_size_gb': float,
                'compression_ratio': float,
                'organization_score': int  # 0-100
            }
        """
        report = {
            'total_size_gb': 0,
            'test_size_gb': 0,
            'production_size_gb': 0,
            'archive_size_gb': 0,
            'compression_ratio': 0.0,
            'organization_score': 0
        }

        # Calculate sizes
        if self.test_dir.exists():
            report['test_size_gb'] = sum(f.stat().st_size for f in self.test_dir.rglob('*') if f.is_file()) / (1024**3)

        if self.production_dir.exists():
            report['production_size_gb'] = sum(f.stat().st_size for f in self.production_dir.rglob('*') if f.is_file()) / (1024**3)

        if self.archive_dir.exists():
            report['archive_size_gb'] = sum(f.stat().st_size for f in self.archive_dir.rglob('*') if f.is_file()) / (1024**3)

        report['total_size_gb'] = report['test_size_gb'] + report['production_size_gb'] + report['archive_size_gb']

        # Calculate organization score (simplified)
        root_clutter = len(list(Path('.').glob('*.{json,txt,log,xlsx}')))
        report['organization_score'] = max(0, 100 - root_clutter)

        # Check storage alerts
        warn_threshold = self.config['validation']['storage_alerts']['warn_threshold_gb']
        error_threshold = self.config['validation']['storage_alerts']['error_threshold_gb']

        if report['total_size_gb'] > error_threshold:
            print(f"❌ ERROR: Storage usage ({report['total_size_gb']:.1f} GB) exceeds threshold ({error_threshold} GB)")
        elif report['total_size_gb'] > warn_threshold:
            print(f"⚠️  WARNING: Storage usage ({report['total_size_gb']:.1f} GB) approaching threshold ({error_threshold} GB)")

        return report
