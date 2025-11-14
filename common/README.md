# Common Utilities (common/)

**Purpose**: Shared utilities, base classes, and interfaces used across all three pipelines

## 🎯 Responsibilities

### **Base Classes**
- BaseExtractionAgent - Foundation for all extraction agents
- BasePipeline - Common pipeline interface
- BaseValidator - Validation framework
- BaseAnalyzer - Intelligence analysis framework

### **Interfaces**
- IDetector - Detection interface contract
- IExtractor - Extraction interface contract
- IAnalyzer - Analysis interface contract
- IValidator - Validation interface contract

### **Utilities**
- File I/O operations
- JSON/YAML configuration management
- Logging and monitoring
- Error handling
- Type definitions

## 📁 Directory Structure

```
common/
├── src/
│   ├── base/                  # Base classes
│   │   ├── base_agent.py
│   │   ├── base_pipeline.py
│   │   ├── base_validator.py
│   │   └── base_analyzer.py
│   ├── interfaces/            # Common interfaces
│   │   ├── detector.py
│   │   ├── extractor.py
│   │   ├── analyzer.py
│   │   └── validator.py
│   └── utilities/             # Shared utilities
│       ├── file_io.py
│       ├── config_manager.py
│       ├── logger.py
│       ├── error_handler.py
│       └── type_definitions.py
├── tests/
│   ├── test_base_classes.py
│   ├── test_interfaces.py
│   └── test_utilities.py
└── docs/
    ├── base_classes.md
    ├── interfaces.md
    └── utilities.md
```

## 🔧 Base Classes

### **BaseExtractionAgent**
Foundation class for all extraction agents across pipelines.

```python
from common.base import BaseExtractionAgent

class MyExtractor(BaseExtractionAgent):
    def __init__(self, config):
        super().__init__(config)

    def detect(self, document):
        # Detection logic
        pass

    def extract(self, document, zones):
        # Extraction logic
        pass

    def validate(self, results):
        # Validation logic
        pass
```

### **BasePipeline**
Common pipeline interface for all three pipelines.

```python
from common.base import BasePipeline

class MyPipeline(BasePipeline):
    def __init__(self, config_path):
        super().__init__(config_path)

    def process(self, input_data):
        # Pipeline processing logic
        pass

    def save_results(self, results, output_path):
        # Save results
        pass
```

## 🔌 Interfaces

### **IDetector**
Detection interface contract for all detectors.

```python
from common.interfaces import IDetector

class YOLODetector(IDetector):
    def detect(self, document):
        # Return zones with bboxes and confidence
        pass
```

### **IExtractor**
Extraction interface contract for all extractors.

```python
from common.interfaces import IExtractor

class EquationExtractor(IExtractor):
    def extract(self, document, zones):
        # Extract content from zones
        pass
```

## 🛠️ Utilities

### **ConfigManager**
YAML/JSON configuration management.

```python
from common.utilities import ConfigManager

config = ConfigManager.load("config/pipeline_config.yaml")
value = config.get("extraction.detection.yolo.confidence_threshold", default=0.5)
```

### **Logger**
Structured logging across all pipelines.

```python
from common.utilities import Logger

logger = Logger.get_logger(__name__)
logger.info("Pipeline started", extra={"pipeline": "extraction_v14_P1"})
```

### **ErrorHandler**
Consistent error handling and reporting.

```python
from common.utilities import ErrorHandler

try:
    result = risky_operation()
except Exception as e:
    ErrorHandler.handle(
        exception=e,
        context={"operation": "equation_extraction", "page": 5}
    )
```

## 📊 Type Definitions

Common type definitions shared across pipelines:

```python
from common.utilities.type_definitions import (
    BBox,
    Zone,
    ExtractionResult,
    SemanticChunk,
    KnowledgeGraphNode,
    KnowledgeGraphEdge
)

# Type-safe usage across all pipelines
bbox: BBox = {"x0": 100.5, "y0": 200.0, "x1": 300.5, "y1": 400.0}
zone: Zone = {"bbox": bbox, "page": 1, "confidence": 0.95}
```

## 🔗 Pipeline Integration

All three pipelines depend on `common/`:

```python
# extraction_v14_P1 uses common
from common.base import BaseExtractionAgent
from common.interfaces import IDetector, IExtractor

# rag_v14_P2 uses common
from common.base import BaseAnalyzer
from common.utilities import ConfigManager

# curation_v14_P3 uses common
from common.base import BaseValidator
from common.utilities import Logger
```

## 📝 Installation

```bash
cd /home/thermodynamics/document_translator_v14/common
pip install -e .
```

This makes common utilities available to all pipelines:
```python
# Can be imported from any pipeline
from common.base import BaseExtractionAgent
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/test_base_classes.py
pytest tests/test_interfaces.py
pytest tests/test_utilities.py

# Test common utilities work in each pipeline
pytest ../extraction_v14_P1/tests/test_common_integration.py
pytest ../rag_v14_P2/tests/test_common_integration.py
pytest ../curation_v14_P3/tests/test_common_integration.py
```

## 📚 Documentation

- **Base Classes**: `docs/base_classes.md`
- **Interfaces**: `docs/interfaces.md`
- **Utilities**: `docs/utilities.md`
- **Type Definitions**: `docs/type_definitions.md`

---

**Status**: Phase 0 - Foundation setup in progress
**Next**: Implement base classes and interfaces for use by all pipelines
