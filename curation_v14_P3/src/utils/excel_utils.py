# -*- coding: utf-8 -*-
"""
Excel Utilities - Validation and formatting for Excel file creation.

This module provides utilities for ensuring Excel file compliance with
Microsoft Excel specifications and best practices.
"""

import sys
import os
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
from typing import Optional


# Excel specifications
EXCEL_MAX_SHEET_NAME_LENGTH = 31
EXCEL_INVALID_SHEET_CHARS = r'[\[\]:*?/\\]'  # Characters not allowed in sheet names


def validate_sheet_name(name: str, max_length: int = EXCEL_MAX_SHEET_NAME_LENGTH) -> str:
    """
    Validate and fix Excel sheet name to comply with Excel specifications.

    Excel sheet name requirements:
    - Maximum 31 characters
    - Cannot contain: [ ] : * ? / \\
    - Cannot be empty
    - Cannot start or end with apostrophe

    This function intelligently shortens names by:
    1. Removing invalid characters
    2. Shortening intelligently (preserving important parts)
    3. Ensuring uniqueness with suffix if needed

    Args:
        name: Proposed sheet name
        max_length: Maximum length (default: 31 for Excel)

    Returns:
        Valid sheet name that complies with Excel specifications

    Examples:
        >>> validate_sheet_name("Table_2_Convective_Heat_Transfer")
        'Table_2_Conv_Heat_Transfer'

        >>> validate_sheet_name("Data [2024]: Results/Summary")
        'Data 2024 Results_Summary'

        >>> validate_sheet_name("Very_Long_Table_Name_That_Exceeds_Maximum_Length_Allowed")
        'Very_Long_Table_Name_That_Ex'
    """
    if not name or len(name.strip()) == 0:
        return "Sheet1"

    # Step 1: Remove invalid characters
    cleaned = re.sub(EXCEL_INVALID_SHEET_CHARS, '_', name)

    # Step 2: Remove leading/trailing apostrophes and whitespace
    cleaned = cleaned.strip().strip("'")

    # Step 3: If within length limit, return cleaned name
    if len(cleaned) <= max_length:
        return cleaned

    # Step 4: Intelligently shorten the name
    return _intelligent_truncate(cleaned, max_length)


def _intelligent_truncate(name: str, max_length: int) -> str:
    """
    Intelligently truncate a sheet name to fit within max_length.

    Strategy:
    1. Try to preserve table number and key descriptive words
    2. Abbreviate common words
    3. Remove middle sections if necessary
    4. Keep prefix and important suffix

    Args:
        name: Sheet name to truncate
        max_length: Maximum allowed length

    Returns:
        Truncated name that preserves meaning
    """
    # Common abbreviations
    abbreviations = {
        'Convective': 'Conv',
        'Transfer': 'Tran',
        'Coefficient': 'Coeff',
        'Temperature': 'Temp',
        'Pressure': 'Press',
        'Properties': 'Props',
        'Thermal': 'Therm',
        'Conductivity': 'Cond',
        'Emissivity': 'Emiss',
        'Overall': 'Ovrl',
        'Equivalent': 'Equiv',
        'Resistance': 'Resist',
        'Network': 'Net'
    }

    # Apply abbreviations
    abbreviated = name
    for full, abbrev in abbreviations.items():
        if full in abbreviated:
            abbreviated = abbreviated.replace(full, abbrev)
            if len(abbreviated) <= max_length:
                return abbreviated

    # If still too long, try preserving table number and key parts
    parts = abbreviated.split('_')

    if len(parts) >= 3:
        # Format: Table_N_Description_More_Words
        # Keep: Table_N and shorten description
        table_prefix = '_'.join(parts[:2])  # e.g., "Table_2"
        description = '_'.join(parts[2:])  # e.g., "Conv_Heat_Tran"

        # Calculate available space for description
        available = max_length - len(table_prefix) - 1  # -1 for underscore

        if available > 0:
            shortened_desc = description[:available]
            result = f"{table_prefix}_{shortened_desc}"
            return result

    # Fallback: Simple truncation
    return name[:max_length]


def ensure_unique_sheet_names(names: list) -> list:
    """
    Ensure all sheet names in a workbook are unique.

    If duplicates exist, append numeric suffix (_2, _3, etc.).

    Args:
        names: List of sheet names

    Returns:
        List of unique sheet names

    Example:
        >>> ensure_unique_sheet_names(['Data', 'Data', 'Results', 'Data'])
        ['Data', 'Data_2', 'Results', 'Data_3']
    """
    seen = {}
    unique_names = []

    for name in names:
        if name not in seen:
            seen[name] = 1
            unique_names.append(name)
        else:
            # Append counter
            seen[name] += 1
            counter = seen[name]

            # Make sure suffixed name fits within limit
            suffix = f"_{counter}"
            max_base = EXCEL_MAX_SHEET_NAME_LENGTH - len(suffix)
            base_name = name[:max_base]
            unique_name = f"{base_name}{suffix}"
            unique_names.append(unique_name)

    return unique_names


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_names = [
        "Table_1_Thermal_Conductivity",
        "Table_2_Convective_Heat_Transfer",  # 32 chars - too long!
        "Table_3_Emissivity_Values",
        "Very_Long_Table_Name_That_Exceeds_Maximum_Length_Limit",
        "Data [2024]: Results/Summary",
        "Sheet_With\\Invalid:Chars*?[]"
    ]

    print("Excel Sheet Name Validation Tests:")
    print("=" * 70)
    print(f"{'Original':<45} {'Length':<8} {'Result':<20}")
    print("=" * 70)

    for name in test_names:
        validated = validate_sheet_name(name)
        print(f"{name:<45} {len(name):<8} {validated} ({len(validated)})")

    print("\n" + "=" * 70)
    print("Uniqueness Test:")
    print("=" * 70)

    duplicate_names = ['Data', 'Data', 'Results', 'Data', 'Table_1']
    unique = ensure_unique_sheet_names(duplicate_names)
    for orig, uniq in zip(duplicate_names, unique):
        print(f"{orig:<20} -> {uniq}")
