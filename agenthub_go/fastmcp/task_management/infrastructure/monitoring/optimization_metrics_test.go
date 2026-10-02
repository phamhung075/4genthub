package monitoring_test

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/monitoring"
)

func newOptCollector() *monitoring.OptimizationMetricsCollector {
	return monitoring.NewOptimizationMetricsCollector(1000, 30, nil, true)
}

func TestOptimizationMetricFormats(t *testing.T) {
	orig, opt := 1000, 400
	m := &monitoring.OptimizationMetric{
		Name:             "response_optimization",
		Value:            60,
		Unit:             "percent",
		Timestamp:        time.Unix(1700000000, 0).UTC(),
		OptimizationType: "MINIMAL",
		Operation:        "response_format",
		OriginalSize:     &orig,
		OptimizedSize:    &opt,
		Tags:             strTags("b", "2"),
	}
	if got := m.CompressionRatio(); !approx(got, 60) {
		t.Fatalf("ratio = %v", got)
	}
	zero := 0
	empty := &monitoring.OptimizationMetric{OriginalSize: &zero, OptimizedSize: &opt}
	if got := empty.CompressionRatio(); got != 0 {
		t.Fatalf("zero-original ratio = %v", got)
	}
	want := `response_optimization{b="2",optimization_type="MINIMAL",operation="response_format"} 60.0 1700000000000`
	if got := m.ToPrometheusFormat(); got != want {
		t.Fatalf("prometheus = %q, want %q", got, want)
	}
}

func TestOptimizationSummaryAndAlerts(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := newOptCollector()
	c.RecordResponseOptimization(1000, 900, 50, "MINIMAL", "response_format", nil)

	s := c.GetOptimizationSummary(1)
	if noData, _ := s.Get("no_data"); noData != nil {
		t.Fatalf("unexpected no_data: %v", s)
	}
	optPerf := mustMap(t, s, "optimization_performance")
	if got, _ := optPerf.Get("total_optimizations"); got != 1 {
		t.Fatalf("total = %v", got)
	}
	if got, _ := optPerf.Get("avg_compression_ratio"); !approx(got.(float64), 10) {
		t.Fatalf("avg = %v", got)
	}
	distAny, _ := optPerf.Get("profile_distribution")
	dist, ok := distAny.(*entities.OrderedMap[int])
	if !ok {
		t.Fatalf("dist type = %T", distAny)
	}
	if got, _ := dist.Get("MINIMAL"); got != 1 {
		t.Fatalf("dist = %v", got)
	}

	alerts := mustMap(t, s, "alerts")
	if got, _ := alerts.Get("total_alerts"); got != 1 {
		t.Fatalf("total_alerts = %v", got)
	}
	if got, _ := alerts.Get("warning_alerts"); got != 1 {
		t.Fatalf("warning_alerts = %v", got)
	}
	if got, _ := alerts.Get("critical_alerts"); got != 0 {
		t.Fatalf("critical_alerts = %v", got)
	}
	recs, _ := s.Get("recommendations")
	if len(recs.([]string)) == 0 {
		t.Fatalf("recommendations empty")
	}
}

func TestOptimizationNoData(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := newOptCollector()
	s := c.GetOptimizationSummary(1)
	if got, _ := s.Get("no_data"); got != true {
		t.Fatalf("no_data = %v", got)
	}
	if got, _ := s.Get("message"); got != "No optimization data in specified time window" {
		t.Fatalf("message = %v", got)
	}
}

func TestOptimizationAlertsTrimmed(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := newOptCollector()
	for i := 0; i < 51; i++ {
		c.RecordResponseOptimization(1000, 900, 50, "MINIMAL", "response_format", nil)
	}
	s := c.GetOptimizationSummary(1)
	alerts := mustMap(t, s, "alerts")
	if got, _ := alerts.Get("total_alerts"); got != 50 {
		t.Fatalf("total_alerts = %v, want 50", got)
	}
}

func TestSystemHealthScoreAndCacheHitRate(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := newOptCollector()
	c.RecordSystemHealthMetrics(0, 0, 0, 0, 0, nil)
	c.FlushMetrics()
	score := c.GetMetricSummary("system_health_score", nil)
	if score == nil || !approx(score.AvgValue, 100) {
		t.Fatalf("score = %v", score)
	}

	c.RecordSystemHealthMetrics(100, 100, 0, 0, 1000, nil)
	c.FlushMetrics()
	score = c.GetMetricSummary("system_health_score", nil)
	if score == nil || !approx(score.AvgValue, 60) {
		t.Fatalf("avg score = %v, want 60", score)
	}

	c.RecordContextInjectionMetrics(10, 5, 100, true, "global", nil)
	c.RecordContextInjectionMetrics(10, 5, 100, false, "global", nil)
	c.FlushMetrics()
	hit := c.GetMetricSummary("cache_hit_rate_global", nil)
	if hit == nil || !approx(hit.AvgValue, 75) {
		t.Fatalf("hit rate avg = %v, want 75", hit)
	}
}

func mustMap(t *testing.T, m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	om, ok := v.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("key %q is %T", key, v)
	}
	return om
}
