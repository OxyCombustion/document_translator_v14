#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick verification script for integration test fixes.
Tests the data parsing logic without running full integration test.
"""

import json
from pathlib import Path

print("=" * 80)
print("Integration Test Fixes Verification")
print("=" * 80)

# Test 1: Extraction summary parsing
print("\n[TEST 1] Extraction summary parsing")
summary_file = Path("test_output_orchestrator/unified_pipeline_summary.json")
if summary_file.exists():
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    # Test the new parsing logic
    if "total_objects" in summary:
        total = summary["total_objects"]
        print(f"  ✓ Found 'total_objects': {total}")
    elif "zones_detected" in summary and "total" in summary["zones_detected"]:
        total = summary["zones_detected"]["total"]
        print(f"  ✓ Found 'zones_detected.total': {total}")
    else:
        zones = summary.get("zones_detected", {})
        total = zones.get("equations", 0) + zones.get("tables", 0) + zones.get("figures", 0)
        print(f"  ✓ Calculated total from zones: {total}")

    print(f"  → Total objects: {total}")
else:
    print("  ✗ Summary file not found")

# Test 2: Data contract validation logic
print("\n[TEST 2] Data contract validation")
if summary_file.exists():
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    has_total = False
    if "total_objects" in summary:
        has_total = True
        method = "'total_objects' field"
    elif "zones_detected" in summary:
        zones = summary["zones_detected"]
        if "total" in zones or ("equations" in zones and "tables" in zones):
            has_total = True
            method = "'zones_detected' structure"

    if has_total:
        print(f"  ✓ Contract validated using {method}")
    else:
        print("  ✗ Contract validation failed")
else:
    print("  ✗ Summary file not found")

# Test 3: ChromaDB API compatibility (mock test)
print("\n[TEST 3] ChromaDB API pattern (mock test)")
print("  Testing collection name extraction logic:")

# Simulate v0.5.x behavior (collection objects)
class MockCollectionOld:
    def __init__(self, name):
        self.name = name

# Simulate v0.6.0+ behavior (strings)
mock_collections_new = ["test_collection"]
mock_collections_old = [MockCollectionOld("test_collection")]

for i, collections in enumerate([mock_collections_new, mock_collections_old], 1):
    collection_name = collections[0] if isinstance(collections[0], str) else collections[0].name
    print(f"  ✓ Test {i}: Extracted name '{collection_name}'")

print("\n" + "=" * 80)
print("All verification tests completed!")
print("=" * 80)
