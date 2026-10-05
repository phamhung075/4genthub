package services

import (
	"fmt"
	"math"
	"os"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Performance Monitor for Rule Orchestration Platform.
//
// Port of performance_monitor.py. The asyncio methods are ordinary synchronous methods;
// there is no event loop, so the background monitoring loop is not started as a task.

// PerfCounter is the injectable monotonic clock used by CacheBenchmark timing.
var PerfCounter = func() float64 { return float64(time.Now().UnixNano()) / 1e9 }

// PerformanceSnapshot is performance_monitor.PerformanceSnapshot.
type PerformanceSnapshot struct {
	Timestamp             float64
	HitRate               float64
	MissRate              float64
	AverageResponseTimeMS float64
	OperationsPerSecond   float64
	MemoryUsageMB         float64
	CacheSize             int
	EvictionCount         int
}

// NewPerformanceSnapshot builds a PerformanceSnapshot.
func NewPerformanceSnapshot(timestamp, hitRate, missRate, averageResponseTimeMS, operationsPerSecond, memoryUsageMB float64, cacheSize, evictionCount int) *PerformanceSnapshot {
	return &PerformanceSnapshot{
		Timestamp:             timestamp,
		HitRate:               hitRate,
		MissRate:              missRate,
		AverageResponseTimeMS: averageResponseTimeMS,
		OperationsPerSecond:   operationsPerSecond,
		MemoryUsageMB:         memoryUsageMB,
		CacheSize:             cacheSize,
		EvictionCount:         evictionCount,
	}
}

// BenchmarkConfig is performance_monitor.BenchmarkConfig.
type BenchmarkConfig struct {
	NumOperations          int
	ConcurrentOperations   int
	DataSizeBytes          int
	TestDurationSeconds    int
	WarmupOperations       int
	IncludeStressTest      bool
	IncludeMemoryTest      bool
	IncludeConcurrencyTest bool
}

// NewBenchmarkConfig builds BenchmarkConfig with the Python dataclass defaults.
func NewBenchmarkConfig() *BenchmarkConfig {
	return &BenchmarkConfig{
		NumOperations:          1000,
		ConcurrentOperations:   10,
		DataSizeBytes:          1024,
		TestDurationSeconds:    60,
		WarmupOperations:       100,
		IncludeStressTest:      true,
		IncludeMemoryTest:      true,
		IncludeConcurrencyTest: true,
	}
}

// BenchmarkResult is performance_monitor.BenchmarkResult.
type BenchmarkResult struct {
	Config                           BenchmarkConfig
	StartTime                        float64
	EndTime                          float64
	TotalOperations                  int
	SuccessfulOperations             int
	FailedOperations                 int
	OperationsPerSecond              float64
	AverageResponseTimeMS            float64
	MinResponseTimeMS                float64
	MaxResponseTimeMS                float64
	P50ResponseTimeMS                float64
	P95ResponseTimeMS                float64
	P99ResponseTimeMS                float64
	FinalHitRate                     float64
	FinalCacheSize                   int
	MemoryUsageMB                    float64
	EvictionCount                    int
	MaxConcurrentOperations          int
	ConcurrentPerformanceDegradation float64
	ErrorRate                        float64
	TimeoutCount                     int
	Recommendations                  []string
}

// NewBenchmarkResult builds a BenchmarkResult, applying the Python dataclass defaults.
func NewBenchmarkResult(config BenchmarkConfig, startTime, endTime float64) *BenchmarkResult {
	return &BenchmarkResult{
		Config:          config,
		StartTime:       startTime,
		EndTime:         endTime,
		Recommendations: []string{},
	}
}

// boundedSnapshots is a Go stand-in for collections.deque(maxlen=history_size).
type boundedSnapshots struct {
	items  []*PerformanceSnapshot
	maxlen int
}

func newBoundedSnapshots(maxlen int) *boundedSnapshots {
	return &boundedSnapshots{items: []*PerformanceSnapshot{}, maxlen: maxlen}
}

func (b *boundedSnapshots) append(s *PerformanceSnapshot) {
	if b.maxlen <= 0 {
		return
	}
	b.items = append(b.items, s)
	if len(b.items) > b.maxlen {
		b.items = b.items[len(b.items)-b.maxlen:]
	}
}

// Len is len(deque).
func (b *boundedSnapshots) Len() int { return len(b.items) }

// At is deque[i] (0 is the oldest).
func (b *boundedSnapshots) At(i int) *PerformanceSnapshot { return b.items[i] }

// Last is deque[-1].
func (b *boundedSnapshots) Last() *PerformanceSnapshot {
	if len(b.items) == 0 {
		return nil
	}
	return b.items[len(b.items)-1]
}

// All returns the snapshots from oldest to newest.
func (b *boundedSnapshots) All() []*PerformanceSnapshot {
	return append([]*PerformanceSnapshot{}, b.items...)
}

// boundedFloats is a Go stand-in for collections.deque(maxlen=1000).
type boundedFloats struct {
	items  []float64
	maxlen int
}

func newBoundedFloats(maxlen int) *boundedFloats {
	return &boundedFloats{items: []float64{}, maxlen: maxlen}
}

func (b *boundedFloats) append(v float64) {
	if b.maxlen <= 0 {
		return
	}
	b.items = append(b.items, v)
	if len(b.items) > b.maxlen {
		b.items = b.items[len(b.items)-b.maxlen:]
	}
}

// Len is len(deque).
func (b *boundedFloats) Len() int { return len(b.items) }

// CacheManager is the consumer-side view of the cache manager used by the monitor.
type CacheManager interface {
	Get(key string, lazyLoadCallback func(string) (any, error)) (any, error)
	Put(key string, content any, ttl *float64, tags []string, priority int) (bool, error)
	Invalidate(key string) (bool, error)
	GetPerformanceMetrics() *entities.OrderedMap[any]
}

// PerformanceMonitor is performance_monitor.PerformanceMonitor.
type PerformanceMonitor struct {
	CacheManager       CacheManager
	MonitoringInterval float64
	HistorySize        int
	PerformanceHistory *boundedSnapshots
	AlertThresholds    map[string]float64
	MonitoringActive   bool
	MonitorTask        any
	AlertCallbacks     []func(alert string, snapshot *PerformanceSnapshot) error
	OperationTimes     *boundedFloats
	ErrorCount         int
	LastSnapshotTime   float64
}

// NewPerformanceMonitor builds the real-time performance monitor.
func NewPerformanceMonitor(cacheManager CacheManager, monitoringInterval float64, historySize int) *PerformanceMonitor {
	return &PerformanceMonitor{
		CacheManager:       cacheManager,
		MonitoringInterval: monitoringInterval,
		HistorySize:        historySize,
		PerformanceHistory: newBoundedSnapshots(historySize),
		AlertThresholds: map[string]float64{
			"hit_rate_min":         0.7,
			"response_time_max_ms": 100.0,
			"memory_usage_max_mb":  1024.0,
			"error_rate_max":       0.05,
		},
		MonitoringActive: false,
		MonitorTask:      nil,
		AlertCallbacks:   []func(alert string, snapshot *PerformanceSnapshot) error{},
		OperationTimes:   newBoundedFloats(1000),
		LastSnapshotTime: nowSeconds(),
	}
}

// StartMonitoring is PerformanceMonitor.start_monitoring.
func (m *PerformanceMonitor) StartMonitoring() {
	if m.MonitoringActive {
		return
	}
	m.MonitoringActive = true
	// self.monitor_task = asyncio.create_task(self._monitoring_loop()) has no equivalent
	// without an event loop.
}

// StopMonitoring is PerformanceMonitor.stop_monitoring.
func (m *PerformanceMonitor) StopMonitoring() {
	m.MonitoringActive = false
	if m.MonitorTask != nil {
		// self.monitor_task.cancel() has no equivalent without an event loop.
	}
}

func (m *PerformanceMonitor) monitoringLoop() {
	if !m.MonitoringActive {
		return
	}
	m.captureSnapshot()
	m.checkAlerts()
}

func (m *PerformanceMonitor) captureSnapshot() {
	metrics := m.CacheManager.GetPerformanceMetrics()
	cacheStatistics := omMap(metrics.GetAny("cache_statistics"))
	performanceMetrics := omMap(metrics.GetAny("performance_metrics"))
	cacheLevels := omMap(metrics.GetAny("cache_levels"))
	evictionStatistics := omMap(metrics.GetAny("eviction_statistics"))

	snapshot := NewPerformanceSnapshot(
		nowSeconds(),
		omFloat(cacheStatistics, "hit_rate"),
		omFloat(cacheStatistics, "miss_rate"),
		omFloat(performanceMetrics, "average_response_time_ms"),
		omFloat(performanceMetrics, "operations_per_second"),
		omFloat(cacheLevels, "memory_size_bytes")/(1024*1024),
		omInt(cacheLevels, "memory_entries"),
		omInt(evictionStatistics, "total_evictions"),
	)
	m.PerformanceHistory.append(snapshot)
}

func (m *PerformanceMonitor) checkAlerts() {
	if m.PerformanceHistory.Len() == 0 {
		return
	}
	latest := m.PerformanceHistory.Last()
	var alerts []string

	if latest.HitRate < m.AlertThresholds["hit_rate_min"] {
		alerts = append(alerts, fmt.Sprintf("Low hit rate: %.2f%%", latest.HitRate*100))
	}
	if latest.AverageResponseTimeMS > m.AlertThresholds["response_time_max_ms"] {
		alerts = append(alerts, fmt.Sprintf("High response time: %.2fms", latest.AverageResponseTimeMS))
	}
	if latest.MemoryUsageMB > m.AlertThresholds["memory_usage_max_mb"] {
		alerts = append(alerts, fmt.Sprintf("High memory usage: %.2fMB", latest.MemoryUsageMB))
	}

	for _, alert := range alerts {
		for _, callback := range m.AlertCallbacks {
			_ = callback(alert, latest)
		}
	}
}

// AddAlertCallback is PerformanceMonitor.add_alert_callback.
func (m *PerformanceMonitor) AddAlertCallback(callback func(alert string, snapshot *PerformanceSnapshot) error) {
	m.AlertCallbacks = append(m.AlertCallbacks, callback)
}

// GetPerformanceSummary is PerformanceMonitor.get_performance_summary.
func (m *PerformanceMonitor) GetPerformanceSummary(timeWindowMinutes int) *entities.OrderedMap[any] {
	cutoffTime := nowSeconds() - float64(timeWindowMinutes)*60
	recentSnapshots := []*PerformanceSnapshot{}
	for _, s := range m.PerformanceHistory.All() {
		if s.Timestamp >= cutoffTime {
			recentSnapshots = append(recentSnapshots, s)
		}
	}

	if len(recentSnapshots) == 0 {
		out := newOrderedAny()
		out.Set("error", "No data available for specified time window")
		return out
	}

	n := float64(len(recentSnapshots))
	hitRates := make([]float64, len(recentSnapshots))
	responseTimes := make([]float64, len(recentSnapshots))
	opsPerSec := make([]float64, len(recentSnapshots))
	memoryUsages := make([]float64, len(recentSnapshots))
	for i, s := range recentSnapshots {
		hitRates[i] = s.HitRate
		responseTimes[i] = s.AverageResponseTimeMS
		opsPerSec[i] = s.OperationsPerSecond
		memoryUsages[i] = s.MemoryUsageMB
	}
	avgHitRate := value_objects.PySum(hitRates) / n
	avgResponseTime := value_objects.PySum(responseTimes) / n
	avgOpsPerSec := value_objects.PySum(opsPerSec) / n
	avgMemoryUsage := value_objects.PySum(memoryUsages) / n

	hitRateTrend := 0.0
	responseTimeTrend := 0.0
	if len(recentSnapshots) >= 2 {
		hitRateTrend = recentSnapshots[len(recentSnapshots)-1].HitRate - recentSnapshots[0].HitRate
		responseTimeTrend = recentSnapshots[len(recentSnapshots)-1].AverageResponseTimeMS - recentSnapshots[0].AverageResponseTimeMS
	}

	averages := newOrderedAny()
	averages.Set("hit_rate", avgHitRate)
	averages.Set("response_time_ms", avgResponseTime)
	averages.Set("operations_per_second", avgOpsPerSec)
	averages.Set("memory_usage_mb", avgMemoryUsage)

	trends := newOrderedAny()
	trends.Set("hit_rate_change", hitRateTrend)
	trends.Set("response_time_change_ms", responseTimeTrend)

	last := recentSnapshots[len(recentSnapshots)-1]
	current := newOrderedAny()
	current.Set("hit_rate", last.HitRate)
	current.Set("response_time_ms", last.AverageResponseTimeMS)
	current.Set("cache_size", last.CacheSize)
	current.Set("memory_usage_mb", last.MemoryUsageMB)

	out := newOrderedAny()
	out.Set("time_window_minutes", timeWindowMinutes)
	out.Set("data_points", len(recentSnapshots))
	out.Set("averages", averages)
	out.Set("trends", trends)
	out.Set("current", current)
	return out
}

// ExportPerformanceData is PerformanceMonitor.export_performance_data. An unsupported
// format mirrors the Python ValueError and is swallowed to return false.
func (m *PerformanceMonitor) ExportPerformanceData(filePath string, format string) bool {
	data := []any{}
	for _, s := range m.PerformanceHistory.All() {
		seconds := int64(math.Floor(s.Timestamp))
		nanos := int64(math.Round((s.Timestamp - float64(seconds)) * 1e9))
		item := newOrderedAny()
		item.Set("timestamp", s.Timestamp)
		item.Set("datetime", value_objects.IsoFormatNaive(time.Unix(seconds, nanos).Local()))
		item.Set("hit_rate", s.HitRate)
		item.Set("miss_rate", s.MissRate)
		item.Set("average_response_time_ms", s.AverageResponseTimeMS)
		item.Set("operations_per_second", s.OperationsPerSecond)
		item.Set("memory_usage_mb", s.MemoryUsageMB)
		item.Set("cache_size", s.CacheSize)
		item.Set("eviction_count", s.EvictionCount)
		data = append(data, item)
	}

	if value_objects.PyLower(format) == "json" {
		text, err := value_objects.PyJSONDumps(data, 2)
		if err != nil {
			return false
		}
		if err := os.WriteFile(filePath, []byte(text), 0o666); err != nil {
			return false
		}
		return true
	}

	// raise ValueError(f"Unsupported export format: {format}")
	return false
}

// CacheBenchmark is performance_monitor.CacheBenchmark.
type CacheBenchmark struct {
	CacheManager  CacheManager
	ResponseTimes []float64
}

// NewCacheBenchmark builds a CacheBenchmark.
func NewCacheBenchmark(cacheManager CacheManager) *CacheBenchmark {
	return &CacheBenchmark{CacheManager: cacheManager, ResponseTimes: []float64{}}
}

// RunBasicBenchmark is CacheBenchmark.run_basic_benchmark.
func (b *CacheBenchmark) RunBasicBenchmark(numOperations int) (*entities.OrderedMap[any], error) {
	startTime := PerfCounter()

	keys := make([]string, numOperations)
	contents := make([]string, numOperations)
	for i := 0; i < numOperations; i++ {
		keys[i] = fmt.Sprintf("test_key_%d", i)
		contents[i] = strings.Repeat(fmt.Sprintf("test_content_%d", i), 100)
	}

	putStart := PerfCounter()
	putSuccess := 0
	for i := range keys {
		ok, err := b.CacheManager.Put(keys[i], contents[i], nil, nil, 1)
		if err != nil {
			return nil, err
		}
		if ok {
			putSuccess++
		}
	}
	putTime := PerfCounter() - putStart

	getStart := PerfCounter()
	getSuccess := 0
	for _, key := range keys {
		value, err := b.CacheManager.Get(key, nil)
		if err != nil {
			return nil, err
		}
		if value != nil {
			getSuccess++
		}
	}
	getTime := PerfCounter() - getStart

	totalTime := PerfCounter() - startTime

	finalMetrics := b.CacheManager.GetPerformanceMetrics()
	cacheStatistics := omMap(finalMetrics.GetAny("cache_statistics"))
	cacheLevels := omMap(finalMetrics.GetAny("cache_levels"))
	evictionStatistics := omMap(finalMetrics.GetAny("eviction_statistics"))

	configuration := newOrderedAny()
	configuration.Set("num_operations", numOperations)
	configuration.Set("data_size_per_item", 100*len("test_content_0"))

	performance := newOrderedAny()
	performance.Set("total_operations", numOperations*2)
	performance.Set("total_time_seconds", totalTime)
	performance.Set("operations_per_second", float64(numOperations*2)/totalTime)
	performance.Set("put_operations_per_second", float64(numOperations)/putTime)
	performance.Set("get_operations_per_second", float64(numOperations)/getTime)
	performance.Set("put_success_rate", float64(putSuccess)/float64(numOperations))
	performance.Set("get_success_rate", float64(getSuccess)/float64(numOperations))

	timing := newOrderedAny()
	timing.Set("average_put_time_ms", (putTime/float64(numOperations))*1000)
	timing.Set("average_get_time_ms", (getTime/float64(numOperations))*1000)
	timing.Set("total_put_time_seconds", putTime)
	timing.Set("total_get_time_seconds", getTime)

	cacheMetrics := newOrderedAny()
	cacheMetrics.Set("final_hit_rate", omFloat(cacheStatistics, "hit_rate"))
	cacheMetrics.Set("final_cache_size", omInt(cacheLevels, "memory_entries"))
	cacheMetrics.Set("memory_usage_mb", omFloat(cacheLevels, "memory_size_bytes")/(1024*1024))
	cacheMetrics.Set("total_evictions", omInt(evictionStatistics, "total_evictions"))

	benchmarkResults := newOrderedAny()
	benchmarkResults.Set("configuration", configuration)
	benchmarkResults.Set("performance", performance)
	benchmarkResults.Set("timing", timing)
	benchmarkResults.Set("cache_metrics", cacheMetrics)

	recommendations := []string{}
	if omFloat(performance, "operations_per_second") < 1000 {
		recommendations = append(recommendations, "Low throughput detected - consider performance optimizations")
	}
	if omFloat(cacheMetrics, "final_hit_rate") < 0.8 {
		recommendations = append(recommendations, "Low hit rate - consider increasing cache size or adjusting TTL")
	}
	if omFloat(performance, "put_success_rate") < 0.95 {
		recommendations = append(recommendations, "High put failure rate - investigate cache capacity issues")
	}
	benchmarkResults.Set("recommendations", recommendations)

	for _, key := range keys {
		b.CacheManager.Invalidate(key)
	}

	return benchmarkResults, nil
}

func omMap(v any) *entities.OrderedMap[any] {
	if om, ok := v.(*entities.OrderedMap[any]); ok && om != nil {
		return om
	}
	return newOrderedAny()
}
