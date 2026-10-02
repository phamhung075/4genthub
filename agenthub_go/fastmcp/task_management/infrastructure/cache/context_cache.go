package cache

import (
	"bytes"
	"compress/zlib"
	"encoding/base64"
	"regexp"
	"sort"
	"strings"
	"sync"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// InMemoryCache is the fallback cache used when Redis is unavailable
// (context_cache.InMemoryCache). Redis is not ported, so this is always the backend.
type InMemoryCache struct {
	Cache  *entities.OrderedMap[string]
	TTLMap *entities.OrderedMap[float64]
}

// NewInMemoryCache builds an empty in-memory cache.
func NewInMemoryCache() *InMemoryCache {
	return &InMemoryCache{Cache: entities.NewOrderedMap[string](), TTLMap: entities.NewOrderedMap[float64]()}
}

// Get mirrors InMemoryCache.get; ok is false when the key is missing or expired.
func (c *InMemoryCache) Get(key string) (string, bool) {
	if v, ok := c.Cache.Get(key); ok {
		if exp, hasTTL := c.TTLMap.Get(key); hasTTL && cacheClock() > exp {
			c.Cache.Delete(key)
			c.TTLMap.Delete(key)
			return "", false
		}
		return v, true
	}
	return "", false
}

// Setex mirrors InMemoryCache.setex.
func (c *InMemoryCache) Setex(key string, ttl int, value string) {
	c.Cache.Set(key, value)
	c.TTLMap.Set(key, cacheClock()+float64(ttl))
}

// Delete mirrors InMemoryCache.delete.
func (c *InMemoryCache) Delete(key string) {
	c.Cache.Delete(key)
	c.TTLMap.Delete(key)
}

// ScanIter mirrors InMemoryCache.scan_iter: "*" becomes ".*" and the pattern is
// matched at the start of the key (re.match), in cache insertion order.
// An invalid pattern is re.error in Python, raised when the first key is matched (re.match
// compiles lazily), so an empty cache never fails.
func (c *InMemoryCache) ScanIter(pattern string) ([]string, error) {
	keys := c.Cache.Keys()
	if len(keys) == 0 {
		return nil, nil
	}
	re, err := regexp.Compile("^(?:" + strings.ReplaceAll(pattern, "*", ".*") + ")")
	if err != nil {
		return nil, err
	}
	var out []string
	for _, k := range keys {
		if re.MatchString(k) {
			out = append(out, k)
		}
	}
	return out, nil
}

// Pipeline mirrors InMemoryCache.pipeline.
func (c *InMemoryCache) Pipeline() *InMemoryPipeline { return &InMemoryPipeline{cache: c} }

// Ping mirrors InMemoryCache.ping.
func (c *InMemoryCache) Ping() bool { return true }

type pipelineOp struct {
	kind  string
	key   string
	ttl   int
	value string
}

// InMemoryPipeline batches in-memory cache operations (context_cache.InMemoryPipeline).
type InMemoryPipeline struct {
	cache      *InMemoryCache
	operations []pipelineOp
}

// Get queues a get.
func (p *InMemoryPipeline) Get(key string) *InMemoryPipeline {
	p.operations = append(p.operations, pipelineOp{kind: "get", key: key})
	return p
}

// Setex queues a setex.
func (p *InMemoryPipeline) Setex(key string, ttl int, value string) *InMemoryPipeline {
	p.operations = append(p.operations, pipelineOp{kind: "setex", key: key, ttl: ttl, value: value})
	return p
}

// Delete queues a delete.
func (p *InMemoryPipeline) Delete(key string) *InMemoryPipeline {
	p.operations = append(p.operations, pipelineOp{kind: "delete", key: key})
	return p
}

// Execute runs the queued operations in order and returns their results.
func (p *InMemoryPipeline) Execute() []any {
	results := []any{}
	for _, op := range p.operations {
		switch op.kind {
		case "get":
			if v, ok := p.cache.Get(op.key); ok {
				results = append(results, v)
			} else {
				results = append(results, nil)
			}
		case "setex":
			p.cache.Setex(op.key, op.ttl, op.value)
			results = append(results, true)
		case "delete":
			p.cache.Delete(op.key)
			results = append(results, true)
		}
	}
	return results
}

// ContextRef identifies a cached context (the dicts passed to the batch methods).
type ContextRef struct {
	Level     string
	ContextID string
}

// ContextEntry is a ContextRef with the data cached by SetMultipleContexts.
type ContextEntry struct {
	Level     string
	ContextID string
	Data      *entities.OrderedMap[any]
}

// ContextCache is the caching layer for context operations (context_cache.ContextCache).
// The Python Redis path is not ported: with no Redis package available Python falls back
// to InMemoryCache, which is the only backend implemented here.
type ContextCache struct {
	TTL               int
	EnableCompression bool
	Redis             *InMemoryCache
	UseRedis          bool
}

// NewContextCache applies the Python constructor defaults
// (redis_db=1, ttl_seconds=300, enable_compression=True).
func NewContextCache() *ContextCache {
	return NewContextCacheWith(1, 300, true)
}

// NewContextCacheWith mirrors the non-Redis branch of ContextCache.__init__.
func NewContextCacheWith(redisDB, ttlSeconds int, enableCompression bool) *ContextCache {
	return &ContextCache{TTL: ttlSeconds, EnableCompression: enableCompression, Redis: NewInMemoryCache(), UseRedis: false}
}

// makeKey mirrors ContextCache._make_key: kwargs sorted by key, None values skipped.
func (c *ContextCache) makeKey(prefix string, kwargs *entities.OrderedMap[any]) string {
	parts := []string{prefix}
	keys := kwargs.Keys()
	sort.Strings(keys)
	for _, k := range keys {
		v, _ := kwargs.Get(k)
		if v != nil {
			parts = append(parts, k+":"+value_objects.PyStr(v))
		}
	}
	return strings.Join(parts, ":")
}

// compress mirrors ContextCache._compress.
func (c *ContextCache) compress(data string) string {
	if !c.EnableCompression || len(data) < 1024 {
		return data
	}
	var buf bytes.Buffer
	zw := zlib.NewWriter(&buf)
	_, _ = zw.Write([]byte(data))
	_ = zw.Close()
	if float64(buf.Len()) < float64(len(data))*0.9 {
		return "COMPRESSED:" + base64.StdEncoding.EncodeToString(buf.Bytes())
	}
	return data
}

// decompress mirrors ContextCache._decompress.
func (c *ContextCache) decompress(data string) string {
	if strings.HasPrefix(data, "COMPRESSED:") {
		raw, err := base64.StdEncoding.DecodeString(data[len("COMPRESSED:"):])
		if err != nil {
			return data
		}
		zr, err := zlib.NewReader(bytes.NewReader(raw))
		if err != nil {
			return data
		}
		var out bytes.Buffer
		_, _ = out.ReadFrom(zr)
		_ = zr.Close()
		return out.String()
	}
	return data
}

func (c *ContextCache) decode(data string) (*entities.OrderedMap[any], error) {
	decoded, err := entities.DecodeJSON([]byte(c.decompress(data)))
	if err != nil {
		return nil, err
	}
	if m, ok := decoded.(*entities.OrderedMap[any]); ok {
		return m, nil
	}
	return nil, nil
}

func (c *ContextCache) key(prefix, level, contextID, userID string) string {
	kw := entities.NewOrderedMap[any]()
	kw.Set("level", level)
	kw.Set("context_id", contextID)
	kw.Set("user_id", userID)
	return c.makeKey(prefix, kw)
}

// GetInheritanceChain mirrors ContextCache.get_inheritance_chain.
func (c *ContextCache) GetInheritanceChain(level, contextID, userID string) (*entities.OrderedMap[any], error) {
	data, ok := c.Redis.Get(c.key("inheritance", level, contextID, userID))
	if ok && data != "" {
		return c.decode(data)
	}
	return nil, nil
}

// SetInheritanceChain mirrors ContextCache.set_inheritance_chain.
func (c *ContextCache) SetInheritanceChain(level, contextID, userID string, data *entities.OrderedMap[any]) error {
	jsonData, err := value_objects.PyJSONDumps(data, -1)
	if err != nil {
		return err
	}
	c.Redis.Setex(c.key("inheritance", level, contextID, userID), c.TTL, c.compress(jsonData))
	return nil
}

// InvalidateInheritance mirrors ContextCache.invalidate_inheritance.
func (c *ContextCache) InvalidateInheritance(userID string, level, contextID *string) error {
	return c.invalidate("inheritance", userID, level, contextID)
}

// GetContext mirrors ContextCache.get_context.
func (c *ContextCache) GetContext(level, contextID, userID string) (*entities.OrderedMap[any], error) {
	data, ok := c.Redis.Get(c.key("context", level, contextID, userID))
	if ok && data != "" {
		return c.decode(data)
	}
	return nil, nil
}

// SetContext mirrors ContextCache.set_context.
func (c *ContextCache) SetContext(level, contextID, userID string, data *entities.OrderedMap[any], ttl *int) error {
	jsonData, err := value_objects.PyJSONDumps(data, -1)
	if err != nil {
		return err
	}
	t := c.TTL
	if ttl != nil && *ttl != 0 {
		t = *ttl
	}
	c.Redis.Setex(c.key("context", level, contextID, userID), t, c.compress(jsonData))
	return nil
}

// InvalidateContext mirrors ContextCache.invalidate_context.
func (c *ContextCache) InvalidateContext(userID string, level, contextID *string) error {
	return c.invalidate("context", userID, level, contextID)
}

func (c *ContextCache) invalidate(prefix, userID string, level, contextID *string) error {
	if level != nil && contextID != nil && *level != "" && *contextID != "" {
		kw := entities.NewOrderedMap[any]()
		kw.Set("level", *level)
		kw.Set("context_id", *contextID)
		kw.Set("user_id", userID)
		c.Redis.Delete(c.makeKey(prefix, kw))
		return nil
	}
	pattern := prefix + ":*user_id:" + userID + "*"
	keys, err := c.Redis.ScanIter(pattern)
	if err != nil {
		return err
	}
	for _, key := range keys {
		c.Redis.Delete(key)
	}
	return nil
}

// GetMultipleContexts mirrors ContextCache.get_multiple_contexts.
func (c *ContextCache) GetMultipleContexts(contexts []ContextRef, userID string) ([]*entities.OrderedMap[any], error) {
	pipeline := c.Redis.Pipeline()
	for _, ctx := range contexts {
		pipeline.Get(c.key("context", ctx.Level, ctx.ContextID, userID))
	}
	results := pipeline.Execute()
	decoded := make([]*entities.OrderedMap[any], 0, len(results))
	for _, data := range results {
		if s, ok := data.(string); ok && s != "" {
			m, err := c.decode(s)
			if err != nil {
				return nil, err
			}
			decoded = append(decoded, m)
		} else {
			decoded = append(decoded, nil)
		}
	}
	return decoded, nil
}

// SetMultipleContexts mirrors ContextCache.set_multiple_contexts.
func (c *ContextCache) SetMultipleContexts(contexts []ContextEntry, userID string, ttl *int) error {
	pipeline := c.Redis.Pipeline()
	t := c.TTL
	if ttl != nil && *ttl != 0 {
		t = *ttl
	}
	for _, ctx := range contexts {
		jsonData, err := value_objects.PyJSONDumps(ctx.Data, -1)
		if err != nil {
			return err
		}
		pipeline.Setex(c.key("context", ctx.Level, ctx.ContextID, userID), t, c.compress(jsonData))
	}
	pipeline.Execute()
	return nil
}

// GetCacheStats mirrors ContextCache.get_cache_stats for the in-memory backend.
func (c *ContextCache) GetCacheStats() map[string]any {
	return map[string]any{"type": "in-memory", "connected": true, "cache_size": c.Redis.Cache.Len()}
}

// ClearCache mirrors ContextCache.clear_cache (the non-Redis branch).
func (c *ContextCache) ClearCache(pattern *string) error {
	if pattern != nil && *pattern != "" {
		keys, err := c.Redis.ScanIter(*pattern)
		if err != nil {
			return err
		}
		for _, key := range keys {
			c.Redis.Delete(key)
		}
		return nil
	}
	c.Redis.Cache = entities.NewOrderedMap[string]()
	c.Redis.TTLMap = entities.NewOrderedMap[float64]()
	return nil
}

// Singleton instance (context_cache._cache_instance / get_context_cache).
var (
	contextCacheMu       sync.Mutex
	contextCacheInstance *ContextCache
)

// GetContextCache returns the process-wide context cache, creating it on first use.
func GetContextCache() *ContextCache {
	contextCacheMu.Lock()
	defer contextCacheMu.Unlock()
	if contextCacheInstance == nil {
		contextCacheInstance = NewContextCache()
	}
	return contextCacheInstance
}

// ResetContextCache drops the singleton (used by tests; the Python module has no reset).
func ResetContextCache() {
	contextCacheMu.Lock()
	defer contextCacheMu.Unlock()
	contextCacheInstance = nil
}
