package services_test

import (
	"os"
	"path/filepath"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/services"
)

func TestPerformanceSnapshotFields(t *testing.T) {
	s := services.NewPerformanceSnapshot(1.5, 0.9, 0.1, 2.5, 100.0, 4.0, 7, 3)
	if s.Timestamp != 1.5 || s.HitRate != 0.9 || s.MissRate != 0.1 ||
		s.AverageResponseTimeMS != 2.5 || s.OperationsPerSecond != 100.0 ||
		s.MemoryUsageMB != 4.0 || s.CacheSize != 7 || s.EvictionCount != 3 {
		t.Fatalf("snapshot = %+v", s)
	}
}

func TestBenchmarkConfigDefaults(t *testing.T) {
	c := services.NewBenchmarkConfig()
	if c.NumOperations != 1000 || c.ConcurrentOperations != 10 || c.DataSizeBytes != 1024 {
		t.Errorf("config = %+v", c)
	}
	if c.TestDurationSeconds != 60 || c.WarmupOperations != 100 {
		t.Errorf("config = %+v", c)
	}
	if !c.IncludeStressTest || !c.IncludeMemoryTest || !c.IncludeConcurrencyTest {
		t.Errorf("config = %+v", c)
	}
}

func TestBenchmarkResultDefaults(t *testing.T) {
	r := services.NewBenchmarkResult(*services.NewBenchmarkConfig(), 1.0, 2.0)
	if r.StartTime != 1.0 || r.EndTime != 2.0 {
		t.Errorf("times = %v/%v", r.StartTime, r.EndTime)
	}
	if r.TotalOperations != 0 || r.SuccessfulOperations != 0 || r.FailedOperations != 0 {
		t.Errorf("counts = %+v", r)
	}
	if r.OperationsPerSecond != 0.0 || r.AverageResponseTimeMS != 0.0 || r.P50ResponseTimeMS != 0.0 {
		t.Errorf("metrics = %+v", r)
	}
	if r.Recommendations == nil || len(r.Recommendations) != 0 {
		t.Errorf("Recommendations = %#v, want non-nil empty", r.Recommendations)
	}
}

func TestCacheBenchmarkRunBasic(t *testing.T) {
	mgr := services.NewEnhancedRuleCacheManager(memConfig())
	benchmark := services.NewCacheBenchmark(mgr)

	results, err := benchmark.RunBasicBenchmark(3)
	if err != nil {
		t.Fatalf("RunBasicBenchmark error = %v", err)
	}

	configuration := orderedField(t, results, "configuration")
	if v, _ := configuration.Get("num_operations"); v != 3 {
		t.Errorf("num_operations = %v, want 3", v)
	}
	if v, _ := configuration.Get("data_size_per_item"); v != 1400 {
		t.Errorf("data_size_per_item = %v, want 1400", v)
	}

	performance := orderedField(t, results, "performance")
	if v, _ := performance.Get("total_operations"); v != 6 {
		t.Errorf("total_operations = %v, want 6", v)
	}
	if v, _ := performance.Get("put_success_rate"); v != 1.0 {
		t.Errorf("put_success_rate = %v, want 1.0", v)
	}
	if v, _ := performance.Get("get_success_rate"); v != 1.0 {
		t.Errorf("get_success_rate = %v, want 1.0", v)
	}

	cacheMetrics := orderedField(t, results, "cache_metrics")
	if v, _ := cacheMetrics.Get("final_cache_size"); v != 3 {
		t.Errorf("final_cache_size = %v, want 3", v)
	}
	if v, _ := cacheMetrics.Get("final_hit_rate"); v != 1.0 {
		t.Errorf("final_hit_rate = %v, want 1.0", v)
	}
	if v, _ := cacheMetrics.Get("memory_usage_mb"); v != 0.0 {
		t.Errorf("memory_usage_mb = %v, want 0.0 (no memory_size_bytes key)", v)
	}
	if _, ok := results.Get("recommendations"); !ok {
		t.Error("results missing recommendations")
	}

	metrics := mgr.GetPerformanceMetrics()
	levels := orderedField(t, metrics, "cache_levels")
	if v, _ := levels.Get("memory_entries"); v != 0 {
		t.Errorf("memory_entries after cleanup = %v, want 0", v)
	}
}

func TestPerformanceMonitorSummaryEmpty(t *testing.T) {
	mgr := services.NewEnhancedRuleCacheManager(memConfig())
	monitor := services.NewPerformanceMonitor(mgr, 1.0, 10)

	summary := monitor.GetPerformanceSummary(60)
	v, ok := summary.Get("error")
	if !ok || v != "No data available for specified time window" {
		t.Fatalf("summary = %#v", summary)
	}
}

func TestPerformanceMonitorExport(t *testing.T) {
	mgr := services.NewEnhancedRuleCacheManager(memConfig())
	monitor := services.NewPerformanceMonitor(mgr, 1.0, 10)

	path := filepath.Join(t.TempDir(), "perf.json")
	if !monitor.ExportPerformanceData(path, "json") {
		t.Fatal("ExportPerformanceData(json) = false")
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != "[]" {
		t.Errorf("exported data = %q, want %q", string(data), "[]")
	}

	badPath := filepath.Join(t.TempDir(), "perf.csv")
	if monitor.ExportPerformanceData(badPath, "csv") {
		t.Error("ExportPerformanceData(csv) = true, want false")
	}
	if _, err := os.Stat(badPath); err == nil {
		t.Error("unsupported export wrote a file")
	}
}

func TestPerformanceMonitorAlertCallbackRegistration(t *testing.T) {
	mgr := services.NewEnhancedRuleCacheManager(memConfig())
	monitor := services.NewPerformanceMonitor(mgr, 1.0, 10)

	called := 0
	monitor.AddAlertCallback(func(alert string, snapshot *services.PerformanceSnapshot) error {
		called++
		return nil
	})
	if called != 0 {
		t.Errorf("callback called before any alert: %d", called)
	}

	monitor.StartMonitoring()
	monitor.StopMonitoring()
}

func TestCacheManagerInterfaceSatisfied(t *testing.T) {
	var manager services.CacheManager = services.NewEnhancedRuleCacheManager(memConfig())
	if manager == nil {
		t.Fatal("nil CacheManager")
	}
	var _ *entities.OrderedMap[any] = manager.GetPerformanceMetrics()
}
