package services

import (
	"context"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeCacheRepo struct {
	entries map[string]*entities.OrderedMap[any]
	stats   *entities.OrderedMap[any]
}

func newFakeCacheRepo() *fakeCacheRepo {
	return &fakeCacheRepo{entries: map[string]*entities.OrderedMap[any]{}}
}

func fk(m *entities.OrderedMap[any]) string {
	return ccsStr(m, "context_level") + ":" + ccsStr(m, "context_id")
}

func (f *fakeCacheRepo) GetCacheEntry(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error) {
	return f.entries[level+":"+contextID], nil
}

func (f *fakeCacheRepo) StoreCacheEntry(ctx context.Context, e *entities.OrderedMap[any]) error {
	f.entries[fk(e)] = e
	return nil
}

func (f *fakeCacheRepo) UpdateCacheStats(ctx context.Context, level, contextID string, updates *entities.OrderedMap[any]) error {
	return nil
}

func (f *fakeCacheRepo) InvalidateCacheEntry(ctx context.Context, level, contextID, reason string) error {
	if e, ok := f.entries[level+":"+contextID]; ok {
		e.Set("invalidated", true)
		e.Set("invalidation_reason", reason)
	}
	return nil
}

func (f *fakeCacheRepo) GetCacheEntriesByLevel(ctx context.Context, level string) ([]*entities.OrderedMap[any], error) {
	out := []*entities.OrderedMap[any]{}
	for _, e := range f.sorted() {
		if ccsStr(e, "context_level") == level {
			out = append(out, e)
		}
	}
	return out, nil
}

func (f *fakeCacheRepo) GetTaskCachesByProject(ctx context.Context, projectID string) ([]*entities.OrderedMap[any], error) {
	out := []*entities.OrderedMap[any]{}
	for _, e := range f.sorted() {
		if ccsStr(e, "context_level") == "task" && ccsStr(e, "project_id") == projectID {
			out = append(out, e)
		}
	}
	return out, nil
}

func (f *fakeCacheRepo) GetExpiredCacheEntries(ctx context.Context, now time.Time) ([]*entities.OrderedMap[any], error) {
	out := []*entities.OrderedMap[any]{}
	for _, e := range f.sorted() {
		v, ok := e.Get("expires_at")
		if !ok {
			continue
		}
		if t, ok := v.(string); ok {
			if parsed, err := time.Parse(time.RFC3339, t); err == nil && parsed.Before(now) {
				out = append(out, e)
			}
		}
	}
	return out, nil
}

func (f *fakeCacheRepo) RemoveCacheEntry(ctx context.Context, level, contextID string) error {
	delete(f.entries, level+":"+contextID)
	return nil
}

func (f *fakeCacheRepo) GetInvalidatedCacheEntries(ctx context.Context) ([]*entities.OrderedMap[any], error) {
	out := []*entities.OrderedMap[any]{}
	for _, e := range f.sorted() {
		if v, ok := e.Get("invalidated"); ok && ccsTruthy(v) {
			out = append(out, e)
		}
	}
	return out, nil
}

func (f *fakeCacheRepo) ClearAllCacheEntries(ctx context.Context) (int, error) {
	n := len(f.entries)
	f.entries = map[string]*entities.OrderedMap[any]{}
	return n, nil
}

func (f *fakeCacheRepo) GetCacheStatistics(ctx context.Context) (*entities.OrderedMap[any], error) {
	return f.stats, nil
}

func (f *fakeCacheRepo) GetTopHitCacheEntries(ctx context.Context, limit int) ([]*entities.OrderedMap[any], error) {
	out := f.sorted()
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

func (f *fakeCacheRepo) GetLowHitCacheEntries(ctx context.Context, hitThreshold, limit int) ([]*entities.OrderedMap[any], error) {
	out := []*entities.OrderedMap[any]{}
	for _, e := range f.sorted() {
		if ccsIntDefault(e, "hit_count", 0) < hitThreshold {
			out = append(out, e)
		}
	}
	return out, nil
}

// sorted returns entries in a stable order for deterministic fake behaviour.
func (f *fakeCacheRepo) sorted() []*entities.OrderedMap[any] {
	out := make([]*entities.OrderedMap[any], 0, len(f.entries))
	for _, k := range []string{"global:g", "project:p", "task:t"} {
		if e, ok := f.entries[k]; ok {
			out = append(out, e)
		}
	}
	return out
}

func TestContextCacheServiceCacheAndGet(t *testing.T) {
	repo := newFakeCacheRepo()
	c := NewContextCacheService(repo, 1, nil)

	resolved := entities.NewOrderedMap[any]()
	resolved.Set("foo", "bar")
	if !c.CacheResolvedContext(context.Background(), "task", "t1", resolved, "deps", []string{"global", "task"}, nil) {
		t.Fatal("cache failed")
	}
	entry := repo.entries["task:t1"]
	if entry == nil {
		t.Fatal("entry not stored")
	}
	wantKeys := "context_id,context_level,resolved_context,dependencies_hash,resolution_path,created_at,expires_at,hit_count,last_hit,cache_size_bytes,invalidated,invalidation_reason"
	if strings.Join(entry.Keys(), ",") != wantKeys {
		t.Fatalf("entry keys = %v", entry.Keys())
	}
	if v, _ := entry.Get("hit_count"); v != 0 {
		t.Fatalf("hit_count = %v", v)
	}
	if v, _ := entry.Get("invalidated"); v != false {
		t.Fatalf("invalidated = %v", v)
	}
	if v, _ := entry.Get("invalidation_reason"); v != nil {
		t.Fatalf("invalidation_reason = %v", v)
	}

	got, _ := c.GetCachedContext(context.Background(), "task", "t1")
	if got != entry {
		t.Fatal("expected cached entry")
	}

	// invalidated entries are removed
	entry.Set("invalidated", true)
	got, _ = c.GetCachedContext(context.Background(), "task", "t1")
	if got != nil {
		t.Fatal("invalidated entry returned")
	}
	if _, ok := repo.entries["task:t1"]; ok {
		t.Fatal("invalidated entry not cleaned up")
	}
}

func TestContextCacheServiceExpiredString(t *testing.T) {
	repo := newFakeCacheRepo()
	c := NewContextCacheService(repo, 1, nil)
	e := entities.NewOrderedMap[any]()
	e.Set("context_level", "task")
	e.Set("context_id", "old")
	e.Set("invalidated", false)
	e.Set("expires_at", time.Now().UTC().Add(-time.Hour).Format(time.RFC3339))
	repo.entries["task:old"] = e

	got, _ := c.GetCachedContext(context.Background(), "task", "old")
	if got != nil {
		t.Fatal("expired entry returned")
	}
	if _, ok := repo.entries["task:old"]; ok {
		t.Fatal("expired entry not removed")
	}
}

func TestContextCacheServiceInvalidateDependentGlobal(t *testing.T) {
	repo := newFakeCacheRepo()
	c := NewContextCacheService(repo, 1, nil)
	for _, spec := range [][2]string{{"project", "p"}, {"task", "t"}} {
		e := entities.NewOrderedMap[any]()
		e.Set("context_level", spec[0])
		e.Set("context_id", spec[1])
		e.Set("invalidated", false)
		repo.entries[spec[0]+":"+spec[1]] = e
	}
	got := c.InvalidateDependentCaches(context.Background(), "global", "g", "dependency_changed")
	if strings.Join(got, ",") != "project:p,task:t" {
		t.Fatalf("invalidated = %v", got)
	}
	for _, e := range repo.entries {
		if v, _ := e.Get("invalidated"); v != true {
			t.Fatal("not all dependent caches invalidated")
		}
	}
}

func TestContextCacheServiceStatsAndOptimize(t *testing.T) {
	repo := newFakeCacheRepo()
	repo.stats = entities.NewOrderedMap[any]()
	repo.stats.Set("total_entries", 2)
	repo.stats.Set("total_size_bytes", 1000)
	repo.stats.Set("total_hits", 20)
	c := NewContextCacheService(repo, 1, nil)

	stats := c.GetCacheStats(context.Background())
	wantKeys := "total_entries,total_size_bytes,total_hits,performance_metrics,health_indicators,timestamp"
	if strings.Join(stats.Keys(), ",") != wantKeys {
		t.Fatalf("stats keys = %v", stats.Keys())
	}
	pm, _ := stats.Get("performance_metrics")
	perf := pm.(*entities.OrderedMap[any])
	if v, _ := perf.Get("hit_rate_estimated"); v != 1.0 {
		t.Fatalf("hit_rate = %v", v)
	}
	if v, _ := perf.Get("average_entry_size_bytes"); v != 500.0 {
		t.Fatalf("avg size = %v", v)
	}
	if v, _ := perf.Get("cache_efficiency"); v != "high" {
		t.Fatalf("efficiency = %v", v)
	}
	hi, _ := stats.Get("health_indicators")
	health := hi.(*entities.OrderedMap[any])
	if v, _ := health.Get("cache_pressure"); v != "low" {
		t.Fatalf("pressure = %v", v)
	}

	opt := c.OptimizeCache(context.Background())
	if v, _ := opt.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	actions, _ := opt.Get("actions_taken")
	if strings.Join(actions.([]string), ",") != "cleaned_expired,cleaned_invalidated" {
		t.Fatalf("actions = %v", actions)
	}
}

func TestContextCacheServiceClearAll(t *testing.T) {
	repo := newFakeCacheRepo()
	c := NewContextCacheService(repo, 1, nil)
	e := entities.NewOrderedMap[any]()
	e.Set("context_level", "task")
	e.Set("context_id", "t")
	repo.entries["task:t"] = e

	res := c.ClearAllCache(context.Background())
	if v, _ := res.Get("removed_count"); v != 1 {
		t.Fatalf("removed = %v", v)
	}
	if len(repo.entries) != 0 {
		t.Fatal("entries not cleared")
	}
}
