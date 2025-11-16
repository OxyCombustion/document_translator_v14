# V13→V14 Migration: Unmigrated Components Inventory
**Date**: 2025-11-15
**Status**: Comprehensive inventory of components NOT migrated to v14

---

## Executive Summary

- **Total v13 Components Analyzed**: 63
- **Migrated to v14**: 117 components (117/339 = 34.5%)
- **Not Migrated**: 63 components
  - Agent directories/files: 60
  - UI files: 3
- **Python Files in Unmigrated**: 117

### Priority Breakdown

- **High Priority**: 1 components (need immediate attention)
- **Medium Priority**: 27 components (should migrate)
- **Low Priority**: 14 components (can defer)
- **None** (Already Replaced): 21 components

### Category Breakdown

- **Analysis Tools**: 4 components
- **Core Infrastructure**: 1 components
- **Documentation**: 1 components
- **External Integration**: 1 components
- **Extraction Agents**: 14 components
- **Gui Components**: 6 components
- **Infrastructure**: 1 components
- **Orchestration**: 1 components
- **Other**: 20 components
- **Processing**: 2 components
- **Session Management**: 3 components
- **Standalone Agents**: 5 components
- **Testing**: 2 components
- **Validation**: 2 components

---

## Detailed Inventory by Category

### Analysis Tools (4 components)

#### LOW Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| connectivity_analyzer | directory | 0.0 | 1 | replaced | analysis_tools_v14_P9 |  |
| object_detector | directory | 57.7 | 5 | replaced | analysis_tools_v14_P9 |  |
| symbol_detector | directory | 0.0 | 1 | replaced | analysis_tools_v14_P9 |  |

#### NONE Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| extraction_comparison | directory | 213.0 | 5 | replaced | extraction_comparison_v14_P12 |  |

### Core Infrastructure (1 components)

#### NONE Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| base.py | file | 27.8 | 1 | replaced | common/src/base/ | Base classes migrated to common package |

### Documentation (1 components)

#### LOW Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| documentation_agent | directory | 77.0 | 5 | deferred | - |  |

### External Integration (1 components)

#### MEDIUM Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| mathematica_agent | directory | 16.3 | 1 | deferred | - | Mathematica integration - may be added to Pipeline 3 later |

### Extraction Agents (14 components)

#### NONE Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| caption_extraction | directory | 43.8 | 3 | replaced | extraction_v14_P1 |  |
| detection | directory | 32.4 | 5 | replaced | detection_v14_P14 | Detection agents migrated to detection_v14_P14 |
| docling_agent | directory | 8.1 | 2 | replaced | docling_agents_v14_P8 or docling_agents_v14_P17 | Replaced by unified docling agents packages in v14 |
| docling_first_agent | directory | 114.2 | 2 | replaced | docling_agents_v14_P8 or docling_agents_v14_P17 | Replaced by unified docling agents packages in v14 |
| docling_roi_agent | directory | 4.7 | 1 | replaced | docling_agents_v14_P8 or docling_agents_v14_P17 | Replaced by unified docling agents packages in v14 |
| equation_extractor | directory | 4.5 | 2 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |
| figure_extraction | directory | 29.1 | 2 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |
| figure_extractor | directory | 1.1 | 1 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |
| image_extractor | directory | 0.0 | 1 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |
| metadata | directory | 176.7 | 9 | replaced | metadata_v14_P13 | Metadata agents migrated to metadata_v14_P13 |
| rag_extraction | directory | 140.7 | 8 | replaced | rag_v14_P2 or rag_extraction_v14_P16 | RAG functionality migrated to Pipeline 2 |
| table_extraction | directory | 20.8 | 1 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |
| table_extractor | directory | 28.5 | 3 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |
| text_extractor | directory | 2.2 | 2 | replaced | extraction_v14_P1 or specialized_extraction_v14_P15 | Core extraction functionality migrated to extraction_v14_P1 |

### Gui Components (6 components)

#### LOW Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| agent_monitor_gui.py | file | 115.3 | 1 | deferred | - | GUI file (2487 lines) - intentionally deferred in Phase 0 |
| gpu_compatibility_monitor | directory | 16.8 | 1 | deferred | - | GUI components intentionally deferred in Phase 0 |
| gui_lifecycle_integration.py | file | 10.9 | 1 | deferred | - | GUI file (259 lines) - intentionally deferred in Phase 0 |
| gui_viewer_agent.py | file | 39.5 | 1 | deferred | - | GUI components intentionally deferred in Phase 0 |
| gui_viewer_agent_context.md | file | 0.0 | 0 | deferred | - | GUI components intentionally deferred in Phase 0 |
| multi_method_equation_viewer.py | file | 52.0 | 1 | deferred | - | GUI file (1120 lines) - intentionally deferred in Phase 0 |

### Infrastructure (1 components)

#### NONE Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| infrastructure | directory | 31.2 | 1 | replaced | infrastructure_v14_P10 |  |

### Orchestration (1 components)

#### HIGH Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| coordination | directory | 11.7 | 1 | unknown | - | Orchestration components - need review for v14 integration |

### Other (20 components)

#### MEDIUM Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| README.md | file | 0.0 | 0 | unknown | - |  |
| __init__.py | file | 0.0 | 1 | unknown | - |  |
| equation_analysis | directory | 73.8 | 4 | unknown | - |  |
| equation_number_ocr_agent | directory | 6.5 | 1 | unknown | - |  |
| equation_refinement_agent | directory | 55.9 | 2 | unknown | - |  |
| extraction_orchestrator_cli.py | file | 25.3 | 1 | unknown | - |  |
| formula_detector_agent | directory | 2.3 | 1 | unknown | - |  |
| frame_box_detector | directory | 10.7 | 1 | unknown | - |  |
| grid_overlay | directory | 2.4 | 1 | unknown | - |  |
| heuristic_formula_probe | directory | 2.8 | 1 | unknown | - |  |
| image_extractor.py | file | 13.1 | 1 | unknown | - |  |
| raster_tightener | directory | 5.9 | 1 | unknown | - |  |
| semantic_equation_extractor.py | file | 39.4 | 1 | unknown | - |  |
| sympy_equation_parser.py | file | 20.8 | 1 | unknown | - |  |
| table_diagram_extractor.py | file | 8.1 | 1 | unknown | - |  |
| table_note_extractor.py | file | 17.3 | 1 | unknown | - |  |
| table_processing_pipeline.py | file | 13.8 | 1 | unknown | - |  |
| vision_table_extractor.py | file | 12.7 | 1 | unknown | - |  |

#### NONE Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| metadata_v14_P13 | directory | 176.3 | 8 | already_in_v14 | metadata_v14_P13 | Already migrated to v14 (present in both v13 and v14) |
| specialized_extraction_v14_P15 | directory | 113.0 | 8 | already_in_v14 | specialized_extraction_v14_P15 | Already migrated to v14 (present in both v13 and v14) |

### Processing (2 components)

#### LOW Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| consolidation | directory | 0.0 | 0 | replaced | processing_utilities_v14_P11 or semantic_processing_v14_P4 |  |
| refinement | directory | 30.2 | 1 | replaced | processing_utilities_v14_P11 or semantic_processing_v14_P4 |  |

### Session Management (3 components)

#### MEDIUM Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| context_lifecycle | directory | 17.5 | 1 | deferred | - | Session/context management - may be needed for v14 |
| extraction_orchestrator_context.md | file | 0.0 | 0 | deferred | - | Session/context management - may be needed for v14 |
| session_preservation | directory | 47.5 | 2 | deferred | - | Session/context management - may be needed for v14 |

### Standalone Agents (5 components)

#### MEDIUM Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| base_extraction_agent.py | file | 15.6 | 1 | unknown | - | Standalone agent file - needs assessment |
| latex_quality_control_agent.py | file | 20.2 | 1 | unknown | - | Standalone agent file - needs assessment |
| table_detection_agent.py | file | 17.2 | 1 | unknown | - | Standalone agent file - needs assessment |
| table_export_agent.py | file | 12.8 | 1 | unknown | - | Standalone agent file - needs assessment |
| uncertainty_assessment_agent.py | file | 21.1 | 1 | unknown | - | Standalone agent file - needs assessment |

### Testing (2 components)

#### LOW Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| testing_agent.py | file | 18.0 | 1 | deferred | - | Testing utilities - to be migrated later |
| testing_agent_context.md | file | 0.0 | 0 | deferred | - | Testing utilities - to be migrated later |

### Validation (2 components)

#### NONE Priority

| Name | Type | Size (KB) | Python Files | Reason | v14 Replacement | Notes |
|------|------|-----------|--------------|--------|-----------------|-------|
| validation | directory | 28.8 | 2 | replaced | analysis_validation_v14_P19 |  |
| validation_agent | directory | 28.1 | 3 | replaced | analysis_validation_v14_P19 |  |

---

## High-Priority Missing Components (Immediate Action Needed)

| Component | Location | Reason | Recommended Action |
|-----------|----------|--------|--------------------|
| coordination | v13/agents/coordination/ | unknown | Orchestration components - need review for v14 integration |

---

## Medium-Priority Components (Should Migrate)

**Total**: 27 components

| Component | Category | Python Files | Size (KB) | Notes |
|-----------|----------|--------------|-----------|-------|
| mathematica_agent | external_integration | 1 | 16.3 | Mathematica integration - may be added t... |
| README.md | other | 0 | 0.0 | ... |
| __init__.py | other | 1 | 0.0 | ... |
| equation_analysis | other | 4 | 73.8 | ... |
| equation_number_ocr_agent | other | 1 | 6.5 | ... |
| equation_refinement_agent | other | 2 | 55.9 | ... |
| extraction_orchestrator_cli.py | other | 1 | 25.3 | ... |
| formula_detector_agent | other | 1 | 2.3 | ... |
| frame_box_detector | other | 1 | 10.7 | ... |
| grid_overlay | other | 1 | 2.4 | ... |
| heuristic_formula_probe | other | 1 | 2.8 | ... |
| image_extractor.py | other | 1 | 13.1 | ... |
| raster_tightener | other | 1 | 5.9 | ... |
| semantic_equation_extractor.py | other | 1 | 39.4 | ... |
| sympy_equation_parser.py | other | 1 | 20.8 | ... |
| table_diagram_extractor.py | other | 1 | 8.1 | ... |
| table_note_extractor.py | other | 1 | 17.3 | ... |
| table_processing_pipeline.py | other | 1 | 13.8 | ... |
| vision_table_extractor.py | other | 1 | 12.7 | ... |
| context_lifecycle | session_management | 1 | 17.5 | Session/context management - may be need... |
| extraction_orchestrator_context.md | session_management | 0 | 0.0 | Session/context management - may be need... |
| session_preservation | session_management | 2 | 47.5 | Session/context management - may be need... |
| base_extraction_agent.py | standalone_agents | 1 | 15.6 | Standalone agent file - needs assessment... |
| latex_quality_control_agent.py | standalone_agents | 1 | 20.2 | Standalone agent file - needs assessment... |
| table_detection_agent.py | standalone_agents | 1 | 17.2 | Standalone agent file - needs assessment... |
| table_export_agent.py | standalone_agents | 1 | 12.8 | Standalone agent file - needs assessment... |
| uncertainty_assessment_agent.py | standalone_agents | 1 | 21.1 | Standalone agent file - needs assessment... |

---

## Components Already Replaced in v14

These components have been replaced by v14 packages and don't need migration:

| v13 Component | v14 Replacement |
|---------------|------------------|
| base.py | common/src/base/ |
| caption_extraction | extraction_v14_P1 |
| connectivity_analyzer | analysis_tools_v14_P9 |
| consolidation | processing_utilities_v14_P11 or semantic_processing_v14_P4 |
| detection | detection_v14_P14 |
| docling_agent | docling_agents_v14_P8 or docling_agents_v14_P17 |
| docling_first_agent | docling_agents_v14_P8 or docling_agents_v14_P17 |
| docling_roi_agent | docling_agents_v14_P8 or docling_agents_v14_P17 |
| equation_extractor | extraction_v14_P1 or specialized_extraction_v14_P15 |
| extraction_comparison | extraction_comparison_v14_P12 |
| figure_extraction | extraction_v14_P1 or specialized_extraction_v14_P15 |
| figure_extractor | extraction_v14_P1 or specialized_extraction_v14_P15 |
| image_extractor | extraction_v14_P1 or specialized_extraction_v14_P15 |
| infrastructure | infrastructure_v14_P10 |
| metadata | metadata_v14_P13 |
| object_detector | analysis_tools_v14_P9 |
| rag_extraction | rag_v14_P2 or rag_extraction_v14_P16 |
| refinement | processing_utilities_v14_P11 or semantic_processing_v14_P4 |
| symbol_detector | analysis_tools_v14_P9 |
| table_extraction | extraction_v14_P1 or specialized_extraction_v14_P15 |
| table_extractor | extraction_v14_P1 or specialized_extraction_v14_P15 |
| text_extractor | extraction_v14_P1 or specialized_extraction_v14_P15 |
| validation | analysis_validation_v14_P19 |
| validation_agent | analysis_validation_v14_P19 |

---

## GUI Components (Deferred)

All GUI components were intentionally deferred in Phase 0:

| Component | Location | Size (KB) | Lines (if file) |
|-----------|----------|-----------|------------------|
| agent_monitor_gui.py | v13/ui/agent_monitor_gui.py | 115.3 | 2487 |
| gpu_compatibility_monitor | v13/agents/gpu_compatibility_monitor/ | 16.8 | - |
| gui_lifecycle_integration.py | v13/ui/gui_lifecycle_integration.py | 10.9 | 259 |
| gui_viewer_agent.py | v13/agents/gui_viewer_agent.py | 39.5 | - |
| gui_viewer_agent_context.md | v13/agents/gui_viewer_agent_context.md | 0.0 | - |
| multi_method_equation_viewer.py | v13/ui/multi_method_equation_viewer.py | 52.0 | 1120 |

---

## Recommended Next Migration Steps

### Phase 1 (Immediate - Next 2 weeks)

1. **Review 1 high-priority orchestration components**
   - Assess if coordination/orchestration agents are needed in v14
   - Map to appropriate v14 pipeline if needed

2. **Assess 3 session management components**
   - Determine if session preservation needed in v14
   - Context lifecycle management requirements

### Phase 2 (Short-term - Weeks 3-4)

1. **Migrate 27 medium-priority components**
   - External integrations (Mathematica, etc.)
   - Standalone agents with unclear status

### Phase 3 (Long-term - Month 2+)

1. **GUI Components Migration** (deferred)
   - 6 GUI components totaling 234.5 KB
   - Consider modern UI framework vs tkinter

2. **Testing Infrastructure**
   - 2 testing components to assess

---

## Notes

- **Replaced Components**: Components marked as 'replaced' have equivalent functionality in v14 packages
- **Deferred Components**: GUI and some testing components were intentionally deferred in Phase 0
- **Unknown Status**: Components with 'unknown' status need assessment for v14 relevance
- **v14 Structure**: All v14 packages follow `{function}_v14_P{number}` naming convention

---

*Generated from: /home/thermodynamics/document_translator_v14/UNMIGRATED_AGENTS_INVENTORY.json*
*Date: 2025-11-15*
