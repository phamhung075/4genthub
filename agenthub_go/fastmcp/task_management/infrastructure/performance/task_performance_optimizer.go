// task_performance_optimizer.go ports
// task_management/infrastructure/performance/task_performance_optimizer.py.
//
// The three SQLAlchemy/Session methods (optimize_task_query, analyze_query_performance,
// create_optimized_indexes) require the database layer/ORM and are intentionally not
// ported; see MIGRATION notes. The cache, payload and pagination helpers are portable.
package performance

import (
	"crypto/md5"
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskPerformanceOptimizer is task_performance_optimizer.TaskPerformanceOptimizer.
type TaskPerformanceOptimizer struct {
	CacheTTL   int
	QueryStats map[string]map[string]any

	cache map[string]perfCacheEntry
	now   func() time.Time
}

type perfCacheEntry struct {
	value     any
	timestamp time.Time
}

// NewTaskPerformanceOptimizer applies the Python default TTL of 300 seconds.
func NewTaskPerformanceOptimizer(cacheTTLSeconds int) *TaskPerformanceOptimizer {
	return &TaskPerformanceOptimizer{
		CacheTTL:   cacheTTLSeconds,
		QueryStats: map[string]map[string]any{},
		cache:      map[string]perfCacheEntry{},
		now:        time.Now,
	}
}

// perfSortable canonicalises dicts to map[string]any so json.dumps(sort_keys=True) sorts
// every level (OrderedAny would otherwise keep insertion order).
func perfSortable(v any) any {
	if o, ok := v.(tmvo.OrderedAny); ok {
		m := map[string]any{}
		for _, k := range o.KeysAny() {
			m[k] = perfSortable(o.GetAny(k))
		}
		return m
	}
	switch x := v.(type) {
	case map[string]any:
		m := map[string]any{}
		for k, val := range x {
			m[k] = perfSortable(val)
		}
		return m
	case []any:
		out := make([]any, len(x))
		for i, e := range x {
			out[i] = perfSortable(e)
		}
		return out
	}
	return v
}

// GetCacheKey mirrors get_cache_key: md5 of json.dumps({"operation":..., "params":...},
// sort_keys=True).
func (o *TaskPerformanceOptimizer) GetCacheKey(operation string, params map[string]any) (string, error) {
	keyData := map[string]any{"operation": operation, "params": params}
	keyStr, err := tmvo.PyJSONDumps(perfSortable(keyData), -1)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%x", md5.Sum([]byte(keyStr))), nil
}

// GetFromCache returns the cached value when it has not expired, otherwise nil.
func (o *TaskPerformanceOptimizer) GetFromCache(cacheKey string) any {
	if entry, ok := o.cache[cacheKey]; ok {
		if o.now().Sub(entry.timestamp) < time.Duration(o.CacheTTL)*time.Second {
			return entry.value
		}
		delete(o.cache, cacheKey)
	}
	return nil
}

// SetCache stores a value and cleans up when the cache exceeds 1000 entries.
func (o *TaskPerformanceOptimizer) SetCache(cacheKey string, value any) {
	o.cache[cacheKey] = perfCacheEntry{value: value, timestamp: o.now()}
	if len(o.cache) > 1000 {
		o.cleanupCache()
	}
}

func (o *TaskPerformanceOptimizer) cleanupCache() {
	now := o.now()
	for key, entry := range o.cache {
		if now.Sub(entry.timestamp) >= time.Duration(o.CacheTTL)*time.Second {
			delete(o.cache, key)
		}
	}
}

func perfGet(task map[string]any, key string, def any) any {
	if v, ok := task[key]; ok {
		return v
	}
	return def
}

// perfLen is Python len() for the JSON container/string kinds that reach this module.
func perfLen(v any) int {
	switch x := v.(type) {
	case nil:
		return 0
	case []any:
		return len(x)
	case []string:
		return len(x)
	case map[string]any:
		return len(x)
	case string:
		return len([]rune(x))
	}
	if o, ok := v.(tmvo.OrderedAny); ok {
		return len(o.KeysAny())
	}
	return 0
}

// perfSequence returns the elements of a list/string, or an empty slice otherwise.
func perfSequence(v any) []any {
	switch x := v.(type) {
	case nil:
		return []any{}
	case []any:
		return x
	case []string:
		out := make([]any, len(x))
		for i, s := range x {
			out[i] = s
		}
		return out
	case string:
		out := []any{}
		for _, r := range x {
			out = append(out, string(r))
		}
		return out
	}
	if o, ok := v.(tmvo.OrderedAny); ok {
		out := []any{}
		for _, k := range o.KeysAny() {
			out = append(out, o.GetAny(k))
		}
		return out
	}
	return []any{}
}

// OptimizeResponsePayload mirrors optimize_response_payload.
func (o *TaskPerformanceOptimizer) OptimizeResponsePayload(tasks []map[string]any) []*entities.OrderedMap[any] {
	optimizedTasks := []*entities.OrderedMap[any]{}
	for _, task := range tasks {
		labels := []any{}
		for _, label := range perfSequence(perfGet(task, "labels", []any{})) {
			if m, ok := label.(map[string]any); ok {
				labels = append(labels, m["name"])
			} else if m, ok := label.(*entities.OrderedMap[any]); ok {
				v, _ := m.Get("name")
				labels = append(labels, v)
			} else {
				labels = append(labels, label)
			}
		}

		deps := perfSequence(perfGet(task, "dependencies", []any{}))
		isBlocked := false
		for _, dep := range deps {
			status := any(nil)
			switch d := dep.(type) {
			case map[string]any:
				status = d["status"]
			case *entities.OrderedMap[any]:
				status, _ = d.Get("status")
			}
			if status != "done" {
				isBlocked = true
				break
			}
		}

		optimized := entities.NewOrderedMap[any]()
		optimized.Set("id", perfGet(task, "id", nil))
		optimized.Set("title", perfGet(task, "title", nil))
		optimized.Set("status", perfGet(task, "status", nil))
		optimized.Set("priority", perfGet(task, "priority", nil))
		optimized.Set("progress_percentage", perfGet(task, "progress_percentage", 0))
		optimized.Set("assignees_count", perfLen(perfGet(task, "assignees", []any{})))
		optimized.Set("labels", labels)
		optimized.Set("due_date", perfGet(task, "due_date", nil))
		optimized.Set("updated_at", perfGet(task, "updated_at", nil))
		optimized.Set("has_dependencies", len(deps) > 0)
		optimized.Set("is_blocked", isBlocked)

		description := perfGet(task, "description", "")
		if s, ok := description.(string); ok && len([]rune(s)) > 200 {
			optimized.Set("description_preview", string([]rune(s)[:197])+"...")
		}
		optimizedTasks = append(optimizedTasks, optimized)
	}
	return optimizedTasks
}

// GetPaginationMetadata mirrors get_pagination_metadata.
func (o *TaskPerformanceOptimizer) GetPaginationMetadata(totalCount, limit, offset int) *entities.OrderedMap[any] {
	currentPage := 1
	if limit > 0 {
		currentPage = perfFloorDiv(offset, limit) + 1
	}
	totalPages := 1
	if limit > 0 {
		totalPages = perfFloorDiv(totalCount+limit-1, limit)
	}
	var nextOffset any
	if offset+limit < totalCount {
		nextOffset = perfMin(offset+limit, totalCount)
	}
	var prevOffset any
	if offset > 0 {
		prevOffset = perfMax(offset-limit, 0)
	}
	return obj(
		"total_count", totalCount,
		"current_page", currentPage,
		"total_pages", totalPages,
		"limit", limit,
		"offset", offset,
		"has_next", offset+limit < totalCount,
		"has_prev", offset > 0,
		"next_offset", nextOffset,
		"prev_offset", prevOffset,
	)
}

func perfFloorDiv(a, b int) int {
	q := a / b
	if (a%b != 0) && ((a < 0) != (b < 0)) {
		q--
	}
	return q
}

func perfMin(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func perfMax(a, b int) int {
	if a > b {
		return a
	}
	return b
}

var performanceOptimizerInstance *TaskPerformanceOptimizer

// GetPerformanceOptimizer is get_performance_optimizer.
func GetPerformanceOptimizer() *TaskPerformanceOptimizer {
	if performanceOptimizerInstance == nil {
		performanceOptimizerInstance = NewTaskPerformanceOptimizer(300)
	}
	return performanceOptimizerInstance
}
