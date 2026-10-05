package utilities

import "time"

// TimedCacheNotFound is Python's TimedCache.NOT_FOUND sentinel (a unique object()).
// Returned by Get when the key is missing or expired.
var TimedCacheNotFound = &struct{}{}

type timedCacheEntry struct {
	Value   any
	Expires time.Time
}

// TimedCache mirrors utilities.cache.TimedCache: a dict of key -> (value, expires).
type TimedCache struct {
	Expiration time.Duration
	Cache      map[any]timedCacheEntry
}

// NewTimedCache builds an empty cache with the given expiration.
func NewTimedCache(expiration time.Duration) *TimedCache {
	return &TimedCache{Expiration: expiration, Cache: map[any]timedCacheEntry{}}
}

// Set stores value under key with an expiration of now + Expiration.
func (c *TimedCache) Set(key, value any) {
	if c.Cache == nil {
		c.Cache = map[any]timedCacheEntry{}
	}
	c.Cache[key] = timedCacheEntry{Value: value, Expires: time.Now().UTC().Add(c.Expiration)}
}

// Get returns the value if it exists and has not expired, else TimedCacheNotFound.
// As in Python, an expired entry is not deleted.
func (c *TimedCache) Get(key any) any {
	if c.Cache == nil {
		return TimedCacheNotFound
	}
	entry, ok := c.Cache[key]
	if ok && entry.Expires.After(time.Now().UTC()) {
		return entry.Value
	}
	return TimedCacheNotFound
}

// Clear empties the cache.
func (c *TimedCache) Clear() { clear(c.Cache) }
