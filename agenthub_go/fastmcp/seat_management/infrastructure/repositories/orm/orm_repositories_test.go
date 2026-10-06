package orm

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/jackc/pgx/v5/pgconn"
	"io"
	"reflect"
	"strings"
	"sync"
	"testing"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// fakeDriver is a scripted database/sql driver: it records every prepared statement and
// answers queries through respond. SELECT 1 (the connection check) is answered by Exec.
type fakeDriver struct {
	mu      sync.Mutex
	queries []string
	respond func(q string, args []driver.Value) (cols []string, rows [][]driver.Value, err error)
	execErr func(q string) error
}

func (f *fakeDriver) record(q string) {
	f.mu.Lock()
	f.queries = append(f.queries, q)
	f.mu.Unlock()
}

func (f *fakeDriver) recorded() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.queries...)
}

func (f *fakeDriver) open() *sql.DB { return sql.OpenDB(fakeConnector{f}) }

type fakeConnector struct{ f *fakeDriver }

func (c fakeConnector) Connect(context.Context) (driver.Conn, error) { return &fakeConn{f: c.f}, nil }
func (c fakeConnector) Driver() driver.Driver                        { return nil }

type fakeConn struct{ f *fakeDriver }

func (c *fakeConn) Prepare(q string) (driver.Stmt, error) { return &fakeStmt{f: c.f, q: q}, nil }
func (c *fakeConn) Close() error                          { return nil }
func (c *fakeConn) Begin() (driver.Tx, error)             { return fakeTx{}, nil }

type fakeTx struct{}

func (fakeTx) Commit() error   { return nil }
func (fakeTx) Rollback() error { return nil }

type fakeStmt struct {
	f *fakeDriver
	q string
}

func (s *fakeStmt) Close() error  { return nil }
func (s *fakeStmt) NumInput() int { return -1 }

func (s *fakeStmt) Exec([]driver.Value) (driver.Result, error) {
	s.f.record(s.q)
	if s.f.execErr != nil {
		if err := s.f.execErr(s.q); err != nil {
			return nil, err
		}
	}
	return driver.RowsAffected(1), nil
}

func (s *fakeStmt) Query(args []driver.Value) (driver.Rows, error) {
	s.f.record(s.q)
	if s.f.respond == nil {
		return &fakeRows{}, nil
	}
	cols, rows, err := s.f.respond(s.q, args)
	if err != nil {
		return nil, err
	}
	return &fakeRows{cols: cols, rows: rows}, nil
}

type fakeRows struct {
	cols []string
	rows [][]driver.Value
	i    int
}

func (r *fakeRows) Columns() []string { return r.cols }
func (r *fakeRows) Close() error      { return nil }
func (r *fakeRows) Next(dest []driver.Value) error {
	if r.i >= len(r.rows) {
		return io.EOF
	}
	copy(dest, r.rows[r.i])
	r.i++
	return nil
}

func newFakeManager(t *testing.T, f *fakeDriver) *database.SessionManager {
	t.Helper()
	db := f.open()
	t.Cleanup(func() { _ = db.Close() })
	return database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
}

func fakeRow(values ...any) []driver.Value {
	out := make([]driver.Value, len(values))
	for i, v := range values {
		out[i] = v
	}
	return out
}

const (
	testUser       = "user-1"
	testOtherUser  = "user-2"
	testModuleID   = "11111111-1111-4111-8111-111111111111"
	testVersionID  = "44444444-4444-4444-8444-444444444444"
	testSeatTypeID = "33333333-3333-4333-8333-333333333333"
	testSeatID     = "22222222-2222-4222-8222-222222222222"
	testRoomID     = "55555555-5555-4555-8555-555555555555"
)

var (
	moduleCols              = []string{"id", "user_id", "slug", "kind", "created_at"}
	moduleVersionCols       = []string{"id", "user_id", "module_id", "version", "content", "checksum", "created_at"}
	moduleJoinCols          = []string{"id", "user_id", "module_id", "version", "content", "checksum", "created_at", "slug", "kind"}
	seatTypeVersionJoinCols = []string{"id", "user_id", "seat_type_id", "version", "default_runtime", "module_refs", "created_at", "slug"}
	overlayCols             = []string{"id", "user_id", "scope", "room_id", "seat_id", "ops", "created_at", "updated_at"}
)

func TestModuleAddVersionImmutable(t *testing.T) {
	ctx := context.Background()
	content := "hello"
	checksum := moduleVersionChecksum(content)
	now := time.Now().UTC()
	moduleRow := fakeRow(testModuleID, testUser, "instr", "instruction", now)

	env := func(existingChecksum string) (*ORMModuleRepository, *fakeDriver) {
		f := &fakeDriver{}
		f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
			switch {
			case strings.Contains(q, `FROM "modules"`):
				return moduleCols, [][]driver.Value{moduleRow}, nil
			case strings.Contains(q, `FROM "module_versions"`):
				return moduleVersionCols, [][]driver.Value{
					fakeRow(testVersionID, testUser, testModuleID, "1.0.0", content, existingChecksum, now),
				}, nil
			}
			return nil, nil, nil
		}
		repo, err := NewORMModuleRepository(newFakeManager(t, f))
		if err != nil {
			t.Fatalf("NewORMModuleRepository: %v", err)
		}
		return repo, f
	}

	repo, f := env(checksum)
	got, err := repo.AddVersion(ctx, testUser, "instr", "1.0.0", content)
	if err != nil {
		t.Fatalf("AddVersion(same checksum) = %v", err)
	}
	if got == nil || got.Checksum != checksum || got.Slug != "instr" {
		t.Fatalf("AddVersion = %+v", got)
	}
	assertNoStatement(t, f, `INSERT INTO "module_versions"`)

	repo, f = env(moduleVersionChecksum("other"))
	if _, err := repo.AddVersion(ctx, testUser, "instr", "1.0.0", content); err == nil || !strings.Contains(err.Error(), "different checksum") {
		t.Fatalf("AddVersion(different checksum) = %v, want a different-checksum error", err)
	}
	assertNoStatement(t, f, `INSERT INTO "module_versions"`)
}

func TestModuleSaveModuleGetOrCreate(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `INSERT INTO "modules"`):
			return moduleCols, [][]driver.Value{fakeRow(testModuleID, testUser, "instr", "instruction", now)}, nil
		case strings.Contains(q, `FROM "modules"`):
			return moduleCols, nil, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMModuleRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	got, err := repo.SaveModule(ctx, testUser, "instr", resolver.KindInstruction)
	if err != nil {
		t.Fatalf("SaveModule: %v", err)
	}
	if got.Slug != "instr" || got.Kind != resolver.KindInstruction {
		t.Fatalf("SaveModule = %+v", got)
	}

	f2 := &fakeDriver{}
	f2.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "modules"`) {
			return moduleCols, [][]driver.Value{fakeRow(testModuleID, testUser, "instr", "instruction", now)}, nil
		}
		return nil, nil, nil
	}
	repo2, _ := NewORMModuleRepository(newFakeManager(t, f2))
	again, err := repo2.SaveModule(ctx, testUser, "instr", resolver.KindInstruction)
	if err != nil || again == nil {
		t.Fatalf("SaveModule(existing) = %+v, %v", again, err)
	}
	assertNoStatement(t, f2, `INSERT INTO "modules"`)

	if _, err := repo2.SaveModule(ctx, testUser, "instr", resolver.KindDocument); err == nil {
		t.Fatal("SaveModule with a different kind must fail")
	}
}

func TestTenantScoping(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `INSERT INTO "modules"`):
			return moduleCols, [][]driver.Value{fakeRow(testModuleID, testUser, "instr", "instruction", now)}, nil
		case strings.Contains(q, `FROM "modules"`):
			return moduleCols, nil, nil
		case strings.Contains(q, "FROM module_versions AS mv"):
			return moduleJoinCols, nil, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMModuleRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.SaveModule(ctx, testUser, "instr", resolver.KindInstruction); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetVersion(ctx, testUser, "instr", "1.0.0"); err != nil {
		t.Fatal(err)
	}

	sawModule, sawJoin := false, false
	for _, q := range f.recorded() {
		if strings.Contains(q, `FROM "modules"`) {
			sawModule = true
			if !strings.Contains(q, `"user_id" = $1`) {
				t.Errorf("modules query not tenant-scoped: %s", q)
			}
		}
		if strings.Contains(q, "FROM module_versions AS mv") {
			sawJoin = true
			if !strings.Contains(q, `mv."user_id" = $1`) {
				t.Errorf("module join query not tenant-scoped: %s", q)
			}
		}
	}
	if !sawModule || !sawJoin {
		t.Fatalf("expected tenant-scoped queries, sawModule=%v sawJoin=%v", sawModule, sawJoin)
	}
}

func TestDBCatalogGet(t *testing.T) {
	now := time.Now().UTC()
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, "FROM module_versions AS mv") {
			return moduleJoinCols, [][]driver.Value{
				fakeRow("a", testUser, testModuleID, "2.0.0", "newest", moduleVersionChecksum("newest"), now, "instr", "instruction"),
				fakeRow("b", testUser, testModuleID, "1.0.0", "older", moduleVersionChecksum("older"), now.Add(-time.Hour), "instr", "instruction"),
			}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMModuleRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}

	catalog := NewDBCatalog(repo, testUser)
	mv, ok := catalog.Get("instr", "2.0.0")
	if !ok || mv.Version != "2.0.0" || mv.Kind != resolver.KindInstruction || mv.Content != "newest" {
		t.Fatalf("Get = %+v, %v", mv, ok)
	}
	if err := catalog.Err(); err != nil {
		t.Fatalf("Err = %v", err)
	}
}

func TestErrorsAreNotSwallowed(t *testing.T) {
	ctx := context.Background()
	boom := errors.New("db boom")

	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "modules"`) || strings.Contains(q, "FROM module_versions AS mv") {
			return nil, nil, boom
		}
		return nil, nil, nil
	}
	repo, err := NewORMModuleRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.SaveModule(ctx, testUser, "instr", resolver.KindInstruction); err == nil {
		t.Fatal("SaveModule swallowed the database error")
	}
	if _, err := repo.GetVersion(ctx, testUser, "instr", "1.0.0"); err == nil {
		t.Fatal("GetVersion swallowed the database error")
	}

	// A conversion error must surface, not be reported as not found.
	bad := &fakeDriver{}
	bad.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, "FROM seat_type_versions AS stv") {
			return seatTypeVersionJoinCols, [][]driver.Value{
				fakeRow("v", testUser, testSeatTypeID, "1.0.0", "go1.23", []byte("{not json"), time.Now().UTC(), "seat.standard"),
			}, nil
		}
		return nil, nil, nil
	}
	seatTypes, err := NewORMSeatTypeRepository(newFakeManager(t, bad))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := seatTypes.GetVersion(ctx, testUser, "seat.standard", "1.0.0"); err == nil {
		t.Fatal("GetVersion swallowed a conversion error")
	}
}

func TestSeatTypeAddVersionImmutable(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	refs := []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	encoded, err := encodeModuleRefs(refs)
	if err != nil {
		t.Fatal(err)
	}
	seatTypeRow := fakeRow(testSeatTypeID, testUser, "seat.standard", "Standard", "desc", now)

	env := func(stored json.RawMessage) (*ORMSeatTypeRepository, *fakeDriver) {
		f := &fakeDriver{}
		f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
			switch {
			case strings.Contains(q, `FROM "seat_types"`):
				return []string{"id", "user_id", "slug", "name", "description", "created_at"}, [][]driver.Value{seatTypeRow}, nil
			case strings.Contains(q, `FROM "seat_type_versions"`):
				return []string{"id", "user_id", "seat_type_id", "version", "default_runtime", "module_refs", "created_at"}, [][]driver.Value{
					fakeRow("v", testUser, testSeatTypeID, "1.0.0", "go1.23", []byte(stored), now),
				}, nil
			}
			return nil, nil, nil
		}
		repo, err := NewORMSeatTypeRepository(newFakeManager(t, f))
		if err != nil {
			t.Fatal(err)
		}
		return repo, f
	}

	repo, f := env(encoded)
	got, err := repo.AddVersion(ctx, testUser, "seat.standard", "1.0.0", "go1.23", refs)
	if err != nil {
		t.Fatalf("AddVersion(same refs) = %v", err)
	}
	if got == nil || len(got.ModuleRefs) != 1 || got.ModuleRefs[0].Slug != "instr" || got.DefaultRuntime != "go1.23" {
		t.Fatalf("AddVersion = %+v", got)
	}
	assertNoStatement(t, f, `INSERT INTO "seat_type_versions"`)

	different := json.RawMessage(`[{"slug":"other","version":"2.0.0"}]`)
	repo, f = env(different)
	if _, err := repo.AddVersion(ctx, testUser, "seat.standard", "1.0.0", "go1.23", refs); !errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) {
		t.Fatalf("AddVersion(different refs) = %v, want ErrSeatTypeVersionConflict", err)
	}
	assertNoStatement(t, f, `INSERT INTO "seat_type_versions"`)

	repo, f = env(encoded)
	if _, err := repo.AddVersion(ctx, testUser, "seat.standard", "1.0.0", "codex", refs); !errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) {
		t.Fatalf("AddVersion(different runtime) = %v, want ErrSeatTypeVersionConflict", err)
	}
	assertNoStatement(t, f, `INSERT INTO "seat_type_versions"`)
}

// A writer that loses the race for the next version gets a unique violation on insert. Its
// result must be decided by the winner's row, not reported as an internal error.
func TestSeatTypeAddVersionLostRace(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	refs := []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	encoded, err := encodeModuleRefs(refs)
	if err != nil {
		t.Fatal(err)
	}
	winner := func(runtime string, stored []byte) (*ORMSeatTypeRepository, *fakeDriver) {
		f := &fakeDriver{}
		versionReads := 0
		f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
			if strings.Contains(q, `"seat_type_versions"`) {
				// every statement on the versions table, the re-read included, is scoped to the user
				// and to this seat type
				joined := fmt.Sprint(args)
				if !strings.Contains(joined, testUser) || !strings.Contains(joined, testSeatTypeID) {
					t.Errorf("unscoped statement %q with args %v", q, args)
				}
			}
			switch {
			case strings.Contains(q, `FROM "seat_types"`):
				return []string{"id", "user_id", "slug", "name", "description", "created_at"}, [][]driver.Value{
					fakeRow(testSeatTypeID, testUser, "seat.standard", "Standard", "desc", now),
				}, nil
			case strings.Contains(q, `INSERT INTO "seat_type_versions"`):
				return nil, nil, &pgconn.PgError{Code: "23505", Message: "duplicate key value violates unique constraint"}
			case strings.Contains(q, `FROM "seat_type_versions"`):
				versionReads++
				if versionReads == 1 {
					return []string{"id", "user_id", "seat_type_id", "version", "default_runtime", "module_refs", "created_at"}, nil, nil
				}
				return []string{"id", "user_id", "seat_type_id", "version", "default_runtime", "module_refs", "created_at"}, [][]driver.Value{
					fakeRow("v", testUser, testSeatTypeID, "1.0.1", runtime, stored, now),
				}, nil
			}
			return nil, nil, nil
		}
		repo, err := NewORMSeatTypeRepository(newFakeManager(t, f))
		if err != nil {
			t.Fatal(err)
		}
		return repo, f
	}

	repo, _ := winner("go1.23", []byte(encoded))
	got, err := repo.AddVersion(ctx, testUser, "seat.standard", "1.0.1", "go1.23", refs)
	if err != nil || got == nil || got.Version != "1.0.1" {
		t.Fatalf("lost race with identical content = %+v, %v, want the winner's row", got, err)
	}

	repo, _ = winner("codex", []byte(encoded))
	if _, err := repo.AddVersion(ctx, testUser, "seat.standard", "1.0.1", "go1.23", refs); !errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) {
		t.Fatalf("lost race with another runtime = %v, want ErrSeatTypeVersionConflict", err)
	}
	repo, _ = winner("go1.23", []byte(`[{"slug":"other","version":"2.0.0"}]`))
	if _, err := repo.AddVersion(ctx, testUser, "seat.standard", "1.0.1", "go1.23", refs); !errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) {
		t.Fatalf("lost race with other refs = %v, want ErrSeatTypeVersionConflict", err)
	}
}

// Only a unique violation means "someone else took the version"; any other integrity error
// is returned as it is, and a failing re-read is not hidden behind the original error.
func TestSeatTypeAddVersionOnlyReReadsAfterUniqueViolation(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	refs := []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	versionCols := []string{"id", "user_id", "seat_type_id", "version", "default_runtime", "module_refs", "created_at"}
	run := func(insertErr, rereadErr error) (error, int) {
		f := &fakeDriver{}
		reads := 0
		f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
			switch {
			case strings.Contains(q, `FROM "seat_types"`):
				return []string{"id", "user_id", "slug", "name", "description", "created_at"}, [][]driver.Value{
					fakeRow(testSeatTypeID, testUser, "seat.standard", "Standard", "desc", now),
				}, nil
			case strings.Contains(q, `INSERT INTO "seat_type_versions"`):
				return nil, nil, insertErr
			case strings.Contains(q, `FROM "seat_type_versions"`):
				reads++
				if reads == 1 {
					return versionCols, nil, nil
				}
				return nil, nil, rereadErr
			}
			return nil, nil, nil
		}
		repo, err := NewORMSeatTypeRepository(newFakeManager(t, f))
		if err != nil {
			t.Fatal(err)
		}
		_, err = repo.AddVersion(ctx, testUser, "seat.standard", "1.0.1", "go1.23", refs)
		return err, reads
	}

	// a foreign key violation (SQLSTATE 23503) is not a lost race: no re-read
	if err, reads := run(&pgconn.PgError{Code: "23503", Message: "violates foreign key constraint"}, nil); err == nil || errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) || reads != 1 {
		t.Errorf("foreign key violation: err = %v, reads = %d, want the original error after one read", err, reads)
	}
	// a failing re-read is reported, not replaced by the integrity error
	boom := errors.New("re-read boom")
	if err, _ := run(&pgconn.PgError{Code: "23505", Message: "duplicate key"}, &pgconn.PgError{Code: "08006", Message: boom.Error()}); err == nil || !strings.Contains(err.Error(), "re-read") || !strings.Contains(err.Error(), boom.Error()) {
		t.Errorf("re-read failure: err = %v, want it to name the re-read and its cause", err)
	}
}

func TestResolvedSeatSaveLostRace(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	resolvedCols := []string{"id", "user_id", "seat_id", "hash", "runtime", "files", "policy", "created_at"}
	seat := domainrepo.ResolvedSeat{SeatID: testSeatID, Hash: "h1", Runtime: "omp"}
	winnerRow := fakeRow("66666666-6666-4666-8666-666666666666", testUser, testSeatID, "h1", "omp", []byte("[]"), []byte("{}"), now)

	newRepo := func(insertErr error, reads *int, rereadErr error) *ORMResolvedSeatRepository {
		f := &fakeDriver{}
		f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
			switch {
			case strings.Contains(q, `INSERT INTO "resolved_seats"`):
				return nil, nil, insertErr
			case strings.Contains(q, `FROM "resolved_seats"`):
				*reads++
				if *reads == 1 {
					return resolvedCols, nil, nil
				}
				if rereadErr != nil {
					return nil, nil, rereadErr
				}
				return resolvedCols, [][]driver.Value{winnerRow}, nil
			}
			return nil, nil, nil
		}
		repo, err := NewORMResolvedSeatRepository(newFakeManager(t, f))
		if err != nil {
			t.Fatal(err)
		}
		return repo
	}

	// The concurrent writer won the insert: its row is returned, with one re-read.
	reads := 0
	got, err := newRepo(&pgconn.PgError{Code: "23505", Message: "duplicate key value violates unique constraint"}, &reads, nil).Save(ctx, testUser, seat)
	if err != nil || got == nil || got.Hash != "h1" || got.ID != "66666666-6666-4666-8666-666666666666" {
		t.Fatalf("lost race = %+v, %v, want the winner's row", got, err)
	}
	if reads != 2 {
		t.Errorf("reads = %d, want the first read and one re-read", reads)
	}

	// Any other insert error is returned and nothing is re-read.
	reads = 0
	if _, err := newRepo(&pgconn.PgError{Code: "23503", Message: "foreign key violation"}, &reads, nil).Save(ctx, testUser, seat); err == nil {
		t.Fatal("a non-unique insert error was swallowed")
	}
	if reads != 1 {
		t.Errorf("reads = %d, want only the first read after a non-unique error", reads)
	}

	// A failing re-read is reported, not hidden behind the unique violation.
	reads = 0
	_, err = newRepo(&pgconn.PgError{Code: "23505", Message: "duplicate key value violates unique constraint"}, &reads, errors.New("reread boom")).Save(ctx, testUser, seat)
	if err == nil || !strings.Contains(err.Error(), "reread boom") {
		t.Fatalf("failing re-read = %v, want it reported", err)
	}
}

func TestOverlayUpsertScoped(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	ops, err := encodeOps([]resolver.Op{{Kind: resolver.OpAdd, Slug: "instr", Version: "1.0.0"}})
	if err != nil {
		t.Fatal(err)
	}

	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `UPDATE "overlays"`):
			return overlayCols, [][]driver.Value{fakeRow("o1", testUser, "company", nil, nil, []byte(ops), now, now.Add(time.Minute))}, nil
		case strings.Contains(q, `INSERT INTO "overlays"`):
			return overlayCols, [][]driver.Value{fakeRow("o2", testUser, "company", nil, nil, []byte(ops), now, now)}, nil
		case strings.Contains(q, `FROM "overlays"`):
			return overlayCols, nil, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMOverlayRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	created, err := repo.Upsert(ctx, testUser, domainrepo.Overlay{Scope: domainrepo.ScopeCompany, Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "instr", Version: "1.0.0"}}})
	if err != nil {
		t.Fatalf("Upsert(create): %v", err)
	}
	if created == nil || created.Scope != domainrepo.ScopeCompany || len(created.Ops) != 1 {
		t.Fatalf("Upsert(create) = %+v", created)
	}

	// Existing target: the update must stay inside the tenant.
	f2 := &fakeDriver{}
	f2.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `UPDATE "overlays"`):
			return overlayCols, [][]driver.Value{fakeRow("o1", testUser, "company", nil, nil, []byte(ops), now, now.Add(time.Minute))}, nil
		case strings.Contains(q, `FROM "overlays"`):
			return overlayCols, [][]driver.Value{fakeRow("o1", testUser, "company", nil, nil, []byte("[]"), now, now)}, nil
		}
		return nil, nil, nil
	}
	repo2, _ := NewORMOverlayRepository(newFakeManager(t, f2))
	if _, err := repo2.Upsert(ctx, testUser, domainrepo.Overlay{Scope: domainrepo.ScopeCompany, Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "instr", Version: "1.0.0"}}}); err != nil {
		t.Fatalf("Upsert(update): %v", err)
	}
	scoped := false
	for _, q := range f2.recorded() {
		if strings.Contains(q, `UPDATE "overlays"`) {
			scoped = strings.Contains(q, `"user_id" = $3`)
		}
	}
	if !scoped {
		t.Fatalf("overlay update not tenant-scoped: %v", f2.recorded())
	}
}

func TestSeatTypeListOrderedBySlug(t *testing.T) {
	now := time.Now().UTC()
	seatTypeCols := []string{"id", "user_id", "slug", "name", "description", "created_at"}
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "seat_types"`) {
			return seatTypeCols, [][]driver.Value{
				fakeRow("b", testUser, "zeta", "Zeta", "d", now),
				fakeRow("a", testUser, "alpha", "Alpha", "d", now),
			}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatTypeRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	got, err := repo.List(context.Background(), testUser)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 2 || got[0].Slug != "alpha" || got[1].Slug != "zeta" {
		t.Fatalf("List = %+v", got)
	}
	scoped := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `FROM "seat_types"`) && strings.Contains(q, `"user_id" = $1`) {
			scoped = true
		}
	}
	if !scoped {
		t.Fatalf("seat type list not tenant-scoped: %v", f.recorded())
	}
}

func TestSeatSettingsGetDefaultsFalse(t *testing.T) {
	f := &fakeDriver{}
	repo, err := NewORMSeatSettingsRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	got, err := repo.Get(context.Background(), testUser)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got == nil || got.UserID != testUser || got.FollowLatest {
		t.Fatalf("Get(no row) = %+v", got)
	}
}

func TestSeatSettingsSetInsertsThenUpdates(t *testing.T) {
	now := time.Now().UTC()
	settingsCols := []string{"user_id", "follow_latest", "updated_at"}

	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `INSERT INTO "seat_settings"`):
			return settingsCols, [][]driver.Value{fakeRow(testUser, true, now)}, nil
		case strings.Contains(q, `FROM "seat_settings"`):
			return settingsCols, nil, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatSettingsRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	created, err := repo.Set(context.Background(), testUser, true)
	if err != nil || created == nil || !created.FollowLatest {
		t.Fatalf("Set(create) = %+v, %v", created, err)
	}

	f2 := &fakeDriver{}
	f2.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `UPDATE "seat_settings"`):
			return settingsCols, [][]driver.Value{fakeRow(testUser, false, now)}, nil
		case strings.Contains(q, `FROM "seat_settings"`):
			return settingsCols, [][]driver.Value{fakeRow(testUser, true, now)}, nil
		}
		return nil, nil, nil
	}
	repo2, _ := NewORMSeatSettingsRepository(newFakeManager(t, f2))
	updated, err := repo2.Set(context.Background(), testUser, false)
	if err != nil || updated == nil || updated.FollowLatest {
		t.Fatalf("Set(update) = %+v, %v", updated, err)
	}
	scoped := false
	for _, q := range f2.recorded() {
		if strings.Contains(q, `UPDATE "seat_settings"`) {
			scoped = strings.Contains(q, `"user_id" = $3`)
		}
	}
	if !scoped {
		t.Fatalf("settings update not tenant-scoped: %v", f2.recorded())
	}
}

func TestSeatUpdateOccupantTenantScoped(t *testing.T) {
	f := &fakeDriver{}
	repo, err := NewORMSeatRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.UpdateOccupant(context.Background(), testUser, testSeatID, "codex", "gpt-5.1"); err != nil {
		t.Fatalf("UpdateOccupant: %v", err)
	}
	updated := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `UPDATE "seats" SET "runtime" = $1, "model" = $2`) {
			updated = strings.Contains(q, `"user_id" = $4 AND "id" = $5`)
		}
	}
	if !updated {
		t.Fatalf("occupant update missing or not tenant-scoped: %v", f.recorded())
	}
}

func TestSeatSettingsErrorsNotSwallowed(t *testing.T) {
	boom := errors.New("db boom")
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `"seat_settings"`) {
			return nil, nil, boom
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatSettingsRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Get(context.Background(), testUser); err == nil {
		t.Fatal("Get swallowed the database error")
	}
	if _, err := repo.Set(context.Background(), testUser, true); err == nil {
		t.Fatal("Set swallowed the database error")
	}
}

func TestMachineReplaceSnapshotUpsertsThenReplacesSeats(t *testing.T) {
	f := &fakeDriver{}
	repo, err := NewORMMachineStatusRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	now := time.Now().UTC()
	err = repo.ReplaceSnapshot(context.Background(), testUser, domainrepo.Machine{
		MachineID: "pc-home", LastSeen: now,
		Seats: []domainrepo.SeatStatus{
			{Room: "eng", Seat: "coder", State: "running", Runtime: "claude-code", ReportedAt: now},
			{Room: "eng", Seat: "qa", State: "idle", Runtime: "codex", ReportedAt: now},
		},
		Agents: []domainrepo.MachineAgent{{Agent: "claude", Status: "idle", PaneID: "w5:p3"}},
	})
	if err != nil {
		t.Fatalf("ReplaceSnapshot: %v", err)
	}
	var order []string
	for _, q := range f.recorded() {
		switch {
		case strings.Contains(q, `INSERT INTO "machines"`) && strings.Contains(q, `ON CONFLICT ("user_id", "machine_id")`):
			order = append(order, "upsert")
		case strings.Contains(q, `DELETE FROM "seat_status"`) && strings.Contains(q, `"user_id" = $1 AND "machine_id" = $2`):
			order = append(order, "delete")
		case strings.Contains(q, `INSERT INTO "seat_status"`):
			order = append(order, "insert")
		}
	}
	if got := strings.Join(order, ","); got != "upsert,delete,insert,insert" {
		t.Fatalf("statement order = %s", got)
	}
}

func TestMachineReplaceSnapshotErrorNotSwallowed(t *testing.T) {
	boom := errors.New("db boom")
	f := &fakeDriver{execErr: func(q string) error {
		if strings.Contains(q, `DELETE FROM "seat_status"`) {
			return boom
		}
		return nil
	}}
	repo, err := NewORMMachineStatusRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.ReplaceSnapshot(context.Background(), testUser, domainrepo.Machine{MachineID: "pc-home"}); err == nil {
		t.Fatal("ReplaceSnapshot swallowed the database error")
	}
}

func TestMachineDeleteSeatStatusForRoomIsTenantAndRoomScoped(t *testing.T) {
	f := &fakeDriver{}
	repo, err := NewORMMachineStatusRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.DeleteSeatStatusForRoom(context.Background(), testUser, "eng"); err != nil {
		t.Fatalf("DeleteSeatStatusForRoom: %v", err)
	}
	found := false
	for _, q := range f.recorded() {
		if strings.Contains(q, `DELETE FROM "seat_status" WHERE "user_id" = $1 AND "room" = $2`) {
			found = true
		}
	}
	if !found {
		t.Fatalf("no tenant and room scoped delete: %v", f.recorded())
	}
}

func TestMachineListGroupsSeatsAndAgentsPerMachine(t *testing.T) {
	now := time.Now().UTC()
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `FROM "machines"`):
			return []string{"machine_id", "last_seen", "agents"}, [][]driver.Value{
				fakeRow("pc-home", now, []byte(`[{"agent":"claude","status":"idle","pane_id":"w5:p3"}]`)),
				fakeRow("pc-work", now, []byte(`[]`)),
			}, nil
		case strings.Contains(q, `FROM "seat_status"`):
			return []string{"machine_id", "room", "seat", "state", "runtime", "running_hash", "expected_hash", "detail", "redacted", "reported_at"}, [][]driver.Value{
				fakeRow("pc-home", "eng", "coder", "running", "claude-code", "abc", "def", "busy", true, now),
			}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMMachineStatusRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	got, err := repo.List(context.Background(), testUser)
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 2 || len(got[0].Seats) != 1 || got[0].Seats[0].RunningHash != "abc" || got[0].Seats[0].ExpectedHash != "def" || !got[0].Seats[0].Redacted ||
		len(got[0].Agents) != 1 || got[0].Agents[0].PaneID != "w5:p3" || len(got[1].Seats) != 0 {
		t.Fatalf("List = %+v", got)
	}
	for _, q := range f.recorded() {
		if strings.Contains(q, `FROM "machines"`) || strings.Contains(q, `FROM "seat_status"`) {
			if !strings.Contains(q, `"user_id" = $1`) {
				t.Fatalf("machine list not tenant-scoped: %s", q)
			}
		}
		if strings.Contains(q, `FROM "seat_status"`) {
			// the expected hash joins rooms, seats and resolved_seats, each on the same user
			for _, join := range []string{
				`"rooms" AS r ON r."user_id" = ss."user_id"`,
				`"seats" AS s ON s."user_id" = ss."user_id"`,
				`WHERE rs."user_id" = ss."user_id" AND rs."seat_id" = s."id" ORDER BY rs."created_at" DESC, rs."id" DESC LIMIT 1`,
			} {
				if !strings.Contains(q, join) {
					t.Fatalf("expected-hash query missing %q: %s", join, q)
				}
			}
		}
	}
}

func TestSeatTableMetadataMatchesStructs(t *testing.T) {
	cases := []struct {
		table string
		typ   reflect.Type
	}{
		{"modules", reflect.TypeOf(seatdb.ModuleORM{})},
		{"module_versions", reflect.TypeOf(seatdb.ModuleVersionORM{})},
		{"seat_types", reflect.TypeOf(seatdb.SeatTypeORM{})},
		{"seat_type_versions", reflect.TypeOf(seatdb.SeatTypeVersionORM{})},
		{"rooms", reflect.TypeOf(seatdb.RoomORM{})},
		{"seats", reflect.TypeOf(seatdb.SeatORM{})},
		{"overlays", reflect.TypeOf(seatdb.OverlayORM{})},
		{"seat_links", reflect.TypeOf(seatdb.SeatLinkORM{})},
		{"resolved_seats", reflect.TypeOf(seatdb.ResolvedSeatORM{})},
		{"seat_settings", reflect.TypeOf(seatdb.SeatSettingsORM{})},
		{"machines", reflect.TypeOf(seatdb.MachineORM{})},
		{"seat_status", reflect.TypeOf(seatdb.SeatStatusORM{})},
	}
	byName := map[string]database.TableDef{}
	for _, def := range database.Tables {
		byName[def.Name] = def
	}
	for _, tc := range cases {
		def, ok := byName[tc.table]
		if !ok {
			t.Errorf("table %s is not registered", tc.table)
			continue
		}
		cols := map[string]bool{}
		for _, c := range def.Columns {
			cols[c.Name] = true
		}
		for i := 0; i < tc.typ.NumField(); i++ {
			tag := tc.typ.Field(i).Tag.Get("db")
			if !cols[tag] {
				t.Errorf("table %s: field %s (db %q) missing from metadata", tc.table, tc.typ.Field(i).Name, tag)
			}
		}
	}
}

func TestRepositoryConstructors(t *testing.T) {
	sessions := database.NewSessionManager(&database.DatabaseConfig{})
	if _, err := NewORMModuleRepository(sessions); err != nil {
		t.Fatalf("NewORMModuleRepository: %v", err)
	}
	if _, err := NewORMSeatTypeRepository(sessions); err != nil {
		t.Fatalf("NewORMSeatTypeRepository: %v", err)
	}
	if _, err := NewORMRoomRepository(sessions); err != nil {
		t.Fatalf("NewORMRoomRepository: %v", err)
	}
	if _, err := NewORMSeatRepository(sessions); err != nil {
		t.Fatalf("NewORMSeatRepository: %v", err)
	}
	if _, err := NewORMOverlayRepository(sessions); err != nil {
		t.Fatalf("NewORMOverlayRepository: %v", err)
	}
	if _, err := NewORMSeatLinkRepository(sessions); err != nil {
		t.Fatalf("NewORMSeatLinkRepository: %v", err)
	}
	if _, err := NewORMResolvedSeatRepository(sessions); err != nil {
		t.Fatalf("NewORMResolvedSeatRepository: %v", err)
	}
	if _, err := NewORMSeatSettingsRepository(sessions); err != nil {
		t.Fatalf("NewORMSeatSettingsRepository: %v", err)
	}
	if _, err := NewORMMachineStatusRepository(sessions); err != nil {
		t.Fatalf("NewORMMachineStatusRepository: %v", err)
	}
}

func assertNoStatement(t *testing.T, f *fakeDriver, substr string) {
	t.Helper()
	for _, q := range f.recorded() {
		if strings.Contains(q, substr) {
			t.Fatalf("unexpected statement %q", q)
		}
	}
}

// ---- cross-tenant coverage for the five seat tables the other tests do not assert ----
//
// The reviewer found that module_versions, seat_type_versions, rooms, seat_links and
// resolved_seats had no test asserting the user_id filter. Every statement that touches a
// seat table must carry it (an INSERT writes the column; a SELECT/UPDATE/DELETE filters on it).

// assertTenantScoped fails when a recorded statement touches table without user_id.
func assertTenantScoped(t *testing.T, f *fakeDriver, table string) {
	t.Helper()
	saw := false
	for _, q := range f.recorded() {
		if !strings.Contains(q, `"`+table+`"`) {
			continue
		}
		saw = true
		if strings.Contains(q, "INSERT INTO") {
			open := strings.Index(q, "(")
			closeIdx := strings.Index(q, ")")
			if open < 0 || closeIdx < open || !strings.Contains(q[open:closeIdx], `"user_id"`) {
				t.Errorf("%s insert does not write user_id in its column list: %s", table, q)
			}
			continue
		}
		if !strings.Contains(q, `"user_id" = $`) {
			t.Errorf("%s statement not tenant-scoped: %s", table, q)
		}
	}
	if !saw {
		t.Fatalf("no statement touched %q", table)
	}
}

func TestRoomStatementsAreTenantScoped(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	roomCols := []string{"id", "user_id", "slug", "name", "team_id", "created_at", "updated_at"}
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		if strings.Contains(q, `FROM "rooms"`) {
			return roomCols, [][]driver.Value{fakeRow(testRoomID, testUser, "eng", "Engineering", nil, now, now)}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMRoomRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.List(ctx, testUser); err != nil {
		t.Fatalf("List: %v", err)
	}
	if _, err := repo.GetBySlug(ctx, testUser, "eng"); err != nil {
		t.Fatalf("GetBySlug: %v", err)
	}
	// The sharing reads and the sharing write are covered by the same rule: GetVisibleBySlug
	// widens by the caller's memberships and SetTeam matches the owner, and both still carry the
	// user_id filter this test asserts.
	if _, err := repo.GetVisibleBySlug(ctx, testUser, "eng"); err != nil {
		t.Fatalf("GetVisibleBySlug: %v", err)
	}
	if err := repo.SetTeam(ctx, testUser, testRoomID, testRoomID); err != nil {
		t.Fatalf("SetTeam: %v", err)
	}
	if err := repo.Delete(ctx, testUser, testRoomID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	assertTenantScoped(t, f, "rooms")
}

func TestSeatLinkStatementsAreTenantScoped(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	cols := []string{"id", "user_id", "from_seat_id", "to_seat_id", "kind", "allow", "created_at"}
	linkRow := fakeRow("l1", testUser, testSeatID, testRoomID, "delegates_to", true, now)
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `FROM "seat_links"`):
			return cols, nil, nil // no existing link, so Upsert takes the create path
		case strings.Contains(q, `INSERT INTO "seat_links"`):
			return cols, [][]driver.Value{linkRow}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatLinkRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Upsert(ctx, testUser, domainrepo.SeatLink{FromSeatID: testSeatID, ToSeatID: testRoomID, Kind: "delegates_to", Allow: true}); err != nil {
		t.Fatalf("Upsert: %v", err)
	}
	if _, err := repo.ListFrom(ctx, testUser, testSeatID); err != nil {
		t.Fatalf("ListFrom: %v", err)
	}
	if _, err := repo.Delete(ctx, testUser, testSeatID, testRoomID, "delegates_to"); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if err := repo.DeleteBySeat(ctx, testUser, testSeatID); err != nil {
		t.Fatalf("DeleteBySeat: %v", err)
	}
	assertTenantScoped(t, f, "seat_links")
}

func TestResolvedSeatStatementsAreTenantScoped(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	cols := []string{"id", "user_id", "seat_id", "hash", "runtime", "files", "policy", "created_at"}
	row := fakeRow("66666666-6666-4666-8666-666666666666", testUser, testSeatID, "h1", "omp", []byte("[]"), []byte("{}"), now)
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `FROM "resolved_seats"`):
			return cols, nil, nil // no snapshot yet, so Save takes the create path
		case strings.Contains(q, `INSERT INTO "resolved_seats"`):
			return cols, [][]driver.Value{row}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMResolvedSeatRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetLatest(ctx, testUser, testSeatID); err != nil {
		t.Fatalf("GetLatest: %v", err)
	}
	if _, err := repo.Save(ctx, testUser, domainrepo.ResolvedSeat{SeatID: testSeatID, Hash: "h1", Runtime: "omp"}); err != nil {
		t.Fatalf("Save: %v", err)
	}
	if err := repo.DeleteBySeat(ctx, testUser, testSeatID); err != nil {
		t.Fatalf("DeleteBySeat: %v", err)
	}
	assertTenantScoped(t, f, "resolved_seats")
}

func TestModuleVersionStatementsAreTenantScoped(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `FROM "modules"`):
			return moduleCols, [][]driver.Value{fakeRow(testModuleID, testUser, "instr", "instruction", now)}, nil
		case strings.Contains(q, `FROM "module_versions"`):
			return moduleVersionCols, nil, nil // no version yet, so AddVersion inserts
		case strings.Contains(q, `INSERT INTO "module_versions"`):
			return moduleVersionCols, [][]driver.Value{fakeRow(testVersionID, testUser, testModuleID, "1.0.0", "hello", moduleVersionChecksum("hello"), now)}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMModuleRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.AddVersion(ctx, testUser, "instr", "1.0.0", "hello"); err != nil {
		t.Fatalf("AddVersion: %v", err)
	}
	assertTenantScoped(t, f, "module_versions")
}

func TestSeatTypeVersionStatementsAreTenantScoped(t *testing.T) {
	ctx := context.Background()
	now := time.Now().UTC()
	refs := []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	encoded, err := encodeModuleRefs(refs)
	if err != nil {
		t.Fatal(err)
	}
	versionCols := []string{"id", "user_id", "seat_type_id", "version", "default_runtime", "module_refs", "created_at"}
	f := &fakeDriver{}
	f.respond = func(q string, args []driver.Value) ([]string, [][]driver.Value, error) {
		switch {
		case strings.Contains(q, `FROM "seat_types"`):
			return []string{"id", "user_id", "slug", "name", "description", "created_at"}, [][]driver.Value{fakeRow(testSeatTypeID, testUser, "seat.standard", "Standard", "desc", now)}, nil
		case strings.Contains(q, `FROM "seat_type_versions"`):
			return versionCols, nil, nil // no version yet, so AddVersion inserts
		case strings.Contains(q, `INSERT INTO "seat_type_versions"`):
			return versionCols, [][]driver.Value{fakeRow("v", testUser, testSeatTypeID, "0.0.1", "go1.23", []byte(encoded), now)}, nil
		}
		return nil, nil, nil
	}
	repo, err := NewORMSeatTypeRepository(newFakeManager(t, f))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.AddVersion(ctx, testUser, "seat.standard", "0.0.1", "go1.23", refs); err != nil {
		t.Fatalf("AddVersion: %v", err)
	}
	assertTenantScoped(t, f, "seat_type_versions")
}
