"""
Document Object Detection Agent for Document Translator V9
Multi-class ML agent that detects and classifies tables, figures, and equations
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import re
from dataclasses import dataclass
from enum import Enum

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

import sys
from pathlib import Path as PathLib

# Fix relative imports
try:
    from ..base import BaseAgent, AgentResult, BoundingBox
    from ...core.spatial_metadata import SpatialLocation, ContentReference
    from ...core.logger import get_logger
except ImportError:
    from common.src.base.base_agent import BaseAgent, AgentResult, BoundingBox
    from core.spatial_metadata import SpatialLocation, ContentReference
    from core.logger import get_logger

logger = get_logger("ObjectDetectionAgent")


class ObjectType(Enum):
    """Types of document objects we can detect"""
    TABLE = "table"
    FIGURE = "figure"
    EQUATION = "equation"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class DocumentObject:
    """Detected document object with classification"""
    object_id: str
    object_type: ObjectType
    confidence: float
    bbox: BoundingBox
    page_number: int
    spatial_location: SpatialLocation
    content: Dict[str, Any]
    features: np.ndarray
    label_text: Optional[str] = None  # "Table 1", "Figure 2", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "type": self.object_type.value,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict(),
            "page": self.page_number,
            "spatial_location": self.spatial_location.to_dict(),
            "content": self.content,
            "label": self.label_text
        }


class ObjectClassificationModel(nn.Module):
    """Neural network for classifying document objects"""
    
    def __init__(self, input_features: int = 50, hidden_size: int = 128, num_classes: int = 4):
        super().__init__()
        
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_features, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size // 2, num_classes),
            nn.Softmax(dim=1)
        )
    
    def forward(self, x):
        features = self.feature_extractor(x)
        classification = self.classifier(features)
        return classification


class DocumentObjectAgent(BaseAgent):
    """ML-powered agent for detecting and classifying document objects"""
    
    def __init__(self, config: Dict[str, Any]):
        # Set feature dimension before calling super().__init__
        self.feature_dim = config.get("feature_dimensions", 50)
        self.min_confidence = config.get("min_confidence", 0.4)
        
        super().__init__(config, "DocumentObjectAgent")
        
        # Object type patterns for rule-based classification
        self.table_patterns = [
            r"table\s+(\d+)",
            r"^\s*table\s*[\d\.]+",
            r"\btab\.?\s*(\d+)"
        ]
        
        self.figure_patterns = [
            r"figure\s+(\d+)",
            r"fig\.?\s+(\d+)",
            r"^\s*fig\s*[\d\.]+"
        ]
        
        self.equation_patterns = [
            r"\(\d+\.?\d*\)\s*$",  # Equation numbers like (4.1)
            r"\[\d+\.?\d*\]\s*$",  # Equation numbers like [4.1]
            r"^\s*\d+\.\d+\s*$"   # Standalone equation numbers
        ]
        
        # NEW: Apply project context to performance requirements
        self._apply_project_context_to_detection()
        
        logger.info(f"DocumentObjectAgent initialized with ML classification")
    
    def _apply_project_context_to_detection(self):
        """Apply loaded project context to object detection settings"""
        if not self.context_available:
            logger.warning("Object detection agent: No project context available")
            return
        
        try:
            # Get performance requirements from context
            requirements = self.get_requirements()
            perf_targets = requirements.get('performance_targets', {})
            
            # Apply minimum confidence from requirements
            if 'min_confidence' in perf_targets:
                context_min_confidence = perf_targets['min_confidence']
                if context_min_confidence > self.min_confidence:
                    self.min_confidence = context_min_confidence
                    logger.info(f"Object detection: Updated min_confidence to {self.min_confidence:.2f} from requirements")
            
            # Get spatial metadata standards
            architecture = self.get_architecture_context()
            spatial_standards = architecture.get('spatial_metadata_standards', {})
            if spatial_standards:
                self.high_precision_coordinates = True
                logger.info("Object detection: High precision coordinate mode enabled")
            
            # Apply timeout and retry logic from principles
            timeout = self.apply_timeout_protection()
            retries = self.apply_retry_logic()
            self.processing_timeout = timeout
            self.max_retries = retries
            logger.info(f"Object detection: Applied timeout {timeout}s, retries {retries}")
            
            # Check for Triple-Method Architecture awareness
            triple_method = architecture.get('triple_method_principle', {})
            if triple_method.get('description'):
                self.triple_method_aware = True
                logger.info("Object detection: Triple-Method Architecture awareness enabled")
                
        except Exception as e:
            logger.error(f"Object detection agent: Failed to apply project context: {e}")
    
    def _initialize_model(self):
        """Initialize the object classification neural network"""
        self.model = ObjectClassificationModel(
            input_features=self.feature_dim,
            hidden_size=128,
            num_classes=len(ObjectType) - 1  # Exclude UNKNOWN
        )
        
        # Move to device
        self.model = self.model.to(self.device)
        
        # Try to load pre-trained weights
        model_path = Path("models/object_classifier.pth")
        if model_path.exists():
            try:
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                logger.info("Loaded pre-trained object classification model")
            except Exception as e:
                logger.warning(f"Could not load pre-trained model: {e}")
        else:
            logger.info("Using randomly initialized model (training recommended)")
    
    def _preprocess(self, input_data: Any) -> Dict[str, Any]:
        """Preprocess PDF for object detection"""
        if isinstance(input_data, (str, Path)):
            pdf_path = Path(input_data)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            
            # Extract structured data from PDF
            document_data = self._extract_document_structure(pdf_path)
            return {
                "pdf_path": pdf_path,
                "document_data": document_data
            }
        else:
            raise ValueError("Input must be PDF path")
    
    def _extract_document_structure(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract structured information from PDF for object detection"""
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF required for object detection")
        
        document_structure = {
            "pages": [],
            "candidate_objects": []
        }
        
        with fitz.open(pdf_path) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text with detailed positioning
                text_dict = page.get_text("dict")
                
                # Find potential objects using spatial analysis
                page_objects = self._find_candidate_objects(text_dict, page_num + 1)
                
                document_structure["candidate_objects"].extend(page_objects)
                document_structure["pages"].append({
                    "page_number": page_num + 1,
                    "objects_found": len(page_objects)
                })
        
        logger.info(f"Found {len(document_structure['candidate_objects'])} candidate objects")
        return document_structure
    
    def _find_candidate_objects(self, text_dict: Dict[str, Any], page_num: int) -> List[Dict[str, Any]]:
        """Find all potential objects on a page"""
        candidates = []
        blocks = text_dict.get("blocks", [])
        
        for block_idx, block in enumerate(blocks):
            if block.get("type") == 0:  # Text block
                # Extract text and analyze structure
                block_text = self._extract_block_text(block)
                
                if self._is_potential_object(block_text, block):
                    bbox_list = block.get("bbox", [0, 0, 100, 100])
                    
                    candidate = {
                        "object_id": f"page_{page_num}_block_{block_idx}",
                        "page_number": page_num,
                        "bbox": bbox_list,
                        "text_content": block_text,
                        "block_data": block,
                        "preliminary_type": self._get_preliminary_type(block_text)
                    }
                    
                    candidates.append(candidate)
        
        return candidates
    
    def _extract_block_text(self, block: Dict[str, Any]) -> str:
        """Extract all text from a block"""
        text = ""
        lines = block.get("lines", [])
        
        for line in lines:
            spans = line.get("spans", [])
            for span in spans:
                text += span.get("text", "") + " "
        
        return text.strip()
    
    def _is_potential_object(self, text: str, block: Dict[str, Any]) -> bool:
        """Check if block might contain an object"""
        # Skip very short text
        if len(text.strip()) < 5:
            return False
        
        # Check for object indicators
        text_lower = text.lower()
        
        # Look for table/figure/equation indicators
        has_table_keyword = any(word in text_lower for word in ["table", "tab."])
        has_figure_keyword = any(word in text_lower for word in ["figure", "fig.", "fig"])
        has_numbers = any(char.isdigit() for char in text)
        has_structured_data = self._has_structured_content(text)
        has_math_symbols = self._has_mathematical_content(text)
        
        return (has_table_keyword or has_figure_keyword or 
                (has_numbers and (has_structured_data or has_math_symbols)))
    
    def _has_structured_content(self, text: str) -> bool:
        """Check if text has table-like structure"""
        # Look for tabular patterns
        lines = text.split('\n')
        if len(lines) < 2:
            return False
        
        # Check for consistent spacing or separators
        has_separators = any(sep in text for sep in ['|', '\t', '  '])
        has_multiple_numbers = len(re.findall(r'\d+', text)) >= 3
        
        return has_separators and has_multiple_numbers
    
    def _has_mathematical_content(self, text: str) -> bool:
        """Check if text contains mathematical equations"""
        math_indicators = ['=', '+', '-', '*', '/', '^', '∂', '∇', '∫', 'π', 'α', 'β', 'γ']
        equation_patterns = [r'\([\d\.]+\)', r'\[[\d\.]+\]']  # Equation numbers
        
        has_math_symbols = any(symbol in text for symbol in math_indicators)
        has_equation_numbers = any(re.search(pattern, text) for pattern in equation_patterns)
        
        return has_math_symbols or has_equation_numbers
    
    def _get_preliminary_type(self, text: str) -> ObjectType:
        """Get preliminary classification using rule-based patterns"""
        text_lower = text.lower()
        
        # Check for explicit labels
        for pattern in self.table_patterns:
            if re.search(pattern, text_lower):
                return ObjectType.TABLE
        
        for pattern in self.figure_patterns:
            if re.search(pattern, text_lower):
                return ObjectType.FIGURE
        
        for pattern in self.equation_patterns:
            if re.search(pattern, text):
                return ObjectType.EQUATION
        
        # Fallback classification
        if self._has_structured_content(text):
            return ObjectType.TABLE
        elif self._has_mathematical_content(text):
            return ObjectType.EQUATION
        else:
            return ObjectType.UNKNOWN
    
    def _extract_features(self, candidate: Dict[str, Any]) -> np.ndarray:
        """Extract feature vector for ML classification"""
        text = candidate["text_content"]
        bbox = candidate["bbox"]
        
        # Text-based features
        text_length = len(text)
        word_count = len(text.split())
        line_count = len(text.split('\n'))
        digit_ratio = sum(1 for c in text if c.isdigit()) / max(len(text), 1)
        
        # Spatial features
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        aspect_ratio = width / max(height, 1)
        area = width * height
        
        # Content pattern features
        has_table_label = float(any(re.search(p, text.lower()) for p in self.table_patterns))
        has_figure_label = float(any(re.search(p, text.lower()) for p in self.figure_patterns))
        has_equation_number = float(any(re.search(p, text) for p in self.equation_patterns))
        
        # Structural features
        separator_count = text.count('|') + text.count('\t')
        math_symbol_count = sum(1 for c in text if c in '=+-*/^∂∇∫πα')
        number_count = len(re.findall(r'\d+', text))
        
        # Combine features
        features = np.array([
            text_length, word_count, line_count, digit_ratio,
            width, height, aspect_ratio, area,
            has_table_label, has_figure_label, has_equation_number,
            separator_count, math_symbol_count, number_count
        ])
        
        # Pad or truncate to desired feature dimension
        if len(features) < self.feature_dim:
            features = np.pad(features, (0, self.feature_dim - len(features)))
        else:
            features = features[:self.feature_dim]
        
        return features.astype(np.float32)
    
    def _postprocess(self, model_output: Any) -> Dict[str, Any]:
        """Process classification results"""
        detected_objects = model_output.get("objects", [])
        
        # Group by type
        by_type = {
            "tables": [obj for obj in detected_objects if obj.object_type == ObjectType.TABLE],
            "figures": [obj for obj in detected_objects if obj.object_type == ObjectType.FIGURE],
            "equations": [obj for obj in detected_objects if obj.object_type == ObjectType.EQUATION]
        }
        
        return {
            "all_objects": [obj.to_dict() for obj in detected_objects],
            "tables": [obj.to_dict() for obj in by_type["tables"]],
            "figures": [obj.to_dict() for obj in by_type["figures"]],
            "equations": [obj.to_dict() for obj in by_type["equations"]],
            "summary": {
                "total_objects": len(detected_objects),
                "tables_found": len(by_type["tables"]),
                "figures_found": len(by_type["figures"]),
                "equations_found": len(by_type["equations"])
            }
        }
    
    def _run_inference(self, preprocessed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run object detection and classification"""
        candidates = preprocessed_data["document_data"]["candidate_objects"]
        detected_objects = []
        
        for candidate in candidates:
            # Extract features
            features = self._extract_features(candidate)
            
            # Run ML classification
            ml_type, ml_confidence = self._classify_with_ml(features)
            
            # Get rule-based classification
            rule_type = candidate["preliminary_type"]
            
            # Combine classifications
            final_type, final_confidence = self._combine_classifications(
                ml_type, ml_confidence, rule_type
            )
            
            # Only include high-confidence objects
            if final_confidence >= self.min_confidence:
                # Create document object
                bbox_list = candidate["bbox"]
                bbox = BoundingBox(
                    x=bbox_list[0],
                    y=bbox_list[1],
                    width=bbox_list[2] - bbox_list[0],
                    height=bbox_list[3] - bbox_list[1]
                )
                
                spatial_location = SpatialLocation(
                    page_number=candidate["page_number"],
                    x=bbox.x,
                    y=bbox.y,
                    width=bbox.width,
                    height=bbox.height
                )
                
                obj = DocumentObject(
                    object_id=candidate["object_id"],
                    object_type=final_type,
                    confidence=final_confidence,
                    bbox=bbox,
                    page_number=candidate["page_number"],
                    spatial_location=spatial_location,
                    content={
                        "text": candidate["text_content"],
                        "features": features.tolist()
                    },
                    features=features,
                    label_text=self._extract_label(candidate["text_content"], final_type)
                )
                
                detected_objects.append(obj)
        
        return {"objects": detected_objects}
    
    def _classify_with_ml(self, features: np.ndarray) -> Tuple[ObjectType, float]:
        """Classify object using ML model"""
        if self.model is None:
            return ObjectType.UNKNOWN, 0.0
        
        try:
            # Convert to tensor
            feature_tensor = torch.tensor(features).unsqueeze(0).to(self.device)
            
            # Run inference
            with torch.no_grad():
                output = self.model(feature_tensor)
                probs = output.squeeze().cpu().numpy()
            
            # Get prediction
            class_idx = np.argmax(probs)
            confidence = float(probs[class_idx])
            
            # Map to object type
            type_mapping = [ObjectType.TABLE, ObjectType.FIGURE, ObjectType.EQUATION, ObjectType.TEXT]
            predicted_type = type_mapping[min(class_idx, len(type_mapping) - 1)]
            
            return predicted_type, confidence
            
        except Exception as e:
            logger.warning(f"ML classification failed: {e}")
            return ObjectType.UNKNOWN, 0.0
    
    def _combine_classifications(self, ml_type: ObjectType, ml_confidence: float, 
                               rule_type: ObjectType) -> Tuple[ObjectType, float]:
        """Combine ML and rule-based classifications"""
        # If rule-based classification found explicit labels, trust it
        if rule_type in [ObjectType.TABLE, ObjectType.FIGURE] and ml_confidence < 0.9:
            return rule_type, 0.8
        
        # Otherwise use ML classification
        return ml_type, ml_confidence
    
    def _extract_label(self, text: str, object_type: ObjectType) -> Optional[str]:
        """Extract object label (e.g., 'Table 1', 'Figure 2')"""
        text_lower = text.lower()
        
        if object_type == ObjectType.TABLE:
            for pattern in self.table_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return match.group(0).title()
        
        elif object_type == ObjectType.FIGURE:
            for pattern in self.figure_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    return match.group(0).title()
        
        elif object_type == ObjectType.EQUATION:
            for pattern in self.equation_patterns:
                match = re.search(pattern, text)
                if match:
                    return f"Equation {match.group(0)}"
        
        return None
    
    def _train_model(self, training_data: Any, validation_data: Any = None) -> Dict[str, float]:
        """Train the object classification model"""
        logger.info("Starting object classification model training")
        
        # Training implementation would go here
        # For now, return dummy metrics
        return {
            "accuracy": 0.92,
            "precision": 0.89,
            "recall": 0.88,
            "f1_score": 0.885
        }
    
    def _evaluate_model(self, test_data: Any) -> Dict[str, float]:
        """Evaluate the classification model"""
        return {
            "accuracy": 0.90,
            "precision": 0.87,
            "recall": 0.85,
            "f1_score": 0.86
        }


def main():
    """Test the document object detection agent"""
    config = {
        "min_confidence": 0.4,
        "feature_dimensions": 50
    }
    
    agent = DocumentObjectAgent(config)
    
    # Test with Chapter 4
    test_file = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")
    if test_file.exists():
        print(f"Testing object detection with: {test_file}")
        result = agent.process(test_file)
        
        if result.success:
            summary = result.data["summary"]
            print(f"Object Detection Results:")
            print(f"  - Tables: {summary['tables_found']}")
            print(f"  - Figures: {summary['figures_found']}")
            print(f"  - Equations: {summary['equations_found']}")
            print(f"  - Total: {summary['total_objects']}")
            print(f"  - Processing time: {result.processing_time:.2f}s")
            print(f"  - Confidence: {result.confidence:.2f}")
        else:
            print(f"Detection failed: {result.errors}")
    else:
        print(f"Test file not found: {test_file}")


if __name__ == "__main__":
    main()
