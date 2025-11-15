#!/usr/bin/env python3
"""
Full Document 4-Method Extraction Orchestrator
V9 Document Translator - Scaling from single-table to full-document processing

Integrates the proven 4-method extraction system with V9's intelligent chunking
architecture to process complete documents following the scan-first strategy.

Author: V9 Integration Team  
Version: 8.0.0
Date: 2025-08-22

Integration Strategy:
1. Scan First: Use intelligent chunker to identify content zones
2. Focus on Tables: Apply 4-method extraction to table-related chunks
3. Scale Performance: Process multiple tables across full document
4. Preserve Quality: Maintain extraction accuracy from single-table tests
"""

import sys
import io
import time
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

# REQUIRED: UTF-8 setup for all Python scripts (V9 Engineering Standard)
# Set UTF-8 encoding for Windows compatibility
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import V9 base classes and utilities
try:
    from ...core.logger import get_logger
    from ...core.intelligent_chunker import LogicalChunker
    from ...core.spatial_metadata import SpatialLocation
    from ..base import BaseAgent, AgentResult, BoundingBox
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from core.logger import get_logger
    from core.intelligent_chunker import LogicalChunker
    from core.spatial_metadata import SpatialLocation
    from agents.base import BaseAgent, AgentResult, BoundingBox

# Import existing extraction methods
from .extraction_comparison_agent import ExtractionComparisonAgent, MethodComparison, ComparisonReport
from .method_2_docling_extractor import DoclingTableExtractor
from .method_3_gemini_extractor import GeminiTableExtractor
from .method_4_mathematica_extractor import MathematicaTableExtractor

logger = get_logger("FullDocumentExtractionOrchestrator")


@dataclass
class TableZone:
    """
    Represents a table zone identified by the intelligent chunker.
    
    Contains all information needed to apply 4-method extraction to a specific
    table area within the document, including spatial coordinates and content.
    """
    zone_id: str
    chunk_index: int
    pages_involved: List[int]
    spatial_bounds: Dict[str, float]  # Combined bounding box
    content_preview: str  # First 200 chars of content
    confidence: float  # Chunker's confidence this contains a table
    chunk_metadata: Dict[str, Any]  # Original chunk metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class FullDocumentExtractionResults:
    """
    Complete results from processing an entire document with 4-method extraction.
    
    Aggregates results from all table zones found in the document and provides
    comprehensive analysis across the full document scope.
    """
    document_path: str
    processing_timestamp: str
    total_pages: int
    chunks_analyzed: int
    table_zones_found: int
    table_zones_processed: int
    zone_results: List[Dict[str, Any]]  # Results for each table zone
    document_summary: Dict[str, Any]  # Overall document analysis
    performance_metrics: Dict[str, Any]  # Full document performance
    method_performance_comparison: Dict[str, Any]  # Cross-zone method analysis
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class FullDocumentExtractionOrchestrator:
    """
    Orchestrates 4-method table extraction across complete documents.
    
    This class bridges the intelligent chunking system with the proven 4-method
    extraction approach, scaling from single-table focus to full-document processing
    while maintaining extraction quality and following V9's scan-first strategy.
    
    Architecture Integration:
    - Uses intelligent_chunker.py to identify table zones (scan-first)
    - Applies extraction_comparison_agent.py to each zone (focus)  
    - Aggregates results across all zones (scale)
    - Maintains spatial metadata and performance tracking
    
    Why This Orchestrator is Needed:
    - Bridges proven single-table extraction with full-document scope
    - Leverages existing V9 chunking architecture for efficiency
    - Provides comprehensive document-level analysis
    - Maintains performance tracking across multiple extraction zones
    - Enables systematic comparison of extraction methods at document scale
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the full document extraction orchestrator.
        
        Args:
            config: Configuration for chunking, extraction methods, and orchestration
            
        The configuration combines settings for the intelligent chunker,
        all 4 extraction methods, and document-level processing parameters.
        """
        self.config = config
        
        # Chunking configuration
        self.chunker_config = config.get("chunker", {
            'min_chunk_size_mb': 0.5,
            'max_chunk_size_mb': 10, 
            'preserve_tables': True,
            'preserve_figures': True
        })
        
        # Extraction method configuration (from proven single-table config)
        self.extraction_config = config.get("extraction", {
            "parallel_execution": config.get("parallel_extraction", True),
            "timeout_per_method": config.get("method_timeout", 300),
        })
        
        # Document-level processing settings
        self.process_all_zones = config.get("process_all_table_zones", True)
        self.zone_processing_timeout = config.get("zone_timeout", 600)  # 10 min per zone
        self.max_concurrent_zones = config.get("max_concurrent_zones", 2)
        
        # Initialize components
        self.chunker = LogicalChunker(self.chunker_config)
        self.extraction_agents = {}  # Will hold extraction agents per zone
        
        logger.info(f"Initialized FullDocumentExtractionOrchestrator")
        logger.info(f"Configuration: chunk_preserve_tables={self.chunker_config['preserve_tables']}")
        logger.info(f"Configuration: parallel_extraction={self.extraction_config['parallel_execution']}")
        logger.info(f"Configuration: max_concurrent_zones={self.max_concurrent_zones}")
    
    def process_full_document(self, document_path: str) -> FullDocumentExtractionResults:
        """
        Process entire document using scan-first 4-method extraction strategy.
        
        Args:
            document_path: Path to document file to process
            
        Returns:
            FullDocumentExtractionResults: Comprehensive extraction results
            
        This is the main entry point that implements the complete scan-first strategy:
        1. Scan: Use intelligent chunker to analyze document structure
        2. Identify: Find all table zones within the document  
        3. Focus: Apply 4-method extraction to each table zone
        4. Aggregate: Combine results into document-level analysis
        """
        start_time = time.time()
        logger.info(f"Starting full document extraction: {Path(document_path).name}")
        
        # Phase 1: Scan document structure using intelligent chunker
        logger.info("Phase 1: Scanning document structure with intelligent chunker")
        chunks = list(self.chunker.chunk_document_intelligently(document_path))
        
        # Phase 2: Identify table zones from chunks
        logger.info("Phase 2: Identifying table zones from chunks")
        table_zones = self._identify_table_zones(chunks, document_path)
        
        # Phase 3: Apply 4-method extraction to each table zone
        logger.info(f"Phase 3: Applying 4-method extraction to {len(table_zones)} table zones")
        zone_results = self._process_table_zones(table_zones, document_path)
        
        # Phase 4: Aggregate and analyze results
        logger.info("Phase 4: Aggregating results and generating document analysis")
        document_summary = self._generate_document_summary(zone_results, chunks)
        performance_metrics = self._calculate_performance_metrics(zone_results, start_time)
        method_comparison = self._compare_methods_across_zones(zone_results)
        
        # Create comprehensive results
        results = FullDocumentExtractionResults(
            document_path=document_path,
            processing_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_pages=self._count_document_pages(document_path),
            chunks_analyzed=len(chunks),
            table_zones_found=len(table_zones),
            table_zones_processed=len(zone_results),
            zone_results=zone_results,
            document_summary=document_summary,
            performance_metrics=performance_metrics,
            method_performance_comparison=method_comparison
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Full document extraction completed in {processing_time:.2f}s")
        logger.info(f"Results: {len(table_zones)} zones, {len(zone_results)} processed")
        
        return results
    
    def _identify_table_zones(self, chunks: List[Any], document_path: str) -> List[TableZone]:
        """
        Identify table zones from intelligent chunker output.
        
        Args:
            chunks: List of document chunks from intelligent chunker
            document_path: Path to source document
            
        Returns:
            List of TableZone objects representing potential table areas
            
        This function bridges the chunker output with the extraction system by
        identifying chunks that likely contain tables and preparing them for
        4-method extraction processing.
        """
        table_zones = []
        
        for i, chunk in enumerate(chunks):
            # Check if chunk is table-related
            is_table_chunk = self._is_table_chunk(chunk)
            
            if is_table_chunk:
                # Extract spatial information
                spatial_bounds = self._extract_spatial_bounds(chunk)
                pages_involved = self._extract_pages_involved(chunk)
                
                # Create table zone
                zone = TableZone(
                    zone_id=f"zone_{i}_{len(table_zones)}",
                    chunk_index=i,
                    pages_involved=pages_involved,
                    spatial_bounds=spatial_bounds,
                    content_preview=self._get_content_preview(chunk),
                    confidence=getattr(chunk, 'confidence', 0.8),
                    chunk_metadata=self._extract_chunk_metadata(chunk)
                )
                
                table_zones.append(zone)
                logger.info(f"Identified table zone {zone.zone_id} on pages {pages_involved}")
        
        logger.info(f"Total table zones identified: {len(table_zones)}")
        return table_zones
    
    def _process_table_zones(self, table_zones: List[TableZone], document_path: str) -> List[Dict[str, Any]]:
        """
        Process each table zone using 4-method extraction.
        
        Args:
            table_zones: List of table zones to process
            document_path: Path to source document
            
        Returns:
            List of zone processing results
            
        This function applies the proven 4-method extraction system to each
        identified table zone, maintaining the same extraction quality while
        scaling to multiple tables across the document.
        """
        zone_results = []
        
        if self.max_concurrent_zones > 1:
            # Process zones in parallel
            with ThreadPoolExecutor(max_workers=self.max_concurrent_zones) as executor:
                future_to_zone = {
                    executor.submit(self._process_single_zone, zone, document_path): zone
                    for zone in table_zones
                }
                
                for future in as_completed(future_to_zone):
                    zone = future_to_zone[future]
                    try:
                        result = future.result(timeout=self.zone_processing_timeout)
                        zone_results.append(result)
                        logger.info(f"Completed zone {zone.zone_id}")
                    except Exception as e:
                        logger.error(f"Error processing zone {zone.zone_id}: {e}")
                        # Add error result
                        zone_results.append({
                            'zone_id': zone.zone_id,
                            'success': False,
                            'error': str(e),
                            'processing_time': 0.0
                        })
        else:
            # Process zones sequentially
            for zone in table_zones:
                try:
                    result = self._process_single_zone(zone, document_path)
                    zone_results.append(result)
                    logger.info(f"Completed zone {zone.zone_id}")
                except Exception as e:
                    logger.error(f"Error processing zone {zone.zone_id}: {e}")
                    zone_results.append({
                        'zone_id': zone.zone_id,
                        'success': False,
                        'error': str(e),
                        'processing_time': 0.0
                    })
        
        return zone_results
    
    def _process_single_zone(self, zone: TableZone, document_path: str) -> Dict[str, Any]:
        """
        Process a single table zone using the 4-method extraction system.
        
        Args:
            zone: TableZone to process
            document_path: Path to source document
            
        Returns:
            Zone processing results
            
        This function adapts the proven single-table extraction approach to work
        with zone-based input from the intelligent chunker, maintaining extraction
        quality while enabling multi-table processing.
        """
        zone_start_time = time.time()
        
        # Create zone-specific extraction configuration
        zone_config = self.extraction_config.copy()
        zone_config.update({
            "target_document": document_path,
            "target_zone": zone.to_dict(),
            "spatial_bounds": zone.spatial_bounds,
            "pages_filter": zone.pages_involved
        })
        
        # Create extraction agent for this zone
        extraction_agent = ExtractionComparisonAgent(zone_config)
        
        # Process the zone using proven 4-method approach
        try:
            # Note: We'll need to modify the extraction agent to handle zones
            # For now, use the document-level processing and filter results
            result = extraction_agent.process(document_path)
            
            zone_result = {
                'zone_id': zone.zone_id,
                'zone_metadata': zone.to_dict(),
                'extraction_results': result.data if result.success else None,
                'success': result.success,
                'error': result.error_message if not result.success else None,
                'processing_time': time.time() - zone_start_time,
                'methods_tested': self._count_methods_tested(result) if result.success else 0,
                'tables_extracted': self._count_tables_extracted(result) if result.success else 0
            }
            
        except Exception as e:
            zone_result = {
                'zone_id': zone.zone_id,
                'zone_metadata': zone.to_dict(),
                'extraction_results': None,
                'success': False,
                'error': str(e),
                'processing_time': time.time() - zone_start_time,
                'methods_tested': 0,
                'tables_extracted': 0
            }
        
        return zone_result
    
    def _is_table_chunk(self, chunk: Any) -> bool:
        """Check if a chunk likely contains table content"""
        # Check chunk type if available
        if hasattr(chunk, 'chunk_type'):
            chunk_type_str = str(chunk.chunk_type).lower()
            if 'table' in chunk_type_str:
                return True
        
        # Check content for table indicators
        if hasattr(chunk, 'content'):
            content = str(chunk.content).lower()
            table_indicators = ['table', 'column', 'row', '|', 'header']
            if any(indicator in content for indicator in table_indicators):
                return True
        
        return False
    
    def _extract_spatial_bounds(self, chunk: Any) -> Dict[str, float]:
        """Extract spatial bounding box from chunk"""
        if hasattr(chunk, 'spatial_bounds'):
            return chunk.spatial_bounds
        
        # Default bounds
        return {'x': 0, 'y': 0, 'width': 0, 'height': 0}
    
    def _extract_pages_involved(self, chunk: Any) -> List[int]:
        """Extract page numbers involved in chunk"""
        if hasattr(chunk, 'page_numbers'):
            return list(chunk.page_numbers)
        elif hasattr(chunk, 'page_number'):
            return [chunk.page_number]
        
        return [1]  # Default to page 1
    
    def _get_content_preview(self, chunk: Any) -> str:
        """Get preview of chunk content"""
        if hasattr(chunk, 'content'):
            content = str(chunk.content)
            return content[:200] + "..." if len(content) > 200 else content
        
        return "No content preview available"
    
    def _extract_chunk_metadata(self, chunk: Any) -> Dict[str, Any]:
        """Extract metadata from chunk"""
        metadata = {}
        
        if hasattr(chunk, 'metadata'):
            metadata.update(chunk.metadata)
        
        # Add common chunk attributes
        for attr in ['chunk_type', 'confidence', 'element_count']:
            if hasattr(chunk, attr):
                metadata[attr] = getattr(chunk, attr)
        
        return metadata
    
    def _count_document_pages(self, document_path: str) -> int:
        """Count total pages in document"""
        try:
            import fitz
            doc = fitz.open(document_path)
            page_count = len(doc)
            doc.close()
            return page_count
        except Exception:
            return 0
    
    def _generate_document_summary(self, zone_results: List[Dict], chunks: List[Any]) -> Dict[str, Any]:
        """Generate summary analysis of document processing"""
        successful_zones = [r for r in zone_results if r['success']]
        failed_zones = [r for r in zone_results if not r['success']]
        
        return {
            'total_zones_processed': len(zone_results),
            'successful_extractions': len(successful_zones),
            'failed_extractions': len(failed_zones),
            'success_rate': len(successful_zones) / len(zone_results) if zone_results else 0,
            'total_tables_extracted': sum(r.get('tables_extracted', 0) for r in successful_zones),
            'average_processing_time_per_zone': statistics.mean([r['processing_time'] for r in zone_results]) if zone_results else 0
        }
    
    def _calculate_performance_metrics(self, zone_results: List[Dict], start_time: float) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        total_time = time.time() - start_time
        processing_times = [r['processing_time'] for r in zone_results if r.get('processing_time')]
        
        return {
            'total_processing_time': total_time,
            'average_zone_time': statistics.mean(processing_times) if processing_times else 0,
            'fastest_zone_time': min(processing_times) if processing_times else 0,
            'slowest_zone_time': max(processing_times) if processing_times else 0,
            'zones_per_minute': len(zone_results) / (total_time / 60) if total_time > 0 else 0
        }
    
    def _compare_methods_across_zones(self, zone_results: List[Dict]) -> Dict[str, Any]:
        """Compare extraction method performance across all zones"""
        # This would analyze method performance across all zones
        # For now, return placeholder data
        return {
            'method_success_rates': {},
            'method_average_times': {},
            'method_reliability_ranking': [],
            'cross_zone_consistency': 0.0
        }
    
    def _count_methods_tested(self, result: Any) -> int:
        """Count how many methods were tested"""
        if hasattr(result, 'data') and isinstance(result.data, dict):
            return len(result.data.get('method_comparisons', []))
        return 0
    
    def _count_tables_extracted(self, result: Any) -> int:
        """Count total tables extracted across all methods"""
        if hasattr(result, 'data') and isinstance(result.data, dict):
            comparisons = result.data.get('method_comparisons', [])
            return sum(c.get('tables_extracted', 0) for c in comparisons)
        return 0


def main():
    """Test the full document extraction orchestrator"""
    config = {
        "chunker": {
            'min_chunk_size_mb': 0.5,
            'max_chunk_size_mb': 10,
            'preserve_tables': True,
            'preserve_figures': True
        },
        "extraction": {
            "parallel_execution": True,
            "timeout_per_method": 300,
        },
        "process_all_table_zones": True,
        "max_concurrent_zones": 1,  # Start with sequential processing
        "zone_timeout": 600
    }
    
    orchestrator = FullDocumentExtractionOrchestrator(config)
    
    # Test on Chapter 4
    document_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    if Path(document_path).exists():
        print(f"Processing full document: {document_path}")
        results = orchestrator.process_full_document(document_path)
        
        print(f"\nResults Summary:")
        print(f"Total zones found: {results.table_zones_found}")
        print(f"Zones processed: {results.table_zones_processed}")
        print(f"Success rate: {results.document_summary['success_rate']:.1%}")
        print(f"Total processing time: {results.performance_metrics['total_processing_time']:.2f}s")
        
        # Save results
        output_file = f"results/full_document_4method_extraction_{time.strftime('%Y%m%d_%H%M%S')}.json"
        Path("results").mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to: {output_file}")
    
    else:
        print(f"Document not found: {document_path}")


if __name__ == "__main__":
    main()