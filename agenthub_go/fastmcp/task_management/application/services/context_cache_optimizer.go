package services

import (
	"bytes"
	"compress/gzip"
	"crypto/md5"
	"encoding/hex"
	"errors"
	"math"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CacheStrategy mirrors the CacheStrategy enum
// (Python application/services/context_cache_optimizer.py).
type CacheStrategy string

const (
	CacheStrategyLRU      CacheStrategy = "lru"
	CacheStrategyLFU      CacheStrategy = "lfu"
	CacheStrategyTTL      CacheStrategy = "ttl"
	CacheStrategyAdaptive CacheStrategy = "adaptive"
)

// CacheEntry is the Python dataclass CacheEntry.
type CacheEntry struct {
	Data          any
	CreatedAt     time.Time
	LastAccessed  time.Time
	AccessCount   int
	TTLSeconds    *int
	SizeBytes     int
	ContextType   string
	OperationType string
}

// IsExpired mirrors CacheEntry.is_expired: a nil or falsy TTL never expires.
func (e *CacheEntry) IsExpired() bool {
	if e.TTLSeconds == nil || *e.TTLSeconds == 0 {
		return false
	}
	return time.Now().After(e.CreatedAt.Add(time.Duration(*e.TTLSeconds) * time.Second))
}

// Touch mirrors CacheEntry.touch.
func (e *CacheEntry) Touch() {
	e.LastAccessed = time.Now()
	e.AccessCount++
}

var ccoDefaultTTL = map[string]int{
	"task":       300,
	"project":    1800,
	"context":    600,
	"user":       900,
	"git_branch": 1800,
	"agent":      3600,
	"template":   7200,
	"field_spec": 3600,
}

var ccoSizeLimits = map[string]int{
	"task": 50, "project": 20, "context": 30, "user": 10,
	"git_branch": 15, "agent": 5, "template": 10, "field_spec": 5,
}

// ContextCacheOptimizer optimizes context caching for maximum performance
// (Python class ContextCacheOptimizer).
type ContextCacheOptimizer struct {
	maxSizeBytes int
	defaultTTL   int
	strategy     CacheStrategy
	adaptiveTTL  bool

	cache          *entities.OrderedMap[*CacheEntry]
	lock           sync.Mutex
	accessPatterns map[string][]time.Time
	contextStats   map[string]map[string]any
	metrics        *entities.OrderedMap[int]
}

// NewContextCacheOptimizer mirrors ContextCacheOptimizer.__init__ with the Python
// keyword defaults max_size_mb=200, default_ttl=600, strategy=ADAPTIVE, adaptive_ttl=True.
func NewContextCacheOptimizer(maxSizeMB, defaultTTL int, strategy CacheStrategy, adaptiveTTL bool) *ContextCacheOptimizer {
	o := &ContextCacheOptimizer{
		maxSizeBytes:   maxSizeMB * 1024 * 1024,
		defaultTTL:     defaultTTL,
		strategy:       strategy,
		adaptiveTTL:    adaptiveTTL,
		cache:          entities.NewOrderedMap[*CacheEntry](),
		accessPatterns: map[string][]time.Time{},
		contextStats:   map[string]map[string]any{},
		metrics:        entities.NewOrderedMap[int](),
	}
	o.metrics.Set("cache_hits", 0)
	o.metrics.Set("cache_misses", 0)
	o.metrics.Set("evictions", 0)
	o.metrics.Set("size_bytes", 0)
	o.metrics.Set("entries_count", 0)
	o.metrics.Set("cleanup_runs", 0)
	o.metrics.Set("adaptive_adjustments", 0)
	return o
}

func (o *ContextCacheOptimizer) metric(key string) int {
	v, _ := o.metrics.Get(key)
	return v
}

func (o *ContextCacheOptimizer) addMetric(key string, delta int) {
	o.metrics.Set(key, o.metric(key)+delta)
}

// Get mirrors ContextCacheOptimizer.get.
func (o *ContextCacheOptimizer) Get(key, contextType string) any {
	o.lock.Lock()
	defer o.lock.Unlock()

	entry, ok := o.cache.Get(key)
	if !ok {
		o.addMetric("cache_misses", 1)
		return nil
	}
	if entry.IsExpired() {
		o.removeEntry(key)
		o.addMetric("cache_misses", 1)
		return nil
	}
	entry.Touch()
	o.trackAccess(key, contextType)
	o.addMetric("cache_hits", 1)

	data := entry.Data
	if b, ok := data.([]byte); ok {
		if dec, err := ccoGunzipJSON(b); err == nil {
			data = dec
		}
	}
	return data
}

func ccoGunzipJSON(b []byte) (any, error) {
	zr, err := gzip.NewReader(bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	defer zr.Close()
	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(zr); err != nil {
		return nil, err
	}
	return entities.DecodeJSON(buf.Bytes())
}

// generateKey mirrors ContextCacheOptimizer._generate_key.
func (o *ContextCacheOptimizer) generateKey(operation string, params map[string]any) string {
	sortedParams := value_objects.PyJSONDumpsDefaultStr(params, -1)
	keyString := operation + ":" + sortedParams
	sum := md5.Sum([]byte(keyString))
	return hex.EncodeToString(sum[:])
}

// Put mirrors ContextCacheOptimizer.put. The optimize flag is accepted but unused,
// exactly like the Python.
func (o *ContextCacheOptimizer) Put(key string, data any, contextType, operationType string, ttl *int, optimize, compress bool) bool {
	o.lock.Lock()
	defer o.lock.Unlock()

	originalData := data
	var sizeBytes int
	if compress {
		jsonData := value_objects.PyJSONDumpsDefaultStr(data, -1)
		var buf bytes.Buffer
		zw := gzip.NewWriter(&buf)
		if _, err := zw.Write([]byte(jsonData)); err == nil {
			if err := zw.Close(); err == nil {
				data = buf.Bytes()
				sizeBytes = len(buf.Bytes())
			} else {
				data = originalData
				sizeBytes = len([]byte(value_objects.PyJSONDumpsDefaultStr(data, -1)))
			}
		} else {
			data = originalData
			sizeBytes = len([]byte(value_objects.PyJSONDumpsDefaultStr(data, -1)))
		}
	} else {
		sizeBytes = len([]byte(value_objects.PyJSONDumpsDefaultStr(data, -1)))
	}

	if float64(sizeBytes) > float64(o.maxSizeBytes)*0.1 {
		return false
	}

	var entryTTL int
	if ttl != nil && *ttl != 0 {
		entryTTL = *ttl
	} else {
		entryTTL = o.adaptiveTTLFor(contextType, operationType)
	}
	ttlCopy := entryTTL

	entry := &CacheEntry{
		Data:          data,
		CreatedAt:     time.Now(),
		LastAccessed:  time.Now(),
		TTLSeconds:    &ttlCopy,
		SizeBytes:     sizeBytes,
		ContextType:   contextType,
		OperationType: operationType,
	}

	for o.totalSize()+sizeBytes > o.maxSizeBytes {
		if !o.evictEntry() {
			return false
		}
	}

	if old, ok := o.cache.Get(key); ok {
		o.addMetric("size_bytes", -old.SizeBytes)
	} else {
		o.addMetric("entries_count", 1)
	}
	o.cache.Set(key, entry)
	o.addMetric("size_bytes", sizeBytes)
	return true
}

// Invalidate mirrors ContextCacheOptimizer.invalidate. A nil argument means Python None;
// an empty string is falsy and falls through, like Python.
func (o *ContextCacheOptimizer) Invalidate(key, contextType, pattern *string) int {
	o.lock.Lock()
	defer o.lock.Unlock()

	var toRemove []string
	if key != nil && *key != "" {
		if o.cache.Has(*key) {
			toRemove = append(toRemove, *key)
		}
	} else if contextType != nil && *contextType != "" {
		for _, k := range o.cache.Keys() {
			e, _ := o.cache.Get(k)
			if e.ContextType == *contextType {
				toRemove = append(toRemove, k)
			}
		}
	} else if pattern != nil && *pattern != "" {
		for _, k := range o.cache.Keys() {
			if ccoFnmatch(k, *pattern) {
				toRemove = append(toRemove, k)
			}
		}
	}

	for _, k := range toRemove {
		o.removeEntry(k)
	}
	return len(toRemove)
}

// InvalidatePattern mirrors ContextCacheOptimizer.invalidate_pattern.
func (o *ContextCacheOptimizer) InvalidatePattern(pattern string) int {
	return o.Invalidate(nil, nil, &pattern)
}

func (o *ContextCacheOptimizer) adaptiveTTLFor(contextType, operationType string) int {
	if o.strategy != CacheStrategyAdaptive {
		if v, ok := ccoDefaultTTL[contextType]; ok {
			return v
		}
		return o.defaultTTL
	}

	baseTTL := o.defaultTTL
	if v, ok := ccoDefaultTTL[contextType]; ok {
		baseTTL = v
	}

	stats := o.contextStats[contextType]
	hitRate := 0.5
	avgAccessInterval := float64(300)
	if stats != nil {
		if v, ok := stats["hit_rate"].(float64); ok {
			hitRate = v
		}
		if v, ok := stats["avg_access_interval"].(float64); ok {
			avgAccessInterval = v
		}
	}

	if hitRate > 0.8 {
		baseTTL = int(float64(baseTTL) * 1.5)
	} else if hitRate < 0.3 {
		baseTTL = int(float64(baseTTL) * 0.5)
	}

	if avgAccessInterval < 60 {
		baseTTL = baseTTL * 2
	} else if avgAccessInterval > 1800 {
		baseTTL = int(float64(baseTTL) * 0.7)
	}

	if operationType == "list" || operationType == "search" || operationType == "count" {
		baseTTL = int(float64(baseTTL) * 0.8)
	} else if operationType == "get" || operationType == "detail" {
		baseTTL = int(float64(baseTTL) * 1.2)
	}

	o.addMetric("adaptive_adjustments", 1)

	minTTL := 60
	if o.defaultTTL < minTTL {
		minTTL = o.defaultTTL
	}
	maxTTL := 7200
	if o.defaultTTL*10 > maxTTL {
		maxTTL = o.defaultTTL * 10
	}
	if baseTTL < minTTL {
		return minTTL
	}
	if baseTTL > maxTTL {
		return maxTTL
	}
	return baseTTL
}

func (o *ContextCacheOptimizer) evictEntry() bool {
	if o.cache.Len() == 0 {
		return false
	}
	keys := o.cache.Keys()
	var oldestKey string

	switch o.strategy {
	case CacheStrategyLRU:
		for i, k := range keys {
			e, _ := o.cache.Get(k)
			if i == 0 {
				oldestKey = k
				continue
			}
			prev, _ := o.cache.Get(oldestKey)
			if e.LastAccessed.Before(prev.LastAccessed) {
				oldestKey = k
			}
		}
	case CacheStrategyLFU:
		for i, k := range keys {
			e, _ := o.cache.Get(k)
			if i == 0 {
				oldestKey = k
				continue
			}
			prev, _ := o.cache.Get(oldestKey)
			if e.AccessCount < prev.AccessCount {
				oldestKey = k
			}
		}
	case CacheStrategyTTL:
		oldestKey = o.firstExpiredOrOldest(keys)
	default:
		oldestKey = o.firstExpiredOrOldest(keys)
		if oldestKey == "" {
			now := time.Now()
			bestScore := math.Inf(-1)
			for _, k := range keys {
				e, _ := o.cache.Get(k)
				ageScore := now.Sub(e.LastAccessed).Seconds()
				accessScore := 1.0 / math.Max(float64(e.AccessCount), 1)
				sizeScore := float64(e.SizeBytes) / 1024
				score := ageScore + accessScore + sizeScore
				if score > bestScore {
					bestScore = score
					oldestKey = k
				}
			}
		}
	}

	o.removeEntry(oldestKey)
	o.addMetric("evictions", 1)
	return true
}

// firstExpiredOrOldest returns the first expired key, else the oldest created_at key;
// "" when there are no expired keys and the TTL branch should fall through to adaptive.
func (o *ContextCacheOptimizer) firstExpiredOrOldest(keys []string) string {
	for _, k := range keys {
		e, _ := o.cache.Get(k)
		if e.IsExpired() {
			return k
		}
	}
	if o.strategy != CacheStrategyTTL {
		return ""
	}
	oldestKey := keys[0]
	for _, k := range keys[1:] {
		e, _ := o.cache.Get(k)
		prev, _ := o.cache.Get(oldestKey)
		if e.CreatedAt.Before(prev.CreatedAt) {
			oldestKey = k
		}
	}
	return oldestKey
}

func (o *ContextCacheOptimizer) removeEntry(key string) {
	entry, ok := o.cache.Get(key)
	if !ok {
		return
	}
	o.cache.Delete(key)
	o.addMetric("size_bytes", -entry.SizeBytes)
	o.addMetric("entries_count", -1)
}

func (o *ContextCacheOptimizer) trackAccess(key, contextType string) {
	now := time.Now()
	o.accessPatterns[contextType] = append(o.accessPatterns[contextType], now)

	cutoff := now.Add(-time.Hour)
	kept := o.accessPatterns[contextType][:0]
	for _, access := range o.accessPatterns[contextType] {
		if access.After(cutoff) {
			kept = append(kept, access)
		}
	}
	o.accessPatterns[contextType] = kept

	if len(o.accessPatterns[contextType])%10 == 0 {
		o.updateContextStats(contextType)
	}
}

func (o *ContextCacheOptimizer) updateContextStats(contextType string) {
	accesses := o.accessPatterns[contextType]
	if len(accesses) < 2 {
		return
	}

	totalAccesses := 0
	cacheHits := 0
	for _, k := range o.cache.Keys() {
		e, _ := o.cache.Get(k)
		if e.ContextType == contextType {
			totalAccesses += e.AccessCount
			if e.AccessCount > 1 {
				cacheHits++
			}
		}
	}
	denom := totalAccesses
	if denom < 1 {
		denom = 1
	}
	hitRate := float64(cacheHits) / float64(denom)

	var avgInterval float64
	if len(accesses) > 1 {
		total := 0.0
		for i := 1; i < len(accesses); i++ {
			total += accesses[i].Sub(accesses[i-1]).Seconds()
		}
		avgInterval = total / float64(len(accesses)-1)
	} else {
		avgInterval = 300
	}

	o.contextStats[contextType] = map[string]any{
		"hit_rate":            hitRate,
		"avg_access_interval": avgInterval,
		"last_updated":        time.Now(),
	}
}

func (o *ContextCacheOptimizer) totalSize() int {
	total := 0
	for _, e := range o.cache.Values() {
		total += e.SizeBytes
	}
	return total
}

// CleanupExpired mirrors ContextCacheOptimizer.cleanup_expired.
func (o *ContextCacheOptimizer) CleanupExpired() int {
	o.lock.Lock()
	defer o.lock.Unlock()
	return o.cleanupExpiredLocked()
}

func (o *ContextCacheOptimizer) cleanupExpiredLocked() int {
	var expired []string
	for _, k := range o.cache.Keys() {
		e, _ := o.cache.Get(k)
		if e.IsExpired() {
			expired = append(expired, k)
		}
	}
	for _, k := range expired {
		o.removeEntry(k)
	}
	o.addMetric("cleanup_runs", 1)
	return len(expired)
}

// GetCacheStats mirrors ContextCacheOptimizer.get_cache_stats, returning the ordered
// dict (with the Python attribute-access shim dropped: Go callers use map access).
func (o *ContextCacheOptimizer) GetCacheStats() *entities.OrderedMap[any] {
	o.lock.Lock()
	defer o.lock.Unlock()

	hits := o.metric("cache_hits")
	misses := o.metric("cache_misses")
	totalRequests := hits + misses
	var hitRate any
	if totalRequests > 0 {
		hitRate = float64(hits) / float64(totalRequests) * 100
	} else {
		hitRate = 0
	}

	breakdown := entities.NewOrderedMap[any]()
	for _, e := range o.cache.Values() {
		ctxType := e.ContextType
		curAny, ok := breakdown.Get(ctxType)
		var cur *entities.OrderedMap[any]
		if ok {
			cur = curAny.(*entities.OrderedMap[any])
		} else {
			cur = entities.NewOrderedMap[any]()
			cur.Set("count", 0)
			cur.Set("size_bytes", 0)
			breakdown.Set(ctxType, cur)
		}
		c, _ := cur.Get("count")
		sb, _ := cur.Get("size_bytes")
		cur.Set("count", c.(int)+1)
		cur.Set("size_bytes", sb.(int)+e.SizeBytes)
	}

	stats := entities.NewOrderedMap[any]()
	stats.Set("total_entries", o.metric("entries_count"))
	stats.Set("hit_count", hits)
	stats.Set("miss_count", misses)
	stats.Set("current_size_mb", ccoRound(float64(o.metric("size_bytes"))/(1024*1024), 6))
	stats.Set("max_size_mb", ccoRound(float64(o.maxSizeBytes)/(1024*1024), 2))

	performance := entities.NewOrderedMap[any]()
	if f, ok := hitRate.(float64); ok {
		performance.Set("hit_rate_percent", ccoRound(f, 2))
	} else {
		performance.Set("hit_rate_percent", 0)
	}
	performance.Set("total_requests", totalRequests)
	performance.Set("cache_hits", hits)
	performance.Set("cache_misses", misses)
	stats.Set("performance", performance)

	storage := entities.NewOrderedMap[any]()
	storage.Set("size_bytes", o.metric("size_bytes"))
	storage.Set("size_mb", ccoRound(float64(o.metric("size_bytes"))/(1024*1024), 2))
	storage.Set("entries_count", o.metric("entries_count"))
	storage.Set("max_size_mb", ccoRound(float64(o.maxSizeBytes)/(1024*1024), 2))
	stats.Set("storage", storage)

	maintenance := entities.NewOrderedMap[any]()
	maintenance.Set("evictions", o.metric("evictions"))
	maintenance.Set("cleanup_runs", o.metric("cleanup_runs"))
	maintenance.Set("adaptive_adjustments", o.metric("adaptive_adjustments"))
	stats.Set("maintenance", maintenance)

	stats.Set("context_breakdown", breakdown)
	stats.Set("strategy", string(o.strategy))
	return stats
}

// OptimizeCache mirrors ContextCacheOptimizer.optimize_cache.
func (o *ContextCacheOptimizer) OptimizeCache() *entities.OrderedMap[any] {
	o.lock.Lock()
	defer o.lock.Unlock()

	initialSize := o.metric("size_bytes")
	initialCount := o.metric("entries_count")
	expiredRemoved := o.cleanupExpiredLocked()

	if o.strategy == CacheStrategyAdaptive {
		for contextType := range o.accessPatterns {
			o.updateContextStats(contextType)
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("expired_removed", expiredRemoved)
	result.Set("size_reduced_bytes", initialSize-o.metric("size_bytes"))
	result.Set("entries_reduced", initialCount-o.metric("entries_count"))
	result.Set("context_stats_updated", len(o.contextStats))
	result.Set("strategy", string(o.strategy))
	return result
}

// WarmCache mirrors ContextCacheOptimizer.warm_cache. A Python tuple value
// (context_type, data) is represented as a [2]any.
func (o *ContextCacheOptimizer) WarmCache(commonData map[string]any, contextType string) int {
	warmed := 0
	for key, value := range commonData {
		ctxType := contextType
		data := value
		if tuple, ok := value.([2]any); ok {
			ctxType = value_objects.PyStr(tuple[0])
			data = tuple[1]
		}
		if o.Put(key, data, ctxType, "warmup", nil, false, false) {
			warmed++
		}
	}
	return warmed
}

// ResetCache mirrors ContextCacheOptimizer.reset_cache.
func (o *ContextCacheOptimizer) ResetCache() {
	o.lock.Lock()
	defer o.lock.Unlock()
	o.cache = entities.NewOrderedMap[*CacheEntry]()
	o.accessPatterns = map[string][]time.Time{}
	o.contextStats = map[string]map[string]any{}
	o.metrics = entities.NewOrderedMap[int]()
	o.metrics.Set("cache_hits", 0)
	o.metrics.Set("cache_misses", 0)
	o.metrics.Set("evictions", 0)
	o.metrics.Set("size_bytes", 0)
	o.metrics.Set("entries_count", 0)
	o.metrics.Set("cleanup_runs", 0)
	o.metrics.Set("adaptive_adjustments", 0)
}

// SaveToDisk mirrors ContextCacheOptimizer.save_to_disk.
func (o *ContextCacheOptimizer) SaveToDisk(filePath string) bool {
	o.lock.Lock()
	cacheData := entities.NewOrderedMap[any]()

	cache := entities.NewOrderedMap[any]()
	for _, key := range o.cache.Keys() {
		entry, _ := o.cache.Get(key)
		d := entities.NewOrderedMap[any]()
		d.Set("data", entry.Data)
		d.Set("created_at", value_objects.IsoFormatNaive(entry.CreatedAt))
		d.Set("last_accessed", value_objects.IsoFormatNaive(entry.LastAccessed))
		d.Set("access_count", entry.AccessCount)
		if entry.TTLSeconds == nil {
			d.Set("ttl_seconds", nil)
		} else {
			d.Set("ttl_seconds", *entry.TTLSeconds)
		}
		d.Set("size_bytes", entry.SizeBytes)
		d.Set("context_type", entry.ContextType)
		d.Set("operation_type", entry.OperationType)
		cache.Set(key, d)
	}
	cacheData.Set("cache", cache)

	metrics := entities.NewOrderedMap[any]()
	for _, k := range o.metrics.Keys() {
		v, _ := o.metrics.Get(k)
		metrics.Set(k, v)
	}
	cacheData.Set("metrics", metrics)

	settings := entities.NewOrderedMap[any]()
	settings.Set("max_size_bytes", o.maxSizeBytes)
	settings.Set("default_ttl", o.defaultTTL)
	settings.Set("strategy", string(o.strategy))
	settings.Set("adaptive_ttl", o.adaptiveTTL)
	cacheData.Set("settings", settings)

	s, err := value_objects.PyJSONDumps(cacheData, 2)
	o.lock.Unlock()
	if err != nil {
		return false
	}
	if err := os.WriteFile(filePath, []byte(s), 0o644); err != nil {
		return false
	}
	return true
}

// LoadFromDisk mirrors ContextCacheOptimizer.load_from_disk.
func (o *ContextCacheOptimizer) LoadFromDisk(filePath string) bool {
	raw, err := os.ReadFile(filePath)
	if err != nil {
		return false
	}
	decoded, err := entities.DecodeJSON(raw)
	if err != nil {
		return false
	}
	cacheData, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		return false
	}

	o.lock.Lock()
	defer o.lock.Unlock()

	o.cache = entities.NewOrderedMap[*CacheEntry]()
	if cacheAny, ok := cacheData.Get("cache"); ok {
		if cache, ok := cacheAny.(*entities.OrderedMap[any]); ok {
			for _, key := range cache.Keys() {
				entryAny, _ := cache.Get(key)
				entryData, ok := entryAny.(*entities.OrderedMap[any])
				if !ok {
					continue
				}
				entry := ccoEntryFromDict(entryData)
				if entry == nil {
					continue
				}
				if !entry.IsExpired() {
					o.cache.Set(key, entry)
				}
			}
		}
	}

	if metricsAny, ok := cacheData.Get("metrics"); ok {
		if metrics, ok := metricsAny.(*entities.OrderedMap[any]); ok {
			for _, k := range metrics.Keys() {
				v, _ := metrics.Get(k)
				o.metrics.Set(k, ccoToInt(v))
			}
		}
	}
	return true
}

func ccoEntryFromDict(d *entities.OrderedMap[any]) *CacheEntry {
	data, _ := d.Get("data")

	createdAt, cErr := ccoGetTime(d, "created_at")
	lastAccessed, lErr := ccoGetTime(d, "last_accessed")
	if cErr != nil || lErr != nil {
		return nil
	}

	accessCount := 0
	if v, ok := d.Get("access_count"); ok {
		accessCount = ccoToInt(v)
	}
	var ttl *int
	if v, ok := d.Get("ttl_seconds"); ok && v != nil {
		t := ccoToInt(v)
		ttl = &t
	}
	sizeBytes := 0
	if v, ok := d.Get("size_bytes"); ok {
		sizeBytes = ccoToInt(v)
	}
	contextType, _ := d.Get("context_type")
	operationType, _ := d.Get("operation_type")

	return &CacheEntry{
		Data:          data,
		CreatedAt:     createdAt,
		LastAccessed:  lastAccessed,
		AccessCount:   accessCount,
		TTLSeconds:    ttl,
		SizeBytes:     sizeBytes,
		ContextType:   value_objects.PyStr(contextType),
		OperationType: value_objects.PyStr(operationType),
	}
}

func ccoGetTime(d *entities.OrderedMap[any], key string) (time.Time, error) {
	v, ok := d.Get(key)
	if !ok {
		return time.Time{}, errors.New("missing " + key)
	}
	s, ok := v.(string)
	if !ok {
		return time.Time{}, errors.New("not a string")
	}
	t, err := value_objects.ParseISO(s)
	if err != nil {
		return time.Time{}, err
	}
	return ccoLocalize(t, s), nil
}

// ccoLocalize reinterprets an offset-less ISO string in the local zone, since Python's
// datetime.fromisoformat returns a naive datetime compared against datetime.now().
func ccoLocalize(t time.Time, raw string) time.Time {
	hasZone := strings.HasSuffix(raw, "Z")
	if idx := strings.IndexByte(raw, 'T'); idx >= 0 {
		rest := raw[idx+1:]
		if strings.ContainsAny(rest, "+-") {
			hasZone = true
		}
	}
	if hasZone {
		return t
	}
	return time.Date(t.Year(), t.Month(), t.Day(), t.Hour(), t.Minute(), t.Second(), t.Nanosecond(), time.Local)
}

func ccoToInt(v any) int {
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

// ccoRound mirrors Python round(x, ndigits) with banker's rounding on the scaled value.
func ccoRound(x float64, nd int) float64 {
	p := math.Pow(10, float64(nd))
	scaled := x * p
	floor := math.Floor(scaled)
	diff := scaled - floor
	var r float64
	switch {
	case diff > 0.5:
		r = floor + 1
	case diff < 0.5:
		r = floor
	default:
		if math.Mod(floor, 2) == 0 {
			r = floor
		} else {
			r = floor + 1
		}
	}
	return r / p
}

// ccoFnmatch mirrors fnmatch.fnmatch on a single name.
func ccoFnmatch(name, pattern string) bool {
	re, err := regexp.Compile(ccoFnmatchTranslate(pattern))
	if err != nil {
		return false
	}
	return re.MatchString(name)
}

func ccoFnmatchTranslate(pattern string) string {
	var b strings.Builder
	b.WriteString("(?s)^")
	i := 0
	n := len(pattern)
	for i < n {
		c := pattern[i]
		i++
		switch c {
		case '*':
			b.WriteString(".*")
		case '?':
			b.WriteString(".")
		case '[':
			j := i
			if j < n && (pattern[j] == '!' || pattern[j] == '^') {
				j++
			}
			if j < n && pattern[j] == ']' {
				j++
			}
			for j < n && pattern[j] != ']' {
				j++
			}
			if j >= n {
				b.WriteString("\\[")
			} else {
				stuff := pattern[i:j]
				i = j + 1
				if strings.HasPrefix(stuff, "!") {
					stuff = "^" + stuff[1:]
				}
				b.WriteString("[" + stuff + "]")
			}
		default:
			b.WriteString(regexp.QuoteMeta(string(c)))
		}
	}
	b.WriteString("$")
	return b.String()
}
