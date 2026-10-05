// Package monitoring ports task_management/infrastructure/monitoring.
package monitoring

import (
	"fmt"
	"math"
	"math/big"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Now is the wall clock used for MetricPoint timestamps and report times
// (Python datetime.now(UTC) / time.time()).
var Now = func() time.Time { return time.Now().UTC() }

// PerfCounter mirrors time.perf_counter().
var PerfCounter = func() float64 { return float64(time.Now().UnixNano()) / 1e9 }

// obj builds a Python-ordered dict with the given key/value pairs.
func obj(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// tagsOf builds a str->str ordered dict from alternating key/value arguments.
func tagsOf(kv ...string) *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i], kv[i+1])
	}
	return m
}

func emptyTags() *entities.OrderedMap[string] { return entities.NewOrderedMap[string]() }

// MetricPoint is one metric measurement point.
type MetricPoint struct {
	Name      string
	Value     float64
	Unit      string
	Timestamp time.Time
	Tags      *entities.OrderedMap[string]
	Category  string
}

// ToDict converts to a dictionary for serialization.
func (m *MetricPoint) ToDict() *entities.OrderedMap[any] {
	return obj(
		"name", m.Name,
		"value", m.Value,
		"unit", m.Unit,
		"timestamp", tmvo.IsoFormat(m.Timestamp),
		"tags", m.Tags,
		"category", m.Category,
	)
}

// ToPrometheusFormat converts to Prometheus metrics format.
func (m *MetricPoint) ToPrometheusFormat() string {
	var parts []string
	if m.Tags != nil {
		for _, k := range m.Tags.Keys() {
			v, _ := m.Tags.Get(k)
			parts = append(parts, fmt.Sprintf("%s=\"%s\"", k, v))
		}
	}
	tagsStr := strings.Join(parts, ",")
	tagsPart := ""
	if tagsStr != "" {
		tagsPart = "{" + tagsStr + "}"
	}
	return fmt.Sprintf("%s%s %s %d", m.Name, tagsPart, tmvo.PyStr(m.Value), m.Timestamp.UnixMilli())
}

// MetricSummary is a statistical summary of metrics.
type MetricSummary struct {
	Name           string
	Count          int
	MinValue       float64
	MaxValue       float64
	AvgValue       float64
	P50Value       float64
	P95Value       float64
	P99Value       float64
	SumValue       float64
	StdDev         float64
	Unit           string
	TimeRangeStart time.Time
	TimeRangeEnd   time.Time
}

// ToDict mirrors dataclasses.asdict: datetimes stay datetime objects.
func (s *MetricSummary) ToDict() *entities.OrderedMap[any] {
	return obj(
		"name", s.Name,
		"count", s.Count,
		"min_value", s.MinValue,
		"max_value", s.MaxValue,
		"avg_value", s.AvgValue,
		"p50_value", s.P50Value,
		"p95_value", s.P95Value,
		"p99_value", s.P99Value,
		"sum_value", s.SumValue,
		"std_dev", s.StdDev,
		"unit", s.Unit,
		"time_range_start", s.TimeRangeStart,
		"time_range_end", s.TimeRangeEnd,
	)
}

// SystemMetricsProvider is the psutil seam. Python calls psutil directly; Go injects
// these functions so tests can be deterministic.
type SystemMetricsProvider struct {
	CPUPercent    func(interval float64) float64
	VirtualMemory func() (percent float64, availableBytes int64)
	ProcessMemory func() (rss, vms int64)
	DiskIO        func() (readBytes, writeBytes int64, ok bool)
}

// DefaultSystemMetrics returns a best-effort Linux provider (psutil is not available).
func DefaultSystemMetrics() SystemMetricsProvider {
	return SystemMetricsProvider{
		CPUPercent:    func(interval float64) float64 { return 0 },
		VirtualMemory: readProcMeminfo,
		ProcessMemory: readProcSelfStatm,
		DiskIO:        func() (int64, int64, bool) { return 0, 0, false },
	}
}

func readProcMeminfo() (float64, int64) {
	raw, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0, 0
	}
	var totalKB, availKB int64 = -1, -1
	for _, line := range strings.Split(string(raw), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		var dst *int64
		switch fields[0] {
		case "MemTotal:":
			dst = &totalKB
		case "MemAvailable:":
			dst = &availKB
		default:
			continue
		}
		n, ok := tmvo.PyParseInt(fields[1])
		if !ok || !n.IsInt64() {
			continue
		}
		*dst = n.Int64()
	}
	if totalKB <= 0 || availKB < 0 {
		return 0, 0
	}
	used := totalKB - availKB
	return float64(used) / float64(totalKB) * 100, availKB * 1024
}

func readProcSelfStatm() (int64, int64) {
	raw, err := os.ReadFile("/proc/self/statm")
	if err != nil {
		return 0, 0
	}
	fields := strings.Fields(string(raw))
	if len(fields) < 2 {
		return 0, 0
	}
	size, ok1 := tmvo.PyParseInt(fields[0])
	rss, ok2 := tmvo.PyParseInt(fields[1])
	if !ok1 || !ok2 || !size.IsInt64() || !rss.IsInt64() {
		return 0, 0
	}
	page := int64(os.Getpagesize())
	return rss.Int64() * page, size.Int64() * page
}

// MetricsCollector collects, aggregates and exports performance metrics.
type MetricsCollector struct {
	BufferSize      int
	FlushInterval   int
	OutputDirectory string

	System SystemMetricsProvider

	bufferMu      sync.Mutex
	metricsBuffer []*MetricPoint

	aggMu           sync.Mutex
	aggregated      map[string][]*MetricPoint
	aggregatedOrder []string

	running      bool
	startTime    float64
	metricCounts map[string]int
}

// NewMetricsCollector mirrors MetricsCollector.__init__.
func NewMetricsCollector(bufferSize, flushIntervalSeconds int, outputDirectory *string) *MetricsCollector {
	dir := "/tmp/metrics"
	if outputDirectory != nil {
		dir = *outputDirectory
	}
	_ = os.MkdirAll(dir, 0o755)
	return &MetricsCollector{
		BufferSize:      bufferSize,
		FlushInterval:   flushIntervalSeconds,
		OutputDirectory: dir,
		System:          DefaultSystemMetrics(),
		aggregated:      map[string][]*MetricPoint{},
		startTime:       wallSeconds(),
		metricCounts:    map[string]int{},
	}
}

func wallSeconds() float64 { return float64(Now().UnixNano()) / 1e9 }

// appendBuffer is deque(maxlen=buffer_size): the oldest item is dropped when full.
func (c *MetricsCollector) appendBuffer(m *MetricPoint) {
	if c.BufferSize <= 0 {
		return
	}
	c.metricsBuffer = append(c.metricsBuffer, m)
	if len(c.metricsBuffer) > c.BufferSize {
		c.metricsBuffer = c.metricsBuffer[len(c.metricsBuffer)-c.BufferSize:]
	}
}

// StartCollection starts background metric collection and processing. Python creates
// asyncio tasks here; Go only records the state (there is no event loop).
func (c *MetricsCollector) StartCollection() {
	if c.running {
		return
	}
	c.running = true
	c.startTime = wallSeconds()
}

// StopCollection stops collection and flushes remaining metrics.
func (c *MetricsCollector) StopCollection() {
	if !c.running {
		return
	}
	c.running = false
	c.FlushMetrics()
}

// RecordMetric records a single metric point.
func (c *MetricsCollector) RecordMetric(name string, value float64, unit string, tags *entities.OrderedMap[string], category string) {
	if tags == nil {
		tags = emptyTags()
	}
	metric := &MetricPoint{
		Name:      name,
		Value:     value,
		Unit:      unit,
		Timestamp: Now(),
		Tags:      tags,
		Category:  category,
	}
	c.bufferMu.Lock()
	c.appendBuffer(metric)
	c.metricCounts[name]++
	c.bufferMu.Unlock()
}

// RecordTimingMetric records a timing metric from start/end times.
func (c *MetricsCollector) RecordTimingMetric(name string, startTime float64, endTime *float64, tags *entities.OrderedMap[string]) {
	end := startTime
	if endTime == nil {
		end = PerfCounter()
	} else {
		end = *endTime
	}
	duration := (end - startTime) * 1000
	c.RecordMetric(name, duration, "ms", tags, "timing")
}

// RecordSizeMetric records a size metric in bytes.
func (c *MetricsCollector) RecordSizeMetric(name string, sizeBytes int, tags *entities.OrderedMap[string]) {
	c.RecordMetric(name, float64(sizeBytes), "bytes", tags, "size")
}

// RecordPercentageMetric records a percentage metric (0-100).
func (c *MetricsCollector) RecordPercentageMetric(name string, percentage float64, tags *entities.OrderedMap[string]) {
	c.RecordMetric(name, percentage, "percent", tags, "percentage")
}

// RecordRateMetric records an operations-per-second rate metric.
func (c *MetricsCollector) RecordRateMetric(name string, rate float64, tags *entities.OrderedMap[string]) {
	c.RecordMetric(name, rate, "ops/sec", tags, "rate")
}

// FlushMetrics flushes buffered metrics to storage and returns how many were flushed.
func (c *MetricsCollector) FlushMetrics() int {
	c.bufferMu.Lock()
	if len(c.metricsBuffer) == 0 {
		c.bufferMu.Unlock()
		return 0
	}
	toFlush := c.metricsBuffer
	c.metricsBuffer = nil
	c.bufferMu.Unlock()

	if len(toFlush) == 0 {
		return 0
	}
	c.processMetricsBatch(toFlush)
	return len(toFlush)
}

func (c *MetricsCollector) processMetricsBatch(metrics []*MetricPoint) {
	c.aggMu.Lock()
	for _, metric := range metrics {
		if _, seen := c.aggregated[metric.Name]; !seen {
			c.aggregatedOrder = append(c.aggregatedOrder, metric.Name)
		}
		c.aggregated[metric.Name] = append(c.aggregated[metric.Name], metric)
	}
	c.aggMu.Unlock()

	timestamp := Now().Format("20060102_150405")
	filename := filepath.Join(c.OutputDirectory, "metrics_batch_"+timestamp+".json")
	items := make([]any, len(metrics))
	for i, metric := range metrics {
		items[i] = metric.ToDict()
	}
	_ = os.WriteFile(filename, []byte(tmvo.PyJSONDumpsDefaultStr(items, 2)), 0o644)
}

// CollectSystemMetrics performs one psutil collection pass (the Python loop sleeps 10s).
func (c *MetricsCollector) CollectSystemMetrics() {
	cpuPercent := c.System.CPUPercent(1)
	c.RecordPercentageMetric("system_cpu_usage", cpuPercent, tagsOf("source", "system"))

	percent, available := c.System.VirtualMemory()
	c.RecordPercentageMetric("system_memory_usage", percent, tagsOf("source", "system"))
	c.RecordSizeMetric("system_memory_available", int(available), tagsOf("source", "system"))

	rss, vms := c.System.ProcessMemory()
	c.RecordSizeMetric("process_memory_rss", int(rss), tagsOf("source", "process"))
	c.RecordSizeMetric("process_memory_vms", int(vms), tagsOf("source", "process"))

	if readBytes, writeBytes, ok := c.System.DiskIO(); ok {
		c.RecordRateMetric("system_disk_read_rate", float64(readBytes), tagsOf("source", "system"))
		c.RecordRateMetric("system_disk_write_rate", float64(writeBytes), tagsOf("source", "system"))
	}
}

// GetMetricSummary returns the statistical summary for a metric, or nil.
func (c *MetricsCollector) GetMetricSummary(metricName string, timeWindowHours *float64) *MetricSummary {
	c.aggMu.Lock()
	all, ok := c.aggregated[metricName]
	if !ok {
		c.aggMu.Unlock()
		return nil
	}
	metrics := append([]*MetricPoint{}, all...)
	c.aggMu.Unlock()

	if timeWindowHours != nil && *timeWindowHours != 0 {
		cutoff := Now().Add(-time.Duration(*timeWindowHours * float64(time.Hour)))
		filtered := metrics[:0:0]
		for _, m := range metrics {
			if !m.Timestamp.Before(cutoff) {
				filtered = append(filtered, m)
			}
		}
		metrics = filtered
	}
	if len(metrics) == 0 {
		return nil
	}

	values := make([]float64, len(metrics))
	for i, m := range metrics {
		values[i] = m.Value
	}
	sorted := append([]float64{}, values...)
	sort.Float64s(sorted)

	minV, maxV := sorted[0], sorted[0]
	sum := tmvo.PySum(values)
	for _, v := range sorted {
		if v < minV {
			minV = v
		}
		if v > maxV {
			maxV = v
		}
	}

	var p95, p99 float64
	if len(values) > 1 {
		p95 = pyExclusiveQuantile(sorted, 20, 19)
	} else {
		p95 = values[0]
	}
	if len(values) > 2 {
		p99 = pyExclusiveQuantile(sorted, 100, 99)
	} else {
		p99 = values[0]
	}

	stdDev := 0.0
	if len(values) > 1 {
		stdDev = pyStdev(values)
	}

	start, end := metrics[0].Timestamp, metrics[0].Timestamp
	for _, m := range metrics {
		if m.Timestamp.Before(start) {
			start = m.Timestamp
		}
		if m.Timestamp.After(end) {
			end = m.Timestamp
		}
	}

	return &MetricSummary{
		Name:           metricName,
		Count:          len(values),
		MinValue:       minV,
		MaxValue:       maxV,
		AvgValue:       pyMean(values),
		P50Value:       pyMedian(values),
		P95Value:       p95,
		P99Value:       p99,
		SumValue:       sum,
		StdDev:         stdDev,
		Unit:           metrics[0].Unit,
		TimeRangeStart: start,
		TimeRangeEnd:   end,
	}
}

// pyExclusiveQuantile mirrors statistics.quantiles(data, n=n, method="exclusive")[i-1].
func pyExclusiveQuantile(sortedData []float64, n, i int) float64 {
	m := len(sortedData) + 1
	j := i * m / n
	if j < 1 {
		j = 1
	}
	if j > len(sortedData)-1 {
		j = len(sortedData) - 1
	}
	delta := i*m - j*n
	return (sortedData[j-1]*float64(n-delta) + sortedData[j]*float64(delta)) / float64(n)
}

// pyMedian mirrors statistics.median.
func pyMedian(values []float64) float64 {
	sorted := append([]float64{}, values...)
	sort.Float64s(sorted)
	n := len(sorted)
	if n == 0 {
		return math.NaN()
	}
	if n%2 == 1 {
		return sorted[n/2]
	}
	i := n / 2
	return (sorted[i-1] + sorted[i]) / 2
}

// ratOf converts a finite float to its exact rational value.
func ratOf(f float64) *big.Rat {
	r := new(big.Rat)
	if r.SetFloat64(f) == nil {
		return nil
	}
	return r
}

// pyMean mirrors statistics.mean: exact rational sum divided by n.
func pyMean(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	total := new(big.Rat)
	for _, v := range values {
		r := ratOf(v)
		if r == nil {
			return tmvo.PySum(values) / float64(len(values))
		}
		total.Add(total, r)
	}
	total.Quo(total, new(big.Rat).SetInt64(int64(len(values))))
	f, _ := total.Float64()
	return f
}

// pyStdev mirrors statistics.stdev: sqrt(sum((x-mean)^2)/(n-1)) with exact deviations.
func pyStdev(values []float64) float64 {
	n := len(values)
	if n < 2 {
		return 0
	}
	total := new(big.Rat)
	for _, v := range values {
		r := ratOf(v)
		if r == nil {
			return 0
		}
		total.Add(total, r)
	}
	meanRat := new(big.Rat).Quo(total, new(big.Rat).SetInt64(int64(n)))
	ss := new(big.Rat)
	for _, v := range values {
		r := ratOf(v)
		diff := new(big.Rat).Sub(r, meanRat)
		ss.Add(ss, new(big.Rat).Mul(diff, diff))
	}
	denom := new(big.Rat).SetInt64(int64(n - 1))
	return tmvo.PySqrtRat(new(big.Rat).Quo(ss, denom))
}

// GetAllMetricNames returns all collected metric names in insertion order.
func (c *MetricsCollector) GetAllMetricNames() []string {
	c.aggMu.Lock()
	defer c.aggMu.Unlock()
	return append([]string{}, c.aggregatedOrder...)
}

// ExportPrometheusMetrics exports metrics in Prometheus format.
func (c *MetricsCollector) ExportPrometheusMetrics(outputFile *string) string {
	var lines []string

	c.aggMu.Lock()
	for _, metricName := range c.aggregatedOrder {
		metricsList := c.aggregated[metricName]
		latest := map[string]*MetricPoint{}
		var order []string
		for _, metric := range metricsList {
			tagKey := tagKeyJSON(metric.Tags)
			prev, ok := latest[tagKey]
			if !ok || metric.Timestamp.After(prev.Timestamp) {
				if !ok {
					order = append(order, tagKey)
				}
				latest[tagKey] = metric
			}
		}
		for _, key := range order {
			lines = append(lines, latest[key].ToPrometheusFormat())
		}
	}
	c.aggMu.Unlock()

	content := strings.Join(lines, "\n")
	if outputFile != nil {
		_ = os.WriteFile(*outputFile, []byte(content), 0o644)
	}
	return content
}

func tagKeyJSON(tags *entities.OrderedMap[string]) string {
	keys := []string{}
	if tags != nil {
		keys = tags.Keys()
	}
	sort.Strings(keys)
	pairs := make([]any, len(keys))
	for i, k := range keys {
		v, _ := tags.Get(k)
		pairs[i] = []any{k, v}
	}
	s, _ := tmvo.PyJSONDumps(pairs, -1)
	return s
}

// GeneratePerformanceReport generates a comprehensive performance report.
func (c *MetricsCollector) GeneratePerformanceReport(timeWindowHours float64) *entities.OrderedMap[any] {
	report := obj(
		"report_timestamp", tmvo.IsoFormat(Now()),
		"time_window_hours", timeWindowHours,
		"metric_summaries", entities.NewOrderedMap[any](),
		"system_health", entities.NewOrderedMap[any](),
		"performance_targets", entities.NewOrderedMap[any](),
	)
	summaries, _ := report.Get("metric_summaries")
	systemHealth, _ := report.Get("system_health")
	targets, _ := report.Get("performance_targets")
	summariesMap := summaries.(*entities.OrderedMap[any])
	healthMap := systemHealth.(*entities.OrderedMap[any])
	targetsMap := targets.(*entities.OrderedMap[any])

	for _, name := range c.GetAllMetricNames() {
		summary := c.GetMetricSummary(name, &timeWindowHours)
		if summary != nil {
			summariesMap.Set(name, summary.ToDict())
		}
	}

	one := 1.0
	cpuSummary := c.GetMetricSummary("system_cpu_usage", &one)
	memorySummary := c.GetMetricSummary("system_memory_usage", &one)

	if cpuSummary != nil {
		healthMap.Set("cpu_usage", obj(
			"avg_percent", cpuSummary.AvgValue,
			"max_percent", cpuSummary.MaxValue,
			"status", healthStatus(cpuSummary.AvgValue),
		))
	}
	if memorySummary != nil {
		healthMap.Set("memory_usage", obj(
			"avg_percent", memorySummary.AvgValue,
			"max_percent", memorySummary.MaxValue,
			"status", healthStatus(memorySummary.AvgValue),
		))
	}

	responseTimeSummary := c.GetMetricSummary("mcp_response_time", &timeWindowHours)
	if responseTimeSummary != nil {
		targetsMap.Set("response_time", obj(
			"avg_ms", responseTimeSummary.AvgValue,
			"p95_ms", responseTimeSummary.P95Value,
			"target_met", responseTimeSummary.P95Value <= 200,
			"target_ms", 200,
		))
	}

	totalMetrics := 0
	for _, n := range c.metricCounts {
		totalMetrics += n
	}
	uptimeHours := (wallSeconds() - c.startTime) / 3600
	metricsPerHour := 0.0
	if uptimeHours > 0 {
		metricsPerHour = float64(totalMetrics) / uptimeHours
	}
	bufferUtilization := float64(len(c.metricsBuffer)) / float64(c.BufferSize)

	report.Set("collection_stats", obj(
		"total_metrics_collected", totalMetrics,
		"metrics_per_hour", metricsPerHour,
		"unique_metric_names", len(c.metricCounts),
		"uptime_hours", uptimeHours,
		"buffer_utilization", bufferUtilization,
	))
	return report
}

func healthStatus(avg float64) string {
	if avg < 80 {
		return "healthy"
	}
	if avg < 95 {
		return "warning"
	}
	return "critical"
}

// ClearOldMetrics clears metrics older than the specified hours and returns the count.
func (c *MetricsCollector) ClearOldMetrics(hoursToKeep float64) int {
	cutoff := Now().Add(-time.Duration(hoursToKeep * float64(time.Hour)))
	removedCount := 0

	c.aggMu.Lock()
	for _, metricName := range append([]string{}, c.aggregatedOrder...) {
		original := c.aggregated[metricName]
		kept := original[:0:0]
		for _, m := range original {
			if !m.Timestamp.Before(cutoff) {
				kept = append(kept, m)
			}
		}
		c.aggregated[metricName] = kept
		removedCount += len(original) - len(kept)
		if len(kept) == 0 {
			delete(c.aggregated, metricName)
			c.aggregatedOrder = removeString(c.aggregatedOrder, metricName)
		}
	}
	c.aggMu.Unlock()
	return removedCount
}

func removeString(xs []string, s string) []string {
	for i, x := range xs {
		if x == s {
			return append(xs[:i:i], xs[i+1:]...)
		}
	}
	return xs
}

// TimingContext is a context manager for measuring execution time.
type TimingContext struct {
	Collector  *MetricsCollector
	MetricName string
	Tags       *entities.OrderedMap[string]
	StartTime  *float64
}

// NewTimingContext mirrors TimingContext(collector, metric_name, tags).
func NewTimingContext(collector *MetricsCollector, metricName string, tags *entities.OrderedMap[string]) *TimingContext {
	return &TimingContext{Collector: collector, MetricName: metricName, Tags: tags}
}

// Enter mirrors __enter__.
func (t *TimingContext) Enter() *TimingContext {
	st := PerfCounter()
	t.StartTime = &st
	return t
}

// Exit mirrors __exit__.
func (t *TimingContext) Exit() {
	if t.StartTime != nil && *t.StartTime != 0 {
		t.Collector.RecordTimingMetric(t.MetricName, *t.StartTime, nil, t.Tags)
	}
}

var (
	globalCollectorMu sync.Mutex
	globalCollector   *MetricsCollector
)

// GetGlobalCollector returns (creating if needed) the global metrics collector.
func GetGlobalCollector() *MetricsCollector {
	globalCollectorMu.Lock()
	defer globalCollectorMu.Unlock()
	if globalCollector == nil {
		globalCollector = NewMetricsCollector(10000, 60, nil)
	}
	return globalCollector
}

// RecordMetric records a metric on the global collector.
func RecordMetric(name string, value float64, unit string, tags *entities.OrderedMap[string]) {
	GetGlobalCollector().RecordMetric(name, value, unit, tags, "general")
}

// TimingContextGlobal creates a timing context using the global collector.
func TimingContextGlobal(name string, tags *entities.OrderedMap[string]) *TimingContext {
	return NewTimingContext(GetGlobalCollector(), name, tags)
}

// StartGlobalCollection starts global metrics collection.
func StartGlobalCollection() { GetGlobalCollector().StartCollection() }

// StopGlobalCollection stops global metrics collection.
func StopGlobalCollection() {
	globalCollectorMu.Lock()
	defer globalCollectorMu.Unlock()
	if globalCollector != nil {
		globalCollector.StopCollection()
		globalCollector = nil
	}
}
