package cached

// Shared cache plumbing for the cached repository wrappers
// (Python infrastructure/repositories/cached/cached_*.py).
//
// The Python wrappers build a redis-py client from REDIS_HOST/REDIS_PORT/... and disable
// caching when the connection test fails. Go has no Redis client in this module (the
// go-redis dependency is not in go.mod), so the client is injected through CacheClient and
// MemoryCache provides an in-process implementation with an injectable clock. Cache keys,
// namespaces, TTL and the SCAN/glob invalidation patterns are reproduced exactly.

import (
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// CacheClient is the subset of the redis-py client used by the cached wrappers.
type CacheClient interface {
	// Get returns the stored value (false when absent/expired), like redis GET.
	Get(key string) (any, bool)
	// SetEX stores value with the given TTL in seconds (redis SETEX).
	SetEX(key string, ttlSeconds int, value any)
	// Delete removes the given keys (redis DEL).
	Delete(keys ...string)
	// Scan returns the keys matching the glob pattern (redis SCAN MATCH).
	Scan(match string) []string
	// Ping tests the connection (redis PING).
	Ping() error
}

// memoryCacheEntry is one in-process cache entry.
type memoryCacheEntry struct {
	value     any
	expiresAt time.Time
}

// MemoryCache is an in-process CacheClient. The clock is injectable so TTL expiry is
// deterministic in tests.
type MemoryCache struct {
	mu      sync.Mutex
	entries map[string]*memoryCacheEntry
	clock   func() time.Time
}

// NewMemoryCache builds the cache; a nil clock uses time.Now.
func NewMemoryCache(clock func() time.Time) *MemoryCache {
	if clock == nil {
		clock = time.Now
	}
	return &MemoryCache{entries: map[string]*memoryCacheEntry{}, clock: clock}
}

// Get returns the entry value, evicting it when expired.
func (m *MemoryCache) Get(key string) (any, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	entry, ok := m.entries[key]
	if !ok {
		return nil, false
	}
	if !entry.expiresAt.IsZero() && !m.clock().Before(entry.expiresAt) {
		delete(m.entries, key)
		return nil, false
	}
	return entry.value, true
}

// SetEX stores value; ttlSeconds <= 0 means no expiry (redis rejects it, but no caller uses it).
func (m *MemoryCache) SetEX(key string, ttlSeconds int, value any) {
	entry := &memoryCacheEntry{value: value}
	if ttlSeconds > 0 {
		entry.expiresAt = m.clock().Add(time.Duration(ttlSeconds) * time.Second)
	}
	m.mu.Lock()
	defer m.mu.Unlock()
	m.entries[key] = entry
}

// Delete removes the given keys.
func (m *MemoryCache) Delete(keys ...string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, k := range keys {
		delete(m.entries, k)
	}
}

// Scan returns every non-expired key matching the glob pattern.
func (m *MemoryCache) Scan(match string) []string {
	m.mu.Lock()
	defer m.mu.Unlock()
	now := m.clock()
	out := []string{}
	for k, entry := range m.entries {
		if !entry.expiresAt.IsZero() && !now.Before(entry.expiresAt) {
			delete(m.entries, k)
			continue
		}
		if cachedGlobMatch(match, k) {
			out = append(out, k)
		}
	}
	return out
}

// Ping always succeeds.
func (m *MemoryCache) Ping() error { return nil }

// cachedCache is the shared key-namespacing / TTL / invalidation behaviour.
type cachedCache struct {
	client    CacheClient
	namespace string
	ttl       int
}

func newCachedCache(client CacheClient, namespace string, ttl int) cachedCache {
	if client != nil {
		if err := client.Ping(); err != nil {
			client = nil
		}
	}
	return cachedCache{client: client, namespace: namespace, ttl: ttl}
}

func (c cachedCache) enabled() bool { return c.client != nil }

// key mirrors `_cache_key`: "<namespace>:<key>".
func (c cachedCache) key(k string) string { return c.namespace + ":" + k }

// invalidateKey mirrors `_invalidate_key`.
func (c cachedCache) invalidateKey(k string) {
	if c.client == nil {
		return
	}
	c.client.Delete(c.key(k))
}

// invalidatePattern mirrors `_invalidate_pattern`: SCAN the namespaced glob then DEL.
func (c cachedCache) invalidatePattern(pattern string) {
	if c.client == nil {
		return
	}
	keys := c.client.Scan(c.key(pattern))
	if len(keys) > 0 {
		c.client.Delete(keys...)
	}
}

// get mirrors `_get_cached` (nil when disabled / absent).
func (c cachedCache) get(k string) any {
	if c.client == nil {
		return nil
	}
	v, ok := c.client.Get(c.key(k))
	if !ok {
		return nil
	}
	return v
}

// set mirrors `_set_cached`.
func (c cachedCache) set(k string, v any) {
	if c.client == nil {
		return
	}
	c.client.SetEX(c.key(k), c.ttl, v)
}

// cachedTTLFromEnv is int(os.getenv("CACHE_TTL", "300")).
func cachedTTLFromEnv(getenv func(string) string) (int, error) {
	if getenv == nil {
		getenv = os.Getenv
	}
	raw := getenv("CACHE_TTL")
	if raw == "" {
		raw = "300"
	}
	ttl, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return 0, &tmvo.ValueError{Msg: "invalid literal for int() with base 10: '" + raw + "'"}
	}
	return ttl, nil
}

// cachedEnv returns the environment value or "".
func cachedEnv(getenv func(string) string, key string) string {
	if getenv == nil {
		return os.Getenv(key)
	}
	return getenv(key)
}

// cachedGlobMatch implements redis glob matching (*, ?, [...] and backslash escapes).
func cachedGlobMatch(pattern, s string) bool {
	p := []rune(pattern)
	str := []rune(s)
	var match func(pi, si int) bool
	match = func(pi, si int) bool {
		for pi < len(p) {
			switch p[pi] {
			case '*':
				for pi+1 < len(p) && p[pi+1] == '*' {
					pi++
				}
				if pi+1 == len(p) {
					return true
				}
				for k := si; k <= len(str); k++ {
					if match(pi+1, k) {
						return true
					}
				}
				return false
			case '?':
				if si >= len(str) {
					return false
				}
				pi++
				si++
			case '[':
				if si >= len(str) {
					return false
				}
				end := pi + 1
				neg := false
				if end < len(p) && (p[end] == '^' || p[end] == '!') {
					neg = true
					end++
				}
				startClass := end
				if end < len(p) && p[end] == ']' {
					end++
				}
				for end < len(p) && p[end] != ']' {
					end++
				}
				if end >= len(p) {
					if str[si] != '[' {
						return false
					}
					pi++
					si++
					continue
				}
				matched := false
				for i := startClass; i < end; i++ {
					if i+2 < end && p[i+1] == '-' {
						if str[si] >= p[i] && str[si] <= p[i+2] {
							matched = true
						}
						i += 2
					} else if p[i] == str[si] {
						matched = true
					}
				}
				if matched == neg {
					return false
				}
				pi = end + 1
				si++
			case '\\':
				if pi+1 < len(p) {
					pi++
				}
				if si >= len(str) || p[pi] != str[si] {
					return false
				}
				pi++
				si++
			default:
				if si >= len(str) || p[pi] != str[si] {
					return false
				}
				pi++
				si++
			}
		}
		return si == len(str)
	}
	return match(0, 0)
}
