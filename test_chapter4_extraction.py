#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chapter 4 Extraction Test - Full Pipeline
Tests equation, table, figure, and text extraction on real PDF
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Setup output directory
output_dir = Path("test_output_chapter4")
output_dir.mkdir(exist_ok=True)

print("=" * 70)
print("CHAPTER 4 EXTRACTION TEST")
print("=" * 70)
print(f"Output directory: {output_dir}")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Import required modules
print("Importing modules...")
try:
    import fitz  # PyMuPDF
    from common.src.base.base_extraction_agent import Zone, ExtractedObject
    from detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule
    print("✅ Core modules imported")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Load PDF
pdf_path = Path("test_data/Ch-04_Heat_Transfer.pdf")
print(f"\nLoading PDF: {pdf_path}")

try:
    doc = fitz.open(str(pdf_path))
    print(f"✅ PDF loaded: {len(doc)} pages")
except Exception as e:
    print(f"❌ Failed to load PDF: {e}")
    sys.exit(1)

# Test 1: Text Extraction (simplest test)
print("\n" + "=" * 70)
print("TEST 1: Text Extraction")
print("=" * 70)

try:
    page = doc[0]
    text = page.get_text()
    
    # Save text
    text_output = output_dir / "page_00_text.txt"
    with open(text_output, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"✅ Text extracted from page 0")
    print(f"   - Length: {len(text)} characters")
    print(f"   - Lines: {len(text.splitlines())} lines")
    print(f"   - Output: {text_output}")
    print(f"   - Preview: {text[:200]}...")
except Exception as e:
    print(f"❌ Text extraction failed: {e}")

# Test 2: Image/Figure Extraction
print("\n" + "=" * 70)
print("TEST 2: Image/Figure Extraction")
print("=" * 70)

try:
    images_extracted = 0
    for page_num in range(min(5, len(doc))):  # First 5 pages
        page = doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            
            if pix.n - pix.alpha < 4:  # RGB or Gray
                img_output = output_dir / f"page_{page_num:02d}_image_{img_index:02d}.png"
                pix.save(str(img_output))
                images_extracted += 1
            else:  # CMYK
                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                img_output = output_dir / f"page_{page_num:02d}_image_{img_index:02d}.png"
                pix1.save(str(img_output))
                images_extracted += 1
                pix1 = None
            
            pix = None
    
    print(f"✅ Images extracted: {images_extracted}")
    print(f"   - From pages: 0-{min(5, len(doc))-1}")
    print(f"   - Output: {output_dir}/page_XX_image_XX.png")
except Exception as e:
    print(f"❌ Image extraction failed: {e}")

# Test 3: Detect objects with Unified Detection
print("\n" + "=" * 70)
print("TEST 3: Unified Detection (YOLO)")
print("=" * 70)

try:
    detector = UnifiedDetectionModule()
    print(f"✅ UnifiedDetectionModule instantiated")
    
    # Detect on first page only (to keep test fast)
    print(f"   Running detection on page 0...")
    zones = detector.detect_page(str(pdf_path), 0)
    
    print(f"✅ Detection complete")
    print(f"   - Zones detected: {len(zones)}")
    
    # Count by type
    zone_types = {}
    for zone in zones:
        ztype = zone.zone_type
        zone_types[ztype] = zone_types.get(ztype, 0) + 1
    
    for ztype, count in sorted(zone_types.items()):
        print(f"   - {ztype}: {count}")
    
    # Save zones to JSON
    zones_output = output_dir / "page_00_zones.json"
    zones_data = []
    for zone in zones:
        zones_data.append({
            'zone_type': zone.zone_type,
            'bbox': zone.bbox,
            'confidence': zone.confidence,
            'metadata': zone.metadata
        })
    
    with open(zones_output, 'w', encoding='utf-8') as f:
        json.dump(zones_data, f, indent=2)
    
    print(f"   - Output: {zones_output}")
    
except Exception as e:
    print(f"❌ Detection failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Extract zones to images
print("\n" + "=" * 70)
print("TEST 4: Zone Extraction (crop zones from PDF)")
print("=" * 70)

try:
    if 'zones' in dir() and len(zones) > 0:
        page = doc[0]
        zones_extracted = 0
        
        for idx, zone in enumerate(zones[:10]):  # First 10 zones
            bbox = zone.bbox
            rect = fitz.Rect(bbox)
            
            # Render zone at 2x resolution
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            
            zone_output = output_dir / f"zone_{idx:02d}_{zone.zone_type}.png"
            pix.save(str(zone_output))
            zones_extracted += 1
        
        print(f"✅ Zones extracted: {zones_extracted}")
        print(f"   - Output: {output_dir}/zone_XX_type.png")
    else:
        print("⚠️  No zones available to extract")
except Exception as e:
    print(f"❌ Zone extraction failed: {e}")

# Close PDF
doc.close()

# Final Summary
print("\n" + "=" * 70)
print("EXTRACTION SUMMARY")
print("=" * 70)

output_files = list(output_dir.glob("*"))
print(f"\nOutput files created: {len(output_files)}")
for f in sorted(output_files)[:20]:  # Show first 20
    size = f.stat().st_size
    print(f"   - {f.name} ({size:,} bytes)")

if len(output_files) > 20:
    print(f"   ... and {len(output_files) - 20} more files")

print(f"\n✅ CHAPTER 4 EXTRACTION TEST COMPLETE")
print(f"   All output saved to: {output_dir}/")
print()
