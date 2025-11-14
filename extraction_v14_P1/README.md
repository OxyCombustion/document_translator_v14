# Pipeline 1: Extraction (extraction_v14_P1)

**Purpose**: PDF → Structured JSON

**Input**: Raw PDF documents
**Output**: `extraction_results_v1.json` (equations, tables, figures, text with bboxes)

## 🎯 Responsibilities

### **Detection**
- YOLO-based object detection (equations, figures, tables)
- Docling structural analysis
- PyMuPDF text extraction
- Hybrid multi-method detection

### **Extraction**
- Equation extraction (bidirectional, parallel)
- Table extraction (text-based, vision-based)
- Figure extraction (image crops, captions)
- Text extraction (semantic chunking)

### **Validation**
- Bounding box validation
- Content completeness checking
- Duplicate detection
- Quality scoring

## 📁 Directory Structure

```
extraction_v14_P1/
├── src/
│   ├── agents/
│   │   ├── detection/         # Detection agents
│   │   │   ├── yolo_detector.py
│   │   │   ├── docling_detector.py
│   │   │   └── pymupdf_detector.py
│   │   └── extraction/        # Extraction agents
│   │       ├── equation_extractor.py
│   │       ├── table_extractor.py
│   │       ├── figure_extractor.py
│   │       └── text_extractor.py
│   ├── core/
│   │   ├── pipeline.py        # Main extraction pipeline
│   │   ├── validator.py       # Output validation
│   │   └── schema.py          # Data models
│   └── utils/
│       ├── bbox_utils.py      # Bounding box utilities
│       ├── image_utils.py     # Image processing
│       └── parallel_utils.py  # Multi-core processing
├── config/
│   └── extraction_v14_P1_config.yaml
├── tests/
│   ├── test_detection.py
│   ├── test_extraction.py
│   └── test_integration.py
└── docs/
    ├── detection_methods.md
    ├── extraction_methods.md
    └── schema_reference.md
```

## 🔧 Recovered v12 Components

These working components from v12 will be integrated into this pipeline:

1. **bidirectional_equation_extractor.py** (17K)
   - Handles equation numbers before OR after mathematical content
   - Scoring algorithm for equation quality
   - Multi-line equation support

2. **parallel_equation_extractor.py** (21K)
   - Multi-core CPU optimization
   - Batch processing for page arrays
   - 1.9x speedup with perfect accuracy preservation

3. **parallel_table_extractor.py** (15K)
   - Multi-core table extraction
   - Batch processing optimization
   - Proven accuracy match to sequential

## 📊 Output Schema

### `extraction_results_v1.json`

```json
{
  "metadata": {
    "document_id": "string",
    "filename": "string",
    "pages": "integer",
    "extraction_date": "ISO-8601",
    "pipeline_version": "extraction_v14_P1",
    "schema_version": "v1"
  },
  "equations": [
    {
      "equation_id": "string",
      "page": "integer",
      "bbox": {"x0": "float", "y0": "float", "x1": "float", "y1": "float"},
      "content": "string",
      "latex": "string",
      "confidence": "float",
      "extraction_method": "string"
    }
  ],
  "tables": [
    {
      "table_id": "string",
      "page": "integer",
      "bbox": {...},
      "headers": ["string"],
      "rows": [["string"]],
      "markdown": "string",
      "confidence": "float"
    }
  ],
  "figures": [
    {
      "figure_id": "string",
      "page": "integer",
      "bbox": {...},
      "caption": "string",
      "image_path": "string",
      "confidence": "float"
    }
  ],
  "text": [
    {
      "chunk_id": "string",
      "page": "integer",
      "bbox": {...},
      "content": "string",
      "semantic_type": "string"
    }
  ]
}
```

## 🚀 Usage (After Phase 1)

### **Basic Extraction**
```python
from extraction_v14_P1 import ExtractionPipeline

pipeline = ExtractionPipeline(config_path="config/extraction_v14_P1_config.yaml")
results = pipeline.extract(pdf_path="document.pdf")

# Save results
pipeline.save_results(results, output_path="extraction_results.json")
```

### **Parallel Processing**
```python
from extraction_v14_P1 import ParallelExtractionPipeline

pipeline = ParallelExtractionPipeline(
    config_path="config/extraction_v14_P1_config.yaml",
    num_workers=8
)
results = pipeline.extract_batch(pdf_paths=["doc1.pdf", "doc2.pdf"])
```

## 🔗 Integration with Pipeline 2

**Output Contract**: Pipeline 1 produces `extraction_results_v1.json` conforming to schema `schemas/extraction/extraction_results_v1.json`.

**Pipeline 2 Consumption**: RAG preparation pipeline reads this JSON and creates semantic chunks with relationships.

## 📝 Configuration

See `config/extraction_v14_P1_config.yaml` for configuration options:
- Detection methods (enable/disable YOLO, Docling, PyMuPDF)
- Extraction parameters (thresholds, batch sizes)
- Parallel processing (number of workers)
- Output formats (JSON, JSONL, both)

## 🧪 Testing

```bash
# Unit tests
pytest tests/test_detection.py
pytest tests/test_extraction.py

# Integration tests
pytest tests/test_integration.py

# Full pipeline test
python tests/test_full_pipeline.py --input tests/data/sample.pdf
```

## 📚 Documentation

- **Detection Methods**: `docs/detection_methods.md`
- **Extraction Methods**: `docs/extraction_methods.md`
- **Schema Reference**: `docs/schema_reference.md`
- **Migration Notes**: `docs/v13_migration_notes.md`

---

**Status**: Phase 0 - Foundation setup in progress
**Next**: Phase 1 - Implement core extraction pipeline
