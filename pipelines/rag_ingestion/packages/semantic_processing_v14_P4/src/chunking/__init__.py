"""
Semantic-Aware Hierarchical Chunking Package

Provides intelligent document chunking that respects logical boundaries
(chapters, sections) while maintaining memory efficiency.
"""

from .data_structures import (
    SectionType,
    LogicalSection,
    ProcessingUnit,
    DocumentStructure,
    ProcessingPlan
)

from .semantic_structure_detector import (
    SemanticStructureDetector,
    StructureDetectionError
)

from .hierarchical_processing_planner import (
    HierarchicalProcessingPlanner,
    PlanningError
)

from .semantic_hierarchical_processor import (
    SemanticHierarchicalProcessor,
    ProcessingError
)

__all__ = [
    'SectionType',
    'LogicalSection',
    'ProcessingUnit',
    'DocumentStructure',
    'ProcessingPlan',
    'SemanticStructureDetector',
    'StructureDetectionError',
    'HierarchicalProcessingPlanner',
    'PlanningError',
    'SemanticHierarchicalProcessor',
    'ProcessingError'
]

__version__ = '1.0.0'
