# WebSocket Metrics Monitoring Guide

**Date**: 2025-10-30
**Component**: WebSocket Message Queue System
**Metrics Format**: Prometheus

---

## Overview

Comprehensive Prometheus metrics for monitoring WebSocket message queue performance, connection health, and system reliability.

## Metrics Endpoint

**URL**: `/ws/metrics`
**Method**: GET
**Format**: Prometheus text format
**Authentication**: None (recommend restricting to internal network)

### Example Request

```bash
curl http://localhost:8000/ws/metrics
```

---

## Available Metrics

### 1. Connection Metrics

#### `websocket_connections`
**Type**: Gauge
**Description**: Number of active WebSocket connections
**Labels**:
- `status`: Connection status
  - `active`: Total active connections
  - `authenticated`: Authenticated connections
  - `unauthenticated`: Unauthenticated connections

**Example**:
```
websocket_connections{status="active"} 150
websocket_connections{status="authenticated"} 148
websocket_connections{status="unauthenticated"} 2
```

**Usage**:
- Monitor connection growth trends
- Alert on unusual spikes or drops
- Track authentication rates

---

### 2. Queue Size Metrics

#### `websocket_message_queue_size`
**Type**: Gauge
**Description**: Current number of queued messages per user
**Labels**:
- `user_id`: User identifier

**Example**:
```
websocket_message_queue_size{user_id="user-123"} 5
websocket_message_queue_size{user_id="user-456"} 0
```

**Usage**:
- Detect message backlog for specific users
- Identify users with connection issues
- Monitor queue buildup trends

#### `websocket_message_queue_max_size`
**Type**: Gauge
**Description**: Maximum queue size reached per user
**Labels**:
- `user_id`: User identifier

**Example**:
```
websocket_message_queue_max_size{user_id="user-123"} 15
```

**Usage**:
- Track peak queue sizes
- Identify capacity issues
- Set queue size limits

---

### 3. Retry Metrics

#### `websocket_message_retries_total`
**Type**: Counter
**Description**: Total number of message retry attempts
**Labels**:
- `result`: Retry outcome (`success` or `failure`)
- `attempt`: Retry attempt number (`1`, `2`, `3`)

**Example**:
```
websocket_message_retries_total{result="success",attempt="1"} 45
websocket_message_retries_total{result="success",attempt="2"} 12
websocket_message_retries_total{result="failure",attempt="3"} 3
```

**Usage**:
- Track retry success rates
- Identify persistent delivery failures
- Measure retry effectiveness

**Alerting Rules**:
```yaml
# High retry failure rate
- alert: HighRetryFailureRate
  expr: |
    rate(websocket_message_retries_total{result="failure"}[5m]) > 10
  annotations:
    summary: "High message retry failure rate"
```

---

### 4. Delivery Latency Metrics

#### `websocket_message_delivery_seconds`
**Type**: Histogram
**Description**: Message delivery time in seconds
**Labels**:
- `delivery_type`: Type of delivery
  - `immediate`: Message delivered on first attempt
  - `retry`: Message delivered after retry
  - `failed`: Message failed after all retries

**Example**:
```
websocket_message_delivery_seconds_bucket{delivery_type="immediate",le="0.1"} 1250
websocket_message_delivery_seconds_bucket{delivery_type="retry",le="5.0"} 45
websocket_message_delivery_seconds_sum{delivery_type="immediate"} 125.5
websocket_message_delivery_seconds_count{delivery_type="immediate"} 1250
```

**Usage**:
- Monitor delivery performance
- Track retry delays
- Identify slow delivery patterns

**Percentile Queries**:
```promql
# 95th percentile delivery time for immediate deliveries
histogram_quantile(0.95,
  rate(websocket_message_delivery_seconds_bucket{delivery_type="immediate"}[5m])
)

# Average retry delay
rate(websocket_message_delivery_seconds_sum{delivery_type="retry"}[5m]) /
rate(websocket_message_delivery_seconds_count{delivery_type="retry"}[5m])
```

---

### 5. Broadcast Duration Metrics

#### `websocket_broadcast_duration_seconds`
**Type**: Histogram
**Description**: Time spent broadcasting messages to all connections
**Labels**:
- `event_type`: Type of event (`created`, `updated`, `deleted`)
- `entity_type`: Type of entity (`task`, `project`, `branch`, etc.)

**Example**:
```
websocket_broadcast_duration_seconds_bucket{event_type="created",entity_type="task",le="0.5"} 890
websocket_broadcast_duration_seconds_sum{event_type="created",entity_type="task"} 125.3
websocket_broadcast_duration_seconds_count{event_type="created",entity_type="task"} 890
```

**Usage**:
- Monitor broadcast performance
- Identify slow event types
- Detect performance degradation

**Performance Queries**:
```promql
# Average broadcast time by entity type
rate(websocket_broadcast_duration_seconds_sum[5m]) /
rate(websocket_broadcast_duration_seconds_count[5m])

# 99th percentile broadcast time
histogram_quantile(0.99,
  rate(websocket_broadcast_duration_seconds_bucket[5m])
)
```

---

## Monitoring Dashboards

### Key Performance Indicators (KPIs)

1. **Connection Health**
   - Active connections trend
   - Connection churn rate
   - Authentication success rate

2. **Queue Performance**
   - Average queue size
   - Maximum queue size per user
   - Queue growth rate

3. **Delivery Reliability**
   - First-attempt success rate: `rate(websocket_message_retries_total{result="success",attempt="1"}[5m])`
   - Retry success rate: `rate(websocket_message_retries_total{result="success"}[5m])`
   - Message failure rate: `rate(websocket_message_retries_total{result="failure"}[5m])`

4. **Performance Metrics**
   - P50, P95, P99 delivery latency
   - Average broadcast duration
   - Messages per second

### Example Grafana Dashboard

```json
{
  "dashboard": {
    "title": "WebSocket Metrics",
    "panels": [
      {
        "title": "Active Connections",
        "targets": [{
          "expr": "websocket_connections{status=\"active\"}"
        }]
      },
      {
        "title": "Queue Size Distribution",
        "targets": [{
          "expr": "sum by (user_id) (websocket_message_queue_size)"
        }]
      },
      {
        "title": "Retry Success Rate",
        "targets": [{
          "expr": "rate(websocket_message_retries_total{result=\"success\"}[5m]) / rate(websocket_message_retries_total[5m])"
        }]
      }
    ]
  }
}
```

---

## Alerting Rules

### Critical Alerts

```yaml
groups:
  - name: websocket_alerts
    rules:
      # Connection Alerts
      - alert: WebSocketConnectionDrop
        expr: |
          rate(websocket_connections{status="active"}[5m]) < -10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Rapid WebSocket connection drop detected"

      # Queue Alerts
      - alert: MessageQueueBacklog
        expr: |
          websocket_message_queue_size > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High message queue backlog for user {{ $labels.user_id }}"

      # Retry Alerts
      - alert: HighMessageFailureRate
        expr: |
          rate(websocket_message_retries_total{result="failure"}[5m]) > 5
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "High message failure rate detected"

      # Performance Alerts
      - alert: SlowBroadcastPerformance
        expr: |
          histogram_quantile(0.95,
            rate(websocket_broadcast_duration_seconds_bucket[5m])
          ) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 broadcast duration exceeds 2 seconds"
```

---

## Troubleshooting Guide

### High Queue Size

**Symptom**: `websocket_message_queue_size` consistently high for users

**Possible Causes**:
1. User connection unstable/disconnected
2. Network latency issues
3. Client not processing messages fast enough

**Actions**:
1. Check user connection status
2. Review network logs
3. Check client-side message processing

### High Retry Failure Rate

**Symptom**: `websocket_message_retries_total{result="failure"}` increasing rapidly

**Possible Causes**:
1. Users frequently offline
2. WebSocket connection quality poor
3. Max retry limit too low

**Actions**:
1. Review retry configuration (RETRY_MAX_ATTEMPTS)
2. Check connection stability metrics
3. Investigate client connectivity patterns

### Slow Broadcast Performance

**Symptom**: `websocket_broadcast_duration_seconds` P95 > 1 second

**Possible Causes**:
1. Too many active connections
2. Large message payloads
3. Authorization checks slow

**Actions**:
1. Review connection count trends
2. Optimize message payload size
3. Profile authorization logic

---

## Performance Optimization

### Baseline Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| Active Connections | < 1000 | 2000 |
| Queue Size (per user) | < 10 | 50 |
| Retry Success Rate | > 95% | < 80% |
| P95 Delivery Latency | < 500ms | > 2s |
| P95 Broadcast Duration | < 1s | > 5s |

### Scaling Recommendations

**When connections > 1000**:
- Consider horizontal scaling (multiple instances)
- Implement connection load balancing
- Use Redis for cross-instance message coordination

**When queue sizes consistently high**:
- Increase retry frequency (reduce RETRY_QUEUE_CHECK_INTERVAL)
- Implement priority queues for critical messages
- Add queue size limits per user

---

## Integration Examples

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: 'websocket_metrics'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/ws/metrics'
```

### Python Client Example

```python
import requests

response = requests.get('http://localhost:8000/ws/metrics')
print(response.text)
```

### cURL Example

```bash
# Get all metrics
curl http://localhost:8000/ws/metrics

# Get specific metric
curl http://localhost:8000/ws/metrics | grep websocket_connections

# Monitor metrics continuously
watch -n 5 'curl -s http://localhost:8000/ws/metrics | grep websocket_connections'
```

---

## References

- **Prometheus Documentation**: https://prometheus.io/docs/
- **Metric Types**: https://prometheus.io/docs/concepts/metric_types/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/basics/
- **Grafana Dashboards**: https://grafana.com/docs/grafana/latest/dashboards/

---

**Last Updated**: 2025-10-30
**Maintained By**: Platform Engineering Team
