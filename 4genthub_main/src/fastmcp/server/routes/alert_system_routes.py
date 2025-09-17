#!/usr/bin/env python
"""Alert System API Routes - Configurable performance alerting with webhook notifications"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import httpx

from ...auth.interface.fastapi_auth import get_authenticated_user
from ...task_management.infrastructure.performance.task_performance_optimizer import get_performance_optimizer
from ...task_management.infrastructure.cache.cache_manager import get_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["Alert System"])


@dataclass
class AlertRule:
    """Configuration for a performance alert rule."""
    id: str
    name: str
    metric: str
    condition: str  # 'greater_than', 'less_than', 'equals'
    threshold: float
    enabled: bool = True
    webhook_url: Optional[str] = None
    cooldown_minutes: int = 30
    severity: str = "warning"  # 'info', 'warning', 'error', 'critical'
    description: str = ""


@dataclass
class AlertEvent:
    """Represents a triggered alert event."""
    rule_id: str
    rule_name: str
    metric: str
    current_value: float
    threshold: float
    severity: str
    message: str
    timestamp: datetime
    acknowledged: bool = False
    webhook_sent: bool = False


# In-memory storage for demo (in production, use database)
_alert_rules: Dict[str, AlertRule] = {}
_alert_events: List[AlertEvent] = []
_alert_cache = get_cache("alerts")


@router.get("/rules")
async def list_alert_rules(
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """List all configured alert rules."""
    
    return {
        "rules": [asdict(rule) for rule in _alert_rules.values()],
        "total_rules": len(_alert_rules),
        "enabled_rules": len([r for r in _alert_rules.values() if r.enabled])
    }


@router.post("/rules")
async def create_alert_rule(
    rule_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """
    Create a new alert rule.
    
    Example rule_data:
    {
        "name": "Low Cache Hit Rate",
        "metric": "cache_hit_rate",
        "condition": "less_than",
        "threshold": 0.8,
        "severity": "warning",
        "webhook_url": "https://hooks.slack.com/...",
        "description": "Alert when cache hit rate falls below 80%"
    }
    """
    
    try:
        # Validate required fields
        required_fields = ['name', 'metric', 'condition', 'threshold']
        for field in required_fields:
            if field not in rule_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Generate unique ID
        rule_id = f"rule_{len(_alert_rules) + 1}_{int(datetime.now().timestamp())}"
        
        # Create alert rule
        alert_rule = AlertRule(
            id=rule_id,
            name=rule_data['name'],
            metric=rule_data['metric'],
            condition=rule_data['condition'],
            threshold=float(rule_data['threshold']),
            enabled=rule_data.get('enabled', True),
            webhook_url=rule_data.get('webhook_url'),
            cooldown_minutes=rule_data.get('cooldown_minutes', 30),
            severity=rule_data.get('severity', 'warning'),
            description=rule_data.get('description', '')
        )
        
        # Validate condition
        valid_conditions = ['greater_than', 'less_than', 'equals']
        if alert_rule.condition not in valid_conditions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid condition. Must be one of: {valid_conditions}"
            )
        
        # Store rule
        _alert_rules[rule_id] = alert_rule
        
        return {
            "message": "Alert rule created successfully",
            "rule_id": rule_id,
            "rule": asdict(alert_rule)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert rule")


@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: str,
    rule_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """Update an existing alert rule."""
    
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    try:
        rule = _alert_rules[rule_id]
        
        # Update fields
        if 'name' in rule_data:
            rule.name = rule_data['name']
        if 'metric' in rule_data:
            rule.metric = rule_data['metric']
        if 'condition' in rule_data:
            rule.condition = rule_data['condition']
        if 'threshold' in rule_data:
            rule.threshold = float(rule_data['threshold'])
        if 'enabled' in rule_data:
            rule.enabled = rule_data['enabled']
        if 'webhook_url' in rule_data:
            rule.webhook_url = rule_data['webhook_url']
        if 'cooldown_minutes' in rule_data:
            rule.cooldown_minutes = rule_data['cooldown_minutes']
        if 'severity' in rule_data:
            rule.severity = rule_data['severity']
        if 'description' in rule_data:
            rule.description = rule_data['description']
        
        return {
            "message": "Alert rule updated successfully",
            "rule": asdict(rule)
        }
        
    except Exception as e:
        logger.error(f"Error updating alert rule: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert rule")


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """Delete an alert rule."""
    
    if rule_id not in _alert_rules:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    del _alert_rules[rule_id]
    
    return {"message": "Alert rule deleted successfully"}


@router.get("/events")
async def list_alert_events(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    limit: int = 50,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None
) -> Dict[str, Any]:
    """List recent alert events with optional filtering."""
    
    events = _alert_events
    
    # Apply filters
    if severity:
        events = [e for e in events if e.severity == severity]
    
    if acknowledged is not None:
        events = [e for e in events if e.acknowledged == acknowledged]
    
    # Sort by timestamp (newest first) and limit
    events = sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    # Convert to dict for JSON serialization
    events_data = []
    for event in events:
        event_dict = asdict(event)
        event_dict['timestamp'] = event.timestamp.isoformat()
        events_data.append(event_dict)
    
    return {
        "events": events_data,
        "total_events": len(_alert_events),
        "unacknowledged_events": len([e for e in _alert_events if not e.acknowledged])
    }


@router.post("/events/{event_index}/acknowledge")
async def acknowledge_alert(
    event_index: int,
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """Acknowledge an alert event."""
    
    if event_index >= len(_alert_events) or event_index < 0:
        raise HTTPException(status_code=404, detail="Alert event not found")
    
    _alert_events[event_index].acknowledged = True
    
    return {"message": "Alert acknowledged successfully"}


@router.post("/check-rules")
async def check_alert_rules(
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """
    Manually trigger alert rule checking.
    Normally this would run on a schedule.
    """
    
    background_tasks.add_task(_check_and_trigger_alerts)
    
    return {
        "message": "Alert rule check initiated",
        "active_rules": len([r for r in _alert_rules.values() if r.enabled])
    }


@router.post("/test-webhook")
async def test_webhook(
    webhook_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(get_authenticated_user)
) -> Dict[str, Any]:
    """Test a webhook URL with sample alert data."""
    
    webhook_url = webhook_data.get('webhook_url')
    if not webhook_url:
        raise HTTPException(status_code=400, detail="webhook_url is required")
    
    # Sample alert payload
    test_payload = {
        "alert_type": "test",
        "rule_name": "Test Alert",
        "metric": "test_metric",
        "current_value": 0.5,
        "threshold": 0.8,
        "severity": "info",
        "message": "This is a test alert from the 4genthub system",
        "timestamp": datetime.now().isoformat(),
        "system": "4genthub"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook_url,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
        return {
            "message": "Test webhook sent successfully",
            "status_code": response.status_code,
            "response": response.text[:500] if response.text else None
        }
        
    except Exception as e:
        logger.error(f"Error testing webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook test failed: {str(e)}")


async def _check_and_trigger_alerts():
    """Background task to check alert rules and trigger notifications."""
    
    logger.info("Checking alert rules...")
    
    try:
        # Get current performance metrics (reuse from performance routes)
        from .performance_metrics_routes import get_performance_overview
        
        # Mock user for internal system checks
        mock_user = {"sub": "system"}
        
        # Get current metrics
        current_metrics = await get_performance_overview(mock_user, include_details=False)
        
        alerts_triggered = 0
        
        for rule in _alert_rules.values():
            if not rule.enabled:
                continue
            
            # Check cooldown
            last_trigger = _get_last_trigger_time(rule.id)
            if last_trigger and (datetime.now() - last_trigger).total_seconds() < rule.cooldown_minutes * 60:
                continue
            
            # Extract metric value
            current_value = _extract_metric_value(current_metrics, rule.metric)
            if current_value is None:
                logger.warning(f"Could not extract metric '{rule.metric}' for rule '{rule.name}'")
                continue
            
            # Check condition
            triggered = False
            if rule.condition == "greater_than" and current_value > rule.threshold:
                triggered = True
            elif rule.condition == "less_than" and current_value < rule.threshold:
                triggered = True
            elif rule.condition == "equals" and abs(current_value - rule.threshold) < 0.001:
                triggered = True
            
            if triggered:
                await _trigger_alert(rule, current_value)
                alerts_triggered += 1
        
        logger.info(f"Alert check completed. Triggered: {alerts_triggered}")
        
    except Exception as e:
        logger.error(f"Error in alert checking: {e}")


async def _trigger_alert(rule: AlertRule, current_value: float):
    """Trigger an alert and send webhook if configured."""
    
    # Create alert event
    message = f"{rule.name}: {rule.metric} is {current_value:.2f} (threshold: {rule.threshold:.2f})"
    
    event = AlertEvent(
        rule_id=rule.id,
        rule_name=rule.name,
        metric=rule.metric,
        current_value=current_value,
        threshold=rule.threshold,
        severity=rule.severity,
        message=message,
        timestamp=datetime.now()
    )
    
    # Store event
    _alert_events.append(event)
    
    # Keep only last 1000 events
    if len(_alert_events) > 1000:
        _alert_events.pop(0)
    
    logger.warning(f"ALERT TRIGGERED: {message}")
    
    # Send webhook if configured
    if rule.webhook_url:
        try:
            webhook_payload = {
                "alert_type": "performance_alert",
                "rule_name": rule.name,
                "metric": rule.metric,
                "current_value": current_value,
                "threshold": rule.threshold,
                "severity": rule.severity,
                "message": message,
                "timestamp": event.timestamp.isoformat(),
                "system": "4genthub",
                "rule_id": rule.id
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    rule.webhook_url,
                    json=webhook_payload,
                    headers={"Content-Type": "application/json"}
                )
                
            event.webhook_sent = True
            logger.info(f"Webhook sent for alert '{rule.name}': {response.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook for alert '{rule.name}': {e}")


def _get_last_trigger_time(rule_id: str) -> Optional[datetime]:
    """Get the timestamp of the last trigger for a rule."""
    
    for event in reversed(_alert_events):
        if event.rule_id == rule_id:
            return event.timestamp
    
    return None


def _extract_metric_value(metrics_data: Dict, metric_name: str) -> Optional[float]:
    """Extract a specific metric value from the performance data."""
    
    try:
        # Performance score
        if metric_name == "performance_score":
            return metrics_data.get("performance_score")
        
        # Cache hit rates
        if metric_name == "cache_hit_rate":
            cache_metrics = metrics_data.get("metrics", {}).get("caching", {})
            hit_rates = []
            for cache_data in cache_metrics.values():
                if isinstance(cache_data, dict) and "hit_rate" in cache_data:
                    hit_rates.append(cache_data["hit_rate"])
            return sum(hit_rates) / len(hit_rates) if hit_rates else None
        
        # Connection pool metrics
        if metric_name == "connection_wait_time":
            sqlite_data = metrics_data.get("metrics", {}).get("connections", {}).get("sqlite", {})
            return sqlite_data.get("avg_wait_time")
        
        # Active connections
        if metric_name == "active_connections":
            return metrics_data.get("metrics", {}).get("server_health", {}).get("active_connections")
        
        # System health status (convert to numeric)
        if metric_name == "system_health":
            health = metrics_data.get("system_health", "unknown")
            health_scores = {"healthy": 1.0, "degraded": 0.5, "critical": 0.0}
            return health_scores.get(health, 0.0)
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting metric '{metric_name}': {e}")
        return None


# Initialize some default alert rules
def _initialize_default_rules():
    """Initialize some sensible default alert rules."""
    
    if not _alert_rules:  # Only initialize if empty
        default_rules = [
            {
                "name": "Low Performance Score",
                "metric": "performance_score", 
                "condition": "less_than",
                "threshold": 70.0,
                "severity": "warning",
                "description": "Alert when overall performance score drops below 70"
            },
            {
                "name": "Critical Performance Score",
                "metric": "performance_score",
                "condition": "less_than", 
                "threshold": 50.0,
                "severity": "critical",
                "description": "Critical alert when performance score drops below 50"
            },
            {
                "name": "Low Cache Hit Rate",
                "metric": "cache_hit_rate",
                "condition": "less_than",
                "threshold": 0.6,
                "severity": "warning", 
                "description": "Alert when average cache hit rate falls below 60%"
            },
            {
                "name": "High Connection Wait Time",
                "metric": "connection_wait_time",
                "condition": "greater_than",
                "threshold": 0.5,  # 500ms
                "severity": "warning",
                "description": "Alert when database connection wait time exceeds 500ms"
            }
        ]
        
        for i, rule_data in enumerate(default_rules):
            rule_id = f"default_rule_{i+1}"
            _alert_rules[rule_id] = AlertRule(
                id=rule_id,
                name=rule_data['name'],
                metric=rule_data['metric'],
                condition=rule_data['condition'],
                threshold=rule_data['threshold'],
                severity=rule_data['severity'],
                description=rule_data['description'],
                enabled=True
            )
        
        logger.info(f"Initialized {len(default_rules)} default alert rules")


# Initialize on module import
_initialize_default_rules()