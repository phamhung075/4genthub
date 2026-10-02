package database

// Enhanced Database Utilities (Python
// task_management/infrastructure/database/database_utils.py).
//
// SQLAlchemy Sessions map to direct *sql.DB calls; check_database_health and friends return
// OrderedMap in Python key order, and errors become DatabaseException/ValidationException
// with the Python messages. Python's round(x, 2) uses banker's rounding; Go's math.Round is
// used here (values are timings, so exact ties are not observable).

import (
	"context"
	"database/sql"
	"fmt"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// pgColumnInfo is a reflected column (name plus a SQLAlchemy-like type string).
type pgColumnInfo struct {
	Name string
	Type string
}

// introspectColumnTypes reads information_schema.columns in ordinal order.
func introspectColumnTypes(ctx context.Context, q interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}, table string) ([]pgColumnInfo, error) {
	rows, err := q.QueryContext(ctx, "SELECT column_name, data_type, udt_name, character_maximum_length FROM information_schema.columns WHERE table_schema = current_schema() AND table_name = $1 ORDER BY ordinal_position", table)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []pgColumnInfo
	for rows.Next() {
		var name, dataType, udtName string
		var charMax sql.NullInt64
		if err := rows.Scan(&name, &dataType, &udtName, &charMax); err != nil {
			return nil, err
		}
		out = append(out, pgColumnInfo{Name: name, Type: pgTypeString(dataType, udtName, charMax)})
	}
	return out, rows.Err()
}

// pgTypeString renders a PostgreSQL type the way SQLAlchemy reflection does.
func pgTypeString(dataType, udtName string, charMax sql.NullInt64) string {
	switch dataType {
	case "character varying", "character":
		if charMax.Valid {
			return "VARCHAR(" + strconv.FormatInt(charMax.Int64, 10) + ")"
		}
		return "VARCHAR"
	case "timestamp without time zone":
		return "TIMESTAMP WITHOUT TIME ZONE"
	case "timestamp with time zone":
		return "TIMESTAMP WITH TIME ZONE"
	case "USER-DEFINED":
		return udtName
	case "ARRAY":
		return strings.ToUpper(udtName)
	}
	return strings.ToUpper(dataType)
}

// introspectForeignKeys returns the constrained column names of a table's foreign keys.
func introspectForeignKeys(ctx context.Context, q interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}, table string) ([]string, error) {
	rows, err := q.QueryContext(ctx, `SELECT a.attname
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f' AND t.relname = $1 AND n.nspname = current_schema()
ORDER BY a.attnum`, table)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		out = append(out, name)
	}
	return out, rows.Err()
}

// introspectIndexNames returns all index names in the current schema.
func introspectIndexNames(ctx context.Context, q interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
}) (map[string]bool, error) {
	rows, err := q.QueryContext(ctx, "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string]bool{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		out[name] = true
	}
	return out, rows.Err()
}

// DatabaseUtils provides database operations, schema and timestamp utilities.
type DatabaseUtils struct {
	ctx    context.Context
	config *DatabaseConfig
	engine *Engine
}

// NewDatabaseUtils builds the utilities over a configuration.
func NewDatabaseUtils(ctx context.Context, config *DatabaseConfig) *DatabaseUtils {
	return &DatabaseUtils{ctx: ctx, config: config}
}

// Engine returns the engine, creating it from the configuration if needed.
func (u *DatabaseUtils) Engine() (*Engine, error) {
	if u.engine == nil {
		e, err := u.config.GetEngine()
		if err != nil {
			return nil, err
		}
		u.engine = e
	}
	return u.engine, nil
}

// CheckDatabaseHealth mirrors check_database_health.
func (u *DatabaseUtils) CheckDatabaseHealth() *entities.OrderedMap[any] {
	start := time.Now().UTC()
	engine, err := u.Engine()
	if err != nil {
		return databaseUtilsUnhealthy(err)
	}
	var one int
	if err := engine.DB.QueryRowContext(u.ctx, "SELECT 1").Scan(&one); err != nil {
		return databaseUtilsUnhealthy(err)
	}
	var version string
	if err := engine.DB.QueryRowContext(u.ctx, "SELECT version()").Scan(&version); err != nil {
		return databaseUtilsUnhealthy(err)
	}
	tables, err := tableNames(u.ctx, engine.DB)
	if err != nil {
		return databaseUtilsUnhealthy(err)
	}
	end := time.Now().UTC()
	out := entities.NewOrderedMap[any]()
	out.Set("status", "healthy")
	out.Set("database_type", "postgresql")
	out.Set("database_version", version)
	out.Set("table_count", len(tables))
	out.Set("response_time_ms", math.Round(end.Sub(start).Seconds()*1000*100)/100)
	out.Set("timestamp_events_active", true)
	out.Set("checked_at", tmvo.IsoFormat(end))
	return out
}

func databaseUtilsUnhealthy(err error) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("status", "unhealthy")
	out.Set("error", err.Error())
	out.Set("checked_at", tmvo.IsoFormat(time.Now().UTC()))
	return out
}

// ValidateSchemaIntegrity mirrors validate_schema_integrity.
func (u *DatabaseUtils) ValidateSchemaIntegrity() (*entities.OrderedMap[any], error) {
	out, err := u.validateSchemaIntegrityInner()
	if err != nil {
		return nil, exceptions.NewDatabaseException("Schema validation error: "+err.Error(), "", "")
	}
	return out, nil
}

func (u *DatabaseUtils) validateSchemaIntegrityInner() (*entities.OrderedMap[any], error) {
	engine, err := u.Engine()
	if err != nil {
		return nil, err
	}
	tables, err := tableNames(u.ctx, engine.DB)
	if err != nil {
		return nil, err
	}
	errorsList := []any{}
	warnings := []any{}
	tablesChecked := 0
	timestampTables := 0
	for _, table := range tables {
		tablesChecked++
		columns, err := introspectColumnTypes(u.ctx, engine.DB, table)
		if err != nil {
			return nil, err
		}
		names := map[string]bool{}
		for _, c := range columns {
			names[c.Name] = true
		}
		hasCreated := names["created_at"]
		hasUpdated := names["updated_at"]
		if hasCreated || hasUpdated {
			timestampTables++
			if hasCreated && !hasUpdated {
				warnings = append(warnings, "Table "+table+" has created_at but missing updated_at")
			} else if hasUpdated && !hasCreated {
				warnings = append(warnings, "Table "+table+" has updated_at but missing created_at")
			}
			for _, c := range columns {
				if c.Name == "created_at" || c.Name == "updated_at" {
					if !strings.HasPrefix(strings.ToLower(c.Type), "datetime") {
						errorsList = append(errorsList, "Table "+table+"."+c.Name+" should be DATETIME type, got "+c.Type)
					}
				}
			}
		}
	}
	existing := map[string]bool{}
	for _, t := range tables {
		existing[t] = true
	}
	required := []string{"projects", "project_git_branchs", "tasks", "subtasks", "global_contexts", "project_contexts", "branch_contexts", "task_contexts"}
	for _, name := range required {
		if !existing[name] {
			errorsList = append(errorsList, "Missing required table: "+name)
		}
	}
	status := "valid"
	timestampCompliance := true
	if len(errorsList) > 0 {
		status = "invalid"
		timestampCompliance = false
	} else if len(warnings) > 0 {
		status = "valid_with_warnings"
	}
	out := entities.NewOrderedMap[any]()
	out.Set("status", status)
	out.Set("errors", errorsList)
	out.Set("warnings", warnings)
	out.Set("timestamp_compliance", timestampCompliance)
	out.Set("tables_checked", tablesChecked)
	out.Set("timestamp_tables", timestampTables)
	return out, nil
}

// NormalizeTimestamp mirrors normalize_timestamp; None stays None.
func (u *DatabaseUtils) NormalizeTimestamp(timestamp any) (*time.Time, error) {
	if timestamp == nil {
		return nil, nil
	}
	var dt time.Time
	switch v := timestamp.(type) {
	case string:
		s := v
		if strings.HasSuffix(s, "Z") {
			s = s[:len(s)-1] + "+00:00"
		}
		parsed, err := tmvo.ParseISO(s)
		if err != nil {
			return nil, exceptions.NewValidationException("Invalid timestamp format: "+err.Error(), "", nil)
		}
		dt = parsed
	case time.Time:
		dt = v
	default:
		return nil, exceptions.NewValidationException(fmt.Sprintf("Invalid timestamp type: %T", timestamp), "", nil)
	}
	dt = dt.UTC()
	return &dt, nil
}

// ValidateTimestampRange mirrors validate_timestamp_range.
func (u *DatabaseUtils) ValidateTimestampRange(startTime, endTime *time.Time) (time.Time, time.Time, error) {
	if startTime == nil || endTime == nil {
		return time.Time{}, time.Time{}, exceptions.NewValidationException("Both start_time and end_time must be provided", "", nil)
	}
	normStart, err := u.NormalizeTimestamp(*startTime)
	if err != nil {
		return time.Time{}, time.Time{}, err
	}
	normEnd, err := u.NormalizeTimestamp(*endTime)
	if err != nil {
		return time.Time{}, time.Time{}, err
	}
	if !normStart.Before(*normEnd) {
		return time.Time{}, time.Time{}, exceptions.NewValidationException("start_time must be before end_time", "", nil)
	}
	maxRangeDays := 365 * 10
	if days := int(normEnd.Sub(*normStart).Hours() / 24); days > maxRangeDays {
		return time.Time{}, time.Time{}, exceptions.NewValidationException(fmt.Sprintf("Timestamp range too large (max %d days)", maxRangeDays), "", nil)
	}
	return *normStart, *normEnd, nil
}

// OptimizeDatabasePerformance mirrors optimize_database_performance.
func (u *DatabaseUtils) OptimizeDatabasePerformance() (*entities.OrderedMap[any], error) {
	out, err := u.optimizeDatabasePerformanceInner()
	if err != nil {
		return nil, exceptions.NewDatabaseException("Database optimization error: "+err.Error(), "", "")
	}
	return out, nil
}

func (u *DatabaseUtils) optimizeDatabasePerformanceInner() (*entities.OrderedMap[any], error) {
	engine, err := u.Engine()
	if err != nil {
		return nil, err
	}
	operations := []any{}
	gain := entities.NewOrderedMap[any]()
	recommendations := []any{}
	if _, err := engine.DB.ExecContext(u.ctx, "ANALYZE"); err != nil {
		return nil, err
	}
	operations = append(operations, "ran_analyze")
	if _, err := engine.DB.ExecContext(u.ctx, "VACUUM"); err != nil {
		return nil, err
	}
	operations = append(operations, "ran_vacuum")
	rows, err := engine.DB.QueryContext(u.ctx, "SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del FROM pg_stat_user_tables WHERE schemaname = 'public' ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC LIMIT 5")
	if err != nil {
		return nil, err
	}
	top := []any{}
	for rows.Next() {
		var schema, table string
		var ins, upd, del sql.NullInt64
		if err := rows.Scan(&schema, &table, &ins, &upd, &del); err != nil {
			rows.Close()
			return nil, err
		}
		entry := entities.NewOrderedMap[any]()
		entry.Set("table", table)
		entry.Set("total_operations", ins.Int64+upd.Int64+del.Int64)
		top = append(top, entry)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()
	gain.Set("top_active_tables", top)
	tables, err := tableNames(u.ctx, engine.DB)
	if err != nil {
		return nil, err
	}
	if len(tables) > 20 {
		recommendations = append(recommendations, "Consider table partitioning for large tables")
	}
	recommendations = append(recommendations,
		"Regularly run ANALYZE for optimal query planning",
		"Monitor timestamp query performance on large tables",
		"Consider composite indexes for timestamp + status queries")
	out := entities.NewOrderedMap[any]()
	out.Set("status", "completed")
	out.Set("operations", operations)
	out.Set("performance_gain", gain)
	out.Set("recommendations", recommendations)
	return out, nil
}

// SetupCleanTimestampInfrastructure mirrors setup_clean_timestamp_infrastructure.
func (u *DatabaseUtils) SetupCleanTimestampInfrastructure() (*entities.OrderedMap[any], error) {
	out, err := u.setupCleanTimestampInfrastructureInner()
	if err != nil {
		return nil, exceptions.NewDatabaseException("Timestamp setup error: "+err.Error(), "", "")
	}
	return out, nil
}

func (u *DatabaseUtils) setupCleanTimestampInfrastructureInner() (*entities.OrderedMap[any], error) {
	engine, err := u.Engine()
	if err != nil {
		return nil, err
	}
	CleanupTimestampEvents()
	SetupTimestampEvents()
	var one int
	if err := engine.DB.QueryRowContext(u.ctx, "SELECT 1").Scan(&one); err != nil {
		return nil, err
	}
	out := entities.NewOrderedMap[any]()
	out.Set("status", "success")
	out.Set("timestamp_events_active", true)
	out.Set("automatic_timestamp_management", true)
	out.Set("supported_entities", []any{"Project", "GitBranch", "Task", "Subtask", "Agent", "Label", "Template"})
	out.Set("setup_at", tmvo.IsoFormat(time.Now().UTC()))
	return out, nil
}

// GetDatabaseMetrics mirrors get_database_metrics.
func (u *DatabaseUtils) GetDatabaseMetrics() (*entities.OrderedMap[any], error) {
	out, err := u.getDatabaseMetricsInner()
	if err != nil {
		return nil, exceptions.NewDatabaseException("Metrics collection error: "+err.Error(), "", "")
	}
	return out, nil
}

func (u *DatabaseUtils) getDatabaseMetricsInner() (*entities.OrderedMap[any], error) {
	engine, err := u.Engine()
	if err != nil {
		return nil, err
	}
	tables, err := tableNames(u.ctx, engine.DB)
	if err != nil {
		return nil, err
	}
	metrics := entities.NewOrderedMap[any]()
	metrics.Set("database_type", "postgresql")
	metrics.Set("table_count", len(tables))
	metrics.Set("timestamp_tables", 0)
	metrics.Set("total_records", 0)
	metrics.Set("performance", entities.NewOrderedMap[any]())
	metrics.Set("collected_at", tmvo.IsoFormat(time.Now().UTC()))
	timestampTables := 0
	totalRecords := 0
	for _, table := range tables {
		columns, err := introspectColumnTypes(u.ctx, engine.DB, table)
		if err != nil {
			return nil, err
		}
		hasTimestamps := false
		for _, c := range columns {
			if c.Name == "created_at" || c.Name == "updated_at" {
				hasTimestamps = true
			}
		}
		if hasTimestamps {
			timestampTables++
		}
		var count int
		if err := engine.DB.QueryRowContext(u.ctx, "SELECT COUNT(*) FROM "+table).Scan(&count); err == nil {
			totalRecords += count
			metrics.Set("table_"+table+"_count", count)
		}
	}
	metrics.Set("timestamp_tables", timestampTables)
	metrics.Set("total_records", totalRecords)
	start := time.Now().UTC()
	var one int
	if err := engine.DB.QueryRowContext(u.ctx, "SELECT 1").Scan(&one); err != nil {
		return nil, err
	}
	end := time.Now().UTC()
	performance := entities.NewOrderedMap[any]()
	performance.Set("query_response_time_ms", math.Round(end.Sub(start).Seconds()*1000*100)/100)
	performance.Set("timestamp_events_enabled", true)
	performance.Set("clean_architecture_compliant", true)
	metrics.Set("performance", performance)
	return metrics, nil
}

// CreatePerformanceIndexes mirrors create_performance_indexes.
func (u *DatabaseUtils) CreatePerformanceIndexes() (*entities.OrderedMap[any], error) {
	out, err := u.createPerformanceIndexesInner()
	if err != nil {
		return nil, exceptions.NewDatabaseException("Index creation error: "+err.Error(), "", "")
	}
	return out, nil
}

func (u *DatabaseUtils) createPerformanceIndexesInner() (*entities.OrderedMap[any], error) {
	engine, err := u.Engine()
	if err != nil {
		return nil, err
	}
	created := []any{}
	skipped := []any{}
	timestampIndexes := []struct {
		Name    string
		Table   string
		Columns []string
	}{
		{"idx_tasks_timestamps", "tasks", []string{"created_at", "updated_at"}},
		{"idx_projects_timestamps", "projects", []string{"created_at", "updated_at"}},
		{"idx_subtasks_timestamps", "subtasks", []string{"created_at", "updated_at"}},
		{"idx_tasks_status_created", "tasks", []string{"status", "created_at"}},
		{"idx_tasks_priority_updated", "tasks", []string{"priority", "updated_at"}},
	}
	existingIndexes, err := introspectIndexNames(u.ctx, engine.DB)
	if err != nil {
		return nil, err
	}
	tables, err := tableNames(u.ctx, engine.DB)
	if err != nil {
		return nil, err
	}
	for _, idx := range timestampIndexes {
		if existingIndexes[idx.Name] {
			skip := entities.NewOrderedMap[any]()
			skip.Set("name", idx.Name)
			skip.Set("reason", "already_exists")
			skipped = append(skipped, skip)
			continue
		}
		if !contains(tables, idx.Table) {
			skip := entities.NewOrderedMap[any]()
			skip.Set("name", idx.Name)
			skip.Set("reason", "table_"+idx.Table+"_not_found")
			skipped = append(skipped, skip)
			continue
		}
		parts := make([]string, len(idx.Columns))
		for i, col := range idx.Columns {
			if col == "created_at" || col == "updated_at" {
				parts[i] = col + " DESC"
			} else {
				parts[i] = col
			}
		}
		columnsStr := strings.Join(parts, ", ")
		createSQL := "CREATE INDEX IF NOT EXISTS " + idx.Name + " ON " + idx.Table + " (" + columnsStr + ")"
		if _, err := engine.DB.ExecContext(u.ctx, createSQL); err != nil {
			skip := entities.NewOrderedMap[any]()
			skip.Set("name", idx.Name)
			skip.Set("reason", "error: "+err.Error())
			skipped = append(skipped, skip)
			continue
		}
		entry := entities.NewOrderedMap[any]()
		entry.Set("name", idx.Name)
		entry.Set("table", idx.Table)
		columns := make([]any, len(idx.Columns))
		for i, c := range idx.Columns {
			columns[i] = c
		}
		entry.Set("columns", columns)
		created = append(created, entry)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("status", "success")
	out.Set("indexes_created", created)
	out.Set("indexes_skipped", skipped)
	out.Set("database_type", "postgresql")
	return out, nil
}

var (
	dbUtilsMu       sync.Mutex
	dbUtilsInstance *DatabaseUtils
)

// GetDatabaseUtils returns the singleton utilities instance.
func GetDatabaseUtils(ctx context.Context, deps Deps) (*DatabaseUtils, error) {
	dbUtilsMu.Lock()
	defer dbUtilsMu.Unlock()
	if dbUtilsInstance == nil {
		cfg, err := GetInstance(ctx, deps)
		if err != nil {
			return nil, err
		}
		dbUtilsInstance = NewDatabaseUtils(ctx, cfg)
	}
	return dbUtilsInstance, nil
}

// CheckDatabaseHealth is the convenience function.
func CheckDatabaseHealth(ctx context.Context, deps Deps) *entities.OrderedMap[any] {
	u, err := GetDatabaseUtils(ctx, deps)
	if err != nil {
		return databaseUtilsUnhealthy(err)
	}
	return u.CheckDatabaseHealth()
}

// ValidateSchemaIntegrity is the convenience function.
func ValidateSchemaIntegrity(ctx context.Context, deps Deps) (*entities.OrderedMap[any], error) {
	u, err := GetDatabaseUtils(ctx, deps)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Schema validation error: "+err.Error(), "", "")
	}
	return u.ValidateSchemaIntegrity()
}

// SetupCleanTimestampInfrastructure is the convenience function.
func SetupCleanTimestampInfrastructure(ctx context.Context, deps Deps) (*entities.OrderedMap[any], error) {
	u, err := GetDatabaseUtils(ctx, deps)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Timestamp setup error: "+err.Error(), "", "")
	}
	return u.SetupCleanTimestampInfrastructure()
}

// OptimizeDatabasePerformance is the convenience function.
func OptimizeDatabasePerformance(ctx context.Context, deps Deps) (*entities.OrderedMap[any], error) {
	u, err := GetDatabaseUtils(ctx, deps)
	if err != nil {
		return nil, exceptions.NewDatabaseException("Database optimization error: "+err.Error(), "", "")
	}
	return u.OptimizeDatabasePerformance()
}
