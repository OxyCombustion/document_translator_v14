#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Plugin Interface for Context Maintenance System
Defines the contract for maintenance operation plugins

Author: Claude Sonnet 4.5 (Local)
Date: 2025-10-24
Version: 1.0.0
Purpose: Step 6 - Plugin/Hook System
"""

import sys
import os

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class MaintenancePlugin(ABC):
    """
    Abstract base class for maintenance operation plugins.

    All maintenance operations should inherit from this class and implement
    the execute() method. Plugins can be built-in (shipped with the system)
    or user-defined (custom operations).

    Example:
        class MyCustomPlugin(MaintenancePlugin):
            def __init__(self, config):
                super().__init__(
                    name="my_custom_operation",
                    description="Performs custom maintenance",
                    version="1.0.0"
                )
                self.config = config

            def execute(self) -> Dict[str, Any]:
                # Perform operation
                return {
                    "operation": self.name,
                    "success": True,
                    "message": "Operation completed"
                }
    """

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        enabled: bool = True
    ):
        """
        Initialize plugin.

        Args:
            name: Unique plugin identifier (e.g., "requirements_sync")
            description: Human-readable description
            version: Plugin version (semantic versioning)
            enabled: Whether plugin is enabled by default
        """
        self.name = name
        self.description = description
        self.version = version
        self.enabled = enabled

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        """
        Execute the maintenance operation.

        This method must be implemented by all plugins. It should perform
        the maintenance operation and return a result dictionary.

        Returns:
            Dictionary with operation results:
            {
                "operation": str,          # Operation name
                "success": bool,           # Whether operation succeeded
                "duration_seconds": float, # Execution time
                "exit_code": int,          # Exit code (0 = success)
                "stdout": str,             # Standard output
                "stderr": str,             # Standard error
                "error": Optional[str],    # Error message if failed
                # ... plugin-specific fields ...
            }

        Raises:
            Exception: If operation fails critically
        """
        pass

    def validate(self) -> bool:
        """
        Validate plugin can run (check dependencies, files exist, etc.).

        Returns:
            True if plugin can run, False otherwise
        """
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get plugin metadata.

        Returns:
            Dictionary with plugin information
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "valid": self.validate()
        }

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} "
                f"name='{self.name}' "
                f"version='{self.version}' "
                f"enabled={self.enabled}>")
