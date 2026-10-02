package repositories

// Repository utilities (Python repositories/utils.py): configuration validation, timestamp
// validation, query-parameter normalization and repository metrics. The functions that need
// database_utils (not yet ported) go through the RepositoryDatabaseUtils hook declared here.

import (
	"fmt"
	"os"
	"reflect"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// RepositoryDatabaseUtils is the subset of database_utils.DatabaseUtils used by this package.
// The database package registers an implementation; it depends on database_utils, which is not
// yet ported to Go.
type RepositoryDatabaseUtils interface {
	NormalizeTimestamp(timestamp any) (*time.Time, error)
	CheckDatabaseHealth() (*entities.OrderedMap[any], error)
	GetSession() (any, error)
}

var repoDatabaseUtils RepositoryDatabaseUtils

// SetRepositoryDatabaseUtils registers the database_utils implementation.
func SetRepositoryDatabaseUtils(utils RepositoryDatabaseUtils) { repoDatabaseUtils = utils }

// GetRepositoryDatabaseUtils returns the registered database_utils implementation.
func GetRepositoryDatabaseUtils() RepositoryDatabaseUtils { return repoDatabaseUtils }

func repoUtilsGetenvDefault(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return fallback
}

// GetValidatedDatabaseType returns the validated DATABASE_TYPE environment variable.
func GetValidatedDatabaseType() (string, error) {
	databaseType, ok := os.LookupEnv("DATABASE_TYPE")
	if !ok || databaseType == "" {
		return "", exceptions.NewConfigurationException(
			"DATABASE_TYPE environment variable is not set. Please set DATABASE_TYPE to 'postgresql', 'sqlite', or 'supabase'", "")
	}
	validTypes := []string{"postgresql", "sqlite", "supabase"}
	lower := strings.ToLower(databaseType)
	for _, t := range validTypes {
		if lower == t {
			return lower, nil
		}
	}
	return "", exceptions.NewConfigurationException(
		fmt.Sprintf("Invalid DATABASE_TYPE '%s'. Must be one of: %s", databaseType, strings.Join(validTypes, ", ")), "")
}

// GetRepositoryConfig returns the validated repository configuration.
func GetRepositoryConfig() (*entities.OrderedMap[any], error) {
	environment := strings.ToLower(repoUtilsGetenvDefault("ENVIRONMENT", "production"))
	databaseType, err := GetValidatedDatabaseType()
	if err != nil {
		return nil, exceptions.NewConfigurationException("Repository configuration error: "+err.Error(), "")
	}
	validEnvironments := map[string]bool{"development": true, "testing": true, "staging": true, "production": true}
	if !validEnvironments[environment] {
		environment = "production"
	}
	config := entities.NewOrderedMap[any]()
	config.Set("environment", environment)
	config.Set("database_type", databaseType)
	config.Set("redis_enabled", strings.ToLower(repoUtilsGetenvDefault("REDIS_ENABLED", "false")) == "true")
	config.Set("use_cache", strings.ToLower(repoUtilsGetenvDefault("USE_CACHE", "false")) == "true")
	config.Set("debug_mode", environment == "development" || environment == "testing")
	config.Set("performance_mode", strings.ToLower(repoUtilsGetenvDefault("PERFORMANCE_MODE", "false")) == "true")
	config.Set("timestamp_events_enabled", true)
	config.Set("clean_architecture_mode", true)
	return config, nil
}

// ValidateEntityTimestamps validates the created_at / updated_at fields of an entity.
func ValidateEntityTimestamps(entity any) (*entities.OrderedMap[any], error) {
	result := entities.NewOrderedMap[any]()
	result.Set("entity_class", repoUtilsTypeName(entity))
	result.Set("has_timestamps", false)
	result.Set("timestamps_valid", false)
	result.Set("created_at", nil)
	result.Set("updated_at", nil)
	result.Set("timezone_compliant", false)
	errs := []any{}
	result.Set("errors", errs)

	createdField, hasCreated := repoUtilsTimeField(entity, "CreatedAt")
	updatedField, hasUpdated := repoUtilsTimeField(entity, "UpdatedAt")
	_ = createdField
	_ = updatedField
	if !(hasCreated && hasUpdated) {
		errs = append(errs, "Entity missing required timestamp fields (created_at, updated_at)")
		result.Set("errors", errs)
		return result, nil
	}
	result.Set("has_timestamps", true)

	createdAt := repoUtilsFieldValue(entity, "CreatedAt")
	updatedAt := repoUtilsFieldValue(entity, "UpdatedAt")
	createdValid := false
	updatedValid := false
	if createdAt != nil {
		if t, ok := repoUtilsAsTime(createdAt); ok {
			result.Set("created_at", value_objects.IsoFormat(t))
			createdValid = true
			if !repoUtilsIsUTC(t) {
				errs = append(errs, "created_at must be timezone-aware UTC datetime")
			}
		} else {
			errs = append(errs, fmt.Sprintf("created_at must be datetime, got %s", repoUtilsTypeName(createdAt)))
		}
	}
	if updatedAt != nil {
		if t, ok := repoUtilsAsTime(updatedAt); ok {
			result.Set("updated_at", value_objects.IsoFormat(t))
			updatedValid = true
			if !repoUtilsIsUTC(t) {
				errs = append(errs, "updated_at must be timezone-aware UTC datetime")
			}
		} else {
			errs = append(errs, fmt.Sprintf("updated_at must be datetime, got %s", repoUtilsTypeName(updatedAt)))
		}
	}
	if createdValid && updatedValid && BothAreDatetime(createdAt, updatedAt) {
		c, _ := repoUtilsAsTime(createdAt)
		u, _ := repoUtilsAsTime(updatedAt)
		if u.Before(c) {
			errs = append(errs, "updated_at cannot be before created_at")
		}
	}
	result.Set("errors", errs)
	valid := len(errs) == 0
	result.Set("timestamps_valid", valid)
	tzCompliant := valid && createdValid && updatedValid
	if t, ok := repoUtilsAsTime(createdAt); ok && !repoUtilsIsUTC(t) {
		tzCompliant = false
	}
	if t, ok := repoUtilsAsTime(updatedAt); ok && !repoUtilsIsUTC(t) {
		tzCompliant = false
	}
	result.Set("timezone_compliant", tzCompliant)
	return result, nil
}

// BothAreDatetime reports whether both values are datetimes.
func BothAreDatetime(dt1, dt2 any) bool {
	_, ok1 := repoUtilsAsTime(dt1)
	_, ok2 := repoUtilsAsTime(dt2)
	return ok1 && ok2
}

// NormalizeQueryParams trims strings, normalizes timestamps and drops None list items.
func NormalizeQueryParams(params Kwargs) (Kwargs, error) {
	normalized := NewKwargs()
	if params == nil {
		return normalized, nil
	}
	for _, key := range params.Keys() {
		value, _ := params.Get(key)
		if value == nil {
			continue
		}
		if strings.HasSuffix(key, "_at") || key == "start_time" || key == "end_time" || key == "before" || key == "after" {
			utils := GetRepositoryDatabaseUtils()
			if utils == nil {
				return nil, exceptions.NewConfigurationException("Repository database utils are not registered", "")
			}
			t, err := utils.NormalizeTimestamp(value)
			if err != nil {
				return nil, exceptions.NewValidationException("Invalid query parameters: "+err.Error(), "", nil)
			}
			if t == nil {
				normalized.Set(key, nil)
			} else {
				normalized.Set(key, *t)
			}
			continue
		}
		switch v := value.(type) {
		case string:
			if trimmed := value_objects.PyStrip(v); trimmed != "" {
				normalized.Set(key, trimmed)
			} else {
				normalized.Set(key, nil)
			}
		case bool:
			normalized.Set(key, v)
		case int, int8, int16, int32, int64, float32, float64:
			normalized.Set(key, v)
		case []any:
			list := []any{}
			for _, item := range v {
				if item != nil {
					list = append(list, item)
				}
			}
			normalized.Set(key, list)
		case []string:
			list := []any{}
			for _, item := range v {
				list = append(list, item)
			}
			normalized.Set(key, list)
		default:
			normalized.Set(key, v)
		}
	}
	return normalized, nil
}

// WithDatabaseErrorHandling is the Go form of the with_database_error_handling decorator.
func WithDatabaseErrorHandling[T any](fn func() (T, error)) (T, error) {
	v, err := fn()
	if err == nil {
		return v, nil
	}
	switch err.(type) {
	case *exceptions.ValidationException, *exceptions.ConfigurationException:
		return v, err
	}
	if database.IsSQLAlchemyError(err) {
		return v, exceptions.NewDatabaseException("Database operation failed: "+err.Error(), "", "")
	}
	return v, exceptions.NewDatabaseException("Unexpected database error: "+err.Error(), "", "")
}

// GetPerformanceSettings returns the performance configuration.
func GetPerformanceSettings() (*entities.OrderedMap[any], error) {
	config, err := GetRepositoryConfig()
	if err != nil {
		return nil, err
	}
	batchSize, err := repoUtilsGetenvInt("REPO_BATCH_SIZE", "100")
	if err != nil {
		return nil, err
	}
	poolSize, err := repoUtilsGetenvInt("DB_POOL_SIZE", "10")
	if err != nil {
		return nil, err
	}
	queryTimeout, err := repoUtilsGetenvInt("QUERY_TIMEOUT", "30")
	if err != nil {
		return nil, err
	}
	settings := entities.NewOrderedMap[any]()
	settings.Set("batch_size", batchSize)
	settings.Set("connection_pool_size", poolSize)
	settings.Set("query_timeout", queryTimeout)
	settings.Set("enable_query_cache", repoUtilsConfigBool(config, "use_cache", true))
	settings.Set("enable_lazy_loading", repoUtilsConfigBool(config, "performance_mode", true))
	settings.Set("timestamp_index_optimization", true)
	settings.Set("bulk_operations_enabled", true)
	return settings, nil
}

// GetRepositoryHealthStatus returns the repository health status; failures become an unhealthy
// result, as in Python.
func GetRepositoryHealthStatus() *entities.OrderedMap[any] {
	status := "unhealthy"
	out := entities.NewOrderedMap[any]()
	utils := GetRepositoryDatabaseUtils()
	if utils == nil {
		out.Set("status", "unhealthy")
		out.Set("error", "Repository database utils are not registered")
		out.Set("checked_at", value_objects.IsoFormat(time.Now().UTC()))
		return out
	}
	dbHealth, err := utils.CheckDatabaseHealth()
	if err != nil {
		out.Set("status", "unhealthy")
		out.Set("error", err.Error())
		out.Set("checked_at", value_objects.IsoFormat(time.Now().UTC()))
		return out
	}
	config, err := GetRepositoryConfig()
	if err != nil {
		out.Set("status", "unhealthy")
		out.Set("error", err.Error())
		out.Set("checked_at", value_objects.IsoFormat(time.Now().UTC()))
		return out
	}
	if v, _ := dbHealth.Get("status"); v == "healthy" {
		status = "healthy"
	}
	perf, err := GetPerformanceSettings()
	if err != nil {
		out.Set("status", "unhealthy")
		out.Set("error", err.Error())
		out.Set("checked_at", value_objects.IsoFormat(time.Now().UTC()))
		return out
	}
	repoConfig := entities.NewOrderedMap[any]()
	dt, _ := config.Get("database_type")
	env, _ := config.Get("environment")
	tsActive, _ := config.Get("timestamp_events_enabled")
	cleanMode, _ := config.Get("clean_architecture_mode")
	repoConfig.Set("database_type", dt)
	repoConfig.Set("environment", env)
	repoConfig.Set("timestamp_events_active", tsActive)
	repoConfig.Set("clean_architecture_mode", cleanMode)
	out.Set("status", status)
	out.Set("database_health", dbHealth)
	out.Set("repository_config", repoConfig)
	out.Set("performance_settings", perf)
	out.Set("checked_at", value_objects.IsoFormat(time.Now().UTC()))
	return out
}

// CreateRepositorySessionContext returns the database session context (database_utils.get_session).
func CreateRepositorySessionContext() (any, error) {
	utils := GetRepositoryDatabaseUtils()
	if utils == nil {
		return nil, exceptions.NewConfigurationException("Repository database utils are not registered", "")
	}
	return utils.GetSession()
}

// RepositoryMetrics collects repository operation metrics.
type RepositoryMetrics struct {
	OperationCounts map[string]int
	ErrorCounts     map[string]int
	StartTime       time.Time
}

// NewRepositoryMetrics builds an empty metrics collector.
func NewRepositoryMetrics() *RepositoryMetrics {
	return &RepositoryMetrics{OperationCounts: map[string]int{}, ErrorCounts: map[string]int{}, StartTime: time.Now().UTC()}
}

// RecordOperation records a successful repository operation.
func (m *RepositoryMetrics) RecordOperation(operationName string) {
	m.OperationCounts[operationName]++
}

// RecordError records a failed repository operation.
func (m *RepositoryMetrics) RecordError(operationName string) {
	m.ErrorCounts[operationName+"_error"]++
}

// GetMetrics returns the collected metrics.
func (m *RepositoryMetrics) GetMetrics() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("uptime_seconds", time.Since(m.StartTime).Seconds())
	out.Set("operation_counts", repoUtilsCountMap(m.OperationCounts))
	out.Set("error_counts", repoUtilsCountMap(m.ErrorCounts))
	out.Set("total_operations", repoUtilsSum(m.OperationCounts))
	out.Set("total_errors", repoUtilsSum(m.ErrorCounts))
	out.Set("success_rate", m.CalculateSuccessRate())
	out.Set("collected_at", value_objects.IsoFormat(time.Now().UTC()))
	return out
}

// CalculateSuccessRate is _calculate_success_rate.
func (m *RepositoryMetrics) CalculateSuccessRate() float64 {
	totalOps, totalErrors := repoUtilsSum(m.OperationCounts), repoUtilsSum(m.ErrorCounts)
	if totalOps+totalErrors == 0 {
		return 1.0
	}
	return float64(totalOps) / float64(totalOps+totalErrors)
}

var repositoryMetrics *RepositoryMetrics

// GetRepositoryMetrics returns the singleton repository metrics instance.
func GetRepositoryMetrics() *RepositoryMetrics {
	if repositoryMetrics == nil {
		repositoryMetrics = NewRepositoryMetrics()
	}
	return repositoryMetrics
}

// ---- helpers -------------------------------------------------------------------

func repoUtilsGetenvInt(key, fallback string) (int, error) {
	raw := repoUtilsGetenvDefault(key, fallback)
	n, err := strconv.Atoi(raw)
	if err != nil {
		return 0, &ValueError{Msg: fmt.Sprintf("invalid literal for int() with base 10: %s", value_objects.PyRepr(raw))}
	}
	return n, nil
}

func repoUtilsConfigBool(config *entities.OrderedMap[any], key string, fallback bool) any {
	v, ok := config.Get(key)
	if !ok {
		return fallback
	}
	return v
}

func repoUtilsCountMap(counts map[string]int) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	// Python dict insertion order: sorted for a deterministic Go equivalent.
	keys := make([]string, 0, len(counts))
	for k := range counts {
		keys = append(keys, k)
	}
	repoUtilsSortStrings(keys)
	for _, k := range keys {
		out.Set(k, counts[k])
	}
	return out
}

func repoUtilsSortStrings(keys []string) {
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
}

func repoUtilsSum(counts map[string]int) int {
	total := 0
	for _, v := range counts {
		total += v
	}
	return total
}

func repoUtilsTypeName(v any) string {
	if v == nil {
		return "NoneType"
	}
	t := reflect.TypeOf(v)
	for t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	return t.Name()
}

func repoUtilsTimeField(entity any, name string) (reflect.Value, bool) {
	v := reflect.ValueOf(entity)
	for v.Kind() == reflect.Pointer {
		if v.IsNil() {
			return reflect.Value{}, false
		}
		v = v.Elem()
	}
	if v.Kind() != reflect.Struct {
		return reflect.Value{}, false
	}
	f := v.FieldByName(name)
	return f, f.IsValid()
}

func repoUtilsFieldValue(entity any, name string) any {
	f, ok := repoUtilsTimeField(entity, name)
	if !ok || !f.IsValid() {
		return nil
	}
	if f.Kind() == reflect.Pointer {
		if f.IsNil() {
			return nil
		}
		return f.Interface()
	}
	return f.Interface()
}

func repoUtilsAsTime(v any) (time.Time, bool) {
	switch t := v.(type) {
	case time.Time:
		return t, true
	case *time.Time:
		if t == nil {
			return time.Time{}, false
		}
		return *t, true
	}
	return time.Time{}, false
}

func repoUtilsIsUTC(t time.Time) bool { return t.Location() == time.UTC }
