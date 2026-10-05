package database

// Database Adapter for SQLite/PostgreSQL compatibility (Python
// task_management/infrastructure/database/database_adapter.py).
//
// The Go database is always PostgreSQL, so the SQLite branches and the NotImplementedError
// paths for other dialects are not ported; the PostgreSQL expression text is produced
// verbatim. Python's execute_with_json_result takes named parameters (SQLAlchemy ":name"
// bindings) which database/sql does not have; callers pass positional arguments instead.

import (
	"context"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// DatabaseAdapter generates dialect-specific JSON SQL.
type DatabaseAdapter struct {
	Engine *Engine
}

// NewDatabaseAdapter wraps an engine.
func NewDatabaseAdapter(engine *Engine) *DatabaseAdapter {
	return &DatabaseAdapter{Engine: engine}
}

// JSONExtract is column->>'path'.
func (a *DatabaseAdapter) JSONExtract(column, path string) string {
	return column + "->>" + tmvo.PyRepr(path)
}

// JSONSet is jsonb_set(column, '{path}', <json value>).
func (a *DatabaseAdapter) JSONSet(column, path string, value any) (string, error) {
	jsonValue, err := tmvo.PyJSONDumps(value, -1)
	if err != nil {
		return "", err
	}
	return "jsonb_set(" + column + ", '{" + path + "}', " + tmvo.PyRepr(jsonValue) + ")", nil
}

// JSONMerge is column || <json data>::jsonb.
func (a *DatabaseAdapter) JSONMerge(column string, newData *entities.OrderedMap[any]) (string, error) {
	jsonData, err := tmvo.PyJSONDumps(newData, -1)
	if err != nil {
		return "", err
	}
	return column + " || " + tmvo.PyRepr(jsonData) + "::jsonb", nil
}

// PrepareJSONValue mirrors the Python: dict/list values are json.dumps-ed, everything else
// goes through str().
func (a *DatabaseAdapter) PrepareJSONValue(value any) (string, error) {
	if isJSONContainer(value) {
		return tmvo.PyJSONDumps(value, -1)
	}
	return tmvo.PyStr(value), nil
}

// ParseJSONValue mirrors the Python: None stays None, a string is json.loads-ed when valid
// (otherwise returned unchanged), anything else is returned unchanged.
func (a *DatabaseAdapter) ParseJSONValue(value any) any {
	if value == nil {
		return nil
	}
	if s, ok := value.(string); ok {
		if v, err := entities.DecodeJSON([]byte(s)); err == nil {
			return v
		}
		return s
	}
	return value
}

// CreateJSONContainsCondition is column @> <search dict>::jsonb.
func (a *DatabaseAdapter) CreateJSONContainsCondition(column string, searchDict *entities.OrderedMap[any]) (string, error) {
	searchJSON, err := tmvo.PyJSONDumps(searchDict, -1)
	if err != nil {
		return "", err
	}
	return column + " @> " + tmvo.PyRepr(searchJSON) + "::jsonb", nil
}

// GetJSONKeys is jsonb_object_keys(column).
func (a *DatabaseAdapter) GetJSONKeys(column string) string {
	return "jsonb_object_keys(" + column + ")"
}

// ExecuteWithJSONResult runs the query and parses result columns that look like JSON
// objects or arrays, like the Python dict(row._mapping) loop.
func (a *DatabaseAdapter) ExecuteWithJSONResult(ctx context.Context, query string, args ...any) ([]*entities.OrderedMap[any], error) {
	conn, err := a.Engine.DB.Conn(ctx)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	rows, err := conn.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	columns, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	parsed := []*entities.OrderedMap[any]{}
	for rows.Next() {
		values := make([]any, len(columns))
		ptrs := make([]any, len(columns))
		for i := range values {
			ptrs[i] = &values[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		rowDict := entities.NewOrderedMap[any]()
		for i, name := range columns {
			rowDict.Set(name, parseJSONScanValue(values[i]))
		}
		parsed = append(parsed, rowDict)
	}
	return parsed, rows.Err()
}

// GetSchemaType is the JSON column type; always JSONB here.
func (a *DatabaseAdapter) GetSchemaType() string { return "JSONB" }

// MigrateToPostgresql is a no-op in Python too.
func (a *DatabaseAdapter) MigrateToPostgresql(sqliteDBPath, postgresqlURL string) {}

// WithSession provides the get_session context manager over a transaction: commit on
// success, rollback on error.
func (a *DatabaseAdapter) WithSession(ctx context.Context, fn func(DBTX) error) error {
	conn, err := a.Engine.DB.Conn(ctx)
	if err != nil {
		return err
	}
	defer conn.Close()
	tx, err := conn.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	if err := fn(AsDBTX(tx)); err != nil {
		_ = tx.Rollback()
		return err
	}
	return tx.Commit()
}

func isJSONContainer(v any) bool {
	switch v.(type) {
	case tmvo.OrderedAny, []any, map[string]any:
		return true
	}
	return false
}

func parseJSONScanValue(v any) any {
	var s string
	switch x := v.(type) {
	case string:
		s = x
	case []byte:
		s = string(x)
	default:
		return v
	}
	if strings.HasPrefix(s, "{") || strings.HasPrefix(s, "[") {
		if decoded, err := entities.DecodeJSON([]byte(s)); err == nil {
			return decoded
		}
	}
	return s
}
