#!/usr/bin/env python
"""Performance Metrics API Routes - Aggregates system performance data"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query

# Import existing performance infrastructure
from ...task_management.infrastructure.performance.task_performance_optimizer import get_performance_optimizer
from ...task_management.infrastructure.cache.cache_manager import get_cache
from ...task_management.infrastructure.database.connection_pool import get_connection_pool, get_supabase_pool
from ...connection_management.infrastructure.services.mcp_server_health_service import MCPServerHealthService
from ...auth.interface.fastapi_auth import get_authenticated_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/performance", tags=["Performance Metrics"])

# Initialize services
health_service = MCPServerHealthService()
performance_optimizer = get_performance_optimizer()


@router.get("/metrics/overview")
async def get_performance_overview(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    include_details: bool = Query(False, description="Include detailed breakdown")
) -> Dict[str, Any]:
    """
    Get comprehensive performance metrics overview.
    
    Returns aggregated metrics from:
    - Connection pools (SQLite & Supabase)  
    - Cache managers (all instances)
    - Query performance analyzer
    - Server health status
    """
    try:
        overview = {
            "timestamp": datetime.now().isoformat(),
            "system_health": "healthy",
            "performance_score": 0.0,  # Calculated below
            "metrics": {}
        }
        
        # 1. Connection Pool Metrics
        connection_metrics = {}
        
        # SQLite pool
        db_path = os.getenv("DATABASE_PATH", "/data/agenthub.db")
        try:
            sqlite_pool = get_connection_pool(db_path)
            sqlite_stats = sqlite_pool.get_stats()
            connection_metrics["sqlite"] = {
                "type": "sqlite",
                "status": "active",
                "pool_size": sqlite_stats.get("pool_size", 0),
                "connections_created": sqlite_stats.get("connections_created", 0),
                "avg_wait_time": sqlite_stats.get("avg_wait_time", 0.0),
                "hit_rate": 1.0 - (sqlite_stats.get("pool_exhausted_count", 0) / max(sqlite_stats.get("get_count", 1), 1))
            }
        except Exception as e:
            logger.warning(f"Could not get SQLite pool stats: {e}")
            connection_metrics["sqlite"] = {"type": "sqlite", "status": "unavailable"}
        
        # Supabase pool  
        try:
            supabase_pool = get_supabase_pool()
            if supabase_pool:
                supabase_stats = supabase_pool.get_pool_status()
                connection_metrics["supabase"] = {
                    "type": "postgresql",
                    "status": "active",
                    "pool_size": supabase_stats.get("size", 0),
                    "checked_out": supabase_stats.get("checked_out", 0),
                    "overflow": supabase_stats.get("overflow", 0),
                    "pool_class": supabase_stats.get("class", "Unknown")
                }
            else:
                connection_metrics["supabase"] = {"type": "postgresql", "status": "not_configured"}
        except Exception as e:
            logger.warning(f"Could not get Supabase pool stats: {e}")
            connection_metrics["supabase"] = {"type": "postgresql", "status": "unavailable"}
        
        overview["metrics"]["connections"] = connection_metrics
        
        # 2. Cache Performance Metrics
        cache_metrics = {}
        cache_names = ["default", "task_cache", "context_cache", "agent_cache"]
        
        for cache_name in cache_names:
            try:
                cache = get_cache(cache_name)
                stats = cache.get_stats()
                cache_metrics[cache_name] = {
                    "hit_rate": stats.get("hit_rate", 0.0),
                    "size": stats.get("size", 0),
                    "max_size": stats.get("max_size", 0),
                    "hits": stats.get("hits", 0),
                    "misses": stats.get("misses", 0),
                    "evictions": stats.get("evictions", 0)
                }
            except Exception as e:
                logger.debug(f"Cache {cache_name} not available: {e}")
                cache_metrics[cache_name] = {"status": "unavailable"}
        
        overview["metrics"]["caching"] = cache_metrics
        
        # 3. Server Health Status
        try:
            environment_info = health_service.get_environment_info()
            config_validation = health_service.validate_server_configuration()
            
            overview["metrics"]["server_health"] = {
                "auth_enabled": environment_info.get("auth_enabled", False),
                "database_configured": environment_info.get("database_configured", False),
                "active_connections": config_validation.get("active_connections", 0),
                "uptime_seconds": config_validation.get("uptime_seconds", 0),
                "status": config_validation.get("status", "unknown")
            }
        except Exception as e:
            logger.error(f"Error getting server health: {e}")
            overview["metrics"]["server_health"] = {"status": "error"}
        
        # 4. Performance Score Calculation
        score_components = []
        
        # Connection pool health (0-30 points)
        if connection_metrics.get("sqlite", {}).get("status") == "active":
            sqlite_hit_rate = connection_metrics["sqlite"].get("hit_rate", 0)
            score_components.append(min(sqlite_hit_rate * 30, 30))
        
        # Cache performance (0-40 points) 
        cache_hit_rates = []
        for cache_name, cache_data in cache_metrics.items():
            if isinstance(cache_data, dict) and "hit_rate" in cache_data:
                cache_hit_rates.append(cache_data["hit_rate"])
        
        if cache_hit_rates:
            avg_cache_hit_rate = sum(cache_hit_rates) / len(cache_hit_rates)
            score_components.append(avg_cache_hit_rate * 40)
        
        # Server health (0-30 points)
        server_status = overview["metrics"]["server_health"].get("status", "unknown")
        if server_status == "healthy":
            score_components.append(30)
        elif server_status == "configuration_error":
            score_components.append(15)
        
        overview["performance_score"] = sum(score_components)
        overview["system_health"] = "healthy" if overview["performance_score"] > 70 else "degraded"
        
        # 5. Include detailed analytics if requested
        if include_details:
            overview["details"] = {
                "cache_distribution": {
                    name: data.get("size", 0) for name, data in cache_metrics.items()
                    if isinstance(data, dict) and "size" in data
                },
                "connection_efficiency": {
                    "sqlite_avg_wait_ms": connection_metrics.get("sqlite", {}).get("avg_wait_time", 0) * 1000,
                    "total_connections_created": connection_metrics.get("sqlite", {}).get("connections_created", 0)
                },
                "performance_recommendations": _generate_performance_recommendations(overview)
            }
        
        return overview
        
    except Exception as e:
        logger.error(f"Error generating performance overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance metrics")


@router.get("/metrics/timeseries")
async def get_performance_timeseries(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    hours: int = Query(24, ge=1, le=168, description="Hours of history (1-168)"),
    interval: str = Query("1h", regex="^(5m|15m|1h|6h|24h)$", description="Data interval")
) -> Dict[str, Any]:
    """
    Get performance metrics over time.
    Note: This is a placeholder implementation. In production, you'd store
    historical metrics in a time-series database like InfluxDB or Prometheus.
    """
    
    # Generate mock time series data for demonstration
    # In production, this would query historical data
    
    now = datetime.now()
    data_points = []
    
    # Convert interval to minutes
    interval_minutes = {
        "5m": 5, "15m": 15, "1h": 60, "6h": 360, "24h": 1440
    }[interval]
    
    points_count = (hours * 60) // interval_minutes
    
    for i in range(points_count):
        timestamp = now - timedelta(minutes=i * interval_minutes)
        
        # Generate realistic mock data (in production, query real historical data)
        data_points.append({
            "timestamp": timestamp.isoformat(),
            "cache_hit_rate": 0.75 + (i % 10) * 0.02,  # 75-95% hit rate
            "avg_response_time": 50 + (i % 20) * 5,      # 50-150ms response time
            "active_connections": 3 + (i % 5),           # 3-8 connections
            "performance_score": 75 + (i % 15)           # 75-90 score
        })
    
    return {
        "interval": interval,
        "hours": hours,
        "data_points": list(reversed(data_points)),
        "note": "This is mock data. In production, implement time-series storage."
    }


@router.get("/metrics/alerts")
async def get_performance_alerts(
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """
    Get current performance alerts and thresholds.
    """
    
    # Get current metrics to check against thresholds
    current_overview = await get_performance_overview(user, include_details=False)
    
    alerts = []
    thresholds = {
        "performance_score_min": 70,
        "cache_hit_rate_min": 0.8,
        "connection_pool_exhaustion_max": 0.1,
        "avg_wait_time_max": 0.5  # 500ms
    }
    
    # Check performance score
    if current_overview["performance_score"] < thresholds["performance_score_min"]:
        alerts.append({
            "type": "warning",
            "metric": "performance_score",
            "current_value": current_overview["performance_score"],
            "threshold": thresholds["performance_score_min"],
            "message": f"Performance score ({current_overview['performance_score']:.1f}) below threshold ({thresholds['performance_score_min']})"
        })
    
    # Check cache hit rates
    cache_metrics = current_overview["metrics"].get("caching", {})
    for cache_name, cache_data in cache_metrics.items():
        if isinstance(cache_data, dict) and "hit_rate" in cache_data:
            hit_rate = cache_data["hit_rate"]
            if hit_rate < thresholds["cache_hit_rate_min"]:
                alerts.append({
                    "type": "warning", 
                    "metric": "cache_hit_rate",
                    "cache_name": cache_name,
                    "current_value": hit_rate,
                    "threshold": thresholds["cache_hit_rate_min"],
                    "message": f"Cache {cache_name} hit rate ({hit_rate:.2%}) below threshold ({thresholds['cache_hit_rate_min']:.0%})"
                })
    
    return {
        "timestamp": datetime.now().isoformat(),
        "active_alerts": alerts,
        "thresholds": thresholds,
        "alert_count": len(alerts)
    }


def _generate_performance_recommendations(overview: Dict[str, Any]) -> List[str]:
    """Generate performance recommendations based on current metrics."""
    
    recommendations = []
    
    # Cache recommendations
    cache_metrics = overview["metrics"].get("caching", {})
    low_hit_rate_caches = [
        name for name, data in cache_metrics.items()
        if isinstance(data, dict) and data.get("hit_rate", 1.0) < 0.8
    ]
    
    if low_hit_rate_caches:
        recommendations.append(f"Consider increasing TTL or cache size for: {', '.join(low_hit_rate_caches)}")
    
    # Connection pool recommendations
    connection_metrics = overview["metrics"].get("connections", {})
    sqlite_data = connection_metrics.get("sqlite", {})
    
    if sqlite_data.get("avg_wait_time", 0) > 0.1:  # 100ms
        recommendations.append("Consider increasing SQLite connection pool size due to high wait times")
    
    # Performance score recommendations  
    if overview["performance_score"] < 80:
        recommendations.append("Overall performance below optimal - review caching strategy and connection pooling")
    
    if not recommendations:
        recommendations.append("System performance is optimal")
    
    return recommendations


@router.post("/metrics/clear-cache")
async def clear_performance_cache(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    cache_name: Optional[str] = Query(None, description="Specific cache to clear (default: all)")
) -> Dict[str, Any]:
    """
    Clear performance cache for testing/maintenance.
    """
    
    cleared_caches = []
    
    if cache_name:
        # Clear specific cache
        try:
            cache = get_cache(cache_name)
            cache.clear()
            cleared_caches.append(cache_name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not clear cache '{cache_name}': {e}")
    else:
        # Clear all caches
        cache_names = ["default", "task_cache", "context_cache", "agent_cache"]
        for name in cache_names:
            try:
                cache = get_cache(name)
                cache.clear()
                cleared_caches.append(name)
            except Exception as e:
                logger.warning(f"Could not clear cache '{name}': {e}")
    
    return {
        "cleared_caches": cleared_caches,
        "timestamp": datetime.now().isoformat(),
        "message": f"Cleared {len(cleared_caches)} cache(s)"
    }