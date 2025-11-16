# Import Path Migration Plan - v14 Package Reorganization

## Overview
21 packages were moved from root to pipeline-specific subdirectories. All import paths need updating.

## New Package Locations

### Extraction Pipeline (7 packages)
- `pipelines/extraction/packages/detection_v14_P14/`
- `pipelines/extraction/packages/docling_agents_v14_P17/`
- `pipelines/extraction/packages/docling_agents_v14_P8/`
- `pipelines/extraction/packages/extraction_comparison_v14_P12/`
- `pipelines/extraction/packages/extraction_utilities_v14_P18/`
- `pipelines/extraction/packages/extraction_v14_P1/`
- `pipelines/extraction/packages/specialized_extraction_v14_P15/`

### RAG Ingestion Pipeline (4 packages)
- `pipelines/rag_ingestion/packages/analysis_validation_v14_P19/`
- `pipelines/rag_ingestion/packages/rag_extraction_v14_P16/`
- `pipelines/rag_ingestion/packages/rag_v14_P2/`
- `pipelines/rag_ingestion/packages/semantic_processing_v14_P4/`

### Data Management Pipeline (4 packages)
- `pipelines/data_management/packages/curation_v14_P3/`
- `pipelines/data_management/packages/database_v14_P6/`
- `pipelines/data_management/packages/metadata_v14_P13/`
- `pipelines/data_management/packages/relationship_detection_v14_P5/`

### Shared Pipeline (6 packages)
- `pipelines/shared/packages/analysis_tools_v14_P9/`
- `pipelines/shared/packages/cli_v14_P7/`
- `pipelines/shared/packages/common/`
- `pipelines/shared/packages/infrastructure_v14_P10/`
- `pipelines/shared/packages/processing_utilities_v14_P11/`
- `pipelines/shared/packages/specialized_utilities_v14_P20/`

## Migration Strategy

### Phase 1: Analysis (COMPLETED)
- Identified 361 Python files in packages
- Identified 400 total Python files in project
- Found import patterns needing updates

### Phase 2: Automated Import Updates
1. Create Python script to update all import statements
2. Handle different import patterns:
   - `from package_v14_PXX.src...` → `from pipelines.PIPELINE.packages.package_v14_PXX.src...`
   - `import package_v14_PXX...` → `import pipelines.PIPELINE.packages.package_v14_PXX...`
   - Relative imports within packages (no changes needed)

3. Execution order:
   - Update imports in packages first (inter-package dependencies)
   - Update imports in root-level scripts
   - Update imports in test files

### Phase 3: Validation
1. Run syntax validation on all updated files
2. Check for circular dependencies
3. Run existing tests to verify functionality
4. Manual review of critical files

### Phase 4: PYTHONPATH Configuration
1. Update pyproject.toml or setup.py to include new paths
2. Consider creating __init__.py files at pipeline level if needed
3. Update any environment configuration files

## Critical Files Requiring Updates

### Root Level Scripts (19 files with imports)
- test_gui_viewer.py
- debug_yolo_classes.py
- (others identified by grep)

### Package Files with Cross-Package Imports
- unified_pipeline_orchestrator.py (15+ cross-package imports)
- structure_based_validator.py (multiple locations)
- object_numbering_coordinator.py
- figure_detection_agent.py
- validation_filtered_extractor.py
- agent.py (docling_agents)

## Package-to-Pipeline Mapping

```python
PACKAGE_PIPELINE_MAP = {
    # Extraction
    'detection_v14_P14': 'extraction',
    'docling_agents_v14_P17': 'extraction',
    'docling_agents_v14_P8': 'extraction',
    'extraction_comparison_v14_P12': 'extraction',
    'extraction_utilities_v14_P18': 'extraction',
    'extraction_v14_P1': 'extraction',
    'specialized_extraction_v14_P15': 'extraction',
    
    # RAG Ingestion
    'analysis_validation_v14_P19': 'rag_ingestion',
    'rag_extraction_v14_P16': 'rag_ingestion',
    'rag_v14_P2': 'rag_ingestion',
    'semantic_processing_v14_P4': 'rag_ingestion',
    
    # Data Management
    'curation_v14_P3': 'data_management',
    'database_v14_P6': 'data_management',
    'metadata_v14_P13': 'data_management',
    'relationship_detection_v14_P5': 'data_management',
    
    # Shared
    'analysis_tools_v14_P9': 'shared',
    'cli_v14_P7': 'shared',
    'common': 'shared',
    'infrastructure_v14_P10': 'shared',
    'processing_utilities_v14_P11': 'shared',
    'specialized_utilities_v14_P20': 'shared',
}
```

## Risk Mitigation

1. **Git Safety**: Commit current state before migration
2. **Backup**: Create backup of all files being modified
3. **Testing**: Comprehensive testing after each phase
4. **Rollback Plan**: Keep migration script reversible
5. **Documentation**: Track all changes made

## Next Steps

1. Create automated migration script (migrate_imports.py)
2. Run script with --dry-run to preview changes
3. Execute migration
4. Validate with tests
5. Update documentation

## Success Criteria

- All imports resolve correctly
- No broken dependencies
- All existing tests pass
- No circular import issues
- Code remains functionally identical
