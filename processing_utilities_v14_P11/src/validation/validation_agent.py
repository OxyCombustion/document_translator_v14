"""
ValidationAgent for Triple-Method Comparison
Compares and validates results from all three extraction methods
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from ..base import BaseAgent, AgentResult
from ...core.test_data_manager import get_test_data_manager, TestDocument

logger = logging.getLogger(__name__)

@dataclass
class MethodResult:
    """Results from a single extraction method"""
    method: str
    content: Dict[str, Any]
    processing_time: float
    memory_usage: float
    confidence: float

@dataclass
class ComparisonResult:
    """Comparison of all three extraction methods"""
    document_id: str
    timestamp: str
    docling_result: MethodResult
    gemini_result: MethodResult
    mathematica_result: MethodResult
    best_method: Dict[str, str]  # Content type -> best method
    confidence_scores: Dict[str, float]
    comparison_metrics: Dict[str, Any]

class ValidationAgent(BaseAgent):
    """Validates and compares results from all extraction methods"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.test_data_manager = get_test_data_manager()
        self.comparison_history: List[ComparisonResult] = []
    
    def _initialize_model(self):
        """No ML model needed for validation"""
        logger.info(f"{self.name}: Using rule-based validation")
    
    def compare_extraction_methods(
        self,
        doc_id: str,
        docling_result: Dict[str, Any],
        gemini_result: Dict[str, Any],
        mathematica_result: Dict[str, Any]
    ) -> ComparisonResult:
        """Compare results from all three extraction methods"""
        # Get test document info
        test_doc = self.test_data_manager.get_test_document(doc_id)
        if not test_doc:
            raise ValueError(f"Unknown test document: {doc_id}")
        
        # Process each method's results
        docling = self._process_method_result("docling", docling_result)
        gemini = self._process_method_result("gemini", gemini_result)
        mathematica = self._process_method_result("mathematica", mathematica_result)
        
        # Compare results and determine best method per content type
        best_methods = self._determine_best_methods(
            test_doc, docling, gemini, mathematica
        )
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(
            test_doc, docling, gemini, mathematica
        )
        
        # Generate comparison metrics
        comparison_metrics = self._generate_comparison_metrics(
            test_doc, docling, gemini, mathematica
        )
        
        # Create comparison result
        result = ComparisonResult(
            document_id=doc_id,
            timestamp=datetime.now().isoformat(),
            docling_result=docling,
            gemini_result=gemini,
            mathematica_result=mathematica,
            best_method=best_methods,
            confidence_scores=confidence_scores,
            comparison_metrics=comparison_metrics
        )
        
        # Save to history
        self.comparison_history.append(result)
        
        return result
    
    def _process_method_result(
        self,
        method: str,
        result: Dict[str, Any]
    ) -> MethodResult:
        """Process results from a single method"""
        return MethodResult(
            method=method,
            content=result.get("content", {}),
            processing_time=result.get("processing_time", 0.0),
            memory_usage=result.get("memory_usage", 0.0),
            confidence=result.get("confidence", 0.0)
        )
    
    def _determine_best_methods(
        self,
        test_doc: TestDocument,
        docling: MethodResult,
        gemini: MethodResult,
        mathematica: MethodResult
    ) -> Dict[str, str]:
        """Determine best method for each content type"""
        best_methods = {}
        
        # Compare table extraction
        if "tables" in test_doc.validation_focus:
            table_scores = {
                "docling": self._evaluate_tables(docling.content.get("tables", [])),
                "gemini": self._evaluate_tables(gemini.content.get("tables", [])),
                "mathematica": self._evaluate_tables(mathematica.content.get("tables", []))
            }
            best_methods["tables"] = max(table_scores.items(), key=lambda x: x[1])[0]
        
        # Compare equation extraction
        if "equation_preservation" in test_doc.validation_focus:
            equation_scores = {
                "docling": self._evaluate_equations(docling.content.get("equations", [])),
                "gemini": self._evaluate_equations(gemini.content.get("equations", [])),
                "mathematica": self._evaluate_equations(mathematica.content.get("equations", []))
            }
            best_methods["equations"] = max(equation_scores.items(), key=lambda x: x[1])[0]
        
        # Compare text extraction
        text_scores = {
            "docling": self._evaluate_text(docling.content.get("text", "")),
            "gemini": self._evaluate_text(gemini.content.get("text", "")),
            "mathematica": self._evaluate_text(mathematica.content.get("text", ""))
        }
        best_methods["text"] = max(text_scores.items(), key=lambda x: x[1])[0]
        
        return best_methods
    
    def _calculate_confidence_scores(
        self,
        test_doc: TestDocument,
        docling: MethodResult,
        gemini: MethodResult,
        mathematica: MethodResult
    ) -> Dict[str, float]:
        """Calculate confidence scores for each method"""
        scores = {
            "docling": self._calculate_method_confidence(test_doc, docling),
            "gemini": self._calculate_method_confidence(test_doc, gemini),
            "mathematica": self._calculate_method_confidence(test_doc, mathematica)
        }
        return scores
    
    def _generate_comparison_metrics(
        self,
        test_doc: TestDocument,
        docling: MethodResult,
        gemini: MethodResult,
        mathematica: MethodResult
    ) -> Dict[str, Any]:
        """Generate detailed comparison metrics"""
        return {
            "processing_time": {
                "docling": docling.processing_time,
                "gemini": gemini.processing_time,
                "mathematica": mathematica.processing_time,
                "baseline": test_doc.baseline_time
            },
            "memory_usage": {
                "docling": docling.memory_usage,
                "gemini": gemini.memory_usage,
                "mathematica": mathematica.memory_usage,
                "target_reduction": test_doc.memory_target
            },
            "content_completeness": {
                "docling": self._calculate_completeness(test_doc, docling),
                "gemini": self._calculate_completeness(test_doc, gemini),
                "mathematica": self._calculate_completeness(test_doc, mathematica)
            }
        }
    
    def _evaluate_tables(self, tables: List[Dict]) -> float:
        """Evaluate table extraction quality"""
        # TODO: Implement detailed table evaluation
        return len(tables) / 11  # Known number of tables
    
    def _evaluate_equations(self, equations: List[Dict]) -> float:
        """Evaluate equation extraction quality"""
        # TODO: Implement equation evaluation
        return 0.9  # Placeholder
    
    def _evaluate_text(self, text: str) -> float:
        """Evaluate text extraction quality"""
        # TODO: Implement text evaluation
        return 0.95  # Placeholder
    
    def _calculate_method_confidence(
        self,
        test_doc: TestDocument,
        result: MethodResult
    ) -> float:
        """Calculate overall confidence for a method"""
        # TODO: Implement proper confidence calculation
        return result.confidence
    
    def _calculate_completeness(
        self,
        test_doc: TestDocument,
        result: MethodResult
    ) -> float:
        """Calculate content completeness vs ground truth"""
        # TODO: Implement completeness calculation
        return 0.9  # Placeholder
    
    def save_comparison_results(self, result: ComparisonResult):
        """Save comparison results to file"""
        results_dir = Path("results/comparisons")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"comparison_{result.document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(results_dir / filename, 'w') as f:
            json.dump({
                "document_id": result.document_id,
                "timestamp": result.timestamp,
                "best_methods": result.best_method,
                "confidence_scores": result.confidence_scores,
                "metrics": result.comparison_metrics
            }, f, indent=2)
        
        logger.info(f"Saved comparison results to {filename}")
    
    def get_comparison_history(self) -> List[ComparisonResult]:
        """Get history of all comparisons"""
        return self.comparison_history.copy()

def main():
    """Test the validation agent"""
    config = {
        "test_mode": True
    }
    
    agent = ValidationAgent(config)
    
    # Test with sample results
    doc_id = "ch04"
    docling_result = {
        "content": {
            "tables": [{"id": 1}, {"id": 2}],
            "text": "Sample text"
        },
        "processing_time": 3.5,
        "memory_usage": 100.5,
        "confidence": 0.85
    }
    
    gemini_result = {
        "content": {
            "tables": [{"id": 1}],
            "text": "Sample text"
        },
        "processing_time": 2.5,
        "memory_usage": 80.5,
        "confidence": 0.75
    }
    
    mathematica_result = {
        "content": {
            "tables": [{"id": 1}, {"id": 2}, {"id": 3}],
            "text": "Sample text"
        },
        "processing_time": 4.5,
        "memory_usage": 120.5,
        "confidence": 0.95
    }
    
    result = agent.compare_extraction_methods(
        doc_id, docling_result, gemini_result, mathematica_result
    )
    
    print("Comparison Results:")
    print(f"Best methods: {result.best_method}")
    print(f"Confidence scores: {result.confidence_scores}")
    print(f"Processing times: {result.comparison_metrics['processing_time']}")
    
    # Save results
    agent.save_comparison_results(result)

if __name__ == "__main__":
    main()