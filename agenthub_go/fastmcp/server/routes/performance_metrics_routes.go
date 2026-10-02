package routes

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func format1(v float64) string { return strconv.FormatFloat(v, 'f', 1, 64) }

// formatPercent2 mirrors format(v, ".2%").
func formatPercent2(v float64) string { return fmt.Sprintf("%.2f%%", v*100) }

func pmItoa(n int) string { return strconv.Itoa(n) }

func keysOf(m *entities.OrderedMap[any]) []string {
	if m == nil {
		return nil
	}
	return m.Keys()
}

// The performance infrastructure modules have no Go port yet; the minimal
// surfaces the routes use are declared here and injected through variables.
type HealthService interface {
	GetEnvironmentInfo() *entities.OrderedMap[any]
	ValidateServerConfiguration() *entities.OrderedMap[any]
}

// ConnectionStatsPool is get_connection_pool(...) (SQLite).
type ConnectionStatsPool interface {
	GetStats() *entities.OrderedMap[any]
}

// SupabasePool is get_supabase_pool() (PostgreSQL).
type SupabasePool interface {
	GetPoolStatus() *entities.OrderedMap[any]
}

// CacheStore is the subset of the cache managers used here.
type CacheStore interface {
	GetStats() *entities.OrderedMap[any]
	Clear()
}

var (
	// HealthServiceDefault is the module-level MCPServerHealthService().
	HealthServiceDefault HealthService
	// GetConnectionPoolDefault is get_connection_pool.
	GetConnectionPoolDefault func(path string) (ConnectionStatsPool, error)
	// GetSupabasePoolDefault is get_supabase_pool (nil, nil = not configured).
	GetSupabasePoolDefault func() (SupabasePool, error)
	// GetCacheDefault is get_cache.
	GetCacheDefault func(name string) (CacheStore, error)
)

func databasePath() string {
	if v, ok := os.LookupEnv("DATABASE_PATH"); ok {
		return v
	}
	return "/data/agenthub.db"
}

func numFloat(v any, def float64) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case float32:
		return float64(n)
	case int:
		return float64(n)
	case int64:
		return float64(n)
	}
	return def
}

func numInt(v any, def int) int {
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return def
}

func pmOmGet(m *entities.OrderedMap[any], k string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(k)
	return v
}

func omGetStr(m *entities.OrderedMap[any], k string, def string) string {
	if s, ok := pmOmGet(m, k).(string); ok {
		return s
	}
	return def
}

// GetPerformanceOverview is get_performance_overview GET /metrics/overview.
func GetPerformanceOverview(includeDetails bool) (*entities.OrderedMap[any], error) {
	overview := entities.NewOrderedMap[any]()
	overview.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	overview.Set("system_health", "healthy")
	overview.Set("performance_score", 0.0)
	overview.Set("metrics", entities.NewOrderedMap[any]())

	connectionMetrics := entities.NewOrderedMap[any]()

	// SQLite pool
	if GetConnectionPoolDefault == nil {
		sqlite := entities.NewOrderedMap[any]()
		sqlite.Set("type", "sqlite")
		sqlite.Set("status", "unavailable")
		connectionMetrics.Set("sqlite", sqlite)
	} else if pool, err := GetConnectionPoolDefault(databasePath()); err != nil {
		sqlite := entities.NewOrderedMap[any]()
		sqlite.Set("type", "sqlite")
		sqlite.Set("status", "unavailable")
		connectionMetrics.Set("sqlite", sqlite)
	} else {
		stats := pool.GetStats()
		poolExhausted := numInt(pmOmGet(stats, "pool_exhausted_count"), 0)
		getCount := numInt(pmOmGet(stats, "get_count"), 1)
		if getCount < 1 {
			getCount = 1
		}
		sqlite := entities.NewOrderedMap[any]()
		sqlite.Set("type", "sqlite")
		sqlite.Set("status", "active")
		sqlite.Set("pool_size", numInt(pmOmGet(stats, "pool_size"), 0))
		sqlite.Set("connections_created", numInt(pmOmGet(stats, "connections_created"), 0))
		sqlite.Set("avg_wait_time", numFloat(pmOmGet(stats, "avg_wait_time"), 0.0))
		sqlite.Set("hit_rate", 1.0-float64(poolExhausted)/float64(getCount))
		connectionMetrics.Set("sqlite", sqlite)
	}

	// Supabase pool
	supabase, supErr := SupabasePoolOrNil()
	if supErr != nil {
		conn := entities.NewOrderedMap[any]()
		conn.Set("type", "postgresql")
		conn.Set("status", "unavailable")
		connectionMetrics.Set("supabase", conn)
	} else if supabase == nil {
		conn := entities.NewOrderedMap[any]()
		conn.Set("type", "postgresql")
		conn.Set("status", "not_configured")
		connectionMetrics.Set("supabase", conn)
	} else {
		stats := supabase.GetPoolStatus()
		conn := entities.NewOrderedMap[any]()
		conn.Set("type", "postgresql")
		conn.Set("status", "active")
		conn.Set("pool_size", numInt(pmOmGet(stats, "size"), 0))
		conn.Set("checked_out", numInt(pmOmGet(stats, "checked_out"), 0))
		conn.Set("overflow", numInt(pmOmGet(stats, "overflow"), 0))
		conn.Set("pool_class", omGetStr(stats, "class", "Unknown"))
		connectionMetrics.Set("supabase", conn)
	}

	metrics := entities.NewOrderedMap[any]()
	metrics.Set("connections", connectionMetrics)

	// Cache performance metrics
	cacheMetrics := entities.NewOrderedMap[any]()
	cacheNames := []string{"default", "task_cache", "context_cache", "agent_cache"}
	for _, cacheName := range cacheNames {
		if GetCacheDefault == nil {
			u := entities.NewOrderedMap[any]()
			u.Set("status", "unavailable")
			cacheMetrics.Set(cacheName, u)
			continue
		}
		cache, err := GetCacheDefault(cacheName)
		if err != nil || cache == nil {
			u := entities.NewOrderedMap[any]()
			u.Set("status", "unavailable")
			cacheMetrics.Set(cacheName, u)
			continue
		}
		stats := cache.GetStats()
		entry := entities.NewOrderedMap[any]()
		entry.Set("hit_rate", numFloat(pmOmGet(stats, "hit_rate"), 0.0))
		entry.Set("size", numInt(pmOmGet(stats, "size"), 0))
		entry.Set("max_size", numInt(pmOmGet(stats, "max_size"), 0))
		entry.Set("hits", numInt(pmOmGet(stats, "hits"), 0))
		entry.Set("misses", numInt(pmOmGet(stats, "misses"), 0))
		entry.Set("evictions", numInt(pmOmGet(stats, "evictions"), 0))
		cacheMetrics.Set(cacheName, entry)
	}
	metrics.Set("caching", cacheMetrics)

	// Server health status
	if HealthServiceDefault == nil {
		h := entities.NewOrderedMap[any]()
		h.Set("status", "error")
		metrics.Set("server_health", h)
	} else {
		envInfo := HealthServiceDefault.GetEnvironmentInfo()
		configValidation := HealthServiceDefault.ValidateServerConfiguration()
		h := entities.NewOrderedMap[any]()
		h.Set("auth_enabled", boolOr(pmOmGet(envInfo, "auth_enabled"), false))
		h.Set("database_configured", boolOr(pmOmGet(envInfo, "database_configured"), false))
		h.Set("active_connections", numInt(pmOmGet(configValidation, "active_connections"), 0))
		h.Set("uptime_seconds", numInt(pmOmGet(configValidation, "uptime_seconds"), 0))
		h.Set("status", omGetStr(configValidation, "status", "unknown"))
		metrics.Set("server_health", h)
	}

	overview.Set("metrics", metrics)

	// Performance score
	scoreComponents := []float64{}
	if sqliteObj, ok := connectionMetrics.Get("sqlite"); ok {
		if m, ok := sqliteObj.(*entities.OrderedMap[any]); ok && omGetStr(m, "status", "") == "active" {
			hit := numFloat(pmOmGet(m, "hit_rate"), 0)
			scoreComponents = append(scoreComponents, minFloat(hit*30, 30))
		}
	}
	cacheHitRates := []float64{}
	for _, name := range keysOf(cacheMetrics) {
		if m, ok := cacheMetrics.Get(name); ok {
			if mm, ok := m.(*entities.OrderedMap[any]); ok && mm.Has("hit_rate") {
				cacheHitRates = append(cacheHitRates, numFloat(pmOmGet(mm, "hit_rate"), 0))
			}
		}
	}
	if len(cacheHitRates) > 0 {
		sum := 0.0
		for _, r := range cacheHitRates {
			sum += r
		}
		scoreComponents = append(scoreComponents, sum/float64(len(cacheHitRates))*40)
	}
	serverHealth, _ := metrics.Get("server_health")
	serverStatus := omGetStr(asOM(serverHealth), "status", "unknown")
	if serverStatus == "healthy" {
		scoreComponents = append(scoreComponents, 30)
	} else if serverStatus == "configuration_error" {
		scoreComponents = append(scoreComponents, 15)
	}
	total := 0.0
	for _, c := range scoreComponents {
		total += c
	}
	overview.Set("performance_score", total)
	if total > 70 {
		overview.Set("system_health", "healthy")
	} else {
		overview.Set("system_health", "degraded")
	}

	if includeDetails {
		dist := entities.NewOrderedMap[any]()
		for _, name := range keysOf(cacheMetrics) {
			if m, ok := cacheMetrics.Get(name); ok {
				if mm, ok := m.(*entities.OrderedMap[any]); ok && mm.Has("size") {
					dist.Set(name, numInt(pmOmGet(mm, "size"), 0))
				}
			}
		}
		sqliteStats := asOM(pmOmGet(connectionMetrics, "sqlite"))
		eff := entities.NewOrderedMap[any]()
		eff.Set("sqlite_avg_wait_ms", numFloat(pmOmGet(sqliteStats, "avg_wait_time"), 0)*1000)
		eff.Set("total_connections_created", numInt(pmOmGet(sqliteStats, "connections_created"), 0))
		details := entities.NewOrderedMap[any]()
		details.Set("cache_distribution", dist)
		details.Set("connection_efficiency", eff)
		details.Set("performance_recommendations", PerformanceRecommendations(overview))
		overview.Set("details", details)
	}
	return overview, nil
}

// SupabasePoolOrNil mirrors get_supabase_pool(): (nil, nil) means not configured.
func SupabasePoolOrNil() (SupabasePool, error) {
	if GetSupabasePoolDefault == nil {
		return nil, nil
	}
	return GetSupabasePoolDefault()
}

func boolOr(v any, def bool) bool {
	if b, ok := v.(bool); ok {
		return b
	}
	return def
}

func asOM(v any) *entities.OrderedMap[any] {
	if m, ok := v.(*entities.OrderedMap[any]); ok {
		return m
	}
	return nil
}

func minFloat(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// PerformanceRecommendations is _generate_performance_recommendations.
func PerformanceRecommendations(overview *entities.OrderedMap[any]) []string {
	recommendations := []string{}
	metrics := asOM(pmOmGet(overview, "metrics"))
	cacheMetrics := asOM(pmOmGet(metrics, "caching"))
	lowHitRateCaches := []string{}
	for _, name := range keysOf(cacheMetrics) {
		if mm, ok := cacheMetrics.Get(name); ok {
			if m, ok := mm.(*entities.OrderedMap[any]); ok && numFloat(pmOmGet(m, "hit_rate"), 1.0) < 0.8 {
				lowHitRateCaches = append(lowHitRateCaches, name)
			}
		}
	}
	if len(lowHitRateCaches) > 0 {
		recommendations = append(recommendations, "Consider increasing TTL or cache size for: "+joinComma(lowHitRateCaches))
	}
	connectionMetrics := asOM(pmOmGet(metrics, "connections"))
	sqliteData := asOM(pmOmGet(connectionMetrics, "sqlite"))
	if numFloat(pmOmGet(sqliteData, "avg_wait_time"), 0) > 0.1 {
		recommendations = append(recommendations, "Consider increasing SQLite connection pool size due to high wait times")
	}
	if numFloat(pmOmGet(overview, "performance_score"), 0) < 80 {
		recommendations = append(recommendations, "Overall performance below optimal - review caching strategy and connection pooling")
	}
	if len(recommendations) == 0 {
		recommendations = append(recommendations, "System performance is optimal")
	}
	return recommendations
}

func joinComma(items []string) string {
	out := ""
	for i, s := range items {
		if i > 0 {
			out += ", "
		}
		out += s
	}
	return out
}

// GetPerformanceTimeseries is get_performance_timeseries GET /metrics/timeseries.
func GetPerformanceTimeseries(hours int, interval string) (*entities.OrderedMap[any], error) {
	intervalMinutes, ok := map[string]int{"5m": 5, "15m": 15, "1h": 60, "6h": 360, "24h": 1440}[interval]
	if !ok {
		return nil, httpErr(500, "interval")
	}
	now := time.Now()
	dataPoints := []*entities.OrderedMap[any]{}
	pointsCount := (hours * 60) / intervalMinutes
	for i := 0; i < pointsCount; i++ {
		timestamp := now.Add(-time.Duration(i*intervalMinutes) * time.Minute)
		pt := entities.NewOrderedMap[any]()
		pt.Set("timestamp", value_objects.IsoFormatNaive(timestamp))
		pt.Set("cache_hit_rate", 0.75+float64(i%10)*0.02)
		pt.Set("avg_response_time", 50+(i%20)*5)
		pt.Set("active_connections", 3+(i%5))
		pt.Set("performance_score", 75+(i%15))
		dataPoints = append(dataPoints, pt)
	}
	reversed := make([]*entities.OrderedMap[any], 0, len(dataPoints))
	for i := len(dataPoints) - 1; i >= 0; i-- {
		reversed = append(reversed, dataPoints[i])
	}
	out := entities.NewOrderedMap[any]()
	out.Set("interval", interval)
	out.Set("hours", hours)
	out.Set("data_points", reversed)
	out.Set("note", "This is mock data. In production, implement time-series storage.")
	return out, nil
}

// GetPerformanceAlerts is get_performance_alerts GET /metrics/alerts.
func GetPerformanceAlerts() (*entities.OrderedMap[any], error) {
	currentOverview, err := GetPerformanceOverview(false)
	if err != nil {
		return nil, err
	}
	alerts := []*entities.OrderedMap[any]{}
	thresholds := entities.NewOrderedMap[any]()
	thresholds.Set("performance_score_min", 70)
	thresholds.Set("cache_hit_rate_min", 0.8)
	thresholds.Set("connection_pool_exhaustion_max", 0.1)
	thresholds.Set("avg_wait_time_max", 0.5)

	score := numFloat(pmOmGet(currentOverview, "performance_score"), 0)
	if score < 70 {
		a := entities.NewOrderedMap[any]()
		a.Set("type", "warning")
		a.Set("metric", "performance_score")
		a.Set("current_value", score)
		a.Set("threshold", 70)
		a.Set("message", "Performance score ("+format1(score)+") below threshold (70)")
		alerts = append(alerts, a)
	}
	metrics := asOM(pmOmGet(currentOverview, "metrics"))
	cacheMetrics := asOM(pmOmGet(metrics, "caching"))
	for _, cacheName := range keysOf(cacheMetrics) {
		mm, _ := cacheMetrics.Get(cacheName)
		m, ok := mm.(*entities.OrderedMap[any])
		if !ok || !m.Has("hit_rate") {
			continue
		}
		hitRate := numFloat(pmOmGet(m, "hit_rate"), 0)
		if hitRate < 0.8 {
			a := entities.NewOrderedMap[any]()
			a.Set("type", "warning")
			a.Set("metric", "cache_hit_rate")
			a.Set("cache_name", cacheName)
			a.Set("current_value", hitRate)
			a.Set("threshold", 0.8)
			a.Set("message", "Cache "+cacheName+" hit rate ("+formatPercent2(hitRate)+") below threshold (80%)")
			alerts = append(alerts, a)
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	out.Set("active_alerts", alerts)
	out.Set("thresholds", thresholds)
	out.Set("alert_count", len(alerts))
	return out, nil
}

// ClearPerformanceCache is clear_performance_cache POST /metrics/clear-cache.
func ClearPerformanceCache(cacheName *string) (*entities.OrderedMap[any], error) {
	clearedCaches := []string{}
	if cacheName != nil && *cacheName != "" {
		if GetCacheDefault == nil {
			return nil, httpErr(400, "Could not clear cache '"+*cacheName+"': unavailable")
		}
		cache, err := GetCacheDefault(*cacheName)
		if err != nil || cache == nil {
			return nil, httpErr(400, "Could not clear cache '"+*cacheName+"': unavailable")
		}
		cache.Clear()
		clearedCaches = append(clearedCaches, *cacheName)
	} else {
		for _, name := range []string{"default", "task_cache", "context_cache", "agent_cache"} {
			if GetCacheDefault == nil {
				continue
			}
			cache, err := GetCacheDefault(name)
			if err != nil || cache == nil {
				continue
			}
			cache.Clear()
			clearedCaches = append(clearedCaches, name)
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("cleared_caches", clearedCaches)
	out.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	out.Set("message", "Cleared "+pmItoa(len(clearedCaches))+" cache(s)")
	return out, nil
}
