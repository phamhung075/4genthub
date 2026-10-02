package workers_test

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/workers"
)

type fakeProvider struct{ summary *entities.OrderedMap[any] }

func (f *fakeProvider) GetOptimizationSummary(float64) *entities.OrderedMap[any] { return f.summary }

func om(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func getMap(m *entities.OrderedMap[any], k string) *entities.OrderedMap[any] {
	v, _ := m.Get(k)
	om, _ := v.(*entities.OrderedMap[any])
	return om
}

func pinNow(t *testing.T, at time.Time) {
	t.Helper()
	prev := workers.Now
	workers.Now = func() time.Time { return at }
	t.Cleanup(func() { workers.Now = prev })
}

func baseSummary() *entities.OrderedMap[any] {
	return om(
		"optimization_performance", om(
			"total_optimizations", 3,
			"avg_compression_ratio", 50.0,
			"min_compression_ratio", 40.0,
			"max_compression_ratio", 60.0,
		),
		"system_health", om("health_score", nil),
		"alerts", om("total_alerts", 0, "critical_alerts", 0, "warning_alerts", 0, "recent_alerts", []*entities.OrderedMap[any]{}),
		"recommendations", []string{},
	)
}

func TestReportConfigDefaults(t *testing.T) {
	c := workers.NewReportConfig()
	if c.EmailSMTPServer != "localhost" || c.EmailSMTPPort != 587 {
		t.Fatalf("smtp = %s:%d", c.EmailSMTPServer, c.EmailSMTPPort)
	}
	if c.OutputDirectory != "/tmp/mcp_reports" || !c.FileOutputEnabled || c.EmailEnabled {
		t.Fatalf("output = %+v", c)
	}
	if c.AlertThresholds["compression_ratio_min"] != 30.0 || c.AlertThresholds["system_health_min"] != 70.0 {
		t.Fatalf("thresholds = %v", c.AlertThresholds)
	}
	if c.EmailRecipients == nil {
		t.Fatal("recipients nil")
	}
}

func TestGenerateDailyReport(t *testing.T) {
	pinNow(t, time.Date(2024, 1, 1, 10, 0, 0, 0, time.UTC))
	dir := t.TempDir()
	cfg := workers.NewReportConfig()
	cfg.OutputDirectory = dir
	cfg.FileOutputEnabled = true

	r := workers.NewMetricsReporter(&fakeProvider{summary: baseSummary()}, cfg)
	rep := r.GenerateDailyReport(nil)
	if v, _ := rep.Get("report_type"); v != "daily" {
		t.Fatalf("report_type = %v", v)
	}
	if v, _ := rep.Get("report_date"); v != "2024-01-01" {
		t.Fatalf("report_date = %v", v)
	}
	if v, _ := rep.Get("file_saved"); v != true {
		t.Fatalf("file_saved = %v", v)
	}
	if _, err := os.Stat(filepath.Join(dir, "daily_report_20240101.html")); err != nil {
		t.Fatalf("report file: %v", err)
	}
}

func TestGenerateWeeklyReportTrends(t *testing.T) {
	pinNow(t, time.Date(2024, 1, 3, 10, 0, 0, 0, time.UTC)) // Wednesday
	dir := t.TempDir()
	cfg := workers.NewReportConfig()
	cfg.OutputDirectory = dir
	cfg.FileOutputEnabled = false

	r := workers.NewMetricsReporter(&fakeProvider{summary: baseSummary()}, cfg)
	rep, err := r.GenerateWeeklyReport(nil)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := rep.Get("week_start"); v != "2024-01-01" {
		t.Fatalf("week_start = %v", v)
	}
	if v, _ := rep.Get("week_end"); v != "2024-01-07" {
		t.Fatalf("week_end = %v", v)
	}
	trends := getMap(rep, "trends")
	cr := getMap(trends, "compression_ratio")
	if v, _ := cr.Get("current"); v != 50.0 {
		t.Fatalf("current = %v", v)
	}
	if v, _ := cr.Get("previous"); v != 25.0 {
		t.Fatalf("previous = %v", v)
	}
	if v, _ := cr.Get("trend"); v != "up" {
		t.Fatalf("trend = %v", v)
	}
	if v, _ := cr.Get("change_percent"); v != 100.0 {
		t.Fatalf("change = %v", v)
	}
	sh := getMap(trends, "system_health")
	if v, _ := sh.Get("current"); v != 0.0 {
		t.Fatalf("health current = %v", v)
	}
	if v, _ := sh.Get("trend"); v != "down" {
		t.Fatalf("health trend = %v", v)
	}
	if v, _ := sh.Get("change_percent"); v != -100.0 {
		t.Fatalf("health change = %v", v)
	}
}

func TestGenerateWeeklyReportCacheDataError(t *testing.T) {
	pinNow(t, time.Date(2024, 1, 3, 10, 0, 0, 0, time.UTC))
	summary := baseSummary()
	summary.Set("performance_metrics", om("cache_hit_rates", om("global", "not-a-dict")))
	cfg := workers.NewReportConfig()
	cfg.OutputDirectory = t.TempDir()
	cfg.FileOutputEnabled = false
	r := workers.NewMetricsReporter(&fakeProvider{summary: summary}, cfg)
	if _, err := r.GenerateWeeklyReport(nil); err == nil {
		t.Fatal("expected error for non-dict cache data")
	}
}

func TestGenerateMonthlyRoiMetrics(t *testing.T) {
	pinNow(t, time.Date(2024, 1, 15, 10, 0, 0, 0, time.UTC))
	summary := om(
		"optimization_performance", om("total_optimizations", 10, "avg_compression_ratio", 50.0),
	)
	dir := t.TempDir()
	cfg := workers.NewReportConfig()
	cfg.OutputDirectory = dir
	cfg.FileOutputEnabled = true
	r := workers.NewMetricsReporter(&fakeProvider{summary: summary}, cfg)

	rep, err := r.GenerateMonthlyRoiReport(nil)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := rep.Get("month"); v != "January 2024" {
		t.Fatalf("month = %v", v)
	}
	roi := getMap(rep, "roi_analysis")
	if v, _ := roi.Get("bytes_saved_estimate"); v != 25000.0 {
		t.Fatalf("bytes = %v", v)
	}
	if v, _ := roi.Get("estimated_cost_savings"); v != 2.5 {
		t.Fatalf("cost = %v", v)
	}
	if v, _ := roi.Get("efficiency_improvement"); v != 50.0 {
		t.Fatalf("efficiency = %v", v)
	}
	if v, _ := roi.Get("processing_time_performance"); v != 100.0 {
		t.Fatalf("processing = %v", v)
	}
	if _, err := os.Stat(filepath.Join(dir, "monthly_roi_202401.json")); err != nil {
		t.Fatalf("roi file: %v", err)
	}
}

func TestWaitHelpers(t *testing.T) {
	pinNow(t, time.Date(2024, 1, 1, 8, 0, 0, 0, time.UTC)) // Monday 08:00
	r := &workers.MetricsReporter{Config: workers.NewReportConfig()}
	if got := r.WaitUntilTime("09:00"); got != 3600 {
		t.Fatalf("wait time = %v", got)
	}
	if got := r.WaitUntilWeekday("monday"); got != float64(7*24*3600+3600) {
		t.Fatalf("wait weekday = %v", got)
	}
	if got := r.WaitUntilMonthday(15); got != float64(14*24*3600+3600) {
		t.Fatalf("wait monthday = %v", got)
	}
}
