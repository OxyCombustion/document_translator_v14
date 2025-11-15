#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Completeness Validation Agent

Compares actual extracted objects against expected objects from document references.
Identifies gaps, generates quality metrics, and provides actionable reports.

Purpose:
    - Compare found vs expected object counts
    - Identify missing objects (e.g., "Table 4 missing")
    - Generate coverage statistics (10/12 tables = 83.3%)
    - Provide actionable gap reports for extraction improvements

Example:
    Expected (from DocumentReferenceInventoryAgent):
        Tables 1-11 (12 unique references)

    Found (from ObjectNumberingCoordinator):
        Tables 1, 2, 3, 5, 6, 7, 8a, 8b, 10, 11

    Report:
        Missing: Table 4, Table 9
        Coverage: 10/12 (83.3%)

Author: V12 Development Team
Created: 2025-10-20
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
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


@dataclass
class CompletenessReport:
    """Completeness validation report for a single object type."""

    object_type: str  # 'tables', 'figures', 'equations'
    expected_count: int  # Number of unique references found
    found_count: int  # Number of objects actually extracted
    missing_objects: List[str]  # Object numbers that are missing
    unexpected_objects: List[str]  # Object numbers found but not referenced
    coverage_percent: float  # found_count / expected_count * 100
    quality_grade: str  # A (95%+), B (85%+), C (75%+), D (60%+), F (<60%)


class CompletenessValidationAgent:
    """
    Validates extraction completeness by comparing found vs expected objects.

    This agent compares:
    1. Expected objects (from DocumentReferenceInventoryAgent)
    2. Found objects (from ObjectNumberingCoordinator)
    3. Generates actionable gap reports

    Example:
        >>> agent = CompletenessValidationAgent()
        >>> inventory = load_inventory("reference_inventory.json")
        >>> extracted_zones = load_extracted_zones()
        >>> report = agent.validate_completeness(inventory, extracted_zones)
        >>> print(f"Tables missing: {report['tables'].missing_objects}")
        ['4', '9']
    """

    def __init__(self):
        """Initialize completeness validation agent."""
        print("================================================================================")
        print("COMPLETENESS VALIDATION AGENT")
        print("================================================================================")
        print()

    def validate_completeness(
        self,
        inventory: Dict[str, Any],
        extracted_zones: Dict[str, List[Any]]
    ) -> Dict[str, CompletenessReport]:
        """
        Validate completeness by comparing inventory vs extracted objects.

        Args:
            inventory: Dictionary from DocumentReferenceInventoryAgent
                {
                    'tables': {'all_referenced': {'1', '2', '3'}, ...},
                    'figures': {...},
                    'equations': {...}
                }
            extracted_zones: Dictionary of extracted zones with object_number metadata
                {
                    'tables': [Zone(metadata={'object_number': '1'}), ...],
                    'figures': [...],
                    'equations': [...]
                }

        Returns:
            Dictionary mapping object type to CompletenessReport
        """
        print("Validating extraction completeness...")
        print()

        reports = {}

        for obj_type in ['tables', 'figures', 'equations']:
            print(f"Validating {obj_type}...")

            # Get expected objects from inventory
            if obj_type in inventory:
                expected = set(inventory[obj_type]['all_referenced'])
            else:
                expected = set()

            # Get found objects from extracted zones
            if obj_type in extracted_zones:
                found = set()
                for zone in extracted_zones[obj_type]:
                    if 'object_number' in zone.metadata:
                        obj_num = str(zone.metadata['object_number'])
                        # Only count numbered objects (skip unnumbered_*)
                        if not obj_num.startswith('unnumbered_'):
                            found.add(obj_num)
            else:
                found = set()

            # Calculate gaps
            missing = expected - found
            unexpected = found - expected

            # Calculate coverage
            expected_count = len(expected)
            found_count = len(found & expected)  # Only count expected objects found

            if expected_count > 0:
                coverage = (found_count / expected_count) * 100
            else:
                coverage = 0.0

            # Assign quality grade
            quality_grade = self._calculate_quality_grade(coverage)

            # Create report
            report = CompletenessReport(
                object_type=obj_type,
                expected_count=expected_count,
                found_count=found_count,
                missing_objects=sorted(list(missing), key=self._natural_sort_key),
                unexpected_objects=sorted(list(unexpected), key=self._natural_sort_key),
                coverage_percent=coverage,
                quality_grade=quality_grade
            )

            reports[obj_type] = report

            # Print summary
            print(f"  Expected: {expected_count} unique {obj_type}")
            print(f"  Found: {found_count} ({coverage:.1f}% coverage)")
            print(f"  Quality: {quality_grade}")

            if missing:
                print(f"  ❌ Missing ({len(missing)}): {', '.join(sorted(missing, key=self._natural_sort_key)[:10])}")
                if len(missing) > 10:
                    print(f"     ... and {len(missing) - 10} more")
            else:
                print(f"  ✅ No missing {obj_type}")

            if unexpected:
                print(f"  ⚠️  Unexpected ({len(unexpected)}): {', '.join(sorted(unexpected, key=self._natural_sort_key)[:5])}")
                if len(unexpected) > 5:
                    print(f"     ... and {len(unexpected) - 5} more")

            print()

        print("================================================================================")
        print()

        return reports

    def _calculate_quality_grade(self, coverage: float) -> str:
        """
        Calculate quality grade from coverage percentage.

        Args:
            coverage: Coverage percentage (0-100)

        Returns:
            Quality grade: A, B, C, D, or F
        """
        if coverage >= 95.0:
            return "A"
        elif coverage >= 85.0:
            return "B"
        elif coverage >= 75.0:
            return "C"
        elif coverage >= 60.0:
            return "D"
        else:
            return "F"

    def _natural_sort_key(self, s: str):
        """
        Natural sort key for strings like '1', '2', '10', '8a', '8b'.

        Returns tuple: (numeric_part, alpha_part)
        """
        import re
        match = re.match(r'(\d+)([a-z]?)', str(s))
        if match:
            num, alpha = match.groups()
            return (int(num), alpha)
        return (0, str(s))

    def generate_actionable_report(
        self,
        reports: Dict[str, CompletenessReport],
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate human-readable actionable report.

        Args:
            reports: Dictionary of CompletenessReport objects
            output_path: Optional path to save report

        Returns:
            Markdown-formatted report string
        """
        lines = []
        lines.append("# Extraction Completeness Report")
        lines.append("")
        lines.append(f"**Generated**: {datetime.now().isoformat()}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Overall summary
        lines.append("## Overall Summary")
        lines.append("")
        lines.append("| Object Type | Expected | Found | Missing | Coverage | Grade |")
        lines.append("|-------------|----------|-------|---------|----------|-------|")

        for obj_type, report in reports.items():
            lines.append(
                f"| {obj_type.title()} | {report.expected_count} | {report.found_count} | "
                f"{len(report.missing_objects)} | {report.coverage_percent:.1f}% | {report.quality_grade} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

        # Detailed gap analysis
        for obj_type, report in reports.items():
            lines.append(f"## {obj_type.title()} Gap Analysis")
            lines.append("")

            if report.missing_objects:
                lines.append(f"### ❌ Missing {obj_type.title()} ({len(report.missing_objects)})")
                lines.append("")

                # Group consecutive missing numbers
                missing_groups = self._group_consecutive(report.missing_objects)
                for group in missing_groups:
                    if len(group) == 1:
                        lines.append(f"- {obj_type.rstrip('s').title()} {group[0]}")
                    else:
                        lines.append(f"- {obj_type.rstrip('s').title()}s {group[0]}-{group[-1]}")

                lines.append("")
                lines.append("**Action Required**: Investigate why these objects were not extracted.")
                lines.append("")
            else:
                lines.append(f"✅ **No missing {obj_type}** - 100% of referenced objects found!")
                lines.append("")

            if report.unexpected_objects:
                lines.append(f"### ⚠️ Unexpected {obj_type.title()} ({len(report.unexpected_objects)})")
                lines.append("")
                lines.append("These objects were extracted but not referenced in the document:")
                lines.append("")
                for obj_num in report.unexpected_objects[:10]:
                    lines.append(f"- {obj_type.rstrip('s').title()} {obj_num}")
                if len(report.unexpected_objects) > 10:
                    lines.append(f"- ... and {len(report.unexpected_objects) - 10} more")
                lines.append("")
                lines.append("**Note**: These may be false positives or objects referenced indirectly.")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Recommendations
        lines.append("## Recommendations")
        lines.append("")

        for obj_type, report in reports.items():
            if report.quality_grade in ['D', 'F']:
                lines.append(f"- **{obj_type.title()}**: Coverage is {report.quality_grade} ({report.coverage_percent:.1f}%). "
                           f"Priority investigation needed - missing {len(report.missing_objects)} objects.")
            elif report.quality_grade == 'C':
                lines.append(f"- **{obj_type.title()}**: Coverage is {report.quality_grade} ({report.coverage_percent:.1f}%). "
                           f"Consider improving extraction methods.")
            elif report.quality_grade == 'B':
                lines.append(f"- **{obj_type.title()}**: Coverage is {report.quality_grade} ({report.coverage_percent:.1f}%). "
                           f"Good quality with room for improvement.")
            else:  # A
                lines.append(f"- **{obj_type.title()}**: Coverage is {report.quality_grade} ({report.coverage_percent:.1f}%). "
                           f"Excellent extraction quality!")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by CompletenessValidationAgent*")

        report_text = "\n".join(lines)

        # Save if path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_text, encoding='utf-8')
            print(f"✅ Saved actionable report to: {output_path}")

        return report_text

    def _group_consecutive(self, numbers: List[str]) -> List[List[str]]:
        """
        Group consecutive numbers for compact display.

        Args:
            numbers: List of number strings (e.g., ['1', '2', '3', '5'])

        Returns:
            List of groups (e.g., [['1', '2', '3'], ['5']])
        """
        if not numbers:
            return []

        # Sort with natural ordering
        sorted_nums = sorted(numbers, key=self._natural_sort_key)

        groups = []
        current_group = [sorted_nums[0]]

        for i in range(1, len(sorted_nums)):
            # Extract numeric part
            import re
            match_curr = re.match(r'(\d+)', sorted_nums[i])
            match_prev = re.match(r'(\d+)', sorted_nums[i-1])

            if match_curr and match_prev:
                num_curr = int(match_curr.group(1))
                num_prev = int(match_prev.group(1))

                # Consecutive if difference is 1
                if num_curr == num_prev + 1:
                    current_group.append(sorted_nums[i])
                else:
                    groups.append(current_group)
                    current_group = [sorted_nums[i]]
            else:
                groups.append(current_group)
                current_group = [sorted_nums[i]]

        groups.append(current_group)
        return groups

    def save_reports(
        self,
        reports: Dict[str, CompletenessReport],
        output_path: Path
    ) -> None:
        """
        Save completeness reports to JSON file.

        Args:
            reports: Dictionary of CompletenessReport objects
            output_path: Path to output JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to serializable format
        output_data = {
            "validation_timestamp": datetime.now().isoformat(),
            "reports": {}
        }

        for obj_type, report in reports.items():
            output_data["reports"][obj_type] = {
                "object_type": report.object_type,
                "expected_count": report.expected_count,
                "found_count": report.found_count,
                "missing_objects": report.missing_objects,
                "unexpected_objects": report.unexpected_objects,
                "coverage_percent": report.coverage_percent,
                "quality_grade": report.quality_grade
            }

        with output_path.open('w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved validation reports to: {output_path}")


if __name__ == "__main__":
    # Test with Chapter 4 data
    from pathlib import Path
    import json

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from base_extraction_agent import Zone

    # Load inventory (from DocumentReferenceInventoryAgent)
    inventory_path = Path("results/inventory/reference_inventory.json")

    if not inventory_path.exists():
        print(f"ERROR: Inventory not found at {inventory_path}")
        print("Run DocumentReferenceInventoryAgent first!")
        sys.exit(1)

    with inventory_path.open('r', encoding='utf-8') as f:
        inventory_data = json.load(f)
        inventory = inventory_data['inventory']

    # Create test extracted zones (simulating ObjectNumberingCoordinator output)
    # This is mock data - in production, this comes from the coordinator

    test_extracted = {
        'tables': [
            Zone(zone_id="table_1", type="table", page=2, bbox=[0,0,100,100],
                 metadata={'object_number': '1'}),
            Zone(zone_id="table_2", type="table", page=4, bbox=[0,0,100,100],
                 metadata={'object_number': '2'}),
            Zone(zone_id="table_3", type="table", page=6, bbox=[0,0,100,100],
                 metadata={'object_number': '3'}),
            # Missing: Table 4
            Zone(zone_id="table_4", type="table", page=8, bbox=[0,0,100,100],
                 metadata={'object_number': '5'}),
            # ... more tables, but missing Table 9
        ],
        'figures': [],  # Empty for now
        'equations': []  # Empty for now
    }

    # Run validation
    agent = CompletenessValidationAgent()
    reports = agent.validate_completeness(inventory, test_extracted)

    # Generate actionable report
    report_path = Path("results/validation/completeness_report.md")
    report_text = agent.generate_actionable_report(reports, report_path)

    # Save JSON reports
    json_path = Path("results/validation/completeness_validation.json")
    agent.save_reports(reports, json_path)

    print("\n=== VALIDATION SUMMARY ===")
    for obj_type, report in reports.items():
        print(f"\n{obj_type.upper()}:")
        print(f"  Coverage: {report.found_count}/{report.expected_count} ({report.coverage_percent:.1f}%)")
        print(f"  Grade: {report.quality_grade}")
        if report.missing_objects:
            print(f"  Missing: {', '.join(report.missing_objects[:5])}")
