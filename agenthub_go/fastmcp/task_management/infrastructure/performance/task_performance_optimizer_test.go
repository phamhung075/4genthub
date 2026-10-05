package performance

import (
	"strings"
	"testing"
	"time"
)

func TestTaskPerformanceOptimizerCacheKey(t *testing.T) {
	o := NewTaskPerformanceOptimizer(300)
	key, err := o.GetCacheKey("get_task", map[string]any{"task_id": "T1"})
	if err != nil {
		t.Fatal(err)
	}
	if key != "1102be071c75a5231abfee143503dc48" {
		t.Fatalf("key = %s", key)
	}
	// sort_keys makes the result independent of map iteration order.
	key2, _ := o.GetCacheKey("get_task", map[string]any{"b": "x", "a": 1})
	if key2 != "80b12d23d81f834a2c22b5edb32a303e" {
		t.Fatalf("key2 = %s", key2)
	}
}

func TestTaskPerformanceOptimizerCacheExpiry(t *testing.T) {
	o := NewTaskPerformanceOptimizer(300)
	base := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	now := base
	o.now = func() time.Time { return now }

	o.SetCache("k", 5)
	if got := o.GetFromCache("k"); got != 5 {
		t.Fatalf("cached = %v", got)
	}
	now = base.Add(299 * time.Second)
	if got := o.GetFromCache("k"); got != 5 {
		t.Fatalf("cached before expiry = %v", got)
	}
	now = base.Add(300 * time.Second)
	if got := o.GetFromCache("k"); got != nil {
		t.Fatalf("expired = %v", got)
	}
	if _, ok := o.cache["k"]; ok {
		t.Fatal("expired entry was not removed")
	}
}

func TestTaskPerformanceOptimizerPayload(t *testing.T) {
	o := NewTaskPerformanceOptimizer(300)
	task := map[string]any{
		"id": "T1", "title": "T", "status": "in_progress", "priority": "high",
		"progress_percentage": 40, "assignees": []any{"a", "b"},
		"labels":   []any{map[string]any{"name": "x"}, "y"},
		"due_date": "2024-01-01", "updated_at": "2024-02-02",
		"dependencies": []any{map[string]any{"status": "done"}, map[string]any{"status": "todo"}},
		"description":  strings.Repeat("d", 250),
	}
	got := o.OptimizeResponsePayload([]map[string]any{task})
	if len(got) != 1 {
		t.Fatalf("len = %d", len(got))
	}
	m := got[0]
	wantKeys := []string{"id", "title", "status", "priority", "progress_percentage", "assignees_count",
		"labels", "due_date", "updated_at", "has_dependencies", "is_blocked", "description_preview"}
	if strings.Join(m.Keys(), ",") != strings.Join(wantKeys, ",") {
		t.Fatalf("keys = %v", m.Keys())
	}
	if v, _ := m.Get("assignees_count"); v != 2 {
		t.Fatalf("assignees_count = %v", v)
	}
	labels, _ := m.Get("labels")
	if strings.Join([]string{labels.([]any)[0].(string), labels.([]any)[1].(string)}, ",") != "x,y" {
		t.Fatalf("labels = %v", labels)
	}
	if v, _ := m.Get("has_dependencies"); v != true {
		t.Fatalf("has_dependencies = %v", v)
	}
	if v, _ := m.Get("is_blocked"); v != true {
		t.Fatalf("is_blocked = %v", v)
	}
	preview, _ := m.Get("description_preview")
	if len([]rune(preview.(string))) != 200 || !strings.HasSuffix(preview.(string), "...") {
		t.Fatalf("preview = %q", preview)
	}
}

func TestTaskPerformanceOptimizerPagination(t *testing.T) {
	o := NewTaskPerformanceOptimizer(300)
	m := o.GetPaginationMetadata(25, 10, 10)
	checks := map[string]any{"total_count": 25, "current_page": 2, "total_pages": 3, "limit": 10, "offset": 10,
		"has_next": true, "has_prev": true, "next_offset": 20, "prev_offset": 0}
	for k, want := range checks {
		if v, _ := m.Get(k); v != want {
			t.Fatalf("%s = %v want %v", k, v, want)
		}
	}

	m2 := o.GetPaginationMetadata(25, 10, 0)
	if v, _ := m2.Get("has_prev"); v != false {
		t.Fatalf("has_prev = %v", v)
	}
	if v, _ := m2.Get("prev_offset"); v != nil {
		t.Fatalf("prev_offset = %v", v)
	}
	if v, _ := m2.Get("next_offset"); v != 10 {
		t.Fatalf("next_offset = %v", v)
	}

	// Python quirk: limit 0 keeps has_next true for a positive total.
	m3 := o.GetPaginationMetadata(25, 0, 0)
	if v, _ := m3.Get("has_next"); v != true {
		t.Fatalf("limit=0 has_next = %v", v)
	}
	if v, _ := m3.Get("current_page"); v != 1 {
		t.Fatalf("limit=0 current_page = %v", v)
	}
}
