"""
Relationship detection source modules.

Citation detection, variable analysis, dependency tracking, and code generation.
"""

from . import citations
from . import variables
from . import dependencies
from . import generators
from . import data_structures

__all__ = [
    'citations',
    'variables',
    'dependencies',
    'generators',
    'data_structures',
]
