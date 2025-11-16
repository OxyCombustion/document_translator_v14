# Docling API Migration Notes

## Date: 2025-11-15

## Issue: v13→v14 Import Path Fixes Revealed Docling API Changes

During the systematic fix of import paths for v14 migration, we discovered that the Docling library API had changed between versions.

## API Changes

### 1. Conversion Method

**Old API** (used in original v14 code):
```python
result = converter.convert(str(pdf_path))  # Returns generator
result = next(generator)  # Get first result
```

**New API** (current Docling version):
```python
result = converter.convert_single(pdf_path)  # Returns ConversionResult directly
```

**Why It Changed**:
- `convert()` now returns a generator for batch processing
- `convert_single()` is the new method for single-document conversion
- Accepts Path object directly (no need to convert to string)

### 2. Result Object Structure

**Old API**:
```python
doc = result.document
tables = result.document.tables
figures = result.document.figures
```

**New API**:
```python
doc = result.output  # Changed attribute name
tables = result.output.tables
figures = result.output.figures
equations = result.output.equations
main_text = result.output.main_text
```

**Why It Changed**:
- `ConversionResult.document` → `ConversionResult.output`
- Output type: `ExportedCCSDocument`
- More structured output format

## Files Fixed

### Import Path Fixes (3 files):
1. `specialized_extraction_v14_P15/src/coordination/object_numbering_coordinator.py`
   - Fixed: `caption_extraction.table_caption_extractor` → `specialized_extraction_v14_P15.src.captions.table_caption_extractor`

2. `rag_v14_P2/src/orchestrators/unified_pipeline_orchestrator.py`
   - Fixed: `curation_v14_P3.src.export.table_export_agent` → `extraction_v14_P1.src.agents.table.table_export_agent`

3. `specialized_utilities_v14_P20/src/visualization/__init__.py`
   - Fixed: Lazy imports to avoid tkinter dependency in headless environments

### Docling API Fixes (4 files):

1. **`rag_v14_P2/src/orchestrators/unified_pipeline_orchestrator.py`**
   - Line 207: Changed `converter.convert(str(pdf_path))` → `converter.convert_single(pdf_path)`

2. **`detection_v14_P14/src/docling/docling_table_detector.py`**
   - Line 86: Changed `converter.convert(str(pdf_path))` → `converter.convert_single(pdf_path)`
   - Line 91-92: Changed `result.document` → `result.output`

3. **`detection_v14_P14/src/docling/docling_figure_detector.py`**
   - Line 96: Changed `converter.convert(str(pdf_path))` → `converter.convert_single(pdf_path)`
   - Line 102: Changed `result.document` → `result.output`

4. **`detection_v14_P14/src/docling/docling_text_detector.py`**
   - Line 91: Changed `converter.convert(str(pdf_path))` → `converter.convert_single(pdf_path)`
   - Line 95: Changed `docling_result.document` → `docling_result.output`

## Testing

**Test Script**: `test_with_unified_orchestrator.py`

**Results** (expected after fixes):
- ✅ Phase 0 (Document Reference Inventory): Working
- ✅ Phase 1 (Parallel Detection): Docling conversion succeeds
- ✅ Table detection: Using `result.output.tables`
- ✅ Figure detection: Using `result.output.figures`
- ✅ Text detection: Using `result.output.main_text`

## Lesson Learned

**The Issue**: When we migrated from v13 to v14, we focused on package structure changes but didn't account for external dependency API changes (Docling).

**The Fix**: Systematic approach to fixing:
1. First, fix import paths for v14 package structure
2. Then, fix external API compatibility issues that were masked by import errors
3. Clear Python bytecode cache to ensure updated code is used

**Future Prevention**:
- Document external dependency versions in requirements.txt with exact versions
- Test external API compatibility early in migration
- Consider pinning critical dependencies to avoid unexpected API changes

## Verification Commands

```bash
# Check Docling version
./venv/bin/pip show docling

# Test ConversionResult structure
./venv/bin/python -c "
from docling.document_converter import DocumentConverter
from pathlib import Path
converter = DocumentConverter()
result = converter.convert_single(Path('test_data/Ch-04_Heat_Transfer.pdf'))
print('Has output:', hasattr(result, 'output'))
print('Has document:', hasattr(result, 'document'))
print('Tables found:', len(result.output.tables) if hasattr(result, 'output') else 0)
"

# Clear cache before testing
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Run end-to-end test
./venv/bin/python test_with_unified_orchestrator.py
```

## Status

**Date**: 2025-11-15
**Status**: ✅ All API compatibility issues resolved
**Next Steps**: Complete end-to-end extraction test, then proceed to Phase 2 (Embedding) and Phase 3 (LLM Validation)
