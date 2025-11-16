#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zotero Working Copy Manager - Safe PDF Isolation System

Manages working copies of Zotero PDFs with session-based cleanup.
Never modifies Zotero library files - always works on isolated copies.

Safety Architecture:
------------------
1. Find PDF in Zotero (read-only query)
2. Copy to working_documents/{zotero_key}/ (isolation)
3. Work on copy during session (Zotero untouched)
4. Auto-cleanup when session ends (remove working copies)

Author: Claude Code
Date: 2025-10-03
Version: 1.0
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil
import json
from datetime import datetime

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

# Import Zotero integration
from .zotero_integration_agent import ZoteroIntegrationAgent


class ZoteroWorkingCopyManager:
    """
    Manages safe working copies of Zotero PDFs.

    Session-Based Workflow:
    ----------------------
    1. session_start() → Set up session tracking
    2. get_working_copy() → Copy PDF from Zotero to working dir
    3. [Process working copy - Zotero untouched]
    4. session_end() → Clean up all working copies

    Usage Example:
    -------------
    >>> manager = ZoteroWorkingCopyManager()
    >>> manager.session_start()
    >>>
    >>> # Get working copy (copies from Zotero)
    >>> result = manager.get_working_copy("Ch-04_Heat_Transfer.pdf")
    >>> working_pdf = result['working_path']
    >>> metadata = result['metadata']
    >>>
    >>> # Process working copy safely
    >>> process_document(working_pdf)
    >>>
    >>> # End session (removes working copies)
    >>> manager.session_end()
    """

    def __init__(self, project_root: Optional[Path] = None, enable_classification: bool = True):
        """
        Initialize working copy manager.

        Args:
            project_root: Project root directory (default: auto-detect)
            enable_classification: Enable automatic document classification (default: True)
        """
        # Project root
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent.parent
        self.project_root = Path(project_root)

        # Working directory: project_root/working_documents/
        self.working_dir = self.project_root / "working_documents"
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Session tracking
        self.session_file = self.working_dir / ".session.json"
        self.session_active = False
        self.current_files = {}  # {pdf_filename: {zotero_key, working_path, copied_at}}

        # Zotero integration
        self.zotero_agent = ZoteroIntegrationAgent()

        # Document classification
        self.enable_classification = enable_classification
        self.classifier = None
        if enable_classification:
            try:
                from classification import DocumentClassifier
                self.classifier = DocumentClassifier()
            except (ImportError, Exception) as e:
                print(f"   ⚠️  Classification disabled: {e}")
                self.enable_classification = False

    def session_start(self) -> Dict[str, Any]:
        """
        Start new working session.

        Cleans up any previous session files and initializes tracking.

        Returns:
            Session info with start time and working directory
        """
        print("="*70)
        print("STARTING ZOTERO WORKING COPY SESSION")
        print("="*70)

        # Clean up any leftover files from previous sessions
        if self.session_file.exists():
            print("⚠️  Found previous session - cleaning up...")
            self._cleanup_previous_session()

        # Initialize new session
        self.session_active = True
        self.current_files = {}

        session_info = {
            "started_at": datetime.now().isoformat(),
            "working_dir": str(self.working_dir),
            "files": {}
        }

        # Save session file
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, indent=2)

        print(f"✅ Session started: {session_info['started_at']}")
        print(f"✅ Working directory: {self.working_dir}")
        print("="*70)

        return session_info

    def get_working_copy(
        self,
        pdf_filename: str,
        force_recopy: bool = False
    ) -> Dict[str, Any]:
        """
        Get working copy of PDF from Zotero.

        Workflow:
        --------
        1. Check if already copied in this session (unless force_recopy)
        2. Find PDF in Zotero database
        3. Copy to working_documents/{zotero_key}/{filename}
        4. Track in session
        5. Return working path + metadata

        Args:
            pdf_filename: PDF filename to find in Zotero
            force_recopy: Always copy fresh (default: False - reuse if in session)

        Returns:
            Dictionary with:
            - working_path: Path to working copy
            - zotero_path: Original Zotero path (read-only reference)
            - zotero_key: Zotero item key
            - metadata: Full bibliographic metadata
            - copied_at: Timestamp of copy

        Raises:
            FileNotFoundError: PDF not found in Zotero
            RuntimeError: Session not started
        """
        if not self.session_active:
            raise RuntimeError("Session not started - call session_start() first")

        # Check if already in session (unless force_recopy)
        if not force_recopy and pdf_filename in self.current_files:
            print(f"♻️  Using existing working copy: {pdf_filename}")
            return self.current_files[pdf_filename]

        print(f"\n📋 Getting working copy: {pdf_filename}")

        # Find in Zotero
        print("   1. Searching Zotero database...")
        zotero_info = self.zotero_agent.find_item_by_pdf(Path(pdf_filename))

        if not zotero_info:
            raise FileNotFoundError(f"PDF not found in Zotero: {pdf_filename}")

        zotero_key = zotero_info['zotero_key']
        zotero_path = zotero_info['pdf_path']

        print(f"   ✅ Found in Zotero: {zotero_key}")

        # Get metadata
        print("   2. Extracting metadata...")
        metadata = self.zotero_agent.get_metadata(zotero_key)

        # Create working directory for this item
        item_working_dir = self.working_dir / zotero_key
        item_working_dir.mkdir(parents=True, exist_ok=True)

        # Copy to working directory
        working_path = item_working_dir / pdf_filename
        print(f"   3. Copying to working directory...")
        print(f"      From: {zotero_path}")
        print(f"      To:   {working_path}")

        shutil.copy2(zotero_path, working_path)

        # Classify document if enabled
        classification = None
        if self.enable_classification and self.classifier:
            try:
                print("   4. Classifying document...")
                zotero_item_type = metadata.get('item_type')
                classification = self.classifier.classify(
                    pdf_path=working_path,
                    zotero_key=zotero_key,
                    zotero_item_type=zotero_item_type,
                    force_user_confirmation=False
                )
                print(f"      Type: {classification.document_type} (confidence: {classification.confidence:.2f})")
                print(f"      Strategy: {classification.chunking_strategy.name}")
            except Exception as e:
                print(f"      ⚠️  Classification failed: {e}")
                classification = None

        # Track in session
        copied_at = datetime.now().isoformat()
        file_info = {
            "working_path": working_path,
            "zotero_path": zotero_path,
            "zotero_key": zotero_key,
            "metadata": metadata,
            "copied_at": copied_at,
            "classification": classification.to_dict() if classification else None
        }

        self.current_files[pdf_filename] = file_info

        # Update session file
        self._update_session_file()

        print(f"   ✅ Working copy ready: {working_path}")

        return file_info

    def session_end(self) -> Dict[str, Any]:
        """
        End session and clean up all working copies.

        SAFETY: Removes all working copies from this session.
        Zotero library remains untouched.

        Returns:
            Cleanup summary with files removed and session duration
        """
        if not self.session_active:
            print("⚠️  No active session to end")
            return {"status": "no_active_session"}

        print("\n" + "="*70)
        print("ENDING ZOTERO WORKING COPY SESSION")
        print("="*70)

        # Get session info
        session_start = None
        if self.session_file.exists():
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                session_start = session_data.get('started_at')

        # Clean up working copies
        removed_files = []
        removed_dirs = []

        for pdf_filename, file_info in self.current_files.items():
            working_path = file_info['working_path']
            zotero_key = file_info['zotero_key']

            # Remove working copy
            if working_path.exists():
                working_path.unlink()
                removed_files.append(str(working_path))
                print(f"   🗑️  Removed: {pdf_filename}")

            # Remove item directory if empty
            item_dir = self.working_dir / zotero_key
            if item_dir.exists() and not any(item_dir.iterdir()):
                item_dir.rmdir()
                removed_dirs.append(str(item_dir))

        # Remove session file
        if self.session_file.exists():
            self.session_file.unlink()

        # Reset session state
        self.session_active = False
        self.current_files = {}

        # Summary
        session_end = datetime.now().isoformat()
        summary = {
            "status": "cleanup_complete",
            "session_start": session_start,
            "session_end": session_end,
            "files_removed": len(removed_files),
            "directories_removed": len(removed_dirs),
            "removed_files": removed_files,
            "removed_directories": removed_dirs
        }

        print(f"\n✅ Cleanup complete:")
        print(f"   Files removed: {len(removed_files)}")
        print(f"   Directories removed: {len(removed_dirs)}")
        print(f"   Session duration: {session_start} → {session_end}")
        print("="*70)

        return summary

    def get_pdfs_by_key(
        self,
        zotero_key: str,
        pdf_index: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get working copies of PDFs by Zotero item key.

        Returns all PDFs in Zotero order (article first, then supplementary).
        Handles filename conflicts with number suffixes (file.pdf, file_2.pdf, etc.).

        Args:
            zotero_key: Zotero item key (8 characters)
            pdf_index: Optional index to get specific PDF (0-based)
                       If None, returns all PDFs

        Returns:
            List of working copy information dictionaries (or single-item list if pdf_index specified)

        Raises:
            FileNotFoundError: No PDFs found for this item
            IndexError: pdf_index out of range
            RuntimeError: Session not started
        """
        if not self.session_active:
            raise RuntimeError("Session not started - call session_start() first")

        print(f"\n📋 Getting PDFs for Zotero item: {zotero_key}")

        # Get all PDF attachments for this item
        pdfs = self.zotero_agent.get_pdf_attachments(zotero_key)

        if not pdfs:
            raise FileNotFoundError(f"No PDFs found for Zotero item: {zotero_key}")

        print(f"   Found {len(pdfs)} PDF(s) for this item:")
        for i, pdf in enumerate(pdfs):
            print(f"   [{i}] {pdf['filename']} ({pdf['size_mb']:.1f} MB)")

        # Filter to specific index if requested
        if pdf_index is not None:
            if pdf_index < 0 or pdf_index >= len(pdfs):
                raise IndexError(f"PDF index {pdf_index} out of range (0-{len(pdfs)-1})")
            pdfs = [pdfs[pdf_index]]
            print(f"\n   Selected PDF {pdf_index}: {pdfs[0]['filename']}")

        # Create working copies for all requested PDFs
        results = []
        for pdf_info in pdfs:
            # Check if already copied in this session
            tracking_key = f"{zotero_key}:{pdf_info['filename']}"
            if tracking_key in self.current_files:
                print(f"   ♻️  Using existing: {pdf_info['filename']}")
                results.append(self.current_files[tracking_key])
                continue

            # Create working directory for this item
            item_working_dir = self.working_dir / zotero_key
            item_working_dir.mkdir(parents=True, exist_ok=True)

            # Handle filename conflicts with number suffix
            working_path = self._resolve_filename_conflict(
                item_working_dir,
                pdf_info['filename']
            )

            # Copy to working directory
            print(f"   📄 Copying: {pdf_info['filename']}")
            print(f"      From: {pdf_info['path']}")
            print(f"      To:   {working_path}")

            shutil.copy2(pdf_info['path'], working_path)

            # Get metadata
            metadata = self.zotero_agent.get_metadata(zotero_key)

            # Track in session
            copied_at = datetime.now().isoformat()
            file_info = {
                "working_path": working_path,
                "zotero_path": pdf_info['path'],
                "zotero_key": zotero_key,
                "attachment_key": pdf_info['attachment_key'],
                "original_filename": pdf_info['filename'],
                "metadata": metadata,
                "copied_at": copied_at,
                "size_mb": pdf_info['size_mb']
            }

            self.current_files[tracking_key] = file_info
            results.append(file_info)

        # Update session file
        self._update_session_file()

        print(f"   ✅ Working copies ready: {len(results)} PDF(s)")
        return results

    def _resolve_filename_conflict(self, directory: Path, filename: str) -> Path:
        """
        Resolve filename conflicts by adding number suffix.

        Args:
            directory: Target directory
            filename: Desired filename

        Returns:
            Path with unique filename (original or with _2, _3, etc. suffix)
        """
        target_path = directory / filename

        # No conflict - use original
        if not target_path.exists():
            return target_path

        # Conflict - add number suffix
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 2

        while True:
            new_filename = f"{stem}_{counter}{suffix}"
            target_path = directory / new_filename
            if not target_path.exists():
                print(f"      ⚠️  Filename conflict - using: {new_filename}")
                return target_path
            counter += 1

    def _cleanup_previous_session(self):
        """Clean up files from previous session."""
        if not self.session_file.exists():
            return

        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Remove tracked files
            for pdf_filename, file_info in session_data.get('files', {}).items():
                working_path = Path(file_info['working_path'])
                if working_path.exists():
                    working_path.unlink()
                    print(f"   🗑️  Removed leftover: {pdf_filename}")

            # Remove session file
            self.session_file.unlink()

        except Exception as e:
            print(f"   ⚠️  Cleanup warning: {e}")

    def _update_session_file(self):
        """Update session file with current files."""
        if not self.session_file.exists():
            return

        with open(self.session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Update files (convert Path to str for JSON)
        session_data['files'] = {
            pdf: {
                'working_path': str(info['working_path']),
                'zotero_path': str(info['zotero_path']),
                'zotero_key': info['zotero_key'],
                'copied_at': info['copied_at']
            }
            for pdf, info in self.current_files.items()
        }

        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)

    def list_working_copies(self) -> Dict[str, Any]:
        """
        List all working copies in current session.

        Returns:
            Dictionary with working copy info
        """
        if not self.session_active:
            return {"status": "no_active_session", "files": []}

        files_info = []
        for pdf_filename, file_info in self.current_files.items():
            files_info.append({
                "filename": pdf_filename,
                "zotero_key": file_info['zotero_key'],
                "working_path": str(file_info['working_path']),
                "copied_at": file_info['copied_at']
            })

        return {
            "status": "active_session",
            "file_count": len(files_info),
            "files": files_info
        }

    def __enter__(self):
        """Context manager entry - start session."""
        self.session_start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - end session and cleanup."""
        self.session_end()


def main():
    """Test working copy manager with Steam Chapter 4."""
    print("Testing Zotero Working Copy Manager...")

    # Context manager usage (auto cleanup)
    with ZoteroWorkingCopyManager() as manager:
        # Get working copy
        result = manager.get_working_copy("Ch-04_Heat_Transfer.pdf")

        print("\n📄 Working Copy Information:")
        print(f"   Working path: {result['working_path']}")
        print(f"   Zotero key: {result['zotero_key']}")
        print(f"   Original: {result['zotero_path']}")

        if result['metadata']:
            print(f"\n📚 Metadata:")
            metadata = result['metadata']
            for key, value in metadata.items():
                if key not in ['zotero_key', 'storage_key']:
                    print(f"   {key}: {value}")

        # List all working copies
        print("\n📋 Current Working Copies:")
        copies = manager.list_working_copies()
        for file_info in copies['files']:
            print(f"   - {file_info['filename']} ({file_info['zotero_key']})")

    # After context manager: working copies automatically cleaned up
    print("\n✅ Test complete - working copies cleaned up automatically")


if __name__ == "__main__":
    main()
