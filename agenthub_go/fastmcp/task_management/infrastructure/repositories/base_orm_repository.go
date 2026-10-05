package repositories

// Base ORM Repository (Python repositories/base_orm_repository.py): generic CRUD over the
// generated table metadata (database.Tables), standing in for SQLAlchemy's Session/query API.
//
// M is a row struct from database/models.go; its `db:"column"` tags map columns to fields.
// kwargs/filters are keyed by the Python attribute name (the column name except for
// model_metadata -> "metadata"), in the order the caller supplies them.

import (
	"context"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// Kwargs are attribute values in caller order (Python **kwargs).
type Kwargs = *entities.OrderedMap[any]

// NewKwargs builds Kwargs from alternating attribute names and values.
func NewKwargs(kv ...any) Kwargs {
	k := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		k.Set(kv[i].(string), kv[i+1])
	}
	return k
}

// ORMRepository is BaseORMRepository[M].
type ORMRepository[M any] struct {
	Table    database.TableDef
	Sessions *database.SessionManager
	// Operation is the repository class name used in DatabaseException.operation.
	Operation string

	cols      []string       // select list (uuid columns cast to text)
	fieldIdx  []int          // struct field index per column
	byAttr    map[string]int // python attribute name -> column position
	pkAttr    string
	newRow    func() *M
	timestamp bool
}

// NewORMRepository builds the repository for the table named tableName.
func NewORMRepository[M any](tableName string, sessions *database.SessionManager) (*ORMRepository[M], error) {
	var table *database.TableDef
	for i := range database.Tables {
		if database.Tables[i].Name == tableName {
			table = &database.Tables[i]
		}
	}
	if table == nil {
		return nil, fmt.Errorf("unknown table %q", tableName)
	}
	typ := reflect.TypeOf((*M)(nil)).Elem()
	byTag := map[string]int{}
	for i := 0; i < typ.NumField(); i++ {
		if tag := typ.Field(i).Tag.Get("db"); tag != "" {
			byTag[tag] = i
		}
	}
	r := &ORMRepository[M]{Table: *table, Sessions: sessions, Operation: table.Model + "Repository", byAttr: map[string]int{}, newRow: func() *M { return new(M) }}
	for pos, c := range table.Columns {
		idx, ok := byTag[c.Name]
		if !ok {
			return nil, fmt.Errorf("%s has no field for column %s", typ.Name(), c.Name)
		}
		r.fieldIdx = append(r.fieldIdx, idx)
		r.byAttr[c.Attr] = pos
		if c.PrimaryKey && r.pkAttr == "" {
			r.pkAttr = c.Attr
		}
		expr := quoteIdent(c.Name)
		if c.SQLType == "UUID" {
			expr += "::text AS " + quoteIdent(c.Name)
		}
		r.cols = append(r.cols, expr)
	}
	_, r.timestamp = any(new(M)).(database.Timestamped)
	return r, nil
}

func quoteIdent(s string) string { return `"` + strings.ReplaceAll(s, `"`, `""`) + `"` }

// GetDBSession runs fn in a session, reusing the transaction on ctx, and converts database
// errors to DatabaseException like get_db_session.
func (r *ORMRepository[M]) GetDBSession(ctx context.Context, fn func(ctx context.Context, s database.DBTX) error) error {
	err := r.Sessions.WithSession(ctx, fn)
	if err != nil && database.IsSQLAlchemyError(err) {
		return exceptions.NewDatabaseException("Database operation failed: "+err.Error(), r.Operation, r.Table.Name)
	}
	return err
}

// Transaction runs fn with one transaction shared by every session started from its context.
func (r *ORMRepository[M]) Transaction(ctx context.Context, fn func(ctx context.Context) error) error {
	err := r.Sessions.Transaction(ctx, fn)
	if err != nil && database.IsSQLAlchemyError(err) {
		return exceptions.NewDatabaseException("Transaction failed: "+err.Error(), "transaction", r.Table.Name)
	}
	return err
}

// ---- value binding / scanning -------------------------------------------------

// bind converts a Go value to a statement argument for the column (SQLAlchemy bind processors).
func bind(c database.ColumnDef, v any) (any, error) {
	switch c.SQLType {
	case "UUID":
		// UnifiedUUID.process_bind_param: non-UUID strings become the deterministic uuid5;
		// bind failures surface as StatementError (a SQLAlchemyError).
		bv, err := database.UnifiedUUIDBindParam(v, database.DialectPostgres)
		if err != nil {
			return nil, &database.StatementError{Err: err}
		}
		return bv, nil
	case "JSON":
		switch x := v.(type) {
		case json.RawMessage:
			if x == nil {
				return "null", nil
			}
			return string(x), nil
		case []byte:
			return string(x), nil
		}
		return tmvo.PyJSONDumps(v, -1)
	}
	switch x := v.(type) {
	case time.Time:
		return x.UTC(), nil
	case *time.Time:
		if x == nil {
			return nil, nil
		}
		return x.UTC(), nil
	}
	return v, nil
}

// scanDest returns the scan destinations for every column of row.
func (r *ORMRepository[M]) scanDest(row *M) []any {
	v := reflect.ValueOf(row).Elem()
	dest := make([]any, len(r.fieldIdx))
	for i, idx := range r.fieldIdx {
		f := v.Field(idx)
		if f.Type() == reflect.TypeOf(json.RawMessage(nil)) {
			dest[i] = (*[]byte)(f.Addr().UnsafePointer())
		} else {
			dest[i] = f.Addr().Interface()
		}
	}
	return dest
}

func (r *ORMRepository[M]) selectList() string { return strings.Join(r.cols, ", ") }

// defaultFor produces the client-side default of a column (SQLAlchemy column default).
func defaultFor(c database.ColumnDef, now func() time.Time) (any, bool) {
	switch c.Default {
	case database.DefaultString:
		var s string
		_ = json.Unmarshal([]byte(c.DefaultValue), &s)
		return s, true
	case database.DefaultEnum:
		var s string
		_ = json.Unmarshal([]byte(c.DefaultValue), &s)
		return s, true
	case database.DefaultInt:
		var n int64
		fmt.Sscan(c.DefaultValue, &n)
		return n, true
	case database.DefaultFloat:
		var f float64
		fmt.Sscan(c.DefaultValue, &f)
		return f, true
	case database.DefaultBool:
		return c.DefaultValue == "true", true
	case database.DefaultEmptyList:
		return json.RawMessage("[]"), true
	case database.DefaultEmptyDict:
		return json.RawMessage("{}"), true
	case database.DefaultUUIDv4:
		return tmvo.NewUUIDv4(), true
	case database.DefaultNowUTC, database.DefaultNowUTCNaive:
		return now().UTC(), true
	}
	return nil, false
}

// Now is the clock used for client-side defaults (overridable in tests).
var Now = func() time.Time { return time.Now().UTC() }

// setField assigns a bound-independent Go value into the row struct field (for timestamp hooks
// and results that must reflect inserted values).
func (r *ORMRepository[M]) toColumnValues(kwargs Kwargs, forInsert bool) (map[int]any, error) {
	vals := map[int]any{}
	if kwargs == nil {
		return vals, nil
	}
	for _, attr := range kwargs.Keys() {
		pos, ok := r.byAttr[attr]
		if !ok {
			if forInsert {
				return nil, &tmvo.TypeError{Msg: fmt.Sprintf("%s is an invalid keyword argument for %s", tmvo.PyRepr(attr), r.Table.Model)}
			}
			continue
		}
		v, _ := kwargs.Get(attr)
		vals[pos] = v
	}
	return vals, nil
}

// ---- CRUD ----------------------------------------------------------------------

// Create inserts a record (create): None values fall back to column defaults, timestamps are
// managed by the timestamp events for mapped classes that define touch(), and the stored row
// (RETURNING) is returned.
func (r *ORMRepository[M]) Create(ctx context.Context, kwargs Kwargs) (*M, error) {
	var out *M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.insert(ctx, s, kwargs)
		out = row
		return err
	})
	return out, err
}

func (r *ORMRepository[M]) insert(ctx context.Context, s database.DBTX, kwargs Kwargs) (*M, error) {
	return r.insertWith(ctx, s, kwargs, true)
}

// insertWith inserts a row; convertIntegrity maps an integrity violation to DatabaseIntegrityException.
func (r *ORMRepository[M]) insertWith(ctx context.Context, s database.DBTX, kwargs Kwargs, convertIntegrity bool) (*M, error) {
	vals, err := r.toColumnValues(kwargs, true)
	if err != nil {
		return nil, err
	}
	// before_insert timestamp handler (only for classes with touch()).
	if r.timestamp && database.TimestampEventsActive() {
		probe := r.newRow()
		ts := any(probe).(database.Timestamped)
		for i, c := range r.Table.Columns {
			if v, ok := vals[i]; ok && v != nil {
				switch c.Name {
				case "created_at":
					if t := asTime(v); t != nil {
						ts.SetCreatedAt(t)
					}
				case "updated_at":
					if t := asTime(v); t != nil {
						ts.SetUpdatedAt(t)
					}
				}
			}
		}
		database.BeforeInsertTimestamps(probe)
		for i, c := range r.Table.Columns {
			switch c.Name {
			case "created_at":
				if t := ts.GetCreatedAt(); t != nil {
					vals[i] = *t
				}
			case "updated_at":
				if t := ts.GetUpdatedAt(); t != nil {
					vals[i] = *t
				}
			}
		}
	}
	var names []string
	var holders []string
	var args []any
	for i, c := range r.Table.Columns {
		v, provided := vals[i]
		// ORM INSERT omits None attributes (so defaults apply) except JSON columns, which store JSON null.
		if !provided || (v == nil && c.SQLType != "JSON") {
			dv, ok := defaultFor(c, Now)
			if !ok {
				continue
			}
			v = dv
		}
		bv, err := bind(c, v)
		if err != nil {
			return nil, err
		}
		args = append(args, bv)
		names = append(names, quoteIdent(c.Name))
		holders = append(holders, fmt.Sprintf("$%d", len(args)))
	}
	q := fmt.Sprintf("INSERT INTO %s (%s) VALUES (%s) RETURNING %s", quoteIdent(r.Table.Name), strings.Join(names, ", "), strings.Join(holders, ", "), r.selectList())
	if len(names) == 0 {
		q = fmt.Sprintf("INSERT INTO %s DEFAULT VALUES RETURNING %s", quoteIdent(r.Table.Name), r.selectList())
	}
	row := r.newRow()
	if err := s.QueryRowContext(ctx, q, args...).Scan(r.scanDest(row)...); err != nil {
		if convertIntegrity && database.IsIntegrityError(err) {
			return nil, exceptions.NewDatabaseIntegrityException("Database integrity constraint violation: "+err.Error(), extractConstraintName(err.Error()))
		}
		return nil, err
	}
	return row, nil
}

func asTime(v any) *time.Time {
	switch t := v.(type) {
	case time.Time:
		return &t
	case *time.Time:
		return t
	}
	return nil
}

// ExtractConstraintName is _extract_constraint_name.
func (r *ORMRepository[M]) ExtractConstraintName(msg string) string {
	return extractConstraintName(msg)
}

func extractConstraintName(msg string) string {
	patterns := []struct {
		pattern string
		hasName bool
	}{
		{"UNIQUE constraint failed: ", true},
		{"NOT NULL constraint failed: ", true},
		{"CHECK constraint failed: ", true},
		{"FOREIGN KEY constraint failed", false},
	}
	for _, p := range patterns {
		if strings.Contains(msg, p.pattern) {
			if !p.hasName {
				return ""
			}
			parts := strings.Split(msg, p.pattern)
			if len(parts) > 1 {
				fields := strings.Fields(parts[1])
				if len(fields) == 0 {
					return ""
				}
				return strings.TrimSpace(fields[0])
			}
		}
	}
	return ""
}

// where builds "col = $n AND ..." for filters (unknown attributes are ignored; None becomes IS NULL).
func (r *ORMRepository[M]) where(filters Kwargs, argStart int) (string, []any, error) {
	var conds []string
	var args []any
	if filters != nil {
		for _, attr := range filters.Keys() {
			pos, ok := r.byAttr[attr]
			if !ok {
				continue
			}
			c := r.Table.Columns[pos]
			v, _ := filters.Get(attr)
			if v == nil {
				conds = append(conds, quoteIdent(c.Name)+" IS NULL")
				continue
			}
			bv, err := bind(c, v)
			if err != nil {
				return "", nil, err
			}
			args = append(args, bv)
			conds = append(conds, fmt.Sprintf("%s = $%d", quoteIdent(c.Name), argStart+len(args)-1))
		}
	}
	if len(conds) == 0 {
		return "", nil, nil
	}
	return " WHERE " + strings.Join(conds, " AND "), args, nil
}

func (r *ORMRepository[M]) selectRows(ctx context.Context, s database.DBTX, suffix string, args ...any) ([]*M, error) {
	rows, err := s.QueryContext(ctx, fmt.Sprintf("SELECT %s FROM %s%s", r.selectList(), quoteIdent(r.Table.Name), suffix), args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []*M
	for rows.Next() {
		row := r.newRow()
		if err := rows.Scan(r.scanDest(row)...); err != nil {
			return nil, err
		}
		out = append(out, row)
	}
	return out, rows.Err()
}

func (r *ORMRepository[M]) pkColumn() string {
	return quoteIdent(r.Table.Columns[r.byAttr[r.pkAttr]].Name)
}

// GetByID returns the record with the primary key, or nil.
func (r *ORMRepository[M]) GetByID(ctx context.Context, id any) (*M, error) {
	var out *M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := r.getByID(ctx, s, id)
		out = row
		return err
	})
	return out, err
}

func (r *ORMRepository[M]) getByID(ctx context.Context, s database.DBTX, id any) (*M, error) {
	pk := r.Table.Columns[r.byAttr[r.pkAttr]]
	bv, err := bind(pk, id)
	if err != nil {
		return nil, err
	}
	rows, err := r.selectRows(ctx, s, " WHERE "+r.pkColumn()+" = $1 LIMIT 1", bv)
	if err != nil || len(rows) == 0 {
		return nil, err
	}
	return rows[0], nil
}

// GetAll returns all records; offset then limit are applied when truthy (non-zero).
func (r *ORMRepository[M]) GetAll(ctx context.Context, limit, offset *int) ([]*M, error) {
	var out []*M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		suffix := ""
		if offset != nil && *offset != 0 {
			suffix += fmt.Sprintf(" OFFSET %d", *offset)
		}
		if limit != nil && *limit != 0 {
			suffix = fmt.Sprintf(" LIMIT %d", *limit) + suffix
		}
		rows, err := r.selectRows(ctx, s, suffix)
		out = rows
		return err
	})
	return out, err
}

// Update sets the given attributes on the record and returns the refreshed row, or nil when absent.
func (r *ORMRepository[M]) Update(ctx context.Context, id any, kwargs Kwargs) (*M, error) {
	var out *M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		cur, err := r.getByID(ctx, s, id)
		if err != nil || cur == nil {
			return err
		}
		vals, _ := r.toColumnValues(kwargs, false)
		changed := map[int]any{}
		curV := reflect.ValueOf(cur).Elem()
		for pos, v := range vals {
			c := r.Table.Columns[pos]
			if !valuesEqual(c, curV.Field(r.fieldIdx[pos]).Interface(), v) {
				changed[pos] = v
			}
		}
		// before_update fires for any assigned known attribute, even when the value is unchanged.
		if len(vals) > 0 && r.timestamp && database.TimestampEventsActive() {
			now := database.TimestampNow()
			for pos, c := range r.Table.Columns {
				if c.Name == "updated_at" {
					changed[pos] = now
				}
			}
		}
		if len(changed) == 0 {
			out = cur
			return nil
		}
		var sets []string
		var args []any
		for pos := range r.Table.Columns { // declaration order
			v, ok := changed[pos]
			if !ok {
				continue
			}
			c := r.Table.Columns[pos]
			var bv any
			if v != nil || c.SQLType == "JSON" {
				if bv, err = bind(c, v); err != nil {
					return err
				}
			}
			args = append(args, bv)
			sets = append(sets, fmt.Sprintf("%s = $%d", quoteIdent(c.Name), len(args)))
		}
		pk := r.Table.Columns[r.byAttr[r.pkAttr]]
		pkv, err := bind(pk, id)
		if err != nil {
			return err
		}
		args = append(args, pkv)
		q := fmt.Sprintf("UPDATE %s SET %s WHERE %s = $%d RETURNING %s", quoteIdent(r.Table.Name), strings.Join(sets, ", "), r.pkColumn(), len(args), r.selectList())
		row := r.newRow()
		if err := s.QueryRowContext(ctx, q, args...).Scan(r.scanDest(row)...); err != nil {
			return err
		}
		out = row
		return nil
	})
	return out, err
}

// valuesEqual compares the stored field value with a new attribute value like SQLAlchemy's
// attribute history (==), treating JSON documents structurally.
func valuesEqual(c database.ColumnDef, stored, next any) bool {
	if c.SQLType == "JSON" {
		a, aerr := tmvo.PyJSONDumps(jsonValue(stored), -1)
		b, berr := tmvo.PyJSONDumps(jsonValue(next), -1)
		return aerr == nil && berr == nil && a == b
	}
	return reflect.DeepEqual(normalizeScalar(stored), normalizeScalar(next))
}

// normalizeScalar dereferences pointers and widens integers so equal values compare equal;
// times compare by instant.
func normalizeScalar(v any) any {
	rv := reflect.ValueOf(v)
	for rv.IsValid() && rv.Kind() == reflect.Ptr {
		if rv.IsNil() {
			return nil
		}
		rv = rv.Elem()
	}
	if !rv.IsValid() {
		return nil
	}
	switch rv.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return rv.Int()
	case reflect.Float32, reflect.Float64:
		return rv.Float()
	}
	if t, ok := rv.Interface().(time.Time); ok {
		return t.UTC().UnixNano()
	}
	return rv.Interface()
}

func jsonValue(v any) any {
	if raw, ok := v.(json.RawMessage); ok {
		if raw == nil {
			return nil
		}
		d, err := entities.DecodeJSON(raw)
		if err != nil {
			return string(raw)
		}
		return d
	}
	return v
}

// Delete removes the record by ID and reports whether it existed.
func (r *ORMRepository[M]) Delete(ctx context.Context, id any) (bool, error) {
	deleted := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		pk := r.Table.Columns[r.byAttr[r.pkAttr]]
		bv, err := bind(pk, id)
		if err != nil {
			return err
		}
		res, err := s.ExecContext(ctx, fmt.Sprintf("DELETE FROM %s WHERE %s = $1", quoteIdent(r.Table.Name), r.pkColumn()), bv)
		if err != nil {
			return err
		}
		n, _ := res.RowsAffected()
		deleted = n > 0
		return nil
	})
	return deleted, err
}

// Exists reports whether any record matches the filters.
func (r *ORMRepository[M]) Exists(ctx context.Context, filters Kwargs) (bool, error) {
	rows, err := r.FindBy(ctx, filters)
	return len(rows) > 0, err
}

// Count counts the records matching the filters.
func (r *ORMRepository[M]) Count(ctx context.Context, filters Kwargs) (int, error) {
	n := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		return s.QueryRowContext(ctx, fmt.Sprintf("SELECT count(*) FROM %s%s", quoteIdent(r.Table.Name), w), args...).Scan(&n)
	})
	return n, err
}

// FindBy returns the records matching the filters.
func (r *ORMRepository[M]) FindBy(ctx context.Context, filters Kwargs) ([]*M, error) {
	var out []*M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w, args...)
		out = rows
		return err
	})
	return out, err
}

// FindOneBy returns the first record matching the filters, or nil.
func (r *ORMRepository[M]) FindOneBy(ctx context.Context, filters Kwargs) (*M, error) {
	var out *M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		w, args, err := r.where(filters, 1)
		if err != nil {
			return err
		}
		rows, err := r.selectRows(ctx, s, w+" LIMIT 1", args...)
		if len(rows) > 0 {
			out = rows[0]
		}
		return err
	})
	return out, err
}

// BulkCreate inserts several records in one session.
func (r *ORMRepository[M]) BulkCreate(ctx context.Context, records []Kwargs) ([]*M, error) {
	var out []*M
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		for _, rec := range records {
			row, err := r.insertWith(ctx, s, rec, false) // only create() converts IntegrityError
			if err != nil {
				return err
			}
			out = append(out, row)
		}
		return nil
	})
	return out, err
}

// ExecuteQuery runs a custom query function in a managed session.
func (r *ORMRepository[M]) ExecuteQuery(ctx context.Context, fn func(ctx context.Context, s database.DBTX) error) error {
	return r.GetDBSession(ctx, fn)
}
