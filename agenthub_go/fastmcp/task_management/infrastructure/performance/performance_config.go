// Package performance ports task_management/infrastructure/performance.
package performance

import (
	"fmt"
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Config holds the performance settings Python reads from the environment once, at import.
type Config struct {
	CacheEnabled           bool
	CacheTTLSeconds        int
	CacheMaxSize           int
	UseSelectinload        bool
	QueryTimeoutMs         int
	DefaultPageSize        int
	MaxPageSize            int
	MinimalResponseMode    bool
	CompressResponses      bool
	ConnectionPoolSize     int
	ConnectionPoolOverflow int
	ConnectionPoolTimeout  int
	EnableQueryLogging     bool
	SlowQueryThresholdMs   int
}

func envBool(getenv func(string) (string, bool), key, def string) bool {
	v, ok := getenv(key)
	if !ok {
		v = def
	}
	return tmvo.PyLower(v) == "true"
}

func envInt(getenv func(string) (string, bool), key, def string) (int, error) {
	v, ok := getenv(key)
	if !ok {
		v = def
	}
	n, ok := tmvo.PyParseInt(v)
	if !ok || !n.IsInt64() {
		return 0, &tmvo.ValueError{Msg: fmt.Sprintf("invalid literal for int() with base 10: %s", tmvo.PyRepr(v))}
	}
	return int(n.Int64()), nil
}

// LoadConfig reads the settings through getenv. An unparsable integer is the ValueError
// Python raises while importing the module.
func LoadConfig(getenv func(string) (string, bool)) (*Config, error) {
	c := &Config{
		CacheEnabled:        envBool(getenv, "TASK_CACHE_ENABLED", "true"),
		UseSelectinload:     envBool(getenv, "USE_SELECTINLOAD", "true"),
		MinimalResponseMode: envBool(getenv, "MINIMAL_RESPONSE_MODE", "true"),
		CompressResponses:   envBool(getenv, "COMPRESS_RESPONSES", "false"),
		EnableQueryLogging:  envBool(getenv, "ENABLE_QUERY_LOGGING", "false"),
	}
	ints := []struct {
		dst      *int
		key, def string
	}{
		{&c.CacheTTLSeconds, "TASK_CACHE_TTL", "300"}, {&c.CacheMaxSize, "TASK_CACHE_MAX_SIZE", "1000"},
		{&c.QueryTimeoutMs, "QUERY_TIMEOUT_MS", "5000"}, {&c.DefaultPageSize, "DEFAULT_PAGE_SIZE", "50"},
		{&c.MaxPageSize, "MAX_PAGE_SIZE", "200"}, {&c.ConnectionPoolSize, "DB_POOL_SIZE", "20"},
		{&c.ConnectionPoolOverflow, "DB_POOL_OVERFLOW", "10"}, {&c.ConnectionPoolTimeout, "DB_POOL_TIMEOUT", "30"},
		{&c.SlowQueryThresholdMs, "SLOW_QUERY_THRESHOLD_MS", "1000"},
	}
	for _, i := range ints {
		n, err := envInt(getenv, i.key, i.def)
		if err != nil {
			return nil, err
		}
		*i.dst = n
	}
	return c, nil
}

func osGetenv(k string) (string, bool) { return os.LookupEnv(k) }

// Settings is the process-wide configuration, evaluated at startup like Python's import.
var Settings = func() *Config {
	c, err := LoadConfig(osGetenv)
	if err != nil {
		panic(err)
	}
	return c
}()

func obj(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// GetConfig returns all settings as a nested dictionary.
func (c *Config) GetConfig() *entities.OrderedMap[any] {
	return obj(
		"cache", obj("enabled", c.CacheEnabled, "ttl_seconds", c.CacheTTLSeconds, "max_size", c.CacheMaxSize),
		"query", obj("use_selectinload", c.UseSelectinload, "timeout_ms", c.QueryTimeoutMs),
		"pagination", obj("default_size", c.DefaultPageSize, "max_size", c.MaxPageSize),
		"response", obj("minimal_mode", c.MinimalResponseMode, "compress", c.CompressResponses),
		"database", obj("pool_size", c.ConnectionPoolSize, "pool_overflow", c.ConnectionPoolOverflow, "pool_timeout", c.ConnectionPoolTimeout),
		"monitoring", obj("enable_query_logging", c.EnableQueryLogging, "slow_query_threshold_ms", c.SlowQueryThresholdMs),
	)
}

// IsPerformanceMode is always true (Python forces performance mode).
func (c *Config) IsPerformanceMode() bool { return true }
