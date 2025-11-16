# Pipeline 3: Curation (curation_v14_P3)

**Purpose**: RAG-Ready Data → Curated Knowledge Database

**Input**: `rag_bundles_v1.json` (from Pipeline 2)
**Output**: `knowledge_graph_v1.json` (validated, calibrated, curated)

## 🎯 Responsibilities

### **LLM Confidence Calibration**
- Bias pattern detection and mitigation
- Confidence score adjustment
- Training date awareness
- Uncertainty quantification

### **Domain Specificity Validation**
- Heat transfer specialty validation
- Domain-specific terminology checking
- Cross-domain concept validation
- Specialty scoring

### **Novelty Assessment**
- Training date versioning ("2024-09-18" vs "1.0")
- Post-training knowledge detection
- Research frontier identification
- Novelty confidence scoring

### **Quality Assurance**
- Completeness validation
- Consistency checking
- Accuracy assessment
- Final curation decisions

## 📁 Directory Structure

```
curation_v14_P3/
├── src/
│   ├── core/
│   │   ├── llm_confidence_calibrator.py
│   │   ├── domain_specificity_validator.py
│   │   └── novelty_metadata_database.py
│   ├── validators/
│   │   ├── completeness_validator.py
│   │   ├── consistency_validator.py
│   │   └── accuracy_validator.py
│   ├── database/
│   │   ├── knowledge_graph_builder.py
│   │   └── metadata_manager.py
│   └── utils/
│       ├── calibration_utils.py
│       ├── validation_utils.py
│       └── scoring_utils.py
├── config/
│   └── curation_v14_P3_config.yaml
├── tests/
│   ├── test_calibration.py
│   ├── test_validation.py
│   ├── test_database.py
│   └── test_integration.py
└── docs/
    ├── calibration_methodology.md
    ├── validation_criteria.md
    └── schema_reference.md
```

## 🔬 v13 Calibration Work (Migrated to v14)

These P0/P1 priority components from v13 are preserved in this pipeline:

### **1. LLM Confidence Calibrator** (470 lines)

**Four Bias Patterns Detected**:
1. **Numeric Skepticism**: Conservative with precise numbers
2. **Proper Nouns**: Struggles with named entities
3. **Textbook Formulas**: Overconfident on standard equations
4. **Post-Training Override**: Cautious on knowledge gaps

**Calibration Strategy**:
```python
# Before calibration
raw_confidence = llm.get_confidence(chunk)  # e.g., 0.65

# After calibration
calibrated_confidence = calibrator.adjust_confidence(
    raw_confidence=0.65,
    bias_pattern="numeric_skepticism",
    context=chunk
)  # e.g., 0.85 (adjusted upward)
```

**Target Accuracy**: 95-97% (vs 90-93% baseline)

### **2. Domain Specificity Validator** (650+ lines)

**Heat Transfer Specialty Validation**:
- Thermodynamics terminology (0.95 confidence threshold)
- Heat transfer equations (validated against known formulas)
- Material properties (cross-referenced with databases)
- Dimensional analysis (unit consistency checking)

**Validation Levels**:
- **High Specificity** (0.90+): Core heat transfer concepts
- **Medium Specificity** (0.70-0.89): General thermodynamics
- **Low Specificity** (0.50-0.69): Tangential concepts
- **Not Specific** (<0.50): Out of domain

### **3. Novelty Metadata Database** (600 lines)

**Training Date Versioning**:
```python
# OLD approach (brittle)
version = "1.0"

# NEW approach (accurate)
training_date = "2024-09-18"
post_training_knowledge = detect_novelty(
    training_cutoff="2024-09-18",
    document_date="2024-11-14"
)
```

**Novelty Detection**:
- **Pre-Training** (before 2024-09-18): High confidence expected
- **Post-Training** (after 2024-09-18): Novel knowledge, verify carefully
- **Research Frontier**: New findings, require external validation

**Economic Motivation**:
- Qwen 2.5 3B Instruct on NVIDIA Blackwell GB10
- $4 for 10M chunks vs $300,000 cloud APIs (75,000x cheaper)
- Accuracy-first: 100% LLM probing (not cost-minimization)

## 📊 Output Schema

### `knowledge_graph_v1.json`

```json
{
  "metadata": {
    "document_id": "string",
    "source_rag_bundles": "string",
    "curation_date": "ISO-8601",
    "pipeline_version": "curation_v14_P3",
    "schema_version": "v1",
    "quality_metrics": {
      "overall_quality": "float",
      "completeness": "float",
      "consistency": "float",
      "accuracy": "float"
    }
  },
  "curated_chunks": [
    {
      "chunk_id": "string",
      "content": "string",
      "calibrated_confidence": "float",
      "domain_specificity": {
        "score": "float",
        "domain": "string",
        "specialty": "string"
      },
      "novelty": {
        "is_novel": "boolean",
        "training_cutoff": "string",
        "novelty_score": "float"
      },
      "validation": {
        "completeness": "float",
        "consistency": "float",
        "accuracy": "float"
      },
      "curation_decision": "string",
      "curation_notes": "string"
    }
  ],
  "knowledge_graph": {
    "nodes": [...],
    "edges": [...],
    "graph_metrics": {
      "node_count": "integer",
      "edge_count": "integer",
      "avg_degree": "float",
      "clustering_coefficient": "float"
    }
  }
}
```

## 🚀 Usage (After Phase 4)

### **Basic Curation**
```python
from curation_v14_P3 import CurationPipeline

pipeline = CurationPipeline(config_path="config/curation_v14_P3_config.yaml")
curated_kg = pipeline.curate(rag_bundles="rag_bundles.json")

# Save results
pipeline.save_knowledge_graph(curated_kg, output_path="knowledge_graph.json")
```

### **With Calibration**
```python
from curation_v14_P3.core import (
    LLMConfidenceCalibrator,
    DomainSpecificityValidator,
    NoveltyMetadataDatabase
)

# Initialize calibration components
calibrator = LLMConfidenceCalibrator(
    model_training_date="2024-09-18",
    bias_patterns={
        "numeric_skepticism": 1.3,
        "proper_nouns": 1.2,
        "textbook_formulas": 0.8,
        "post_training_override": 1.5
    }
)

domain_validator = DomainSpecificityValidator(
    domain="heat_transfer",
    specialty_threshold=0.90
)

novelty_db = NoveltyMetadataDatabase(
    training_cutoff_date="2024-09-18"
)

# Create pipeline with calibration
pipeline = CurationPipeline(
    calibrator=calibrator,
    domain_validator=domain_validator,
    novelty_db=novelty_db
)

curated_kg = pipeline.curate(rag_bundles="rag_bundles.json")
```

### **Quality Assessment**
```python
from curation_v14_P3.validators import (
    CompletenessValidator,
    ConsistencyValidator,
    AccuracyValidator
)

# Validate knowledge graph quality
completeness = CompletenessValidator().validate(curated_kg)
consistency = ConsistencyValidator().validate(curated_kg)
accuracy = AccuracyValidator().validate(curated_kg)

print(f"Completeness: {completeness:.2%}")
print(f"Consistency: {consistency:.2%}")
print(f"Accuracy: {accuracy:.2%}")
```

## 🔗 Integration

**Input Contract**: Reads `rag_bundles_v1.json` from Pipeline 2

**Output Contract**: Produces `knowledge_graph_v1.json` (final curated output)

**Feedback Loop**: Can provide validation feedback to Pipeline 2 for quality improvement

## 📝 Configuration

See `config/curation_v14_P3_config.yaml` for configuration options:
- Calibration bias pattern weights
- Domain validation thresholds
- Novelty detection parameters
- Quality assurance criteria
- Knowledge graph construction settings

## 🧪 Testing

```bash
# Unit tests
pytest tests/test_calibration.py
pytest tests/test_validation.py
pytest tests/test_database.py

# Integration tests
pytest tests/test_integration.py

# Full pipeline test
python tests/test_full_pipeline.py --input tests/data/rag_bundles.json
```

## 📊 Key Metrics (v13 Performance)

**LLM Confidence Calibration**:
- Bias pattern detection: 4 patterns identified
- Calibration improvement: 90-93% → 95-97% accuracy
- Confidence adjustment: ±0.2 typical range

**Domain Specificity**:
- Heat transfer specialty: 0.95 threshold
- Validation coverage: 100% of technical terms
- Domain precision: 0.92+ for core concepts

**Novelty Detection**:
- Training cutoff: 2024-09-18
- Post-training detection: 98% accuracy
- Novelty scoring: 0.0 (pre-training) to 1.0 (frontier)

## 📚 Documentation

- **Calibration Methodology**: `docs/calibration_methodology.md`
- **Validation Criteria**: `docs/validation_criteria.md`
- **Schema Reference**: `docs/schema_reference.md`
- **Local LLM Economics**: `docs/local_llm_economics.md`

---

**Status**: Phase 0 - Foundation setup in progress
**Next**: Phase 4 - Implement calibration and validation systems
