package services_test

import (
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/services"
)

func strPtr(s string) *string { return &s }

func memConfig() *services.CacheConfiguration {
	c := services.NewCacheConfiguration()
	c.DiskEnabled = false
	return c
}

func tempConfig(t *testing.T) *services.CacheConfiguration {
	t.Helper()
	c := services.NewCacheConfiguration()
	c.DiskCacheDir = strPtr(t.TempDir())
	return c
}

func freshEntry(content any, size int) *services.CacheEntry {
	now := float64(time.Now().UnixNano()) / 1e9
	return services.NewCacheEntry(content, now, now, 1, 3600.0, size, "h", nil, 1)
}

func orderedField(t *testing.T, m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	om, ok := v.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("key %q is %T, want *OrderedMap", key, v)
	}
	return om
}

func TestCacheEntryExpiryAgeFrequency(t *testing.T) {
	old := services.Now
	defer func() { services.Now = old }()

	base := time.Unix(1000, 0)
	services.Now = func() time.Time { return base }

	entry := services.NewCacheEntry("x", 1000.0, 1000.0, 5, 10.0, 1, "hash", nil, 1)
	if entry.Tags == nil || len(entry.Tags) != 0 {
		t.Fatalf("Tags = %#v, want non-nil empty", entry.Tags)
	}

	services.Now = func() time.Time { return base.Add(5 * time.Second) }
	if entry.IsExpired() {
		t.Error("entry (age 5, ttl 10) reported expired")
	}
	if got := entry.AgeSeconds(); got != 5.0 {
		t.Errorf("AgeSeconds() = %v, want 5", got)
	}
	if got := entry.AccessFrequency(); got != 50.0 {
		t.Errorf("AccessFrequency() = %v, want 50 (5 / max(5/3600, 0.1))", got)
	}

	services.Now = func() time.Time { return base.Add(11 * time.Second) }
	if !entry.IsExpired() {
		t.Error("entry (age 11, ttl 10) reported not expired")
	}
}

func TestPerformanceMetrics(t *testing.T) {
	m := services.NewPerformanceMetrics()
	if got := m.HitRate(); got != 0.0 {
		t.Errorf("HitRate() = %v, want 0", got)
	}
	if got := m.MissRate(); got != 1.0 {
		t.Errorf("MissRate() = %v, want 1", got)
	}
	if !isInf(m.MinResponseTime) {
		t.Errorf("MinResponseTime = %v, want +Inf", m.MinResponseTime)
	}

	m.TotalRequests = 4
	m.CacheHits = 3
	m.CacheMisses = 1
	if got := m.HitRate(); got != 0.75 {
		t.Errorf("HitRate() = %v, want 0.75", got)
	}
	if got := m.MissRate(); got != 0.25 {
		t.Errorf("MissRate() = %v, want 0.25", got)
	}

	m.UpdateResponseTime(10.0)
	m.UpdateResponseTime(20.0)
	if got := m.AverageResponseTime(); got != 7.5 {
		t.Errorf("AverageResponseTime() = %v, want 7.5", got)
	}
	if m.MinResponseTime != 10.0 || m.MaxResponseTime != 20.0 {
		t.Errorf("min/max = %v/%v, want 10/20", m.MinResponseTime, m.MaxResponseTime)
	}
	if got := m.AverageResponseTime(); got != m.TotalResponseTime/4 {
		t.Errorf("AverageResponseTime() = %v, want total/count", got)
	}
	if got := m.AverageResponseTime(); got == 0.0 {
		t.Error("AverageResponseTime() unexpectedly 0")
	}
}

func isInf(f float64) bool { return f > 1e308 }

func TestMemoryStorageBasics(t *testing.T) {
	cfg := memConfig()
	cfg.MemoryMaxSize = 100
	cfg.MemoryMaxMemoryMB = 512
	store := services.NewMemoryStorage(cfg)

	if store.Size() != 0 {
		t.Fatalf("fresh Size() = %d, want 0", store.Size())
	}
	entry := freshEntry("value", 5)
	if !store.Put("a", entry) {
		t.Fatal("Put returned false")
	}
	if store.Size() != 1 {
		t.Fatalf("Size() = %d, want 1", store.Size())
	}
	keys := store.Keys()
	if len(keys) != 1 || keys[0] != "a" {
		t.Fatalf("Keys() = %v, want [a]", keys)
	}

	got := store.Get("a")
	if got == nil || got.Content != "value" {
		t.Fatalf("Get(a) = %#v", got)
	}
	if got.AccessCount != 2 {
		t.Errorf("AccessCount = %d, want 2", got.AccessCount)
	}
	if store.Get("missing") != nil {
		t.Error("Get(missing) != nil")
	}

	if !store.Delete("a") {
		t.Error("Delete(a) = false")
	}
	if store.Delete("a") {
		t.Error("second Delete(a) = true")
	}
	if store.Size() != 0 {
		t.Errorf("Size() after delete = %d, want 0", store.Size())
	}

	store.Put("a", freshEntry(1, 1))
	store.Put("b", freshEntry(2, 1))
	if !store.Clear() {
		t.Error("Clear() = false")
	}
	if store.Size() != 0 || len(store.Keys()) != 0 {
		t.Errorf("after Clear: Size=%d Keys=%v", store.Size(), store.Keys())
	}
}

func TestMemoryStorageLRUEviction(t *testing.T) {
	cfg := memConfig()
	cfg.MemoryMaxSize = 2
	cfg.MemoryPolicy = services.CachePolicyLRU
	store := services.NewMemoryStorage(cfg)

	store.Put("a", freshEntry("a", 1))
	store.Put("b", freshEntry("b", 1))
	store.Get("a") // a becomes most recently used
	store.Put("c", freshEntry("c", 1))

	got := store.Keys()
	want := []string{"a", "c"}
	if len(got) != len(want) || got[0] != want[0] || got[1] != want[1] {
		t.Fatalf("Keys() = %v, want %v (b should be evicted)", got, want)
	}
	if store.Get("b") != nil {
		t.Error("b should have been evicted")
	}
}

func TestMemoryStorageMaxMemoryEviction(t *testing.T) {
	cfg := memConfig()
	cfg.MemoryMaxSize = 100
	cfg.MemoryMaxMemoryMB = 1
	cfg.MemoryPolicy = services.CachePolicyLRU
	store := services.NewMemoryStorage(cfg)

	big := 2 * 1024 * 1024
	store.Put("a", freshEntry("a", big))
	store.Put("b", freshEntry("b", big))

	got := store.Keys()
	if len(got) != 1 || got[0] != "b" {
		t.Fatalf("Keys() = %v, want [b] (memory limit exceeded)", got)
	}
}

func TestEnhancedRuleCacheManagerMultiLevel(t *testing.T) {
	cfg := tempConfig(t)
	cfg.MemoryMaxSize = 1
	mgr := services.NewEnhancedRuleCacheManager(cfg)

	big := strings.Repeat("x", 2000)
	if ok, err := mgr.Put("a", big, nil, nil, 1); err != nil || !ok {
		t.Fatalf("Put(a) = %v, %v", ok, err)
	}
	if ok, err := mgr.Put("b", big, nil, nil, 1); err != nil || !ok {
		t.Fatalf("Put(b) = %v, %v", ok, err)
	}

	if mgr.MemoryStorage.Get("a") != nil {
		t.Fatal("a should have been evicted from memory")
	}

	value, err := mgr.Get("a", nil)
	if err != nil {
		t.Fatalf("Get(a) error = %v", err)
	}
	if value != big {
		t.Fatalf("Get(a) = %v, want the disk-promoted content", value)
	}

	metrics := mgr.GetPerformanceMetrics()
	stats := orderedField(t, metrics, "cache_statistics")
	if v, _ := stats.Get("total_requests"); v != 1 {
		t.Errorf("total_requests = %v, want 1", v)
	}
	if v, _ := stats.Get("cache_hits"); v != 1 {
		t.Errorf("cache_hits = %v, want 1", v)
	}
}

func TestDiskStorageRoundTrip(t *testing.T) {
	cfg := tempConfig(t)
	store := services.NewDiskStorage(cfg)

	entry := services.NewCacheEntry("payload", float64(time.Now().UnixNano())/1e9, float64(time.Now().UnixNano())/1e9, 1, 3600.0, 7, "h", []string{"t1"}, 2)
	if !store.Put("key", entry) {
		t.Fatal("Put returned false")
	}
	if store.Size() != 1 {
		t.Fatalf("Size() = %d, want 1", store.Size())
	}
	got := store.Get("key")
	if got == nil || got.Content != "payload" {
		t.Fatalf("Get = %#v", got)
	}
	if got.ContentHash != "h" || got.SizeBytes != 7 || got.Priority != 2 {
		t.Errorf("round-trip entry = %#v", got)
	}
	if len(got.Tags) != 1 || got.Tags[0] != "t1" {
		t.Errorf("Tags = %v, want [t1]", got.Tags)
	}
	if !store.Delete("key") {
		t.Error("Delete = false")
	}
	if store.Get("key") != nil {
		t.Error("Get after delete != nil")
	}
}

func TestEnhancedRuleCacheManagerInvalidateAndTags(t *testing.T) {
	cfg := memConfig()
	mgr := services.NewEnhancedRuleCacheManager(cfg)

	mgr.Put("t1", "one", nil, []string{"x"}, 1)
	mgr.Put("t2", "two", nil, []string{"y"}, 1)
	mgr.Put("t3", "three", nil, []string{"x", "y"}, 1)

	if got := mgr.InvalidateByTags([]string{"x"}); got != 2 {
		t.Errorf("InvalidateByTags([x]) = %d, want 2", got)
	}
	if v, _ := mgr.Get("t1", nil); v != nil {
		t.Errorf("t1 still cached: %v", v)
	}
	if v, _ := mgr.Get("t3", nil); v != nil {
		t.Errorf("t3 still cached: %v", v)
	}
	if v, _ := mgr.Get("t2", nil); v != "two" {
		t.Errorf("t2 = %v, want two", v)
	}

	if ok, _ := mgr.Invalidate("t2"); !ok {
		t.Error("Invalidate(t2) = false")
	}
	if ok, _ := mgr.Invalidate("missing"); !ok {
		t.Error("Invalidate(missing) with disk disabled = false, want true (memory delete result is ignored)")
	}
}

func TestEnhancedRuleCacheManagerClear(t *testing.T) {
	cfg := memConfig()
	mgr := services.NewEnhancedRuleCacheManager(cfg)
	mgr.Put("a", "one", nil, nil, 1)
	mgr.Get("a", nil)

	if !mgr.Clear() {
		t.Error("Clear() = false")
	}
	metrics := mgr.GetPerformanceMetrics()
	stats := orderedField(t, metrics, "cache_statistics")
	if v, _ := stats.Get("total_requests"); v != 0 {
		t.Errorf("total_requests after Clear = %v, want 0", v)
	}
	levels := orderedField(t, metrics, "cache_levels")
	if v, _ := levels.Get("memory_entries"); v != 0 {
		t.Errorf("memory_entries after Clear = %v, want 0", v)
	}
}

func TestGetPerformanceMetricsShape(t *testing.T) {
	old := services.VirtualMemory
	defer func() { services.VirtualMemory = old }()
	services.VirtualMemory = func() (float64, int64) { return 42.5, 1048576 }

	mgr := services.NewEnhancedRuleCacheManager(memConfig())
	mgr.Put("a", "one", nil, nil, 1)
	mgr.Get("a", nil)

	metrics := mgr.GetPerformanceMetrics()
	for _, key := range []string{"cache_statistics", "performance_metrics", "memory_metrics", "cache_levels", "eviction_statistics"} {
		if _, ok := metrics.Get(key); !ok {
			t.Fatalf("metrics missing %q", key)
		}
	}
	memoryMetrics := orderedField(t, metrics, "memory_metrics")
	if v, _ := memoryMetrics.Get("system_memory_percent"); v != 42.5 {
		t.Errorf("system_memory_percent = %v, want 42.5", v)
	}
	if v, _ := memoryMetrics.Get("available_memory_mb"); v != 1.0 {
		t.Errorf("available_memory_mb = %v, want 1.0", v)
	}
	levels := orderedField(t, metrics, "cache_levels")
	if v, _ := levels.Get("memory_entries"); v != 1 {
		t.Errorf("memory_entries = %v, want 1", v)
	}
	if v, _ := levels.Get("disk_entries"); v != 0 {
		t.Errorf("disk_entries = %v, want 0", v)
	}
	evictions := orderedField(t, metrics, "eviction_statistics")
	if v, _ := evictions.Get("total_evictions"); v != 0 {
		t.Errorf("total_evictions = %v, want 0", v)
	}
}

func TestCacheConfigurationDefaults(t *testing.T) {
	c := services.NewCacheConfiguration()
	if c.MemoryMaxSize != 1000 || c.MemoryMaxMemoryMB != 512 || c.MemoryPolicy != services.CachePolicyAdaptive {
		t.Errorf("memory defaults = %+v", c)
	}
	if !c.DiskEnabled || c.DiskMaxSize != 10000 || c.DiskMaxSizeGB != 5 || c.DiskCacheDir != nil {
		t.Errorf("disk defaults = %+v", c)
	}
	if c.DistributedEnabled || c.DistributedBackend != "redis" || c.DistributedConfig == nil {
		t.Errorf("distributed defaults = %+v", c)
	}
	if c.DefaultTTL != 3600.0 || c.MaxTTL != 86400.0 || c.MinTTL != 60.0 {
		t.Errorf("ttl defaults = %+v", c)
	}
	if !c.LazyLoading || !c.PrefetchEnabled || !c.CompressionEnabled || !c.AsyncOperations {
		t.Errorf("performance defaults = %+v", c)
	}
	if !c.MetricsEnabled || c.MetricsInterval != 60.0 || !c.PerformanceLogging {
		t.Errorf("monitoring defaults = %+v", c)
	}
}

func TestCreatePerformanceCacheManager(t *testing.T) {
	mgr := services.CreatePerformanceCacheManager(10, 64, false, 5, 2.0, true)
	if mgr.Config.MemoryMaxSize != 10 || mgr.Config.MemoryMaxMemoryMB != 64 {
		t.Errorf("config = %+v", mgr.Config)
	}
	if mgr.Config.DiskEnabled {
		t.Error("DiskEnabled = true, want false")
	}
	if mgr.DiskStorage != nil {
		t.Error("DiskStorage != nil when disk disabled")
	}
	if mgr.Config.DiskMaxSizeGB != 5 {
		t.Errorf("DiskMaxSizeGB = %d, want 5", mgr.Config.DiskMaxSizeGB)
	}
	if mgr.Config.DefaultTTL != 7200.0 {
		t.Errorf("DefaultTTL = %v, want 7200", mgr.Config.DefaultTTL)
	}
	if !mgr.Config.MetricsEnabled {
		t.Error("MetricsEnabled = false")
	}
}
