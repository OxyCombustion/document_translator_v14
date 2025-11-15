"""
Structure-Based Table Validation Framework
Uses document structure analysis to validate table extractions vs false positives
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

# Import our analyzers
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents.mathematica_agent.document_structure_analyzer import MathematicaDocumentAnalyzer

logger = logging.getLogger(__name__)


class StructureBasedValidator:
    """
    Validates table extractions using document structure analysis
    
    Strategy:
    1. Use Mathematica/fallback to identify likely table zones (32 found vs 177 extracted)
    2. Compare extracted tables against these structural zones
    3. Flag extractions that don't align with document structure
    4. Provide confidence scores based on structural evidence
    """
    
    def __init__(self):
        self.structure_analyzer = MathematicaDocumentAnalyzer()
        self.validation_criteria = {
            "min_table_area": 5000,  # Minimum area for a valid table
            "max_aspect_ratio": 4.0,  # Maximum width/height ratio
            "min_aspect_ratio": 0.3,  # Minimum width/height ratio
            "min_rows": 2,  # Minimum number of rows
            "min_cols": 2,  # Minimum number of columns
        }
        
    def validate_extractions(self, pdf_path: str, extraction_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate table extractions against document structure
        
        Args:
            pdf_path: Path to original PDF
            extraction_results: List of extracted table results
            
        Returns:
            Validation report with scores and recommendations
        """
        start_time = time.time()
        
        # Get document structure overview
        print("📊 Analyzing document structure...")
        structure = self.structure_analyzer.analyze_document_structure(pdf_path)
        
        # Get table zones
        print("🎯 Identifying structural table zones...")
        table_zones = self.structure_analyzer.identify_table_zones(pdf_path)
        
        # Validate each extraction
        print(f"🔍 Validating {len(extraction_results)} extractions...")
        validation_results = []
        
        for i, extraction in enumerate(extraction_results):
            validation = self._validate_single_extraction(extraction, structure, table_zones)
            validation["extraction_id"] = i
            validation_results.append(validation)
        
        # Generate summary
        summary = self._generate_validation_summary(validation_results, structure, extraction_results)
        
        validation_time = time.time() - start_time
        
        return {
            "document_structure": structure,
            "table_zones": table_zones,
            "extraction_validations": validation_results,
            "summary": summary,
            "validation_time": validation_time,
            "timestamp": time.time()
        }
    
    def _validate_single_extraction(self, extraction: Dict[str, Any], 
                                   structure: Dict[str, Any], 
                                   table_zones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a single table extraction
        
        Returns validation scores and flags
        """
        validation = {
            "is_valid_table": False,
            "confidence_score": 0.0,
            "validation_flags": [],
            "structural_alignment": 0.0,
            "content_quality": 0.0,
            "geometric_validity": 0.0
        }
        
        # 1. Content Quality Analysis
        content_score = self._analyze_content_quality(extraction)
        validation["content_quality"] = content_score
        
        # 2. Geometric Validity
        geometric_score = self._analyze_geometric_validity(extraction)
        validation["geometric_validity"] = geometric_score
        
        # 3. Structural Alignment (if we have table zones)
        if table_zones:
            alignment_score = self._analyze_structural_alignment(extraction, table_zones)
            validation["structural_alignment"] = alignment_score
        else:
            # Use document-level statistics
            validation["structural_alignment"] = self._estimate_alignment_from_structure(extraction, structure)
        
        # 4. Overall validation
        overall_score = (content_score * 0.4 + geometric_score * 0.3 + validation["structural_alignment"] * 0.3)
        validation["confidence_score"] = overall_score
        validation["is_valid_table"] = overall_score > 0.6
        
        return validation
    
    def _analyze_content_quality(self, extraction: Dict[str, Any]) -> float:
        """
        Analyze the quality of extracted content
        
        Real tables should have:
        - Multiple rows and columns
        - Consistent structure
        - Tabular data (not flowing text)
        """
        score = 0.0
        flags = []
        
        rows = extraction.get("rows", [])
        headers = extraction.get("headers", [])
        
        # Check for minimum table structure
        if len(rows) >= self.validation_criteria["min_rows"]:
            score += 0.3
        else:
            flags.append("insufficient_rows")
        
        # Check for consistent column count
        if rows:
            col_counts = [len(row) for row in rows if isinstance(row, list)]
            if col_counts:
                max_cols = max(col_counts)
                min_cols = min(col_counts)
                
                if max_cols >= self.validation_criteria["min_cols"]:
                    score += 0.2
                
                # Consistency bonus
                if max_cols == min_cols:
                    score += 0.2
                elif max_cols - min_cols <= 1:
                    score += 0.1
                else:
                    flags.append("inconsistent_columns")
        
        # Check for flowing text vs tabular data
        text_content = self._extract_text_content(extraction)
        if self._is_flowing_text(text_content):
            score = max(0, score - 0.4)  # Major penalty for flowing text
            flags.append("flowing_text_detected")
        else:
            score += 0.3
        
        return min(1.0, score)
    
    def _analyze_geometric_validity(self, extraction: Dict[str, Any]) -> float:
        """
        Analyze geometric properties for table validity
        """
        score = 0.0
        
        spatial = extraction.get("spatial", {})
        if not spatial:
            return 0.1  # Low score if no spatial info
        
        width = spatial.get("width", 0)
        height = spatial.get("height", 0)
        area = spatial.get("area", width * height)
        
        # Check minimum area
        if area >= self.validation_criteria["min_table_area"]:
            score += 0.4
        
        # Check aspect ratio
        if width > 0 and height > 0:
            aspect_ratio = width / height
            if (self.validation_criteria["min_aspect_ratio"] <= aspect_ratio <= 
                self.validation_criteria["max_aspect_ratio"]):
                score += 0.3
            else:
                score = max(0, score - 0.2)
        
        # Reasonable position on page
        page_x = spatial.get("x", 0)
        page_y = spatial.get("y", 0)
        
        # Not too close to edges (likely content, not margins)
        if page_x > 20 and page_y > 20:
            score += 0.3
        
        return min(1.0, score)
    
    def _analyze_structural_alignment(self, extraction: Dict[str, Any], 
                                    table_zones: List[Dict[str, Any]]) -> float:
        """
        Check if extraction aligns with identified table zones
        """
        extraction_spatial = extraction.get("spatial", {})
        if not extraction_spatial:
            return 0.1
        
        ext_x = extraction_spatial.get("x", 0)
        ext_y = extraction_spatial.get("y", 0)
        ext_w = extraction_spatial.get("width", 0)
        ext_h = extraction_spatial.get("height", 0)
        
        best_alignment = 0.0
        
        for zone in table_zones:
            zone_bbox = zone.get("bbox", [])
            if len(zone_bbox) >= 4:
                # Calculate overlap
                overlap = self._calculate_bbox_overlap(
                    [ext_x, ext_y, ext_x + ext_w, ext_y + ext_h],
                    zone_bbox
                )
                alignment = overlap * zone.get("confidence", 0.5)
                best_alignment = max(best_alignment, alignment)
        
        return best_alignment
    
    def _estimate_alignment_from_structure(self, extraction: Dict[str, Any], 
                                         structure: Dict[str, Any]) -> float:
        """
        Estimate alignment based on document-level structure when zones unavailable
        """
        # Use document type to estimate likelihood
        doc_type = structure.get("document_type", "unknown")
        total_table_regions = structure.get("total_table_regions", 0)
        total_text_regions = structure.get("total_text_regions", 0)
        
        # Base score from document type
        if doc_type == "table_heavy":
            base_score = 0.7
        elif doc_type == "mixed_content":
            base_score = 0.5
        elif doc_type == "text_with_tables":
            base_score = 0.3
        else:
            base_score = 0.1
        
        # Adjust based on extraction quality
        content_quality = self._analyze_content_quality(extraction)
        return min(1.0, base_score * (0.5 + 0.5 * content_quality))
    
    def _extract_text_content(self, extraction: Dict[str, Any]) -> str:
        """Extract all text content from extraction"""
        text_parts = []
        
        rows = extraction.get("rows", [])
        for row in rows:
            if isinstance(row, list):
                text_parts.extend([str(cell) for cell in row])
            else:
                text_parts.append(str(row))
        
        headers = extraction.get("headers", [])
        text_parts.extend([str(h) for h in headers])
        
        return " ".join(text_parts)
    
    def _is_flowing_text(self, text: str) -> bool:
        """
        Detect if content is flowing text rather than tabular data
        
        Indicators of flowing text:
        - Long sentences
        - Common text words
        - Narrative structure
        """
        if not text or len(text) < 50:
            return False
        
        # Check for narrative indicators
        narrative_indicators = [
            "the", "and", "of", "to", "a", "in", "for", "is", "on", "that", "by", "this", "with", "as"
        ]
        
        words = text.lower().split()
        if len(words) < 10:
            return False
        
        narrative_count = sum(1 for word in words if word in narrative_indicators)
        narrative_ratio = narrative_count / len(words)
        
        # If more than 30% are common narrative words, likely flowing text
        return narrative_ratio > 0.3
    
    def _calculate_bbox_overlap(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate overlap ratio between two bounding boxes"""
        if len(bbox1) < 4 or len(bbox2) < 4:
            return 0.0
        
        # bbox format: [x1, y1, x2, y2]
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x1 >= x2 or y1 >= y2:
            return 0.0  # No overlap
        
        overlap_area = (x2 - x1) * (y2 - y1)
        bbox1_area = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        
        return overlap_area / bbox1_area if bbox1_area > 0 else 0.0
    
    def _generate_validation_summary(self, validations: List[Dict[str, Any]], 
                                   structure: Dict[str, Any], 
                                   extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate validation summary and recommendations"""
        
        total_extractions = len(extractions)
        valid_extractions = sum(1 for v in validations if v["is_valid_table"])
        
        avg_confidence = sum(v["confidence_score"] for v in validations) / total_extractions if total_extractions > 0 else 0
        
        # Expected vs actual analysis
        expected_tables = structure.get("total_table_regions", 0)
        actual_extractions = total_extractions
        
        false_positive_rate = max(0, (actual_extractions - expected_tables) / actual_extractions) if actual_extractions > 0 else 0
        
        return {
            "total_extractions": total_extractions,
            "valid_extractions": valid_extractions,
            "invalid_extractions": total_extractions - valid_extractions,
            "average_confidence": avg_confidence,
            "expected_table_count": expected_tables,
            "false_positive_rate": false_positive_rate,
            "validation_success_rate": valid_extractions / total_extractions if total_extractions > 0 else 0,
            "recommendations": self._generate_recommendations(validations, structure, false_positive_rate)
        }
    
    def _generate_recommendations(self, validations: List[Dict[str, Any]], 
                                structure: Dict[str, Any], 
                                false_positive_rate: float) -> List[str]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        if false_positive_rate > 0.5:
            recommendations.append("HIGH PRIORITY: Reduce false positives - consider stricter table detection criteria")
        
        low_content_quality = sum(1 for v in validations if v["content_quality"] < 0.4)
        if low_content_quality > len(validations) * 0.3:
            recommendations.append("Improve content quality filtering - many extractions contain flowing text")
        
        low_geometric_validity = sum(1 for v in validations if v["geometric_validity"] < 0.4)
        if low_geometric_validity > len(validations) * 0.3:
            recommendations.append("Review geometric criteria - many extractions have invalid dimensions")
        
        doc_type = structure.get("document_type", "unknown")
        if doc_type == "mixed_content":
            recommendations.append("Document has mixed content - consider page-by-page analysis")
        
        return recommendations


def main():
    """Test the structure-based validator with our Chapter 4 results"""
    import sys
    import io
    
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    validator = StructureBasedValidator()
    
    # Load our previous extraction results
    results_path = "results/Ch-04_Heat_Transfer_enhanced_tables.json"
    
    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            extraction_results = json.load(f)
    except FileNotFoundError:
        print(f"❌ Results file not found: {results_path}")
        print("Please run table extraction first")
        return
    
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    print("🔍 Structure-Based Table Validation")
    print("=" * 50)
    print(f"📄 Document: {Path(pdf_path).name}")
    print(f"📊 Extractions to validate: {len(extraction_results)}")
    
    # Run validation
    validation_report = validator.validate_extractions(pdf_path, extraction_results)
    
    # Print results
    summary = validation_report["summary"]
    print(f"\n📈 Validation Results:")
    print(f"  Total Extractions: {summary['total_extractions']}")
    print(f"  Valid Tables: {summary['valid_extractions']}")
    print(f"  Invalid/False Positives: {summary['invalid_extractions']}")
    print(f"  Average Confidence: {summary['average_confidence']:.2f}")
    print(f"  Expected Table Count: {summary['expected_table_count']}")
    print(f"  False Positive Rate: {summary['false_positive_rate']:.1%}")
    
    print(f"\n💡 Recommendations:")
    for i, rec in enumerate(summary['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    # Save validation report
    output_path = "results/Ch-04_Heat_Transfer_validation_report.json"
    with open(output_path, 'w') as f:
        json.dump(validation_report, f, indent=2, default=str)
    
    print(f"\n💾 Validation report saved: {output_path}")
    
    # Show examples of valid vs invalid extractions
    validations = validation_report["extraction_validations"]
    
    print(f"\n✅ Example Valid Tables (confidence > 0.6):")
    valid_examples = [v for v in validations if v["is_valid_table"]][:3]
    for v in valid_examples:
        print(f"  Table {v['extraction_id']}: confidence={v['confidence_score']:.2f}")
    
    print(f"\n❌ Example Invalid/False Positives (confidence < 0.6):")
    invalid_examples = [v for v in validations if not v["is_valid_table"]][:3]
    for v in invalid_examples:
        print(f"  Table {v['extraction_id']}: confidence={v['confidence_score']:.2f}")


if __name__ == "__main__":
    main()