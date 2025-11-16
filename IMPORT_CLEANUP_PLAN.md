# Import Cleanup Plan: V13→V14 Import Path Migration

**Status**: Planning Complete, Ready for Execution
**Date**: 2025-11-15
**Scope**: 46 files (8 v13 imports + 38 sys.path manipulations)

## Overview

Now that all 222 agent files have been migrated to 21 v14 packages, we need to update import statements across the codebase to use the new v14 package structure.

## Current Situation

### Files with V13 Imports (8 files)
```
1. analysis_validation_v14_P19/src/validation/structure_based_validator.py
2. extraction_utilities_v14_P18/src/tables/validation_filtered_extractor.py
3. rag_extraction_v14_P16/src/equations/equation_extraction_agent.py
4. rag_extraction_v14_P16/src/figures/figure_extraction_agent.py
5. processing_utilities_v14_P11/src/validation/structure_based_validator.py
6. rag_v14_P2/src/orchestrators/unified_pipeline_orchestrator.py
7. rag_v14_P2/src/agents/extraction/figure_extraction_agent.py
8. rag_v14_P2/src/agents/extraction/equation_extraction_agent.py
```

### Files with sys.path Manipulation (38 files)
All files using patterns like:
```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

## Import Mapping: V13 → V14

### Base Agent Imports
**Old V13**:
```python
from agents.base_extraction_agent import BaseExtractionAgent, Zone, ExtractedObject
from agents.base import BaseAgent, AgentResult, AgentStatus
```

**New V14**:
```python
from common.src.base.base_agent import BaseExtractionAgent, Zone, ExtractedObject
from common.src.base.base_agent import BaseAgent, AgentResult, AgentStatus
```

### Detection Imports
**Old V13**:
```python
from agents.detection.unified_detection_module import UnifiedDetectionModule
```

**New V14**:
```python
from detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule
```

### Extraction Imports
**Old V13**:
```python
from agents.extraction.equation_extraction_agent import EquationExtractionAgent
from agents.extraction.figure_extraction_agent import FigureExtractionAgent
from agents.extraction.table_extraction_agent import TableExtractionAgent
```

**New V14**:
```python
from rag_extraction_v14_P16.src.equations.equation_extraction_agent import EquationExtractionAgent
from rag_extraction_v14_P16.src.figures.figure_extraction_agent import FigureExtractionAgent
from rag_extraction_v14_P16.src.tables.table_extraction_agent import TableExtractionAgent
```

### Metadata Imports
**Old V13**:
```python
from agents.metadata.zotero_agent import ZoteroAgent
```

**New V14**:
```python
from metadata_v14_P13.src.zotero.zotero_agent import ZoteroAgent
```

## Cleanup Strategy

### Phase 1: Remove sys.path Manipulation (38 files)

**Pattern to Remove**:
```python
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

**Replacement**: Remove these lines entirely, rely on proper package imports

### Phase 2: Update V13 Imports (8 files)

**Strategy**: Use search-and-replace with validation:
1. Identify import statement
2. Map to new v14 package location
3. Update import path
4. Verify module exists at new location

### Phase 3: Validation

**Tests**:
1. Syntax check: `python -m py_compile <file>`
2. Import validation: Try importing each updated module
3. Functional test: Run existing test suite

## Implementation Plan

### Step 1: Create Import Mapping Database (JSON)
```json
{
  "agents.base_extraction_agent": "common.src.base.base_agent",
  "agents.base": "common.src.base.base_agent",
  "agents.detection.unified_detection_module": "detection_v14_P14.src.unified.unified_detection_module",
  ...
}
```

### Step 2: Create Automated Update Script
```python
# tools/update_imports.py
# - Read mapping database
# - Process each file
# - Update imports
# - Remove sys.path manipulation
# - Validate syntax
```

### Step 3: Execute Updates
- Run update script on all 46 files
- Review changes with git diff
- Validate syntax and imports

### Step 4: Test and Validate
- Run test suite
- Fix any broken imports
- Commit changes

## Risk Mitigation

1. **Backup**: All changes in git, easy to revert
2. **Validation**: Syntax check after each file
3. **Testing**: Run tests before committing
4. **Incremental**: Can update package-by-package if needed

## Success Criteria

- ✅ Zero files with `from agents.` imports
- ✅ Zero files with `sys.path.insert()` manipulation
- ✅ All imports resolve correctly
- ✅ All existing tests pass
- ✅ Clean git diff showing only import changes

## Estimated Time

- Mapping creation: 30 minutes
- Script development: 1 hour
- Execution & validation: 1 hour
- **Total: 2.5 hours**

## Next Steps

1. Create complete import mapping (all v13→v14 paths)
2. Develop `tools/update_imports.py` script
3. Execute on all 46 files
4. Validate and test
5. Document completion
