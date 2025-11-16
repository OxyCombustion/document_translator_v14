"""
Base Agent Class for Document Translator V9
Defines the interface and common functionality for all ML agents
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time
import sys
from pathlib import Path

import numpy as np
import torch

# Fix relative imports
try:
    from ..logging.logger import setup_logger
    from ..context.context_loader import load_agent_context, ProjectContext
    # TODO: task_context_manager is P1 - will be migrated in Phase 2
    # from ..context.task_context_manager import TaskContextManager, TaskContext
except ImportError:
    from logging.logger import setup_logger
    from context.context_loader import load_agent_context, ProjectContext
    # TODO: task_context_manager is P1 - will be migrated in Phase 2
    # from context.task_context_manager import TaskContextManager, TaskContext

logger = setup_logger(__name__)

# Global task context manager instance
_task_context_manager = None

# TODO: task_context_manager is P1 - will be migrated in Phase 2
# def get_task_context_manager() -> TaskContextManager:
#     """Get global task context manager instance"""
#     global _task_context_manager
#
#     if _task_context_manager is None:
#         _task_context_manager = TaskContextManager()
#
#     return _task_context_manager

def get_task_context_manager():
    """Get global task context manager instance (stub until P1 migration)"""
    # TODO: Implement when task_context_manager is migrated in Phase 2
    return None


class AgentStatus(Enum):
    """Status of an agent"""
    IDLE = "idle"
    PROCESSING = "processing"
    TRAINING = "training"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class AgentResult:
    """Result from agent processing"""
    agent_name: str
    status: str
    confidence: float
    processing_time: float
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    
    @property
    def success(self) -> bool:
        """Check if processing was successful"""
        return self.status == "success" and not self.errors


@dataclass
class BoundingBox:
    """Bounding box for detected objects"""
    x: float
    y: float
    width: float
    height: float
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        }
    
    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union with another box"""
        # Calculate intersection
        x1 = max(self.x, other.x)
        y1 = max(self.y, other.y)
        x2 = min(self.x + self.width, other.x + other.width)
        y2 = min(self.y + self.height, other.y + other.height)
        
        if x2 < x1 or y2 < y1:
            return 0.0
            
        intersection = (x2 - x1) * (y2 - y1)
        
        # Calculate union
        area1 = self.width * self.height
        area2 = other.width * other.height
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0


class BaseAgent(ABC):
    """Abstract base class for all processing agents"""
    
    def __init__(self, config: Dict[str, Any], name: str = None):
        self.config = config
        self.name = name or self.__class__.__name__
        self.status = AgentStatus.IDLE
        self.model = None
        self.device = self._get_device()
        self.metrics = {
            "processed_count": 0,
            "total_processing_time": 0.0,
            "average_confidence": 0.0,
            "error_count": 0
        }
        
        # Context management
        self.static_context = self._load_static_context()
        self.project_context = self._load_project_context()
        self.context_available = self.project_context is not None or self.static_context is not None
        self.task_context_manager = get_task_context_manager()
        self.current_task_id = None
        
        # Initialize model
        self._initialize_model()
        
        logger.info(f"Initialized agent: {self.name} (context: {'available' if self.context_available else 'minimal'})")
    
    def _get_device(self) -> torch.device:
        """Get compute device (GPU if available)"""
        if torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"{self.name}: Using GPU")
        else:
            device = torch.device("cpu")
            logger.info(f"{self.name}: Using CPU")
        return device
    
    def _load_static_context(self) -> Optional[Dict[str, Any]]:
        """Load static context specific to this agent type"""
        try:
            agent_dir = Path(__file__).parent
            context_file = agent_dir / 'static_context.md'
            
            if not context_file.exists():
                logger.debug(f"{self.name}: No static context file found")
                return None
                
            with open(context_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse markdown sections into dictionary
            context = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('## '):
                    if current_section:
                        context[current_section] = '\n'.join(current_content).strip()
                    current_section = line[3:].strip()
                    current_content = []
                elif current_section:
                    current_content.append(line)
                    
            if current_section:
                context[current_section] = '\n'.join(current_content).strip()
                
            logger.debug(f"{self.name}: Loaded static context with sections: {list(context.keys())}")
            return context
            
        except Exception as e:
            logger.warning(f"{self.name}: Failed to load static context: {e}")
            return None
            
    def _load_project_context(self) -> Optional[ProjectContext]:
        """Load selective project context based on agent needs"""
        try:
            # Check if context loading is disabled
            if self.config.get("disable_context_loading", False):
                logger.info(f"{self.name}: Context loading disabled by configuration")
                return None
            
            # Get context loader
            context = load_agent_context(force_reload=False)
            
            # Filter context based on agent type
            if context and self.static_context:
                required_sections = self._get_required_context_sections()
                filtered_context = self._filter_context(context, required_sections)
                logger.debug(f"{self.name}: Loaded filtered project context")
                return filtered_context
            
            logger.debug(f"{self.name}: Using full project context")
            return context
            
        except Exception as e:
            logger.warning(f"{self.name}: Failed to load project context: {e}")
            logger.info(f"{self.name}: Operating with static context only")
            return None
            
    def _get_required_context_sections(self) -> List[str]:
        """Get list of required context sections based on static context"""
        if not self.static_context:
            return []
            
        required = []
        if 'Critical Dependencies' in self.static_context:
            required.append('external_dependencies')
        if 'Performance Targets' in self.static_context:
            required.append('requirements')
        if 'Processing Patterns' in self.static_context:
            required.append('architecture')
            
        return required
        
    def _filter_context(self, context: ProjectContext, required_sections: List[str]) -> ProjectContext:
        """Filter project context to only include required sections"""
        filtered = ProjectContext(
            engineering_principles={},
            requirements={},
            architecture={},
            external_dependencies={},
            software_design={},
            last_updated=context.last_updated,
            context_version=context.context_version
        )
        
        if 'external_dependencies' in required_sections:
            filtered.external_dependencies = context.external_dependencies
        if 'requirements' in required_sections:
            filtered.requirements = context.requirements
        if 'architecture' in required_sections:
            filtered.architecture = context.architecture
            
        return filtered
        
    def set_task_context(self, task_id: str, context: Dict[str, Any], memory_limit: Optional[int] = None):
        """Set temporary context for current task"""
        self.current_task_id = task_id
        self.task_context_manager.create_task_context(
            task_id=task_id,
            agent_type=self.name,
            initial_context=context,
            memory_limit=memory_limit
        )
        logger.debug(f"{self.name}: Set task context for {task_id}")
        
    def get_current_task_context(self) -> Optional[Dict[str, Any]]:
        """Get context for current task"""
        if not self.current_task_id:
            return None
            
        task_context = self.task_context_manager.get_task_context(self.current_task_id)
        return task_context.context if task_context else None
        
    def update_task_context(self, updates: Dict[str, Any], merge: bool = True):
        """Update context for current task"""
        if not self.current_task_id:
            logger.warning(f"{self.name}: No active task for context update")
            return
            
        self.task_context_manager.update_task_context(
            task_id=self.current_task_id,
            updates=updates,
            merge=merge
        )
        
    def clear_task_context(self):
        """Clear temporary task context"""
        if self.current_task_id:
            self.task_context_manager.cleanup_task_context(self.current_task_id)
            self.current_task_id = None
            logger.debug(f"{self.name}: Cleared task context")
    
    def get_engineering_principles(self) -> Dict[str, Any]:
        """Get engineering principles from available context"""
        if self.static_context and 'Core Responsibilities' in self.static_context:
            # Combine static and project principles if available
            principles = self._get_default_principles()
            if self.project_context and self.project_context.engineering_principles:
                principles.update(self.project_context.engineering_principles)
            return principles
        elif self.project_context:
            return self.project_context.engineering_principles
        return self._get_default_principles()
    
    def get_requirements(self) -> Dict[str, Any]:
        """Get loaded requirements for agent validation"""
        if not self.context_available:
            return {}
        return self.project_context.requirements
    
    def get_architecture_context(self) -> Dict[str, Any]:
        """Get architecture patterns and principles"""
        if not self.context_available:
            return {}
        return self.project_context.architecture
    
    def get_external_dependencies(self) -> Dict[str, Any]:
        """Get external tool integration patterns"""
        if not self.context_available:
            return {}
        return self.project_context.external_dependencies
    
    def apply_timeout_protection(self, timeout_seconds: Optional[int] = None) -> int:
        """Get timeout value based on loaded principles"""
        if self.context_available:
            timeout_protocols = self.project_context.engineering_principles.get('timeout_protocols', {})
            return timeout_seconds or timeout_protocols.get('default_timeout', 30)
        return timeout_seconds or 30
    
    def apply_retry_logic(self, max_retries: Optional[int] = None) -> int:
        """Get retry count based on loaded principles"""
        if self.context_available:
            timeout_protocols = self.project_context.engineering_principles.get('timeout_protocols', {})
            return max_retries or timeout_protocols.get('default_retries', 3)
        return max_retries or 3
    
    def validate_against_requirements(self, result: Any, result_type: str = "general") -> bool:
        """Validate result against loaded requirements"""
        if not self.context_available:
            return True  # No requirements to validate against
        
        try:
            requirements = self.get_requirements()
            
            # Check performance targets
            perf_targets = requirements.get('performance_targets', {})
            if 'min_confidence' in perf_targets and hasattr(result, 'confidence'):
                if result.confidence < perf_targets['min_confidence']:
                    logger.warning(f"{self.name}: Result confidence {result.confidence:.2f} below requirement {perf_targets['min_confidence']:.2f}")
                    return False
            
            # Check quality standards
            quality_standards = requirements.get('quality_standards', {})
            if 'min_accuracy' in quality_standards and hasattr(result, 'accuracy'):
                if result.accuracy < quality_standards['min_accuracy']:
                    logger.warning(f"{self.name}: Result accuracy {result.accuracy:.2f} below requirement {quality_standards['min_accuracy']:.2f}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Error validating against requirements: {e}")
            return True  # Don't fail processing due to validation errors
    
    def apply_documentation_standards(self, function_name: str, purpose: str) -> str:
        """Generate documentation following loaded standards"""
        if not self.context_available:
            return f'"""{purpose}"""'
        
        try:
            doc_standards = self.project_context.engineering_principles.get('documentation_standards', {})
            
            if doc_standards.get('docstring_requirements'):
                return f'''"""
                {purpose}
                
                This function follows V9 engineering principles for comprehensive documentation.
                
                Args:
                    [To be filled based on function parameters]
                    
                Returns:
                    [To be filled based on function return type]
                    
                Raises:
                    [To be filled based on potential exceptions]
                    
                Example:
                    [To be filled with usage example]
                    
                Note:
                    Generated following V9 software engineering principles for WHY-focused documentation.
                    Includes UTF-8 encoding handling for Windows compatibility.
                """'''
            else:
                return f'"""{purpose}"""'
                
        except Exception as e:
            logger.error(f"{self.name}: Error applying documentation standards: {e}")
            return f'"""{purpose}"""'
    
    def get_unicode_standards(self) -> Dict[str, Any]:
        """Get Unicode/encoding standards from loaded principles"""
        if not self.context_available:
            return self._get_default_unicode_standards()
        
        doc_standards = self.project_context.engineering_principles.get('documentation_standards', {})
        return doc_standards.get('unicode_encoding', self._get_default_unicode_standards())
    
    def apply_utf8_setup_pattern(self) -> str:
        """Get the standard UTF-8 setup pattern for Python scripts"""
        return '''
# Set UTF-8 encoding for Windows compatibility
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
'''
    
    def get_safe_console_output(self, message: str, use_ascii_symbols: bool = True) -> str:
        """Convert Unicode symbols to ASCII alternatives for Windows compatibility"""
        if not use_ascii_symbols:
            return message
        
        # Common Unicode to ASCII replacements
        replacements = {
            '✅': '[✓]',
            '❌': '[✗]', 
            '⚠️': '[!]',
            '🎯': '[→]',
            '📊': '[#]',
            '🔧': '[T]',
            '📝': '[=]',
            '🚀': '[^]',
            '⏰': '[T]',
            '🔄': '[↻]',
            '📋': '[□]',
            '🏗️': '[B]',
            '🤖': '[AI]'
        }
        
        safe_message = message
        for unicode_char, ascii_replacement in replacements.items():
            safe_message = safe_message.replace(unicode_char, ascii_replacement)
        
        return safe_message
    
    def _get_default_unicode_standards(self) -> Dict[str, Any]:
        """Default Unicode standards when context unavailable"""
        return {
            'utf8_required': True,
            'windows_compatibility': True,
            'file_operations': "Always specify encoding='utf-8'",
            'console_output': "Use ASCII alternatives for Unicode symbols"
        }
    
    def apply_error_handling_patterns(self) -> Dict[str, Any]:
        """Get error handling patterns from loaded principles"""
        if not self.context_available:
            return self._get_default_error_patterns()
        
        return self.project_context.engineering_principles.get('error_handling_patterns', self._get_default_error_patterns())
    
    def _get_default_principles(self) -> Dict[str, Any]:
        """Default principles when context unavailable"""
        return {
            'documentation_standards': {
                'docstring_requirements': True,
                'comment_focus': 'WHY not WHAT'
            },
            'timeout_protocols': {
                'default_timeout': 30,
                'default_retries': 3
            }
        }
    
    def _get_default_error_patterns(self) -> Dict[str, Any]:
        """Default error handling patterns"""
        return {
            'graceful_degradation': True,
            'timeout_protection': True,
            'retry_logic': True
        }
    
    @abstractmethod
    def _initialize_model(self):
        """Initialize the ML model for this agent"""
        pass
    
    @abstractmethod
    def _preprocess(self, input_data: Any) -> Any:
        """Preprocess input data for model"""
        pass
    
    @abstractmethod
    def _postprocess(self, model_output: Any) -> Dict[str, Any]:
        """Postprocess model output"""
        pass
    
    @abstractmethod
    def _extract_features(self, input_data: Any) -> np.ndarray:
        """Extract features from input data"""
        pass
    
    def process(self, input_data: Any) -> AgentResult:
        """
        Main processing method for the agent
        
        Args:
            input_data: Input data to process
            
        Returns:
            AgentResult with extracted information
        """
        start_time = time.time()
        self.status = AgentStatus.PROCESSING
        errors = []
        
        try:
            # Validate input
            if not self._validate_input(input_data):
                raise ValueError("Invalid input data")
            
            # Preprocess
            preprocessed = self._preprocess(input_data)
            
            # Run model inference
            with torch.no_grad():
                model_output = self._run_inference(preprocessed)
            
            # Postprocess
            processed_data = self._postprocess(model_output)
            
            # Calculate confidence
            confidence = self._calculate_confidence(model_output)
            
            # Update metrics
            processing_time = time.time() - start_time
            self._update_metrics(confidence, processing_time)
            
            # Create result
            result = AgentResult(
                agent_name=self.name,
                status="success",
                confidence=confidence,
                processing_time=processing_time,
                data=processed_data,
                metadata=self._get_metadata()
            )
            
            # NEW: Validate against loaded requirements
            if not self.validate_against_requirements(result):
                logger.warning(f"{self.name}: Result does not meet loaded requirements")
                result.metadata['requirements_validation'] = False
            else:
                result.metadata['requirements_validation'] = True
            
            logger.debug(f"{self.name}: Processing completed in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"{self.name}: Processing error - {str(e)}")
            errors.append(str(e))
            
            result = AgentResult(
                agent_name=self.name,
                status="error",
                confidence=0.0,
                processing_time=time.time() - start_time,
                data={},
                errors=errors
            )
            
            self.metrics["error_count"] += 1
        
        finally:
            self.status = AgentStatus.IDLE
        
        return result
    
    def _validate_input(self, input_data: Any) -> bool:
        """Validate input data"""
        # Basic validation - override in subclasses
        return input_data is not None
    
    def _run_inference(self, preprocessed_data: Any) -> Any:
        """Run model inference"""
        if self.model is None:
            raise RuntimeError(f"{self.name}: Model not initialized")
        
        # Move data to device
        if isinstance(preprocessed_data, torch.Tensor):
            preprocessed_data = preprocessed_data.to(self.device)
        
        # Run inference
        self.model.eval()
        output = self.model(preprocessed_data)
        
        return output
    
    def _calculate_confidence(self, model_output: Any) -> float:
        """
        Calculate confidence score from model output
        Override in subclasses for specific confidence calculation
        """
        if isinstance(model_output, torch.Tensor):
            # For classification, use max probability
            if len(model_output.shape) > 1:
                probs = torch.softmax(model_output, dim=-1)
                confidence = torch.max(probs).item()
            else:
                # For single value output
                confidence = torch.sigmoid(model_output).item()
        else:
            # Default confidence
            confidence = 0.5
            
        return float(confidence)
    
    def _update_metrics(self, confidence: float, processing_time: float):
        """Update agent metrics"""
        n = self.metrics["processed_count"]
        
        # Update count
        self.metrics["processed_count"] = n + 1
        
        # Update total time
        self.metrics["total_processing_time"] += processing_time
        
        # Update average confidence
        avg_conf = self.metrics["average_confidence"]
        self.metrics["average_confidence"] = (avg_conf * n + confidence) / (n + 1)
    
    def _get_metadata(self) -> Dict[str, Any]:
        """Get agent metadata"""
        metadata = {
            "agent_name": self.name,
            "model_version": self.config.get("model_version", "unknown"),
            "device": str(self.device),
            "metrics": self.get_metrics(),
            "context_available": self.context_available
        }
        
        # Add context version if available
        if self.context_available:
            metadata["context_version"] = self.project_context.context_version
            metadata["context_last_updated"] = self.project_context.last_updated
        
        return metadata
    
    def train(self, training_data: Any, validation_data: Any = None) -> Dict[str, float]:
        """
        Train or fine-tune the agent's model
        
        Args:
            training_data: Training dataset
            validation_data: Optional validation dataset
            
        Returns:
            Training metrics
        """
        self.status = AgentStatus.TRAINING
        logger.info(f"{self.name}: Starting training")
        
        try:
            # Training implementation in subclasses
            metrics = self._train_model(training_data, validation_data)
            
            logger.info(f"{self.name}: Training completed")
            return metrics
            
        except Exception as e:
            logger.error(f"{self.name}: Training error - {str(e)}")
            raise
            
        finally:
            self.status = AgentStatus.IDLE
    
    @abstractmethod
    def _train_model(self, training_data: Any, validation_data: Any = None) -> Dict[str, float]:
        """Implementation of model training"""
        pass
    
    def evaluate(self, test_data: Any) -> Dict[str, float]:
        """
        Evaluate agent performance on test data
        
        Args:
            test_data: Test dataset
            
        Returns:
            Evaluation metrics
        """
        logger.info(f"{self.name}: Starting evaluation")
        
        # Evaluation implementation
        metrics = self._evaluate_model(test_data)
        
        logger.info(f"{self.name}: Evaluation completed - {metrics}")
        return metrics
    
    @abstractmethod
    def _evaluate_model(self, test_data: Any) -> Dict[str, float]:
        """Implementation of model evaluation"""
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current agent metrics"""
        return self.metrics.copy()
    
    def reset_metrics(self):
        """Reset agent metrics"""
        self.metrics = {
            "processed_count": 0,
            "total_processing_time": 0.0,
            "average_confidence": 0.0,
            "error_count": 0
        }
        logger.info(f"{self.name}: Metrics reset")
    
    def save_model(self, path: str):
        """Save model to disk"""
        if self.model is None:
            raise RuntimeError(f"{self.name}: No model to save")
            
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "config": self.config,
            "metrics": self.metrics
        }, path)
        
        logger.info(f"{self.name}: Model saved to {path}")
    
    def load_model(self, path: str):
        """Load model from disk"""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.config.update(checkpoint.get("config", {}))
        self.metrics = checkpoint.get("metrics", self.metrics)
        
        logger.info(f"{self.name}: Model loaded from {path}")
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info(f"{self.name}: Cleaning up resources")
        
        # Clear task context
        self.clear_task_context()
        
        # Clear model from memory
        if self.model is not None:
            del self.model
            self.model = None
            
        # Clear GPU cache if using CUDA
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, status={self.status.value})"