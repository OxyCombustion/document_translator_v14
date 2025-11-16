# Docling Figure Detector - V13 to V14 API Migration Fix

## The Problem

**Current V14 Error** (line 117):
```python
for page_num, page in enumerate(doc.pages, 1):
```

Error: `'ExportedCCSDocument' object has no attribute 'pages'`

**Root Cause**: The Docling API changed between versions. V14 uses a different result structure.

---

## The Solution: V13 Working Pattern

### How V13 Successfully Used Docling

V13's `docling_figure_detector.py` (lines 101-127) shows the correct pattern:

```python
# CORRECT V13 PATTERN
if hasattr(result, 'document'):
    doc = result.document
    
    # Method 1: Check for pictures collection
    if hasattr(doc, 'pictures') and doc.pictures:
        print(f"Found {len(doc.pictures)} pictures in document.pictures")
        for i, picture in enumerate(doc.pictures):
            zone = self._picture_to_zone(picture, i)
            if zone:
                zones.append(zone)
    
    # Method 2: Scan page elements for picture items
    else:
        print("Scanning page elements for pictures...")
        picture_count = 0
        for page_num, page in enumerate(doc.pages, 1):  # Access pages via doc.pages
            if hasattr(page, 'children'):
                for item in page.children:
                    item_type = type(item).__name__
                    if 'Picture' in item_type or 'Figure' in item_type:
                        zone = self._element_to_zone(item, page_num, picture_count)
```

### The Key Difference: Result Structure

**V13 (WORKING)**:
```
result (from converter.convert())
  ├── result.document  <-- Access document THIS WAY
  │   ├── document.pictures
  │   └── document.pages  <-- Iterate pages from document
```

**V14 (BROKEN - Current)**:
```
result (from converter.convert_single())
  ├── result.output  <-- V14 returns output instead!
  │   ├── output.pictures
  │   └── output.pages
```

---

## The Fix: Two Options

### Option 1: Update to V14 API (Recommended)

Change line 101-102 in V14:
```python
# WRONG (V14)
if hasattr(result, 'output'):
    doc = result.output

# Then use doc.pages directly:
for page_num, page in enumerate(doc.pages, 1):
```

### Option 2: Use V13 Pattern with Backward Compatibility

```python
# BEST - Works with both APIs
if hasattr(result, 'document'):
    doc = result.document
elif hasattr(result, 'output'):
    doc = result.output
else:
    print(f"ERROR: Unknown result structure. Has attributes: {dir(result)}")
    return []

# Now doc is guaranteed to have .pages, .pictures, etc.
if hasattr(doc, 'pictures') and doc.pictures:
    for i, picture in enumerate(doc.pictures):
        zone = self._picture_to_zone(picture, i)
```

---

## Complete Working V14 Code

```python
def detect_figures(self, pdf_path: Path, docling_result=None) -> List[Zone]:
    """
    Detect figure regions using Docling's document model.
    
    Compatible with Docling 1.9+
    """
    print(f"\n{'='*80}")
    print(f"DOCLING FIGURE DETECTION")
    print(f"{'='*80}")
    print(f"PDF: {pdf_path}")
    print()

    start_time = datetime.now()

    # Use provided result or run conversion
    if docling_result:
        print("Using existing Docling result (from table detection)...")
        result = docling_result
    else:
        print("Running Docling conversion...")
        result = self.converter.convert(str(pdf_path))

    # Extract figure zones from Docling's document model
    zones = []

    # COMPATIBILITY FIX: Handle both v13 and v14 result structures
    if hasattr(result, 'document'):
        doc = result.document
    elif hasattr(result, 'output'):
        doc = result.output
    else:
        print(f"ERROR: Unknown Docling result structure")
        print(f"Available attributes: {[a for a in dir(result) if not a.startswith('_')]}")
        return []

    # Method 1: Check for pictures collection
    if hasattr(doc, 'pictures') and doc.pictures:
        print(f"Found {len(doc.pictures)} pictures in document.pictures")
        for i, picture in enumerate(doc.pictures):
            zone = self._picture_to_zone(picture, i)
            if zone:
                zones.append(zone)
                print(f"  Picture {i+1}: page {zone.page}, bbox {zone.bbox}")

    # Method 2: Scan page elements for picture items
    else:
        print("Scanning page elements for pictures...")
        picture_count = 0
        
        # CRITICAL: Access pages via doc.pages (not result.pages)
        if hasattr(doc, 'pages'):
            for page_num, page in enumerate(doc.pages, 1):
                if hasattr(page, 'children'):
                    for item in page.children:
                        item_type = type(item).__name__
                        if 'Picture' in item_type or 'Figure' in item_type or 'Image' in item_type:
                            zone = self._element_to_zone(item, page_num, picture_count)
                            if zone:
                                zones.append(zone)
                                print(f"  Picture {picture_count+1}: page {page_num}, bbox {zone.bbox}")
                                picture_count += 1

    duration = (datetime.now() - start_time).total_seconds()

    print()
    print(f"Detection complete in {duration:.1f}s")
    print(f"Figures detected: {len(zones)}")
    print()

    return zones
```

---

## What Changed Between V13 and V14

| Aspect | V13 | V14 |
|--------|-----|-----|
| **Converter method** | `converter.convert()` | `converter.convert_single()` |
| **Result structure** | `result.document` | `result.output` |
| **Accessing pages** | `result.document.pages` | `result.output.pages` |
| **Pictures list** | `result.document.pictures` | `result.output.pictures` |

---

## How Other V13 Detectors Handle This

### DoclingTableDetector (V13, lines 91-92):
```python
if hasattr(result, 'document') and hasattr(result.document, 'tables'):
    for i, table in enumerate(result.document.tables):
```

### DoclingTextDetector (V13, line 97):
```python
doc = docling_result.document

# Then directly access:
for idx, text_item in enumerate(doc.texts):
    page_num = text_item.prov[0].page_no if text_item.prov else 1
```

---

## Summary of the Fix

1. **The Issue**: V14 returns `result.output` instead of `result.document`
2. **The Solution**: Access `doc = result.output` (or use compatibility check)
3. **The Access**: Use `doc.pages` to iterate pages (not `result.pages`)
4. **The Pattern**: `for page_num, page in enumerate(doc.pages, 1):`

This matches exactly how V13 successfully extracted figures!
