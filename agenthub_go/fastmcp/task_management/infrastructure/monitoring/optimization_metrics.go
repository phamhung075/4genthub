package monitoring

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// OptimizationMetric is an optimization-specific metric point with extra context.
type OptimizationMetric struct {
	Name             string
	Value            float64
	Unit             string
	Timestamp        time.Time
	OptimizationType string
	Operation        string
	OriginalSize     *int
	OptimizedSize    *int
	Tags             *entities.OrderedMap[string]
}

// CompressionRatio returns the compression ratio if both sizes are truthy, else 0.
func (o *OptimizationMetric) CompressionRatio() float64 {
	if o.OriginalSize != nil && *o.OriginalSize != 0 && o.OptimizedSize != nil && *o.OptimizedSize != 0 {
		return float64(*o.OriginalSize-*o.OptimizedSize) / float64(*o.OriginalSize) * 100
	}
	return 0.0
}

// ToPrometheusFormat converts to Prometheus metrics format with optimization context.
func (o *OptimizationMetric) ToPrometheusFormat() string {
	tags := entities.NewOrderedMap[string]()
	if o.Tags != nil {
		for _, k := range o.Tags.Keys() {
			v, _ := o.Tags.Get(k)
			tags.Set(k, v)
		}
	}
	tags.Set("optimization_type", o.OptimizationType)
	tags.Set("operation", o.Operation)
	var parts []string
	for _, k := range tags.Keys() {
		v, _ := tags.Get(k)
		parts = append(parts, fmt.Sprintf("%s=\"%s\"", k, v))
	}
	tagsStr := ""
	if len(parts) > 0 {
		tagsStr = "{" + joinComma(parts) + "}"
	}
	return fmt.Sprintf("%s%s %s %d", o.Name, tagsStr, tmvo.PyStr(o.Value), o.Timestamp.UnixMilli())
}

func joinComma(parts []string) string {
	out := ""
	for i, p := range parts {
		if i > 0 {
			out += ","
		}
		out += p
	}
	return out
}

type aggregationWindowEntry struct {
	Timestamp int
	Metric    string
	Value     float64
}

// OptimizationMetricsCollector is the enhanced collector for response optimization.
type OptimizationMetricsCollector struct {
	*MetricsCollector

	EnablePrometheus     bool
	PerformanceBaselines map[string]float64

	optimizationMu      sync.Mutex
	optimizationMetrics []*OptimizationMetric

	alertMu         sync.Mutex
	alertsTriggered map[string][]*entities.OrderedMap[any]
	alertOrder      []string

	windowOrder        []string
	aggregationWindows map[string][]aggregationWindowEntry
	windowMaxlen       map[string]int

	cacheHits  map[string]int
	cacheTotal map[string]int
	aiSuccess  map[string]int
	aiTotal    map[string]int
}

// NewOptimizationMetricsCollector mirrors OptimizationMetricsCollector.__init__.
func NewOptimizationMetricsCollector(bufferSize, flushIntervalSeconds int, outputDirectory *string, enablePrometheus bool) *OptimizationMetricsCollector {
	c := &OptimizationMetricsCollector{
		MetricsCollector: NewMetricsCollector(bufferSize, flushIntervalSeconds, outputDirectory),
		EnablePrometheus: enablePrometheus,
		PerformanceBaselines: map[string]float64{
			"response_size_threshold":   10000,
			"processing_time_threshold": 300,
			"cache_hit_rate_minimum":    70,
			"compression_ratio_minimum": 30,
		},
		alertsTriggered:    map[string][]*entities.OrderedMap[any]{},
		aggregationWindows: map[string][]aggregationWindowEntry{},
		windowMaxlen:       map[string]int{"1m": 60, "5m": 60, "1h": 60, "24h": 24},
		windowOrder:        []string{"1m", "5m", "1h", "24h"},
		cacheHits:          map[string]int{},
		cacheTotal:         map[string]int{},
		aiSuccess:          map[string]int{},
		aiTotal:            map[string]int{},
	}
	return c
}

func (o *OptimizationMetricsCollector) appendOptimization(m *OptimizationMetric) {
	o.optimizationMu.Lock()
	defer o.optimizationMu.Unlock()
	o.optimizationMetrics = append(o.optimizationMetrics, m)
	if o.BufferSize > 0 && len(o.optimizationMetrics) > o.BufferSize {
		o.optimizationMetrics = o.optimizationMetrics[len(o.optimizationMetrics)-o.BufferSize:]
	}
}

// RecordResponseOptimization records response optimization metrics.
func (o *OptimizationMetricsCollector) RecordResponseOptimization(originalSize, optimizedSize int, processingTimeMs float64, optimizationType string, operation string, tags *entities.OrderedMap[string]) {
	compressionRatio := (float64(originalSize-optimizedSize) / float64(originalSize)) * 100

	optMetric := &OptimizationMetric{
		Name:             "response_optimization",
		Value:            compressionRatio,
		Unit:             "percent",
		Timestamp:        Now(),
		OptimizationType: optimizationType,
		Operation:        operation,
		OriginalSize:     intPtr(originalSize),
		OptimizedSize:    intPtr(optimizedSize),
		Tags:             orEmptyTags(tags),
	}
	o.appendOptimization(optMetric)

	o.RecordSizeMetric("response_original_size", originalSize, tags)
	o.RecordSizeMetric("response_optimized_size", optimizedSize, tags)
	o.RecordPercentageMetric("response_compression_ratio", compressionRatio, tags)
	// Python passes processing_time_ms/1000 as a perf_counter start time; bug preserved.
	o.RecordTimingMetric("response_processing_time", processingTimeMs/1000, nil, tags)

	o.updateAggregationWindows("response_optimization", compressionRatio)
	o.updateAggregationWindows("response_processing_time", processingTimeMs)
	o.checkOptimizationAlerts(compressionRatio, processingTimeMs, optimizationType)
}

// RecordContextInjectionMetrics records context injection performance metrics.
func (o *OptimizationMetricsCollector) RecordContextInjectionMetrics(fieldsRequested, fieldsReturned int, queryTimeMs float64, cacheHit bool, tier string, tags *entities.OrderedMap[string]) {
	fieldReductionRatio := (float64(fieldsRequested-fieldsReturned) / float64(maxInt(fieldsRequested, 1))) * 100

	contextTags := entities.NewOrderedMap[string]()
	if tags != nil {
		for _, k := range tags.Keys() {
			v, _ := tags.Get(k)
			contextTags.Set(k, v)
		}
	}
	contextTags.Set("cache_hit", pyBoolStr(cacheHit))
	contextTags.Set("tier", tier)

	o.RecordMetric("context_fields_requested", float64(fieldsRequested), "count", contextTags, "general")
	o.RecordMetric("context_fields_returned", float64(fieldsReturned), "count", contextTags, "general")
	o.RecordPercentageMetric("context_field_reduction", fieldReductionRatio, contextTags)
	o.RecordTimingMetric("context_query_time", queryTimeMs/1000, nil, contextTags)
	hit := 0.0
	if cacheHit {
		hit = 1.0
	}
	o.RecordMetric("context_cache_hit", hit, "boolean", contextTags, "general")

	o.updateCacheHitRate(cacheHit, tier)
}

// RecordAIPerformanceMetrics records AI performance and comprehension metrics.
func (o *OptimizationMetricsCollector) RecordAIPerformanceMetrics(parseSuccess bool, extractionTimeMs float64, responseFormat, agentOperation string, errorType *string, tags *entities.OrderedMap[string]) {
	aiTags := entities.NewOrderedMap[string]()
	if tags != nil {
		for _, k := range tags.Keys() {
			v, _ := tags.Get(k)
			aiTags.Set(k, v)
		}
	}
	aiTags.Set("response_format", responseFormat)
	aiTags.Set("agent_operation", agentOperation)
	if errorType != nil && *errorType != "" {
		aiTags.Set("error_type", *errorType)
	}

	success := 0.0
	if parseSuccess {
		success = 1.0
	}
	o.RecordMetric("ai_parse_success", success, "boolean", aiTags, "general")
	o.RecordTimingMetric("ai_extraction_time", extractionTimeMs/1000, nil, aiTags)

	if !parseSuccess {
		o.RecordMetric("ai_parse_errors", 1.0, "count", aiTags, "errors")
	}
	o.RecordMetric("ai_agent_operations", 1.0, "count", aiTags, "operations")

	o.updateAISuccessRate(parseSuccess, agentOperation)
}

// RecordSystemHealthMetrics records system health and resource utilization metrics.
func (o *OptimizationMetricsCollector) RecordSystemHealthMetrics(cpuUsage, memoryUsage, networkBandwidthKbps float64, dbQueryCount int, dbQueryTimeMs float64, tags *entities.OrderedMap[string]) {
	systemTags := entities.NewOrderedMap[string]()
	if tags != nil {
		for _, k := range tags.Keys() {
			v, _ := tags.Get(k)
			systemTags.Set(k, v)
		}
	}
	systemTags.Set("source", "optimization_system")

	o.RecordPercentageMetric("system_cpu_usage", cpuUsage, systemTags)
	o.RecordPercentageMetric("system_memory_usage", memoryUsage, systemTags)
	o.RecordMetric("system_network_bandwidth", networkBandwidthKbps, "kbps", systemTags, "general")
	o.RecordMetric("system_db_queries", float64(dbQueryCount), "count", systemTags, "general")
	o.RecordTimingMetric("system_db_query_time", dbQueryTimeMs/1000, nil, systemTags)

	healthScore := o.calculateSystemHealthScore(cpuUsage, memoryUsage, dbQueryTimeMs)
	o.RecordMetric("system_health_score", healthScore, "score", systemTags, "general")
}

func (o *OptimizationMetricsCollector) updateAggregationWindows(metricName string, value float64) {
	timestamp := int(Now().Unix())
	for _, windowName := range o.windowOrder {
		window := append(o.aggregationWindows[windowName], aggregationWindowEntry{Timestamp: timestamp, Metric: metricName, Value: value})
		if maxlen := o.windowMaxlen[windowName]; maxlen > 0 && len(window) > maxlen {
			window = window[len(window)-maxlen:]
		}
		o.aggregationWindows[windowName] = window
	}
}

func (o *OptimizationMetricsCollector) updateCacheHitRate(cacheHit bool, tier string) {
	currentHits := o.cacheHits[tier]
	currentTotal := o.cacheTotal[tier]
	currentTotal++
	if cacheHit {
		currentHits++
	}
	o.cacheHits[tier] = currentHits
	o.cacheTotal[tier] = currentTotal

	hitRate := (float64(currentHits) / float64(currentTotal)) * 100
	o.RecordPercentageMetric("cache_hit_rate_"+tier, hitRate, tagsOf("tier", tier))

	if hitRate < o.PerformanceBaselines["cache_hit_rate_minimum"] {
		o.triggerAlert("cache_hit_rate_low",
			fmt.Sprintf("Cache hit rate for %s is %.1f%%", tier, hitRate),
			obj("tier", tier, "hit_rate", hitRate))
	}
}

func (o *OptimizationMetricsCollector) updateAISuccessRate(success bool, operation string) {
	o.aiTotal[operation]++
	if success {
		o.aiSuccess[operation]++
	}
	successRate := (float64(o.aiSuccess[operation]) / float64(o.aiTotal[operation])) * 100
	o.RecordPercentageMetric("ai_success_rate_"+operation, successRate, tagsOf("operation", operation))
}

func (o *OptimizationMetricsCollector) calculateSystemHealthScore(cpu, memory, dbTime float64) float64 {
	cpuScore := maxFloat(0, 30-(cpu/100)*30)
	memoryScore := maxFloat(0, 30-(memory/100)*30)
	dbScore := maxFloat(0, 40-(dbTime/1000)*20)
	return cpuScore + memoryScore + dbScore
}

func (o *OptimizationMetricsCollector) checkOptimizationAlerts(compressionRatio, processingTime float64, optType string) {
	if compressionRatio < o.PerformanceBaselines["compression_ratio_minimum"] {
		o.triggerAlert("low_compression_ratio",
			fmt.Sprintf("Compression ratio %.1f%% below minimum %s%%", compressionRatio, tmvo.PyStr(o.PerformanceBaselines["compression_ratio_minimum"])),
			obj("compression_ratio", compressionRatio, "optimization_type", optType))
	}
	if processingTime > o.PerformanceBaselines["processing_time_threshold"] {
		o.triggerAlert("high_processing_time",
			fmt.Sprintf("Processing time %.1fms exceeds threshold %sms", processingTime, tmvo.PyStr(o.PerformanceBaselines["processing_time_threshold"])),
			obj("processing_time", processingTime, "optimization_type", optType))
	}
}

func (o *OptimizationMetricsCollector) triggerAlert(alertType, message string, context *entities.OrderedMap[any]) {
	alert := obj(
		"type", alertType,
		"message", message,
		"context", context,
		"timestamp", tmvo.IsoFormat(Now()),
		"severity", o.getAlertSeverity(alertType),
	)
	o.alertMu.Lock()
	if _, seen := o.alertsTriggered[alertType]; !seen {
		o.alertOrder = append(o.alertOrder, alertType)
	}
	alerts := append(o.alertsTriggered[alertType], alert)
	if len(alerts) > 50 {
		alerts = alerts[len(alerts)-50:]
	}
	o.alertsTriggered[alertType] = alerts
	o.alertMu.Unlock()
}

func (o *OptimizationMetricsCollector) getAlertSeverity(alertType string) string {
	switch alertType {
	case "high_processing_time", "system_health_critical":
		return "critical"
	case "low_compression_ratio", "cache_hit_rate_low":
		return "warning"
	}
	return "info"
}

func summaryAny(s *MetricSummary) any {
	if s == nil {
		return nil
	}
	return s
}

// GetOptimizationSummary returns a comprehensive optimization performance summary.
func (o *OptimizationMetricsCollector) GetOptimizationSummary(timeWindowHours float64) *entities.OrderedMap[any] {
	cutoffTime := Now().Add(-time.Duration(timeWindowHours * float64(time.Hour)))

	o.optimizationMu.Lock()
	var recent []*OptimizationMetric
	for _, opt := range o.optimizationMetrics {
		if !opt.Timestamp.Before(cutoffTime) {
			recent = append(recent, opt)
		}
	}
	o.optimizationMu.Unlock()

	if len(recent) == 0 {
		return obj(
			"time_window_hours", timeWindowHours,
			"no_data", true,
			"message", "No optimization data in specified time window",
		)
	}

	compressionRatios := make([]float64, len(recent))
	for i, opt := range recent {
		compressionRatios[i] = opt.CompressionRatio()
	}

	profileCounts := entities.NewOrderedMap[int]()
	for _, opt := range recent {
		v, _ := profileCounts.Get(opt.OptimizationType)
		profileCounts.Set(opt.OptimizationType, v+1)
	}

	o.alertMu.Lock()
	var recentAlerts []*entities.OrderedMap[any]
	for _, alertType := range o.alertOrder {
		for _, alert := range o.alertsTriggered[alertType] {
			ts, _ := alert.Get("timestamp")
			parsed, err := tmvo.ParseISO(ts.(string))
			if err == nil && !parsed.Before(cutoffTime) {
				recentAlerts = append(recentAlerts, alert)
			}
		}
	}
	o.alertMu.Unlock()

	criticalCount := 0
	warningCount := 0
	for _, a := range recentAlerts {
		switch omString(a, "severity") {
		case "critical":
			criticalCount++
		case "warning":
			warningCount++
		}
	}
	sort.SliceStable(recentAlerts, func(i, j int) bool {
		return omString(recentAlerts[i], "timestamp") > omString(recentAlerts[j], "timestamp")
	})
	topAlerts := recentAlerts
	if len(topAlerts) > 10 {
		topAlerts = topAlerts[:10]
	}

	return obj(
		"time_window_hours", timeWindowHours,
		"optimization_performance", obj(
			"total_optimizations", len(recent),
			"avg_compression_ratio", tmvo.PySum(compressionRatios)/float64(len(compressionRatios)),
			"min_compression_ratio", minFloat(compressionRatios),
			"max_compression_ratio", maxSlice(compressionRatios),
			"profile_distribution", profileCounts,
		),
		"performance_metrics", obj(
			"avg_processing_time_ms", summaryAny(o.GetMetricSummary("response_processing_time", &timeWindowHours)),
			"cache_hit_rates", obj(
				"global", summaryAny(o.GetMetricSummary("cache_hit_rate_global", &timeWindowHours)),
				"project", summaryAny(o.GetMetricSummary("cache_hit_rate_project", &timeWindowHours)),
				"branch", summaryAny(o.GetMetricSummary("cache_hit_rate_branch", &timeWindowHours)),
				"task", summaryAny(o.GetMetricSummary("cache_hit_rate_task", &timeWindowHours)),
			),
			"ai_success_rates", obj(
				"hint_extraction", summaryAny(o.GetMetricSummary("ai_success_rate_hint_extraction", &timeWindowHours)),
				"response_parsing", summaryAny(o.GetMetricSummary("ai_success_rate_response_parsing", &timeWindowHours)),
				"task_delegation", summaryAny(o.GetMetricSummary("ai_success_rate_task_delegation", &timeWindowHours)),
			),
		),
		"system_health", obj(
			"health_score", summaryAny(o.GetMetricSummary("system_health_score", &timeWindowHours)),
			"resource_utilization", obj(
				"cpu", summaryAny(o.GetMetricSummary("system_cpu_usage", &timeWindowHours)),
				"memory", summaryAny(o.GetMetricSummary("system_memory_usage", &timeWindowHours)),
			),
		),
		"alerts", obj(
			"total_alerts", len(recentAlerts),
			"critical_alerts", criticalCount,
			"warning_alerts", warningCount,
			"recent_alerts", topAlerts,
		),
		"recommendations", o.generateOptimizationRecommendations(recent, recentAlerts),
	)
}

func (o *OptimizationMetricsCollector) generateOptimizationRecommendations(optimizations []*OptimizationMetric, alerts []*entities.OrderedMap[any]) []string {
	recommendations := []string{}
	if len(optimizations) == 0 {
		return append(recommendations, "No optimization data available - enable metrics collection")
	}

	ratios := make([]float64, len(optimizations))
	profileCounts := entities.NewOrderedMap[int]()
	for i, opt := range optimizations {
		ratios[i] = opt.CompressionRatio()
		v, _ := profileCounts.Get(opt.OptimizationType)
		profileCounts.Set(opt.OptimizationType, v+1)
	}
	avgCompression := tmvo.PySum(ratios) / float64(len(ratios))
	if avgCompression < 40 {
		recommendations = append(recommendations, "Consider implementing more aggressive response optimization strategies")
	}

	debug, _ := profileCounts.Get("DEBUG")
	minimal, _ := profileCounts.Get("MINIMAL")
	if debug > minimal {
		recommendations = append(recommendations, "High DEBUG profile usage detected - consider switching to MINIMAL for better performance")
	}

	for _, a := range alerts {
		if omString(a, "severity") == "critical" {
			recommendations = append(recommendations, "Critical performance issues detected - review system resources and optimization settings")
			break
		}
	}
	for _, a := range alerts {
		if containsSubstring(omString(a, "type"), "cache") {
			recommendations = append(recommendations, "Cache performance issues detected - consider increasing cache sizes or TTL values")
			break
		}
	}
	return recommendations
}

// ExportOptimizationDashboardData exports data in a Grafana-dashboard-friendly format.
func (o *OptimizationMetricsCollector) ExportOptimizationDashboardData(timeWindowHours float64) *entities.OrderedMap[any] {
	summary := o.GetOptimizationSummary(timeWindowHours)

	cacheTargets := []any{}
	for _, tier := range []string{"global", "project", "branch", "task"} {
		cacheTargets = append(cacheTargets, obj(
			"expr", "cache_hit_rate_"+tier,
			"legendFormat", tmvo.PyTitle(tier)+" Cache",
		))
	}

	return obj(
		"dashboard", obj(
			"title", "MCP Response Optimization Dashboard",
			"time", obj("from", fmt.Sprintf("now-%dh", int(timeWindowHours)), "to", "now"),
			"panels", []any{},
		),
		"metrics", obj(
			"response_optimization", obj(
				"title", "Response Optimization Performance",
				"type", "graph",
				"targets", []any{
					obj("expr", "response_compression_ratio", "legendFormat", "Compression Ratio %"),
					obj("expr", "response_processing_time", "legendFormat", "Processing Time (ms)"),
				},
			),
			"cache_performance", obj(
				"title", "Cache Hit Rates",
				"type", "stat",
				"targets", cacheTargets,
			),
			"system_health", obj(
				"title", "System Health Metrics",
				"type", "gauge",
				"targets", []any{
					obj("expr", "system_health_score", "legendFormat", "Health Score"),
					obj("expr", "system_cpu_usage", "legendFormat", "CPU Usage %"),
					obj("expr", "system_memory_usage", "legendFormat", "Memory Usage %"),
				},
			),
			"alerts", obj(
				"title", "Alert Status",
				"type", "table",
				"data", omGet(summary, "alerts"),
			),
		),
		"summary", summary,
	)
}

// GenerateOptimizationReport generates a comprehensive optimization performance report.
func (o *OptimizationMetricsCollector) GenerateOptimizationReport(timeWindowHours float64) *entities.OrderedMap[any] {
	summary := o.GetOptimizationSummary(timeWindowHours)
	systemReport := o.GeneratePerformanceReport(timeWindowHours)

	healthScore, _ := omGet(omMap(summary, "system_health"), "health_score").(*MetricSummary)
	healthStatus := "needs_attention"
	if healthScore != nil && healthScore.AvgValue > 70 {
		healthStatus = "healthy"
	}
	optPerf := omMap(summary, "optimization_performance")
	alerts := omMap(summary, "alerts")

	return obj(
		"report_metadata", obj(
			"generated_at", tmvo.IsoFormat(Now()),
			"time_window_hours", timeWindowHours,
			"report_type", "optimization_performance",
		),
		"executive_summary", obj(
			"total_optimizations", intValue(omGet(optPerf, "total_optimizations")),
			"avg_compression_achieved", omGet(optPerf, "avg_compression_ratio"),
			"system_health_status", healthStatus,
			"critical_issues", intValue(omGet(alerts, "critical_alerts")),
		),
		"detailed_metrics", summary,
		"system_performance", systemReport,
		"recommendations", omGet(summary, "recommendations"),
		"next_actions", []string{
			"Monitor critical alerts and address root causes",
			"Optimize cache configuration if hit rates are low",
			"Consider profile adjustments based on performance patterns",
			"Review system resource allocation if health score is declining",
		},
	)
}

func omGet(m *entities.OrderedMap[any], k string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(k)
	return v
}

// omMap returns m[k] when it is a dict, else nil (Python's dict.get chaining).
func omMap(m *entities.OrderedMap[any], k string) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	v, ok := m.Get(k)
	if !ok {
		return nil
	}
	om, _ := v.(*entities.OrderedMap[any])
	return om
}

func pyTruthy(v any) bool { return tmvo.PyTruthy(v) }

func asInt(v any) int {
	f, ok := tmvo.PyFloat(v)
	if !ok {
		return 0
	}
	return int(f)
}

func omString(m *entities.OrderedMap[any], k string) string {
	v := omGet(m, k)
	s, _ := v.(string)
	return s
}

func intValue(v any) int {
	n, _ := v.(int)
	return n
}

func containsSubstring(s, sub string) bool { return strings.Contains(s, sub) }

func orEmptyTags(t *entities.OrderedMap[string]) *entities.OrderedMap[string] {
	if t == nil {
		return entities.NewOrderedMap[string]()
	}
	return t
}

func intPtr(i int) *int { return &i }

func pyBoolStr(b bool) string {
	if b {
		return "True"
	}
	return "False"
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func maxFloat(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

func minFloat(xs []float64) float64 {
	out := xs[0]
	for _, x := range xs[1:] {
		if x < out {
			out = x
		}
	}
	return out
}

func maxSlice(xs []float64) float64 {
	out := xs[0]
	for _, x := range xs[1:] {
		if x > out {
			out = x
		}
	}
	return out
}

var (
	globalOptimizationMu        sync.Mutex
	globalOptimizationCollector *OptimizationMetricsCollector
)

// GetGlobalOptimizationCollector returns (creating if needed) the global collector.
func GetGlobalOptimizationCollector() *OptimizationMetricsCollector {
	globalOptimizationMu.Lock()
	defer globalOptimizationMu.Unlock()
	if globalOptimizationCollector == nil {
		globalOptimizationCollector = NewOptimizationMetricsCollector(15000, 30, nil, true)
	}
	return globalOptimizationCollector
}

// RecordResponseOptimization records response optimization on the global collector.
func RecordResponseOptimization(originalSize, optimizedSize int, processingTimeMs float64, optimizationType string, operation string, tags *entities.OrderedMap[string]) {
	GetGlobalOptimizationCollector().RecordResponseOptimization(originalSize, optimizedSize, processingTimeMs, optimizationType, operation, tags)
}

// RecordContextMetrics records context injection metrics on the global collector.
func RecordContextMetrics(fieldsRequested, fieldsReturned int, queryTimeMs float64, cacheHit bool, tier string, tags *entities.OrderedMap[string]) {
	GetGlobalOptimizationCollector().RecordContextInjectionMetrics(fieldsRequested, fieldsReturned, queryTimeMs, cacheHit, tier, tags)
}

// RecordAIMetrics records AI performance metrics on the global collector.
func RecordAIMetrics(parseSuccess bool, extractionTimeMs float64, responseFormat, agentOperation string, errorType *string, tags *entities.OrderedMap[string]) {
	GetGlobalOptimizationCollector().RecordAIPerformanceMetrics(parseSuccess, extractionTimeMs, responseFormat, agentOperation, errorType, tags)
}

// StartOptimizationMonitoring starts global optimization metrics collection.
func StartOptimizationMonitoring() { GetGlobalOptimizationCollector().StartCollection() }

// StopOptimizationMonitoring stops global optimization metrics collection.
func StopOptimizationMonitoring() {
	globalOptimizationMu.Lock()
	defer globalOptimizationMu.Unlock()
	if globalOptimizationCollector != nil {
		globalOptimizationCollector.StopCollection()
		globalOptimizationCollector = nil
	}
}
