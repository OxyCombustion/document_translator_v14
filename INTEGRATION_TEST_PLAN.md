# Integration Test Plan: V14 Architecture

**Status**: Planning Complete, Ready for Execution
**Date**: 2025-11-15
**Scope**: Validate all 21 v14 packages work together

## Overview

With migration and import cleanup complete, we need to validate that:
1. All packages can be imported correctly
2. Cross-package dependencies resolve
3. The extraction pipeline can run end-to-end
4. No circular dependencies exist

## Test Categories

### Level 1: Package Import Validation
**Goal**: Verify all 21 packages can be imported without errors

Test each package:
```python
import {package_name}
# Should succeed without ImportError
```

**Success Criteria**:
- ✅ All 21 packages import successfully
- ✅ No ImportError exceptions
- ✅ No ModuleNotFoundError exceptions

### Level 2: Package Structure Validation
**Goal**: Verify __init__.py exports work correctly

Test package exports:
```python
from {package_name} import src
# Should expose package contents
```

**Success Criteria**:
- ✅ Package exports defined in __init__.py work
- ✅ Submodule access works correctly
- ✅ Version information accessible

### Level 3: Cross-Package Dependency Validation
**Goal**: Verify imports between packages resolve correctly

Test critical cross-package imports:
```python
from common.src.base.base_agent import BaseExtractionAgent
from detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule
from rag_extraction_v14_P16.src.equations.equation_extraction_agent import EquationExtractionAgent
```

**Success Criteria**:
- ✅ Base agent imports work from all packages
- ✅ Detection → Extraction pipeline works
- ✅ Validation → Analysis dependencies work
- ✅ No circular dependency errors

### Level 4: Functional Validation (Optional)
**Goal**: Run a simple extraction workflow if possible

Test basic extraction:
```python
# Instantiate detection module
detector = UnifiedDetectionModule()

# Instantiate extraction agent
extractor = EquationExtractionAgent()

# Test basic functionality (if test data available)
```

**Success Criteria**:
- ✅ Agents can be instantiated
- ✅ Basic methods can be called
- ✅ No runtime errors

## Package List (21 Packages)

### Core Infrastructure (4 packages)
1. `common` - Base classes and shared utilities
2. `agent_infrastructure_v14_P8` - Agent base classes
3. `parallel_processing_v14_P9` - Multi-core optimization
4. `infrastructure_v14_P10` - Session, context, documentation

### Extraction Pipeline (5 packages)
5. `extraction_v14_P1` - PDF → JSON extraction
6. `extraction_comparison_v14_P12` - Multi-method comparison
7. `specialized_extraction_v14_P15` - Object detection
8. `rag_extraction_v14_P16` - RAG-specific extraction
9. `extraction_utilities_v14_P18` - Extraction utilities

### RAG & Processing (3 packages)
10. `rag_v14_P2` - JSON → JSONL+Graph RAG
11. `semantic_processing_v14_P4` - Document understanding
12. `chunking_v14_P10` - Semantic chunking

### Detection & Analysis (4 packages)
13. `detection_v14_P14` - Content detection
14. `docling_agents_v14_P17` - Docling processing
15. `docling_agents_v14_P8` - Docling agents
16. `analysis_validation_v14_P19` - Analysis & validation

### Data Management (4 packages)
17. `curation_v14_P3` - JSONL → Database curation
18. `database_v14_P6` - Document registry
19. `metadata_v14_P13` - Bibliographic integration
20. `relationship_detection_v14_P5` - Relationship analysis

### Utilities & Tools (2 packages)
21. `cli_v14_P7` - Command line interface
22. `specialized_utilities_v14_P20` - Specialized utilities
23. `processing_utilities_v14_P11` - Processing utilities
24. `cross_referencing_v14_P11` - Citation linking

(Note: List shows 24 items - need to verify actual count is 21)

## Test Implementation

### Test Script Structure
```python
#!/usr/bin/env python3
"""Integration Test Suite for V14 Architecture"""

import sys
import importlib
from pathlib import Path

# Test configuration
PACKAGES = [
    'common',
    'extraction_v14_P1',
    'rag_v14_P2',
    # ... all 21 packages
]

def test_package_import(package_name):
    """Test that package can be imported."""
    try:
        module = importlib.import_module(package_name)
        return True, "Success"
    except ImportError as e:
        return False, f"ImportError: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def test_cross_package_imports():
    """Test imports that cross package boundaries."""
    tests = [
        ("Base agent", "from common.src.base.base_agent import BaseExtractionAgent"),
        ("Detection", "from detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule"),
        ("Extraction", "from rag_extraction_v14_P16.src.equations.equation_extraction_agent import EquationExtractionAgent"),
    ]

    results = []
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            results.append((name, True, "Success"))
        except Exception as e:
            results.append((name, False, str(e)))

    return results

def run_integration_tests():
    """Run complete integration test suite."""
    print("="*70)
    print("V14 Integration Test Suite")
    print("="*70)

    # Level 1: Package imports
    print("\nLevel 1: Package Import Validation")
    print("-"*70)

    success_count = 0
    for package in PACKAGES:
        success, msg = test_package_import(package)
        status = "✅" if success else "❌"
        print(f"{status} {package:40s} {msg}")
        if success:
            success_count += 1

    print(f"\nPackage Import Success: {success_count}/{len(PACKAGES)}")

    # Level 3: Cross-package dependencies
    print("\nLevel 3: Cross-Package Dependency Validation")
    print("-"*70)

    results = test_cross_package_imports()
    for name, success, msg in results:
        status = "✅" if success else "❌"
        print(f"{status} {name:40s} {msg}")

    # Summary
    print("\n" + "="*70)
    print("Integration Test Summary")
    print("="*70)
    print(f"Package Imports: {success_count}/{len(PACKAGES)} passed")
    print(f"Cross-Package: {sum(1 for _, s, _ in results if s)}/{len(results)} passed")

    return success_count == len(PACKAGES)

if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)
```

## Expected Issues & Solutions

### Issue 1: Package Not Found
**Symptom**: `ModuleNotFoundError: No module named '{package}'`
**Cause**: Package not in Python path
**Solution**:
- Add project root to PYTHONPATH
- Use `pip install -e .` for development installation
- Create pyproject.toml for proper package management

### Issue 2: Circular Dependencies
**Symptom**: `ImportError: cannot import name 'X' from partially initialized module`
**Cause**: Two packages importing from each other
**Solution**:
- Identify circular import chain
- Refactor to use dependency injection
- Move shared code to common package

### Issue 3: Missing Dependencies
**Symptom**: `ImportError: cannot import name 'X'`
**Cause**: Class not exported in __init__.py
**Solution**:
- Add missing exports to package __init__.py
- Verify import paths are correct

## Test Execution Plan

### Step 1: Environment Setup
```bash
# Add project to Python path (temporary)
export PYTHONPATH="/home/thermodynamics/document_translator_v14:$PYTHONPATH"

# Or install in development mode (recommended)
pip install -e .
```

### Step 2: Run Integration Tests
```bash
python3 tools/test_v14_integration.py
```

### Step 3: Document Results
- Record all successes and failures
- Document any import errors
- Create issue list for problems found

### Step 4: Fix Issues (if any)
- Update __init__.py exports
- Fix circular dependencies
- Add missing imports

### Step 5: Re-test
- Run tests again until 100% pass
- Validate all fixes work correctly

## Success Criteria

### Must Pass
- ✅ All 21 packages import successfully
- ✅ Cross-package dependencies resolve
- ✅ No circular dependency errors
- ✅ No missing module errors

### Should Pass (if test data available)
- ✅ Agents can be instantiated
- ✅ Basic methods can be called
- ✅ Simple extraction workflow runs

## Risk Assessment

**Low Risk**:
- Package import failures (easy to fix with PYTHONPATH)
- Missing __init__.py exports (easy to add)

**Medium Risk**:
- Circular dependencies (requires refactoring)
- Missing dependencies from other packages

**High Risk**:
- Fundamental architecture issues (would require major rework)
- **Likelihood**: Very low (migration was systematic)

## Timeline

- **Environment Setup**: 10 minutes
- **Test Script Creation**: 20 minutes
- **Initial Test Run**: 5 minutes
- **Issue Investigation**: 15-30 minutes (if issues found)
- **Fixes & Re-testing**: 15-30 minutes (if issues found)
- **Documentation**: 15 minutes
- **Total Estimated**: 1-2 hours

## Next Steps After Integration Testing

1. **If All Pass**: Create production deployment guide
2. **If Issues Found**: Fix issues and re-test
3. **Document Results**: Create integration test report
4. **Update README**: Document v14 architecture for users

---

*Integration test plan created: 2025-11-15*
*Ready for execution*
