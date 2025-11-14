# Pipeline 2: RAG Preparation (rag_v14_P2)

**Purpose**: Structured JSON → RAG-Ready JSONL + Knowledge Graph

**Input**: `extraction_results_v1.json` (from Pipeline 1)
**Output**: `rag_bundles_v1.json` (semantic chunks, embeddings, relationships)

## 🎯 Responsibilities

### **Intelligence Analysis**
- Document structure understanding
- Content type classification
- Relationship mapping
- Semantic segmentation

### **Orchestration**
- Multi-agent scanning coordination
- Cross-validation of detection methods
- Intelligent extraction strategy selection
- Quality assessment

### **Relationship Mapping**
- Spatial relationships (proximity, reading flow)
- Semantic relationships (citations, references)
- Hierarchical relationships (sections, subsections)
- Cross-object relationships (equation ↔ table ↔ figure ↔ text)

### **RAG Optimization**
- Semantic chunking (optimal token boundaries)
- Metadata enrichment
- Context preservation
- Embedding-ready formatting

## 📁 Directory Structure

```
rag_v14_P2/
├── src/
│   ├── orchestration/         # Document orchestrators
│   │   ├── document_intelligence_scanner.py
│   │   └── dual_scanning_agent_framework.py
│   ├── analyzers/             # Intelligence analyzers
│   │   ├── equation_intelligence_analyzer.py
│   │   ├── figure_intelligence_analyzer.py
│   │   ├── table_intelligence_analyzer.py
│   │   └── text_intelligence_analyzer.py
│   ├── processors/            # Semantic processors
│   │   ├── chunker.py
│   │   ├── relationship_mapper.py
│   │   └── metadata_enricher.py
│   ├── core/
│   │   ├── pipeline.py        # Main RAG preparation pipeline
│   │   ├── validator.py       # Output validation
│   │   └── schema.py          # Data models
│   └── utils/
│       ├── semantic_utils.py  # Semantic analysis utilities
│       ├── graph_utils.py     # Knowledge graph utilities
│       └── embedding_utils.py # Embedding preparation
├── config/
│   └── rag_v14_P2_config.yaml
├── tests/
│   ├── test_orchestration.py
│   ├── test_analyzers.py
│   ├── test_processors.py
│   └── test_integration.py
└── docs/
    ├── intelligence_analysis.md
    ├── relationship_mapping.md
    └── schema_reference.md
```

## 🔧 Recovered v12 Components

These working components from v12 will be integrated into this pipeline:

### **Orchestrators** (2 components, 54K total)

1. **document_intelligence_scanner.py** (22K)
   - Phase 1 comprehensive document analysis
   - Orchestrates all 4 intelligence analyzers
   - Strategy generation for adaptive extraction
   - Document-specific parameter optimization

2. **dual_scanning_agent_framework.py** (32K)
   - Multi-agent dual-scanning framework
   - PyMuPDF + Docling cross-validation
   - Intelligent core assignment (32-core optimization)
   - Parallel processing with fault tolerance

### **Intelligence Analyzers** (4 components, 73K total)

3. **equation_intelligence_analyzer.py** (12K)
   - Equation detection and classification
   - Mathematical content scoring
   - Multi-line equation analysis
   - Hybrid PyMuPDF + LaTeX-OCR

4. **figure_intelligence_analyzer.py** (17K)
   - Figure detection via caption-based analysis
   - 100% accuracy on tested documents
   - Caption extraction with context
   - Spatial relationship mapping

5. **table_intelligence_analyzer.py** (9.7K)
   - Docling-based table detection
   - Structure analysis (rows, columns, headers)
   - Quality assessment
   - Image-embedded table identification

6. **text_intelligence_analyzer.py** (25K)
   - Text block extraction and classification
   - Semantic segmentation (optimal embedding boundaries)
   - Content hierarchy detection (headers, body, captions)
   - Multi-column layout analysis
   - Cross-page continuity preservation

## 📊 Output Schema

### `rag_bundles_v1.json`

```json
{
  "metadata": {
    "document_id": "string",
    "source_extraction": "string",
    "processing_date": "ISO-8601",
    "pipeline_version": "rag_v14_P2",
    "schema_version": "v1"
  },
  "semantic_chunks": [
    {
      "chunk_id": "string",
      "content": "string",
      "content_type": "string",
      "page": "integer",
      "bbox": {...},
      "metadata": {
        "equation_id": "string",
        "figure_id": "string",
        "table_id": "string",
        "semantic_type": "string"
      },
      "relationships": [
        {
          "target_chunk_id": "string",
          "relationship_type": "string",
          "confidence": "float"
        }
      ],
      "embedding_ready": "boolean",
      "token_count": "integer"
    }
  ],
  "knowledge_graph": {
    "nodes": [
      {
        "node_id": "string",
        "node_type": "string",
        "content": "string",
        "metadata": {...}
      }
    ],
    "edges": [
      {
        "source_id": "string",
        "target_id": "string",
        "relationship_type": "string",
        "weight": "float"
      }
    ]
  }
}
```

## 🚀 Usage (After Phase 3)

### **Basic RAG Preparation**
```python
from rag_v14_P2 import RAGPreparationPipeline

pipeline = RAGPreparationPipeline(config_path="config/rag_v14_P2_config.yaml")
rag_bundles = pipeline.process(extraction_results="extraction_results.json")

# Save results
pipeline.save_bundles(rag_bundles, output_path="rag_bundles.json")
```

### **With Intelligence Analysis**
```python
from rag_v14_P2.orchestration import DocumentIntelligenceScanner

scanner = DocumentIntelligenceScanner()
intelligence_profile = scanner.scan(pdf_path="document.pdf")

pipeline = RAGPreparationPipeline(
    config_path="config/rag_v14_P2_config.yaml",
    intelligence_profile=intelligence_profile
)
rag_bundles = pipeline.process(extraction_results="extraction_results.json")
```

### **Dual-Scanning Validation**
```python
from rag_v14_P2.orchestration import DualScanningAgentFramework

dual_scanner = DualScanningAgentFramework(num_cores=32)
validation_results = dual_scanner.cross_validate(pdf_path="document.pdf")

# Use validation results to improve extraction
pipeline = RAGPreparationPipeline(validation_data=validation_results)
```

## 🔗 Integration

**Input Contract**: Reads `extraction_results_v1.json` from Pipeline 1

**Output Contract**: Produces `rag_bundles_v1.json` for Pipeline 3

**Cross-Validation**: Can provide feedback to Pipeline 1 for improved extraction

## 📝 Configuration

See `config/rag_v14_P2_config.yaml` for configuration options:
- Intelligence analysis parameters
- Semantic chunking parameters (token limits, overlap)
- Relationship mapping thresholds
- Knowledge graph construction settings
- Embedding preparation options

## 🧪 Testing

```bash
# Unit tests
pytest tests/test_orchestration.py
pytest tests/test_analyzers.py
pytest tests/test_processors.py

# Integration tests
pytest tests/test_integration.py

# Full pipeline test
python tests/test_full_pipeline.py --input tests/data/extraction_results.json
```

## 📊 Key Metrics

From v12 performance (to be validated in v14):

**Intelligence Analysis**:
- Figure Detection: 100% accuracy (41/41 figures)
- Equation Detection: 103% accuracy (109/106 with duplicate filtering)
- Table Detection: 42% accuracy (needs enhancement)
- Text Intelligence: 1,332 blocks, 124K+ chars, 0.90 quality score

**Orchestration**:
- Dual-Scanning: 0.2s for 3-page scan, 90 items/second
- Cross-Validation: 18 items found across content types
- Multi-Core: 14 PyMuPDF, 11 Docling, 4 Comparison cores

## 📚 Documentation

- **Intelligence Analysis**: `docs/intelligence_analysis.md`
- **Relationship Mapping**: `docs/relationship_mapping.md`
- **Schema Reference**: `docs/schema_reference.md`
- **Agentic Architecture**: `docs/agentic_architecture.md`

---

**Status**: Phase 0 - Foundation setup in progress
**Next**: Phase 3 - Implement intelligence analyzers and orchestrators
