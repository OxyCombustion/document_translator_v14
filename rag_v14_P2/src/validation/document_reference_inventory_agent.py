#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Reference Inventory Agent

Scans entire document BEFORE detection to find all object references.
This creates an inventory of expected objects based on in-text mentions.

Purpose:
    - Find all mentions: "Table 4", "Equation 23", "Figure 11"
    - Determine expected ranges: Tables 1-11, Equations 1-106, Figures 1-45
    - Identify gaps: If we see "Table 1" and "Table 3", we know Table 2 exists
    - Enable completeness validation: Compare what we found vs what should exist

Key Insight:
    If a document mentions "Table 11", there should be Tables 1-11.
    If we only detect 10 tables, we know something is missing.

Architecture:
    Phase 0 agent - runs BEFORE detection to set expectations

Author: V12 Development Team
Created: 2025-10-20
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import re
import json
from datetime import datetime
from dataclasses import dataclass, asdict

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

import fitz  # PyMuPDF


@dataclass
class ObjectInventory:
    """Inventory of expected objects based on document references."""

    object_type: str  # 'table', 'figure', 'equation'
    min_number: int
    max_number: int
    all_referenced: Set[str]  # All unique references found (e.g., {'1', '2', '3a', '3b', '4'})
    total_mentions: int  # How many times objects were mentioned
    pages_with_mentions: Set[int]  # Which pages mention this object type


class DocumentReferenceInventoryAgent:
    """
    Scans document to create inventory of expected objects.

    This agent runs BEFORE detection to establish what we're looking for.
    Uses in-text references to determine expected object counts.

    Example:
        >>> agent = DocumentReferenceInventoryAgent(pdf_path)
        >>> inventory = agent.scan_document()
        >>> print(f"Expected tables: {inventory['tables'].min_number}-{inventory['tables'].max_number}")
        Expected tables: 1-11
        >>> print(f"Missing tables: {inventory['tables'].all_referenced - detected_tables}")
        Missing tables: {4, 9}
    """

    def __init__(self, pdf_path: Path):
        """
        Initialize inventory agent.

        Args:
            pdf_path: Path to PDF document

        Raises:
            FileNotFoundError: If PDF doesn't exist
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Compile regex patterns for each object type
        self.patterns = {
            'table': [
                re.compile(r'\bTable\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bTab\.\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bTables\s+(\d+[a-z]?)\s+(?:and|&|,)\s+(\d+[a-z]?)\b', re.IGNORECASE),
            ],
            'figure': [
                re.compile(r'\bFigure\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bFig\.\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bFigs?\.\s+(\d+[a-z]?)\s+(?:and|&|,)\s+(\d+[a-z]?)\b', re.IGNORECASE),
            ],
            'equation': [
                re.compile(r'\bEquation\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\bEq\.\s+(\d+[a-z]?)\b', re.IGNORECASE),
                re.compile(r'\((\d+[a-z]?)\)'),  # Equation numbers in parentheses
                re.compile(r'\bEqs?\.\s+(\d+[a-z]?)\s+(?:and|&|,)\s+(\d+[a-z]?)\b', re.IGNORECASE),
            ]
        }

        # Open PDF
        self.doc = fitz.open(str(self.pdf_path))

    def scan_document(self) -> Dict[str, ObjectInventory]:
        """
        Scan entire document to find all object references.

        Returns:
            Dictionary mapping object type to inventory:
            {
                'tables': ObjectInventory(min=1, max=11, all_referenced={'1','2',...,'11'}),
                'figures': ObjectInventory(...),
                'equations': ObjectInventory(...)
            }
        """
        print("================================================================================")
        print("DOCUMENT REFERENCE INVENTORY - PHASE 0")
        print("================================================================================")
        print(f"PDF: {self.pdf_path.name}")
        print(f"Pages: {len(self.doc)}")
        print()

        # Initialize results
        results = {}

        for obj_type in ['table', 'figure', 'equation']:
            print(f"Scanning for {obj_type} references...")
            inventory = self._scan_object_type(obj_type)
            results[obj_type + 's'] = inventory  # Pluralize key

            if inventory.all_referenced:
                print(f"  ✅ Found {len(inventory.all_referenced)} unique {obj_type}s: {sorted(inventory.all_referenced, key=self._natural_sort_key)[:10]}")
                print(f"     Range: {inventory.min_number}-{inventory.max_number}")
                print(f"     Total mentions: {inventory.total_mentions}")
                print(f"     Pages with mentions: {len(inventory.pages_with_mentions)}")
            else:
                print(f"  ⚠️  No {obj_type} references found")
            print()

        print("================================================================================")
        print()

        return results

    def _scan_object_type(self, obj_type: str) -> ObjectInventory:
        """
        Scan for references to specific object type.

        Args:
            obj_type: 'table', 'figure', or 'equation'

        Returns:
            ObjectInventory with all findings
        """
        all_refs = set()
        total_mentions = 0
        pages_with_mentions = set()

        # Scan all pages
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            text = page.get_text()

            page_found = False

            # Try each pattern for this object type
            for pattern in self.patterns[obj_type]:
                matches = pattern.findall(text)

                if matches:
                    page_found = True

                    # Handle both single captures and tuple captures (for "X and Y" patterns)
                    for match in matches:
                        if isinstance(match, tuple):
                            # "Tables 1 and 2" → ('1', '2')
                            for num in match:
                                if num:  # Skip empty strings
                                    all_refs.add(num)
                                    total_mentions += 1
                        else:
                            # "Table 1" → '1'
                            all_refs.add(match)
                            total_mentions += 1

            if page_found:
                pages_with_mentions.add(page_num + 1)  # 1-indexed

        # Calculate range
        if all_refs:
            # Extract numeric part from references (handles '8a', '8b' → 8)
            numbers = []
            for ref in all_refs:
                # Extract leading digits
                num_match = re.match(r'(\d+)', ref)
                if num_match:
                    numbers.append(int(num_match.group(1)))

            min_num = min(numbers) if numbers else 0
            max_num = max(numbers) if numbers else 0
        else:
            min_num = 0
            max_num = 0

        return ObjectInventory(
            object_type=obj_type,
            min_number=min_num,
            max_number=max_num,
            all_referenced=all_refs,
            total_mentions=total_mentions,
            pages_with_mentions=pages_with_mentions
        )

    def _natural_sort_key(self, s: str) -> Tuple:
        """
        Natural sort key for strings like '1', '2', '10', '8a', '8b'.

        Returns tuple: (numeric_part, alpha_part)
        Examples: '1' → (1, ''), '8a' → (8, 'a'), '10' → (10, '')
        """
        match = re.match(r'(\d+)([a-z]?)', str(s))
        if match:
            num, alpha = match.groups()
            return (int(num), alpha)
        return (0, str(s))

    def save_inventory(self, inventory: Dict[str, ObjectInventory], output_path: Path) -> None:
        """
        Save inventory to JSON file.

        Args:
            inventory: Inventory dictionary from scan_document()
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        output_data = {
            "pdf_source": str(self.pdf_path),
            "scan_timestamp": datetime.now().isoformat(),
            "inventory": {}
        }

        for obj_type, inv in inventory.items():
            output_data["inventory"][obj_type] = {
                "object_type": inv.object_type,
                "min_number": inv.min_number,
                "max_number": inv.max_number,
                "all_referenced": sorted(list(inv.all_referenced), key=self._natural_sort_key),
                "total_mentions": inv.total_mentions,
                "pages_with_mentions": sorted(list(inv.pages_with_mentions))
            }

        with output_path.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved inventory to: {output_path}")

    def __del__(self):
        """Clean up PDF handle."""
        if hasattr(self, 'doc'):
            self.doc.close()


if __name__ == "__main__":
    # Test on Chapter 4
    pdf_path = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")

    if not pdf_path.exists():
        print(f"ERROR: Test PDF not found: {pdf_path}")
        sys.exit(1)

    agent = DocumentReferenceInventoryAgent(pdf_path)
    inventory = agent.scan_document()

    # Save results
    output_path = Path("results/inventory/reference_inventory.json")
    agent.save_inventory(inventory, output_path)

    print("\n=== INVENTORY SUMMARY ===")
    for obj_type, inv in inventory.items():
        print(f"\n{obj_type.upper()}:")
        print(f"  Expected range: {inv.min_number}-{inv.max_number}")
        print(f"  Unique objects: {len(inv.all_referenced)}")
        print(f"  Total mentions: {inv.total_mentions}")
