package database

// Tests for the production models in models_prod.go.
//
// TestProductionModelsMetadata checks the row structs against their table metadata.
// TestProductionModelsCRUD runs a full round trip (insert, select, update, select, delete) for
// every model through a fake database/sql driver, so it needs no server.
// TestProductionModelsCRUDRealPostgres runs the same round trip against a real database when
// TEST_DATABASE_URL points at a production-like schema (it must already contain the eight
// tables and, for the tables whose user_id references users, a usable users table).

import (
	"context"
	"crypto/rand"
	"database/sql"
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"
)

const prodTestDatabaseURLEnv = "TEST_DATABASE_URL"

var (
	prodRawMessageType = reflect.TypeOf(json.RawMessage(nil))
	prodTimeType       = reflect.TypeOf(time.Time{})
	prodTimeA          = time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)
	prodTimeB          = time.Date(2025, 6, 7, 8, 9, 10, 0, time.UTC)
)

// prodModelTypes resolves a TableDef.Model to its row struct type.
var prodModelTypes = map[string]reflect.Type{
	"AgentImportHistory":       reflect.TypeOf(AgentImportHistory{}),
	"AppliedMigration":         reflect.TypeOf(AppliedMigration{}),
	"TokenTransaction":         reflect.TypeOf(TokenTransaction{}),
	"UserAgentConfigurationMd": reflect.TypeOf(UserAgentConfigurationMd{}),
	"UserAPIToken":             reflect.TypeOf(UserAPIToken{}),
	"UserSession":              reflect.TypeOf(UserSession{}),
}

// prodExpectedColumns is the production column list (name:type) per table. It is the guard
// that the transcribed metadata still matches init_schema_postgresql.sql.
var prodExpectedColumns = map[string][]string{
	"agent_import_history": {
		"id:UUID", "importer_user_id:UUID", "source_instance_id:UUID", "imported_instance_id:UUID",
		"imported_at:TIMESTAMP WITHOUT TIME ZONE", "share_token:VARCHAR",
	},
	"applied_migrations": {
		"id:INTEGER", "migration_name:VARCHAR", "applied_at:TIMESTAMP WITH TIME ZONE",
		"success:BOOLEAN", "error_message:TEXT",
	},
	"token_transactions": {
		"id:UUID", "user_id:UUID", "operation_type:VARCHAR", "tokens_deducted:INTEGER",
		"balance_before:INTEGER", "balance_after:INTEGER", "operation_metadata:JSON",
		"created_at:TIMESTAMP WITHOUT TIME ZONE",
	},
	"user_agent_configurations_md": {
		"id:UUID", "instance_id:UUID", "configuration_type:VARCHAR", "content_markdown:TEXT",
		"created_at:TIMESTAMP WITHOUT TIME ZONE", "updated_at:TIMESTAMP WITHOUT TIME ZONE",
	},
	"user_api_tokens": {
		"id:UUID", "user_id:UUID", "token_hash:VARCHAR", "token_cost:INTEGER", "name:VARCHAR",
		"scopes:JSON", "is_active:BOOLEAN", "expires_at:TIMESTAMP WITHOUT TIME ZONE",
		"last_used_at:TIMESTAMP WITHOUT TIME ZONE", "created_at:TIMESTAMP WITHOUT TIME ZONE",
		"updated_at:TIMESTAMP WITHOUT TIME ZONE", "revoked_at:TIMESTAMP WITHOUT TIME ZONE",
	},
	"user_sessions": {
		"id:UUID", "user_id:UUID", "session_token:VARCHAR", "refresh_token:VARCHAR",
		"ip_address:VARCHAR", "user_agent:TEXT", "device_info:JSON",
		"created_at:TIMESTAMP WITHOUT TIME ZONE", "last_activity:TIMESTAMP WITHOUT TIME ZONE",
		"expires_at:TIMESTAMP WITHOUT TIME ZONE", "revoked_at:TIMESTAMP WITHOUT TIME ZONE",
		"is_active:BOOLEAN",
	},
}

func TestProductionModelsMetadata(t *testing.T) {
	if len(ProductionTables) != 6 {
		t.Fatalf("ProductionTables has %d entries, want 6", len(ProductionTables))
	}
	seen := map[string]bool{}
	for _, table := range ProductionTables {
		if seen[table.Name] {
			t.Fatalf("duplicate table %s", table.Name)
		}
		seen[table.Name] = true

		typ, ok := prodModelTypes[table.Model]
		if !ok {
			t.Fatalf("no Go model registered for %s", table.Model)
		}
		if typ.NumField() != len(table.Columns) {
			t.Fatalf("%s: %d struct fields, %d columns", table.Name, typ.NumField(), len(table.Columns))
		}
		for i, c := range table.Columns {
			field := typ.Field(i)
			if got := field.Tag.Get("db"); got != c.Name {
				t.Fatalf("%s column %d: db tag %q, want %q", table.Name, i, got, c.Name)
			}
			if field.Name != c.GoField {
				t.Fatalf("%s column %s: Go field %q, want %q", table.Name, c.Name, field.Name, c.GoField)
			}
			if field.Type == prodRawMessageType && c.SQLType != "JSON" {
				t.Fatalf("%s.%s: json.RawMessage field for %s", table.Name, c.Name, c.SQLType)
			}
		}
		want, ok := prodExpectedColumns[table.Name]
		if !ok {
			t.Fatalf("no expected columns for %s", table.Name)
		}
		var got []string
		for _, c := range table.Columns {
			got = append(got, c.Name+":"+c.SQLType)
		}
		if !reflect.DeepEqual(got, want) {
			t.Fatalf("%s columns = %v, want %v", table.Name, got, want)
		}
	}
	if len(prodExpectedColumns) != len(ProductionTables) {
		t.Fatalf("expected column map has %d tables, want %d", len(prodExpectedColumns), len(ProductionTables))
	}
}

func TestProductionModelsCRUD(t *testing.T) {
	ctx := context.Background()
	db := newProdFakeDB().open()
	defer db.Close()
	for _, table := range ProductionTables {
		table := table
		t.Run(table.Name, func(t *testing.T) {
			prodCRUDRoundTrip(t, ctx, db, table, "")
		})
	}
}

func TestProductionModelsCRUDRealPostgres(t *testing.T) {
	dsn := os.Getenv(prodTestDatabaseURLEnv)
	if dsn == "" {
		t.Skip("SKIPPED, NOT PASSED: " + prodTestDatabaseURLEnv + " is unset, so this case did NOT run - " +
			"it needs a DSN whose database already carries the production-like schema (see the note at the top of this file)")
	}
	db, err := PgxOpener(dsn, EngineOptions{PoolSize: 2, MaxOverflow: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	userID := prodUUID()
	if err := prodEnsureUser(ctx, db, userID); err != nil {
		t.Fatalf("ensure users row: %v", err)
	}
	t.Cleanup(func() {
		_, _ = db.ExecContext(context.Background(), "DELETE FROM users WHERE id = $1", userID)
	})
	for _, table := range ProductionTables {
		table := table
		t.Run(table.Name, func(t *testing.T) {
			prodCRUDRoundTrip(t, ctx, db, table, userID)
		})
	}
}

// prodValues are the per-run values that keep a test's rows distinct from existing data.
type prodValues struct {
	suffix string
	userID string
	pkInt  int64
}

func newProdValues(userID string) prodValues {
	if userID == "" {
		userID = prodUUID()
	}
	return prodValues{suffix: prodRandHex(6), userID: userID, pkInt: prodRandInt()}
}

// prodCRUDRoundTrip inserts a row, reads it back, updates it, reads it back, then deletes it.
func prodCRUDRoundTrip(t *testing.T, ctx context.Context, db *sql.DB, table TableDef, userID string) {
	t.Helper()
	v := newProdValues(userID)
	want := reflect.New(prodModelTypes[table.Model])
	prodFillTable(table, want, v, 1)
	if err := prodInsert(ctx, db, table, want); err != nil {
		t.Fatalf("insert: %v", err)
	}
	pk := prodArg(want.Elem().Field(prodPKIndex(table)))

	got, err := prodSelect(ctx, db, table, pk)
	if err != nil {
		t.Fatalf("select after insert: %v", err)
	}
	prodCompareRows(t, table, want, got)

	prodFillTable(table, want, v, 2)
	if err := prodUpdate(ctx, db, table, want); err != nil {
		t.Fatalf("update: %v", err)
	}
	got, err = prodSelect(ctx, db, table, pk)
	if err != nil {
		t.Fatalf("select after update: %v", err)
	}
	prodCompareRows(t, table, want, got)

	if err := prodDelete(ctx, db, table, pk); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := prodSelect(ctx, db, table, pk); err == nil {
		t.Fatal("row still present after delete")
	} else if !errors.Is(err, sql.ErrNoRows) {
		t.Fatalf("select after delete: %v", err)
	}
}

// prodFillTable assigns sample values for variant 1 or 2; the primary key is left untouched for
// variant 2 so the update addresses the inserted row.
func prodFillTable(table TableDef, row reflect.Value, v prodValues, variant int) {
	e := row.Elem()
	for i, c := range table.Columns {
		if variant > 1 && c.PrimaryKey {
			continue
		}
		f := e.Field(i)
		if f.Type() == prodRawMessageType {
			f.SetBytes([]byte(fmt.Sprintf(`{"k":%d}`, variant)))
			continue
		}
		if f.Kind() == reflect.Ptr {
			f.Set(reflect.New(f.Type().Elem()))
			prodFillScalar(f.Elem(), c, v, variant)
			continue
		}
		prodFillScalar(f, c, v, variant)
	}
}

func prodFillScalar(f reflect.Value, c ColumnDef, v prodValues, variant int) {
	switch f.Kind() {
	case reflect.String:
		switch {
		case c.Name == "user_id":
			f.SetString(v.userID)
		case c.SQLType == "UUID":
			f.SetString(prodUUID())
		default:
			f.SetString(fmt.Sprintf("%s_%d_%s", c.Name, variant, v.suffix))
		}
	case reflect.Int64:
		if c.PrimaryKey {
			f.SetInt(v.pkInt)
		} else {
			f.SetInt(int64(7 * variant))
		}
	case reflect.Bool:
		f.SetBool(variant == 1)
	default:
		if f.Type() == prodTimeType {
			if variant == 1 {
				f.Set(reflect.ValueOf(prodTimeA))
			} else {
				f.Set(reflect.ValueOf(prodTimeB))
			}
			return
		}
		panic(fmt.Sprintf("%s: unsupported column %s (%s)", c.Name, c.SQLType, f.Type()))
	}
}

func prodCompareRows(t *testing.T, table TableDef, want, got reflect.Value) {
	t.Helper()
	we, ge := want.Elem(), got.Elem()
	for i, c := range table.Columns {
		wf, gf := we.Field(i), ge.Field(i)
		if wf.Type() == prodRawMessageType {
			if !prodJSONEqual(wf.Bytes(), gf.Bytes()) {
				t.Fatalf("%s.%s: json %s, want %s", table.Name, c.Name, gf.Bytes(), wf.Bytes())
			}
			continue
		}
		if wf.Kind() == reflect.Ptr {
			if wf.IsNil() != gf.IsNil() {
				t.Fatalf("%s.%s: nil mismatch", table.Name, c.Name)
			}
			if wf.IsNil() {
				continue
			}
			wf, gf = wf.Elem(), gf.Elem()
		}
		if wf.Type() == prodTimeType {
			if !wf.Interface().(time.Time).Equal(gf.Interface().(time.Time)) {
				t.Fatalf("%s.%s: time %v, want %v", table.Name, c.Name, gf.Interface(), wf.Interface())
			}
			continue
		}
		if !reflect.DeepEqual(wf.Interface(), gf.Interface()) {
			t.Fatalf("%s.%s: %v, want %v", table.Name, c.Name, gf.Interface(), wf.Interface())
		}
	}
}

func prodJSONEqual(a, b []byte) bool {
	var x, y any
	if json.Unmarshal(a, &x) != nil || json.Unmarshal(b, &y) != nil {
		return string(a) == string(b)
	}
	return reflect.DeepEqual(x, y)
}

func prodPKIndex(table TableDef) int {
	for i, c := range table.Columns {
		if c.PrimaryKey {
			return i
		}
	}
	panic("table " + table.Name + " has no primary key")
}

// ---- generic SQL over the table metadata ---------------------------------------

func prodInsert(ctx context.Context, db *sql.DB, table TableDef, row reflect.Value) error {
	names := make([]string, len(table.Columns))
	holders := make([]string, len(table.Columns))
	args := make([]any, len(table.Columns))
	for i, c := range table.Columns {
		names[i] = `"` + c.Name + `"`
		holders[i] = fmt.Sprintf("$%d", i+1)
		args[i] = prodArg(row.Elem().Field(i))
	}
	q := fmt.Sprintf(`INSERT INTO "%s" (%s) VALUES (%s)`, table.Name, strings.Join(names, ", "), strings.Join(holders, ", "))
	_, err := db.ExecContext(ctx, q, args...)
	return err
}

func prodSelect(ctx context.Context, db *sql.DB, table TableDef, pk any) (reflect.Value, error) {
	names := make([]string, len(table.Columns))
	for i, c := range table.Columns {
		names[i] = `"` + c.Name + `"`
	}
	pkName := table.Columns[prodPKIndex(table)].Name
	q := fmt.Sprintf(`SELECT %s FROM "%s" WHERE "%s" = $1`, strings.Join(names, ", "), table.Name, pkName)
	row := reflect.New(prodModelTypes[table.Model])
	dest := make([]any, len(table.Columns))
	for i := range table.Columns {
		dest[i] = prodScanDest(row.Elem().Field(i))
	}
	if err := db.QueryRowContext(ctx, q, pk).Scan(dest...); err != nil {
		return reflect.Value{}, err
	}
	return row, nil
}

func prodUpdate(ctx context.Context, db *sql.DB, table TableDef, row reflect.Value) error {
	sets := make([]string, len(table.Columns))
	args := make([]any, 0, len(table.Columns)+1)
	for i, c := range table.Columns {
		sets[i] = fmt.Sprintf(`"%s" = $%d`, c.Name, i+1)
		args = append(args, prodArg(row.Elem().Field(i)))
	}
	pkIdx := prodPKIndex(table)
	args = append(args, prodArg(row.Elem().Field(pkIdx)))
	q := fmt.Sprintf(`UPDATE "%s" SET %s WHERE "%s" = $%d`, table.Name, strings.Join(sets, ", "), table.Columns[pkIdx].Name, len(table.Columns)+1)
	_, err := db.ExecContext(ctx, q, args...)
	return err
}

func prodDelete(ctx context.Context, db *sql.DB, table TableDef, pk any) error {
	pkName := table.Columns[prodPKIndex(table)].Name
	q := fmt.Sprintf(`DELETE FROM "%s" WHERE "%s" = $1`, table.Name, pkName)
	_, err := db.ExecContext(ctx, q, pk)
	return err
}

func prodArg(f reflect.Value) any {
	if f.Type() == prodRawMessageType {
		if f.IsNil() {
			return nil
		}
		return string(f.Bytes())
	}
	if f.Kind() == reflect.Ptr {
		if f.IsNil() {
			return nil
		}
		return f.Elem().Interface()
	}
	return f.Interface()
}

func prodScanDest(f reflect.Value) any {
	if f.Type() == prodRawMessageType {
		return (*[]byte)(f.Addr().UnsafePointer())
	}
	return f.Addr().Interface()
}

// prodEnsureUser makes the user_id foreign keys satisfiable on a production-like database where
// users exists but is empty. It is a no-op when there is no users table.
func prodEnsureUser(ctx context.Context, db *sql.DB, userID string) error {
	var exists bool
	if err := db.QueryRowContext(ctx, "SELECT to_regclass('public.users') IS NOT NULL").Scan(&exists); err != nil {
		return err
	}
	if !exists {
		return nil
	}
	_, err := db.ExecContext(ctx, `INSERT INTO users (id, email, username, password_hash, status, roles, email_verified, failed_login_attempts, refresh_token_version, created_at, updated_at, project_ids, metadata) VALUES ($1, $2, $3, $4, 'active', '[]', false, 0, 0, now(), now(), '[]', '{}') ON CONFLICT (id) DO NOTHING`,
		userID, userID+"@example.test", "prod_"+userID[:8], "unused")
	return err
}

// ---- fake database/sql driver --------------------------------------------------

// prodFakeDB is an in-memory driver for the exact statement shapes the helpers above emit: all
// columns in TableDef order, the primary key in the WHERE clause.
type prodFakeDB struct {
	mu    sync.Mutex
	store map[string]map[string][]driver.Value
}

func newProdFakeDB() *prodFakeDB {
	return &prodFakeDB{store: map[string]map[string][]driver.Value{}}
}

func (f *prodFakeDB) open() *sql.DB { return sql.OpenDB(prodFakeConnector{f}) }

type prodFakeConnector struct{ f *prodFakeDB }

func (c prodFakeConnector) Connect(context.Context) (driver.Conn, error) {
	return &prodFakeConn{c.f}, nil
}
func (c prodFakeConnector) Driver() driver.Driver { return nil }

type prodFakeConn struct{ f *prodFakeDB }

func (c *prodFakeConn) Prepare(q string) (driver.Stmt, error) { return &prodFakeStmt{c.f, q}, nil }
func (c *prodFakeConn) Close() error                          { return nil }
func (c *prodFakeConn) Begin() (driver.Tx, error)             { return prodFakeTx{}, nil }

type prodFakeTx struct{}

func (prodFakeTx) Commit() error   { return nil }
func (prodFakeTx) Rollback() error { return nil }

type prodFakeStmt struct {
	f *prodFakeDB
	q string
}

func (s *prodFakeStmt) Close() error  { return nil }
func (s *prodFakeStmt) NumInput() int { return -1 }

func (s *prodFakeStmt) Exec(args []driver.Value) (driver.Result, error) {
	op, table := prodParseSQL(s.q)
	td, ok := prodTableByName(table)
	if op == "" || !ok {
		return nil, fmt.Errorf("prodFake: unexpected exec %q", s.q)
	}
	pkIdx := prodPKIndex(td)
	s.f.mu.Lock()
	defer s.f.mu.Unlock()
	if s.f.store[table] == nil {
		s.f.store[table] = map[string][]driver.Value{}
	}
	switch op {
	case "insert":
		s.f.store[table][fmt.Sprint(args[pkIdx])] = prodCopy(args)
	case "update":
		key := fmt.Sprint(args[len(td.Columns)])
		s.f.store[table][key] = prodCopy(args[:len(td.Columns)])
	case "delete":
		delete(s.f.store[table], fmt.Sprint(args[0]))
	default:
		return nil, fmt.Errorf("prodFake: %s is not an exec", op)
	}
	return driver.RowsAffected(1), nil
}

func (s *prodFakeStmt) Query(args []driver.Value) (driver.Rows, error) {
	op, table := prodParseSQL(s.q)
	td, ok := prodTableByName(table)
	if op != "select" || !ok {
		return nil, fmt.Errorf("prodFake: unexpected query %q", s.q)
	}
	cols := make([]string, len(td.Columns))
	for i, c := range td.Columns {
		cols[i] = c.Name
	}
	s.f.mu.Lock()
	defer s.f.mu.Unlock()
	return &prodFakeRows{cols: cols, row: s.f.store[table][fmt.Sprint(args[0])]}, nil
}

func prodCopy(values []driver.Value) []driver.Value {
	out := make([]driver.Value, len(values))
	copy(out, values)
	return out
}

type prodFakeRows struct {
	cols []string
	row  []driver.Value
}

func (r *prodFakeRows) Columns() []string { return r.cols }
func (r *prodFakeRows) Close() error      { return nil }
func (r *prodFakeRows) Next(dest []driver.Value) error {
	if r.row == nil {
		return io.EOF
	}
	copy(dest, r.row)
	r.row = nil
	return nil
}

func prodTableByName(name string) (TableDef, bool) {
	for _, t := range ProductionTables {
		if t.Name == name {
			return t, true
		}
	}
	return TableDef{}, false
}

// prodParseSQL recognises the statement shapes emitted by the helpers above.
func prodParseSQL(q string) (op, table string) {
	switch {
	case strings.HasPrefix(q, `INSERT INTO "`):
		return "insert", prodQuotedAfter(q, len(`INSERT INTO "`))
	case strings.HasPrefix(q, "SELECT "):
		i := strings.Index(q, ` FROM "`)
		if i < 0 {
			return "", ""
		}
		return "select", prodQuotedAfter(q, i+len(` FROM "`))
	case strings.HasPrefix(q, `UPDATE "`):
		return "update", prodQuotedAfter(q, len(`UPDATE "`))
	case strings.HasPrefix(q, `DELETE FROM "`):
		return "delete", prodQuotedAfter(q, len(`DELETE FROM "`))
	}
	return "", ""
}

func prodQuotedAfter(q string, start int) string {
	end := strings.IndexByte(q[start:], '"')
	if end < 0 {
		return ""
	}
	return q[start : start+end]
}

// ---- misc helpers --------------------------------------------------------------

func prodUUID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

func prodRandHex(n int) string {
	b := make([]byte, (n+1)/2)
	_, _ = rand.Read(b)
	return fmt.Sprintf("%x", b)[:n]
}

func prodRandInt() int64 {
	var b [4]byte
	_, _ = rand.Read(b[:])
	return int64(b[0])<<24 | int64(b[1])<<16 | int64(b[2])<<8 | int64(b[3])
}
