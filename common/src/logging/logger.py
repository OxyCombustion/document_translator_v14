"""
Logging Configuration for Document Translator V9
Provides structured logging with ML metrics support
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager


class MLFormatter(logging.Formatter):
    """Custom formatter that handles ML metrics and structured data"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)8s | %(name)25s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record):
        # Add ML context if available
        if hasattr(record, 'ml_context'):
            record.msg = f"[{record.ml_context}] {record.msg}"
        
        # Handle dictionaries and objects
        if isinstance(record.msg, dict):
            record.msg = json.dumps(record.msg, indent=2)
        
        return super().format(record)


class V8Logger:
    """Document Translator V9 Logger with ML support"""
    
    def __init__(self, name: str = "DocumentTranslatorV9", config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or self._get_default_config()
        self.logger = self._setup_logger()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default logging configuration"""
        return {
            'level': 'INFO',
            'file': 'document_translator_v9.log',
            'max_size_mb': 100,
            'backup_count': 5,
            'console_output': True,
            'ml_logging': {
                'track_metrics': True,
                'training_progress': True,
                'prediction_logs': False
            }
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logger with file and console handlers"""
        logger = logging.getLogger(self.name)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Set level
        level = getattr(logging, self.config.get('level', 'INFO').upper())
        logger.setLevel(level)
        
        # Create formatter
        formatter = MLFormatter()
        
        # Console handler
        if self.config.get('console_output', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = Path(self.config.get('file', 'document_translator_v9.log'))
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        max_bytes = self.config.get('max_size_mb', 100) * 1024 * 1024
        backup_count = self.config.get('backup_count', 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    @contextmanager
    def ml_context(self, context: str):
        """Context manager for ML logging"""
        try:
            # Store original logger
            original_logger = self.logger
            
            # Create context-aware logger
            class ContextLogger:
                def __init__(self, logger, context):
                    self._logger = logger
                    self._context = context
                
                def info(self, msg, *args, **kwargs):
                    extra = kwargs.get('extra', {})
                    extra['ml_context'] = self._context
                    kwargs['extra'] = extra
                    self._logger.info(msg, *args, **kwargs)
                
                def debug(self, msg, *args, **kwargs):
                    extra = kwargs.get('extra', {})
                    extra['ml_context'] = self._context
                    kwargs['extra'] = extra
                    self._logger.debug(msg, *args, **kwargs)
                
                def warning(self, msg, *args, **kwargs):
                    extra = kwargs.get('extra', {})
                    extra['ml_context'] = self._context
                    kwargs['extra'] = extra
                    self._logger.warning(msg, *args, **kwargs)
                
                def error(self, msg, *args, **kwargs):
                    extra = kwargs.get('extra', {})
                    extra['ml_context'] = self._context
                    kwargs['extra'] = extra
                    self._logger.error(msg, *args, **kwargs)
                
                def critical(self, msg, *args, **kwargs):
                    extra = kwargs.get('extra', {})
                    extra['ml_context'] = self._context
                    kwargs['extra'] = extra
                    self._logger.critical(msg, *args, **kwargs)
            
            self.logger = ContextLogger(original_logger, context)
            yield self.logger
            
        finally:
            self.logger = original_logger
    
    def log_ml_metrics(self, metrics: Dict[str, Any], stage: str = "training"):
        """Log ML metrics with structured format"""
        if not self.config.get('ml_logging', {}).get('track_metrics', True):
            return
        
        formatted_metrics = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'metrics': metrics
        }
        
        self.logger.info(f"ML Metrics [{stage}]: {json.dumps(metrics, indent=2)}")
    
    def log_processing_progress(self, current: int, total: int, item_name: str = "items"):
        """Log processing progress"""
        percentage = (current / total * 100) if total > 0 else 0
        self.logger.info(f"Progress: {current}/{total} {item_name} ({percentage:.1f}%)")
    
    def log_model_performance(self, model_name: str, metrics: Dict[str, float]):
        """Log model performance metrics"""
        if not self.config.get('ml_logging', {}).get('track_metrics', True):
            return
        
        metrics_str = ", ".join([f"{k}: {v:.4f}" for k, v in metrics.items()])
        self.logger.info(f"Model Performance [{model_name}]: {metrics_str}")
    
    def log_document_processing(self, document_id: str, processing_time: float, 
                              confidence: float, status: str = "success"):
        """Log document processing results"""
        self.logger.info(
            f"Document [{document_id}]: {status} in {processing_time:.2f}s "
            f"(confidence: {confidence:.2%})"
        )
    
    def log_system_status(self, status_info: Dict[str, Any]):
        """Log system status information"""
        self.logger.info(f"System Status: {json.dumps(status_info, indent=2)}")
    
    def info(self, msg, *args, **kwargs):
        """Info level logging"""
        self.logger.info(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        """Debug level logging"""
        self.logger.debug(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        """Warning level logging"""
        self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        """Error level logging"""
        self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        """Critical level logging"""
        self.logger.critical(msg, *args, **kwargs)


# Global logger instance
_global_logger = None

def setup_logger(name: str = None, config: Dict[str, Any] = None) -> logging.Logger:
    """Set up and return a logger instance"""
    global _global_logger
    
    if _global_logger is None or name:
        logger_name = name or "DocumentTranslatorV9"
        _global_logger = V8Logger(logger_name, config)
    
    return _global_logger.logger


def get_logger(name: str = None) -> V8Logger:
    """Get the V8Logger instance"""
    global _global_logger
    
    if _global_logger is None:
        _global_logger = V8Logger(name or "DocumentTranslatorV9")
    
    return _global_logger


def main():
    """Test logging functionality"""
    logger = get_logger("TestLogger")
    
    logger.info("Testing V9 Logger")
    logger.debug("Debug message")
    logger.warning("Warning message")
    
    # Test ML context
    with logger.ml_context("SymbolDetection"):
        logger.info("Processing symbols with YOLOv8")
        logger.log_ml_metrics({
            'accuracy': 0.95,
            'loss': 0.045,
            'f1_score': 0.92
        })
    
    # Test progress logging
    for i in range(1, 6):
        logger.log_processing_progress(i, 5, "documents")
    
    # Test model performance
    logger.log_model_performance("YOLOv8", {
        'mAP': 0.87,
        'precision': 0.89,
        'recall': 0.91
    })
    
    print("✅ Logger test complete - check log file")


if __name__ == "__main__":
    main()