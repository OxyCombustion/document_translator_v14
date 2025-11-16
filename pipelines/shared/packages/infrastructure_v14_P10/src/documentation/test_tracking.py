"""
Test Result Tracking for Documentation Agent
Tracks and documents test results and method comparisons
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TestRunResult:
    """Results from a test run"""
    document_id: str
    timestamp: str
    methods_compared: List[str]
    best_methods: Dict[str, str]
    confidence_scores: Dict[str, float]
    performance_metrics: Dict[str, Any]

class TestResultTracker:
    """Tracks and documents test results"""
    
    def __init__(self):
        self.results_dir = Path("results/test_tracking")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: List[TestRunResult] = []
    
    def record_test_run(self, comparison_result: Dict[str, Any]):
        """Record results from a test run"""
        result = TestRunResult(
            document_id=comparison_result["document_id"],
            timestamp=comparison_result["timestamp"],
            methods_compared=["docling", "gemini", "mathematica"],
            best_methods=comparison_result["best_methods"],
            confidence_scores=comparison_result["confidence_scores"],
            performance_metrics=comparison_result["metrics"]
        )
        
        self.current_session.append(result)
        self._save_result(result)
        self._update_test_history(result)
    
    def _save_result(self, result: TestRunResult):
        """Save individual test result"""
        filename = f"test_run_{result.document_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(self.results_dir / filename, 'w') as f:
            json.dump({
                "document_id": result.document_id,
                "timestamp": result.timestamp,
                "methods_compared": result.methods_compared,
                "best_methods": result.best_methods,
                "confidence_scores": result.confidence_scores,
                "performance_metrics": result.performance_metrics
            }, f, indent=2)
    
    def _update_test_history(self, result: TestRunResult):
        """Update cumulative test history"""
        history_file = self.results_dir / "test_history.json"
        
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = {
                "test_runs": [],
                "method_performance": {
                    "docling": {"runs": 0, "best_method_count": 0},
                    "gemini": {"runs": 0, "best_method_count": 0},
                    "mathematica": {"runs": 0, "best_method_count": 0}
                }
            }
        
        # Add current result
        history["test_runs"].append({
            "document_id": result.document_id,
            "timestamp": result.timestamp,
            "best_methods": result.best_methods
        })
        
        # Update method statistics
        for method in result.methods_compared:
            history["method_performance"][method]["runs"] += 1
            best_count = sum(1 for m in result.best_methods.values() if m == method)
            history["method_performance"][method]["best_method_count"] += best_count
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Generate report of current test session"""
        if not self.current_session:
            return {"status": "No tests run in current session"}
        
        report = {
            "session_start": self.current_session[0].timestamp,
            "session_end": self.current_session[-1].timestamp,
            "tests_run": len(self.current_session),
            "method_performance": {
                "docling": {"best_method_count": 0, "avg_confidence": 0.0},
                "gemini": {"best_method_count": 0, "avg_confidence": 0.0},
                "mathematica": {"best_method_count": 0, "avg_confidence": 0.0}
            },
            "documents_tested": []
        }
        
        # Aggregate statistics
        for result in self.current_session:
            report["documents_tested"].append(result.document_id)
            
            # Count best method selections
            for method in result.best_methods.values():
                report["method_performance"][method]["best_method_count"] += 1
            
            # Average confidence scores
            for method, score in result.confidence_scores.items():
                current = report["method_performance"][method]["avg_confidence"]
                report["method_performance"][method]["avg_confidence"] = (
                    current + score / len(self.current_session)
                )
        
        return report
    
    def clear_session(self):
        """Clear current session data"""
        self.current_session = []
        logger.info("Cleared current test session")