# Equation Extraction Pipeline - AI Instance Memory

**Pipeline**: `rag_extraction_v14_P16` (RAG Extraction Package)
**Component**: Equation Extraction Agent
**Last Updated**: 2025-11-16
**AI Scope**: Equation extraction ONLY (no tables, figures, or other content types)

---

## 🎯 PURPOSE OF THIS AI INSTANCE

This AI instance is **dedicated exclusively** to equation extraction. It should:
- ✅ Know everything about LaTeX-OCR, equation numbering, and pairing
- ✅ Remember YOLO detection configurations for equations
- ✅ Track equation extraction success rates and failure modes
- ❌ NOT track table extraction, figure classification, or text chunking
- ❌ NOT carry context about other pipelines

**Context Budget**: Small, focused, deep expertise in equations only.

---

## 📐 EQUATION EXTRACTION DOMAIN KNOWLEDGE

### Current Results (2025-11-16 Test)

**Detection**:
- YOLO detected equations on 30/34 pages
- Total detections: 258+ equation zones across document
- Detection method: `isolate_formula` + `formula_caption` from DocLayout-YOLO

**Extraction**:
- ✅ **107/133 equations extracted** (80.5% success rate)
- ❌ **26 missing equations** (mostly false positives - high numbers like 149, 189, 260, etc.)
- Grade: C (good, but room for improvement)

### Known Equation Types in Chapter 4

**Simple Single-Line Equations** (majority):
- Example: `q = kA/L (T1 - T2)` - Heat conduction equation
- LaTeX-OCR handles these well
- Success rate: ~90%

**Multi-Line Equations**:
- Example: Equation 80 (9 lines, 236px height)
- Requires adaptive crop sizing
- Success rate: ~70% (needs improvement)

**Numbered Equations**:
- Format: `(1)`, `(2)`, etc.
- Pairing: Equation image + equation number
- Current pairing method: Spatial proximity (number right of equation)

**Unnumbered Equations**:
- No explicit reference in text
- Still need extraction for completeness
- Challenge: How to identify and label?

### False Positives (High-Priority Fix)

**Problem**: Reference inventory finds 133 "equations" but many are text references
- Numbers like `(149)`, `(189)`, `(260)` appear in prose as citations
- Not actual equation numbers
- Inflates "expected count" and deflates success rate

**Solution**: Improve reference inventory to distinguish:
- Real equation references: "Using Equation (5)" or "From (5) we get"
- False positives: "pressure of 149 kPa" or "at 189°C"

---

## 🔧 TECHNICAL IMPLEMENTATION

### Agent Location
```
pipelines/rag_ingestion/packages/rag_extraction_v14_P16/
├── src/
│   └── equations/
│       └── equation_extraction_agent.py
└── tests/
```

### Key Detection Method

**YOLO Detection** (DocLayout-YOLO):
- Model: `doclayout_yolo_docstructbench_imgsz1280_2501.pt`
- Classes detected:
  - `isolate_formula` - Equation content
  - `formula_caption` - Equation numbers like "(1)", "(2)"
- Confidence threshold: 0.2 (balances recall vs precision)

**Pairing Algorithm**:
```python
# Match equation numbers to equation content via spatial proximity
for formula_zone in isolate_formula_zones:
    for caption_zone in formula_caption_zones:
        if caption_is_right_of_formula(caption_zone, formula_zone):
            if distance_is_close(caption_zone, formula_zone):
                pair_them_together(formula_zone, caption_zone)
```

### LaTeX-OCR Configuration

**Library**: `pix2tex` (LaTeX-OCR with Vision Transformer)
- Input: Equation image crop (PNG, 216 DPI)
- Output: LaTeX string (e.g., `q_c = -kA \frac{dT}{dx}`)
- Model: Vision Transformer architecture
- Quality: Excellent for single-line, good for multi-line

**Current Issues**:
- Fractions sometimes garbled on complex multi-line equations
- Symbol disambiguation (e.g., lowercase L vs number 1)
- Subscript/superscript nesting on complex expressions

---

## 🚨 CURRENT PRIORITIES

### 1. Improve Reference Inventory Filtering
**Problem**: 133 "expected equations" includes ~26 false positives
**Solution**:
- Add context analysis to reference scanner
- Distinguish "Equation (5)" from "pressure (149 kPa)"
- Reduce expected count to ~107 actual equations

### 2. Investigate Missing Equations
**Current**: 107/133 extracted (80.5%)
**After filtering**: Likely ~107/107 (100% of real equations)
**Action**: Validate that all 26 "missing" are actually false positives

### 3. Multi-Line Equation Enhancement
**Problem**: Complex multi-line equations have lower success rate
**Solution**:
- Adaptive crop sizing (already partially implemented)
- Better handling of equation components spread across lines
- Possible use of Docling formula enrichment (if available)

---

## 📊 EXTRACTION STATISTICS (Latest Test)

```
Test Date: 2025-11-16
Document: Ch-04_Heat_Transfer.pdf (34 pages)

Detection Phase:
- YOLO model load: ~1.5s
- Page detection: ~3-5s per page
- Total detection time: ~39.6s
- Zones created: 108 equation zones

Extraction Phase:
- LaTeX-OCR per equation: ~0.5-2s
- Total extraction time: ~553.9s
- Equations extracted: 107
- Success rate: 99.1% (107/108 zones)

Quality:
- LaTeX validity: 100% (all valid LaTeX syntax)
- Content accuracy: Needs manual validation
- Completeness: Good (single-line), Fair (multi-line)
```

---

## 🔍 KNOWN EDGE CASES

### 1. Equation Numbering Variants
- Standard: `(1)`, `(2)`, `(3)`
- Letter suffixes: `(79a)`, `(79b)` - YOLO handles these
- Unusual: `[1]`, `Eq. 1` - Not currently detected

### 2. Inline vs Display Equations
- Display equations: Centered, numbered - ✅ Detected well
- Inline equations: Within text paragraphs - ❌ Not detected
- Current focus: Display equations only

### 3. Equation Components
- Main equation: `q = kA/L (T1 - T2)`
- Variable definitions: `where k = thermal conductivity`
- Current handling: Main equation only, definitions separate

---

## 🧪 TESTING WORKFLOW

### Quick Validation
```bash
# Check equation extraction on full document
ls -lh test_output_orchestrator/equations/
# Should see 107 equation image files

# Verify LaTeX output exists
cat test_output_orchestrator/equations/equations_latex.json | jq '.equations | length'
# Should output: 107
```

### Debug Specific Equation
```bash
# Find equation by number
ls test_output_orchestrator/equations/ | grep "equation_5"

# Check LaTeX for equation 5
cat test_output_orchestrator/equations/equations_latex.json | jq '.equations[] | select(.equation_number == "5")'
```

---

## 📁 RELATED FILES

### This Pipeline Only
- `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/src/equations/equation_extraction_agent.py`
- `pipelines/extraction/packages/detection_v14_P14/src/yolo/unified_yolo_detector.py` (detection)

### Reference Files
- `test_output_orchestrator/equations/` - Latest extraction results
- `test_output_orchestrator/completeness_validation.json` - Success metrics

---

## 🚫 OUT OF SCOPE FOR THIS AI

This AI should **NOT** track or remember:
- Table extraction (different content type)
- Figure extraction (different content type)
- Text chunking (different content type)
- Detection algorithms (different package - detection_v14_P14)
- v9/v10/v11/v13 migration history (not relevant)
- RAG preparation (different pipeline - rag_v14_P2)

**Keep this AI focused on equations only.**

---

## 📝 STATUS TRACKING

**Current Status**: ACTIVE
**Last Task**: Full document test (2025-11-16)
**Result**: 107/133 equations extracted (80.5%)
**Next Action**: Investigate false positives in reference inventory

**Status File**: `STATUS_EQUATIONS.json` (for inter-AI communication)

---

*This CLAUDE.md file is specific to the equation extraction pipeline AI instance. Other content types have their own dedicated AI instances with separate CLAUDE.md files.*
