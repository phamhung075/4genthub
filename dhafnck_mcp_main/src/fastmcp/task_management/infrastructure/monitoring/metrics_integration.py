#!/usr/bin/env python3
"""
Metrics Integration Module

Integrates optimization metrics collection into the MCP system,
providing decorators, context managers, and middleware for automatic
metrics collection across all system operations.
"""

import time
import asyncio
import logging
import functools
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta

from .optimization_metrics import (
    OptimizationMetricsCollector,
    get_global_optimization_collector,
    record_response_optimization,
    record_context_metrics,
    record_ai_metrics
)
from ..workers.metrics_reporter import (
    MetricsReporter,
    ReportConfig,
    get_global_metrics_reporter,
    start_automated_reporting
)

logger = logging.getLogger(__name__)


class MetricsMiddleware:
    """FastAPI middleware for automatic metrics collection."""
    
    def __init__(self, app, collector: Optional[OptimizationMetricsCollector] = None):
        """Initialize metrics middleware."""
        self.app = app
        self.collector = collector or get_global_optimization_collector()
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.perf_counter()
        request_size = 0
        response_size = 0
        
        # Wrap receive to measure request size
        async def receive_wrapper():
            nonlocal request_size
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                request_size += len(body)
            return message
        
        # Wrap send to measure response size
        async def send_wrapper(message):
            nonlocal response_size
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                response_size += len(body)
            await send(message)
        
        # Process request
        await self.app(scope, receive_wrapper, send_wrapper)
        
        # Record metrics
        end_time = time.perf_counter()
        processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Extract route information
        path = scope.get("path", "unknown")
        method = scope.get("method", "unknown")
        
        # Record API response metrics
        self.collector.record_timing_metric(
            "api_response_time",
            start_time,
            end_time,
            tags={"path": path, "method": method}
        )
        
        self.collector.record_size_metric(
            "api_request_size",
            request_size,
            tags={"path": path, "method": method}
        )
        
        self.collector.record_size_metric(
            "api_response_size", 
            response_size,
            tags={"path": path, "method": method}
        )
        
        # Calculate compression ratio if applicable
        if request_size > 0 and response_size > 0:
            if response_size < request_size:
                compression_ratio = ((request_size - response_size) / request_size) * 100
                self.collector.record_percentage_metric(
                    "api_compression_ratio",
                    compression_ratio,
                    tags={"path": path, "method": method}
                )


def metrics_track(
    operation_name: str,
    track_timing: bool = True,
    track_errors: bool = True,
    track_success_rate: bool = True,
    custom_tags: Optional[Dict[str, str]] = None
):
    """Decorator for automatic metrics tracking on functions."""
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_global_optimization_collector()
            tags = {**(custom_tags or {}), "operation": operation_name}
            
            start_time = time.perf_counter() if track_timing else None
            success = True
            error_type = None
            
            try:
                result = await func(*args, **kwargs)
                
                # Track success if enabled
                if track_success_rate:
                    collector.record_metric(f"{operation_name}_success", 1.0, "boolean", tags)
                
                return result
                
            except Exception as e:
                success = False
                error_type = type(e).__name__
                
                # Track error if enabled
                if track_errors:
                    error_tags = {**tags, "error_type": error_type}
                    collector.record_metric(f"{operation_name}_errors", 1.0, "count", error_tags)
                
                # Track failure if success tracking enabled
                if track_success_rate:
                    collector.record_metric(f"{operation_name}_success", 0.0, "boolean", tags)
                
                raise
                
            finally:
                # Track timing if enabled
                if track_timing and start_time is not None:
                    end_time = time.perf_counter()
                    duration_ms = (end_time - start_time) * 1000
                    collector.record_timing_metric(
                        f"{operation_name}_duration",
                        start_time,
                        end_time,
                        tags=tags
                    )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_global_optimization_collector()
            tags = {**(custom_tags or {}), "operation": operation_name}
            
            start_time = time.perf_counter() if track_timing else None
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                
                # Track success if enabled
                if track_success_rate:
                    collector.record_metric(f"{operation_name}_success", 1.0, "boolean", tags)
                
                return result
                
            except Exception as e:
                success = False
                error_type = type(e).__name__
                
                # Track error if enabled
                if track_errors:
                    error_tags = {**tags, "error_type": error_type}
                    collector.record_metric(f"{operation_name}_errors", 1.0, "count", error_tags)
                
                # Track failure if success tracking enabled
                if track_success_rate:
                    collector.record_metric(f"{operation_name}_success", 0.0, "boolean", tags)
                
                raise
                
            finally:
                # Track timing if enabled
                if track_timing and start_time is not None:
                    end_time = time.perf_counter()
                    duration_ms = (end_time - start_time) * 1000
                    collector.record_timing_metric(
                        f"{operation_name}_duration",
                        start_time,
                        end_time,
                        tags=tags
                    )
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def optimization_context(
    optimization_type: str,
    operation: str = "generic",
    tags: Optional[Dict[str, str]] = None
):
    """Async context manager for optimization tracking."""
    
    collector = get_global_optimization_collector()
    start_time = time.perf_counter()
    context_tags = {**(tags or {}), "optimization_type": optimization_type, "operation": operation}
    
    # Context data for tracking
    context_data = {
        "original_size": None,
        "optimized_size": None,
        "fields_requested": None,
        "fields_returned": None,
        "cache_hit": False,
        "parse_success": True,
        "error_type": None
    }
    
    try:
        yield context_data
        
    except Exception as e:
        context_data["parse_success"] = False
        context_data["error_type"] = type(e).__name__
        raise
        
    finally:
        end_time = time.perf_counter()
        processing_time_ms = (end_time - start_time) * 1000
        
        # Record optimization metrics based on available data
        if context_data.get("original_size") and context_data.get("optimized_size"):
            collector.record_response_optimization(
                original_size=context_data["original_size"],
                optimized_size=context_data["optimized_size"],
                processing_time_ms=processing_time_ms,
                optimization_type=optimization_type,
                operation=operation,
                tags=context_tags
            )
        
        # Record context metrics if available
        if context_data.get("fields_requested") is not None:
            collector.record_context_injection_metrics(
                fields_requested=context_data.get("fields_requested", 0),
                fields_returned=context_data.get("fields_returned", 0),
                query_time_ms=processing_time_ms,
                cache_hit=context_data.get("cache_hit", False),
                tags=context_tags
            )
        
        # Record AI metrics
        collector.record_ai_performance_metrics(
            parse_success=context_data.get("parse_success", True),
            extraction_time_ms=processing_time_ms,
            response_format=optimization_type,
            agent_operation=operation,
            error_type=context_data.get("error_type"),
            tags=context_tags
        )


@contextmanager
def response_optimization_tracker(
    optimization_type: str,
    original_size: int,
    operation: str = "response_format",
    tags: Optional[Dict[str, str]] = None
):
    """Context manager for tracking response optimization."""
    
    collector = get_global_optimization_collector()
    start_time = time.perf_counter()
    
    # Tracking data
    tracking_data = {
        "optimized_size": original_size,  # Default to original if not updated
        "cache_hit": False,
        "error_occurred": False
    }
    
    try:
        yield tracking_data
        
    except Exception as e:
        tracking_data["error_occurred"] = True
        logger.error(f"Error in response optimization tracking: {e}")
        raise
        
    finally:
        end_time = time.perf_counter()
        processing_time_ms = (end_time - start_time) * 1000
        
        # Record optimization metrics
        collector.record_response_optimization(
            original_size=original_size,
            optimized_size=tracking_data["optimized_size"],
            processing_time_ms=processing_time_ms,
            optimization_type=optimization_type,
            operation=operation,
            tags=tags
        )


class MetricsCollectionService:
    """Service for managing metrics collection lifecycle."""
    
    def __init__(self):
        """Initialize metrics collection service."""
        self.collector = get_global_optimization_collector()
        self.reporter = None
        self._started = False
    
    async def start_metrics_collection(
        self,
        enable_reporting: bool = True,
        report_config: Optional[ReportConfig] = None
    ):
        """Start metrics collection and optional reporting."""
        
        if self._started:
            logger.info("Metrics collection already started")
            return
        
        # Start metrics collection
        self.collector.start_collection()
        
        # Start automated reporting if enabled
        if enable_reporting:
            if report_config is None:
                report_config = ReportConfig(
                    file_output_enabled=True,
                    email_enabled=False,  # Disabled by default for security
                    output_directory=Path("/tmp/mcp_reports")
                )
            
            self.reporter = get_global_metrics_reporter(report_config)
            await self.reporter.start_reporting()
        
        self._started = True
        logger.info("Metrics collection service started")
    
    async def stop_metrics_collection(self):
        """Stop metrics collection and reporting."""
        
        if not self._started:
            logger.info("Metrics collection not started")
            return
        
        # Stop reporting
        if self.reporter:
            await self.reporter.stop_reporting()
            self.reporter = None
        
        # Stop metrics collection
        await self.collector.stop_collection()
        
        self._started = False
        logger.info("Metrics collection service stopped")
    
    def get_real_time_metrics(self, time_window_hours: float = 1) -> Dict[str, Any]:
        """Get real-time metrics summary."""
        return self.collector.get_optimization_summary(time_window_hours)
    
    def get_dashboard_data(self, time_window_hours: float = 24) -> Dict[str, Any]:
        """Get dashboard data for visualization."""
        return self.collector.export_optimization_dashboard_data(time_window_hours)
    
    async def generate_on_demand_report(self, report_type: str = "daily") -> Dict[str, Any]:
        """Generate on-demand report."""
        if not self.reporter:
            raise RuntimeError("Reporting not enabled - start metrics collection with enable_reporting=True")
        
        if report_type == "daily":
            return await self.reporter.generate_daily_report()
        elif report_type == "weekly":
            return await self.reporter.generate_weekly_report()
        elif report_type == "monthly":
            return await self.reporter.generate_monthly_roi_report()
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def add_custom_metric(
        self,
        name: str,
        value: float,
        unit: str = "count",
        tags: Optional[Dict[str, str]] = None,
        category: str = "custom"
    ):
        """Add custom metric to collection."""
        self.collector.record_metric(name, value, unit, tags, category)
    
    def set_alert_thresholds(self, thresholds: Dict[str, float]):
        """Update alert thresholds."""
        self.collector.performance_baselines.update(thresholds)
        logger.info(f"Updated alert thresholds: {thresholds}")


# Global metrics service instance
_global_metrics_service: Optional[MetricsCollectionService] = None


def get_metrics_service() -> MetricsCollectionService:
    """Get or create the global metrics service."""
    global _global_metrics_service
    if _global_metrics_service is None:
        _global_metrics_service = MetricsCollectionService()
    return _global_metrics_service


# Convenience functions for common operations
async def initialize_metrics_system(
    enable_reporting: bool = True,
    output_directory: Optional[str] = None,
    email_config: Optional[Dict[str, Any]] = None
) -> MetricsCollectionService:
    """Initialize the complete metrics system."""
    
    service = get_metrics_service()
    
    # Configure reporting if enabled
    if enable_reporting:
        report_config = ReportConfig(
            file_output_enabled=True,
            output_directory=Path(output_directory) if output_directory else Path("/tmp/mcp_reports")
        )
        
        # Configure email if provided
        if email_config:
            report_config.email_enabled = email_config.get("enabled", False)
            report_config.email_smtp_server = email_config.get("smtp_server", "localhost")
            report_config.email_smtp_port = email_config.get("smtp_port", 587)
            report_config.email_username = email_config.get("username", "")
            report_config.email_password = email_config.get("password", "")
            report_config.email_recipients = email_config.get("recipients", [])
    else:
        report_config = None
    
    await service.start_metrics_collection(enable_reporting, report_config)
    
    logger.info("Metrics system initialized successfully")
    return service


def track_optimization(optimization_type: str, operation: str = "generic"):
    """Decorator for tracking optimization operations."""
    return metrics_track(
        operation_name=f"optimization_{operation}",
        custom_tags={"optimization_type": optimization_type}
    )


def track_context_operation(operation: str):
    """Decorator for tracking context operations."""
    return metrics_track(
        operation_name=f"context_{operation}",
        custom_tags={"context_operation": operation}
    )


def track_ai_operation(operation: str):
    """Decorator for tracking AI operations.""" 
    return metrics_track(
        operation_name=f"ai_{operation}",
        custom_tags={"ai_operation": operation}
    )


# Export key components for easy imports
__all__ = [
    'MetricsMiddleware',
    'MetricsCollectionService',
    'get_metrics_service',
    'initialize_metrics_system',
    'metrics_track',
    'optimization_context',
    'response_optimization_tracker',
    'track_optimization',
    'track_context_operation',
    'track_ai_operation'
]