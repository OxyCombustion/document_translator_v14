"""
Configuration Manager for Document Translator V9
Handles YAML configuration loading and validation
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration loading and validation for V9"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/settings.yaml"
        self.config = {}
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            logger.info("Using default configuration")
            self.config = self._get_default_config()
            return self.config
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_file}")
            return self.config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.info("Falling back to default configuration")
            self.config = self._get_default_config()
            return self.config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation (e.g., 'ml.training.batch_size')"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value with dot notation"""
        keys = key.split('.')
        config = self.config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set final value
        config[keys[-1]] = value
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required sections
        required_sections = ['processing', 'files', 'logging']
        for section in required_sections:
            if section not in self.config:
                validation['errors'].append(f"Missing required section: {section}")
                validation['valid'] = False
        
        # Check Python version requirement
        python_version = self.get('processing.python_version', '3.9')
        import sys
        current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if current_version < python_version:
            validation['warnings'].append(f"Python {python_version}+ recommended, found {current_version}")
        
        # Check ML dependencies if ML is enabled
        if self.get('ml.enabled', True):
            try:
                import torch
                validation['warnings'].append("PyTorch available for ML processing")
            except ImportError:
                validation['warnings'].append("PyTorch not found - install for ML features")
        
        # Check file paths
        temp_dir = Path(self.get('files.temp_directory', './temp'))
        results_dir = Path(self.get('files.results_directory', './results'))
        
        for directory in [temp_dir, results_dir]:
            if not directory.exists():
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    validation['warnings'].append(f"Created directory: {directory}")
                except Exception as e:
                    validation['errors'].append(f"Cannot create directory {directory}: {e}")
                    validation['valid'] = False
        
        return validation
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'version': '8.0.0',
            'processing': {
                'mode': 'ml_enhanced',
                'use_mathematica': False,
                'parallel_processing': True,
                'max_workers': 2,
                'cache_results': True,
                'python_version': '3.9'
            },
            'ml': {
                'enabled': True,
                'framework': 'pytorch',
                'device': 'auto'
            },
            'files': {
                'supported_formats': ['pdf', 'docx', 'txt'],
                'max_file_size_mb': 100,
                'temp_directory': './temp',
                'results_directory': './results'
            },
            'logging': {
                'level': 'INFO',
                'file': 'document_translator_v9.log',
                'console_output': True
            },
            'quality': {
                'minimum_accuracy': 0.8,
                'target_accuracy': 0.95
            }
        }
    
    def get_ml_config(self) -> Dict[str, Any]:
        """Get ML-specific configuration"""
        return self.get('ml', {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration"""
        return self.get('processing', {})
    
    def is_ml_enabled(self) -> bool:
        """Check if ML processing is enabled"""
        return self.get('ml.enabled', True)
    
    def get_device(self) -> str:
        """Get ML device (cpu, cuda, etc.)"""
        device = self.get('ml.device', 'auto')
        
        if device == 'auto':
            try:
                import torch
                return 'cuda' if torch.cuda.is_available() else 'cpu'
            except ImportError:
                return 'cpu'
        
        return device
    
    def save_config(self, path: Optional[str] = None) -> bool:
        """Save current configuration to file"""
        save_path = path or self.config_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {save_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def __repr__(self) -> str:
        return f"ConfigManager(config_path='{self.config_path}', version='{self.get('version', 'unknown')}')"


def main():
    """Test configuration manager"""
    config = ConfigManager()
    
    print(f"Configuration Manager: {config}")
    print(f"ML Enabled: {config.is_ml_enabled()}")
    print(f"Device: {config.get_device()}")
    print(f"Processing Mode: {config.get('processing.mode')}")
    
    # Validate configuration
    validation = config.validate_config()
    print(f"\nValidation: {'✅ VALID' if validation['valid'] else '❌ INVALID'}")
    
    if validation['errors']:
        print("Errors:")
        for error in validation['errors']:
            print(f"  - {error}")
    
    if validation['warnings']:
        print("Warnings:")
        for warning in validation['warnings']:
            print(f"  - {warning}")


if __name__ == "__main__":
    main()