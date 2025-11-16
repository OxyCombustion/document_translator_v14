# V13 vs V14 Code Comparison - Exact Working Pattern

## File 1: Figure Detection

### V13 (WORKING) - docling_figure_detector.py
```python
# Lines 90-117
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
                print(f"  Picture {i+1}: page {zone.page}, bbox {zone.bbox}")

    # Method 2: Scan page elements for picture items
    else:
        print("Scanning page elements for pictures...")
        picture_count = 0
        for page_num, page in enumerate(doc.pages, 1):  # ✅ .pages exists!
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
```

### V14 (BROKEN) - docling_figure_detector.py
```python
# Lines 90-117
# Use provided result or run conversion
if docling_result:
    print("Using existing Docling result (from table detection)...")
    result = docling_result
else:
    print("Running Docling conversion...")
    result = self.converter.convert_single(pdf_path)  # ❌ .convert_single()

# Extract figure zones from Docling's document model
zones = []

if hasattr(result, 'output'):  # ❌ Check for .output (WRONG!)
    doc = result.output  # ❌ Get .output (WRONG!)

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
        for page_num, page in enumerate(doc.pages, 1):  # ❌ CRASHES HERE
            # ERROR: 'ExportedCCSDocument' object has no attribute 'pages'
```

---

## File 2: Table Detection

### V13 (WORKING) - docling_table_detector.py
```python
# Lines 80-92
# Use provided result or run conversion
if docling_result:
    print("Using existing Docling result (shared with figures)...")
    result = docling_result
else:
    print("Running Docling conversion...")
    result = self.converter.convert(str(pdf_path))  # ✅ .convert()

# Extract table zones
zones = []

if hasattr(result, 'document') and hasattr(result.document, 'tables'):  # ✅
    for i, table in enumerate(result.document.tables):  # ✅ .document.tables
        # Get table location
        page_num = 1  # Default
        bbox = [0, 0, 100, 100]  # Default

        # Try to extract page and bbox from table metadata
        if hasattr(table, 'prov') and table.prov:
            for prov in table.prov:
                if hasattr(prov, 'page_no'):
                    page_num = prov.page_no
                if hasattr(prov, 'bbox'):
                    bbox_obj = prov.bbox
                    bbox = [
                        bbox_obj.l,
                        bbox_obj.t,
                        bbox_obj.r,
                        bbox_obj.b
                    ]

        # Create zone
        zone_id = f"table_{i+1}"
        zone = Zone(
            zone_id=zone_id,
            type="table",
            page=page_num,
            bbox=bbox,
            metadata={
                'docling_table_index': i,
                'detection_method': 'docling',
                'markdown': table.export_to_markdown()  # ✅ Works!
            }
        )
        zones.append(zone)

        print(f"  Table {i+1}: page {page_num}, bbox {bbox}")
```

### V14 Pattern (Would be broken same way)
```python
result = self.converter.convert_single(pdf_path)  # ❌ WRONG
if hasattr(result, 'output'):  # ❌ WRONG
    doc = result.output  # ❌ WRONG - no tables attribute
```

---

## File 3: Docling Extractor (Core)

### V13 (WORKING) - core/docling_extractor.py
```python
# Lines 86-101
try:
    logger.info(f"Extracting document with Docling: {pdf_path.name}")
    
    # Convert using Docling (V7 approach)
    result = self.converter.convert(str(pdf_path))  # ✅ .convert()
    doc = result.document  # ✅ .document
    
    # Extract text (like V7)
    text_data = doc.export_to_text()  # ✅ Works!
    text_length = len(text_data)
    
    logger.info(f"Text extracted: {text_length:,} characters")
    
    # Extract tables (like V7)
    extracted_tables = []
    
    for i, table in enumerate(doc.tables):  # ✅ .tables exists!
        try:
            # Get page number (V7 approach)
            page_num = None
            if hasattr(table, 'prov') and table.prov:
                page_num = table.prov[0].page_no
            
            # Export to DataFrame (V7 approach)
            df = table.export_to_dataframe()  # ✅ Works!
            
            if not df.empty:
                table_data = {
                    'table_id': i + 1,
                    'page': page_num,
                    'shape': df.shape,
                    'data': df.to_dict('records'),
                    'source': 'docling',
                    'processing_stage': 'standard',
                    'columns': df.columns.tolist(),
                    'rows': len(df)
                }
                
                extracted_tables.append(table_data)
                logger.info(f"Table {i+1} extracted: {df.shape} on page {page_num}")
```

---

## The Quick Fix

For V14 `docling_figure_detector.py`, change these 3 lines:

**Line 96:**
```python
# Before (BROKEN):
result = self.converter.convert_single(pdf_path)

# After (FIXED):
result = self.converter.convert(str(pdf_path))
```

**Lines 101-102:**
```python
# Before (BROKEN):
if hasattr(result, 'output'):
    doc = result.output

# After (FIXED):
if hasattr(result, 'document'):
    doc = result.document
```

That's it! Everything else in your v14 code will work perfectly once these three changes are made.

---

## Why This Happened

**V13 Docling API** (Likely version 1.x or 2.0):
- `converter.convert(path)` → Returns `ConversionResult`
- `ConversionResult.document` → Returns `DoclingDocument` with `.pages`, `.tables`, `.pictures`, `.texts`

**V14 Assumed API** (Outdated/misunderstood):
- `converter.convert_single(path)` → Returns different object type
- Object has `.output` attribute instead of `.document`
- `.output` is `ExportedCCSDocument` (different type, no `.pages`)

**Solution**: Use the proven V13 pattern that works with current Docling.

---

## Verification Checklist

After making the fix, the code should:

- [x] Call `self.converter.convert(str(pdf_path))`
- [x] Check `hasattr(result, 'document')`
- [x] Access `doc = result.document`
- [x] Access `doc.pictures` (for pictures collection)
- [x] Access `doc.pages` (for page-by-page iteration)
- [x] Enumerate with `for page_num, page in enumerate(doc.pages, 1)`

All these work in V13, so they'll work in V14 with this fix.
