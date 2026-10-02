package interfaces

import "time"

// MetricType is the metric type enumeration.
type MetricType string

const (
	MetricTypeCounter   MetricType = "counter"
	MetricTypeGauge     MetricType = "gauge"
	MetricTypeHistogram MetricType = "histogram"
	MetricTypeTimer     MetricType = "timer"
)

// MetricTypeValues lists the metric types in declaration order.
var MetricTypeValues = []MetricType{MetricTypeCounter, MetricTypeGauge, MetricTypeHistogram, MetricTypeTimer}

// IMetric is a recorded metric (Python properties become methods).
type IMetric interface {
	Name() string
	Value() float64
	Timestamp() time.Time
	Labels() map[string]string
}

// IProcessMonitor monitors OS processes.
type IProcessMonitor interface {
	StartMonitoring(processName string) (string, error)
	StopMonitoring(monitorID string) (bool, error)
	GetProcessMetrics(processName string) (map[string]any, error)
	IsProcessRunning(processName string) (bool, error)
	GetResourceUsage(processName string) (map[string]float64, error)
}

// IMonitoringService records metrics and alerts.
type IMonitoringService interface {
	// RecordMetric records a metric (Python default type GAUGE, nil labels).
	RecordMetric(name string, value float64, metricType MetricType, labels map[string]string)
	IncrementCounter(name string, labels map[string]string)
	RecordTimer(name string, duration time.Duration, labels map[string]string)
	// GetMetrics returns metrics whose name matches the pattern (nil = all).
	GetMetrics(namePattern *string) []IMetric
	GetHealthStatus() map[string]any
	CreateAlert(name, condition string, threshold float64) string
	RemoveAlert(alertID string) bool
}
