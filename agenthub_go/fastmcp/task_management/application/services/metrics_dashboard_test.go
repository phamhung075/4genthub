package services

import (
	"errors"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func zpMetricsTestWantKeys(t *testing.T, m *entities.OrderedMap[any], want []string) {
	t.Helper()
	if got := m.Keys(); !reflect.DeepEqual(got, want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
}

func TestMetricType_Values(t *testing.T) {
	want := []MetricType{
		MetricTypeCounter, MetricTypeGauge, MetricTypeHistogram, MetricTypeTimer,
		MetricTypeTaskCompletion, MetricTypeAPIResponseTime, MetricTypeAgentUtilization,
	}
	got := []string{string(MetricTypeCounter), string(MetricTypeGauge), string(MetricTypeHistogram), string(MetricTypeTimer),
		string(MetricTypeTaskCompletion), string(MetricTypeAPIResponseTime), string(MetricTypeAgentUtilization)}
	expected := []string{"counter", "gauge", "histogram", "timer", "task_completion", "api_response_time", "agent_utilization"}
	if !reflect.DeepEqual(got, expected) {
		t.Fatalf("values = %v, want %v", got, expected)
	}
	if string(want[0]) != "counter" || string(want[6]) != "agent_utilization" {
		t.Fatalf("unexpected member values: %v", want)
	}
}

func TestAggregationType_Values(t *testing.T) {
	got := []string{string(AggregationTypeAverage), string(AggregationTypeMax), string(AggregationTypeMin), string(AggregationTypeSum), string(AggregationTypeCount)}
	want := []string{"average", "max", "min", "sum", "count"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("values = %v, want %v", got, want)
	}
}

func TestDashboardWidget_Defaults(t *testing.T) {
	w := zpMetricsNewWidget("w1", "Title", MetricTypeGauge)
	if w.ID != "w1" || w.Title != "Title" || w.MetricType != MetricTypeGauge {
		t.Fatalf("unexpected widget: %+v", w)
	}
	if w.Visualization != "line_chart" {
		t.Fatalf("visualization = %q, want line_chart", w.Visualization)
	}
	if w.Position == nil || len(w.Position) != 0 {
		t.Fatalf("position = %v, want empty dict", w.Position)
	}
}

func TestMetricAlert_Defaults(t *testing.T) {
	a := zpMetricsNewAlert("a1", "Alert", MetricTypeGauge, "greater_than", 5.0)
	if a.Action != "notify" {
		t.Fatalf("action = %q, want notify", a.Action)
	}
	if !a.Enabled {
		t.Fatalf("enabled = false, want true")
	}
}

func TestMetricPoint_ToDict(t *testing.T) {
	tags := entities.NewOrderedMap[string]()
	tags.Set("env", "prod")
	tags.Set("host", "a")
	p := zpMetricsNewMetricPoint(time.Date(2024, 1, 1, 12, 0, 0, 500000000, time.UTC), 7.5, tags)
	out := p.ToDict()
	zpMetricsTestWantKeys(t, out, []string{"timestamp", "value", "tags"})
	if got := zpMetricsTestOut(t, out, "timestamp"); got != "2024-01-01T12:00:00.500000" {
		t.Fatalf("timestamp = %v", got)
	}
	if got := zpMetricsTestOut(t, out, "value"); got != 7.5 {
		t.Fatalf("value = %v", got)
	}
	tagsOut, _ := out.Get("tags")
	om, ok := tagsOut.(*entities.OrderedMap[string])
	if !ok {
		t.Fatalf("tags type = %T", tagsOut)
	}
	if v, _ := om.Get("env"); v != "prod" {
		t.Fatalf("tag env = %q", v)
	}
}

func zpMetricsTestOut(t *testing.T, m *entities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	return v
}

func TestMetricsDashboard_InitializeStandardMetrics(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	if d.RetentionHours != 24 || d.RefreshInterval != 60 {
		t.Fatalf("unexpected dashboard: %+v", d)
	}
	wantNames := []string{
		"response_optimization_count", "response_compression_ratio", "response_processing_time",
		"context_field_reduction", "template_cache_hit_rate", "cache_hit_rate", "cache_size",
		"cache_evictions", "api_response_time", "memory_usage", "optimization_errors",
	}
	if got := d.Metrics.Keys(); !reflect.DeepEqual(got, wantNames) {
		t.Fatalf("metric names = %v, want %v", got, wantNames)
	}
	if len(d.Metrics.Keys()) != 11 {
		t.Fatalf("metric count = %d, want 11", len(d.Metrics.Keys()))
	}
	types := map[string]MetricType{
		"response_optimization_count": MetricTypeCounter,
		"response_compression_ratio":  MetricTypeHistogram,
		"response_processing_time":    MetricTypeTimer,
		"context_field_reduction":     MetricTypeHistogram,
		"template_cache_hit_rate":     MetricTypeGauge,
		"cache_hit_rate":              MetricTypeGauge,
		"cache_size":                  MetricTypeGauge,
		"cache_evictions":             MetricTypeCounter,
		"api_response_time":           MetricTypeTimer,
		"memory_usage":                MetricTypeGauge,
		"optimization_errors":         MetricTypeCounter,
	}
	for name, want := range types {
		m, _ := d.Metrics.Get(name)
		if m.MetricType != want {
			t.Fatalf("%s type = %v, want %v", name, m.MetricType, want)
		}
	}
	units := map[string]string{
		"response_optimization_count": "count",
		"response_compression_ratio":  "percent",
		"response_processing_time":    "milliseconds",
		"context_field_reduction":     "percent",
		"template_cache_hit_rate":     "percent",
		"cache_hit_rate":              "percent",
		"cache_size":                  "bytes",
		"cache_evictions":             "count",
		"api_response_time":           "milliseconds",
		"memory_usage":                "megabytes",
		"optimization_errors":         "count",
	}
	for name, want := range units {
		m, _ := d.Metrics.Get(name)
		if m.Unit != want {
			t.Fatalf("%s unit = %q, want %q", name, m.Unit, want)
		}
	}
}

func TestMetricsDashboard_RecordMetricTypeAndHandler(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	seen := []any{}
	d.SubscribeToMetrics(MetricTypeTaskCompletion, func(m *entities.OrderedMap[any]) {
		seen = append(seen, zpMetricsTestOut(t, m, "value"))
	})
	v := 9.0
	ts := time.Date(2024, 1, 1, 12, 0, 0, 0, time.UTC)
	mt := MetricTypeTaskCompletion
	d.RecordMetric(nil, &v, nil, &mt, &ts)
	if len(d.MetricsStore) != 1 {
		t.Fatalf("store len = %d, want 1", len(d.MetricsStore))
	}
	entry := d.MetricsStore[0]
	zpMetricsTestWantKeys(t, entry, []string{"type", "value", "timestamp", "tags"})
	if got := zpMetricsTestOut(t, entry, "type"); got != "task_completion" {
		t.Fatalf("type = %v", got)
	}
	if got := zpMetricsTestOut(t, entry, "value"); got != 9.0 {
		t.Fatalf("value = %v", got)
	}
	if got := zpMetricsTestOut(t, entry, "timestamp"); got != ts {
		t.Fatalf("timestamp = %v", got)
	}
	if len(seen) != 1 || seen[0] != 9.0 {
		t.Fatalf("handler saw %v", seen)
	}
}

func TestMetricsDashboard_RecordMetricNameAndWindows(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	// Unregistered custom metric only goes to metrics_store.
	name := "custom_x"
	v := 5.0
	d.RecordMetric(&name, &v, nil, nil, nil)
	if len(d.MetricsStore) != 1 {
		t.Fatalf("store len = %d, want 1", len(d.MetricsStore))
	}
	zpMetricsTestWantKeys(t, d.MetricsStore[0], []string{"name", "value", "timestamp", "tags"})
	if d.Metrics.Keys()[0] == "custom_x" {
		t.Fatalf("custom metric must not be registered")
	}
	// Registered metric gets a point and a performance-window entry.
	gaugeName := "cache_hit_rate"
	for i := 0; i < 120; i++ {
		val := float64(i)
		d.RecordMetric(&gaugeName, &val, nil, nil, nil)
	}
	m, _ := d.Metrics.Get(gaugeName)
	if m.GetLatest() == nil || *m.GetLatest() != 119.0 {
		t.Fatalf("latest = %v, want 119", m.GetLatest())
	}
	if d.perfWindows["1m"].Len() != 60 {
		t.Fatalf("1m window len = %d, want 60", d.perfWindows["1m"].Len())
	}
	first := d.perfWindows["1m"].items[0]
	if got := zpMetricsTestOut(t, first, "value"); got != 60.0 {
		t.Fatalf("first window value = %v, want 60.0", got)
	}
	zpMetricsTestWantKeys(t, first, []string{"timestamp", "metric", "value"})
	if head, ok := first.Get("timestamp"); !ok || reflect.TypeOf(head).Kind() != reflect.Int64 {
		t.Fatalf("window timestamp = %v, want int64 unix seconds", head)
	}
	// Cache hit rate below 60 produces warnings, trimmed to the last 100.
	if len(d.Alerts) != 60 {
		t.Fatalf("alerts len = %d, want 60", len(d.Alerts))
	}
}

func TestMetricsDashboard_IncrementSetTimerHistogram(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	d.IncrementCounter("response_optimization_count", 1.0, nil)
	d.IncrementCounter("response_optimization_count", 5.0, nil)
	if got := zpMetricsTestMustGet(d.Metrics, t, "response_optimization_count").GetLatest(); got == nil || *got != 6.0 {
		t.Fatalf("counter = %v, want 6", got)
	}
	d.SetGauge("cache_hit_rate", 42.0, nil)
	if got := zpMetricsTestMustGet(d.Metrics, t, "cache_hit_rate").GetLatest(); got == nil || *got != 42.0 {
		t.Fatalf("gauge = %v, want 42", got)
	}
	d.RecordTimer("api_response_time", 12.5, nil)
	if got := zpMetricsTestMustGet(d.Metrics, t, "api_response_time").GetLatest(); got == nil || *got != 12.5 {
		t.Fatalf("timer = %v, want 12.5", got)
	}
	d.RecordHistogram("context_field_reduction", 33.0, nil)
	if got := zpMetricsTestMustGet(d.Metrics, t, "context_field_reduction").GetLatest(); got == nil || *got != 33.0 {
		t.Fatalf("histogram = %v, want 33", got)
	}
	// Wrong metric kinds are no-ops.
	d.IncrementCounter("cache_hit_rate", 1.0, nil)
	if got := zpMetricsTestMustGet(d.Metrics, t, "cache_hit_rate").GetLatest(); got == nil || *got != 42.0 {
		t.Fatalf("gauge after counter = %v, want 42", got)
	}
	d.SetGauge("response_optimization_count", 1.0, nil)
	if got := zpMetricsTestMustGet(d.Metrics, t, "response_optimization_count").GetLatest(); got == nil || *got != 6.0 {
		t.Fatalf("counter after gauge = %v, want 6", got)
	}
}

func zpMetricsTestMustGet(o *entities.OrderedMap[*Metric], t *testing.T, key string) *Metric {
	t.Helper()
	v, ok := o.Get(key)
	if !ok {
		t.Fatalf("missing metric %q", key)
	}
	return v
}

func TestMetricsDashboard_GetMetricSummary(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	for _, v := range []float64{10, 20, 30, 40, 50} {
		val := v
		name := "cache_hit_rate"
		d.RecordMetric(&name, &val, nil, nil, nil)
	}
	s := d.GetMetricSummary("cache_hit_rate", 60)
	if s == nil {
		t.Fatal("summary is nil")
	}
	zpMetricsTestWantKeys(t, s, []string{"name", "type", "description", "unit", "data_points", "duration_minutes",
		"latest_value", "first_timestamp", "last_timestamp", "min_value", "max_value", "avg_value", "median_value"})
	for key, want := range map[string]any{
		"name": "cache_hit_rate", "type": "gauge", "description": "Overall cache hit rate", "unit": "percent",
		"data_points": 5, "duration_minutes": 60, "latest_value": 50.0,
		"min_value": 10.0, "max_value": 50.0, "avg_value": 30.0, "median_value": 30.0,
	} {
		if got := zpMetricsTestOut(t, s, key); got != want {
			t.Fatalf("summary[%s] = %v, want %v", key, got, want)
		}
	}

	h := zpMetricsNewDashboard(24)
	for _, v := range []float64{10, 20, 30, 40, 50} {
		val := v
		name := "response_compression_ratio"
		h.RecordMetric(&name, &val, nil, nil, nil)
	}
	hs := h.GetMetricSummary("response_compression_ratio", 60)
	zpMetricsTestWantKeys(t, hs, []string{"name", "type", "description", "unit", "data_points", "duration_minutes",
		"latest_value", "first_timestamp", "last_timestamp", "min_value", "max_value", "avg_value", "median_value",
		"p50", "p90", "p95", "p99"})
	for key, want := range map[string]any{"p50": 30.0, "p90": 50.0, "p95": 50.0, "p99": 50.0} {
		if got := zpMetricsTestOut(t, hs, key); got != want {
			t.Fatalf("histogram[%s] = %v, want %v", key, got, want)
		}
	}

	// Counter rate uses explicit timestamps.
	c := zpMetricsNewDashboard(24)
	metric := zpMetricsTestMustGet(c.Metrics, t, "response_optimization_count")
	t0 := time.Date(2024, 1, 1, 12, 0, 0, 0, time.UTC)
	metric.DataPoints = []*MetricPoint{
		{Timestamp: t0, Value: 100},
		{Timestamp: t0.Add(10 * time.Second), Value: 160},
	}
	cs := c.GetMetricSummary("response_optimization_count", 10000000)
	zpMetricsTestWantKeys(t, cs, []string{"name", "type", "description", "unit", "data_points", "duration_minutes",
		"latest_value", "first_timestamp", "last_timestamp", "rate_per_second"})
	if got := zpMetricsTestOut(t, cs, "rate_per_second"); got != 6.0 {
		t.Fatalf("rate = %v, want 6.0", got)
	}

	// Unknown metric and the no-data shape.
	if d.GetMetricSummary("nope", 60) != nil {
		t.Fatal("unknown metric should return nil")
	}
	nd := d.GetMetricSummary("cache_size", 60)
	zpMetricsTestWantKeys(t, nd, []string{"name", "type", "description", "unit", "no_data"})
	if got := zpMetricsTestOut(t, nd, "no_data"); got != true {
		t.Fatalf("no_data = %v", got)
	}
}

func TestMetricsDashboard_AggregateMetrics(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	for i := 100; i < 200; i += 10 {
		v := float64(i)
		d.RecordMetric(nil, &v, nil, &tm, nil)
	}
	cases := map[AggregationType]float64{
		AggregationTypeAverage: 145.0,
		AggregationTypeSum:     1450.0,
		AggregationTypeCount:   10.0,
		AggregationTypeMax:     190.0,
		AggregationTypeMin:     100.0,
	}
	for agg, want := range cases {
		if got := d.AggregateMetrics(tm, agg); got != want {
			t.Fatalf("aggregate %s = %v, want %v", agg, got, want)
		}
	}
	if got := zpMetricsNewDashboard(24).AggregateMetrics(tm, AggregationTypeAverage); got != 0 {
		t.Fatalf("empty aggregate = %v, want 0", got)
	}
}

func TestMetricsDashboard_CalculateTrend(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	for _, v := range []float64{10, 30, 20} {
		val := v
		d.RecordMetric(nil, &val, nil, &tm, nil)
	}
	tr := d.CalculateTrend(tm, TimeRange{Start: time.Date(2020, 1, 1, 0, 0, 0, 0, time.UTC), End: time.Date(2030, 1, 1, 0, 0, 0, 0, time.UTC)})
	zpMetricsTestWantKeys(t, tr, []string{"direction", "change_percentage", "slope"})
	if got := zpMetricsTestOut(t, tr, "direction"); got != "up" {
		t.Fatalf("direction = %v", got)
	}
	if got := zpMetricsTestOut(t, tr, "change_percentage"); got != 100.0 {
		t.Fatalf("change = %v", got)
	}
	if got := zpMetricsTestOut(t, tr, "slope"); got != 3.3333333333333335 {
		t.Fatalf("slope = %v", got)
	}
	flat := d.CalculateTrend(tm, TimeRange{Start: time.Date(2020, 1, 1, 0, 0, 0, 0, time.UTC), End: time.Date(2020, 2, 1, 0, 0, 0, 0, time.UTC)})
	if got := zpMetricsTestOut(t, flat, "direction"); got != "flat" {
		t.Fatalf("flat direction = %v", got)
	}
	if _, ok := zpMetricsTestOut(t, flat, "change_percentage").(int); !ok {
		t.Fatalf("flat change should be int 0, got %T", zpMetricsTestOut(t, flat, "change_percentage"))
	}
	if _, ok := zpMetricsTestOut(t, flat, "slope").(int); !ok {
		t.Fatalf("flat slope should be int 0, got %T", zpMetricsTestOut(t, flat, "slope"))
	}
}

func TestMetricsDashboard_GetMetricsWithTimeRange(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	t0 := time.Date(2024, 1, 1, 12, 0, 0, 0, time.UTC)
	v1, v2 := 1.0, 2.0
	d.RecordMetric(nil, &v1, nil, &tm, &t0)
	later := t0.Add(time.Hour)
	d.RecordMetric(nil, &v2, nil, &tm, &later)
	got := d.GetMetrics(tm, &TimeRange{Start: t0, End: t0.Add(30 * time.Minute)})
	if len(got) != 1 || zpMetricsTestOut(t, got[0], "value") != 1.0 {
		t.Fatalf("filtered = %v", got)
	}
	if all := d.GetMetrics(tm, nil); len(all) != 2 {
		t.Fatalf("unfiltered len = %d, want 2", len(all))
	}
}

func TestMetricsDashboard_CalculatePercentile(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	for _, v := range []float64{100, 200, 300, 400} {
		val := v
		d.RecordMetric(nil, &val, nil, &tm, nil)
	}
	if got := d.CalculatePercentile(tm, 50); got != 250.0 {
		t.Fatalf("p50 even = %v, want 250", got)
	}
	d2 := zpMetricsNewDashboard(24)
	for _, v := range []float64{100, 200, 300, 400, 500} {
		val := v
		d2.RecordMetric(nil, &val, nil, &tm, nil)
	}
	if got := d2.CalculatePercentile(tm, 50); got != 300.0 {
		t.Fatalf("p50 odd = %v, want 300", got)
	}
	d3 := zpMetricsNewDashboard(24)
	for i := 100; i < 200; i += 10 {
		v := float64(i)
		d3.RecordMetric(nil, &v, nil, &tm, nil)
	}
	if got := d3.CalculatePercentile(tm, 95); got != 950.0 {
		t.Fatalf("p95 n=10 = %v, want 950", got)
	}
	if got := d3.CalculatePercentile(tm, 90); got != 180.0 {
		t.Fatalf("p90 n=10 = %v, want 180", got)
	}
	if got := zpMetricsNewDashboard(24).CalculatePercentile(tm, 50); got != 0 {
		t.Fatalf("empty percentile = %v, want 0", got)
	}
}

func TestMetricsDashboard_CalculateCorrelation(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	for _, pair := range [][2]float64{{1, 2}, {2, 4}, {3, 6}} {
		a, b := pair[0], pair[1]
		t1, t2 := MetricTypeTaskCompletion, MetricTypeAgentUtilization
		d.RecordMetric(nil, &a, nil, &t1, nil)
		d.RecordMetric(nil, &b, nil, &t2, nil)
	}
	got := d.CalculateCorrelation(MetricTypeTaskCompletion, MetricTypeAgentUtilization)
	if got != 0.9999999999999998 {
		t.Fatalf("correlation = %v, want 0.9999999999999998", got)
	}
	if got := d.CalculateCorrelation(MetricTypeTaskCompletion, MetricTypeGauge); got != 0 {
		t.Fatalf("mismatched correlation = %v, want 0", got)
	}
}

func TestMetricsDashboard_AlertChecks(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	name := "response_compression_ratio"
	for _, v := range []float64{10, 20, 30, 40, 50} {
		val := v
		d.RecordMetric(&name, &val, nil, nil, nil)
	}
	if len(d.Alerts) != 3 {
		t.Fatalf("alerts = %d, want 3 (values 10,20,30)", len(d.Alerts))
	}
	first, _ := d.Alerts[0].(*entities.OrderedMap[any])
	zpMetricsTestWantKeys(t, first, []string{"timestamp", "level", "message", "metric", "value"})
	if got := zpMetricsTestOut(t, first, "level"); got != "warning" {
		t.Fatalf("level = %v", got)
	}
	if got := zpMetricsTestOut(t, first, "message"); got != "Low compression ratio" {
		t.Fatalf("message = %v", got)
	}
	if got := zpMetricsTestOut(t, first, "value"); got != 10.0 {
		t.Fatalf("value = %v", got)
	}

	mem := "memory_usage"
	high := 600.0
	d.RecordMetric(&mem, &high, nil, nil, nil)
	last, _ := d.Alerts[len(d.Alerts)-1].(*entities.OrderedMap[any])
	if got := zpMetricsTestOut(t, last, "level"); got != "critical" {
		t.Fatalf("memory level = %v", got)
	}
	if got := zpMetricsTestOut(t, last, "message"); got != "High memory usage" {
		t.Fatalf("memory message = %v", got)
	}
}

func TestMetricsDashboard_SetAlertAndCheckAlerts(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	v := 10.0
	d.RecordMetric(nil, &v, nil, &tm, nil)
	greater := zpMetricsNewAlert("a1", "gt", tm, "greater_than", 5.0)
	less := zpMetricsNewAlert("a2", "lt", tm, "less_than", 5.0)
	d.SetAlert(greater)
	d.SetAlert(less)
	triggered := d.CheckAlerts()
	if len(triggered) != 1 || triggered[0].ID != "a1" {
		t.Fatalf("triggered = %v", triggered)
	}
	// Disabled alerts are skipped.
	dis := zpMetricsNewAlert("a3", "dis", tm, "greater_than", 5.0)
	dis.Enabled = false
	d.SetAlert(dis)
	if got := d.CheckAlerts(); len(got) != 1 || got[0].ID != "a1" {
		t.Fatalf("with disabled triggered = %v", got)
	}
}

func TestMetricsDashboard_GetDashboardData(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	dash := d.GetDashboardData(60)
	zpMetricsTestWantKeys(t, dash, []string{"timestamp", "duration_minutes", "metrics", "summary", "alerts", "health_status"})
	metricsAny, _ := dash.Get("metrics")
	metricsMap, ok := metricsAny.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("metrics type = %T", metricsAny)
	}
	if len(metricsMap.Keys()) != 11 {
		t.Fatalf("dashboard metrics = %d, want 11", len(metricsMap.Keys()))
	}
	summaryAny, _ := dash.Get("summary")
	summary, _ := summaryAny.(*entities.OrderedMap[any])
	zpMetricsTestWantKeys(t, summary, []string{"optimization_performance", "system_performance", "error_rates"})
	healthAny, _ := dash.Get("health_status")
	health, _ := healthAny.(*entities.OrderedMap[any])
	zpMetricsTestWantKeys(t, health, []string{"status", "issues", "score"})
	if got := zpMetricsTestOut(t, health, "status"); got != "healthy" {
		t.Fatalf("health = %v", got)
	}
	if got := zpMetricsTestOut(t, health, "score"); got != 100 {
		t.Fatalf("score = %v", got)
	}

	// Degraded health: a low compression average.
	name := "response_compression_ratio"
	v := 10.0
	d.RecordMetric(&name, &v, nil, nil, nil)
	h2 := d.getHealthStatus()
	if got := zpMetricsTestOut(t, h2, "status"); got != "warning" {
		t.Fatalf("degraded status = %v, want warning", got)
	}
	if got := zpMetricsTestOut(t, h2, "score"); got != 80 {
		t.Fatalf("degraded score = %v, want 80", got)
	}
}

func TestMetricsDashboard_PerformanceSummary(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	name := "response_compression_ratio"
	for _, v := range []float64{10, 20, 30, 40} {
		val := v
		d.RecordMetric(&name, &val, nil, nil, nil)
	}
	d.RecordMetric(zpMetricsTestName("context_field_reduction"), zpMetricsTestFloat(50), nil, nil, nil)
	d.RecordMetric(zpMetricsTestName("api_response_time"), zpMetricsTestFloat(80), nil, nil, nil)
	d.RecordMetric(zpMetricsTestName("cache_hit_rate"), zpMetricsTestFloat(70), nil, nil, nil)
	summary := d.getPerformanceSummary(60)
	optAny, _ := summary.Get("optimization_performance")
	opt, _ := optAny.(*entities.OrderedMap[any])
	zpMetricsTestWantKeys(t, opt, []string{"avg_compression_ratio", "p95_compression_ratio", "avg_field_reduction"})
	if got := zpMetricsTestOut(t, opt, "avg_compression_ratio"); got != 25.0 {
		t.Fatalf("avg compression = %v", got)
	}
	if got := zpMetricsTestOut(t, opt, "p95_compression_ratio"); got != 40.0 {
		t.Fatalf("p95 compression = %v", got)
	}
	sysAny, _ := summary.Get("system_performance")
	sys, _ := sysAny.(*entities.OrderedMap[any])
	zpMetricsTestWantKeys(t, sys, []string{"avg_response_time_ms", "p95_response_time_ms", "cache_hit_rate"})
	if got := zpMetricsTestOut(t, sys, "cache_hit_rate"); got != 70.0 {
		t.Fatalf("cache hit = %v", got)
	}
}

func zpMetricsTestName(s string) *string    { return &s }
func zpMetricsTestFloat(f float64) *float64 { return &f }

func TestMetricsDashboard_CreateSnapshot(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	d.AddWidget(zpMetricsNewWidget("w1", "T", MetricTypeGauge))
	tm := MetricTypeGauge
	v := 1.0
	d.RecordMetric(nil, &v, nil, &tm, nil)
	snap := d.CreateSnapshot()
	zpMetricsTestWantKeys(t, snap, []string{"timestamp", "widgets", "metrics_summary"})
	widgetsAny, _ := snap.Get("widgets")
	widgets, _ := widgetsAny.([]any)
	if len(widgets) != 1 {
		t.Fatalf("widgets len = %d", len(widgets))
	}
	w0, _ := widgets[0].(*entities.OrderedMap[any])
	zpMetricsTestWantKeys(t, w0, []string{"id", "title"})
	msAny, _ := snap.Get("metrics_summary")
	ms, _ := msAny.(*entities.OrderedMap[any])
	if got := zpMetricsTestOut(t, ms, "total_metrics"); got != 1 {
		t.Fatalf("total_metrics = %v", got)
	}
}

func TestMetricsDashboard_ExportMetricsCSVAndJSON(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	ts := time.Date(2024, 1, 1, 12, 0, 0, 500000000, time.UTC)
	v := 7.5
	d.RecordMetric(nil, &v, nil, &tm, &ts)
	csv := d.ExportMetrics("csv", []MetricType{tm})
	wantCSV := "timestamp,value,type\n2024-01-01T12:00:00.500000,7.5,task_completion"
	if csv != wantCSV {
		t.Fatalf("csv = %q, want %q", csv, wantCSV)
	}
	js := d.ExportMetrics("json", []MetricType{tm})
	wantJSON := `[{"type": "task_completion", "value": 7.5, "timestamp": "2024-01-01 12:00:00.500000", "tags": {}}]`
	if js != wantJSON {
		t.Fatalf("json = %q, want %q", js, wantJSON)
	}
	if got := d.ExportMetrics("xml", []MetricType{tm}); got != "" {
		t.Fatalf("unsupported format = %q, want empty", got)
	}
}

func TestMetricsDashboard_ExportMetricsOldPrometheusAndError(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	name := "response_compression_ratio"
	for _, v := range []float64{10, 20, 30, 40} {
		val := v
		d.RecordMetric(&name, &val, nil, nil, nil)
	}
	mem := "memory_usage"
	high := 600.0
	d.RecordMetric(&mem, &high, nil, nil, nil)
	got, err := d.ExportMetricsOld("prometheus", 60)
	if err != nil {
		t.Fatalf("prometheus err = %v", err)
	}
	want := "# HELP response_compression_ratio Response compression ratio percentage\n" +
		"# TYPE response_compression_ratio histogram\n" +
		"response_compression_ratio 40.0\n" +
		"response_compression_ratio_p50 30.0\n" +
		"response_compression_ratio_p90 40.0\n" +
		"response_compression_ratio_p95 40.0\n" +
		"response_compression_ratio_p99 40.0\n" +
		"# HELP memory_usage Memory usage\n" +
		"# TYPE memory_usage gauge\n" +
		"memory_usage 600.0"
	if got != want {
		t.Fatalf("prometheus =\n%s\nwant\n%s", got, want)
	}
	if _, err := d.ExportMetricsOld("xml", 60); err == nil {
		t.Fatal("expected ValueError")
	} else {
		var ve *value_objects.ValueError
		if !errors.As(err, &ve) || ve.Msg != "Unsupported format: xml" {
			t.Fatalf("error = %v", err)
		}
	}
}

func TestMetricsDashboard_LoadTemplate(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	d.LoadTemplate("unknown")
	if len(d.Widgets) != 0 {
		t.Fatalf("unknown template changed widgets: %v", d.Widgets)
	}
	d.LoadTemplate("project_overview")
	want := []struct {
		id, title, visualization string
		metricType               MetricType
	}{
		{"w1", "Task Completion Rate", "gauge", MetricTypeTaskCompletion},
		{"w2", "Average Response Time", "line_chart", MetricTypeAPIResponseTime},
		{"w3", "Active Agents", "bar_chart", MetricTypeAgentUtilization},
	}
	if len(d.Widgets) != 3 {
		t.Fatalf("widgets = %d, want 3", len(d.Widgets))
	}
	for i, w := range want {
		if d.Widgets[i].ID != w.id || d.Widgets[i].Title != w.title || d.Widgets[i].Visualization != w.visualization || d.Widgets[i].MetricType != w.metricType {
			t.Fatalf("widget %d = %+v", i, d.Widgets[i])
		}
	}
}

func TestMetricsDashboard_CustomMetric(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	d.DefineCustomMetric("score", "component sum", func(m map[string]float64) float64 {
		return m["a"] + m["b"]
	})
	na, nb := "a", "b"
	va, vb := 3.0, 4.0
	d.RecordMetric(&na, &va, nil, nil, nil)
	d.RecordMetric(&nb, &vb, nil, nil, nil)
	if got := d.CalculateCustomMetric("score"); got != 7.0 {
		t.Fatalf("custom = %v, want 7", got)
	}
	if got := d.CalculateCustomMetric("missing"); got != 0 {
		t.Fatalf("missing custom = %v, want 0", got)
	}
}

func TestMetricsDashboard_DetectAnomalies(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	for i := 0; i < 19; i++ {
		v := 100.0
		d.RecordMetric(nil, &v, nil, &tm, nil)
	}
	v := 115.0
	d.RecordMetric(nil, &v, nil, &tm, nil)
	anomalies := d.DetectAnomalies(tm, "zscore", 2.0)
	if len(anomalies) != 1 {
		t.Fatalf("anomalies = %d, want 1", len(anomalies))
	}
	zpMetricsTestWantKeys(t, anomalies[0], []string{"value", "timestamp"})
	if got := zpMetricsTestOut(t, anomalies[0], "value"); got != 115.0 {
		t.Fatalf("anomaly value = %v", got)
	}
	if _, ok := zpMetricsTestOut(t, anomalies[0], "timestamp").(time.Time); !ok {
		t.Fatalf("anomaly timestamp type = %T, want time.Time", zpMetricsTestOut(t, anomalies[0], "timestamp"))
	}
	short := zpMetricsNewDashboard(24)
	few := 1.0
	short.RecordMetric(nil, &few, nil, &tm, nil)
	if got := short.DetectAnomalies(tm, "zscore", 2.0); len(got) != 0 {
		t.Fatalf("short anomalies = %v, want empty", got)
	}
}

func TestMetricsDashboard_ForecastMetric(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	tm := MetricTypeTaskCompletion
	for _, v := range []float64{10, 20, 30} {
		val := v
		d.RecordMetric(nil, &val, nil, &tm, nil)
	}
	forecast := d.ForecastMetric(tm, 2, "linear")
	if len(forecast) != 2 {
		t.Fatalf("forecast = %d, want 2", len(forecast))
	}
	zpMetricsTestWantKeys(t, forecast[0], []string{"timestamp", "predicted_value", "confidence_interval"})
	if got := zpMetricsTestOut(t, forecast[0], "predicted_value"); got != 40.0 {
		t.Fatalf("predicted[0] = %v, want 40", got)
	}
	if got := zpMetricsTestOut(t, forecast[1], "predicted_value"); got != 50.0 {
		t.Fatalf("predicted[1] = %v, want 50", got)
	}
	ci, _ := zpMetricsTestOut(t, forecast[0], "confidence_interval").([]any)
	if len(ci) != 2 || ci[0] != 36.0 || ci[1] != 44.0 {
		t.Fatalf("ci[0] = %v, want [36 44]", ci)
	}
	ci1, _ := zpMetricsTestOut(t, forecast[1], "confidence_interval").([]any)
	if ci1[1] != 55.00000000000001 {
		t.Fatalf("ci[1][1] = %v, want 55.00000000000001", ci1[1])
	}
	if _, ok := zpMetricsTestOut(t, forecast[0], "timestamp").(time.Time); !ok {
		t.Fatalf("forecast timestamp type = %T", zpMetricsTestOut(t, forecast[0], "timestamp"))
	}
	short := zpMetricsNewDashboard(24)
	v := 1.0
	short.RecordMetric(nil, &v, nil, &tm, nil)
	if got := short.ForecastMetric(tm, 2, "linear"); len(got) != 0 {
		t.Fatalf("short forecast = %v, want empty", got)
	}
}

func TestMetricsDashboard_GenerateShareLink(t *testing.T) {
	d := zpMetricsNewDashboard(24)
	link := d.GenerateShareLink(time.Hour, true)
	zpMetricsTestWantKeys(t, link, []string{"token", "expires_at", "read_only"})
	token, _ := zpMetricsTestOut(t, link, "token").(string)
	if len(token) != 36 {
		t.Fatalf("token = %q, want a uuid4 string", token)
	}
	if got := zpMetricsTestOut(t, link, "read_only"); got != true {
		t.Fatalf("read_only = %v", got)
	}
	if _, ok := zpMetricsTestOut(t, link, "expires_at").(string); !ok {
		t.Fatalf("expires_at type = %T", zpMetricsTestOut(t, link, "expires_at"))
	}
}

func TestMetricsDashboard_ResetMetricsAndCleanup(t *testing.T) {
	d := zpMetricsNewDashboard(1)
	name := "cache_size"
	v := 5.0
	d.RecordMetric(&name, &v, nil, nil, nil)
	tm := MetricTypeGauge
	d.RecordMetric(nil, &v, nil, &tm, nil)
	d.ResetMetrics()
	if len(zpMetricsTestMustGet(d.Metrics, t, name).DataPoints) != 0 {
		t.Fatal("metric data points not cleared")
	}
	if len(d.Alerts) != 0 {
		t.Fatalf("alerts not cleared: %v", d.Alerts)
	}
	if d.perfWindows["1m"].Len() != 0 || d.perfWindows["1h"].Len() != 0 || d.perfWindows["24h"].Len() != 0 {
		t.Fatal("performance windows not reset")
	}
	if len(d.MetricsStore) != 1 {
		t.Fatalf("metrics_store should survive reset, len = %d", len(d.MetricsStore))
	}

	// Periodic cleanup drops points older than retention_hours.
	clean := zpMetricsNewDashboard(1)
	metric := zpMetricsTestMustGet(clean.Metrics, t, "cache_size")
	now := time.Now()
	metric.DataPoints = []*MetricPoint{
		{Timestamp: now.Add(-2 * time.Hour), Value: 1},
		{Timestamp: now, Value: 2},
	}
	clean.lastCleanup = now.Add(-301 * time.Second)
	clean.periodicCleanup()
	if len(metric.DataPoints) != 1 || metric.DataPoints[0].Value != 2 {
		t.Fatalf("cleanup kept %v", metric.DataPoints)
	}
	if time.Since(clean.lastCleanup) > time.Second {
		t.Fatal("lastCleanup not updated")
	}
}
