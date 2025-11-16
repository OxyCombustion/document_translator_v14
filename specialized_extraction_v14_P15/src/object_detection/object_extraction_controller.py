"""
Object Extraction Controller for Document Translator V9
Orchestrates multi-class object detection and extraction
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from .document_object_agent import DocumentObjectAgent, ObjectType
from ...core.spatial_metadata import SpatialIndex, ContentReference
from ...core.logger import get_logger

logger = get_logger("ObjectExtractionController")


class ObjectExtractionController:
    """Controller for comprehensive document object extraction"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize object detection agent
        agent_config = {
            "min_confidence": self.config.get("min_confidence", 0.4),
            "feature_dimensions": self.config.get("feature_dimensions", 50)
        }
        
        self.object_agent = DocumentObjectAgent(agent_config)
        
        logger.info("ObjectExtractionController initialized")
    
    def extract_all_objects(self, pdf_path: str) -> Dict[str, Any]:
        """Extract and classify all document objects"""
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        logger.info(f"Starting object extraction: {pdf_path.name}")
        
        # Run object detection
        agent_result = self.object_agent.process(pdf_path)
        
        if not agent_result.success:
            logger.error(f"Object detection failed: {agent_result.errors}")
            return {
                "success": False,
                "error": agent_result.errors,
                "processing_time": time.time() - start_time
            }
        
        # Process results by type
        all_objects = agent_result.data.get("all_objects", [])
        tables = agent_result.data.get("tables", [])
        figures = agent_result.data.get("figures", [])
        equations = agent_result.data.get("equations", [])
        summary = agent_result.data.get("summary", {})
        
        # Enhance table data with proper structure
        enhanced_tables = self._enhance_table_data(tables)
        
        # Create spatial index
        spatial_index = self._create_spatial_index(all_objects)
        
        processing_time = time.time() - start_time
        
        result = {
            "success": True,
            "all_objects": all_objects,
            "tables": enhanced_tables,
            "figures": figures,
            "equations": equations,
            "summary": {
                **summary,
                "processing_time": processing_time,
                "extraction_method": "ml_object_detection"
            },
            "spatial_index": spatial_index.to_dict() if spatial_index else None,
            "agent_confidence": agent_result.confidence,
            "processing_time": processing_time
        }
        
        logger.info(f"Object extraction completed: {summary.get('total_objects', 0)} objects in {processing_time:.2f}s")
        
        return result
    
    def _enhance_table_data(self, tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance table data with proper structure for compatibility"""
        enhanced = []
        
        for i, table in enumerate(tables, 1):
            # Extract basic structure from content
            content = table.get("content", {})
            text_content = content.get("text", "")
            
            # Try to parse table structure from text
            headers, rows = self._parse_table_structure(text_content)
            
            enhanced_table = {
                "table_number": i,
                "table_id": table.get("object_id", f"table_{i}"),
                "title": self._extract_table_title(text_content),
                "headers": headers,
                "rows": rows,
                "notes": None,
                "confidence": table.get("confidence", 0.5),
                "extraction_method": "ml_object_detection",
                
                # Add spatial information
                "spatial": {
                    "page": table.get("page", 0),
                    "x": table.get("bbox", {}).get("x", 0),
                    "y": table.get("bbox", {}).get("y", 0),
                    "width": table.get("bbox", {}).get("width", 0),
                    "height": table.get("bbox", {}).get("height", 0),
                    "area": table.get("spatial_location", {}).get("area", 0)
                },
                
                # Include original object data
                "object_data": table
            }
            
            enhanced.append(enhanced_table)
        
        return enhanced
    
    def _parse_table_structure(self, text: str) -> tuple[List[str], List[List[str]]]:
        """Parse table structure from text content"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return [], []
        
        headers = []
        rows = []
        
        # Try to identify header row and data rows
        for line in lines:
            # Split by common separators
            cells = self._split_table_line(line)
            
            if len(cells) > 1:  # Multi-column data
                if not headers and not all(self._is_numeric(cell) for cell in cells):
                    # Likely header row
                    headers = cells
                else:
                    # Data row
                    rows.append(cells)
        
        return headers, rows
    
    def _split_table_line(self, line: str) -> List[str]:
        """Split a line into table cells"""
        # Try different separators
        separators = ['\t', '|', '  ']
        
        for sep in separators:
            if sep in line:
                cells = [cell.strip() for cell in line.split(sep) if cell.strip()]
                if len(cells) > 1:
                    return cells
        
        # Fallback: split by spaces if we have multiple words
        words = line.split()
        if len(words) > 2:
            return words
        
        return [line]  # Single cell
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text is primarily numeric"""
        # Remove common non-numeric characters
        cleaned = text.replace(',', '').replace('.', '').replace('-', '').replace('+', '')
        digits = sum(1 for c in cleaned if c.isdigit())
        total = len(cleaned)
        
        return total > 0 and digits / total > 0.5
    
    def _extract_table_title(self, text: str) -> Optional[str]:
        """Extract table title from text"""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'table' in line.lower() and len(line) < 100:  # Likely title
                return line
        
        return None
    
    def _create_spatial_index(self, objects: List[Dict[str, Any]]) -> Optional[SpatialIndex]:
        """Create spatial index from all detected objects"""
        try:
            spatial_index = SpatialIndex()
            
            for obj in objects:
                spatial_data = obj.get("spatial_location", {})
                
                if spatial_data:
                    # Create content reference
                    content_ref = ContentReference(
                        content_id=obj["object_id"],
                        content_type=obj["type"],
                        location=spatial_data,  # Already in correct format
                        chunk_id=obj["object_id"],
                        confidence=obj["confidence"]
                    )
                    
                    spatial_index.add_content(content_ref)
            
            return spatial_index
            
        except Exception as e:
            logger.warning(f"Could not create spatial index: {e}")
            return None
    
    def save_results(self, results: Dict[str, Any], base_path: str) -> Dict[str, bool]:
        """Save extraction results to separate files by type"""
        base_path = Path(base_path)
        base_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_status = {}
        
        # Save tables in compatible format
        try:
            tables_file = base_path.parent / f"{base_path.stem}_tables.json"
            with open(tables_file, 'w', encoding='utf-8') as f:
                json.dump(results.get("tables", []), f, indent=2, ensure_ascii=False)
            save_status["tables"] = True
            logger.info(f"Tables saved to: {tables_file}")
        except Exception as e:
            logger.error(f"Error saving tables: {e}")
            save_status["tables"] = False
        
        # Save figures
        try:
            figures_file = base_path.parent / f"{base_path.stem}_figures.json"
            with open(figures_file, 'w', encoding='utf-8') as f:
                json.dump(results.get("figures", []), f, indent=2, ensure_ascii=False)
            save_status["figures"] = True
        except Exception as e:
            logger.error(f"Error saving figures: {e}")
            save_status["figures"] = False
        
        # Save equations
        try:
            equations_file = base_path.parent / f"{base_path.stem}_equations.json"
            with open(equations_file, 'w', encoding='utf-8') as f:
                json.dump(results.get("equations", []), f, indent=2, ensure_ascii=False)
            save_status["equations"] = True
        except Exception as e:
            logger.error(f"Error saving equations: {e}")
            save_status["equations"] = False
        
        # Save complete results
        try:
            complete_file = base_path.parent / f"{base_path.stem}_complete.json"
            with open(complete_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            save_status["complete"] = True
        except Exception as e:
            logger.error(f"Error saving complete results: {e}")
            save_status["complete"] = False
        
        return save_status
    
    def get_object_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed summary of object extraction"""
        summary = results.get("summary", {})
        
        # Analyze confidence distribution
        all_objects = results.get("all_objects", [])
        confidence_dist = {
            "high": 0,  # >= 0.8
            "medium": 0,  # 0.5-0.8
            "low": 0  # < 0.5
        }
        
        for obj in all_objects:
            conf = obj.get("confidence", 0)
            if conf >= 0.8:
                confidence_dist["high"] += 1
            elif conf >= 0.5:
                confidence_dist["medium"] += 1
            else:
                confidence_dist["low"] += 1
        
        # Count by page
        by_page = {}
        for obj in all_objects:
            page = obj.get("page", 0)
            obj_type = obj.get("type", "unknown")
            
            if page not in by_page:
                by_page[page] = {"tables": 0, "figures": 0, "equations": 0, "total": 0}
            
            by_page[page][obj_type] = by_page[page].get(obj_type, 0) + 1
            by_page[page]["total"] += 1
        
        return {
            **summary,
            "confidence_distribution": confidence_dist,
            "objects_by_page": by_page,
            "avg_confidence": sum(obj.get("confidence", 0) for obj in all_objects) / max(len(all_objects), 1)
        }


def main():
    """Test the object extraction controller"""
    config = {
        "min_confidence": 0.4,
        "feature_dimensions": 50
    }
    
    controller = ObjectExtractionController(config)
    
    # Test with Chapter 4
    test_file = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    if Path(test_file).exists():
        print(f"Testing object extraction with: {test_file}")
        
        results = controller.extract_all_objects(test_file)
        
        if results["success"]:
            summary = controller.get_object_summary(results)
            
            print(f"Object Extraction Results:")
            print(f"  - Tables: {summary.get('tables_found', 0)}")
            print(f"  - Figures: {summary.get('figures_found', 0)}")
            print(f"  - Equations: {summary.get('equations_found', 0)}")
            print(f"  - Average confidence: {summary.get('avg_confidence', 0):.2f}")
            print(f"  - Processing time: {summary.get('processing_time', 0):.2f}s")
            
            # Save results
            base_path = "results/Ch-04_Heat_Transfer_ml_objects"
            save_status = controller.save_results(results, base_path)
            
            print(f"\nSave Status:")
            for file_type, status in save_status.items():
                print(f"  - {file_type}: {'Success' if status else 'Failed'}")
            
        else:
            print(f"Extraction failed: {results.get('error')}")
    else:
        print(f"Test file not found: {test_file}")


if __name__ == "__main__":
    main()
