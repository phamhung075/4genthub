package cache

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"testing"
	"time"
)

func cacheStrPtr(s string) *string     { return &s }
func cacheIntPtr(i int) *int           { return &i }
func cacheFloatPtr(f float64) *float64 { return &f }

func TestCacheManagerSetGetStatsAndEviction(t *testing.T) {
	c := NewCacheManagerWith(2, 300)

	if got := c.Get("missing"); got != nil {
		t.Fatalf("Get(missing) = %v, want nil", got)
	}
	c.Set("a", 1, nil)
	c.Set("b", "x", nil)
	if got := c.Get("a"); got != 1 {
		t.Fatalf("Get(a) = %v, want 1", got)
	}
	if got := c.Get("a"); got != 1 {
		t.Fatalf("Get(a) = %v, want 1", got)
	}
	stats := c.GetStats()
	if statVal(stats, "hits") != 2 || statVal(stats, "misses") != 1 || statVal(stats, "sets") != 2 || statVal(stats, "size") != 2 {
		t.Fatalf("stats = %v", stats)
	}

	// "b" is the least recently used; adding "c" evicts it.
	c.Set("c", 3, nil)
	if got := c.Get("b"); got != nil {
		t.Fatalf("Get(b) = %v, want nil (evicted)", got)
	}
	if got := c.Get("a"); got != 1 {
		t.Fatalf("Get(a) after eviction = %v", got)
	}
	if stats := c.GetStats(); statVal(stats, "evictions") != 1 {
		t.Fatalf("evictions = %v, want 1", statVal(stats, "evictions"))
	}

	if !c.Delete("a") {
		t.Fatal("Delete(a) = false, want true")
	}
	if c.Delete("a") {
		t.Fatal("Delete(a) second = true, want false")
	}
	c.Clear()
	if statVal(c.GetStats(), "size") != 0 {
		t.Fatalf("size after clear = %v", statVal(c.GetStats(), "size"))
	}
}

func TestCacheManagerExpiryAndCleanup(t *testing.T) {
	prev := cacheClock
	now := 1000.0
	cacheClock = func() float64 { return now }
	defer func() { cacheClock = prev }()

	c := NewCacheManagerWith(10, 300)
	ttl := 5
	c.Set("k", "v", &ttl)

	now = 1004.0
	if got := c.Get("k"); got != "v" {
		t.Fatalf("Get(k) before expiry = %v", got)
	}
	now = 1005.0 // (now-created) == ttl is not expired
	if got := c.Get("k"); got != "v" {
		t.Fatalf("Get(k) at boundary = %v", got)
	}
	now = 1005.5
	if got := c.Get("k"); got != nil {
		t.Fatalf("Get(k) after expiry = %v, want nil", got)
	}
	if statVal(c.GetStats(), "expirations") != 1 {
		t.Fatalf("expirations = %v, want 1", statVal(c.GetStats(), "expirations"))
	}

	// ttl <= 0 never expires.
	zero := 0
	c.Set("forever", "y", &zero)
	now = 1e9
	if got := c.Get("forever"); got != "y" {
		t.Fatalf("Get(forever) = %v", got)
	}

	c.Set("e1", 1, &ttl)
	now = 1e9 + 6
	if n := c.CleanupExpired(); n != 1 {
		t.Fatalf("CleanupExpired = %d, want 1", n)
	}
}

func TestCachedRepository(t *testing.T) {
	r := NewCachedRepository("CacheManagerTestRepo", nil)
	if r.CacheName != "CacheManagerTestRepo_cache" {
		t.Fatalf("CacheName = %q", r.CacheName)
	}
	custom := "custom_cache"
	r2 := NewCachedRepository("Ignored", &custom)
	if r2.CacheName != "custom_cache" {
		t.Fatalf("CacheName = %q", r2.CacheName)
	}

	r.Cache.Set("Repo:find:1", "a", nil)
	r.Cache.Set("Repo:find:2", "b", nil)
	r.Cache.Set("other", "c", nil)
	pattern := "find"
	r.InvalidateCache(&pattern)
	if r.Cache.Get("Repo:find:1") != nil || r.Cache.Get("Repo:find:2") != nil {
		t.Fatal("pattern invalidation left keys behind")
	}
	if r.Cache.Get("other") != "c" {
		t.Fatal("pattern invalidation removed an unrelated key")
	}
	r.InvalidateCache(nil)
	if r.Cache.Get("other") != nil {
		t.Fatal("nil pattern did not clear the cache")
	}
}

func TestCacheClockDefaultsToWallTime(t *testing.T) {
	before := time.Now().UnixNano()
	got := cacheClock()
	after := time.Now().UnixNano()
	if got < float64(before)/1e9 || got > float64(after)/1e9 {
		t.Fatalf("cacheClock = %v outside [%v, %v]", got, before, after)
	}
}

func statVal(m *entities.OrderedMap[any], key string) any {
	v, _ := m.Get(key)
	return v
}
