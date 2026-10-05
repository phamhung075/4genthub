package metrics

// WebSocket Metrics for Prometheus Monitoring
// (Python fastmcp/server/metrics/websocket_metrics.py).
//
// Prometheus metrics are kept as an in-process registry (no third-party
// prometheus client module is present in go.mod). The gauge/counter/histogram
// values and helper semantics match the Python module.

import (
	"strconv"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

var (
	wsMetricsMu sync.Mutex

	// Gauge websocket_connections, labels: active / authenticated / unauthenticated.
	wsConnectionGauge = map[string]float64{
		"active":          0,
		"authenticated":   0,
		"unauthenticated": 0,
	}

	// Gauge websocket_message_queue_size, label: user_id.
	wsMessageQueueSize = map[string]float64{}
	// Gauge websocket_message_queue_max_size, label: user_id.
	wsMessageQueueMaxSize = map[string]float64{}
	// Counter websocket_message_retries_total, labels: result, attempt.
	wsMessageRetriesTotal = map[string]float64{}
	// Histogram websocket_message_delivery_seconds, label: delivery_type.
	wsMessageDeliveryCount = map[string]float64{}
	wsMessageDeliverySum   = map[string]float64{}
	// Histogram websocket_broadcast_duration_seconds, labels: event_type, entity_type.
	wsBroadcastDurationCount = map[string]float64{}
	wsBroadcastDurationSum   = map[string]float64{}
)

// UpdateConnectionCount mirrors update_connection_count.
func UpdateConnectionCount(active, authenticated, unauthenticated int) {
	defer func() { _ = recover() }()
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()
	wsConnectionGauge["active"] = float64(active)
	wsConnectionGauge["authenticated"] = float64(authenticated)
	wsConnectionGauge["unauthenticated"] = float64(unauthenticated)
}

// UpdateQueueSize mirrors update_queue_size.
func UpdateQueueSize(userID string, size int) {
	defer func() { _ = recover() }()
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()
	wsMessageQueueSize[userID] = float64(size)
	if float64(size) > wsMessageQueueMaxSize[userID] {
		wsMessageQueueMaxSize[userID] = float64(size)
	}
}

// ClearQueueMetrics mirrors clear_queue_metrics.
func ClearQueueMetrics(userID string) {
	defer func() { _ = recover() }()
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()
	wsMessageQueueSize[userID] = 0
}

// RecordRetryAttempt mirrors record_retry_attempt.
func RecordRetryAttempt(success bool, attempt int) {
	defer func() { _ = recover() }()
	result := "failure"
	if success {
		result = "success"
	}
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()
	wsMessageRetriesTotal[result+"\x00"+strconv.Itoa(attempt)]++
}

// RecordDeliveryTime mirrors record_delivery_time.
func RecordDeliveryTime(deliveryType string, durationSeconds float64) {
	defer func() { _ = recover() }()
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()
	wsMessageDeliveryCount[deliveryType]++
	wsMessageDeliverySum[deliveryType] += durationSeconds
}

// TrackBroadcastDuration mirrors the track_broadcast_duration context manager:
// call the returned function when the broadcast finishes (typically `defer`).
func TrackBroadcastDuration(eventType, entityType string) func() {
	startTime := time.Now()
	return func() {
		defer func() { _ = recover() }()
		key := eventType + "\x00" + entityType
		wsMetricsMu.Lock()
		defer wsMetricsMu.Unlock()
		wsBroadcastDurationCount[key]++
		wsBroadcastDurationSum[key] += value_objects.PyTotalSeconds(time.Since(startTime))
	}
}

// GetMetricsSummary mirrors get_metrics_summary.
func GetMetricsSummary() (summary *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			summary = entities.NewOrderedMap[any]()
		}
	}()
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()

	totalRetries := 0.0
	for _, v := range wsMessageRetriesTotal {
		totalRetries += v
	}
	summary = entities.NewOrderedMap[any]()
	summary.Set("active_connections", wsConnectionGauge["active"])
	summary.Set("authenticated_connections", wsConnectionGauge["authenticated"])
	summary.Set("total_retries", totalRetries)
	return summary
}
