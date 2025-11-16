# Docling API Compatibility: V13 vs V14 Analysis

## Summary
The v14 code is using an outdated/incorrect Docling API. The v13 code shows the **working pattern** that should be used.

## The Core Problem

**V14 (BROKEN)**:
```python
# Line 96 - WRONG METHOD
result = self.converter.convert_single(pdf_path)

# Line 101-102 - WRONG ATTRIBUTE PATH
if hasattr(result, 'output'):
    doc = result.output  # ❌ This attribute doesn't exist!
    
# Line 117 - THEN TRIES TO USE NON-EXISTENT .pages
for page_num, page in enumerate(doc.pages, 1):  # ❌ AttributeError
```

**V13 (WORKING)**:
```python
# Line 96 - CORRECT METHOD
result = self.converter.convert(str(pdf_path))

# Line 101-102 - CORRECT ATTRIBUTE PATH
if hasattr(result, 'document'):
    doc = result.document  # ✅ This is the correct attribute!
    
# Line 117 - THEN USES .pages CORRECTLY
for page_num, page in enumerate(doc.pages, 1):  # ✅ Works!
```

---

## Working Pattern from V13

### Step 1: Convert Document (Correct)
```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert(str(pdf_path))  # ← Use .convert(), NOT .convert_single()
```

### Step 2: Access Document (Correct)
```python
# Result structure: ConversionResult
#  ├── document: DoclingDocument (THIS IS WHAT WE NEED)
#  ├── ...other fields

doc = result.document  # ← Use .document, NOT .output
```

### Step 3: Access Pages (Correct)
```python
# DoclingDocument has .pages attribute
for page_num, page in enumerate(doc.pages, 1):
    print(f"Page {page_num}: {page}")
    
# Also available:
# - doc.pictures - List of pictures in document
# - doc.tables - List of tables
# - doc.texts - List of text blocks
```

### Complete Working Pattern
```python
# From v13/agents/detection/docling_figure_detector.py (lines 90-117)

# Use provided result or run conversion
if docling_result:
    print("Using existing Docling result (from table detection)...")
    result = docling_result
else:
    print("Running Docling conversion...")
    result = self.converter.convert(str(pdf_path))  # ✅ .convert()

# Extract figure zones from Docling's document model
zones = []

if hasattr(result, 'document'):  # ✅ Check for .document
    doc = result.document  # ✅ Get .document

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
        for page_num, page in enumerate(doc.pages, 1):  # ✅ .pages works here
            if hasattr(page, 'children'):
                for item in page.children:
                    # Process picture items...
```

---

## Document Structure (V13 - Correct)

```
result = converter.convert(pdf_path)
  └── result.document (DoclingDocument) ← THIS IS THE KEY
      ├── .pages (List of pages)
      │   └── page.children (Elements on that page)
      ├── .pictures (Direct picture collection)
      ├── .tables (Direct table collection)
      │   └── table.export_to_markdown()
      │   └── table.export_to_dataframe()
      ├── .texts (Direct text blocks)
      ├── export_to_text()
      ├── export_to_markdown()
      └── prov (Provenance/location info)
```

---

## V13 Files Using Correct Pattern

1. **`agents/detection/docling_figure_detector.py`**
   - Uses: `result.document` ✅
   - Uses: `doc.pages` ✅
   - Uses: `enumerate(doc.pages, 1)` ✅
   - Status: WORKING

2. **`agents/detection/docling_table_detector.py`**
   - Uses: `result.document` ✅
   - Uses: `result.document.tables` ✅
   - Uses: `table.export_to_markdown()` ✅
   - Status: WORKING

3. **`agents/detection/docling_text_detector.py`**
   - Uses: `docling_result.document` ✅
   - Uses: `doc.texts` ✅
   - Status: WORKING

4. **`core/docling_extractor.py`**
   - Uses: `result = self.converter.convert(str(pdf_path))` ✅
   - Uses: `doc = result.document` ✅
   - Uses: `doc.tables` ✅
   - Status: WORKING

---

## V14 Error Analysis

**File**: `/home/thermodynamics/document_translator_v14/detection_v14_P14/src/docling/docling_figure_detector.py`

**Error Location**: Line 117
```
AttributeError: 'ExportedCCSDocument' object has no attribute 'pages'
```

**Root Cause Chain**:
1. Line 96: `result = self.converter.convert_single(pdf_path)` ← WRONG METHOD
2. Line 101-102: Checks `hasattr(result, 'output')` ← WRONG ATTRIBUTE
3. Line 102: `doc = result.output` ← Gets wrong object
4. Line 117: `for page_num, page in enumerate(doc.pages, 1):` ← Tries to access `.pages` on wrong object
5. Object returned is `ExportedCCSDocument` NOT `DoclingDocument`

---

## Fix Required

**In V14 `docling_figure_detector.py`**:

Replace lines 96 and 101-102:
```python
# OLD (BROKEN):
result = self.converter.convert_single(pdf_path)  # ❌
if hasattr(result, 'output'):  # ❌
    doc = result.output  # ❌

# NEW (CORRECT - from V13):
result = self.converter.convert(str(pdf_path))  # ✅
if hasattr(result, 'document'):  # ✅
    doc = result.document  # ✅
```

That's it! The rest of the code (lines 105-127) will work correctly once you have the right `doc` object.

---

## Key Takeaways

1. **Method**: Use `.convert()` not `.convert_single()`
2. **Attribute**: Use `.document` not `.output`
3. **Pages Access**: Use `doc.pages` (available after getting `.document`)
4. **Element Type**: You'll get `DoclingDocument` not `ExportedCCSDocument`
5. **Proof**: All 4 v13 files using this pattern work correctly

---

## Reference Files from V13

**Docling Figure Detector** (WORKING):
- File: `/home/thermodynamics/document_translator_v13/agents/detection/docling_figure_detector.py`
- Key lines: 90-117
- Pattern: `result.converter.convert(str(path))` → `result.document` → `doc.pages`

**Docling Table Detector** (WORKING):
- File: `/home/thermodynamics/document_translator_v13/agents/detection/docling_table_detector.py`
- Key lines: 80-92
- Pattern: `result.converter.convert(str(path))` → `result.document` → `result.document.tables`

**Docling Extractor** (WORKING):
- File: `/home/thermodynamics/document_translator_v13/core/docling_extractor.py`
- Key lines: 89-90
- Pattern: `result = self.converter.convert(str(pdf_path))` → `doc = result.document`
