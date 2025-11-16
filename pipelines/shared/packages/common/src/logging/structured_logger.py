#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Structured Logger for Context Maintenance System
Provides JSON-formatted logging with metrics tracking and structured output

Author: Claude Sonnet 4.5 (Local)
Date: 2025-10-24
Version: 1.0.0
Purpose: Step 5 - Structured Logging System
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

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredLogger:
    """
    JSON-formatted structured logger with metrics tracking.

    Provides consistent structured logging output with:
    - JSON format for machine readability
    - Metrics tracking (counters, timers, success/failure)
    - Context preservation across log entries
    - Integration with standard Python logging

    Example:
        logger = StructuredLogger("maintenance")
        logger.info("Operation started", operation="sync", file_count=5)
        logger.metric("operation_duration", 2.5)
        logger.success("Operation completed", items_processed=10)
    """

    def __init__(
        self,
        name: str,
        log_file: Optional[Path] = None,
        console_output: bool = True,
        json_format: bool = True
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name (used as component identifier)
            log_file: Optional path to log file (None = no file logging)
            console_output: Whether to output to console
            json_format: Whether to use JSON format (False = human-readable)
        """
        self.name = name
        self.json_format = json_format
        self.metrics: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}

        # Create standard Python logger
        self.logger = logging.getLogger(f"structured.{name}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # Remove existing handlers

        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            if json_format:
                console_handler.setFormatter(self._json_formatter())
            else:
                console_handler.setFormatter(self._human_formatter())
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            if json_format:
                file_handler.setFormatter(self._json_formatter())
            else:
                file_handler.setFormatter(self._human_formatter())
            self.logger.addHandler(file_handler)

    def _json_formatter(self) -> logging.Formatter:
        """
        Create JSON log formatter.

        Returns:
            Formatter that outputs JSON-structured log entries
        """
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "component": record.name.replace("structured.", ""),
                    "message": record.getMessage(),
                }

                # Add extra fields from record
                if hasattr(record, 'extra_fields'):
                    log_entry.update(record.extra_fields)

                return json.dumps(log_entry, ensure_ascii=False)

        return JSONFormatter()

    def _human_formatter(self) -> logging.Formatter:
        """
        Create human-readable log formatter.

        Returns:
            Formatter that outputs readable log entries
        """
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _log_with_extras(
        self,
        level: int,
        message: str,
        **kwargs
    ) -> None:
        """
        Log message with extra fields.

        Args:
            level: Logging level (logging.DEBUG, INFO, etc.)
            message: Log message
            **kwargs: Extra fields to include in structured log
        """
        # Merge context and kwargs
        extra_fields = {**self.context, **kwargs}

        # Create log record with extra fields
        if self.json_format:
            self.logger.log(
                level,
                message,
                extra={'extra_fields': extra_fields}
            )
        else:
            # For human-readable format, append fields to message
            if extra_fields:
                fields_str = ", ".join(f"{k}={v}" for k, v in extra_fields.items())
                message = f"{message} [{fields_str}]"
            self.logger.log(level, message)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with extra fields."""
        self._log_with_extras(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with extra fields."""
        self._log_with_extras(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with extra fields."""
        self._log_with_extras(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with extra fields."""
        self._log_with_extras(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with extra fields."""
        self._log_with_extras(logging.CRITICAL, message, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        """
        Log success message (info level with success=True).

        Args:
            message: Success message
            **kwargs: Extra fields
        """
        self.info(message, success=True, **kwargs)

    def failure(self, message: str, **kwargs) -> None:
        """
        Log failure message (error level with success=False).

        Args:
            message: Failure message
            **kwargs: Extra fields
        """
        self.error(message, success=False, **kwargs)

    def metric(self, name: str, value: Any) -> None:
        """
        Record a metric value.

        Args:
            name: Metric name
            value: Metric value (number, duration, count, etc.)
        """
        self.metrics[name] = value
        self.debug(f"Metric recorded: {name}", metric_name=name, metric_value=value)

    def increment_counter(self, name: str, delta: int = 1) -> None:
        """
        Increment a counter metric.

        Args:
            name: Counter name
            delta: Amount to increment (default: 1)
        """
        current = self.metrics.get(name, 0)
        self.metrics[name] = current + delta

    def timer_start(self, name: str) -> None:
        """
        Start a timer metric.

        Args:
            name: Timer name
        """
        self.metrics[f"{name}_start"] = time.time()

    def timer_stop(self, name: str) -> float:
        """
        Stop a timer metric and return duration.

        Args:
            name: Timer name

        Returns:
            Duration in seconds
        """
        start_key = f"{name}_start"
        if start_key not in self.metrics:
            self.warning(f"Timer '{name}' was not started")
            return 0.0

        start_time = self.metrics[start_key]
        duration = time.time() - start_time
        self.metrics[name] = duration
        del self.metrics[start_key]  # Clean up start time

        self.debug(f"Timer stopped: {name}", timer_name=name, duration_seconds=duration)
        return duration

    def set_context(self, **kwargs) -> None:
        """
        Set context fields that will be included in all subsequent log entries.

        Args:
            **kwargs: Context fields to set
        """
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context fields."""
        self.context.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all recorded metrics.

        Returns:
            Dictionary of metric name -> value
        """
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics to empty."""
        self.metrics.clear()

    def log_operation_start(self, operation: str, **kwargs) -> None:
        """
        Log operation start with timer.

        Args:
            operation: Operation name
            **kwargs: Extra fields
        """
        self.timer_start(operation)
        self.info(f"Operation started: {operation}", operation=operation, **kwargs)

    def log_operation_end(
        self,
        operation: str,
        success: bool = True,
        **kwargs
    ) -> float:
        """
        Log operation end with timer and success status.

        Args:
            operation: Operation name
            success: Whether operation succeeded
            **kwargs: Extra fields

        Returns:
            Operation duration in seconds
        """
        duration = self.timer_stop(operation)

        if success:
            self.success(
                f"Operation completed: {operation}",
                operation=operation,
                duration_seconds=duration,
                **kwargs
            )
        else:
            self.failure(
                f"Operation failed: {operation}",
                operation=operation,
                duration_seconds=duration,
                **kwargs
            )

        return duration


# Convenience function to create logger
def get_structured_logger(
    name: str,
    log_file: Optional[Path] = None,
    console_output: bool = True,
    json_format: bool = True
) -> StructuredLogger:
    """
    Create a structured logger instance.

    Args:
        name: Logger name
        log_file: Optional log file path
        console_output: Whether to output to console
        json_format: Whether to use JSON format

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, log_file, console_output, json_format)
