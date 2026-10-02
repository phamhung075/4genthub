package cache

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func ordered(values map[string]any, keys ...string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for _, k := range keys {
		m.Set(k, values[k])
	}
	return m
}

func TestContextCacheMakeKeyAndRoundTrip(t *testing.T) {
	cc := NewContextCacheWith(1, 300, true)

	kw := entities.NewOrderedMap[any]()
	kw.Set("level", "project")
	kw.Set("context_id", "c1")
	kw.Set("user_id", nil)
	if got := cc.makeKey("inheritance", kw); got != "inheritance:context_id:c1:level:project" {
		t.Fatalf("makeKey = %q", got)
	}

	data := ordered(map[string]any{"name": "n", "count": 2}, "name", "count")
	if err := cc.SetContext("project", "c1", "u1", data, nil); err != nil {
		t.Fatal(err)
	}
	got, err := cc.GetContext("project", "c1", "u1")
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Get("name"); v != "n" {
		t.Fatalf("name = %v", v)
	}
	if v, _ := got.Get("count"); v != int64(2) {
		t.Fatalf("count = %v", v)
	}
	if k := got.Keys(); len(k) != 2 || k[0] != "name" || k[1] != "count" {
		t.Fatalf("key order = %v", k)
	}

	if missing, _ := cc.GetContext("project", "nope", "u1"); missing != nil {
		t.Fatalf("missing context = %v", missing)
	}

	// Specific invalidation.
	level, contextID := "project", "c1"
	cc.InvalidateContext("u1", &level, &contextID)
	if got, _ := cc.GetContext("project", "c1", "u1"); got != nil {
		t.Fatal("context not invalidated")
	}

	// User-wide invalidation (pattern).
	_ = cc.SetContext("project", "c2", "u1", data, nil)
	_ = cc.SetContext("project", "c3", "other", data, nil)
	cc.InvalidateContext("u1", nil, nil)
	if got, _ := cc.GetContext("project", "c2", "u1"); got != nil {
		t.Fatal("user context not invalidated")
	}
	if got, _ := cc.GetContext("project", "c3", "other"); got == nil {
		t.Fatal("invalidation crossed users")
	}
}

func TestContextCacheInheritanceAndTTL(t *testing.T) {
	cc := NewContextCacheWith(1, 30, true)
	data := ordered(map[string]any{"chain": "global>project"}, "chain")
	if err := cc.SetInheritanceChain("project", "c1", "u1", data); err != nil {
		t.Fatal(err)
	}
	got, err := cc.GetInheritanceChain("project", "c1", "u1")
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Get("chain"); v != "global>project" {
		t.Fatalf("chain = %v", v)
	}
	level, contextID := "project", "c1"
	cc.InvalidateInheritance("u1", &level, &contextID)
	if got, _ := cc.GetInheritanceChain("project", "c1", "u1"); got != nil {
		t.Fatal("inheritance not invalidated")
	}
}

func TestContextCacheCompressionAndBatch(t *testing.T) {
	cc := NewContextCacheWith(1, 300, true)
	big := strings.Repeat("a", 5000)
	data := ordered(map[string]any{"blob": big}, "blob")
	if err := cc.SetContext("global", "g", "u", data, nil); err != nil {
		t.Fatal(err)
	}
	raw, ok := cc.Redis.Get(cc.key("context", "global", "g", "u"))
	if !ok || !strings.HasPrefix(raw, "COMPRESSED:") {
		t.Fatalf("stored value was not compressed: ok=%v prefix=%.20q", ok, raw)
	}
	got, err := cc.GetContext("global", "g", "u")
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := got.Get("blob"); v != big {
		t.Fatalf("round-trip blob length = %d, want %d", len(v.(string)), len(big))
	}
	if s := cc.decompress("plain"); s != "plain" {
		t.Fatalf("decompress(plain) = %q", s)
	}

	// Batch set/get.
	batch := []ContextEntry{
		{Level: "project", ContextID: "b1", Data: ordered(map[string]any{"v": 1}, "v")},
		{Level: "project", ContextID: "b2", Data: ordered(map[string]any{"v": 2}, "v")},
	}
	if err := cc.SetMultipleContexts(batch, "u", nil); err != nil {
		t.Fatal(err)
	}
	refs := []ContextRef{{Level: "project", ContextID: "b1"}, {Level: "project", ContextID: "b2"}, {Level: "project", ContextID: "b3"}}
	results, err := cc.GetMultipleContexts(refs, "u")
	if err != nil {
		t.Fatal(err)
	}
	if len(results) != 3 || results[2] != nil {
		t.Fatalf("batch results = %v", results)
	}
	if v, _ := results[1].Get("v"); v != int64(2) {
		t.Fatalf("b2 v = %v", v)
	}

	stats := cc.GetCacheStats()
	if stats["type"] != "in-memory" || stats["connected"] != true {
		t.Fatalf("stats = %v", stats)
	}
	cc.ClearCache(nil)
	if cc.Redis.Cache.Len() != 0 || cc.Redis.TTLMap.Len() != 0 {
		t.Fatal("ClearCache did not empty the cache")
	}
}

func TestInMemoryCacheScanPipelineAndExpiry(t *testing.T) {
	prev := cacheClock
	now := 100.0
	cacheClock = func() float64 { return now }
	defer func() { cacheClock = prev }()

	c := NewInMemoryCache()
	c.Setex("a:1", 10, "x")
	c.Setex("a:2", 10, "y")
	c.Setex("b:1", 10, "z")
	keys, _ := c.ScanIter("a:*")
	if len(keys) != 2 || keys[0] != "a:1" || keys[1] != "a:2" {
		t.Fatalf("ScanIter = %v", keys)
	}
	if keys, _ := c.ScanIter("c:*"); keys != nil {
		t.Fatalf("ScanIter(c:*) = %v, want nil", keys)
	}

	p := c.Pipeline()
	p.Get("a:1").Setex("c:1", 10, "w").Delete("b:1").Get("missing")
	results := p.Execute()
	if len(results) != 4 || results[0] != "x" || results[1] != true || results[2] != true || results[3] != nil {
		t.Fatalf("pipeline results = %v", results)
	}
	if _, ok := c.Get("b:1"); ok {
		t.Fatal("b:1 was not deleted")
	}

	now = 105.0
	if v, ok := c.Get("a:1"); !ok || v != "x" {
		t.Fatalf("a:1 before expiry = %v ok=%v", v, ok)
	}
	now = 111.0
	if _, ok := c.Get("a:1"); ok {
		t.Fatal("a:1 should be expired")
	}
	if c.Cache.Has("a:1") || c.TTLMap.Has("a:1") {
		t.Fatal("expired entry was not deleted")
	}
	if !c.Ping() {
		t.Fatal("Ping = false")
	}
}

func TestGetContextCacheSingleton(t *testing.T) {
	ResetContextCache()
	a := GetContextCache()
	b := GetContextCache()
	if a != b {
		t.Fatal("GetContextCache did not return the singleton")
	}
	ResetContextCache()
	if c := GetContextCache(); c == a {
		t.Fatal("ResetContextCache did not drop the singleton")
	}
}

func TestScanIterAlternationAndInvalidPattern(t *testing.T) {
	c := NewInMemoryCache()
	c.Setex("ax", 60, "1")
	c.Setex("zb", 60, "1")
	c.Setex("a", 60, "1")
	// re.match("a|b") anchors the whole alternation: keys starting with a or b
	keys, err := c.ScanIter("a|b")
	if err != nil || len(keys) != 2 || keys[0] != "ax" || keys[1] != "a" {
		t.Fatalf("ScanIter(a|b) = %v, %v", keys, err)
	}
	if _, err := c.ScanIter("c("); err == nil {
		t.Fatal("invalid regex must be an error (re.error)")
	}
	if _, err := NewInMemoryCache().ScanIter("c("); err != nil {
		t.Fatal("an empty cache never compiles the pattern (lazy re.match)")
	}
	cc := NewContextCache()
	cc.Redis.Setex("k", 60, "v")
	bad := "["
	if err := cc.ClearCache(&bad); err == nil {
		t.Fatal("ClearCache with an invalid pattern must fail")
	}
}

func TestWarmCacheRequiresTruthyLevel(t *testing.T) {
	m := &CacheInvalidationMixin{CacheEnabled: true, UserID: cacheStrPtr("u")}
	m.cache = NewContextCache()
	empty := ""
	data := entities.NewOrderedMap[any]()
	m.WarmCache("context", "id", data, nil, &empty, nil)
	if n, _ := m.cache.GetCacheStats()["cache_size"].(int); n != 0 {
		t.Fatalf("empty level must not be stored, size=%d", n)
	}
}

func TestInvalidateBulkWithCacheDisabledReturnsError(t *testing.T) {
	m := &CacheInvalidationMixin{CacheEnabled: false, UserID: cacheStrPtr("u")}
	lv := "project"
	if err := m.InvalidateBulk("context", []string{"a"}, CacheOperationUpdate, nil, &lv); err == nil {
		t.Fatal("expected the AttributeError counterpart, not a nil dereference")
	}
}
