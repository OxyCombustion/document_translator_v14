"""
Validation-Filtered Table Extractor
Applies validation framework results to reduce false positives from 177 → ~32 tables
"""

import json
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

# Import validation framework
import sys
from pipelines.rag_ingestion.packages.analysis_validation_v14_P19.src.validation.structure_based_validator import StructureBasedValidator

logger = logging.getLogger(__name__)


class ValidationFilteredExtractor:
    """
    Table extractor that applies validation-based filtering
    
    Strategy:
    1. Run standard table extraction (177 tables)
    2. Apply validation framework scoring
    3. Filter using confidence threshold (>0.6)
    4. Return only validated tables (~32 expected)
    """
    
    def __init__(self, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold
        self.validator = StructureBasedValidator()
        
    def extract_validated_tables(self, pdf_path: str, 
                                original_extractions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Extract tables with validation-based filtering
        
        Args:
            pdf_path: Path to PDF document
            original_extractions: Pre-existing extractions (if None, will load from results)
            
        Returns:
            Filtered extraction results with validation scores
        """
        start_time = time.time()
        
        # Load original extractions if not provided
        if original_extractions is None:
            original_extractions = self._load_original_extractions()
        
        print(f"📊 Starting validation-based filtering...")
        print(f"  Original extractions: {len(original_extractions)}")
        print(f"  Confidence threshold: {self.confidence_threshold}")
        
        # Run validation framework
        print("🔍 Running validation framework...")
        validation_report = self.validator.validate_extractions(pdf_path, original_extractions)
        
        # Apply filtering based on validation scores
        filtered_extractions = self._apply_validation_filtering(
            original_extractions, validation_report
        )
        
        # Generate improvement metrics
        improvement_metrics = self._calculate_improvement_metrics(
            original_extractions, filtered_extractions, validation_report
        )
        
        extraction_time = time.time() - start_time
        
        return {
            "filtered_extractions": filtered_extractions,
            "validation_report": validation_report,
            "improvement_metrics": improvement_metrics,
            "processing_time": extraction_time,
            "timestamp": time.time(),
            "confidence_threshold": self.confidence_threshold
        }
    
    def _load_original_extractions(self) -> List[Dict[str, Any]]:
        """Load original extraction results"""
        results_path = "results/Ch-04_Heat_Transfer_enhanced_tables.json"
        
        try:
            with open(results_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Original extractions not found: {results_path}")
            return []
    
    def _apply_validation_filtering(self, original_extractions: List[Dict[str, Any]], 
                                  validation_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter extractions based on validation confidence scores
        """
        validations = validation_report["extraction_validations"]
        filtered_extractions = []
        
        for i, extraction in enumerate(original_extractions):
            if i < len(validations):
                validation = validations[i]
                confidence = validation["confidence_score"]
                
                if confidence >= self.confidence_threshold:
                    # Add validation metadata to extraction
                    enhanced_extraction = extraction.copy()
                    enhanced_extraction["validation"] = {
                        "confidence_score": confidence,
                        "is_valid_table": validation["is_valid_table"],
                        "content_quality": validation["content_quality"],
                        "geometric_validity": validation["geometric_validity"],
                        "structural_alignment": validation["structural_alignment"]
                    }
                    filtered_extractions.append(enhanced_extraction)
        
        return filtered_extractions
    
    def _calculate_improvement_metrics(self, original: List[Dict[str, Any]], 
                                     filtered: List[Dict[str, Any]], 
                                     validation_report: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvement metrics"""
        
        original_count = len(original)
        filtered_count = len(filtered)
        expected_count = validation_report["document_structure"]["total_table_regions"]
        
        # Calculate reduction rate
        reduction_rate = (original_count - filtered_count) / original_count if original_count > 0 else 0
        
        # Calculate accuracy improvement
        original_false_positive_rate = validation_report["summary"]["false_positive_rate"]
        new_false_positive_rate = max(0, (filtered_count - expected_count) / filtered_count) if filtered_count > 0 else 0
        
        accuracy_improvement = original_false_positive_rate - new_false_positive_rate
        
        # Calculate average confidence
        if filtered:
            avg_confidence = sum(ext["validation"]["confidence_score"] for ext in filtered) / len(filtered)
        else:
            avg_confidence = 0.0
        
        return {
            "original_count": original_count,
            "filtered_count": filtered_count,
            "expected_count": expected_count,
            "reduction_rate": reduction_rate,
            "original_false_positive_rate": original_false_positive_rate,
            "new_false_positive_rate": new_false_positive_rate,
            "accuracy_improvement": accuracy_improvement,
            "average_confidence": avg_confidence,
            "closeness_to_expected": abs(filtered_count - expected_count) / expected_count if expected_count > 0 else 1.0
        }
    
    def test_against_expected_table1(self, filtered_extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Test filtered extractions against expected Table 1 format
        """
        # Load expected Table 1 format
        expected_path = "tests/ground_truth/ch04_table1_expected.txt"
        
        try:
            with open(expected_path, 'r', encoding='utf-8') as f:
                expected_content = f.read()
        except FileNotFoundError:
            return {"error": f"Expected Table 1 not found: {expected_path}"}
        
        # Look for thermal conductivity table
        thermal_conductivity_candidates = []
        
        for i, extraction in enumerate(filtered_extractions):
            content = self._extract_table_content(extraction)
            
            # Check for thermal conductivity indicators
            if self._matches_thermal_conductivity_table(content):
                thermal_conductivity_candidates.append({
                    "extraction_id": i,
                    "confidence": extraction.get("validation", {}).get("confidence_score", 0),
                    "content": content,
                    "match_score": self._calculate_table1_match_score(content)
                })
        
        # Sort candidates by match score
        thermal_conductivity_candidates.sort(key=lambda x: x["match_score"], reverse=True)
        
        return {
            "expected_content": expected_content,
            "candidates_found": len(thermal_conductivity_candidates),
            "best_candidates": thermal_conductivity_candidates[:3],  # Top 3 matches
            "success": len(thermal_conductivity_candidates) > 0
        }
    
    def _extract_table_content(self, extraction: Dict[str, Any]) -> str:
        """Extract text content from table extraction"""
        content_parts = []
        
        # Get headers
        headers = extraction.get("headers", [])
        if headers:
            content_parts.append(" | ".join(str(h) for h in headers))
        
        # Get rows
        rows = extraction.get("rows", [])
        for row in rows:
            if isinstance(row, list):
                content_parts.append(" | ".join(str(cell) for cell in row))
            else:
                content_parts.append(str(row))
        
        return "\n".join(content_parts)
    
    def _matches_thermal_conductivity_table(self, content: str) -> bool:
        """Check if content matches thermal conductivity table indicators"""
        content_lower = content.lower()
        
        thermal_indicators = [
            "thermal conductivity", "btu/h ft f", "w/m c", "w/m k",
            "insulating materials", "liquid metals", "pure metals",
            "gases at atmospheric", "nonmetallic"
        ]
        
        matches = sum(1 for indicator in thermal_indicators if indicator in content_lower)
        return matches >= 3  # At least 3 indicators present
    
    def _calculate_table1_match_score(self, content: str) -> float:
        """Calculate how well content matches expected Table 1"""
        content_lower = content.lower()
        
        # Expected elements in Table 1
        expected_elements = [
            "thermal conductivity", "btu/h ft f", "w/m c",
            "gases at atmospheric pressure", "0.004 to 0.70", "0.007 to 1.2",
            "insulating materials", "0.01 to 0.12", "0.02 to 0.21",
            "nonmetallic liquids", "0.05 to 0.40", "0.09 to 0.70",
            "liquid metals", "5.0 to 45", "8.6 to 78",
            "alloys", "8.0 to 70", "14 to 121",
            "pure metals", "30 to 240", "52 to 415"
        ]
        
        matches = sum(1 for element in expected_elements if element in content_lower)
        return matches / len(expected_elements)


def main():
    """Test the validation-filtered extractor"""
    import sys
    import io
    
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    extractor = ValidationFilteredExtractor(confidence_threshold=0.6)
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    print("🚀 Validation-Based Table Extraction")
    print("=" * 50)
    
    # Run validation-filtered extraction
    start_time = time.time()
    results = extractor.extract_validated_tables(pdf_path)
    
    # Print improvement metrics
    metrics = results["improvement_metrics"]
    print(f"\n📈 Improvement Results:")
    print(f"  Original extractions: {metrics['original_count']}")
    print(f"  Filtered extractions: {metrics['filtered_count']}")
    print(f"  Expected table count: {metrics['expected_count']}")
    print(f"  Reduction rate: {metrics['reduction_rate']:.1%}")
    print(f"  False positive improvement: {metrics['accuracy_improvement']:.1%}")
    print(f"  Average confidence: {metrics['average_confidence']:.2f}")
    print(f"  Closeness to expected: {(1-metrics['closeness_to_expected']):.1%}")
    
    # Test against expected Table 1
    print(f"\n🎯 Testing Against Expected Table 1...")
    table1_results = extractor.test_against_expected_table1(results["filtered_extractions"])
    
    if table1_results["success"]:
        print(f"  ✅ Found {table1_results['candidates_found']} thermal conductivity candidates")
        if table1_results["best_candidates"]:
            best = table1_results["best_candidates"][0]
            print(f"  🏆 Best match: ID {best['extraction_id']}, Score: {best['match_score']:.2f}")
    else:
        print(f"  ❌ No thermal conductivity table candidates found")
    
    # Save results
    output_path = "results/Ch-04_Heat_Transfer_validation_filtered.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved: {output_path}")
    print(f"⏱️ Processing time: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    main()