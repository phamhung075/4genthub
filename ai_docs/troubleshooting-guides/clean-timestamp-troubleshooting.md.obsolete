# Clean Timestamp System - Troubleshooting Guide

## Quick Reference

### 🚨 Emergency Contacts
- **Production Issues**: DevOps team (24/7)
- **Architecture Questions**: Senior developers
- **Performance Problems**: Performance engineering team

### 📊 Health Check Commands
```bash
# Quick system health check
python -c "from health_checks import TimestampSystemHealthCheck; TimestampSystemHealthCheck().run_all_checks()"

# Performance benchmark
python -c "from benchmarks import timestamp_performance_test; timestamp_performance_test()"

# Monitoring dashboard
curl http://monitoring.company.com/api/timestamp-metrics
```

---

## Common Issues and Solutions

### Issue 1: NotImplementedError - Missing Abstract Methods

#### Symptoms
```python
NotImplementedError: _get_entity_id not implemented
# or
NotImplementedError: _validate_entity not implemented
```

#### Root Cause
Entity class inherits from `BaseTimestampEntity` but doesn't implement required abstract methods.

#### Solution
```python
# ❌ BROKEN: Missing required methods
@dataclass
class Task(BaseTimestampEntity):
    title: str = ""

# ✅ FIXED: Implement both abstract methods
@dataclass
class Task(BaseTimestampEntity):
    id: str | None = None
    title: str = ""

    def _get_entity_id(self) -> str:
        return str(self.id) if self.id else "unknown"

    def _validate_entity(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty")
```

#### Prevention
- Use IDE with proper type checking
- Follow implementation template from training materials
- Run unit tests before deployment

---

### Issue 2: Domain Events Memory Leak

#### Symptoms
- Gradually increasing memory usage
- Application slowdown over time
- Out of memory errors in long-running processes

#### Root Cause
Domain events accumulating in entity memory without being processed and cleared.

#### Diagnosis
```python
# Check entity for accumulated events
def diagnose_entity_events(entity: BaseTimestampEntity) -> Dict[str, Any]:
    events = entity.get_domain_events()
    return {
        'entity_id': entity._get_entity_id(),
        'event_count': len(events),
        'event_types': [e.event_type for e in events],
        'memory_usage_estimate': len(events) * 200  # Rough bytes estimate
    }

# Usage
diagnosis = diagnose_entity_events(problematic_entity)
print(f"Entity has {diagnosis['event_count']} unprocessed events")
```

#### Solution
```python
# ❌ PROBLEMATIC: Events never cleared
class BadService:
    def process_tasks(self, task_ids: List[str]):
        for task_id in task_ids:
            task = self.repository.find_by_id(task_id)
            task.touch(reason="processing")
            # Events accumulate here!

# ✅ CORRECT: Proper event processing
class GoodService:
    def process_tasks(self, task_ids: List[str]):
        for task_id in task_ids:
            task = self.repository.find_by_id(task_id)
            task.touch(reason="processing")

            # Process events
            events = task.get_domain_events()
            for event in events:
                self.event_bus.publish(event)

            # Clear events
            task.clear_domain_events()
```

#### Prevention
- Always call `clear_domain_events()` after processing
- Use repository pattern which handles this automatically
- Monitor event accumulation in production

---

### Issue 3: Timezone Confusion in Production

#### Symptoms
- Incorrect timestamp comparisons
- Wrong time-based filtering results
- Inconsistent behavior across environments

#### Root Cause
Mixing timezone-naive and timezone-aware datetimes, or using non-UTC timezones.

#### Diagnosis
```python
def diagnose_timezone_issues(entity: BaseTimestampEntity) -> Dict[str, Any]:
    return {
        'entity_id': entity._get_entity_id(),
        'created_at_tz': str(entity.created_at.tzinfo) if entity.created_at else None,
        'updated_at_tz': str(entity.updated_at.tzinfo) if entity.updated_at else None,
        'is_utc_created': entity.created_at.tzinfo == timezone.utc if entity.created_at else False,
        'is_utc_updated': entity.updated_at.tzinfo == timezone.utc if entity.updated_at else False,
        'timestamps_match_utc': all([
            entity.created_at.tzinfo == timezone.utc if entity.created_at else True,
            entity.updated_at.tzinfo == timezone.utc if entity.updated_at else True
        ])
    }
```

#### Solution
```python
# ❌ PROBLEMATIC: Mixing timezone-naive with UTC
def find_recent_tasks(hours: int):
    cutoff = datetime.now() - timedelta(hours=hours)  # Naive datetime!
    return repository.find_updated_after(cutoff)  # Comparing with UTC timestamps

# ✅ CORRECT: Always use UTC
def find_recent_tasks(hours: int):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)  # UTC datetime
    return repository.find_updated_after(cutoff)

# ❌ PROBLEMATIC: External timezone-naive datetime
def import_external_data(external_timestamp: datetime):
    task.created_at = external_timestamp  # Could be any timezone!

# ✅ CORRECT: Ensure UTC conversion
def import_external_data(external_timestamp: datetime):
    task.created_at = BaseTimestampEntity._coerce_to_utc(external_timestamp)
```

#### Prevention
- Always use `datetime.now(timezone.utc)` for current time
- Convert external timestamps to UTC immediately
- Use static type checking to catch timezone mismatches

---

### Issue 4: Validation Errors in Production

#### Symptoms
```python
ValueError: Task title cannot be empty
ValueError: Invalid status: unknown_status
```

#### Root Cause
- Weak or missing validation rules
- Data integrity issues
- External data import problems

#### Diagnosis
```python
def diagnose_validation_issues(entity: BaseTimestampEntity) -> Dict[str, Any]:
    try:
        entity._validate_entity()
        return {'status': 'valid', 'entity_id': entity._get_entity_id()}
    except Exception as e:
        return {
            'status': 'invalid',
            'entity_id': entity._get_entity_id(),
            'error_type': type(e).__name__,
            'error_message': str(e),
            'entity_state': entity.__dict__
        }
```

#### Solution
```python
# ❌ WEAK: No validation
def _validate_entity(self) -> None:
    pass  # No rules enforced

# ✅ STRONG: Comprehensive validation
def _validate_entity(self) -> None:
    # Required field validation
    if not self.title or not self.title.strip():
        raise ValueError("Task title is required and cannot be empty")

    # Length constraints
    if len(self.title) > 200:
        raise ValueError(f"Task title too long: {len(self.title)}/200 characters")

    # Business rule validation
    if self.status not in ["todo", "in_progress", "done", "cancelled"]:
        raise ValueError(f"Invalid status: '{self.status}'. Must be one of: todo, in_progress, done, cancelled")

    # Cross-field validation
    if self.status == "done" and not self.assignee:
        raise ValueError("Completed tasks must have an assignee")
```

#### Prevention
- Implement comprehensive validation rules
- Add input sanitization for external data
- Use enum types for status fields
- Regular validation rule audits

---

### Issue 5: Performance Degradation

#### Symptoms
- Slow entity creation or updates
- High memory usage
- Database query timeouts

#### Root Cause
- N+1 query patterns
- Excessive touch() calls
- Memory leaks from uncleared events

#### Diagnosis
```python
import time
from contextlib import contextmanager

@contextmanager
def measure_performance():
    start_time = time.perf_counter()
    start_memory = get_memory_usage()
    yield
    end_time = time.perf_counter()
    end_memory = get_memory_usage()

    print(f"Duration: {(end_time - start_time) * 1000:.2f}ms")
    print(f"Memory delta: {end_memory - start_memory:.2f}MB")

# Usage
with measure_performance():
    task = Task(id="test", title="Performance Test")
    task.touch("performance_measurement")
```

#### Solution
```python
# ❌ INEFFICIENT: Multiple touch() calls
def update_task_details(task: Task, updates: Dict[str, Any]):
    for field, value in updates.items():
        setattr(task, field, value)
        task.touch(f"updated_{field}")  # Multiple timestamp updates!

# ✅ EFFICIENT: Single touch() for batch updates
def update_task_details(task: Task, updates: Dict[str, Any]):
    for field, value in updates.items():
        setattr(task, field, value)
    task.touch(f"bulk_update_{len(updates)}_fields")  # Single timestamp update

# ❌ INEFFICIENT: N+1 query pattern
def process_all_tasks():
    task_ids = repository.find_all_task_ids()
    for task_id in task_ids:
        task = repository.find_by_id(task_id)  # N queries
        task.touch("processing")
        repository.save(task)  # N saves

# ✅ EFFICIENT: Batch operations
def process_all_tasks():
    tasks = repository.find_all_tasks()  # 1 query
    all_events = []

    for task in tasks:
        task.touch("processing")
        all_events.extend(task.get_domain_events())
        task.clear_domain_events()

    repository.bulk_save(tasks)  # 1 save
    event_bus.publish_batch(all_events)  # Batch event processing
```

#### Prevention
- Use batch operations for bulk updates
- Minimize touch() calls through update batching
- Regular performance monitoring and profiling
- Implement query optimization techniques

---

## Advanced Debugging Techniques

### Debug Tool: Entity State Inspector

```python
class EntityStateInspector:
    @staticmethod
    def full_analysis(entity: BaseTimestampEntity) -> Dict[str, Any]:
        """Comprehensive entity state analysis for debugging."""
        events = entity.get_domain_events()

        return {
            'basic_info': {
                'entity_id': entity._get_entity_id(),
                'entity_type': entity.__class__.__name__,
                'created_at': entity.created_at.isoformat() if entity.created_at else None,
                'updated_at': entity.updated_at.isoformat() if entity.updated_at else None
            },
            'timestamp_analysis': {
                'age_seconds': entity.get_age_seconds(),
                'staleness_seconds': entity.get_staleness_seconds(),
                'is_newer_than_hour_ago': entity.updated_at > datetime.now(timezone.utc) - timedelta(hours=1) if entity.updated_at else False,
                'timezone_info': {
                    'created_tz': str(entity.created_at.tzinfo) if entity.created_at else None,
                    'updated_tz': str(entity.updated_at.tzinfo) if entity.updated_at else None,
                    'both_utc': all([
                        entity.created_at.tzinfo == timezone.utc if entity.created_at else True,
                        entity.updated_at.tzinfo == timezone.utc if entity.updated_at else True
                    ])
                }
            },
            'validation_status': EntityStateInspector._check_validation(entity),
            'event_analysis': {
                'total_events': len(events),
                'event_types': [e.event_type for e in events],
                'latest_event': events[-1].to_dict() if events else None,
                'memory_estimate_bytes': len(events) * 200
            },
            'performance_indicators': {
                'has_excessive_events': len(events) > 10,
                'is_stale': entity.get_staleness_seconds() > 3600 if entity.get_staleness_seconds() else False,
                'needs_attention': len(events) > 10 or (entity.get_staleness_seconds() or 0) > 3600
            }
        }

    @staticmethod
    def _check_validation(entity: BaseTimestampEntity) -> Dict[str, Any]:
        try:
            entity._validate_entity()
            return {'valid': True, 'error': None}
        except Exception as e:
            return {
                'valid': False,
                'error_type': type(e).__name__,
                'error_message': str(e)
            }

# Usage
analysis = EntityStateInspector.full_analysis(problematic_entity)
print(json.dumps(analysis, indent=2))
```

### Performance Profiler

```python
import cProfile
import pstats
from functools import wraps

def profile_timestamp_operations(func):
    """Decorator to profile timestamp-heavy operations."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()

            # Analysis
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats('timestamp', 20)  # Show top 20 timestamp-related calls

        return result
    return wrapper

# Usage
@profile_timestamp_operations
def bulk_task_processing():
    # Your timestamp-heavy operation here
    pass
```

### Event Flow Tracer

```python
class EventFlowTracer:
    def __init__(self):
        self.events = []

    def trace_entity_lifecycle(self, entity: BaseTimestampEntity) -> None:
        """Trace all events for an entity lifecycle."""
        original_add_event = entity._add_domain_event

        def traced_add_event(event):
            self.events.append({
                'timestamp': datetime.now(timezone.utc),
                'event_type': event.event_type,
                'entity_id': event.entity_id,
                'details': event.to_dict()
            })
            return original_add_event(event)

        entity._add_domain_event = traced_add_event

    def get_trace_report(self) -> Dict[str, Any]:
        return {
            'total_events': len(self.events),
            'event_timeline': self.events,
            'event_type_counts': {
                event_type: len([e for e in self.events if e['event_type'] == event_type])
                for event_type in set(e['event_type'] for e in self.events)
            }
        }

# Usage
tracer = EventFlowTracer()
task = Task(id="trace-test", title="Traced Task")
tracer.trace_entity_lifecycle(task)

# Perform operations
task.touch("operation1")
task.touch("operation2")

# Get trace report
report = tracer.get_trace_report()
print(json.dumps(report, indent=2))
```

---

## Production Monitoring and Alerting

### Critical Metrics to Monitor

```python
# Metrics collection for production monitoring
class TimestampMetrics:
    def __init__(self, metrics_client):
        self.metrics = metrics_client

    def track_entity_creation(self, entity_type: str, duration_ms: float):
        """Track entity creation performance."""
        self.metrics.histogram('timestamp.entity_creation_duration', duration_ms,
                              tags={'entity_type': entity_type})

        if duration_ms > 5:  # Alert threshold
            self.metrics.increment('timestamp.slow_creation',
                                  tags={'entity_type': entity_type})

    def track_validation_error(self, entity_type: str, error_type: str):
        """Track validation failures."""
        self.metrics.increment('timestamp.validation_error',
                              tags={'entity_type': entity_type, 'error_type': error_type})

    def track_event_accumulation(self, entity_id: str, event_count: int):
        """Track domain event accumulation."""
        self.metrics.gauge('timestamp.entity_event_count', event_count,
                          tags={'entity_id': entity_id})

        if event_count > 10:  # Memory leak indicator
            self.metrics.increment('timestamp.event_accumulation_warning',
                                  tags={'entity_id': entity_id})
```

### Health Check Endpoints

```python
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/health")

@router.get("/timestamp-system")
async def timestamp_system_health():
    """Comprehensive timestamp system health check."""
    try:
        health_checker = TimestampSystemHealthCheck()

        # Run all checks
        creation_check = health_checker.check_entity_creation_performance()
        event_check = health_checker.check_domain_event_processing()
        timezone_check = health_checker.check_timezone_consistency()

        overall_status = "healthy" if all([
            creation_check['status'] == 'healthy',
            event_check['status'] == 'healthy',
            timezone_check['status'] == 'healthy'
        ]) else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "entity_creation": creation_check,
                "domain_events": event_check,
                "timezone_handling": timezone_check
            }
        }

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")
```

### Alert Configuration

```yaml
# Example monitoring alert configuration
alerts:
  timestamp_slow_operations:
    condition: avg(timestamp_operation_duration) > 5ms over 5m
    severity: warning
    notification: dev-team-slack

  timestamp_validation_errors:
    condition: rate(timestamp_validation_error) > 10/min over 2m
    severity: critical
    notification: on-call-engineer

  domain_event_accumulation:
    condition: max(timestamp_entity_event_count) > 100
    severity: warning
    notification: performance-team

  timestamp_system_down:
    condition: up(timestamp_health_check) < 1
    severity: critical
    notification: incident-response-team
```

---

## Emergency Procedures

### Critical Production Issues

#### Issue: Complete Timestamp System Failure
**Symptoms**: All entity operations failing, timestamp health check returning 503

**Immediate Actions**:
1. Check system logs for error patterns
2. Verify database connectivity and performance
3. Check memory usage and potential leaks
4. Validate production configuration

**Recovery Steps**:
```bash
# 1. Check system resources
df -h  # Disk space
free -h  # Memory usage
top  # CPU and process status

# 2. Check application logs
tail -f /var/log/agenthub/timestamp-errors.log

# 3. Validate database connection
python -c "from database import test_connection; test_connection()"

# 4. Run emergency health check
python emergency_health_check.py

# 5. If needed, restart application services
sudo systemctl restart agenthub-api
```

#### Issue: Memory Leak from Event Accumulation
**Symptoms**: Gradually increasing memory usage, eventual OOM errors

**Emergency Response**:
```python
# Emergency event cleanup script
def emergency_event_cleanup():
    """Clear accumulated events from all entities."""
    from repository import get_all_repositories

    cleaned_count = 0
    for repo in get_all_repositories():
        entities = repo.find_all_with_events()
        for entity in entities:
            event_count = len(entity.get_domain_events())
            if event_count > 0:
                entity.clear_domain_events()
                repo.save(entity)
                cleaned_count += event_count

    print(f"Emergency cleanup: cleared {cleaned_count} accumulated events")

# Run emergency cleanup
emergency_event_cleanup()
```

### Escalation Procedures

#### Level 1: Development Team (Business Hours)
- Response time: 2 hours
- Contact: #clean-timestamp-support Slack channel
- Scope: Minor issues, questions, performance optimization

#### Level 2: Senior Engineers (24/7)
- Response time: 30 minutes
- Contact: On-call rotation
- Scope: Production performance degradation, validation errors

#### Level 3: Architecture Team (Emergency)
- Response time: 15 minutes
- Contact: Emergency escalation
- Scope: System-wide failures, critical architectural issues

---

## Frequently Asked Questions (FAQ)

### Q: Why do I get "NotImplementedError" when creating an entity?
**A**: Your entity class inherits from `BaseTimestampEntity` but doesn't implement the required abstract methods `_get_entity_id()` and `_validate_entity()`. See Issue 1 above for solution.

### Q: My application is using more memory over time. What's wrong?
**A**: Likely domain event accumulation. Events are created on entity operations but never processed and cleared. See Issue 2 above for diagnosis and solution.

### Q: Timestamp comparisons aren't working correctly across different environments.
**A**: You're probably mixing timezone-naive and timezone-aware datetimes. Always use UTC with `datetime.now(timezone.utc)`. See Issue 3 above.

### Q: How do I optimize performance for bulk operations?
**A**: Use batch updates with a single `touch()` call and batch event processing. Avoid N+1 query patterns. See Issue 5 above for examples.

### Q: Can I customize the timestamp update behavior?
**A**: The `touch()` method in `BaseTimestampEntity` provides the standard behavior. For special cases, you can override it, but ensure you maintain UTC consistency and domain event emission.

### Q: How do I handle timestamps for imported legacy data?
**A**: Use the `_coerce_to_utc()` static method to ensure proper timezone handling:
```python
task.created_at = BaseTimestampEntity._coerce_to_utc(legacy_timestamp)
```

### Q: What's the difference between created_at and updated_at?
**A**: `created_at` is set once when the entity is first created and never changes. `updated_at` is updated every time `touch()` is called. Both are automatically managed.

### Q: How do I test timestamp functionality?
**A**: Follow the testing patterns in the training materials. Key areas: automatic initialization, UTC enforcement, domain events, and validation rules.

---

## Additional Resources

### Documentation References
- [Developer Training Guide](/ai_docs/development-guides/clean-timestamp-developer-training.md)
- [Best Practices Document](/ai_docs/development-guides/clean-timestamp-best-practices.md)
- [Team Training Program](/ai_docs/development-guides/clean-timestamp-team-training-sessions.md)
- [Project Handover Document](/ai_docs/development-guides/clean-timestamp-project-handover.md)

### Code Examples Repository
```bash
# Access training examples and solutions
cd /path/to/timestamp-training
ls exercises/  # Hands-on exercises
ls solutions/  # Complete solutions
ls reference/  # BaseTimestampEntity source
```

### Support Channels
- **Slack**: #clean-timestamp-support
- **Documentation Wiki**: Internal knowledge base
- **Expert Office Hours**: Daily 2-4 PM for complex questions

---

*Troubleshooting Guide Version: 1.0 | Last Updated: 2025-09-25 | Next Review: 2025-12-25*