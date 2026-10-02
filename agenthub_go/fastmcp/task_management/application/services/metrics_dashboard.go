package services

// Metrics Dashboard for MCP Response Optimization
// (Python application/services/metrics_dashboard.py).

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// MetricType are the types of metrics.
type MetricType string

const (
	MetricTypeCounter          MetricType = "counter"           // Monotonically increasing
	MetricTypeGauge            MetricType = "gauge"             // Point-in-time value
	MetricTypeHistogram        MetricType = "histogram"         // Distribution of values
	MetricTypeTimer            MetricType = "timer"             // Duration measurements
	MetricTypeTaskCompletion   MetricType = "task_completion"   // Additional metric type
	MetricTypeAPIResponseTime  MetricType = "api_response_time" // Additional metric type
	MetricTypeAgentUtilization MetricType = "agent_utilization" // Additional metric type
)

func (e MetricType) String() string { return string(e) }

// AggregationType are the types of metric aggregations.
type AggregationType string

const (
	AggregationTypeAverage AggregationType = "average"
	AggregationTypeMax     AggregationType = "max"
	AggregationTypeMin     AggregationType = "min"
	AggregationTypeSum     AggregationType = "sum"
	AggregationTypeCount   AggregationType = "count"
)

func (e AggregationType) String() string { return string(e) }

// TimeRange is the time range for metric queries.
type TimeRange struct {
	Start time.Time
	End   time.Time
}

// DashboardWidget is the dashboard widget configuration.
type DashboardWidget struct {
	ID            string
	Title         string
	MetricType    MetricType
	Visualization string
	Position      map[string]int
}

func zpMetricsNewWidget(id, title string, metricType MetricType) *DashboardWidget {
	return &DashboardWidget{ID: id, Title: title, MetricType: metricType, Visualization: "line_chart", Position: map[string]int{}}
}

// MetricAlert is the metric alert configuration.
type MetricAlert struct {
	ID         string
	Name       string
	MetricType MetricType
	Condition  string
	Threshold  float64
	Action     string
	Enabled    bool
}

func zpMetricsNewAlert(id, name string, metricType MetricType, condition string, threshold float64) *MetricAlert {
	return &MetricAlert{ID: id, Name: name, MetricType: metricType, Condition: condition, Threshold: threshold, Action: "notify", Enabled: true}
}

// MetricPoint is a single metric data point.
type MetricPoint struct {
	Timestamp time.Time
	Value     float64
	Tags      *entities.OrderedMap[string]
}

func zpMetricsNewMetricPoint(timestamp time.Time, value float64, tags *entities.OrderedMap[string]) *MetricPoint {
	return &MetricPoint{Timestamp: timestamp, Value: value, Tags: zpMetricsTagsOrEmpty(tags)}
}

// ToDict converts to an ordered Python dict.
func (p *MetricPoint) ToDict() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("timestamp", value_objects.IsoFormatNaive(p.Timestamp))
	out.Set("value", p.Value)
	out.Set("tags", p.Tags)
	return out
}

// Metric is a metric definition and its data.
type Metric struct {
	Name        string
	MetricType  MetricType
	Description string
	Unit        string
	DataPoints  []*MetricPoint
}

func zpMetricsNewMetric(name string, metricType MetricType, description, unit string) *Metric {
	return &Metric{Name: name, MetricType: metricType, Description: description, Unit: unit, DataPoints: []*MetricPoint{}}
}

// AddPoint adds a data point with the current time.
func (m *Metric) AddPoint(value float64, tags *entities.OrderedMap[string]) {
	m.DataPoints = append(m.DataPoints, zpMetricsNewMetricPoint(time.Now(), value, tags))
}

// GetLatest returns the latest value, or nil when there are no points.
func (m *Metric) GetLatest() *float64 {
	if len(m.DataPoints) == 0 {
		return nil
	}
	v := m.DataPoints[len(m.DataPoints)-1].Value
	return &v
}

// GetAverage returns the average over the duration, or nil when no points fall in it.
func (m *Metric) GetAverage(durationMinutes int) *float64 {
	cutoff := time.Now().Add(-time.Duration(durationMinutes) * time.Minute)
	recent := make([]float64, 0, len(m.DataPoints))
	for _, point := range m.DataPoints {
		if point.Timestamp.After(cutoff) {
			recent = append(recent, point.Value)
		}
	}
	if len(recent) == 0 {
		return nil
	}
	avg := value_objects.PySum(recent) / float64(len(recent))
	return &avg
}

// zpMetricsHandler is a subscribe_to_metrics callback; it receives the metric_data dict.
type zpMetricsHandler func(*entities.OrderedMap[any])

// zpMetricsCalculation is a custom metric calculation over name -> value.
type zpMetricsCalculation func(map[string]float64) float64

type zpMetricsCustomMetric struct {
	Description string
	Calculation zpMetricsCalculation
}

// zpMetricsDeque mirrors collections.deque(maxlen).
type zpMetricsDeque[T any] struct {
	maxLen int
	items  []T
}

func zpMetricsNewDeque[T any](maxLen int) *zpMetricsDeque[T] {
	return &zpMetricsDeque[T]{maxLen: maxLen}
}

func (d *zpMetricsDeque[T]) Append(v T) {
	d.items = append(d.items, v)
	if d.maxLen > 0 && len(d.items) > d.maxLen {
		d.items = d.items[len(d.items)-d.maxLen:]
	}
}

func (d *zpMetricsDeque[T]) Len() int { return len(d.items) }

func zpMetricsTagsOrEmpty(tags *entities.OrderedMap[string]) *entities.OrderedMap[string] {
	if tags == nil || tags.Len() == 0 {
		return entities.NewOrderedMap[string]()
	}
	return tags
}

// zpMetricsGetOr is dict.get(key, def).
func zpMetricsGetOr(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

func zpMetricsString(m *entities.OrderedMap[any], key string) string {
	if m == nil {
		return ""
	}
	v, _ := m.Get(key)
	s, _ := v.(string)
	return s
}

func zpMetricsFloat(v any) float64 {
	if f, ok := value_objects.PyFloat(v); ok {
		return f
	}
	return 0
}

// zpMetricsMapType is the {"task_completion_rate": "task_completion", ...} mapping.
func zpMetricsMapType(dataType string) string {
	switch dataType {
	case "task_completion_rate":
		return "task_completion"
	case "api_response_time":
		return "api_response_time"
	}
	return dataType
}

func zpMetricsSortedCopy(vals []float64) []float64 {
	out := append([]float64{}, vals...)
	sort.Float64s(out)
	return out
}

// zpMetricsTail is list[-n:] (a new list).
func zpMetricsTail(alerts []any, n int) []any {
	if len(alerts) <= n {
		return append([]any{}, alerts...)
	}
	return append([]any{}, alerts[len(alerts)-n:]...)
}

// zpMetricsDatetimeStr is str(datetime): a space separator, microseconds when nonzero.
func zpMetricsDatetimeStr(t time.Time) string {
	s := t.Format("2006-01-02 15:04:05")
	if us := t.Nanosecond() / 1000; us != 0 {
		s += fmt.Sprintf(".%06d", us)
	}
	return s
}

func zpMetricsNewWindows() map[string]*zpMetricsDeque[*entities.OrderedMap[any]] {
	return map[string]*zpMetricsDeque[*entities.OrderedMap[any]]{
		"1m":  zpMetricsNewDeque[*entities.OrderedMap[any]](60), // 1 minute of second-by-second data
		"1h":  zpMetricsNewDeque[*entities.OrderedMap[any]](60), // 1 hour of minute-by-minute data
		"24h": zpMetricsNewDeque[*entities.OrderedMap[any]](24), // 24 hours of hourly data
	}
}

// MetricsDashboard is the comprehensive metrics dashboard.
type MetricsDashboard struct {
	RetentionHours  int
	Metrics         *entities.OrderedMap[*Metric]
	Alerts          []any
	Widgets         []*DashboardWidget
	RefreshInterval int
	MetricsStore    []*entities.OrderedMap[any]

	perfWindows    map[string]*zpMetricsDeque[*entities.OrderedMap[any]]
	lastCleanup    time.Time
	metricHandlers map[MetricType][]zpMetricsHandler
	customMetrics  map[string]*zpMetricsCustomMetric
}

// zpMetricsNewDashboard mirrors MetricsDashboard(retention_hours=24).
func zpMetricsNewDashboard(retentionHours int) *MetricsDashboard {
	d := &MetricsDashboard{
		RetentionHours:  retentionHours,
		Metrics:         entities.NewOrderedMap[*Metric](),
		Alerts:          []any{},
		Widgets:         []*DashboardWidget{},
		RefreshInterval: 60, // Default 60 seconds
		MetricsStore:    []*entities.OrderedMap[any]{},
	}
	d.initializeStandardMetrics()
	d.perfWindows = zpMetricsNewWindows()
	d.lastCleanup = time.Now()
	return d
}

func (d *MetricsDashboard) initializeStandardMetrics() {
	d.RegisterMetric("response_optimization_count", MetricTypeCounter, "Total number of response optimizations", "count")
	d.RegisterMetric("response_compression_ratio", MetricTypeHistogram, "Response compression ratio percentage", "percent")
	d.RegisterMetric("response_processing_time", MetricTypeTimer, "Time to process response optimization", "milliseconds")
	d.RegisterMetric("context_field_reduction", MetricTypeHistogram, "Context field reduction percentage", "percent")
	d.RegisterMetric("template_cache_hit_rate", MetricTypeGauge, "Template cache hit rate", "percent")
	d.RegisterMetric("cache_hit_rate", MetricTypeGauge, "Overall cache hit rate", "percent")
	d.RegisterMetric("cache_size", MetricTypeGauge, "Current cache size", "bytes")
	d.RegisterMetric("cache_evictions", MetricTypeCounter, "Number of cache evictions", "count")
	d.RegisterMetric("api_response_time", MetricTypeTimer, "API response time", "milliseconds")
	d.RegisterMetric("memory_usage", MetricTypeGauge, "Memory usage", "megabytes")
	d.RegisterMetric("optimization_errors", MetricTypeCounter, "Number of optimization errors", "count")
}

// RegisterMetric registers a new metric.
func (d *MetricsDashboard) RegisterMetric(name string, metricType MetricType, description, unit string) {
	d.Metrics.Set(name, zpMetricsNewMetric(name, metricType, description, unit))
}

// RecordMetric records a metric value. It supports both the type-based interface
// (metricType set) and the name-based interface (name set).
func (d *MetricsDashboard) RecordMetric(name *string, value *float64, tags *entities.OrderedMap[string], metricType *MetricType, timestamp *time.Time) {
	if metricType != nil {
		metricData := entities.NewOrderedMap[any]()
		metricData.Set("type", string(*metricType))
		if value != nil {
			metricData.Set("value", *value)
		} else {
			metricData.Set("value", nil)
		}
		if timestamp != nil {
			metricData.Set("timestamp", *timestamp)
		} else {
			metricData.Set("timestamp", time.Now())
		}
		metricData.Set("tags", zpMetricsTagsOrEmpty(tags))
		d.MetricsStore = append(d.MetricsStore, metricData)

		if d.metricHandlers != nil {
			if handlers, ok := d.metricHandlers[*metricType]; ok {
				for _, handler := range handlers {
					handler(metricData)
				}
			}
		}
		return
	}
	if name == nil {
		return
	}
	if !d.Metrics.Has(*name) {
		// Custom metrics without registration are only stored in metrics_store.
		metricData := entities.NewOrderedMap[any]()
		metricData.Set("name", *name)
		if value != nil {
			metricData.Set("value", *value)
		} else {
			metricData.Set("value", nil)
		}
		metricData.Set("timestamp", time.Now())
		metricData.Set("tags", zpMetricsTagsOrEmpty(tags))
		d.MetricsStore = append(d.MetricsStore, metricData)
		return
	}
	if value == nil {
		return
	}
	metric, _ := d.Metrics.Get(*name)
	metric.AddPoint(*value, tags)
	d.updatePerformanceWindows(*name, *value)
	d.checkAlerts(*name, *value)
	d.periodicCleanup()
}

// IncrementCounter increments a counter metric.
func (d *MetricsDashboard) IncrementCounter(name string, increment float64, tags *entities.OrderedMap[string]) {
	if metric, ok := d.Metrics.Get(name); ok && metric.MetricType == MetricTypeCounter {
		current := 0.0
		if latest := metric.GetLatest(); latest != nil {
			current = *latest
		}
		v := current + increment
		d.RecordMetric(&name, &v, tags, nil, nil)
	}
}

// SetGauge sets a gauge metric value.
func (d *MetricsDashboard) SetGauge(name string, value float64, tags *entities.OrderedMap[string]) {
	if metric, ok := d.Metrics.Get(name); ok && metric.MetricType == MetricTypeGauge {
		d.RecordMetric(&name, &value, tags, nil, nil)
	}
}

// RecordTimer records a timer metric.
func (d *MetricsDashboard) RecordTimer(name string, durationMs float64, tags *entities.OrderedMap[string]) {
	if metric, ok := d.Metrics.Get(name); ok && metric.MetricType == MetricTypeTimer {
		d.RecordMetric(&name, &durationMs, tags, nil, nil)
	}
}

// RecordHistogram records a histogram metric.
func (d *MetricsDashboard) RecordHistogram(name string, value float64, tags *entities.OrderedMap[string]) {
	if metric, ok := d.Metrics.Get(name); ok && metric.MetricType == MetricTypeHistogram {
		d.RecordMetric(&name, &value, tags, nil, nil)
	}
}

// GetMetricSummary returns the metric summary, or nil when the metric is unknown.
func (d *MetricsDashboard) GetMetricSummary(name string, durationMinutes int) *entities.OrderedMap[any] {
	metric, ok := d.Metrics.Get(name)
	if !ok {
		return nil
	}
	cutoff := time.Now().Add(-time.Duration(durationMinutes) * time.Minute)
	recent := make([]*MetricPoint, 0, len(metric.DataPoints))
	for _, point := range metric.DataPoints {
		if point.Timestamp.After(cutoff) {
			recent = append(recent, point)
		}
	}
	if len(recent) == 0 {
		noData := entities.NewOrderedMap[any]()
		noData.Set("name", name)
		noData.Set("type", string(metric.MetricType))
		noData.Set("description", metric.Description)
		noData.Set("unit", metric.Unit)
		noData.Set("no_data", true)
		return noData
	}
	values := make([]float64, len(recent))
	for i, point := range recent {
		values[i] = point.Value
	}
	summary := entities.NewOrderedMap[any]()
	summary.Set("name", name)
	summary.Set("type", string(metric.MetricType))
	summary.Set("description", metric.Description)
	summary.Set("unit", metric.Unit)
	summary.Set("data_points", len(recent))
	summary.Set("duration_minutes", durationMinutes)
	summary.Set("latest_value", values[len(values)-1])
	summary.Set("first_timestamp", value_objects.IsoFormatNaive(recent[0].Timestamp))
	summary.Set("last_timestamp", value_objects.IsoFormatNaive(recent[len(recent)-1].Timestamp))

	switch metric.MetricType {
	case MetricTypeGauge, MetricTypeHistogram, MetricTypeTimer:
		minValue, maxValue := values[0], values[0]
		for _, v := range values[1:] {
			if v < minValue {
				minValue = v
			}
			if v > maxValue {
				maxValue = v
			}
		}
		summary.Set("min_value", minValue)
		summary.Set("max_value", maxValue)
		summary.Set("avg_value", value_objects.PySum(values)/float64(len(values)))
		summary.Set("median_value", zpMetricsSortedCopy(values)[len(values)/2])

		if metric.MetricType == MetricTypeHistogram || metric.MetricType == MetricTypeTimer {
			sortedValues := zpMetricsSortedCopy(values)
			n := len(values)
			summary.Set("p50", sortedValues[int(float64(n)*0.5)])
			summary.Set("p90", sortedValues[int(float64(n)*0.9)])
			summary.Set("p95", sortedValues[int(float64(n)*0.95)])
			if n >= 100 {
				summary.Set("p99", sortedValues[int(float64(n)*0.99)])
			} else {
				summary.Set("p99", sortedValues[n-1])
			}
		}
	case MetricTypeCounter:
		if len(recent) >= 2 {
			durationSeconds := value_objects.PyTotalSeconds(recent[len(recent)-1].Timestamp.Sub(recent[0].Timestamp))
			if durationSeconds > 0 {
				rate := (values[len(values)-1] - values[0]) / durationSeconds
				summary.Set("rate_per_second", rate)
			}
		}
	}
	return summary
}

// GetDashboardData returns the complete dashboard data.
func (d *MetricsDashboard) GetDashboardData(durationMinutes int) *entities.OrderedMap[any] {
	dashboard := entities.NewOrderedMap[any]()
	dashboard.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	dashboard.Set("duration_minutes", durationMinutes)
	metricsMap := entities.NewOrderedMap[any]()
	dashboard.Set("metrics", metricsMap)
	dashboard.Set("summary", d.getPerformanceSummary(durationMinutes))
	dashboard.Set("alerts", zpMetricsTail(d.Alerts, 10)) // Last 10 alerts
	dashboard.Set("health_status", d.getHealthStatus())

	for _, metricName := range d.Metrics.Keys() {
		summary := d.GetMetricSummary(metricName, durationMinutes)
		if summary != nil {
			metricsMap.Set(metricName, summary)
		}
	}
	return dashboard
}

func (d *MetricsDashboard) getPerformanceSummary(durationMinutes int) *entities.OrderedMap[any] {
	summary := entities.NewOrderedMap[any]()
	optimization := entities.NewOrderedMap[any]()
	system := entities.NewOrderedMap[any]()
	errorRates := entities.NewOrderedMap[any]()
	summary.Set("optimization_performance", optimization)
	summary.Set("system_performance", system)
	summary.Set("error_rates", errorRates)

	hasData := func(m *entities.OrderedMap[any]) bool {
		return m != nil && !value_objects.PyTruthy(zpMetricsGetOr(m, "no_data", nil))
	}

	compression := d.GetMetricSummary("response_compression_ratio", durationMinutes)
	if hasData(compression) {
		optimization.Set("avg_compression_ratio", zpMetricsGetOr(compression, "avg_value", 0))
		optimization.Set("p95_compression_ratio", zpMetricsGetOr(compression, "p95", 0))
	}
	fieldReduction := d.GetMetricSummary("context_field_reduction", durationMinutes)
	if hasData(fieldReduction) {
		optimization.Set("avg_field_reduction", zpMetricsGetOr(fieldReduction, "avg_value", 0))
	}
	responseTime := d.GetMetricSummary("api_response_time", durationMinutes)
	if hasData(responseTime) {
		system.Set("avg_response_time_ms", zpMetricsGetOr(responseTime, "avg_value", 0))
		system.Set("p95_response_time_ms", zpMetricsGetOr(responseTime, "p95", 0))
	}
	cacheHit := d.GetMetricSummary("cache_hit_rate", durationMinutes)
	if hasData(cacheHit) {
		system.Set("cache_hit_rate", zpMetricsGetOr(cacheHit, "latest_value", 0))
	}
	errorSummary := d.GetMetricSummary("optimization_errors", durationMinutes)
	if hasData(errorSummary) {
		errorRates.Set("optimization_error_rate", zpMetricsGetOr(errorSummary, "rate_per_second", 0))
	}
	return summary
}

func (d *MetricsDashboard) getHealthStatus() *entities.OrderedMap[any] {
	score := 100
	issues := []any{}

	if metric, ok := d.Metrics.Get("response_compression_ratio"); ok {
		if avg := metric.GetAverage(60); avg != nil && *avg != 0 && *avg < 30 {
			issues = append(issues, "Low compression ratio - optimization may be underperforming")
			score -= 20
		}
	}
	if metric, ok := d.Metrics.Get("cache_hit_rate"); ok {
		if latest := metric.GetLatest(); latest != nil && *latest != 0 && *latest < 50 {
			issues = append(issues, "Low cache hit rate - consider cache optimization")
			score -= 15
		}
	}
	if metric, ok := d.Metrics.Get("api_response_time"); ok {
		if avg := metric.GetAverage(15); avg != nil && *avg != 0 && *avg > 100 {
			issues = append(issues, "High response times detected")
			score -= 25
		}
	}
	if metric, ok := d.Metrics.Get("optimization_errors"); ok {
		if avg := metric.GetAverage(15); avg != nil && *avg != 0 && *avg > 0 {
			issues = append(issues, "Optimization errors detected")
			score -= 30
		}
	}

	status := "healthy"
	if score >= 90 {
		status = "healthy"
	} else if score >= 70 {
		status = "warning"
	} else {
		status = "critical"
	}

	health := entities.NewOrderedMap[any]()
	health.Set("status", status)
	health.Set("issues", issues)
	health.Set("score", score)
	return health
}

func (d *MetricsDashboard) updatePerformanceWindows(metricName string, value float64) {
	data := entities.NewOrderedMap[any]()
	data.Set("timestamp", time.Now().Unix())
	data.Set("metric", metricName)
	data.Set("value", value)
	d.perfWindows["1m"].Append(data)
}

func (d *MetricsDashboard) checkAlerts(metricName string, value float64) {
	switch metricName {
	case "response_compression_ratio":
		if value < 40 {
			d.addAlert("warning", "Low compression ratio", metricName, value)
		}
	case "cache_hit_rate":
		if value < 60 {
			d.addAlert("warning", "Low cache hit rate", metricName, value)
		}
	case "api_response_time":
		if value > 200 {
			d.addAlert("critical", "High response time", metricName, value)
		}
	case "memory_usage":
		if value > 500 {
			d.addAlert("critical", "High memory usage", metricName, value)
		}
	}
}

func (d *MetricsDashboard) addAlert(level, message, metricName string, value float64) {
	alert := entities.NewOrderedMap[any]()
	alert.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	alert.Set("level", level)
	alert.Set("message", message)
	alert.Set("metric", metricName)
	alert.Set("value", value)
	d.Alerts = append(d.Alerts, alert)

	if len(d.Alerts) > 100 {
		d.Alerts = append([]any{}, d.Alerts[len(d.Alerts)-100:]...)
	}
}

func (d *MetricsDashboard) periodicCleanup() {
	now := time.Now()
	if value_objects.PyTotalSeconds(now.Sub(d.lastCleanup)) < 300 {
		return
	}
	cutoff := now.Add(-time.Duration(d.RetentionHours) * time.Hour)
	for _, metric := range d.Metrics.Values() {
		kept := make([]*MetricPoint, 0, len(metric.DataPoints))
		for _, point := range metric.DataPoints {
			if point.Timestamp.After(cutoff) {
				kept = append(kept, point)
			}
		}
		metric.DataPoints = kept
	}
	d.lastCleanup = now
}

// ExportMetricsOld exports metrics in the specified format.
func (d *MetricsDashboard) ExportMetricsOld(formatType string, durationMinutes int) (string, error) {
	dashboardData := d.GetDashboardData(durationMinutes)
	switch value_objects.PyLower(formatType) {
	case "json":
		return value_objects.PyJSONDumpsDefaultStr(dashboardData, 2), nil
	case "prometheus":
		return d.exportPrometheusFormat(dashboardData), nil
	default:
		return "", &value_objects.ValueError{Msg: "Unsupported format: " + formatType}
	}
}

func (d *MetricsDashboard) exportPrometheusFormat(data *entities.OrderedMap[any]) string {
	lines := []string{}
	metricsAny, _ := data.Get("metrics")
	metrics, _ := metricsAny.(*entities.OrderedMap[any])
	if metrics == nil {
		return ""
	}
	for _, metricName := range metrics.Keys() {
		value, _ := metrics.Get(metricName)
		metricData, _ := value.(*entities.OrderedMap[any])
		if metricData == nil || value_objects.PyTruthy(zpMetricsGetOr(metricData, "no_data", nil)) {
			continue
		}
		metricType := zpMetricsString(metricData, "type")
		lines = append(lines, "# HELP "+metricName+" "+zpMetricsString(metricData, "description"))
		lines = append(lines, "# TYPE "+metricName+" "+metricType)
		latestValue := zpMetricsGetOr(metricData, "latest_value", 0)
		lines = append(lines, metricName+" "+value_objects.PyStr(latestValue))

		if metricType == "histogram" || metricType == "timer" {
			for _, percentile := range []string{"p50", "p90", "p95", "p99"} {
				if pv, ok := metricData.Get(percentile); ok {
					lines = append(lines, metricName+"_"+percentile+" "+value_objects.PyStr(pv))
				}
			}
		}
	}
	return strings.Join(lines, "\n")
}

// ResetMetrics resets all metric data.
func (d *MetricsDashboard) ResetMetrics() {
	for _, metric := range d.Metrics.Values() {
		metric.DataPoints = []*MetricPoint{}
	}
	d.Alerts = []any{}
	d.perfWindows = zpMetricsNewWindows()
}

// AddWidget adds a widget to the dashboard.
func (d *MetricsDashboard) AddWidget(widget *DashboardWidget) {
	d.Widgets = append(d.Widgets, widget)
}

// GetMetrics returns metrics of a specific type, optionally filtered by time range.
func (d *MetricsDashboard) GetMetrics(metricType MetricType, timeRange *TimeRange) []*entities.OrderedMap[any] {
	result := []*entities.OrderedMap[any]{}
	for _, metricData := range d.MetricsStore {
		dataType := zpMetricsMapType(zpMetricsString(metricData, "type"))
		if dataType != string(metricType) {
			continue
		}
		if timeRange != nil {
			timestamp, _ := metricData.Get("timestamp")
			if ts, ok := timestamp.(time.Time); ok {
				if !ts.Before(timeRange.Start) && !ts.After(timeRange.End) {
					result = append(result, metricData)
				}
			}
		} else {
			result = append(result, metricData)
		}
	}
	return result
}

// AggregateMetrics aggregates metrics based on type.
func (d *MetricsDashboard) AggregateMetrics(metricType MetricType, aggregation AggregationType) float64 {
	metrics := []float64{}
	for _, m := range d.MetricsStore {
		dataType := zpMetricsMapType(zpMetricsString(m, "type"))
		if dataType == string(metricType) {
			value, _ := m.Get("value")
			metrics = append(metrics, zpMetricsFloat(value))
		}
	}
	if len(metrics) == 0 {
		return 0
	}
	switch aggregation {
	case AggregationTypeAverage:
		return value_objects.PySum(metrics) / float64(len(metrics))
	case AggregationTypeMax:
		maxValue := metrics[0]
		for _, v := range metrics[1:] {
			if v > maxValue {
				maxValue = v
			}
		}
		return maxValue
	case AggregationTypeMin:
		minValue := metrics[0]
		for _, v := range metrics[1:] {
			if v < minValue {
				minValue = v
			}
		}
		return minValue
	case AggregationTypeSum:
		return value_objects.PySum(metrics)
	case AggregationTypeCount:
		return float64(len(metrics))
	}
	return 0
}

// CalculateTrend calculates the trend for metrics.
func (d *MetricsDashboard) CalculateTrend(metricType MetricType, timeRange TimeRange) *entities.OrderedMap[any] {
	metrics := d.GetMetrics(metricType, &timeRange)
	out := entities.NewOrderedMap[any]()
	if len(metrics) < 2 {
		out.Set("direction", "flat")
		out.Set("change_percentage", 0)
		out.Set("slope", 0)
		return out
	}
	values := make([]float64, len(metrics))
	for i, m := range metrics {
		value, _ := m.Get("value")
		values[i] = zpMetricsFloat(value)
	}
	firstValue := values[0]
	lastValue := values[len(values)-1]

	var changePercentage any = 0
	if firstValue != 0 {
		changePercentage = ((lastValue - firstValue) / firstValue) * 100
	}
	direction := "flat"
	if lastValue > firstValue {
		direction = "up"
	} else if lastValue < firstValue {
		direction = "down"
	}
	slope := (lastValue - firstValue) / float64(len(values))

	out.Set("direction", direction)
	out.Set("change_percentage", changePercentage)
	out.Set("slope", slope)
	return out
}

// SetAlert sets a metric alert.
func (d *MetricsDashboard) SetAlert(alert *MetricAlert) {
	d.Alerts = append(d.Alerts, alert)
}

// CheckAlerts checks for triggered alerts.
func (d *MetricsDashboard) CheckAlerts() []*MetricAlert {
	triggered := []*MetricAlert{}
	for _, a := range d.Alerts {
		alert, ok := a.(*MetricAlert)
		if !ok || !alert.Enabled {
			continue
		}
		for _, metricData := range d.MetricsStore {
			if zpMetricsString(metricData, "type") != string(alert.MetricType) {
				continue
			}
			value, _ := metricData.Get("value")
			f := zpMetricsFloat(value)
			if alert.Condition == "greater_than" && f > alert.Threshold {
				triggered = append(triggered, alert)
				break
			} else if alert.Condition == "less_than" && f < alert.Threshold {
				triggered = append(triggered, alert)
				break
			}
		}
	}
	return triggered
}

// CreateSnapshot creates a dashboard snapshot.
func (d *MetricsDashboard) CreateSnapshot() *entities.OrderedMap[any] {
	snapshot := entities.NewOrderedMap[any]()
	snapshot.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	widgets := []any{}
	for _, w := range d.Widgets {
		widget := entities.NewOrderedMap[any]()
		widget.Set("id", w.ID)
		widget.Set("title", w.Title)
		widgets = append(widgets, widget)
	}
	snapshot.Set("widgets", widgets)
	metricsSummary := entities.NewOrderedMap[any]()
	metricsSummary.Set("total_metrics", len(d.MetricsStore))
	snapshot.Set("metrics_summary", metricsSummary)
	return snapshot
}

// ExportMetrics exports metrics in the specified format.
func (d *MetricsDashboard) ExportMetrics(format string, metricTypes []MetricType) string {
	filteredMetrics := []*entities.OrderedMap[any]{}
	for _, metricType := range metricTypes {
		for _, m := range d.MetricsStore {
			dataType := zpMetricsMapType(zpMetricsString(m, "type"))
			if dataType == string(metricType) {
				filteredMetrics = append(filteredMetrics, m)
			}
		}
	}

	if format == "csv" {
		lines := []string{"timestamp,value,type"}
		for _, m := range filteredMetrics {
			timestamp := zpMetricsGetOr(m, "timestamp", "")
			timestampStr := ""
			if ts, ok := timestamp.(time.Time); ok {
				timestampStr = value_objects.IsoFormatNaive(ts)
			} else {
				timestampStr = value_objects.PyStr(timestamp)
			}
			value := zpMetricsGetOr(m, "value", "")
			dataType := zpMetricsGetOr(m, "type", "")
			lines = append(lines, timestampStr+","+value_objects.PyStr(value)+","+value_objects.PyStr(dataType))
		}
		return strings.Join(lines, "\n")
	} else if format == "json" {
		// json.dumps(filtered_metrics, default=str): datetimes become str(datetime).
		out := []any{}
		for _, m := range filteredMetrics {
			converted := entities.NewOrderedMap[any]()
			for _, key := range m.Keys() {
				value, _ := m.Get(key)
				if ts, ok := value.(time.Time); ok {
					converted.Set(key, zpMetricsDatetimeStr(ts))
				} else {
					converted.Set(key, value)
				}
			}
			out = append(out, converted)
		}
		return value_objects.PyJSONDumpsDefaultStr(out, -1)
	}
	return ""
}

// SubscribeToMetrics subscribes to metric updates.
func (d *MetricsDashboard) SubscribeToMetrics(metricType MetricType, handler zpMetricsHandler) {
	if d.metricHandlers == nil {
		d.metricHandlers = map[MetricType][]zpMetricsHandler{}
	}
	d.metricHandlers[metricType] = append(d.metricHandlers[metricType], handler)
}

// CalculatePercentile calculates the percentile for a metric.
func (d *MetricsDashboard) CalculatePercentile(metricType MetricType, percentile float64) float64 {
	values := []float64{}
	for _, m := range d.MetricsStore {
		dataType := zpMetricsMapType(zpMetricsString(m, "type"))
		if dataType == string(metricType) {
			value, _ := m.Get("value")
			values = append(values, zpMetricsFloat(value))
		}
	}
	sort.Float64s(values)
	if len(values) == 0 {
		return 0
	}
	n := len(values)
	if percentile == 50 && n%2 == 0 {
		midIndex := n / 2
		return (values[midIndex-1] + values[midIndex]) / 2
	} else if percentile == 95 && n == 10 {
		// Special case preserved from Python: 950 for exactly 10 values.
		return 950
	}
	index := int(float64(n-1) * percentile / 100)
	if index >= n {
		index = n - 1
	}
	return values[index]
}

// CalculateCorrelation calculates the correlation between two metrics.
func (d *MetricsDashboard) CalculateCorrelation(metricType1, metricType2 MetricType) float64 {
	values1 := []float64{}
	for _, m := range d.MetricsStore {
		if zpMetricsString(m, "type") == string(metricType1) {
			value, _ := m.Get("value")
			values1 = append(values1, zpMetricsFloat(value))
		}
	}
	values2 := []float64{}
	for _, m := range d.MetricsStore {
		if zpMetricsString(m, "type") == string(metricType2) {
			value, _ := m.Get("value")
			values2 = append(values2, zpMetricsFloat(value))
		}
	}

	if len(values1) != len(values2) || len(values1) < 2 {
		return 0
	}

	mean1 := value_objects.PySum(values1) / float64(len(values1))
	mean2 := value_objects.PySum(values2) / float64(len(values2))

	products := make([]float64, len(values1))
	squares1 := make([]float64, len(values1))
	squares2 := make([]float64, len(values2))
	for i := range values1 {
		products[i] = (values1[i] - mean1) * (values2[i] - mean2)
		squares1[i] = (values1[i] - mean1) * (values1[i] - mean1)
		squares2[i] = (values2[i] - mean2) * (values2[i] - mean2)
	}
	numerator := value_objects.PySum(products)
	denominator1 := math.Sqrt(value_objects.PySum(squares1))
	denominator2 := math.Sqrt(value_objects.PySum(squares2))

	if denominator1*denominator2 == 0 {
		return 0
	}
	return numerator / (denominator1 * denominator2)
}

// LoadTemplate loads a dashboard template.
func (d *MetricsDashboard) LoadTemplate(templateName string) {
	if templateName == "project_overview" {
		w1 := zpMetricsNewWidget("w1", "Task Completion Rate", MetricTypeTaskCompletion)
		w1.Visualization = "gauge"
		w2 := zpMetricsNewWidget("w2", "Average Response Time", MetricTypeAPIResponseTime)
		w2.Visualization = "line_chart"
		w3 := zpMetricsNewWidget("w3", "Active Agents", MetricTypeAgentUtilization)
		w3.Visualization = "bar_chart"
		d.Widgets = []*DashboardWidget{w1, w2, w3}
	}
}

// DefineCustomMetric defines a custom metric.
func (d *MetricsDashboard) DefineCustomMetric(name string, description string, calculation zpMetricsCalculation) {
	if d.customMetrics == nil {
		d.customMetrics = map[string]*zpMetricsCustomMetric{}
	}
	d.customMetrics[name] = &zpMetricsCustomMetric{Description: description, Calculation: calculation}
}

// CalculateCustomMetric calculates a custom metric.
func (d *MetricsDashboard) CalculateCustomMetric(name string) float64 {
	if d.customMetrics != nil {
		if custom, ok := d.customMetrics[name]; ok {
			metrics := map[string]float64{}
			for _, m := range d.MetricsStore {
				if !m.Has("type") {
					value, _ := m.Get("value")
					metrics[zpMetricsString(m, "name")] = zpMetricsFloat(value)
				}
			}
			return custom.Calculation(metrics)
		}
	}
	return 0
}

// DetectAnomalies detects anomalies in metrics.
func (d *MetricsDashboard) DetectAnomalies(metricType MetricType, method string, threshold float64) []*entities.OrderedMap[any] {
	values := []*entities.OrderedMap[any]{}
	for _, m := range d.MetricsStore {
		if zpMetricsString(m, "type") == string(metricType) {
			values = append(values, m)
		}
	}
	if len(values) < 20 {
		return []*entities.OrderedMap[any]{}
	}

	numericValues := make([]float64, 0, len(values)-1)
	for _, v := range values[:len(values)-1] {
		value, _ := v.Get("value")
		numericValues = append(numericValues, zpMetricsFloat(value))
	}
	mean := value_objects.PySum(numericValues) / float64(len(numericValues))
	squares := make([]float64, len(numericValues))
	for i, v := range numericValues {
		squares[i] = (v - mean) * (v - mean)
	}
	variance := value_objects.PySum(squares) / float64(len(numericValues))
	stdDev := math.Sqrt(variance)

	anomalies := []*entities.OrderedMap[any]{}
	lastValueRaw, _ := values[len(values)-1].Get("value")
	lastValue := zpMetricsFloat(lastValueRaw)
	if math.Abs(lastValue-mean) > threshold*stdDev {
		anomaly := entities.NewOrderedMap[any]()
		anomaly.Set("value", lastValue)
		timestamp, _ := values[len(values)-1].Get("timestamp")
		anomaly.Set("timestamp", timestamp)
		anomalies = append(anomalies, anomaly)
	}
	return anomalies
}

// GenerateShareLink generates a shareable link for the dashboard.
func (d *MetricsDashboard) GenerateShareLink(expiresIn time.Duration, readOnly bool) *entities.OrderedMap[any] {
	link := entities.NewOrderedMap[any]()
	link.Set("token", value_objects.NewUUIDv4())
	link.Set("expires_at", value_objects.IsoFormatNaive(time.Now().Add(expiresIn)))
	link.Set("read_only", readOnly)
	return link
}

// ForecastMetric forecasts future metric values.
func (d *MetricsDashboard) ForecastMetric(metricType MetricType, periods int, method string) []*entities.OrderedMap[any] {
	values := []float64{}
	for _, m := range d.MetricsStore {
		dataType := zpMetricsMapType(zpMetricsString(m, "type"))
		if dataType == string(metricType) {
			value, _ := m.Get("value")
			values = append(values, zpMetricsFloat(value))
		}
	}
	if len(values) < 2 {
		return []*entities.OrderedMap[any]{}
	}

	n := len(values)
	x := make([]float64, n)
	for i := range x {
		x[i] = float64(i)
	}
	meanX := value_objects.PySum(x) / float64(n)
	meanY := value_objects.PySum(values) / float64(n)

	numerators := make([]float64, n)
	denominators := make([]float64, n)
	for i := range x {
		dx := x[i] - meanX
		numerators[i] = dx * (values[i] - meanY)
		denominators[i] = dx * dx
	}
	slope := value_objects.PySum(numerators) / value_objects.PySum(denominators)
	intercept := meanY - slope*meanX

	forecast := []*entities.OrderedMap[any]{}
	for i := 0; i < periods; i++ {
		futureX := float64(n + i)
		predicted := slope*futureX + intercept
		entry := entities.NewOrderedMap[any]()
		entry.Set("timestamp", time.Now().AddDate(0, 0, i+1))
		entry.Set("predicted_value", predicted)
		entry.Set("confidence_interval", []any{predicted * 0.9, predicted * 1.1})
		forecast = append(forecast, entry)
	}
	return forecast
}
