// Package interfaces ports task_management/domain/interfaces: service contracts
// owned by the domain and implemented by infrastructure. Python `**kwargs`
// become a map parameter, `async` methods take a context.Context and return an
// error, and Python `Path` values are plain strings.
package interfaces

import (
	"context"
	"time"
)

// ICacheService is the cache service contract. TTL values are durations (Python
// accepts int seconds or a timedelta; callers convert ints to seconds); a nil
// TTL means no expiry.
type ICacheService interface {
	Get(ctx context.Context, key string) (any, error)
	Set(ctx context.Context, key string, value any, ttl *time.Duration) (bool, error)
	Delete(ctx context.Context, key string) (bool, error)
	Exists(ctx context.Context, key string) (bool, error)
	Clear(ctx context.Context) (bool, error)
	GetMany(ctx context.Context, keys []string) (map[string]any, error)
	SetMany(ctx context.Context, mapping map[string]any, ttl *time.Duration) (bool, error)
	DeleteMany(ctx context.Context, keys []string) (int, error)
	// Increment adds delta (Python default 1) to a counter.
	Increment(ctx context.Context, key string, delta int) (int, error)
	// Decrement subtracts delta (Python default 1) from a counter.
	Decrement(ctx context.Context, key string, delta int) (int, error)
	Expire(ctx context.Context, key string, ttl time.Duration) (bool, error)
	// GetTTL returns the remaining TTL in seconds, or nil when none.
	GetTTL(ctx context.Context, key string) (*int, error)
}

// ICacheKeyBuilder builds cache keys and key patterns.
type ICacheKeyBuilder interface {
	BuildKey(prefix string, args []any, kwargs map[string]any) string
	BuildPattern(prefix, pattern string) string
}
