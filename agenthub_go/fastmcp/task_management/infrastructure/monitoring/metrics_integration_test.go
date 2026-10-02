package monitoring_test

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/monitoring"
	"agenthub/fastmcp/task_management/infrastructure/workers"
)

func resetGlobals() {
	monitoring.StopOptimizationMonitoring()
	workers.StopAutomatedReporting()
}

func TestOptimizationContextRecords(t *testing.T) {
	resetGlobals()
	pinClock(t, time.Unix(1700000000, 0).UTC())

	data, closeFn := monitoring.OptimizationContext("MINIMAL", "response_format", nil)
	if v, _ := data.Get("parse_success"); v != true {
		t.Fatalf("parse_success = %v", v)
	}
	data.Set("original_size", 1000)
	data.Set("optimized_size", 500)
	closeFn(nil)

	c := monitoring.GetGlobalOptimizationCollector()
	s := c.GetOptimizationSummary(1)
	if noData, _ := s.Get("no_data"); noData != nil {
		t.Fatalf("no_data = %v", s)
	}
	optPerf := mustMap(t, s, "optimization_performance")
	if got, _ := optPerf.Get("total_optimizations"); got != 1 {
		t.Fatalf("total = %v", got)
	}
	if got, _ := optPerf.Get("avg_compression_ratio"); !approx(got.(float64), 50) {
		t.Fatalf("avg = %v", got)
	}
	resetGlobals()
}

func TestOptimizationContextError(t *testing.T) {
	resetGlobals()
	pinClock(t, time.Unix(1700000000, 0).UTC())

	data, closeFn := monitoring.OptimizationContext("MINIMAL", "response_format", nil)
	_ = data
	closeFn(&valueErr{"bad parse"})

	c := monitoring.GetGlobalOptimizationCollector()
	c.FlushMetrics()
	if got := c.GetMetricSummary("ai_parse_errors", nil); got == nil || got.Count != 1 {
		t.Fatalf("ai_parse_errors = %v", got)
	}
	resetGlobals()
}

func TestResponseOptimizationTrackerRecords(t *testing.T) {
	resetGlobals()
	pinClock(t, time.Unix(1700000000, 0).UTC())

	data, closeFn := monitoring.ResponseOptimizationTracker("MINIMAL", 2000, "response_format", nil)
	if v, _ := data.Get("optimized_size"); v != 2000 {
		t.Fatalf("optimized_size = %v", v)
	}
	data.Set("optimized_size", 1000)
	closeFn(nil)

	c := monitoring.GetGlobalOptimizationCollector()
	c.FlushMetrics()
	got := c.GetMetricSummary("response_compression_ratio", nil)
	if got == nil || !approx(got.AvgValue, 50) {
		t.Fatalf("compression = %v", got)
	}
	resetGlobals()
}

func TestMetricsCollectionServiceLifecycle(t *testing.T) {
	resetGlobals()
	dir := t.TempDir()
	svc := monitoring.NewMetricsCollectionService()
	if _, err := svc.GenerateOnDemandReport("daily"); err == nil {
		t.Fatal("expected error without reporter")
	}

	cfg := workers.NewReportConfig()
	cfg.OutputDirectory = dir
	cfg.FileOutputEnabled = false
	svc.StartMetricsCollection(false, cfg)
	if !svc.Started {
		t.Fatal("service not started")
	}
	svc.StartMetricsCollection(false, cfg) // idempotent
	svc.StopMetricsCollection()
	if svc.Started {
		t.Fatal("service still started")
	}

	unknown, err := svc.GenerateOnDemandReport("hourly")
	if err == nil {
		t.Fatal("expected unknown report type error")
	}
	_ = unknown
	resetGlobals()
}

func TestInitializeMetricsSystem(t *testing.T) {
	resetGlobals()
	dir := t.TempDir()
	email := entities.NewOrderedMap[any]()
	email.Set("enabled", false)
	email.Set("smtp_server", "mail.example.com")
	email.Set("smtp_port", 2525)
	email.Set("recipients", []any{"a@example.com", "b@example.com"})

	svc, err := monitoring.InitializeMetricsSystem(true, &dir, email)
	if err != nil {
		t.Fatal(err)
	}
	if svc.Reporter == nil {
		t.Fatal("reporter not configured")
	}
	if svc.Reporter.Config.OutputDirectory != dir {
		t.Fatalf("output dir = %q", svc.Reporter.Config.OutputDirectory)
	}
	if svc.Reporter.Config.EmailSMTPServer != "mail.example.com" || svc.Reporter.Config.EmailSMTPPort != 2525 {
		t.Fatalf("email config = %+v", svc.Reporter.Config)
	}
	if len(svc.Reporter.Config.EmailRecipients) != 2 {
		t.Fatalf("recipients = %v", svc.Reporter.Config.EmailRecipients)
	}
	svc.StopMetricsCollection()
	resetGlobals()
}

type valueErr struct{ msg string }

func (e *valueErr) Error() string { return e.msg }
