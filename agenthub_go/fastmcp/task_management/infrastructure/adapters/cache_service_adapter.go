// Package adapters ports task_management/infrastructure/adapters.
//
// cache_service_adapter.go ports cache_service_adapter.py.
package adapters

import (
	"context"
	"sort"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/interfaces"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CacheKeyBuilderAdapter is cache_service_adapter.CacheKeyBuilderAdapter.
type CacheKeyBuilderAdapter struct{}

var _ interfaces.ICacheKeyBuilder = (*CacheKeyBuilderAdapter)(nil)

func NewCacheKeyBuilderAdapter() *CacheKeyBuilderAdapter {
	return &CacheKeyBuilderAdapter{}
}

// BuildKey mirrors build_key.
func (a *CacheKeyBuilderAdapter) BuildKey(prefix string, args []any, kwargs map[string]any) string {
	parts := []string{prefix}
	for _, arg := range args {
		parts = append(parts, value_objects.PyStr(arg))
	}
	keys := make([]string, 0, len(kwargs))
	for k := range kwargs {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		parts = append(parts, k+":"+value_objects.PyStr(kwargs[k]))
	}
	out := ""
	for i, p := range parts {
		if i > 0 {
			out += ":"
		}
		out += p
	}
	return out
}

// BuildPattern mirrors build_pattern.
func (a *CacheKeyBuilderAdapter) BuildPattern(prefix, pattern string) string {
	return prefix + ":" + pattern
}

type cacheItem struct {
	val       any
	expiresAt *time.Time
}

// CacheServiceAdapter implements interfaces.ICacheService.
type CacheServiceAdapter struct {
	items map[string]cacheItem
	mu    sync.RWMutex
}

var _ interfaces.ICacheService = (*CacheServiceAdapter)(nil)

func NewCacheServiceAdapter() *CacheServiceAdapter {
	return &CacheServiceAdapter{
		items: make(map[string]cacheItem),
	}
}

func (c *CacheServiceAdapter) Get(ctx context.Context, key string) (any, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	item, ok := c.items[key]
	if !ok {
		return nil, nil
	}
	if item.expiresAt != nil && time.Now().After(*item.expiresAt) {
		return nil, nil
	}
	return item.val, nil
}

func (c *CacheServiceAdapter) Set(ctx context.Context, key string, value any, ttl *time.Duration) (bool, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	var exp *time.Time
	if ttl != nil {
		t := time.Now().Add(*ttl)
		exp = &t
	}
	c.items[key] = cacheItem{val: value, expiresAt: exp}
	return true, nil
}

func (c *CacheServiceAdapter) Delete(ctx context.Context, key string) (bool, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	_, ok := c.items[key]
	delete(c.items, key)
	return ok, nil
}

func (c *CacheServiceAdapter) Exists(ctx context.Context, key string) (bool, error) {
	val, _ := c.Get(ctx, key)
	return val != nil, nil
}

func (c *CacheServiceAdapter) Clear(ctx context.Context) (bool, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.items = make(map[string]cacheItem)
	return true, nil
}

func (c *CacheServiceAdapter) GetMany(ctx context.Context, keys []string) (map[string]any, error) {
	res := make(map[string]any)
	for _, k := range keys {
		v, _ := c.Get(ctx, k)
		if v != nil {
			res[k] = v
		}
	}
	return res, nil
}

func (c *CacheServiceAdapter) SetMany(ctx context.Context, mapping map[string]any, ttl *time.Duration) (bool, error) {
	for k, v := range mapping {
		_, _ = c.Set(ctx, k, v, ttl)
	}
	return true, nil
}

func (c *CacheServiceAdapter) DeleteMany(ctx context.Context, keys []string) (int, error) {
	cnt := 0
	for _, k := range keys {
		deleted, _ := c.Delete(ctx, k)
		if deleted {
			cnt++
		}
	}
	return cnt, nil
}

func (c *CacheServiceAdapter) Increment(ctx context.Context, key string, delta int) (int, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	item, ok := c.items[key]
	var current int
	if ok {
		if i, ok := item.val.(int); ok {
			current = i
		}
	}
	current += delta
	c.items[key] = cacheItem{val: current, expiresAt: item.expiresAt}
	return current, nil
}

func (c *CacheServiceAdapter) Decrement(ctx context.Context, key string, delta int) (int, error) {
	return c.Increment(ctx, key, -delta)
}

func (c *CacheServiceAdapter) Expire(ctx context.Context, key string, ttl time.Duration) (bool, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	item, ok := c.items[key]
	if !ok {
		return false, nil
	}
	t := time.Now().Add(ttl)
	item.expiresAt = &t
	c.items[key] = item
	return true, nil
}

func (c *CacheServiceAdapter) GetTTL(ctx context.Context, key string) (*int, error) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	item, ok := c.items[key]
	if !ok || item.expiresAt == nil {
		return nil, nil
	}
	secs := int(time.Until(*item.expiresAt).Seconds())
	if secs < 0 {
		return nil, nil
	}
	return &secs, nil
}
