// Package cache ports fastmcp/server/cache/redis_cache_decorator.py.
package cache

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"sync"
	"time"
)

// RedisCacheManager manages in-memory/Redis caching with TTL.
type RedisCacheManager struct {
	mu         sync.RWMutex
	store      map[string]cacheEntry
	RedisURL   string
	DefaultTTL time.Duration
	Prefix     string
}

type cacheEntry struct {
	value     any
	expiresAt time.Time
}

// NewRedisCacheManager creates a new cache manager.
func NewRedisCacheManager(redisURL string, defaultTTLSeconds int, prefix string) *RedisCacheManager {
	if redisURL == "" {
		redisURL = os.Getenv("REDIS_URL")
		if redisURL == "" {
			redisURL = "redis://localhost:6379"
		}
	}
	if defaultTTLSeconds <= 0 {
		defaultTTLSeconds = 300
	}
	if prefix == "" {
		prefix = "api_cache"
	}
	return &RedisCacheManager{
		store:      make(map[string]cacheEntry),
		RedisURL:   redisURL,
		DefaultTTL: time.Duration(defaultTTLSeconds) * time.Second,
		Prefix:     prefix,
	}
}

// BuildKey generates a cache key with prefix and hash.
func (m *RedisCacheManager) BuildKey(parts ...string) string {
	h := sha256.New()
	for _, p := range parts {
		h.Write([]byte(p))
	}
	return fmt.Sprintf("%s:%s", m.Prefix, hex.EncodeToString(h.Sum(nil))[:16])
}

// Get retrieves a cached value if not expired.
func (m *RedisCacheManager) Get(key string) (any, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	entry, ok := m.store[key]
	if !ok || time.Now().After(entry.expiresAt) {
		return nil, false
	}
	return entry.value, true
}

// Set stores a value with TTL.
func (m *RedisCacheManager) Set(key string, value any, ttl ...time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()
	t := m.DefaultTTL
	if len(ttl) > 0 && ttl[0] > 0 {
		t = ttl[0]
	}
	m.store[key] = cacheEntry{
		value:     value,
		expiresAt: time.Now().Add(t),
	}
}

// Delete removes a key from cache.
func (m *RedisCacheManager) Delete(key string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.store, key)
}

// Clear clears all cache entries.
func (m *RedisCacheManager) Clear() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.store = make(map[string]cacheEntry)
}

// GlobalManager is the default global cache manager.
var GlobalManager = NewRedisCacheManager("", 300, "api_cache")

// CacheInvalidator provides invalidation methods for tasks, subtasks and contexts.
type CacheInvalidator struct{}

// InvalidateTaskCache invalidates cached task summaries.
func (CacheInvalidator) InvalidateTaskCache(ctx context.Context, taskID ...string) error {
	GlobalManager.Clear()
	return nil
}

// InvalidateSubtaskCache invalidates cached subtask data.
func (CacheInvalidator) InvalidateSubtaskCache(ctx context.Context, parentTaskID ...string) error {
	GlobalManager.Clear()
	return nil
}

// InvalidateContextCache invalidates cached context data.
func (CacheInvalidator) InvalidateContextCache(ctx context.Context, contextID ...string) error {
	GlobalManager.Clear()
	return nil
}
