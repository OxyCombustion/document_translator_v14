# Table Extraction Pipeline - AI Instance Memory

**Pipeline**: `rag_extraction_v14_P16` (RAG Extraction Package)
**Component**: Table Extraction Agent
**Last Updated**: 2025-11-16
**AI Scope**: Table extraction ONLY (no equations, figures, or other pipelines)

---

## 🎯 PURPOSE OF THIS AI INSTANCE

This AI instance is **dedicated exclusively** to table extraction. It should:
- ✅ Know everything about table extraction edge cases
- ✅ Remember Docling markdown parsing quirks
- ✅ Track which tables work and which fail
- ❌ NOT track equation extraction, detection, or other pipelines
- ❌ NOT carry context about v9, v10, v11, v13 migrations

**Context Budget**: Small, focused, deep expertise in tables only.

---

## 📊 TABLE EXTRACTION DOMAIN KNOWLEDGE

### Known Table Types in Chapter 4

**Text-Based Tables (Docling Works Well)**:
1. **Table 1** - Thermal Conductivity (9 rows) ✅
2. **Table 2** - Convective Heat Transfer Coefficients (8 rows) ⚠️ CURRENTLY FAILING
3. **Table 3** - Emissivity Values (6 rows) ✅
4. **Table 7** - Properties of Various Substances (30 rows) ✅
5. **Table 8a** - Gas Properties Part A (54 rows) ✅
6. **Table 8b** - Gas Properties Part B (37 rows) ✅
7. **Table 10** - Overall Heat Transfer Coefficients (11 rows) ✅
8. **Table 11** - Fouling Factors (8 rows) ✅
9. **Page 15 Table** - Free Convection (4 rows) ✅

**Image-Embedded Tables (Docling Cannot Extract)**:
- **Table 4** - Thermal Resistances (has circuit diagrams)
- **Table 5** - Network Equivalents (has circuit diagrams)
- **Table 6** - Gray Enclosures (has geometry diagrams)
- **Table 9** - Emissivity (26 rows, no images but extraction issues)

### v13 Production Results (Ground Truth)

**From v13 Guide** (`/home/thermodynamics/document_translator_v13/guides/TABLE_EXTRACTION_PIPELINE_GUIDE.md`):
- **13/13 tables extracted** successfully in v13
- **9 embedded diagrams** (Tables 4, 5, 6)
- **10 tables with notes** extracted
- **Hybrid strategy**: Docling (text) + October manual extraction (images)

**v13 Success Rate**:
- Docling: 9/13 tables (69% - text-based only)
- October manual: 4/13 tables (31% - image-embedded)
- Combined: 13/13 (100%)

---

## 🚨 CURRENT ISSUE: Table 2 Extraction Failure

### Problem Statement
**Table 2** on page 7 (PDF page 2 in subset) is failing extraction:
- Docling **detects** the bbox correctly
- Docling returns **empty markdown** (0 chars)
- `table.data.table_cells = []`
- `table.data.num_rows = 0`
- `table.data.num_cols = 0`

### v13 vs v14 Comparison
- **v13**: Successfully extracted Table 2 (8 rows, "Convective Heat Transfer Coefficients")
- **v14**: Failing with "Too few lines after cleaning: 1"

### Investigation Status
- ✅ Metadata contract fixed (html → markdown) in commit fd9924a
- ✅ Extraction agent identical between v13 (813 lines) and v14 (812 lines)
- ⚠️ **Root cause**: Docling returning empty table data for Table 2
- 🔍 **Next step**: Determine if this is a Docling version difference or configuration issue

---

## 🔧 TECHNICAL IMPLEMENTATION

### Agent Location
```
pipelines/rag_ingestion/packages/rag_extraction_v14_P16/
├── src/
│   └── tables/
│       └── table_extraction_agent.py  (812 lines)
└── tests/
```

### Key Methods

**`_parse_markdown_table(markdown: str)`** (Line ~200):
- Parses Docling markdown into pandas DataFrame
- Handles repeated caption rows
- Cleans alignment separators (`|---|---|`)
- **Critical threshold**: Needs ≥2 lines (header + 1 data row)

**Known Edge Cases**:
1. **Repeated Caption Rows**: Docling sometimes duplicates table captions
   - Detection: Line starts with "Table N"
   - Solution: Skip duplicate rows

2. **Alignment Separators**: Markdown table alignment markers
   - Pattern: `^\s*\|[\s\-|]+\|`
   - Solution: Filter out before parsing

3. **Empty Tables**: Docling detects bbox but returns no data
   - Current failure mode for Table 2
   - Need fallback extraction strategy

### Metadata Contract

**Zone metadata required** (from detector):
```python
zone.metadata = {
    'docling_table_index': int,
    'detection_method': 'docling',
    'markdown': str  # ← MUST be 'markdown', not 'html'
}
```

**Recent fix** (commit fd9924a): Changed detector from providing 'html' to 'markdown'

---

## 📁 RELATED FILES

### This Pipeline Only
- `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/src/tables/table_extraction_agent.py`
- `pipelines/extraction/packages/detection_v14_P14/src/docling/docling_table_detector.py`

### v13 Reference (Read-Only)
- `/home/thermodynamics/document_translator_v13/guides/TABLE_EXTRACTION_PIPELINE_GUIDE.md`
- `/home/thermodynamics/document_translator_v13/agents/rag_extraction/table_extraction_agent.py`

### Test Files
- `test_data/Ch-04_Heat_Transfer_subset.pdf` (4 pages: 2, 7, 8, 32)
- `test_subset_tables.py` (fast validation script)

---

## 🧪 TESTING WORKFLOW

### Fast Iteration (4-page subset)
```bash
# Create subset PDF (if needed)
./venv/bin/python create_test_subset.py

# Run subset test (~2 minutes vs 7 minutes full doc)
./venv/bin/python test_subset_tables.py

# Expected: 3 tables (Table 1, Table 4, Table 5)
# Currently: 1/3 tables (33% - Table 1 only)
```

### Debug Specific Table
```bash
# Inspect what Docling provides for Table 2
./venv/bin/python debug_table2_markdown.py

# Check both markdown and HTML
./venv/bin/python debug_table2_html.py
```

---

## 🎯 IMMEDIATE PRIORITIES

1. **Root Cause Table 2 Failure**
   - Why does Docling return empty table data?
   - Is this a Docling version difference (v13 vs v14)?
   - Is this a configuration issue?

2. **Verify v13 Extraction Method**
   - Did v13 use a different Docling configuration?
   - Did v13 use a fallback extraction method?
   - Check v13 session notes for Table 2 specifically

3. **Implement Fallback Strategy**
   - If Docling markdown is empty, try HTML
   - If both empty, use vision OCR as last resort
   - Document which tables require which method

---

## 📖 GIT HISTORY

### Recent Commits (v14)
- `fd9924a` - fix: Change table metadata from html to markdown
- `4f20e34` - fix: Implement equation number extraction (DIFFERENT PIPELINE)

### v13 Reference
- v13 successfully extracted 13/13 tables
- Hybrid approach: Docling + manual extraction
- Production validated by user as "outstanding"

---

## 🚫 OUT OF SCOPE FOR THIS AI

This AI should **NOT** track or remember:
- Equation extraction (different pipeline)
- Figure extraction (different pipeline)
- Detection algorithms (different package)
- v9/v10/v11 migration history (not relevant)
- RAG chunking strategies (different pipeline)
- Database curation (different pipeline)

**Keep this AI focused on tables only.**

---

*This CLAUDE.md file is specific to the table extraction pipeline AI instance. Other pipelines have their own dedicated AI instances with separate CLAUDE.md files.*
