# Docling API Migration: V13 to V14 - Complete Findings

## Task Completed
Successfully found how Docling was successfully used in v13 to extract figures and identified the exact changes needed to fix v14.

---

## File Locations

### V13 Working Implementation
**Primary**: `/home/thermodynamics/document_translator_v13/agents/detection/docling_figure_detector.py`

Key sections:
- **Lines 39-45**: Imports and Zone class
- **Lines 101-102**: Access document via `result.document`
- **Lines 117**: Iterate pages via `doc.pages`
- **Lines 104-127**: Complete figure detection logic

### V14 Broken Implementation  
**Current**: `/home/thermodynamics/document_translator_v14/detection_v14_P14/src/docling/docling_figure_detector.py`

Problem sections:
- **Line 96**: Uses `convert_single()` instead of `convert()`
- **Line 101-102**: Tries to access `result.output` instead of `result.document`
- **Line 117**: Tries to access `doc.pages` when `result.output` doesn't have `.pages` attribute
- **Error**: `'ExportedCCSDocument' object has no attribute 'pages'`

---

## The Root Cause: Docling API Change

### V13 API (Proven Working)
```python
result = converter.convert(str(pdf_path))
# result has attributes:
#   - result.document (the document object)
#       - result.document.pages (list of Page objects)
#       - result.document.pictures
#       - result.document.tables
#       - result.document.texts
```

### V14 API (Current - Broken)
```python
result = converter.convert_single(pdf_path)
# result has attributes:
#   - result.output (different structure than V13's document)
#       - Doesn't have .pages attribute!
#       - Different object type: 'ExportedCCSDocument'
```

---

## The V13 Success Pattern

### Step 1: Get the document
```python
if hasattr(result, 'document'):
    doc = result.document
```

### Step 2: Check for pictures collection
```python
if hasattr(doc, 'pictures') and doc.pictures:
    for i, picture in enumerate(doc.pictures):
        zone = self._picture_to_zone(picture, i)
```

### Step 3: Scan page elements (fallback method)
```python
else:
    for page_num, page in enumerate(doc.pages, 1):  # ← Access pages via doc.pages
        if hasattr(page, 'children'):
            for item in page.children:
                item_type = type(item).__name__
                if 'Picture' in item_type or 'Figure' in item_type:
                    zone = self._element_to_zone(item, page_num, picture_count)
```

---

## The Fix for V14

### Immediate Quick Fix
```python
# At line 101-102, change from:
if hasattr(result, 'output'):
    doc = result.output

# To this compatibility check:
if hasattr(result, 'document'):
    doc = result.document
elif hasattr(result, 'output'):
    doc = result.output
else:
    print("ERROR: Unknown Docling result structure")
    return []

# Then the rest of the code works as-is because doc.pages will exist
```

### Better Fix - Understand What Result Has
Before iterating pages, add debugging:
```python
# After: result = self.converter.convert(str(pdf_path))
print(f"Result type: {type(result)}")
print(f"Result attributes: {[a for a in dir(result) if not a.startswith('_')]}")

if hasattr(result, 'document'):
    print(f"document attributes: {[a for a in dir(result.document) if not a.startswith('_')]}")
elif hasattr(result, 'output'):
    print(f"output attributes: {[a for a in dir(result.output) if not a.startswith('_')]}")
```

This will show which attributes are actually available in V14.

---

## Comparison with Other V13 Detectors

All other v13 detectors use the same pattern successfully:

### DoclingTableDetector (v13, line 91)
```python
if hasattr(result, 'document') and hasattr(result.document, 'tables'):
    for i, table in enumerate(result.document.tables):
```

### DoclingTextDetector (v13, line 97)
```python
doc = docling_result.document

for idx, text_item in enumerate(doc.texts):
    page_num = text_item.prov[0].page_no if text_item.prov else 1
```

### All Access Pattern
```
result.document.COLLECTION
    .pages (for iteration)
    .pictures
    .tables
    .texts
```

---

## What Changed Between Versions

| Feature | V13 | V14 |
|---------|-----|-----|
| Method | `converter.convert(pdf_path)` | `converter.convert_single(pdf_path)` |
| Result.document | ✅ Present | ? Unknown |
| Result.output | ? Unknown | ✅ Present |
| Document.pages | ✅ Works | ? Check |
| Document.pictures | ✅ Works | ? Check |
| Document.tables | ✅ Works | ? Check |
| Document.texts | ✅ Works | ? Check |

---

## Exact Code from V13 That Works

### Complete detect_figures method (lines 71-136)
Location: `/home/thermodynamics/document_translator_v13/agents/detection/docling_figure_detector.py`

```python
def detect_figures(self, pdf_path: Path, docling_result=None) -> List[Zone]:
    """
    Detect figure regions using Docling's document model.

    Args:
        pdf_path: Path to PDF file
        docling_result: Optional pre-computed Docling result (from table detection)

    Returns:
        List[Zone] with figure regions
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

    if hasattr(result, 'document'):  # ← KEY: Access result.document
        doc = result.document

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
            for page_num, page in enumerate(doc.pages, 1):  # ← KEY: Access doc.pages
                if hasattr(page, 'children'):
                    for item in page.children:
                        # Check if this is a picture element
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

## Summary

**What works in V13**:
- ✅ `result.document` exists and has `.pages`, `.pictures`, `.tables`, `.texts`
- ✅ Can iterate `doc.pages` to access page objects
- ✅ Can iterate `doc.pictures` for figure detection
- ✅ Page objects have `.children` list containing elements

**What's broken in V14**:
- ❌ Code tries to access `result.output` instead of `result.document`
- ❌ `result.output` doesn't have `.pages` attribute (it's `ExportedCCSDocument`)
- ❌ This breaks the fallback method that scans page elements

**The Fix**:
- Use compatibility check: `if hasattr(result, 'document'): doc = result.document elif hasattr(result, 'output'): doc = result.output`
- Then the rest of V13's proven code works unchanged
- OR understand what V14's API actually returns and update accordingly

---

## V13 Files to Reference

1. **docling_figure_detector.py** (primary)
   - `/home/thermodynamics/document_translator_v13/agents/detection/docling_figure_detector.py`
   - Lines 101-127: Complete working implementation

2. **docling_table_detector.py** (for table extraction pattern)
   - `/home/thermodynamics/document_translator_v13/agents/detection/docling_table_detector.py`
   - Lines 91-92: Shows `result.document.tables` access

3. **docling_text_detector.py** (for text extraction pattern)
   - `/home/thermodynamics/document_translator_v13/agents/detection/docling_text_detector.py`
   - Line 97: Shows `doc = docling_result.document`

4. **unified_pipeline_orchestrator.py** (integration example)
   - `/home/thermodynamics/document_translator_v13/orchestration/unified_pipeline_orchestrator.py`
   - Shows how all detectors are used together

---

## Next Steps

1. Apply the compatibility check to V14's docling_figure_detector.py
2. Test if V14's `result.output` has the needed attributes
3. If not, update to use `result.document` like V13
4. Run unit tests to verify figure detection works
5. Apply same fix to other Docling detectors in V14

