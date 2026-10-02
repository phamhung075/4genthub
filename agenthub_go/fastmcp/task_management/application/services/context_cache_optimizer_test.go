package services

import (
	"strconv"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestContextCacheOptimizerGenerateKey(t *testing.T) {
	o := NewContextCacheOptimizer(200, 600, CacheStrategyAdaptive, true)
	// json.dumps({...}, sort_keys=True, default=str) -> {"a": 1, "b": 2}
	got := o.generateKey("task_list", map[string]any{"b": 2, "a": 1})
	if got != "27bea2854628f0d34bd2da86b19d1a47" {
		t.Fatalf("generateKey = %q", got)
	}
}

func TestContextCacheOptimizerPutGetAndStats(t *testing.T) {
	o := NewContextCacheOptimizer(200, 600, CacheStrategyAdaptive, true)
	data := entities.NewOrderedMap[any]()
	data.Set("x", 1)
	if !o.Put("k", data, "task", "get", nil, false, false) {
		t.Fatal("Put returned false")
	}
	got := o.Get("k", "task")
	if got != any(data) {
		t.Fatalf("Get = %v", got)
	}
	// miss
	if o.Get("missing", "task") != nil {
		t.Fatal("expected nil for miss")
	}

	stats := o.GetCacheStats()
	wantKeys := []string{"total_entries", "hit_count", "miss_count", "current_size_mb", "max_size_mb", "performance", "storage", "maintenance", "context_breakdown", "strategy"}
	if strings.Join(stats.Keys(), ",") != strings.Join(wantKeys, ",") {
		t.Fatalf("stat keys = %v", stats.Keys())
	}
	if v, _ := stats.Get("total_entries"); v != 1 {
		t.Fatalf("total_entries = %v", v)
	}
	if v, _ := stats.Get("hit_count"); v != 1 {
		t.Fatalf("hit_count = %v", v)
	}
	if v, _ := stats.Get("miss_count"); v != 1 {
		t.Fatalf("miss_count = %v", v)
	}
	breakdown, _ := stats.Get("context_breakdown")
	bd := breakdown.(*entities.OrderedMap[any])
	if keys := bd.Keys(); len(keys) != 1 || keys[0] != "task" {
		t.Fatalf("breakdown keys = %v", keys)
	}
}

func TestContextCacheOptimizerExpiryAndInvalidate(t *testing.T) {
	o := NewContextCacheOptimizer(200, 600, CacheStrategyAdaptive, true)
	o.Put("user:1", "1", "user", "get", nil, false, false)
	o.Put("user:2", "2", "user", "get", nil, false, false)
	o.Put("task:1", "3", "task", "list", nil, false, false)

	if n := o.InvalidatePattern("user:*"); n != 2 {
		t.Fatalf("invalidated = %d", n)
	}
	if o.Get("user:1", "user") != nil {
		t.Fatal("user:1 should be gone")
	}
	if o.Get("task:1", "task") != "3" {
		t.Fatal("task:1 should remain")
	}

	// invalidate by context type
	ctxType := "task"
	if n := o.Invalidate(nil, &ctxType, nil); n != 1 {
		t.Fatalf("context_type invalidated = %d", n)
	}

	// TTL: mutate created_at into the past rather than sleeping.
	ttl := 60
	o.Put("t", "v", "task", "get", &ttl, false, false)
	e, _ := o.cache.Get("t")
	e.CreatedAt = time.Now().Add(-2 * time.Minute)
	if o.Get("t", "task") != nil {
		t.Fatal("expired entry returned")
	}
	if o.cleanupExpiredLocked() != 0 {
		t.Fatal("no entries should remain expired")
	}
}

func TestContextCacheOptimizerLRUEviction(t *testing.T) {
	o := NewContextCacheOptimizer(1, 600, CacheStrategyLRU, true)
	o.maxSizeBytes = 1100 // 10% single-entry cap = 110 bytes
	for i := 0; i < 11; i++ {
		key := "k" + strconv.Itoa(i)
		if !o.Put(key, strings.Repeat("a", 100), "task", "get", nil, false, false) {
			t.Fatalf("Put(%s) failed", key)
		}
	}
	if o.cache.Has("k0") {
		t.Fatal("k0 should have been evicted")
	}
	if !o.cache.Has("k10") {
		t.Fatal("k10 should be present")
	}
	if o.metric("evictions") != 1 {
		t.Fatalf("evictions = %d", o.metric("evictions"))
	}
}

func TestContextCacheOptimizerWarmCacheTuple(t *testing.T) {
	o := NewContextCacheOptimizer(200, 600, CacheStrategyAdaptive, true)
	warmed := o.WarmCache(map[string]any{
		"a": "plain",
		"b": [2]any{"project", "ordered"},
	}, "warmup")
	if warmed != 2 {
		t.Fatalf("warmed = %d", warmed)
	}
	if o.Get("a", "warmup") != "plain" {
		t.Fatal("plain value")
	}
	if o.Get("b", "project") != "ordered" {
		t.Fatal("tuple value")
	}
}

func TestContextCacheOptimizerDefaultAdaptiveTTL(t *testing.T) {
	o := NewContextCacheOptimizer(200, 600, CacheStrategyAdaptive, true)
	if got := o.adaptiveTTLFor("unknown", "unknown"); got != 600 {
		t.Fatalf("ttl = %d", got)
	}
	if o.metric("adaptive_adjustments") != 1 {
		t.Fatalf("adjustments = %d", o.metric("adaptive_adjustments"))
	}
}
