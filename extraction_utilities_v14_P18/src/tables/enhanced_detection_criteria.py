"""
Enhanced Table Detection Criteria
Based on validation framework analysis to achieve target of ~32 tables
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EnhancedDetectionCriteria:
    """
    Enhanced detection criteria based on validation analysis
    
    Target: Reduce from 177 → 32 tables using stricter criteria
    """
    
    def __init__(self):
        # Updated criteria based on validation results
        self.criteria = {
            # Confidence thresholds
            "min_confidence": 0.75,  # Raised from 0.6 to be stricter
            
            # Content quality requirements
            "min_rows": 3,  # At least 3 rows for valid table
            "min_cols": 2,  # At least 2 columns
            "max_flowing_text_ratio": 0.2,  # Max 20% narrative words
            
            # Geometric requirements  
            "min_area": 10000,  # Larger minimum area
            "min_aspect_ratio": 0.2,  # More restrictive
            "max_aspect_ratio": 5.0,  # More restrictive
            
            # Structural requirements
            "min_structural_alignment": 0.3,  # Must align with document structure
            "min_content_quality": 0.5,  # Higher content quality threshold
            "min_geometric_validity": 0.6,  # Higher geometric validity
            
            # Table-specific indicators
            "required_table_indicators": 2,  # Number of table indicators needed
            "table_indicators": [
                "headers", "consistent_columns", "tabular_data",
                "numeric_data", "structured_layout", "cell_boundaries"
            ]
        }
    
    def apply_enhanced_criteria(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply enhanced criteria to achieve target table count
        """
        start_time = time.time()
        
        print("🔧 Applying Enhanced Detection Criteria")
        print("=" * 50)
        
        # Load validation results
        original_extractions = validation_results["filtered_extractions"]
        print(f"📊 Input extractions: {len(original_extractions)}")
        
        # Apply multiple filter stages
        stage1_results = self._apply_confidence_filter(original_extractions)
        stage2_results = self._apply_content_quality_filter(stage1_results)
        stage3_results = self._apply_geometric_filter(stage2_results)
        stage4_results = self._apply_structural_filter(stage3_results)
        
        # Final high-quality table set
        final_results = stage4_results
        
        processing_time = time.time() - start_time
        
        # Generate detailed metrics
        metrics = self._calculate_filtering_metrics(
            original_extractions, final_results, processing_time
        )
        
        return {
            "enhanced_extractions": final_results,
            "filtering_stages": {
                "stage1_confidence": len(stage1_results),
                "stage2_content": len(stage2_results), 
                "stage3_geometric": len(stage3_results),
                "stage4_structural": len(stage4_results)
            },
            "metrics": metrics,
            "criteria_used": self.criteria,
            "processing_time": processing_time,
            "timestamp": time.time()
        }
    
    def _apply_confidence_filter(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 1: Filter by confidence threshold"""
        filtered = []
        
        for extraction in extractions:
            validation = extraction.get("validation", {})
            confidence = validation.get("confidence_score", 0)
            
            if confidence >= self.criteria["min_confidence"]:
                filtered.append(extraction)
        
        print(f"  Stage 1 - Confidence ≥{self.criteria['min_confidence']}: {len(filtered)} tables")
        return filtered
    
    def _apply_content_quality_filter(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 2: Filter by content quality"""
        filtered = []
        
        for extraction in extractions:
            if self._passes_content_quality(extraction):
                filtered.append(extraction)
        
        print(f"  Stage 2 - Content Quality: {len(filtered)} tables")
        return filtered
    
    def _apply_geometric_filter(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 3: Filter by geometric criteria"""
        filtered = []
        
        for extraction in extractions:
            if self._passes_geometric_criteria(extraction):
                filtered.append(extraction)
        
        print(f"  Stage 3 - Geometric Validity: {len(filtered)} tables")
        return filtered
    
    def _apply_structural_filter(self, extractions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Stage 4: Filter by structural alignment"""
        filtered = []
        
        for extraction in extractions:
            validation = extraction.get("validation", {})
            structural_score = validation.get("structural_alignment", 0)
            
            if structural_score >= self.criteria["min_structural_alignment"]:
                filtered.append(extraction)
        
        print(f"  Stage 4 - Structural Alignment: {len(filtered)} tables")
        return filtered
    
    def _passes_content_quality(self, extraction: Dict[str, Any]) -> bool:
        """Check if extraction passes content quality criteria"""
        
        # Check validation content quality score
        validation = extraction.get("validation", {})
        content_quality = validation.get("content_quality", 0)
        
        if content_quality < self.criteria["min_content_quality"]:
            return False
        
        # Check row/column requirements
        rows = extraction.get("rows", [])
        if len(rows) < self.criteria["min_rows"]:
            return False
        
        # Check column consistency
        if rows:
            col_counts = [len(row) for row in rows if isinstance(row, list)]
            if col_counts:
                max_cols = max(col_counts)
                if max_cols < self.criteria["min_cols"]:
                    return False
        
        # Check for flowing text
        content = self._extract_content(extraction)
        if self._is_flowing_text(content):
            return False
        
        return True
    
    def _passes_geometric_criteria(self, extraction: Dict[str, Any]) -> bool:
        """Check if extraction passes geometric criteria"""
        
        # Check validation geometric score
        validation = extraction.get("validation", {})
        geometric_validity = validation.get("geometric_validity", 0)
        
        if geometric_validity < self.criteria["min_geometric_validity"]:
            return False
        
        # Check spatial dimensions
        spatial = extraction.get("spatial", {})
        if not spatial:
            return False
        
        area = spatial.get("area", 0)
        width = spatial.get("width", 0)
        height = spatial.get("height", 0)
        
        # Area check
        if area < self.criteria["min_area"]:
            return False
        
        # Aspect ratio check
        if width > 0 and height > 0:
            aspect_ratio = width / height
            if not (self.criteria["min_aspect_ratio"] <= aspect_ratio <= self.criteria["max_aspect_ratio"]):
                return False
        
        return True
    
    def _extract_content(self, extraction: Dict[str, Any]) -> str:
        """Extract text content from extraction"""
        content_parts = []
        
        rows = extraction.get("rows", [])
        for row in rows:
            if isinstance(row, list):
                content_parts.extend([str(cell) for cell in row])
            else:
                content_parts.append(str(row))
        
        headers = extraction.get("headers", [])
        content_parts.extend([str(h) for h in headers])
        
        return " ".join(content_parts)
    
    def _is_flowing_text(self, content: str) -> bool:
        """Check if content is flowing text rather than tabular data"""
        if not content or len(content) < 30:
            return False
        
        # Check for narrative indicators
        narrative_words = [
            "the", "and", "of", "to", "a", "in", "for", "is", "on", "that", 
            "by", "this", "with", "as", "are", "from", "be", "at", "or"
        ]
        
        words = content.lower().split()
        if len(words) < 10:
            return False
        
        narrative_count = sum(1 for word in words if word in narrative_words)
        narrative_ratio = narrative_count / len(words)
        
        # More strict threshold
        return narrative_ratio > self.criteria["max_flowing_text_ratio"]
    
    def _calculate_filtering_metrics(self, original: List[Dict[str, Any]], 
                                   final: List[Dict[str, Any]], 
                                   processing_time: float) -> Dict[str, Any]:
        """Calculate filtering performance metrics"""
        
        original_count = len(original)
        final_count = len(final)
        target_count = 32  # Expected from validation
        
        reduction_rate = (original_count - final_count) / original_count if original_count > 0 else 0
        target_achievement = abs(final_count - target_count) / target_count if target_count > 0 else 1.0
        
        # Calculate average confidence of final results
        if final:
            final_confidences = [ext["validation"]["confidence_score"] for ext in final]
            avg_confidence = sum(final_confidences) / len(final_confidences)
            min_confidence = min(final_confidences)
            max_confidence = max(final_confidences)
        else:
            avg_confidence = min_confidence = max_confidence = 0.0
        
        return {
            "original_count": original_count,
            "final_count": final_count,
            "target_count": target_count,
            "reduction_rate": reduction_rate,
            "target_achievement": 1.0 - target_achievement,  # Higher is better
            "avg_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
            "processing_time": processing_time,
            "criteria_strictness": "enhanced"
        }
    
    def identify_table1_candidates(self, enhanced_extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Identify candidates for Table 1 (thermal conductivity)
        """
        candidates = []
        
        for i, extraction in enumerate(enhanced_extractions):
            content = self._extract_content(extraction)
            
            # Check for thermal conductivity specific indicators
            table1_score = self._calculate_table1_score(content)
            
            if table1_score > 0.1:  # Some indication of thermal conductivity content
                candidates.append({
                    "extraction_id": i,
                    "table1_score": table1_score,
                    "confidence": extraction["validation"]["confidence_score"],
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                })
        
        # Sort by Table 1 score
        candidates.sort(key=lambda x: x["table1_score"], reverse=True)
        
        return {
            "candidates_found": len(candidates),
            "best_candidates": candidates[:5],  # Top 5
            "success": len(candidates) > 0
        }
    
    def _calculate_table1_score(self, content: str) -> float:
        """Calculate likelihood that content is Table 1 (thermal conductivity)"""
        content_lower = content.lower()
        
        # Thermal conductivity specific indicators
        thermal_indicators = [
            "thermal conductivity", "btu/h ft f", "w/m c", "w/m k",
            "gases at atmospheric", "insulating materials", "nonmetallic liquids",
            "liquid metals", "alloys", "pure metals", "brick", "stone", "concrete"
        ]
        
        # Specific numeric ranges from Table 1
        numeric_indicators = [
            "0.004 to 0.70", "0.007 to 1.2", "0.01 to 0.12", "0.02 to 0.21",
            "0.05 to 0.40", "0.09 to 0.70", "5.0 to 45", "8.6 to 78",
            "8.0 to 70", "14 to 121", "30 to 240", "52 to 415"
        ]
        
        thermal_matches = sum(1 for indicator in thermal_indicators if indicator in content_lower)
        numeric_matches = sum(1 for indicator in numeric_indicators if indicator in content_lower)
        
        # Weight thermal indicators more heavily
        score = (thermal_matches * 0.7 + numeric_matches * 0.3) / (len(thermal_indicators) * 0.7 + len(numeric_indicators) * 0.3)
        
        return score


def main():
    """Test enhanced detection criteria"""
    import sys
    import io
    
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    # Load validation filtered results
    try:
        with open("results/Ch-04_Heat_Transfer_validation_filtered.json", 'r', encoding='utf-8') as f:
            validation_results = json.load(f)
    except FileNotFoundError:
        print("❌ Please run validation_filtered_extractor.py first")
        return
    
    criteria = EnhancedDetectionCriteria()
    
    print("🎯 Enhanced Detection Criteria Application")
    print("=" * 55)
    print(f"📊 Target: Reduce to ~32 tables from validation framework")
    
    # Apply enhanced criteria
    enhanced_results = criteria.apply_enhanced_criteria(validation_results)
    
    # Print results
    metrics = enhanced_results["metrics"]
    stages = enhanced_results["filtering_stages"]
    
    print(f"\n📈 Enhanced Filtering Results:")
    print(f"  Final table count: {metrics['final_count']}")
    print(f"  Target achievement: {metrics['target_achievement']:.1%}")
    print(f"  Reduction rate: {metrics['reduction_rate']:.1%}")
    print(f"  Average confidence: {metrics['avg_confidence']:.2f}")
    print(f"  Confidence range: {metrics['min_confidence']:.2f} - {metrics['max_confidence']:.2f}")
    
    print(f"\n🔧 Filtering Stages:")
    print(f"  Stage 1 (Confidence): {stages['stage1_confidence']} tables")
    print(f"  Stage 2 (Content): {stages['stage2_content']} tables") 
    print(f"  Stage 3 (Geometric): {stages['stage3_geometric']} tables")
    print(f"  Stage 4 (Structural): {stages['stage4_structural']} tables")
    
    # Test Table 1 identification
    print(f"\n🎯 Table 1 Candidate Analysis:")
    table1_results = criteria.identify_table1_candidates(enhanced_results["enhanced_extractions"])
    
    if table1_results["success"]:
        print(f"  ✅ Found {table1_results['candidates_found']} thermal conductivity candidates")
        best = table1_results["best_candidates"][0]
        print(f"  🏆 Best candidate: ID {best['extraction_id']}")
        print(f"     Table 1 score: {best['table1_score']:.2f}")
        print(f"     Confidence: {best['confidence']:.2f}")
        print(f"     Preview: {best['content_preview'][:100]}...")
    else:
        print(f"  ❌ No thermal conductivity candidates found")
    
    # Save enhanced results
    output_path = "results/Ch-04_Heat_Transfer_enhanced_criteria.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced_results, f, indent=2, default=str)
    
    print(f"\n💾 Enhanced results saved: {output_path}")
    print(f"⏱️ Processing time: {enhanced_results['processing_time']:.2f}s")


if __name__ == "__main__":
    main()