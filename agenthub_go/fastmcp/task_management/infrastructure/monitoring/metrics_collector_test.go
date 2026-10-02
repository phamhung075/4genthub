package monitoring_test

import (
	"math"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/monitoring"
)

func strTags(kv ...string) *entities.OrderedMap[string] {
	m := entities.NewOrderedMap[string]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i], kv[i+1])
	}
	return m
}

func pinClock(t *testing.T, at time.Time) {
	t.Helper()
	prevNow, prevPerf := monitoring.Now, monitoring.PerfCounter
	monitoring.Now = func() time.Time { return at }
	monitoring.PerfCounter = func() float64 { return 0 }
	t.Cleanup(func() { monitoring.Now, monitoring.PerfCounter = prevNow, prevPerf })
}

func approx(got, want float64) bool { return math.Abs(got-want) <= 1e-12*math.Max(1, math.Abs(want)) }

func TestMetricPointFormats(t *testing.T) {
	point := &monitoring.MetricPoint{
		Name:      "m",
		Value:     1.5,
		Unit:      "count",
		Timestamp: time.Unix(1700000000, 123000000).UTC(),
		Tags:      strTags("b", "2", "a", "1"),
		Category:  "general",
	}

	wantProm := `m{b="2",a="1"} 1.5 1700000000123`
	if got := point.ToPrometheusFormat(); got != wantProm {
		t.Fatalf("prometheus = %q, want %q", got, wantProm)
	}

	d := point.ToDict()
	if got, _ := d.Get("timestamp"); got != "2023-11-14T22:13:20.123000+00:00" {
		t.Fatalf("timestamp = %v", got)
	}
	if got, _ := d.Get("category"); got != "general" {
		t.Fatalf("category = %v", got)
	}
}

func TestMetricsCollectorSummary(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := monitoring.NewMetricsCollector(100, 60, nil)
	for _, v := range []float64{1, 2, 3, 4, 5} {
		c.RecordMetric("x", v, "count", nil, "general")
	}
	c.FlushMetrics()

	s := c.GetMetricSummary("x", nil)
	if s == nil {
		t.Fatal("summary nil")
	}
	if s.Count != 5 || s.MinValue != 1 || s.MaxValue != 5 {
		t.Fatalf("count/min/max = %d/%v/%v", s.Count, s.MinValue, s.MaxValue)
	}
	if !approx(s.AvgValue, 3) {
		t.Fatalf("avg = %v", s.AvgValue)
	}
	if !approx(s.P50Value, 3) {
		t.Fatalf("p50 = %v", s.P50Value)
	}
	if !approx(s.P95Value, 5.7) {
		t.Fatalf("p95 = %v, want 5.7", s.P95Value)
	}
	if !approx(s.P99Value, 5.94) {
		t.Fatalf("p99 = %v, want 5.94", s.P99Value)
	}
	if !approx(s.SumValue, 15) {
		t.Fatalf("sum = %v", s.SumValue)
	}
	if !approx(s.StdDev, math.Sqrt(2.5)) {
		t.Fatalf("stddev = %v, want %v", s.StdDev, math.Sqrt(2.5))
	}
	if s.Unit != "count" {
		t.Fatalf("unit = %q", s.Unit)
	}
	if s.TimeRangeStart.Unix() != 1700000000 || s.TimeRangeEnd.Unix() != 1700000000 {
		t.Fatalf("time range = %v..%v", s.TimeRangeStart, s.TimeRangeEnd)
	}

	if got := c.GetMetricSummary("missing", nil); got != nil {
		t.Fatalf("missing summary = %v", got)
	}
}

func TestMetricsCollectorFlushAndPrometheus(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := monitoring.NewMetricsCollector(100, 60, nil)
	c.RecordMetric("g", 1, "count", strTags("k", "v"), "general")
	if n := c.FlushMetrics(); n != 1 {
		t.Fatalf("flush = %d", n)
	}
	if n := c.FlushMetrics(); n != 0 {
		t.Fatalf("second flush = %d", n)
	}
	if got := c.GetAllMetricNames(); len(got) != 1 || got[0] != "g" {
		t.Fatalf("names = %v", got)
	}

	// Latest value per tag key wins.
	monitoring.Now = func() time.Time { return time.Unix(1700000010, 0).UTC() }
	c.RecordMetric("g", 2, "count", strTags("k", "v"), "general")
	c.FlushMetrics()
	got := c.ExportPrometheusMetrics(nil)
	want := "g{k=\"v\"} 2.0 1700000010000"
	if got != want {
		t.Fatalf("prometheus = %q, want %q", got, want)
	}
}

func TestMetricsCollectorClearOldMetrics(t *testing.T) {
	pinClock(t, time.Unix(1700000000, 0).UTC())
	c := monitoring.NewMetricsCollector(100, 60, nil)
	c.RecordMetric("old", 1, "count", nil, "general")
	c.RecordMetric("keep", 2, "count", nil, "general")
	c.FlushMetrics()

	monitoring.Now = func() time.Time { return time.Unix(1700000000+7200, 0).UTC() }
	if n := c.ClearOldMetrics(1); n != 2 {
		t.Fatalf("removed = %d, want 2", n)
	}
	if names := c.GetAllMetricNames(); len(names) != 0 {
		t.Fatalf("names = %v", names)
	}
}
