# -*- coding: utf-8 -*-
"""
Relationship Extraction Pipeline - End-to-end orchestration.

This module orchestrates the complete semantic relationship extraction process:
1. Load document metadata and extracted entities
2. Initialize core services (SemanticRegistry, ReferenceResolver, Validator)
3. Execute detectors in dependency order (Variable → Data → Cross-Ref → Citation)
4. Build knowledge graph from relationships
5. Generate RAG micro-bundles
6. Create comprehensive statistics report

Architecture:
- Single Responsibility: Pipeline orchestration only (no extraction logic)
- Dependency Injection: All detectors/services injected via constructor
- Open/Closed: Extensible through detector registration
- Low Coupling: Uses interfaces, not concrete implementations
- High Cohesion: All methods focused on pipeline coordination

Author: V12 Development Team
Created: 2025-11-06
Last Updated: 2025-11-06
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import time

# Set UTF-8 encoding for Windows console
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

# Third-party imports
import yaml
from tqdm import tqdm

# Local imports
from src.core.semantic_registry import SemanticRegistry
from src.core.reference_resolver import ReferenceResolver
from src.validators.relationship_validator import RelationshipValidator
from src.detectors.variable_definition_detector import VariableDefinitionDetector
from src.detectors.data_dependency_detector import DataDependencyDetector
from src.detectors.cross_reference_detector import CrossReferenceDetector
from src.detectors.citation_detector import CitationDetector
from src.exporters.rag_micro_bundle_generator import MicroBundleGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========== Custom Exceptions ==========

class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class DetectorFailureError(PipelineError):
    """Raised when a detector fails."""
    pass


class ValidationFailureError(PipelineError):
    """Raised when validation fails critically."""
    pass


# ========== Data Structures ==========

@dataclass
class PipelineConfig:
    """Pipeline configuration loaded from YAML."""

    # Paths
    input_metadata_path: Path
    input_chunks_path: Path
    input_entities_path: Path
    output_relationships_dir: Path
    output_knowledge_graph_dir: Path
    output_rag_dir: Path
    output_reports_dir: Path

    # Service configs
    semantic_registry_config: Path
    reference_resolver_config: Path
    validator_config: Path

    # Detector configs
    variable_detector_config: Dict[str, Any]
    data_dependency_detector_config: Dict[str, Any]
    cross_reference_detector_config: Dict[str, Any]
    citation_detector_config: Dict[str, Any]

    # RAG bundle config
    rag_bundle_config: Dict[str, Any]

    # Knowledge graph config
    knowledge_graph_config: Dict[str, Any]

    # Execution settings
    execution_config: Dict[str, Any]

    # Quality thresholds
    quality_thresholds: Dict[str, Any]

    @classmethod
    def from_yaml(cls, config_path: Path) -> 'PipelineConfig':
        """Load configuration from YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Extract paths
        paths = config['paths']
        input_cfg = paths['input']
        output_cfg = paths['output']

        # Extract service configs
        services = config['services']

        # Extract detector configs
        detectors = config['detectors']

        return cls(
            # Input paths
            input_metadata_path=Path(input_cfg['metadata']),
            input_chunks_path=Path(input_cfg['chunks']),
            input_entities_path=Path(input_cfg['entities']),

            # Output paths
            output_relationships_dir=Path(output_cfg['relationships']),
            output_knowledge_graph_dir=Path(output_cfg['knowledge_graph']),
            output_rag_dir=Path(output_cfg['rag_output']),
            output_reports_dir=Path(output_cfg['reports']),

            # Service configs
            semantic_registry_config=Path(services['semantic_registry']['config_path']),
            reference_resolver_config=Path(services['reference_resolver']['config_path']),
            validator_config=Path(services['validator']['config_path']),

            # Detector configs
            variable_detector_config=detectors['variable_definitions'],
            data_dependency_detector_config=detectors['data_dependencies'],
            cross_reference_detector_config=detectors['cross_references'],
            citation_detector_config=detectors['citations'],

            # RAG and graph configs
            rag_bundle_config=config['rag_bundles'],
            knowledge_graph_config=config['knowledge_graph'],

            # Execution and quality
            execution_config=config['execution'],
            quality_thresholds=config['quality_thresholds']
        )


@dataclass
class PipelineResult:
    """Results from pipeline execution."""

    success: bool
    total_time_seconds: float

    # Detector results
    variable_definitions_count: int = 0
    data_dependencies_count: int = 0
    cross_references_count: int = 0
    citations_count: int = 0

    # Detector execution times
    variable_definitions_time: float = 0.0
    data_dependencies_time: float = 0.0
    cross_references_time: float = 0.0
    citations_time: float = 0.0

    # Knowledge graph results
    graph_nodes: int = 0
    graph_edges: int = 0
    graph_build_time: float = 0.0

    # RAG bundle results
    rag_bundles_count: int = 0
    rag_bundle_time: float = 0.0

    # Validation results
    validation_passes: int = 0
    validation_warnings: int = 0
    validation_failures: int = 0

    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'total_time_seconds': self.total_time_seconds,
            'detector_results': {
                'variable_definitions': {
                    'count': self.variable_definitions_count,
                    'time_seconds': self.variable_definitions_time
                },
                'data_dependencies': {
                    'count': self.data_dependencies_count,
                    'time_seconds': self.data_dependencies_time
                },
                'cross_references': {
                    'count': self.cross_references_count,
                    'time_seconds': self.cross_references_time
                },
                'citations': {
                    'count': self.citations_count,
                    'time_seconds': self.citations_time
                }
            },
            'knowledge_graph': {
                'nodes': self.graph_nodes,
                'edges': self.graph_edges,
                'build_time_seconds': self.graph_build_time
            },
            'rag_bundles': {
                'count': self.rag_bundles_count,
                'generation_time_seconds': self.rag_bundle_time
            },
            'validation': {
                'passes': self.validation_passes,
                'warnings': self.validation_warnings,
                'failures': self.validation_failures
            },
            'errors': self.errors,
            'warnings': self.warnings
        }


# ========== Pipeline Orchestrator ==========

class RelationshipExtractionPipeline:
    """
    End-to-end semantic relationship extraction pipeline.

    Orchestrates the complete process from document metadata to knowledge graph:
    1. Initialize core services (dependency injection)
    2. Execute detectors in priority order
    3. Build knowledge graph from relationships
    4. Generate RAG micro-bundles
    5. Create comprehensive statistics report

    Architecture:
    - Coordination only (no extraction logic)
    - Dependency injection (all services/detectors injected)
    - Error recovery (continue_on_error mode)
    - Progress tracking (tqdm integration)
    - Checkpointing (save intermediate results)
    """

    def __init__(
        self,
        config: PipelineConfig,
        semantic_registry: Optional[SemanticRegistry] = None,
        reference_resolver: Optional[ReferenceResolver] = None,
        validator: Optional[RelationshipValidator] = None
    ):
        """
        Initialize pipeline with configuration and optional service injection.

        Args:
            config: Pipeline configuration
            semantic_registry: Optional pre-initialized SemanticRegistry
            reference_resolver: Optional pre-initialized ReferenceResolver
            validator: Optional pre-initialized RelationshipValidator
        """
        self.config = config

        # Initialize core services (with dependency injection)
        self.semantic_registry = semantic_registry or SemanticRegistry(
            config.semantic_registry_config
        )
        self.reference_resolver = reference_resolver or ReferenceResolver(
            config.reference_resolver_config
        )
        self.validator = validator or RelationshipValidator(
            config.validator_config
        )

        # Create output directories
        self._create_output_directories()

        # Initialize detectors (dependency injection of services)
        self._initialize_detectors()

        # Initialize RAG bundle generator
        if config.rag_bundle_config['enabled']:
            self.bundle_generator = MicroBundleGenerator(
                Path(config.rag_bundle_config['config_path'])
            )
        else:
            self.bundle_generator = None

        logger.info("Pipeline initialized successfully")

    def _create_output_directories(self):
        """Create all output directories if they don't exist."""
        dirs = [
            self.config.output_relationships_dir,
            self.config.output_knowledge_graph_dir,
            self.config.output_rag_dir,
            self.config.output_reports_dir
        ]

        if self.config.execution_config.get('enable_checkpointing'):
            dirs.append(Path(self.config.execution_config['checkpoint_dir']))

        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created {len(dirs)} output directories")

    def _initialize_detectors(self):
        """Initialize all detectors with dependency injection."""
        # 1. Variable Definition Detector
        var_cfg = self.config.variable_detector_config
        if var_cfg['enabled']:
            self.variable_detector = VariableDefinitionDetector(
                config_path=Path(var_cfg['config_path']),
                semantic_registry=self.semantic_registry,
                validator=self.validator
            )
        else:
            self.variable_detector = None

        # 2. Data Dependency Detector
        data_cfg = self.config.data_dependency_detector_config
        if data_cfg['enabled']:
            self.data_dependency_detector = DataDependencyDetector(
                config_path=Path(data_cfg['config_path']),
                semantic_registry=self.semantic_registry,
                validator=self.validator
            )
        else:
            self.data_dependency_detector = None

        # 3. Cross-Reference Detector
        xref_cfg = self.config.cross_reference_detector_config
        if xref_cfg['enabled']:
            self.cross_reference_detector = CrossReferenceDetector(
                reference_resolver=self.reference_resolver,
                validator=self.validator,
                config_path=Path(xref_cfg['config_path'])
            )
        else:
            self.cross_reference_detector = None

        # 4. Citation Detector
        cite_cfg = self.config.citation_detector_config
        if cite_cfg['enabled']:
            self.citation_detector = CitationDetector(
                reference_resolver=self.reference_resolver,
                validator=self.validator,
                config=cite_cfg
            )
        else:
            self.citation_detector = None

        logger.info("Initialized all enabled detectors")

    def run_full_pipeline(
        self,
        document_metadata: Dict[str, Any]
    ) -> PipelineResult:
        """
        Execute complete pipeline.

        Steps:
        1. Load document metadata and entities
        2. Run Variable Definition Detector
        3. Run Data Dependency Detector
        4. Run Cross-Reference Detector
        5. Run Citation Detector
        6. Build Knowledge Graph
        7. Generate RAG Bundles
        8. Generate Statistics Report

        Args:
            document_metadata: Document metadata dict

        Returns:
            PipelineResult with execution statistics

        Raises:
            PipelineError: If critical error occurs and fail_fast=True
        """
        start_time = time.time()
        result = PipelineResult(success=False, total_time_seconds=0.0)

        try:
            logger.info("=" * 80)
            logger.info("STARTING RELATIONSHIP EXTRACTION PIPELINE")
            logger.info("=" * 80)

            # Step 1: Load metadata and entities
            logger.info("\n[1/8] Loading document metadata and entities...")
            entities = self._load_entities()
            chunks = self._load_chunks()

            # Step 2: Variable Definition Detection
            if self.variable_detector:
                logger.info("\n[2/8] Detecting variable definitions...")
                var_start = time.time()
                var_results = self._run_variable_detection(entities, chunks)
                result.variable_definitions_count = len(var_results)
                result.variable_definitions_time = time.time() - var_start
                logger.info(f"✓ Found {result.variable_definitions_count} variable definitions "
                          f"in {result.variable_definitions_time:.2f}s")

            # Step 3: Data Dependency Detection
            if self.data_dependency_detector:
                logger.info("\n[3/8] Detecting data dependencies...")
                data_start = time.time()
                data_results = self._run_data_dependency_detection(entities)
                result.data_dependencies_count = len(data_results)
                result.data_dependencies_time = time.time() - data_start
                logger.info(f"✓ Found {result.data_dependencies_count} data dependencies "
                          f"in {result.data_dependencies_time:.2f}s")

            # Step 4: Cross-Reference Detection
            if self.cross_reference_detector:
                logger.info("\n[4/8] Detecting cross-references...")
                xref_start = time.time()
                xref_results = self._run_cross_reference_detection(chunks)
                result.cross_references_count = len(xref_results)
                result.cross_references_time = time.time() - xref_start
                logger.info(f"✓ Found {result.cross_references_count} cross-references "
                          f"in {result.cross_references_time:.2f}s")

            # Step 5: Citation Detection
            if self.citation_detector:
                logger.info("\n[5/8] Detecting citations...")
                cite_start = time.time()
                cite_results = self._run_citation_detection(chunks)
                result.citations_count = len(cite_results)
                result.citations_time = time.time() - cite_start
                logger.info(f"✓ Found {result.citations_count} citations "
                          f"in {result.citations_time:.2f}s")

            # Step 6: Build Knowledge Graph
            if self.config.knowledge_graph_config['enabled']:
                logger.info("\n[6/8] Building knowledge graph...")
                # This will be implemented in Phase 2
                logger.info("⚠ Knowledge graph builder not yet implemented (Phase 2)")

            # Step 7: Generate RAG Bundles
            if self.bundle_generator:
                logger.info("\n[7/8] Generating RAG micro-bundles...")
                bundle_start = time.time()
                bundle_count = self._generate_rag_bundles(entities, chunks)
                result.rag_bundles_count = bundle_count
                result.rag_bundle_time = time.time() - bundle_start
                logger.info(f"✓ Generated {result.rag_bundles_count} RAG bundles "
                          f"in {result.rag_bundle_time:.2f}s")

            # Step 8: Generate Statistics Report
            logger.info("\n[8/8] Generating statistics report...")
            # This will be implemented in Phase 4
            logger.info("⚠ Statistics reporter not yet implemented (Phase 4)")

            result.success = True
            result.total_time_seconds = time.time() - start_time

            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info(f"Total time: {result.total_time_seconds:.2f}s")
            logger.info("=" * 80)

        except Exception as e:
            result.success = False
            result.total_time_seconds = time.time() - start_time
            result.errors.append(str(e))
            logger.error(f"Pipeline failed: {e}", exc_info=True)

            if not self.config.execution_config.get('continue_on_error', True):
                raise PipelineError(f"Pipeline failed: {e}") from e

        return result

    def _load_entities(self) -> Dict[str, Any]:
        """Load extracted entities from JSON."""
        if self.config.input_entities_path.exists():
            with open(self.config.input_entities_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"Entities file not found: {self.config.input_entities_path}")
            return {}

    def _load_chunks(self) -> List[Dict[str, Any]]:
        """Load semantic chunks from JSON."""
        if self.config.input_chunks_path.exists():
            with open(self.config.input_chunks_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"Chunks file not found: {self.config.input_chunks_path}")
            return []

    def _run_variable_detection(
        self,
        entities: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run variable definition detector."""
        try:
            results = self.variable_detector.detect_from_nomenclature(chunks)

            # Save results
            output_path = Path(self.config.variable_detector_config['output_file'])
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            return results
        except Exception as e:
            logger.error(f"Variable detection failed: {e}")
            if self.config.execution_config.get('fail_fast'):
                raise DetectorFailureError(f"Variable detection failed: {e}") from e
            return []

    def _run_data_dependency_detection(
        self,
        entities: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Run data dependency detector."""
        try:
            results = self.data_dependency_detector.detect_dependencies(entities)

            # Save results
            output_path = Path(self.config.data_dependency_detector_config['output_file'])
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            return results
        except Exception as e:
            logger.error(f"Data dependency detection failed: {e}")
            if self.config.execution_config.get('fail_fast'):
                raise DetectorFailureError(f"Data dependency detection failed: {e}") from e
            return []

    def _run_cross_reference_detection(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run cross-reference detector."""
        try:
            results = self.cross_reference_detector.detect_cross_references(chunks)

            # Save results
            output_path = Path(self.config.cross_reference_detector_config['output_file'])
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([ref.to_dict() for ref in results], f, indent=2, ensure_ascii=False)

            return results
        except Exception as e:
            logger.error(f"Cross-reference detection failed: {e}")
            if self.config.execution_config.get('fail_fast'):
                raise DetectorFailureError(f"Cross-reference detection failed: {e}") from e
            return []

    def _run_citation_detection(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run citation detector."""
        try:
            results = self.citation_detector.detect_citations(chunks)

            # Save results
            output_path = Path(self.config.citation_detector_config['output_file'])
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([cite.to_dict() for cite in results], f, indent=2, ensure_ascii=False)

            return results
        except Exception as e:
            logger.error(f"Citation detection failed: {e}")
            if self.config.execution_config.get('fail_fast'):
                raise DetectorFailureError(f"Citation detection failed: {e}") from e
            return []

    def _generate_rag_bundles(
        self,
        entities: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> int:
        """Generate RAG micro-bundles."""
        try:
            # Load all relationships
            relationships = self._load_all_relationships()

            # Generate bundles
            bundles = self.bundle_generator.generate_bundles(
                entities=entities,
                chunks=chunks,
                relationships=relationships
            )

            # Save bundles
            output_path = Path(self.config.rag_bundle_config['output_file'])
            with open(output_path, 'w', encoding='utf-8') as f:
                for bundle in bundles:
                    f.write(json.dumps(bundle, ensure_ascii=False) + '\n')

            return len(bundles)
        except Exception as e:
            logger.error(f"RAG bundle generation failed: {e}")
            if self.config.execution_config.get('fail_fast'):
                raise PipelineError(f"RAG bundle generation failed: {e}") from e
            return 0

    def _load_all_relationships(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load all relationship files."""
        relationships = {}

        rel_dir = self.config.output_relationships_dir
        for rel_file in rel_dir.glob('*.json'):
            rel_type = rel_file.stem
            with open(rel_file, 'r', encoding='utf-8') as f:
                relationships[rel_type] = json.load(f)

        return relationships


# ========== Main Entry Point ==========

def main():
    """Main entry point for pipeline execution."""
    # Load configuration
    config_path = Path("config/pipeline/extraction_pipeline_config.yaml")
    config = PipelineConfig.from_yaml(config_path)

    # Initialize pipeline
    pipeline = RelationshipExtractionPipeline(config)

    # Run pipeline
    document_metadata = {
        'title': 'Chapter 4: Heat Transfer',
        'source': 'Ch-04 Heat Transfer.pdf',
        'pages': 34
    }

    result = pipeline.run_full_pipeline(document_metadata)

    # Print results
    print("\n" + "=" * 80)
    print("PIPELINE RESULTS")
    print("=" * 80)
    print(json.dumps(result.to_dict(), indent=2))

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
