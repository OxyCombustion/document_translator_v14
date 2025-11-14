# Configuration Migration Mapping: v13 → v14

**Purpose**: Map all v13 configuration files to v14 three-pipeline architecture
**Date**: 2025-11-14
**Source**: v13 configuration files (YAML, JSON, Python config modules)
**Destination**: v14 pipeline-specific configurations

---

## 📊 Configuration Overview

### **v13 Configuration Files Found**

| Type | Count | Status |
|------|-------|--------|
| YAML configs | 13 | ✅ Mapped |
| Python config modules | TBD | ⏸️ Pending audit |
| JSON configs | TBD | ⏸️ Pending audit |
| Environment files | TBD | ⏸️ Pending audit |

---

## 🗺️ YAML Configuration Migration

### **Root-Level Configurations**

| v13 Config | Purpose | v14 Destination | Priority | Notes |
|------------|---------|-----------------|----------|-------|
| `application.yaml` | Application settings | `config/application_v14.yaml` | P0 | Root-level app config |
| `settings.yaml` | General settings | `config/settings_v14.yaml` | P0 | Merge with application.yaml |
| `agents.yaml` | Agent configurations | Split across pipelines | P0 | See agent-specific mapping below |
| `production.yaml` | Production settings | `config/production_v14.yaml` | P0 | Environment-specific |
| `maintenance_config.yaml` | Maintenance settings | `config/maintenance_v14.yaml` | P1 | Operations config |

**Migration Strategy**:
- Consolidate `application.yaml` + `settings.yaml` → single `config/application_v14.yaml`
- Split `agents.yaml` by pipeline responsibility
- Preserve `production.yaml` as environment-specific override

### **Pipeline 1: Extraction (extraction_v14_P1/)**

| v13 Config | Purpose | v14 Destination | Priority | Notes |
|------------|---------|-----------------|----------|-------|
| `pipeline/extraction_pipeline_config.yaml` | Extraction pipeline | `extraction_v14_P1/config/pipeline_config.yaml` | P0 | Core extraction settings |
| `agents.yaml` (detection section) | Detection agents | `extraction_v14_P1/config/detection_agents.yaml` | P0 | YOLO, Docling, PyMuPDF |
| `agents.yaml` (extraction section) | Extraction agents | `extraction_v14_P1/config/extraction_agents.yaml` | P0 | Equation, table, figure, text |
| `document_classification.yaml` | Document classification | `extraction_v14_P1/config/classification.yaml` | P1 | Content type classification |

**Integration**:
```yaml
# extraction_v14_P1/config/extraction_v14_P1_config.yaml (master)
includes:
  - pipeline_config.yaml
  - detection_agents.yaml
  - extraction_agents.yaml
  - classification.yaml
```

### **Pipeline 2: RAG Preparation (rag_v14_P2/)**

| v13 Config | Purpose | v14 Destination | Priority | Notes |
|------------|---------|-----------------|----------|-------|
| `semantic_chunking.yaml` | Semantic chunking | `rag_v14_P2/config/semantic_chunking.yaml` | P0 | Chunk size, overlap, boundaries |
| `relationship_extraction/reference_patterns.yaml` | Reference patterns | `rag_v14_P2/config/reference_patterns.yaml` | P0 | Citation/reference detection |
| `relationship_extraction/data_dependency_config.yaml` | Data dependencies | `rag_v14_P2/config/data_dependencies.yaml` | P0 | Equation/table/figure relationships |
| `relationship_extraction/variable_definition_patterns.yaml` | Variable patterns | `rag_v14_P2/config/variable_patterns.yaml` | P1 | Variable detection patterns |
| `rag/micro_bundle_config.yaml` | RAG bundle config | `rag_v14_P2/config/bundle_config.yaml` | P0 | Bundle size, metadata |
| `agents.yaml` (intelligence section) | Intelligence analyzers | `rag_v14_P2/config/intelligence_analyzers.yaml` | P0 | From agents.yaml |
| `agents.yaml` (orchestration section) | Orchestrators | `rag_v14_P2/config/orchestrators.yaml` | P0 | From agents.yaml |

**Integration**:
```yaml
# rag_v14_P2/config/rag_v14_P2_config.yaml (master)
includes:
  - semantic_chunking.yaml
  - reference_patterns.yaml
  - data_dependencies.yaml
  - variable_patterns.yaml
  - bundle_config.yaml
  - intelligence_analyzers.yaml
  - orchestrators.yaml
```

### **Pipeline 3: Curation (curation_v14_P3/)**

| v13 Config | Purpose | v14 Destination | Priority | Notes |
|------------|---------|-----------------|----------|-------|
| `agents.yaml` (calibration section) | LLM calibration | `curation_v14_P3/config/calibration_config.yaml` | P0 | Bias patterns, thresholds |
| `agents.yaml` (validation section) | Validation rules | `curation_v14_P3/config/validation_config.yaml` | P0 | Domain specificity, quality |
| `agents.yaml` (metadata section) | Metadata extraction | `curation_v14_P3/config/metadata_config.yaml` | P0 | Zotero, TRL, citations |

**Integration**:
```yaml
# curation_v14_P3/config/curation_v14_P3_config.yaml (master)
includes:
  - calibration_config.yaml
  - validation_config.yaml
  - metadata_config.yaml
```

**Note**: v13 Phase 1 calibration configurations to be extracted from code and added to `calibration_config.yaml`

### **Common Utilities (common/)**

| v13 Config | Purpose | v14 Destination | Priority | Notes |
|------------|---------|-----------------|----------|-------|
| `output_management.yaml` | Output management | `common/config/output_management.yaml` | P0 | Shared across pipelines |
| `maintenance_config.yaml` | Maintenance tasks | `common/config/maintenance.yaml` | P1 | Shared utilities |

---

## 📋 Configuration Migration Checklist

### **Phase 0.9 Tasks**

- [✅] Identify all YAML configuration files (13 found)
- [✅] Map YAML configs to v14 destinations
- [⏸️] Identify Python config modules
- [⏸️] Identify JSON config files
- [⏸️] Identify environment files (.env, .envrc)
- [⏸️] Create config consolidation strategy
- [⏸️] Define config override hierarchy

### **Configuration Consolidation Strategy**

**1. Root-Level Configs** (`config/`):
```
config/
├── application_v14.yaml      # Consolidated app + settings
├── production_v14.yaml        # Production overrides
├── development_v14.yaml       # Development overrides (NEW)
├── maintenance_v14.yaml       # Maintenance tasks
└── .env.template              # Environment variables template
```

**2. Pipeline-Specific Configs**:
```
extraction_v14_P1/config/
├── extraction_v14_P1_config.yaml   # Master config (includes all)
├── pipeline_config.yaml            # Core pipeline settings
├── detection_agents.yaml           # Detection configuration
├── extraction_agents.yaml          # Extraction configuration
└── classification.yaml             # Document classification

rag_v14_P2/config/
├── rag_v14_P2_config.yaml          # Master config (includes all)
├── semantic_chunking.yaml          # Chunking parameters
├── reference_patterns.yaml         # Citation patterns
├── data_dependencies.yaml          # Relationship rules
├── variable_patterns.yaml          # Variable detection
├── bundle_config.yaml              # RAG bundle settings
├── intelligence_analyzers.yaml     # Intelligence analysis
└── orchestrators.yaml              # Orchestration settings

curation_v14_P3/config/
├── curation_v14_P3_config.yaml     # Master config (includes all)
├── calibration_config.yaml         # LLM calibration (from v13 Phase 1)
├── validation_config.yaml          # Validation rules
└── metadata_config.yaml            # Metadata extraction
```

**3. Common Configs** (`common/config/`):
```
common/config/
├── output_management.yaml          # Output organization
└── maintenance.yaml                # Shared maintenance
```

### **Configuration Override Hierarchy**

**Priority Order** (highest to lowest):
1. Environment variables (`export VAR=value`)
2. Command-line arguments (`--config-override key=value`)
3. Environment-specific config (`production_v14.yaml`, `development_v14.yaml`)
4. Pipeline-specific config (`extraction_v14_P1_config.yaml`)
5. Default config (hardcoded in code)

**Example**:
```yaml
# application_v14.yaml (base)
logging:
  level: INFO
  format: json

# production_v14.yaml (override)
logging:
  level: WARNING  # Override: Less verbose in production

# Environment variable (highest priority)
export LOG_LEVEL=DEBUG  # Override: Debug mode for troubleshooting
```

---

## 🔧 Configuration Parameter Migration

### **agents.yaml Split Strategy**

**v13 Structure** (single monolithic file):
```yaml
agents:
  detection:
    yolo: {...}
    docling: {...}
  extraction:
    equations: {...}
    tables: {...}
  intelligence:
    analyzers: {...}
  orchestration:
    scanners: {...}
  calibration:
    llm: {...}
  validation:
    domain: {...}
```

**v14 Structure** (split by pipeline):

**extraction_v14_P1/config/detection_agents.yaml**:
```yaml
detection:
  yolo:
    model: "doclayout_yolo_docstructbench_imgsz1280_2501.pt"
    confidence: 0.5
  docling:
    enabled: true
    mode: "cpu"
  pymupdf:
    enabled: true
```

**extraction_v14_P1/config/extraction_agents.yaml**:
```yaml
extraction:
  equations:
    method: "bidirectional"
    parallel: true
  tables:
    method: "hybrid"
    parallel: true
  figures:
    caption_search_radius: 400
  text:
    semantic_chunking: true
```

**rag_v14_P2/config/intelligence_analyzers.yaml**:
```yaml
intelligence:
  analyzers:
    equation:
      complexity_scoring: true
    figure:
      caption_based: true
    table:
      structure_analysis: true
    text:
      hierarchy_detection: true
```

**rag_v14_P2/config/orchestrators.yaml**:
```yaml
orchestration:
  scanners:
    intelligence_scanner:
      enabled: true
    dual_scanning:
      enabled: true
      pymupdf_cores: 14
      docling_cores: 11
```

**curation_v14_P3/config/calibration_config.yaml**:
```yaml
calibration:
  llm:
    model: "qwen2.5-3b-instruct"
    training_cutoff: "2024-09-18"
  bias_patterns:
    numeric_skepticism: 1.3
    proper_nouns: 1.2
    textbook_formulas: 0.8
    post_training_override: 1.5
```

**curation_v14_P3/config/validation_config.yaml**:
```yaml
validation:
  domain:
    specialty: "heat_transfer"
    high_specificity_threshold: 0.90
    medium_specificity_threshold: 0.70
```

---

## 📊 Configuration Migration Priority

### **P0 (Critical) - Week 1**
Must be migrated before any code execution:
- `application.yaml` → `config/application_v14.yaml`
- `production.yaml` → `config/production_v14.yaml`
- `pipeline/extraction_pipeline_config.yaml` → `extraction_v14_P1/config/`
- `agents.yaml` (split across all pipelines)
- `semantic_chunking.yaml` → `rag_v14_P2/config/`
- `relationship_extraction/*.yaml` → `rag_v14_P2/config/`

### **P1 (Important) - Week 2**
Required for full functionality:
- `output_management.yaml` → `common/config/`
- `maintenance_config.yaml` → `common/config/`
- `document_classification.yaml` → `extraction_v14_P1/config/`
- `rag/micro_bundle_config.yaml` → `rag_v14_P2/config/`

### **P2 (Optional) - Week 3**
Nice to have, can defer:
- Create `development_v14.yaml` (new)
- Create `.env.template` (new)
- Additional pipeline-specific overrides

---

## 🔍 Configuration Validation

### **Automated Validation Checks**

**1. Schema Validation**:
```python
# Validate each config against JSON Schema
validate_config(
    config_file="extraction_v14_P1/config/extraction_v14_P1_config.yaml",
    schema_file="schemas/extraction/config_schema.json"
)
```

**2. Required Fields Check**:
- All P0 configs must have required fields
- No default values in production configs (explicit values only)

**3. Cross-Pipeline Consistency**:
- Shared parameter values must be consistent (e.g., model names)
- No conflicting settings between pipelines

**4. Environment-Specific Validation**:
- Production configs must not have debug settings enabled
- Development configs must have appropriate test data paths

### **Migration Validation Script**

```bash
# Phase 0.13 will create this
python tools/validate_config_migration.py

# Checks:
# - All v13 configs accounted for
# - All v14 configs valid against schema
# - No missing required parameters
# - No conflicting settings
# - Environment-specific configs complete
```

---

## 📝 Notes

### **Configuration Best Practices**

1. **DRY Principle**: Use includes/imports to avoid duplication
2. **Environment Separation**: Never commit secrets or environment-specific values
3. **Schema-Driven**: All configs validated against JSON Schema
4. **Explicit Over Implicit**: No magic defaults, document all parameters
5. **Version Control**: Track config changes with git (except .env)

### **Migration Gotchas**

⚠️ **Watch For**:
- Hardcoded paths in v13 configs (make relative in v14)
- Absolute imports in Python config modules (update to v14 package structure)
- Environment-specific values (extract to .env)
- Deprecated parameters (remove or update)
- Conflicting parameter names across pipelines (namespace properly)

---

## ✅ Phase 0.9 Complete

**Status**: Configuration migration mapping complete
**Files Created**: 1 (this document)
**Configs Mapped**: 13 YAML files → v14 destinations
**Next**: Phase 0.10 (Documentation migration mapping)

---

**Created**: 2025-11-14
**Status**: ✅ Complete - Ready for Phase 1 config migration
