# Figure Extraction Pipeline - AI Instance Memory

**Pipeline**: `rag_extraction_v14_P16` (RAG Extraction Package)
**Component**: Figure Extraction Agent
**Last Updated**: 2025-11-16
**AI Scope**: Figure extraction ONLY (no equations, tables, or text)

---

## 🎯 PURPOSE OF THIS AI INSTANCE

This AI instance is **dedicated exclusively** to figure extraction. It should:
- ✅ Know everything about figure detection, classification, and caption extraction
- ✅ Remember plot vs image classification algorithms
- ✅ Track figure extraction success rates across different types
- ❌ NOT track equation extraction, table parsing, or text chunking
- ❌ NOT carry context about other pipelines

**Context Budget**: Small, focused, deep expertise in figures only.

---

## 🖼️ FIGURE EXTRACTION DOMAIN KNOWLEDGE

### Current Status (2025-11-16)

**Detection**: Disabled in latest test (intentional)
- Figure extraction was not enabled in full document test
- Previous tests showed 47-49 figures detected in Chapter 4
- Detection methods available: Docling figures, YOLO (disabled)

**Expected Figures in Chapter 4**:
- Reference inventory: 43 unique figures mentioned in text
- Range: Figure 1 through Figure 41
- Actual figures may be fewer (some references may be to external sources)

### Figure Types in Technical Documents

**Data Plots** (majority in Chapter 4):
- Line graphs (temperature profiles, heat flux curves)
- Bar charts (comparison data)
- Scatter plots (experimental data)
- Characteristics: Grid lines, axes, data points, legends
- Extraction goal: Digitize data points for reuse

**Diagrams**:
- Circuit diagrams (thermal resistance networks - in tables!)
- Geometry diagrams (heat transfer configurations)
- Flowcharts (process flows)
- Characteristics: Shapes, connectors, labels
- Extraction goal: Preserve visual structure + labels

**Photographs/Images**:
- Equipment photos
- Material samples
- Experimental setups
- Characteristics: Continuous tone, no structured data
- Extraction goal: Image + caption only

---

## 🔧 TECHNICAL IMPLEMENTATION

### Agent Location
```
pipelines/rag_ingestion/packages/rag_extraction_v14_P16/
├── src/
│   └── figures/
│       └── figure_extraction_agent.py
└── tests/
```

### Detection Methods Available

**1. Docling Figure Detection**:
```python
# Uses Docling's built-in figure detection
# Result: Figure zones with bboxes
# Issue: May not distinguish plot vs image vs diagram
```

**2. YOLO Figure Detection** (currently disabled):
```python
# Could use DocLayout-YOLO for figure detection
# Classes: 'figure', 'figure_caption'
# Currently disabled to focus on equations/tables first
```

**3. Caption-Based Detection** (v13 approach):
```python
# Search for "Figure N" captions in text
# Crop region above/below caption
# Worked well in v13 (100% success on 41 figures)
```

### Classification Algorithm

**Plot vs Image Classifier** (7 features):
1. **Grid lines** (35% weight) - Plots have gridlines
2. **Axes** (30% weight) - Coordinate systems
3. **Curves/Lines** (25% weight) - Data plots
4. **Text density** (10% weight) - Axis labels
5. Edge complexity
6. Texture variance
7. Color distribution

**Classification Thresholds**:
- Plot score > 0.55 → "plot" (data-extractable)
- Image score > 0.50 → "image" (visual-only)
- Otherwise → "uncertain" (manual review)

**Previous Results** (47 figures):
- 47 classified as "plot"
- 0 classified as "image"
- 0 uncertain
- Likely over-classifying as "plot" - needs tuning

---

## 🚨 CURRENT PRIORITIES

### 1. Re-Enable Figure Detection
**Status**: Disabled in latest test
**Action**:
- Enable Docling figure detection in orchestrator
- OR enable YOLO figure detection
- OR use caption-based approach (most reliable in v13)

### 2. Improve Classification Accuracy
**Problem**: Previous test classified all 47 figures as "plot"
**Likely**: Some are diagrams or photos, not data plots
**Solution**:
- Refine classification thresholds
- Add "diagram" category (structured shapes + connectors)
- Manual validation of classifications

### 3. Caption Extraction
**Goal**: Extract "Figure N: Description" captions
**Methods**:
- Docling caption detection (paired with figure zones)
- Text search for "Figure N" pattern
- Proximity-based pairing (caption near figure)

**Challenges**:
- Multi-line captions
- Captions spanning columns
- Figures without captions

---

## 📊 EXTRACTION REQUIREMENTS (By Figure Type)

### For Data Plots:
**Required**:
- Image file (PNG, high resolution)
- Caption text
- Data points (digitized from plot)
- Axis labels and units
- Legend information

**Output Format**:
```json
{
  "figure_id": "5",
  "type": "plot",
  "caption": "Temperature distribution in composite wall",
  "image_file": "figure_5.png",
  "data_points": [...],
  "x_axis": {"label": "Distance (m)", "range": [0, 0.5]},
  "y_axis": {"label": "Temperature (°C)", "range": [0, 100]}
}
```

### For Diagrams:
**Required**:
- Image file (PNG or SVG if possible)
- Caption text
- Component labels extracted
- Relationships identified

### For Photos/Images:
**Required**:
- Image file (high quality PNG)
- Caption text
- Descriptive tags

---

## 🔍 KNOWN EDGE CASES

### 1. Embedded Diagrams in Tables
**Example**: Tables 4, 5, 6 have circuit/geometry diagrams
**Problem**: Classified as tables, but contain figure-like content
**Current handling**: Embedded in table extraction output
**Future**: Could extract diagrams separately

### 2. Multi-Part Figures
**Example**: Figure 8a, Figure 8b (related subfigures)
**Challenge**: Detect as separate or combined?
**Current approach**: Detect as separate figures

### 3. Figure References vs Actual Figures
**Problem**: Text mentions "Figure 40" but it's in another chapter
**Solution**: Cross-reference detected figures with text references
**Expected**: ~43 references, but may be < 43 actual figures in chapter

---

## 🧪 TESTING WORKFLOW

### Enable Figure Detection
```python
# In unified_pipeline_orchestrator.py
# Set enable_yolo_figures=True or enable_docling_figures=True
```

### Run Extraction
```bash
./venv/bin/python test_with_unified_orchestrator.py
```

### Validate Results
```bash
# Check figure output
ls -lh test_output_orchestrator/figures/
# Should see ~40-43 figure PNG files

# Check classification results
cat test_output_orchestrator/figures_classification.json | jq '.[] | .classification'
```

---

## 📁 RELATED FILES

### This Pipeline Only
- `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/src/figures/figure_extraction_agent.py`
- `pipelines/extraction/packages/detection_v14_P14/src/docling/docling_figure_detector.py`

### v13 Reference (Proven Working Approach)
- `/home/thermodynamics/document_translator_v13/agents/extraction/figure_extractor.py` (caption-based, 100% success)

### Test Results
- `test_output_orchestrator/figures/` - Latest extraction (when enabled)
- Previous test: 47 figures detected, all classified as "plot"

---

## 🚫 OUT OF SCOPE FOR THIS AI

This AI should **NOT** track or remember:
- Equation extraction (different content type)
- Table extraction (different content type)
- Text chunking (different content type)
- Detection algorithms (different package)
- v9/v10/v11/v13 migration history
- Data plotting libraries (that's for analysis, not extraction)

**Keep this AI focused on figure extraction only.**

---

## 📝 STATUS TRACKING

**Current Status**: INACTIVE (figure detection disabled)
**Last Task**: None (awaiting re-enablement)
**Next Action**: Re-enable figure detection in orchestrator

**Status File**: `STATUS_FIGURES.json` (for inter-AI communication)

---

*This CLAUDE.md file is specific to the figure extraction pipeline AI instance. Other content types have their own dedicated AI instances.*
