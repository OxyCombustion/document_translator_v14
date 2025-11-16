# Shared Foundation - Essential Context

## 🎯 Purpose

This document provides **shared engineering standards** and **common development patterns** that apply to ALL pipelines in the Document Translator v14 system.

**For pipeline-specific context, see**:
- Extraction: `pipelines/extraction/CLAUDE_EXTRACTION.md`
- RAG Ingestion: `pipelines/rag_ingestion/CLAUDE_RAG.md`
- Data Management: `pipelines/data_management/CLAUDE_DATABASE.md`

---

## 🚨 MANDATORY: PRE-FLIGHT CHECKLIST BEFORE CODING

**📍 CRITICAL**: Before writing ANY Python code, complete the PRE-FLIGHT CHECKLIST

**Why This Exists**: Context Maintenance System audit (2025-10-23) found Claude violated 9 out of 14 engineering standards by coding BEFORE reading standards, resulting in brittle code.

### **STOP - Complete Checklist Before Coding**

Read **`PRE_FLIGHT_CHECKLIST.md`** and complete ALL 6 steps:

1. **READ STANDARDS** (6 documents) - BEFORE writing code
   - V12_PYTHON_STANDARDS.md (UTF-8 template)
   - SOFTWARE_ENGINEERING_ASSESSMENT.md (engineering requirements)
   - INCREMENTAL_DEVELOPMENT_PRINCIPLE.md (test after each change - MANDATORY)
   - Full V12_PYTHON_STANDARDS.md (Python patterns)
   - ACCURACY_FIRST_PRINCIPLE.md (if doing extraction)
   - MANDATORY_AGENT_DELEGATION_CHECKLIST.md (if specialized work)

2. **PLAN ARCHITECTURE** - Design BEFORE coding
   - Incremental development (break into small testable steps, test after EACH change)
   - Configuration management (YAML files, no hardcoded values)
   - Error handling (custom exceptions, retry logic)
   - Structured logging (JSON format with metrics)
   - Testing infrastructure (test_*.py files)
   - Extensibility (plugin/hook system if needed)

3. **VERIFY DELEGATION** - Check if agent should do work
   - GUI work → GUIViewerAgent
   - Extraction → Appropriate extraction agent
   - Specialized → Check agent architecture

4. **IMPLEMENT WITH STANDARDS** - Follow all requirements
   - UTF-8 template (exact copy from standards)
   - Configuration from YAML (not hardcoded)
   - Custom exception types (not generic Exception)
   - Structured logging (JSON with metrics)
   - Test suite (unit + integration tests)

5. **SELF-AUDIT** - Verify compliance BEFORE commit
   - Code quality audit (9 items)
   - Standards compliance audit (6 items)
   - Documentation audit (3 items)

6. **COMMIT WITH CONFIDENCE** - Only after passing all checks
   - All tests pass
   - No lint errors
   - All checklist items completed
   - Code is not brittle

### **Enforcement**

**Rule**: Cannot skip this checklist. Reading standards AFTER coding is TOO LATE.

**Evidence**: Context Maintenance System (2025-10-23)
- Started coding BEFORE reading SOFTWARE_ENGINEERING_ASSESSMENT.md
- Result: 9 standard violations, C+ grade, brittle code
- Fix: 6-12 hours remediation work
- Prevention: Read standards FIRST would have avoided all violations

**Automated Checks**: Pre-commit hooks verify:
- Configuration files exist (no hardcoded values)
- Test suite exists (test_*.py files)
- Custom exceptions defined
- UTF-8 template present

**Detailed Documentation**: See `PRE_FLIGHT_CHECKLIST.md` for complete requirements

---

## 🛠️ MANDATORY DEVELOPMENT STANDARDS

**📍 CRITICAL**: These standards MUST be followed for ALL development work to prevent project chaos.

### **1. MODULE REGISTRY CHECK (BEFORE ANY NEW CODE)**
```
MANDATORY WORKFLOW:
1. CHECK: python check_module_status.py --module <name>
2. VALIDATE: Review MODULE_REGISTRY.json for existing solutions
3. USE/ENHANCE: Reuse working modules instead of building new ones
```

**Why This Exists**: Claude repeatedly builds redundant modules instead of using proven working ones, wasting time and electricity.

**Enforcement**: Pre-commit hook blocks commits of new modules not in registry.

### **2. PROPER PYTHON PACKAGE STRUCTURE (NO sys.path HACKS)**
```python
# ❌ WRONG - Non-portable, brittle
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from some_module import SomeClass

# ✅ CORRECT - Portable, professional
from agents.detection import UnifiedDetectionModule
from agents.base_extraction_agent import Zone
```

**Requirements**:
- All packages have `__init__.py` files
- Use absolute imports from package root (defined in pyproject.toml)
- Never use sys.path.insert() or sys.path.append()
- Install package in editable mode: `pip install -e .`

**Why This Exists**: Hardcoded paths make software non-portable and break when directory structure changes.

### **3. MANDATORY UTF-8 ENCODING (EVERY PYTHON SCRIPT)**
```python
# -*- coding: utf-8 -*-
"""Module docstring here."""

import sys
import os

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass
```

**Template Location**: `V12_PYTHON_STANDARDS.md` - Section: "MANDATORY: UTF-8 Encoding Pattern"

**Why This Exists**: Claude has failed UTF-8 encoding 5+ times causing UnicodeEncodeError failures.

**Enforcement**: Pre-commit hook checks all .py files for UTF-8 setup block.

### **4. FILE ORGANIZATION STANDARDS**
```
Root Directory Rules:
  ❌ NO Python scripts in root (except __init__.py, setup.py)
  ❌ NO experimental/test scripts in root
  ❌ NO obsolete/backup files in root
  ✅ Tools go in tools/
  ✅ Scripts go in scripts/production/ or experiments/
  ✅ Tests go in tests/
  ✅ Obsolete files go in archive/
```

**Automation**:
- `python tools/file_classifier.py` - Analyze root directory files
- `python tools/cleanup_executor.py --execute` - Move files to proper locations

**Why This Exists**: 323 files accumulated in root causing project to become unmaintainable.

### **5. OUTPUT RETENTION POLICY**
```
Extraction Registry Database:
  - ALL extraction outputs tracked in results/extraction_registry.json
  - NEVER delete outputs - archive/compress after 90 days
  - ALWAYS use Extraction Registry for reuse ("extract once, reuse forever")
  - Manual decision required for actual deletion
```

**Why This Exists**: User explicitly requested database of output with permanent retention.

### **6. TODOWRITE TOOL USAGE (MULTI-STEP TASKS)**
```
Use TodoWrite for:
  - Tasks with 3+ steps
  - Non-trivial complex tasks
  - User requests multiple tasks
  - Any work spanning multiple tool calls
```

**Why This Exists**: Provides visibility into progress and prevents forgetting steps.

### **7. PRE-COMMIT CHECKS**
```
Automated Checks:
  1. No .py files in root directory
  2. All .py files have UTF-8 setup
  3. No sys.path manipulation
  4. All imports use proper package structure
  5. New modules registered in MODULE_REGISTRY.json
```

**Installation**: `python tools/install_pre_commit_hooks.py`

**Why This Exists**: Automated enforcement prevents standards violations.

---

## 🔧 Shared Foundation Packages (6 packages)

### **common/**
**Purpose**: Base classes and shared utilities for all pipelines

**Key Components**:
- Base agent classes
- Common data structures
- Shared utilities
- Configuration management

### **agent_infrastructure_v14_P8**
**Purpose**: Foundation for all agent-based processing

**Key Components**:
- Agent lifecycle management
- Inter-agent communication
- State management
- Error handling framework

### **parallel_processing_v14_P9**
**Purpose**: Multi-core processing infrastructure

**Key Components**:
- Worker pool management
- Task distribution
- Progress tracking
- Resource allocation

### **infrastructure_v14_P10**
**Purpose**: Session management and system infrastructure

**Key Components**:
- Session state preservation
- Context management
- Logging infrastructure
- Monitoring and metrics

### **cli_v14_P7**
**Purpose**: Command-line orchestrator for all pipelines

**Key Components**:
- Pipeline orchestration
- Command-line interface
- Workflow management
- Status reporting

### **specialized_utilities_v14_P20**
**Purpose**: Specialized tools and utilities

**Key Components**:
- PDF processing utilities
- File management tools
- Data conversion utilities
- Diagnostic tools

---

## 🔗 Pipeline Integration Patterns

### Data Contract Enforcement

**Location**: `pipelines/shared/contracts/`

```python
# Example: Extraction output contract
from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class ExtractionOutput:
    """Contract for Extraction Pipeline output."""
    document_id: str
    extractions: Dict[str, List[Dict[str, Any]]]
    metadata: Dict[str, Any]
    status: str  # "complete" | "partial" | "failed"
    timestamp: datetime

    def validate(self) -> bool:
        """Validate contract compliance."""
        assert self.document_id, "document_id required"
        assert "equations" in self.extractions, "equations required"
        assert "tables" in self.extractions, "tables required"
        assert "figures" in self.extractions, "figures required"
        assert "text" in self.extractions, "text required"
        assert self.status in ["complete", "partial", "failed"]
        return True
```

### File-Based Handoff Pattern

```
Pipeline Communication:
1. Pipeline A writes output to results/{pipeline_a}/document_id.json
2. Pipeline B reads from results/{pipeline_a}/document_id.json
3. Pipeline B validates input against contract
4. Pipeline B processes and writes to results/{pipeline_b}/document_id.json
```

### Error Handling Pattern

```python
# Consistent error handling across pipelines
class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass

class ContractValidationError(PipelineError):
    """Raised when data contract validation fails."""
    pass

class ProcessingError(PipelineError):
    """Raised when pipeline processing fails."""
    pass
```

---

## 🧪 Testing Infrastructure

### Test Organization
```
tests/
├── unit/                    # Unit tests (per pipeline)
├── integration/             # Cross-pipeline integration tests
└── end_to_end/             # Complete workflow tests
```

### Integration Test Pattern
```python
def test_extraction_to_rag_handoff():
    """Test data handoff from extraction to RAG pipeline."""
    # Run extraction
    extraction_output = run_extraction_pipeline(test_pdf)

    # Validate extraction output
    assert extraction_output.validate()

    # Test RAG can consume extraction output
    rag_input = RAGInput.from_extraction_output(extraction_output)
    assert rag_input is not None
```

---

## 📚 Documentation Standards

### Required Documentation
- **README.md**: Quick start and overview
- **ARCHITECTURE.md**: Design and implementation details
- **API_REFERENCE.md**: Public API documentation
- **CHANGELOG.md**: Version history and changes

### Code Documentation
- All functions require docstrings
- Complex logic requires inline comments
- WHY-focused comments (not WHAT)
- Examples for public APIs

---

## 🔍 Development Workflow

### 1. Planning Phase
- Read relevant CLAUDE.md files
- Check MODULE_REGISTRY.json
- Review existing code
- Design before coding

### 2. Implementation Phase
- Follow UTF-8 template
- Use configuration files
- Implement tests
- Document as you code

### 3. Validation Phase
- Run unit tests
- Run integration tests
- Check code quality
- Review documentation

### 4. Deployment Phase
- Update MODULE_REGISTRY.json
- Update CHANGELOG.md
- Create pull request
- Deploy after review

---

## 🎯 Quick Commands

### System Management
```bash
# Check module status
python check_module_status.py --module <name>

# Run all tests
pytest tests/

# Run specific pipeline tests
pytest tests/unit/extraction/
pytest tests/unit/rag/
pytest tests/unit/database/

# Run integration tests
pytest tests/integration/
```

### Pipeline Orchestration
```bash
# Run complete workflow
python -m cli_v14_P7 workflow --input pdfs/ --output results/

# Run individual pipeline
python -m cli_v14_P7 extraction --input pdfs/ --output results/extraction/
python -m cli_v14_P7 rag --input results/extraction/ --output results/rag/
python -m cli_v14_P7 database --input results/rag/ --output results/database/
```

---

*This is the shared foundation context. For pipeline-specific details, see the pipeline-specific CLAUDE.md files.*
