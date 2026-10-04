package services

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Enhanced Performance Cache Manager for Rule Orchestration Platform.
//
// Port of performance_cache_manager.py. The asyncio methods are ordinary synchronous
// methods here: there is no event loop, so the background monitoring and prefetch
// starters stay no-ops.

// Now is the injectable clock; Python's time.time() goes through it.
var Now = func() time.Time { return time.Now() }

// VirtualMemory replaces psutil.virtual_memory(): it returns the used-memory percent
// and the available bytes. The default parses /proc/meminfo (MemTotal/MemAvailable) and
// returns (0, 0) when those are unavailable.
var VirtualMemory = func() (percent float64, availableBytes int64) {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return 0, 0
	}
	totalKB := int64(-1)
	availableKB := int64(-1)
	for _, line := range strings.Split(string(data), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		switch fields[0] {
		case "MemTotal:":
			totalKB = meminfoKB(fields[1])
		case "MemAvailable:":
			availableKB = meminfoKB(fields[1])
		}
	}
	if totalKB <= 0 || availableKB < 0 {
		return 0, 0
	}
	percent = float64(totalKB-availableKB) / float64(totalKB) * 100
	return percent, availableKB * 1024
}

func meminfoKB(s string) int64 {
	n, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return -1
	}
	return n
}

func nowSeconds() float64 { return float64(Now().UnixNano()) / 1e9 }

// CacheLevel is performance_cache_manager.CacheLevel.
type CacheLevel string

const (
	CacheLevelMemory      CacheLevel = "memory"
	CacheLevelDisk        CacheLevel = "disk"
	CacheLevelDistributed CacheLevel = "distributed"
)

// CachePolicy is performance_cache_manager.CachePolicy.
type CachePolicy string

const (
	CachePolicyLRU       CachePolicy = "lru"
	CachePolicyLFU       CachePolicy = "lfu"
	CachePolicyTTL       CachePolicy = "ttl"
	CachePolicyAdaptive  CachePolicy = "adaptive"
	CachePolicySizeBased CachePolicy = "size_based"
)

// CacheMetrics is performance_cache_manager.CacheMetrics.
type CacheMetrics string

const (
	CacheMetricsHitRate      CacheMetrics = "hit_rate"
	CacheMetricsMissRate     CacheMetrics = "miss_rate"
	CacheMetricsEvictionRate CacheMetrics = "eviction_rate"
	CacheMetricsMemoryUsage  CacheMetrics = "memory_usage"
	CacheMetricsResponseTime CacheMetrics = "response_time"
	CacheMetricsThroughput   CacheMetrics = "throughput"
)

// CacheConfiguration is performance_cache_manager.CacheConfiguration.
type CacheConfiguration struct {
	MemoryMaxSize     int
	MemoryMaxMemoryMB int
	MemoryPolicy      CachePolicy

	DiskEnabled   bool
	DiskMaxSize   int
	DiskMaxSizeGB int
	DiskCacheDir  *string

	DistributedEnabled bool
	DistributedBackend string
	DistributedConfig  *entities.OrderedMap[any]

	DefaultTTL float64
	MaxTTL     float64
	MinTTL     float64

	LazyLoading        bool
	PrefetchEnabled    bool
	CompressionEnabled bool
	AsyncOperations    bool

	MetricsEnabled     bool
	MetricsInterval    float64
	PerformanceLogging bool
}

// NewCacheConfiguration builds CacheConfiguration with the Python dataclass defaults.
func NewCacheConfiguration() *CacheConfiguration {
	return &CacheConfiguration{
		MemoryMaxSize:      1000,
		MemoryMaxMemoryMB:  512,
		MemoryPolicy:       CachePolicyAdaptive,
		DiskEnabled:        true,
		DiskMaxSize:        10000,
		DiskMaxSizeGB:      5,
		DiskCacheDir:       nil,
		DistributedEnabled: false,
		DistributedBackend: "redis",
		DistributedConfig:  newOrderedAny(),
		DefaultTTL:         3600.0,
		MaxTTL:             86400.0,
		MinTTL:             60.0,
		LazyLoading:        true,
		PrefetchEnabled:    true,
		CompressionEnabled: true,
		AsyncOperations:    true,
		MetricsEnabled:     true,
		MetricsInterval:    60.0,
		PerformanceLogging: true,
	}
}

// CacheEntry is performance_cache_manager.CacheEntry.
type CacheEntry struct {
	Content          any
	Timestamp        float64
	LastAccessed     float64
	AccessCount      int
	TTL              float64
	SizeBytes        int
	ContentHash      string
	Tags             []string
	Priority         int
	SourceLevel      CacheLevel
	CompressionRatio float64
	CreationTime     float64
}

// NewCacheEntry builds a CacheEntry, applying the Python dataclass defaults.
func NewCacheEntry(content any, timestamp, lastAccessed float64, accessCount int, ttl float64, sizeBytes int, contentHash string, tags []string, priority int) *CacheEntry {
	if tags == nil {
		tags = []string{}
	}
	return &CacheEntry{
		Content:          content,
		Timestamp:        timestamp,
		LastAccessed:     lastAccessed,
		AccessCount:      accessCount,
		TTL:              ttl,
		SizeBytes:        sizeBytes,
		ContentHash:      contentHash,
		Tags:             tags,
		Priority:         priority,
		SourceLevel:      CacheLevelMemory,
		CompressionRatio: 1.0,
		CreationTime:     nowSeconds(),
	}
}

// IsExpired is CacheEntry.is_expired.
func (e *CacheEntry) IsExpired() bool { return nowSeconds()-e.Timestamp > e.TTL }

// AgeSeconds is CacheEntry.age_seconds.
func (e *CacheEntry) AgeSeconds() float64 { return nowSeconds() - e.CreationTime }

// AccessFrequency is CacheEntry.access_frequency.
func (e *CacheEntry) AccessFrequency() float64 {
	ageHours := e.AgeSeconds() / 3600
	return float64(e.AccessCount) / math.Max(ageHours, 0.1)
}

// PerformanceMetrics is performance_cache_manager.PerformanceMetrics.
type PerformanceMetrics struct {
	TotalRequests       int
	CacheHits           int
	CacheMisses         int
	TotalResponseTime   float64
	MinResponseTime     float64
	MaxResponseTime     float64
	CurrentMemoryUsage  int
	PeakMemoryUsage     int
	TotalEvictions      int
	EvictionsByPolicy   *entities.OrderedMap[any]
	OperationsPerSecond float64
	LastMetricTime      float64
}

// NewPerformanceMetrics builds PerformanceMetrics with the Python dataclass defaults.
func NewPerformanceMetrics() *PerformanceMetrics {
	return &PerformanceMetrics{
		MinResponseTime:   math.Inf(1),
		EvictionsByPolicy: newOrderedAny(),
		LastMetricTime:    nowSeconds(),
	}
}

// HitRate is PerformanceMetrics.hit_rate.
func (m *PerformanceMetrics) HitRate() float64 {
	if m.TotalRequests == 0 {
		return 0.0
	}
	return float64(m.CacheHits) / float64(m.TotalRequests)
}

// MissRate is PerformanceMetrics.miss_rate.
func (m *PerformanceMetrics) MissRate() float64 { return 1.0 - m.HitRate() }

// AverageResponseTime is PerformanceMetrics.average_response_time.
func (m *PerformanceMetrics) AverageResponseTime() float64 {
	if m.TotalRequests == 0 {
		return 0.0
	}
	return m.TotalResponseTime / float64(m.TotalRequests)
}

// UpdateResponseTime is PerformanceMetrics.update_response_time.
func (m *PerformanceMetrics) UpdateResponseTime(responseTime float64) {
	m.TotalResponseTime += responseTime
	m.MinResponseTime = math.Min(m.MinResponseTime, responseTime)
	m.MaxResponseTime = math.Max(m.MaxResponseTime, responseTime)
}

// CacheStorage is performance_cache_manager.CacheStorage.
type CacheStorage interface {
	Get(key string) *CacheEntry
	Put(key string, entry *CacheEntry) bool
	Delete(key string) bool
	Clear() bool
	Size() int
	Keys() []string
}

// MemoryStorage is performance_cache_manager.MemoryStorage.
type MemoryStorage struct {
	Config       *CacheConfiguration
	Cache        *entities.OrderedMap[*CacheEntry]
	AccessTimes  map[string]float64
	AccessCounts *entities.OrderedMap[int]
	SizeTracker  int
	lock         sync.Mutex
}

// NewMemoryStorage builds a MemoryStorage.
func NewMemoryStorage(config *CacheConfiguration) *MemoryStorage {
	return &MemoryStorage{
		Config:       config,
		Cache:        entities.NewOrderedMap[*CacheEntry](),
		AccessTimes:  map[string]float64{},
		AccessCounts: entities.NewOrderedMap[int](),
	}
}

// Get is MemoryStorage.get.
func (s *MemoryStorage) Get(key string) *CacheEntry {
	s.lock.Lock()
	defer s.lock.Unlock()
	entry, ok := s.Cache.Get(key)
	if !ok {
		return nil
	}
	if entry.IsExpired() {
		s.deleteLocked(key)
		return nil
	}
	entry.LastAccessed = nowSeconds()
	entry.AccessCount++
	s.AccessTimes[key] = nowSeconds()
	if count, ok := s.AccessCounts.Get(key); ok {
		s.AccessCounts.Set(key, count+1)
	} else {
		s.AccessCounts.Set(key, 1)
	}
	s.moveToEnd(key)
	return entry
}

// Put is MemoryStorage.put.
func (s *MemoryStorage) Put(key string, entry *CacheEntry) bool {
	s.lock.Lock()
	defer s.lock.Unlock()
	for s.Cache.Len() >= s.Config.MemoryMaxSize ||
		s.SizeTracker+entry.SizeBytes > s.Config.MemoryMaxMemoryMB*1024*1024 {
		if !s.evictEntry() {
			break
		}
	}
	if old, ok := s.Cache.Get(key); ok {
		s.SizeTracker -= old.SizeBytes
	}
	s.Cache.Set(key, entry)
	s.SizeTracker += entry.SizeBytes
	s.AccessTimes[key] = nowSeconds()
	s.AccessCounts.Set(key, entry.AccessCount)
	return true
}

// Delete is MemoryStorage.delete.
func (s *MemoryStorage) Delete(key string) bool {
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.deleteLocked(key)
}

func (s *MemoryStorage) deleteLocked(key string) bool {
	if entry, ok := s.Cache.Get(key); ok {
		s.Cache.Delete(key)
		s.SizeTracker -= entry.SizeBytes
		delete(s.AccessTimes, key)
		s.AccessCounts.Delete(key)
		return true
	}
	return false
}

// Clear is MemoryStorage.clear.
func (s *MemoryStorage) Clear() bool {
	s.lock.Lock()
	defer s.lock.Unlock()
	s.Cache = entities.NewOrderedMap[*CacheEntry]()
	s.AccessTimes = map[string]float64{}
	s.AccessCounts = entities.NewOrderedMap[int]()
	s.SizeTracker = 0
	return true
}

// Size is MemoryStorage.size.
func (s *MemoryStorage) Size() int {
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.Cache.Len()
}

// Keys is MemoryStorage.keys.
func (s *MemoryStorage) Keys() []string {
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.Cache.Keys()
}

func (s *MemoryStorage) moveToEnd(key string) {
	entry, ok := s.Cache.Get(key)
	if !ok {
		return
	}
	s.Cache.Delete(key)
	s.Cache.Set(key, entry)
}

func (s *MemoryStorage) evictEntry() bool {
	if s.Cache.Len() == 0 {
		return false
	}
	var key string
	switch s.Config.MemoryPolicy {
	case CachePolicyLRU:
		key = s.Cache.Keys()[0]
	case CachePolicyLFU:
		key = s.lfuKey()
	case CachePolicyTTL:
		key = s.oldestTimestampKey()
	case CachePolicyAdaptive:
		key = s.adaptiveEviction()
	default:
		key = s.Cache.Keys()[0]
	}
	s.deleteLocked(key)
	return true
}

func (s *MemoryStorage) lfuKey() string {
	best := ""
	bestCount := 0
	first := true
	for _, key := range s.AccessCounts.Keys() {
		count, _ := s.AccessCounts.Get(key)
		if first || count < bestCount {
			best, bestCount, first = key, count, false
		}
	}
	return best
}

func (s *MemoryStorage) oldestTimestampKey() string {
	best := ""
	bestTimestamp := 0.0
	first := true
	for _, key := range s.Cache.Keys() {
		entry, _ := s.Cache.Get(key)
		if first || entry.Timestamp < bestTimestamp {
			best, bestTimestamp, first = key, entry.Timestamp, false
		}
	}
	return best
}

func (s *MemoryStorage) adaptiveEviction() string {
	now := nowSeconds()
	best := ""
	bestScore := 0.0
	first := true
	for _, key := range s.Cache.Keys() {
		entry, _ := s.Cache.Get(key)
		recencyScore := 1.0 / (now - entry.LastAccessed + 1)
		frequencyScore := entry.AccessFrequency()
		sizePenalty := float64(entry.SizeBytes) / (1024 * 1024)
		score := recencyScore * frequencyScore / (sizePenalty + 1)
		if first || score < bestScore {
			best, bestScore, first = key, score, false
		}
	}
	return best
}

// DiskStorage is performance_cache_manager.DiskStorage.
type DiskStorage struct {
	Config    *CacheConfiguration
	CacheDir  string
	IndexFile string
	Index     *entities.OrderedMap[any]
	lock      sync.Mutex
}

// NewDiskStorage builds a DiskStorage, creating the cache directory.
func NewDiskStorage(config *CacheConfiguration) *DiskStorage {
	dir := ""
	if config.DiskCacheDir != nil {
		dir = *config.DiskCacheDir
	} else {
		cwd, err := os.Getwd()
		if err != nil {
			cwd = ""
		}
		dir = filepath.Join(cwd, ".cache", "rules")
	}
	_ = os.MkdirAll(dir, 0o777)
	s := &DiskStorage{
		Config:    config,
		CacheDir:  dir,
		IndexFile: filepath.Join(dir, "index.json"),
		Index:     newOrderedAny(),
	}
	s.loadIndex()
	return s
}

func (s *DiskStorage) loadIndex() {
	if _, err := os.Stat(s.IndexFile); err != nil {
		return
	}
	data, err := os.ReadFile(s.IndexFile)
	if err != nil {
		s.Index = newOrderedAny()
		return
	}
	parsed, err := entities.DecodeJSON(data)
	if err != nil {
		s.Index = newOrderedAny()
		return
	}
	if om, ok := parsed.(*entities.OrderedMap[any]); ok && om != nil {
		s.Index = om
		return
	}
	s.Index = newOrderedAny()
}

func (s *DiskStorage) saveIndex() {
	text, err := value_objects.PyJSONDumps(s.Index, 2)
	if err != nil {
		return
	}
	_ = os.WriteFile(s.IndexFile, []byte(text), 0o666)
}

func (s *DiskStorage) getFilePath(key string) string {
	sum := sha256.Sum256([]byte(key))
	return filepath.Join(s.CacheDir, hex.EncodeToString(sum[:])+".cache")
}

func (s *DiskStorage) entryDict(key string) (*entities.OrderedMap[any], bool) {
	v, ok := s.Index.Get(key)
	if !ok {
		return nil, false
	}
	d, ok := v.(*entities.OrderedMap[any])
	return d, ok
}

// Get is DiskStorage.get.
func (s *DiskStorage) Get(key string) *CacheEntry {
	s.lock.Lock()
	defer s.lock.Unlock()
	if !s.Index.Has(key) {
		return nil
	}
	filePath := s.getFilePath(key)
	if _, err := os.Stat(filePath); err != nil {
		s.Index.Delete(key)
		s.saveIndex()
		return nil
	}
	entry, err := readCacheEntry(filePath)
	if err != nil {
		s.deleteLocked(key)
		return nil
	}
	if entry.IsExpired() {
		s.deleteLocked(key)
		return nil
	}
	entry.LastAccessed = nowSeconds()
	entry.AccessCount++
	if d, ok := s.entryDict(key); ok {
		d.Set("last_accessed", entry.LastAccessed)
		d.Set("access_count", entry.AccessCount)
	}
	s.saveIndex()
	return entry
}

// Put is DiskStorage.put.
func (s *DiskStorage) Put(key string, entry *CacheEntry) bool {
	s.lock.Lock()
	defer s.lock.Unlock()
	s.enforceSizeLimits()
	filePath := s.getFilePath(key)
	if err := writeCacheEntry(filePath, entry); err != nil {
		return false
	}
	d := newOrderedAny()
	d.Set("timestamp", entry.Timestamp)
	d.Set("last_accessed", entry.LastAccessed)
	d.Set("access_count", entry.AccessCount)
	d.Set("size_bytes", entry.SizeBytes)
	d.Set("ttl", entry.TTL)
	d.Set("file_path", filePath)
	s.Index.Set(key, d)
	s.saveIndex()
	return true
}

// Delete is DiskStorage.delete.
func (s *DiskStorage) Delete(key string) bool {
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.deleteLocked(key)
}

func (s *DiskStorage) deleteLocked(key string) bool {
	if !s.Index.Has(key) {
		return false
	}
	filePath := s.getFilePath(key)
	if _, err := os.Stat(filePath); err == nil {
		if err := os.Remove(filePath); err != nil {
			return false
		}
	}
	s.Index.Delete(key)
	s.saveIndex()
	return true
}

// Clear is DiskStorage.clear.
func (s *DiskStorage) Clear() bool {
	s.lock.Lock()
	defer s.lock.Unlock()
	matches, err := filepath.Glob(filepath.Join(s.CacheDir, "*.cache"))
	if err != nil {
		return false
	}
	for _, path := range matches {
		if err := os.Remove(path); err != nil {
			return false
		}
	}
	s.Index = newOrderedAny()
	s.saveIndex()
	return true
}

// Size is DiskStorage.size.
func (s *DiskStorage) Size() int {
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.Index.Len()
}

// Keys is DiskStorage.keys.
func (s *DiskStorage) Keys() []string {
	s.lock.Lock()
	defer s.lock.Unlock()
	return s.Index.Keys()
}

func (s *DiskStorage) enforceSizeLimits() {
	for s.Index.Len() >= s.Config.DiskMaxSize {
		s.evictOldestEntry()
	}
	totalSize := 0
	for _, key := range s.Index.Keys() {
		d, _ := s.entryDict(key)
		totalSize += omInt(d, "size_bytes")
	}
	maxSizeBytes := s.Config.DiskMaxSizeGB * 1024 * 1024 * 1024
	for totalSize > maxSizeBytes && s.Index.Len() > 0 {
		totalSize -= s.evictOldestEntry()
	}
}

func (s *DiskStorage) evictOldestEntry() int {
	if s.Index.Len() == 0 {
		return 0
	}
	oldestKey := ""
	oldestTimestamp := 0.0
	first := true
	for _, key := range s.Index.Keys() {
		d, _ := s.entryDict(key)
		timestamp := omFloat(d, "timestamp")
		if first || timestamp < oldestTimestamp {
			oldestKey, oldestTimestamp, first = key, timestamp, false
		}
	}
	d, _ := s.entryDict(oldestKey)
	sizeBytes := omInt(d, "size_bytes")
	s.deleteLocked(oldestKey)
	return sizeBytes
}

func cacheEntryToOrderedMap(entry *CacheEntry) *entities.OrderedMap[any] {
	d := newOrderedAny()
	d.Set("content", entry.Content)
	d.Set("timestamp", entry.Timestamp)
	d.Set("last_accessed", entry.LastAccessed)
	d.Set("access_count", entry.AccessCount)
	d.Set("ttl", entry.TTL)
	d.Set("size_bytes", entry.SizeBytes)
	d.Set("content_hash", entry.ContentHash)
	d.Set("tags", entry.Tags)
	d.Set("priority", entry.Priority)
	d.Set("source_level", string(entry.SourceLevel))
	d.Set("compression_ratio", entry.CompressionRatio)
	d.Set("creation_time", entry.CreationTime)
	return d
}

func cacheEntryFromOrderedMap(d *entities.OrderedMap[any]) *CacheEntry {
	entry := &CacheEntry{}
	if v, ok := d.Get("content"); ok {
		entry.Content = v
	}
	entry.Timestamp = omFloat(d, "timestamp")
	entry.LastAccessed = omFloat(d, "last_accessed")
	entry.AccessCount = omInt(d, "access_count")
	entry.TTL = omFloat(d, "ttl")
	entry.SizeBytes = omInt(d, "size_bytes")
	if v, ok := d.Get("content_hash"); ok {
		entry.ContentHash, _ = v.(string)
	}
	if v, ok := d.Get("tags"); ok {
		entry.Tags = decodeTags(v)
	} else {
		entry.Tags = []string{}
	}
	entry.Priority = omIntDefault(d, "priority", 1)
	if v, ok := d.Get("source_level"); ok {
		if s, ok := v.(string); ok {
			entry.SourceLevel = CacheLevel(s)
		}
	} else {
		entry.SourceLevel = CacheLevelMemory
	}
	if _, ok := d.Get("compression_ratio"); ok {
		entry.CompressionRatio = omFloat(d, "compression_ratio")
	} else {
		entry.CompressionRatio = 1.0
	}
	entry.CreationTime = omFloat(d, "creation_time")
	return entry
}

// stringList converts a Python list value into []string. It was previously defined in
// the removed agent_doc_generator.go; decodeTags is now its only consumer.
func stringList(v any) []string {
	switch x := v.(type) {
	case []any:
		out := make([]string, 0, len(x))
		for _, item := range x {
			out = append(out, value_objects.PyStr(item))
		}
		return out
	case []string:
		return x
	case *entities.OrderedMap[any]:
		return x.Keys()
	}
	return nil
}

func decodeTags(v any) []string {
	out := stringList(v)
	if out == nil {
		return []string{}
	}
	return out
}

func writeCacheEntry(path string, entry *CacheEntry) error {
	text := value_objects.PyJSONDumpsDefaultStr(cacheEntryToOrderedMap(entry), -1)
	return os.WriteFile(path, []byte(text), 0o666)
}

func readCacheEntry(path string) (*CacheEntry, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	parsed, err := entities.DecodeJSON(data)
	if err != nil {
		return nil, err
	}
	d, ok := parsed.(*entities.OrderedMap[any])
	if !ok || d == nil {
		return nil, errors.New("cache entry is not an object")
	}
	return cacheEntryFromOrderedMap(d), nil
}

// EnhancedRuleCacheManager is performance_cache_manager.EnhancedRuleCacheManager.
type EnhancedRuleCacheManager struct {
	Config             *CacheConfiguration
	Metrics            *PerformanceMetrics
	MemoryStorage      *MemoryStorage
	DiskStorage        *DiskStorage
	DistributedStorage CacheStorage
	PerformanceMonitor *PerformanceMonitor
	PrefetchTask       any
}

// NewEnhancedRuleCacheManager builds the multi-level cache manager.
func NewEnhancedRuleCacheManager(config *CacheConfiguration) *EnhancedRuleCacheManager {
	if config == nil {
		config = NewCacheConfiguration()
	}
	manager := &EnhancedRuleCacheManager{
		Config:        config,
		Metrics:       NewPerformanceMetrics(),
		MemoryStorage: NewMemoryStorage(config),
	}
	if config.DiskEnabled {
		manager.DiskStorage = NewDiskStorage(config)
	}
	// distributed_storage stays nil (TODO: Redis/distributed storage).
	if config.MetricsEnabled {
		manager.startPerformanceMonitoring()
	}
	if config.PrefetchEnabled {
		manager.startPrefetchSystem()
	}
	return manager
}

// Get is EnhancedRuleCacheManager.get.
func (m *EnhancedRuleCacheManager) Get(key string, lazyLoadCallback func(string) (any, error)) (any, error) {
	startTime := nowSeconds()

	entry := m.MemoryStorage.Get(key)
	if entry != nil {
		m.recordHit(nowSeconds() - startTime)
		return entry.Content, nil
	}

	if m.DiskStorage != nil {
		entry = m.DiskStorage.Get(key)
		if entry != nil {
			m.MemoryStorage.Put(key, entry)
			m.recordHit(nowSeconds() - startTime)
			return entry.Content, nil
		}
	}

	if m.DistributedStorage != nil {
		entry = m.DistributedStorage.Get(key)
		if entry != nil {
			m.MemoryStorage.Put(key, entry)
			if m.DiskStorage != nil {
				m.DiskStorage.Put(key, entry)
			}
			m.recordHit(nowSeconds() - startTime)
			return entry.Content, nil
		}
	}

	if lazyLoadCallback != nil && m.Config.LazyLoading {
		content := m.lazyLoad(key, lazyLoadCallback)
		if content != nil {
			m.recordHit(nowSeconds() - startTime)
			return content, nil
		}
	}

	m.recordMiss(nowSeconds() - startTime)
	return nil, nil
}

// Put is EnhancedRuleCacheManager.put.
func (m *EnhancedRuleCacheManager) Put(key string, content any, ttl *float64, tags []string, priority int) (bool, error) {
	startTime := nowSeconds()

	contentStr := value_objects.PyStr(content)
	sizeBytes := len([]byte(contentStr))
	sum := sha256.Sum256([]byte(contentStr))
	contentHash := hex.EncodeToString(sum[:])

	effectiveTTL := m.Config.DefaultTTL
	if ttl != nil && *ttl != 0 {
		effectiveTTL = *ttl
	}
	if len(tags) == 0 {
		tags = []string{}
	}

	entry := NewCacheEntry(content, nowSeconds(), nowSeconds(), 1, effectiveTTL, sizeBytes, contentHash, tags, priority)

	success := m.MemoryStorage.Put(key, entry)

	if m.DiskStorage != nil && sizeBytes > 1024 {
		m.DiskStorage.Put(key, entry)
	}
	if m.DistributedStorage != nil && priority >= 3 {
		m.DistributedStorage.Put(key, entry)
	}

	m.Metrics.TotalResponseTime += nowSeconds() - startTime
	return success, nil
}

// Invalidate is EnhancedRuleCacheManager.invalidate.
func (m *EnhancedRuleCacheManager) Invalidate(key string) (bool, error) {
	success := true
	m.MemoryStorage.Delete(key)
	if m.DiskStorage != nil {
		success = m.DiskStorage.Delete(key) && success
	}
	if m.DistributedStorage != nil {
		success = m.DistributedStorage.Delete(key) && success
	}
	return success, nil
}

// InvalidateByTags is EnhancedRuleCacheManager.invalidate_by_tags.
func (m *EnhancedRuleCacheManager) InvalidateByTags(tags []string) int {
	invalidatedCount := 0
	memoryKeys := m.MemoryStorage.Keys()
	for _, key := range memoryKeys {
		entry := m.MemoryStorage.Get(key)
		if entry != nil && anyTagIn(entry.Tags, tags) {
			m.Invalidate(key)
			invalidatedCount++
		}
	}
	return invalidatedCount
}

func anyTagIn(entryTags, tags []string) bool {
	for _, tag := range tags {
		for _, entryTag := range entryTags {
			if entryTag == tag {
				return true
			}
		}
	}
	return false
}

// Clear is EnhancedRuleCacheManager.clear.
func (m *EnhancedRuleCacheManager) Clear() bool {
	success := true
	m.MemoryStorage.Clear()
	if m.DiskStorage != nil {
		success = m.DiskStorage.Clear() && success
	}
	if m.DistributedStorage != nil {
		success = m.DistributedStorage.Clear() && success
	}
	m.Metrics = NewPerformanceMetrics()
	return success
}

// GetPerformanceMetrics is EnhancedRuleCacheManager.get_performance_metrics.
func (m *EnhancedRuleCacheManager) GetPerformanceMetrics() *entities.OrderedMap[any] {
	percent, availableBytes := VirtualMemory()

	cacheStatistics := newOrderedAny()
	cacheStatistics.Set("hit_rate", m.Metrics.HitRate())
	cacheStatistics.Set("miss_rate", m.Metrics.MissRate())
	cacheStatistics.Set("total_requests", m.Metrics.TotalRequests)
	cacheStatistics.Set("cache_hits", m.Metrics.CacheHits)
	cacheStatistics.Set("cache_misses", m.Metrics.CacheMisses)

	performanceMetrics := newOrderedAny()
	performanceMetrics.Set("average_response_time_ms", m.Metrics.AverageResponseTime()*1000)
	performanceMetrics.Set("min_response_time_ms", m.Metrics.MinResponseTime*1000)
	performanceMetrics.Set("max_response_time_ms", m.Metrics.MaxResponseTime*1000)
	performanceMetrics.Set("operations_per_second", m.Metrics.OperationsPerSecond)

	memoryMetrics := newOrderedAny()
	memoryMetrics.Set("current_usage_mb", float64(m.Metrics.CurrentMemoryUsage)/(1024*1024))
	memoryMetrics.Set("peak_usage_mb", float64(m.Metrics.PeakMemoryUsage)/(1024*1024))
	memoryMetrics.Set("system_memory_percent", percent)
	memoryMetrics.Set("available_memory_mb", float64(availableBytes)/(1024*1024))

	cacheLevels := newOrderedAny()
	cacheLevels.Set("memory_entries", m.MemoryStorage.Cache.Len())
	diskEntries := 0
	if m.DiskStorage != nil {
		diskEntries = m.DiskStorage.Index.Len()
	}
	cacheLevels.Set("disk_entries", diskEntries)
	cacheLevels.Set("distributed_entries", 0)

	evictionsByPolicy := newOrderedAny()
	for _, key := range m.Metrics.EvictionsByPolicy.Keys() {
		v, _ := m.Metrics.EvictionsByPolicy.Get(key)
		evictionsByPolicy.Set(key, v)
	}
	evictionStatistics := newOrderedAny()
	evictionStatistics.Set("total_evictions", m.Metrics.TotalEvictions)
	evictionStatistics.Set("evictions_by_policy", evictionsByPolicy)

	result := newOrderedAny()
	result.Set("cache_statistics", cacheStatistics)
	result.Set("performance_metrics", performanceMetrics)
	result.Set("memory_metrics", memoryMetrics)
	result.Set("cache_levels", cacheLevels)
	result.Set("eviction_statistics", evictionStatistics)
	return result
}

// OptimizeCache is EnhancedRuleCacheManager.optimize_cache.
func (m *EnhancedRuleCacheManager) OptimizeCache() *entities.OrderedMap[any] {
	optimizationResults := newOrderedAny()
	optimizationResults.Set("expired_entries_removed", 0)
	optimizationResults.Set("memory_compacted", false)
	optimizationResults.Set("disk_defragmented", false)
	optimizationResults.Set("recommendations", []string{})

	expiredCount := m.removeExpiredEntries()
	optimizationResults.Set("expired_entries_removed", expiredCount)

	recommendations := []string{}
	hitRate := m.Metrics.HitRate()
	if hitRate < 0.5 {
		recommendations = append(recommendations, "Consider increasing cache size or adjusting TTL values")
	}
	if float64(m.Metrics.TotalEvictions) > float64(m.Metrics.CacheHits)*0.1 {
		recommendations = append(recommendations, "High eviction rate detected - consider increasing memory cache size")
	}
	optimizationResults.Set("recommendations", recommendations)
	return optimizationResults
}

func (m *EnhancedRuleCacheManager) lazyLoad(key string, callback func(string) (any, error)) any {
	content, err := callback(key)
	if err != nil {
		return nil
	}
	if content != nil {
		m.Put(key, content, nil, nil, 1)
	}
	return content
}

func (m *EnhancedRuleCacheManager) removeExpiredEntries() int {
	removedCount := 0

	for _, key := range m.MemoryStorage.Keys() {
		entry := m.MemoryStorage.Get(key)
		if entry != nil && entry.IsExpired() {
			m.MemoryStorage.Delete(key)
			removedCount++
		}
	}

	if m.DiskStorage != nil {
		for _, key := range m.DiskStorage.Keys() {
			entry := m.DiskStorage.Get(key)
			if entry != nil && entry.IsExpired() {
				m.DiskStorage.Delete(key)
				removedCount++
			}
		}
	}

	return removedCount
}

func (m *EnhancedRuleCacheManager) recordHit(responseTime float64) {
	m.Metrics.TotalRequests++
	m.Metrics.CacheHits++
	m.Metrics.UpdateResponseTime(responseTime)
}

func (m *EnhancedRuleCacheManager) recordMiss(responseTime float64) {
	m.Metrics.TotalRequests++
	m.Metrics.CacheMisses++
	m.Metrics.UpdateResponseTime(responseTime)
}

func (m *EnhancedRuleCacheManager) startPerformanceMonitoring() {
	// TODO: Implement background monitoring task
}

func (m *EnhancedRuleCacheManager) startPrefetchSystem() {
	// TODO: Implement intelligent prefetching
}

// Enter is EnhancedRuleCacheManager.__aenter__.
func (m *EnhancedRuleCacheManager) Enter() *EnhancedRuleCacheManager { return m }

// Exit is EnhancedRuleCacheManager.__aexit__.
func (m *EnhancedRuleCacheManager) Exit() {
	if m.PrefetchTask != nil {
		// self.prefetch_task.cancel() has no equivalent without an event loop.
	}
}

// CreatePerformanceCacheManager is create_performance_cache_manager.
func CreatePerformanceCacheManager(memorySize int, memoryMB int, diskEnabled bool, diskSizeGB int, ttlHours float64, enableMetrics bool) *EnhancedRuleCacheManager {
	config := NewCacheConfiguration()
	config.MemoryMaxSize = memorySize
	config.MemoryMaxMemoryMB = memoryMB
	config.DiskEnabled = diskEnabled
	config.DiskMaxSizeGB = diskSizeGB
	config.DefaultTTL = ttlHours * 3600
	config.MetricsEnabled = enableMetrics
	return NewEnhancedRuleCacheManager(config)
}

func omFloat(m *entities.OrderedMap[any], key string) float64 {
	if m == nil {
		return 0
	}
	v, ok := m.Get(key)
	if !ok {
		return 0
	}
	f, _ := value_objects.PyFloat(v)
	return f
}

func omInt(m *entities.OrderedMap[any], key string) int {
	return int(omFloat(m, key))
}

func omIntDefault(m *entities.OrderedMap[any], key string, def int) int {
	if m == nil {
		return def
	}
	if _, ok := m.Get(key); !ok {
		return def
	}
	return int(omFloat(m, key))
}
