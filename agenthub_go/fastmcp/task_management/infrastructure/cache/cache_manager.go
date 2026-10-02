// Package cache ports task_management/infrastructure/cache.
package cache

import (
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// cacheClock mirrors time.time() (float seconds since the epoch). It is a package
// variable so tests can make TTL checks deterministic.
var cacheClock = func() float64 { return float64(time.Now().UnixNano()) / 1e9 }

// CacheEntry represents a single cache entry (cache_manager.CacheEntry).
type CacheEntry struct {
	Key       string
	Value     any
	CreatedAt float64
	TTL       int
	Hits      int
}

// NewCacheEntry applies the Python dataclass defaults (hits=0).
func NewCacheEntry(key string, value any, createdAt float64, ttl int) *CacheEntry {
	return &CacheEntry{Key: key, Value: value, CreatedAt: createdAt, TTL: ttl}
}

// IsExpired mirrors CacheEntry.is_expired: a ttl <= 0 never expires.
func (e *CacheEntry) IsExpired() bool {
	if e.TTL <= 0 {
		return false
	}
	return (cacheClock() - e.CreatedAt) > float64(e.TTL)
}

// IncrementHits mirrors CacheEntry.increment_hits.
func (e *CacheEntry) IncrementHits() { e.Hits++ }

// CacheManager is a thread-safe in-memory cache with TTL and LRU eviction
// (cache_manager.CacheManager).
type CacheManager struct {
	mu         sync.Mutex
	cache      *entities.OrderedMap[*CacheEntry]
	maxSize    int
	defaultTTL int

	stats map[string]int
}

// NewCacheManager returns a cache with the Python constructor defaults
// (max_size=1000, default_ttl=300).
func NewCacheManager() *CacheManager { return NewCacheManagerWith(1000, 300) }

// NewCacheManagerWith mirrors CacheManager(max_size, default_ttl).
func NewCacheManagerWith(maxSize, defaultTTL int) *CacheManager {
	return &CacheManager{
		cache:      entities.NewOrderedMap[*CacheEntry](),
		maxSize:    maxSize,
		defaultTTL: defaultTTL,
		stats:      map[string]int{"hits": 0, "misses": 0, "evictions": 0, "expirations": 0, "sets": 0},
	}
}

// Get mirrors CacheManager.get; an expired entry is removed and counted.
func (c *CacheManager) Get(key string) any {
	c.mu.Lock()
	defer c.mu.Unlock()
	entry, ok := c.cache.Get(key)
	if !ok {
		c.stats["misses"]++
		return nil
	}
	if entry.IsExpired() {
		c.cache.Delete(key)
		c.stats["expirations"]++
		c.stats["misses"]++
		return nil
	}
	// Move to end (LRU): OrderedMap.Set on an existing key keeps its position.
	c.cache.Delete(key)
	c.cache.Set(key, entry)
	entry.IncrementHits()
	c.stats["hits"]++
	return entry.Value
}

// Set mirrors CacheManager.set; a nil ttl uses the default.
func (c *CacheManager) Set(key string, value any, ttl *int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.cache.Has(key) {
		c.cache.Delete(key)
	}
	if c.cache.Len() >= c.maxSize && c.cache.Len() > 0 {
		evictedKey := c.cache.Keys()[0]
		c.cache.Delete(evictedKey)
		c.stats["evictions"]++
	}
	t := c.defaultTTL
	if ttl != nil {
		t = *ttl
	}
	c.cache.Set(key, &CacheEntry{Key: key, Value: value, CreatedAt: cacheClock(), TTL: t})
	c.stats["sets"]++
}

// Delete mirrors CacheManager.delete.
func (c *CacheManager) Delete(key string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.cache.Has(key) {
		return false
	}
	c.cache.Delete(key)
	return true
}

// Clear mirrors CacheManager.clear.
func (c *CacheManager) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.cache = entities.NewOrderedMap[*CacheEntry]()
}

// GetStats mirrors CacheManager.get_stats.
func (c *CacheManager) GetStats() *entities.OrderedMap[any] {
	c.mu.Lock()
	defer c.mu.Unlock()
	total := c.stats["hits"] + c.stats["misses"]
	var hitRate any = 0
	if total > 0 {
		hitRate = float64(c.stats["hits"]) / float64(total)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("hits", c.stats["hits"])
	out.Set("misses", c.stats["misses"])
	out.Set("evictions", c.stats["evictions"])
	out.Set("expirations", c.stats["expirations"])
	out.Set("sets", c.stats["sets"])
	out.Set("size", c.cache.Len())
	out.Set("max_size", c.maxSize)
	out.Set("hit_rate", hitRate)
	out.Set("total_requests", total)
	return out
}

// CleanupExpired mirrors CacheManager.cleanup_expired and returns the number removed.
func (c *CacheManager) CleanupExpired() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	var expired []string
	for _, key := range c.cache.Keys() {
		entry, _ := c.cache.Get(key)
		if entry.IsExpired() {
			expired = append(expired, key)
		}
	}
	for _, key := range expired {
		c.cache.Delete(key)
		c.stats["expirations"]++
	}
	return len(expired)
}

// Global cache instances (cache_manager._cache_instances / get_cache). The Python
// get_cache kwargs are not reproduced; every named cache uses the defaults, which is
// what all Python callers pass.
var (
	cacheInstancesMu sync.Mutex
	cacheInstances   = map[string]*CacheManager{}
)

// GetCache returns the named cache, creating it with the default configuration on
// first use (cache_manager.get_cache).
func GetCache(name string) *CacheManager {
	cacheInstancesMu.Lock()
	defer cacheInstancesMu.Unlock()
	if cm, ok := cacheInstances[name]; ok {
		return cm
	}
	cm := NewCacheManager()
	cacheInstances[name] = cm
	return cm
}

// CachedRepository adds caching to repositories (cache_manager.CachedRepository). The
// Python mixin's cooperative __init__ has no Go equivalent; className replaces
// self.__class__.__name__ when cacheName is nil.
type CachedRepository struct {
	CacheName string
	Cache     *CacheManager
}

// NewCachedRepository mirrors CachedRepository.__init__'s cache selection.
func NewCachedRepository(className string, cacheName *string) *CachedRepository {
	name := className + "_cache"
	if cacheName != nil {
		name = *cacheName
	}
	return &CachedRepository{CacheName: name, Cache: GetCache(name)}
}

// InvalidateCache mirrors CachedRepository.invalidate_cache: a nil pattern clears all,
// otherwise keys containing pattern are removed.
func (r *CachedRepository) InvalidateCache(pattern *string) {
	if pattern == nil {
		r.Cache.Clear()
		return
	}
	r.Cache.mu.Lock()
	defer r.Cache.mu.Unlock()
	var keysToDelete []string
	for _, key := range r.Cache.cache.Keys() {
		if strings.Contains(key, *pattern) {
			keysToDelete = append(keysToDelete, key)
		}
	}
	for _, key := range keysToDelete {
		r.Cache.cache.Delete(key)
	}
}

// GetCacheStats mirrors CachedRepository.get_cache_stats.
func (r *CachedRepository) GetCacheStats() *entities.OrderedMap[any] { return r.Cache.GetStats() }
