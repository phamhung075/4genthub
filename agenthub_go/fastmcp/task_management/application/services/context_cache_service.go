package services

import (
	"context"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextCacheRepository is the minimal repository contract used by ContextCacheService
// (Python duck-typed `repository`). The concrete PG implementation is not ported here.
type ContextCacheRepository interface {
	GetCacheEntry(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error)
	StoreCacheEntry(ctx context.Context, cacheEntry *entities.OrderedMap[any]) error
	UpdateCacheStats(ctx context.Context, level, contextID string, updates *entities.OrderedMap[any]) error
	InvalidateCacheEntry(ctx context.Context, level, contextID, reason string) error
	GetCacheEntriesByLevel(ctx context.Context, level string) ([]*entities.OrderedMap[any], error)
	GetTaskCachesByProject(ctx context.Context, projectID string) ([]*entities.OrderedMap[any], error)
	GetExpiredCacheEntries(ctx context.Context, now time.Time) ([]*entities.OrderedMap[any], error)
	RemoveCacheEntry(ctx context.Context, level, contextID string) error
	GetInvalidatedCacheEntries(ctx context.Context) ([]*entities.OrderedMap[any], error)
	ClearAllCacheEntries(ctx context.Context) (int, error)
	GetCacheStatistics(ctx context.Context) (*entities.OrderedMap[any], error)
	GetTopHitCacheEntries(ctx context.Context, limit int) ([]*entities.OrderedMap[any], error)
	GetLowHitCacheEntries(ctx context.Context, hitThreshold, limit int) ([]*entities.OrderedMap[any], error)
}

// ContextCacheService manages context resolution caching with dependency tracking and
// automatic invalidation (Python application/services/context_cache_service.py).
type ContextCacheService struct {
	repository      ContextCacheRepository
	defaultTTLHours int
	userID          *string
}

// NewContextCacheService mirrors ContextCacheService.__init__
// (default_ttl_hours=1, user_id=None).
func NewContextCacheService(repository ContextCacheRepository, defaultTTLHours int, userID *string) *ContextCacheService {
	return &ContextCacheService{repository: repository, defaultTTLHours: defaultTTLHours, userID: userID}
}

// WithUser mirrors ContextCacheService.with_user.
func (c *ContextCacheService) WithUser(userID string) *ContextCacheService {
	uid := userID
	return NewContextCacheService(c.repository, c.defaultTTLHours, &uid)
}

// Get mirrors ContextCacheService.get (async).
func (c *ContextCacheService) Get(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error) {
	return c.GetCachedContext(ctx, level, contextID)
}

// GetContext mirrors ContextCacheService.get_context. The Python event-loop branches have
// no Go equivalent, so it delegates directly to the async method.
func (c *ContextCacheService) GetContext(ctx context.Context, level, contextID string) *entities.OrderedMap[any] {
	v, _ := c.GetCachedContext(ctx, level, contextID)
	return v
}

// SetContext mirrors ContextCacheService.set_context (dependencies_hash="manual_cache",
// resolution_path=[level]).
func (c *ContextCacheService) SetContext(ctx context.Context, level, contextID string, contextData *entities.OrderedMap[any]) {
	c.CacheResolvedContext(ctx, level, contextID, contextData, "manual_cache", []string{level}, nil)
}

// InvalidateContext mirrors ContextCacheService.invalidate_context.
func (c *ContextCacheService) InvalidateContext(ctx context.Context, level, contextID string) {
	c.InvalidateContextCache(ctx, level, contextID, "manual_invalidation")
}

// ClearCache mirrors ContextCacheService.clear_cache.
func (c *ContextCacheService) ClearCache(ctx context.Context) {
	c.ClearAllCache(ctx)
}

// InvalidateContextCacheSync mirrors ContextCacheService.invalidate_context_cache_sync.
func (c *ContextCacheService) InvalidateContextCacheSync(ctx context.Context, level, contextID string) {
	c.InvalidateContext(ctx, level, contextID)
}

// Invalidate mirrors ContextCacheService.invalidate (async).
func (c *ContextCacheService) Invalidate(ctx context.Context, level, contextID, reason string) bool {
	return c.InvalidateContextCache(ctx, level, contextID, reason)
}

// GetCachedContext mirrors ContextCacheService.get_cached_context.
func (c *ContextCacheService) GetCachedContext(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error) {
	if c.repository == nil {
		return nil, nil
	}
	cacheEntry, err := c.repository.GetCacheEntry(ctx, level, contextID)
	if err != nil || cacheEntry == nil {
		return nil, nil
	}

	if invalidated, ok := cacheEntry.Get("invalidated"); ok && ccsTruthy(invalidated) {
		c.cleanupInvalidatedEntry(ctx, level, contextID)
		return nil, nil
	}

	if expiresAt, ok := cacheEntry.Get("expires_at"); ok && expiresAt != nil {
		expireTime, ok := ccsToTime(expiresAt)
		if ok {
			currentTime := time.Now()
			if currentTime.After(expireTime) {
				c.cleanupExpiredEntry(ctx, level, contextID)
				return nil, nil
			}
		}
	}

	c.updateHitStats(ctx, level, contextID)
	return cacheEntry, nil
}

func ccsToTime(v any) (time.Time, bool) {
	switch x := v.(type) {
	case time.Time:
		return x.UTC(), true
	case string:
		s := x
		if len(s) > 0 && s[len(s)-1] == 'Z' {
			s = s[:len(s)-1] + "+00:00"
		}
		t, err := value_objects.ParseISO(s)
		if err != nil {
			return time.Time{}, false
		}
		return t.UTC(), true
	}
	return time.Time{}, false
}

func (c *ContextCacheService) updateHitStats(ctx context.Context, level, contextID string) {
	if c.repository == nil {
		return
	}
	updates := entities.NewOrderedMap[any]()
	updates.Set("hit_count", "hit_count + 1")
	updates.Set("last_hit", value_objects.IsoFormat(time.Now().UTC()))
	_ = c.repository.UpdateCacheStats(ctx, level, contextID, updates)
}

// CacheResolvedContext mirrors ContextCacheService.cache_resolved_context.
func (c *ContextCacheService) CacheResolvedContext(ctx context.Context, level, contextID string, resolvedContext *entities.OrderedMap[any], dependenciesHash string, resolutionPath []string, ttlHours *int) bool {
	if c.repository == nil {
		return false
	}
	ttl := c.defaultTTLHours
	if ttlHours != nil && *ttlHours != 0 {
		ttl = *ttlHours
	}
	now := time.Now().UTC()
	expiresAt := now.Add(time.Duration(ttl) * time.Hour)

	cacheData := value_objects.PyJSONDumpsDefaultStr(resolvedContext, -1)
	cacheSize := len([]byte(cacheData))

	entry := entities.NewOrderedMap[any]()
	entry.Set("context_id", contextID)
	entry.Set("context_level", level)
	entry.Set("resolved_context", resolvedContext)
	entry.Set("dependencies_hash", dependenciesHash)
	entry.Set("resolution_path", value_objects.PyJSONDumpsDefaultStr(resolutionPath, -1))
	entry.Set("created_at", value_objects.IsoFormat(now))
	entry.Set("expires_at", value_objects.IsoFormat(expiresAt))
	entry.Set("hit_count", 0)
	entry.Set("last_hit", value_objects.IsoFormat(now))
	entry.Set("cache_size_bytes", cacheSize)
	entry.Set("invalidated", false)
	entry.Set("invalidation_reason", nil)

	if err := c.repository.StoreCacheEntry(ctx, entry); err != nil {
		return false
	}
	return true
}

// InvalidateContextCache mirrors ContextCacheService.invalidate_context_cache.
func (c *ContextCacheService) InvalidateContextCache(ctx context.Context, level, contextID, reason string) bool {
	if c.repository == nil {
		return false
	}
	if err := c.repository.InvalidateCacheEntry(ctx, level, contextID, reason); err != nil {
		return false
	}
	return true
}

// InvalidateDependentCaches mirrors ContextCacheService.invalidate_dependent_caches.
func (c *ContextCacheService) InvalidateDependentCaches(ctx context.Context, level, contextID, reason string) []string {
	invalidated := []string{}
	if c.repository == nil {
		return invalidated
	}
	if level == "global" {
		projectCaches, _ := c.repository.GetCacheEntriesByLevel(ctx, "project")
		taskCaches, _ := c.repository.GetCacheEntriesByLevel(ctx, "task")
		for _, cache := range append(projectCaches, taskCaches...) {
			cacheLevel := ccsStr(cache, "context_level")
			cacheID := ccsStr(cache, "context_id")
			c.InvalidateContextCache(ctx, cacheLevel, cacheID, reason)
			invalidated = append(invalidated, cacheLevel+":"+cacheID)
		}
	} else if level == "project" {
		taskCaches, _ := c.repository.GetTaskCachesByProject(ctx, contextID)
		for _, cache := range taskCaches {
			cacheID := ccsStr(cache, "context_id")
			c.InvalidateContextCache(ctx, "task", cacheID, reason)
			invalidated = append(invalidated, "task:"+cacheID)
		}
	}
	return invalidated
}

// CleanupExpired mirrors ContextCacheService.cleanup_expired.
func (c *ContextCacheService) CleanupExpired(ctx context.Context) *entities.OrderedMap[any] {
	now := time.Now().UTC()
	result := entities.NewOrderedMap[any]()
	if c.repository == nil {
		result.Set("success", false)
		result.Set("error", "no repository")
		result.Set("removed_count", 0)
		result.Set("size_freed_bytes", 0)
		return result
	}
	expiredEntries, err := c.repository.GetExpiredCacheEntries(ctx, now)
	if err != nil {
		result.Set("success", false)
		result.Set("error", err.Error())
		result.Set("removed_count", 0)
		result.Set("size_freed_bytes", 0)
		return result
	}

	removedCount := 0
	totalSizeFreed := 0
	for _, entry := range expiredEntries {
		_ = c.repository.RemoveCacheEntry(ctx, ccsStr(entry, "context_level"), ccsStr(entry, "context_id"))
		removedCount++
		totalSizeFreed += ccsIntDefault(entry, "cache_size_bytes", 0)
	}

	result.Set("success", true)
	result.Set("removed_count", removedCount)
	result.Set("size_freed_bytes", totalSizeFreed)
	result.Set("cleaned_at", value_objects.IsoFormat(now))
	return result
}

// CleanupInvalidated mirrors ContextCacheService.cleanup_invalidated.
func (c *ContextCacheService) CleanupInvalidated(ctx context.Context) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	if c.repository == nil {
		result.Set("success", false)
		result.Set("error", "no repository")
		result.Set("removed_count", 0)
		result.Set("size_freed_bytes", 0)
		return result
	}
	invalidatedEntries, err := c.repository.GetInvalidatedCacheEntries(ctx)
	if err != nil {
		result.Set("success", false)
		result.Set("error", err.Error())
		result.Set("removed_count", 0)
		result.Set("size_freed_bytes", 0)
		return result
	}

	removedCount := 0
	totalSizeFreed := 0
	for _, entry := range invalidatedEntries {
		_ = c.repository.RemoveCacheEntry(ctx, ccsStr(entry, "context_level"), ccsStr(entry, "context_id"))
		removedCount++
		totalSizeFreed += ccsIntDefault(entry, "cache_size_bytes", 0)
	}

	result.Set("success", true)
	result.Set("removed_count", removedCount)
	result.Set("size_freed_bytes", totalSizeFreed)
	result.Set("cleaned_at", value_objects.IsoFormat(time.Now().UTC()))
	return result
}

// ClearAllCache mirrors ContextCacheService.clear_all_cache.
func (c *ContextCacheService) ClearAllCache(ctx context.Context) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	if c.repository == nil {
		result.Set("success", false)
		result.Set("error", "no repository")
		result.Set("removed_count", 0)
		return result
	}
	removedCount, err := c.repository.ClearAllCacheEntries(ctx)
	if err != nil {
		result.Set("success", false)
		result.Set("error", err.Error())
		result.Set("removed_count", 0)
		return result
	}
	result.Set("success", true)
	result.Set("removed_count", removedCount)
	result.Set("cleared_at", value_objects.IsoFormat(time.Now().UTC()))
	return result
}

// GetCacheStats mirrors ContextCacheService.get_cache_stats.
func (c *ContextCacheService) GetCacheStats(ctx context.Context) *entities.OrderedMap[any] {
	if c.repository == nil {
		result := entities.NewOrderedMap[any]()
		result.Set("error", "no repository")
		result.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
		return result
	}
	stats, err := c.repository.GetCacheStatistics(ctx)
	if err != nil {
		result := entities.NewOrderedMap[any]()
		result.Set("error", err.Error())
		result.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
		return result
	}
	if stats == nil {
		result := entities.NewOrderedMap[any]()
		result.Set("error", "no cache statistics")
		result.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
		return result
	}

	totalEntries := ccsIntDefault(stats, "total_entries", 0)
	totalSize := ccsIntDefault(stats, "total_size_bytes", 0)
	totalHits := ccsIntDefault(stats, "total_hits", 0)

	hitRate := 0.0
	if totalEntries > 0 {
		avgHitsPerEntry := float64(totalHits) / float64(totalEntries)
		hitRate = minFloat(avgHitsPerEntry/10.0, 1.0)
	}
	avgEntrySize := 0.0
	if totalEntries > 0 {
		avgEntrySize = float64(totalSize) / float64(totalEntries)
	}

	enhanced := stats.Copy()
	performanceMetrics := entities.NewOrderedMap[any]()
	performanceMetrics.Set("hit_rate_estimated", ccoRound(hitRate, 3))
	performanceMetrics.Set("average_entry_size_bytes", ccoRound(avgEntrySize, 2))
	if hitRate > 0.7 {
		performanceMetrics.Set("cache_efficiency", "high")
	} else if hitRate > 0.3 {
		performanceMetrics.Set("cache_efficiency", "medium")
	} else {
		performanceMetrics.Set("cache_efficiency", "low")
	}
	enhanced.Set("performance_metrics", performanceMetrics)

	healthIndicators := entities.NewOrderedMap[any]()
	healthIndicators.Set("expired_entries", ccsIntDefault(stats, "expired_count", 0))
	healthIndicators.Set("invalidated_entries", ccsIntDefault(stats, "invalidated_count", 0))
	if totalEntries > 1000 {
		healthIndicators.Set("cache_pressure", "high")
	} else if totalEntries > 100 {
		healthIndicators.Set("cache_pressure", "medium")
	} else {
		healthIndicators.Set("cache_pressure", "low")
	}
	enhanced.Set("health_indicators", healthIndicators)
	enhanced.Set("timestamp", value_objects.IsoFormat(time.Now().UTC()))
	return enhanced
}

// GetTopCachedContexts mirrors ContextCacheService.get_top_cached_contexts.
func (c *ContextCacheService) GetTopCachedContexts(ctx context.Context, limit int) []*entities.OrderedMap[any] {
	result := []*entities.OrderedMap[any]{}
	if c.repository == nil {
		return result
	}
	topContexts, err := c.repository.GetTopHitCacheEntries(ctx, limit)
	if err != nil {
		return result
	}
	for _, entry := range topContexts {
		item := entities.NewOrderedMap[any]()
		item.Set("level", ccsStr(entry, "context_level"))
		item.Set("context_id", ccsStr(entry, "context_id"))
		item.Set("hit_count", ccsRaw(entry, "hit_count"))
		item.Set("last_hit", ccsRaw(entry, "last_hit"))
		item.Set("cache_size_bytes", ccsRaw(entry, "cache_size_bytes"))
		item.Set("created_at", ccsRaw(entry, "created_at"))
		result = append(result, item)
	}
	return result
}

// OptimizeCache mirrors ContextCacheService.optimize_cache.
func (c *ContextCacheService) OptimizeCache(ctx context.Context) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	if c.repository == nil {
		result.Set("success", false)
		result.Set("error", "no repository")
		result.Set("optimization_started", value_objects.IsoFormat(time.Now().UTC()))
		return result
	}
	result.Set("optimization_started", value_objects.IsoFormat(time.Now().UTC()))
	actionsTaken := []string{}
	result.Set("actions_taken", actionsTaken)
	result.Set("space_freed_bytes", 0)
	result.Set("entries_removed", 0)

	cleanupResult := c.CleanupExpired(ctx)
	if ccsTruthy(ccsGet(cleanupResult, "success")) {
		actionsTaken = append(actionsTaken, "cleaned_expired")
		result.Set("actions_taken", actionsTaken)
		result.Set("space_freed_bytes", ccsGetInt(result, "space_freed_bytes")+ccsIntDefault(cleanupResult, "size_freed_bytes", 0))
		result.Set("entries_removed", ccsGetInt(result, "entries_removed")+ccsIntDefault(cleanupResult, "removed_count", 0))
	}

	invalidatedResult := c.CleanupInvalidated(ctx)
	if ccsTruthy(ccsGet(invalidatedResult, "success")) {
		actionsTaken = append(actionsTaken, "cleaned_invalidated")
		result.Set("actions_taken", actionsTaken)
		result.Set("space_freed_bytes", ccsGetInt(result, "space_freed_bytes")+ccsIntDefault(invalidatedResult, "size_freed_bytes", 0))
		result.Set("entries_removed", ccsGetInt(result, "entries_removed")+ccsIntDefault(invalidatedResult, "removed_count", 0))
	}

	stats := c.GetCacheStats(ctx)
	totalEntries := ccsIntDefault(stats, "total_entries", 0)
	if totalEntries > 500 {
		lowHitEntries, _ := c.repository.GetLowHitCacheEntries(ctx, 2, 50)
		removedLowHit := 0
		for _, entry := range lowHitEntries {
			_ = c.repository.RemoveCacheEntry(ctx, ccsStr(entry, "context_level"), ccsStr(entry, "context_id"))
			removedLowHit++
			result.Set("space_freed_bytes", ccsGetInt(result, "space_freed_bytes")+ccsIntDefault(entry, "cache_size_bytes", 0))
		}
		if removedLowHit > 0 {
			actionsTaken = append(actionsTaken, "removed_"+ccsItoa(removedLowHit)+"_low_hit_entries")
			result.Set("actions_taken", actionsTaken)
			result.Set("entries_removed", ccsGetInt(result, "entries_removed")+removedLowHit)
		}
	}

	result.Set("optimization_completed", value_objects.IsoFormat(time.Now().UTC()))
	result.Set("success", true)
	return result
}

// CleanupExpiredEntry/cleanup helpers

func (c *ContextCacheService) cleanupExpiredEntry(ctx context.Context, level, contextID string) {
	if c.repository == nil {
		return
	}
	_ = c.repository.RemoveCacheEntry(ctx, level, contextID)
}

func (c *ContextCacheService) cleanupInvalidatedEntry(ctx context.Context, level, contextID string) {
	if c.repository == nil {
		return
	}
	_ = c.repository.RemoveCacheEntry(ctx, level, contextID)
}

// WarmCache mirrors ContextCacheService.warm_cache.
func (c *ContextCacheService) WarmCache(ctx context.Context, contextsToWarm []map[string]string) *entities.OrderedMap[any] {
	warmedCount := 0
	failedCount := 0
	for _, spec := range contextsToWarm {
		_ = spec["level"]
		_ = spec["context_id"]
		warmedCount++
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("warmed_count", warmedCount)
	result.Set("failed_count", failedCount)
	result.Set("total_requested", len(contextsToWarm))
	return result
}

// GetCacheHealth mirrors ContextCacheService.get_cache_health.
func (c *ContextCacheService) GetCacheHealth(ctx context.Context) *entities.OrderedMap[any] {
	stats := c.GetCacheStats(ctx)

	entriesByLevel, _ := stats.Get("entries_by_level")
	byLevel, _ := entriesByLevel.(*entities.OrderedMap[any])

	performanceMetrics, _ := stats.Get("performance_metrics")
	perf, _ := performanceMetrics.(*entities.OrderedMap[any])

	healthIndicators, _ := stats.Get("health_indicators")
	health, _ := healthIndicators.(*entities.OrderedMap[any])

	hitRate := 0.0
	if perf != nil {
		if v, ok := perf.Get("hit_rate_estimated"); ok {
			hitRate = ccsFloat(v)
		}
	}

	result := entities.NewOrderedMap[any]()
	cacheEntries := entities.NewOrderedMap[any]()
	cacheEntries.Set("global", ccsNestedInt(byLevel, "global"))
	cacheEntries.Set("project", ccsNestedInt(byLevel, "project"))
	cacheEntries.Set("branch", ccsNestedInt(byLevel, "branch"))
	cacheEntries.Set("task", ccsNestedInt(byLevel, "task"))
	result.Set("cache_entries", cacheEntries)
	result.Set("cache_hit_rate", hitRate)
	result.Set("cache_miss_rate", 1.0-hitRate)
	if v, ok := stats.Get("average_resolution_time_ms"); ok {
		result.Set("average_resolution_time_ms", v)
	} else {
		result.Set("average_resolution_time_ms", 0.0)
	}
	result.Set("expired_entries", ccsNestedInt(health, "expired_entries"))
	return result
}

func ccsGet(d *entities.OrderedMap[any], key string) any {
	if d == nil {
		return nil
	}
	v, _ := d.Get(key)
	return v
}

func ccsGetInt(d *entities.OrderedMap[any], key string) int {
	return ccsToIntAny(ccsGet(d, key))
}

func ccsStr(d *entities.OrderedMap[any], key string) string {
	if d == nil {
		return ""
	}
	v, _ := d.Get(key)
	return value_objects.PyStr(v)
}

func ccsRaw(d *entities.OrderedMap[any], key string) any {
	if d == nil {
		return nil
	}
	v, _ := d.Get(key)
	return v
}

func ccsIntDefault(d *entities.OrderedMap[any], key string, def int) int {
	if d == nil {
		return def
	}
	v, ok := d.Get(key)
	if !ok || v == nil {
		return def
	}
	return ccsToIntAny(v)
}

func ccsToIntAny(v any) int {
	switch x := v.(type) {
	case int:
		return x
	case int64:
		return int(x)
	case float64:
		return int(x)
	case bool:
		if x {
			return 1
		}
		return 0
	}
	return 0
}

func ccsFloat(v any) float64 {
	switch x := v.(type) {
	case float64:
		return x
	case int:
		return float64(x)
	case int64:
		return float64(x)
	}
	return 0
}

func ccsNestedInt(d *entities.OrderedMap[any], key string) int {
	if d == nil {
		return 0
	}
	v, ok := d.Get(key)
	if !ok || v == nil {
		return 0
	}
	return ccsToIntAny(v)
}

func ccsTruthy(v any) bool {
	b, ok := v.(bool)
	if ok {
		return b
	}
	return v != nil
}

func minFloat(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func ccsItoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
