package database

// Database Initializer for Automatic Setup and Verification (Python
// task_management/infrastructure/database/db_initializer.py).
//
// Base.metadata.create_all/drop_all map to createAll and dropAllSchemaTables over Tables.
// The init SQL is EMBEDDED in this package, so the binary carries the schema instead of reading a
// source path at runtime: that path resolved through runtime.Caller and failed inside the distroless
// image, whose contents and working directory are not a source tree (row b231a84b). The naive
// "split on ;" stays verbatim; the comment rule does NOT - skipping a chunk that STARTS with a comment
// discarded the statement underneath it, so all 24 CREATE TABLE statements never ran (row 12444cc2).

import (
	"context"
	"database/sql"
	_ "embed"
	"log"
	"strings"
	"sync"
)

// DatabaseInitializer checks and creates the schema on startup.
type DatabaseInitializer struct {
	ctx         context.Context
	cfg         *DatabaseConfig
	Initialized bool
}

var databaseInitializerRequiredTables = []string{
	"projects",
	"project_git_branchs",
	"tasks",
	"subtasks",
	"task_assignees",
	"labels",
	"task_labels",
	"global_contexts",
	"project_contexts",
	"branch_contexts",
	"task_contexts",
}

// NewDatabaseInitializer builds an initializer; a nil cfg uses the singleton.
func NewDatabaseInitializer(ctx context.Context, deps Deps, cfg *DatabaseConfig) (*DatabaseInitializer, error) {
	if cfg == nil {
		var err error
		cfg, err = GetInstance(ctx, deps)
		if err != nil {
			return nil, err
		}
	}
	return &DatabaseInitializer{ctx: ctx, cfg: cfg}, nil
}

// Initialize mirrors initialize(): verify, then either verify the existing structure or run
// the PostgreSQL init SQL file. The init SQL file is DDL, so it only runs when AUTO_MIGRATE=true;
// without the opt-in a missing schema is reported as not initialized. It returns the Python bool.
func (d *DatabaseInitializer) Initialize() bool {
	if d.cfg == nil || d.cfg.Engine == nil {
		return false
	}
	if !d.VerifyConnection() {
		return false
	}
	if len(d.ExistingTables()) > 0 {
		d.VerifyTableStructure()
		d.Initialized = true
		return true
	}
	if !autoMigrateEnabled() {
		return false
	}
	if d.ExecuteInitSQLFile() {
		d.Initialized = true
		return true
	}
	return false
}

// VerifyConnection runs SELECT 1.
func (d *DatabaseInitializer) VerifyConnection() bool {
	if d.cfg.Engine == nil {
		return false
	}
	_, err := d.cfg.Engine.DB.ExecContext(d.ctx, "SELECT 1")
	return err == nil
}

// ExistingTables returns the current table names as a set.
func (d *DatabaseInitializer) ExistingTables() map[string]bool {
	out := map[string]bool{}
	tables, err := tableNames(d.ctx, d.cfg.Engine.DB)
	if err != nil {
		return out
	}
	for _, t := range tables {
		out[t] = true
	}
	return out
}

// RequiredTables returns the table names from Tables (Base.metadata).
func (d *DatabaseInitializer) RequiredTables() map[string]bool {
	out := map[string]bool{}
	for _, t := range Tables {
		out[t.Name] = true
	}
	return out
}

// databaseInitializerInitSQL is the schema this binary runs on a fresh database. It is EMBEDDED so the
// asset travels with the binary: the source-path read it replaces resolved through runtime.Caller
// against the working directory and failed in the distroless image, whose root holds the binary itself
// and no source tree (row b231a84b). The .sql file stays the single source - edit it, never a copy.
//
//go:embed init_schema_postgresql.sql
var databaseInitializerInitSQL []byte

// ExecuteInitSQLFile runs the embedded schema's statements in one transaction. Every false return says
// which error produced it: with the schema embedded, an unreadable asset - the failure that used to
// hide behind a bare bool here (row b231a84b) - is impossible by construction.
func (d *DatabaseInitializer) ExecuteInitSQLFile() bool {
	tx, err := d.cfg.Engine.DB.BeginTx(d.ctx, nil)
	if err != nil {
		log.Printf("database: could not begin the init SQL transaction: %v", err)
		return false
	}
	statements := strings.Split(string(databaseInitializerInitSQL), ";")
	for _, raw := range statements {
		statement := stripLeadingComments(raw)
		if statement == "" {
			continue
		}
		if _, err := tx.ExecContext(d.ctx, statement); err != nil {
			_ = tx.Rollback()
			log.Printf("database: init SQL statement failed, rolled back: %v: %s", err, statement)
			return false
		}
	}
	if err := tx.Commit(); err != nil {
		log.Printf("database: could not commit the init SQL transaction: %v", err)
		return false
	}
	return true
}

// stripLeadingComments drops whole comment lines from the FRONT of a statement chunk and returns what
// is left to execute. The port inherited "skip a chunk that starts with -- or /*", which threw the
// statement away together with its comment, and every table in this schema is preceded by a
// `-- Table: X` line - so a run over an empty database created nothing and reported success (row
// 12444cc2). A chunk that is only a comment still yields "", and a comment INSIDE a statement is left
// for Postgres to read.
func stripLeadingComments(chunk string) string {
	rest := chunk
	for {
		trimmed := strings.TrimSpace(rest)
		switch {
		case trimmed == "":
			return ""
		case strings.HasPrefix(trimmed, "--"):
			newline := strings.IndexByte(trimmed, '\n')
			if newline < 0 {
				return ""
			}
			rest = trimmed[newline+1:]
		case strings.HasPrefix(trimmed, "/*"):
			end := strings.Index(trimmed, "*/")
			if end < 0 {
				return ""
			}
			rest = trimmed[end+2:]
		default:
			return trimmed
		}
	}
}

// VerifyTableStructure checks the required core tables are present.
func (d *DatabaseInitializer) VerifyTableStructure() bool {
	existing := d.ExistingTables()
	for _, name := range databaseInitializerRequiredTables {
		if !existing[name] {
			return false
		}
	}
	return true
}

// CreateDefaultData is a no-op returning true, like Python.
func (d *DatabaseInitializer) CreateDefaultData() bool { return true }

// CheckAndInit is the server-startup entry point.
func (d *DatabaseInitializer) CheckAndInit() bool {
	if d.Initialized {
		return true
	}
	if !d.Initialize() {
		return false
	}
	d.CreateDefaultData()
	return true
}

// ResetDatabase drops and recreates every table when confirm is true.
func (d *DatabaseInitializer) ResetDatabase(confirm bool) bool {
	if !confirm {
		return false
	}
	if err := dropAllSchemaTables(d.ctx, d.cfg.Engine.DB); err != nil {
		return false
	}
	if err := createAll(d.ctx, d.cfg.Engine.DB); err != nil {
		return false
	}
	d.CreateDefaultData()
	return true
}

// dropAllSchemaTables is Base.metadata.drop_all: reverse dependency order with CASCADE.
func dropAllSchemaTables(ctx context.Context, db *sql.DB) error {
	for i := len(Tables) - 1; i >= 0; i-- {
		if _, err := db.ExecContext(ctx, "DROP TABLE IF EXISTS "+Tables[i].Name+" CASCADE"); err != nil {
			return err
		}
	}
	return nil
}

var (
	dbInitializerMu       sync.Mutex
	dbInitializerInstance *DatabaseInitializer
)

// GetDBInitializer returns the singleton initializer.
func GetDBInitializer(ctx context.Context, deps Deps, cfg *DatabaseConfig) (*DatabaseInitializer, error) {
	dbInitializerMu.Lock()
	defer dbInitializerMu.Unlock()
	if dbInitializerInstance == nil {
		inst, err := NewDatabaseInitializer(ctx, deps, cfg)
		if err != nil {
			return nil, err
		}
		dbInitializerInstance = inst
	}
	return dbInitializerInstance, nil
}

// InitializeDatabaseOnStartup is the convenience entry point.
func InitializeDatabaseOnStartup(ctx context.Context, deps Deps) bool {
	inst, err := GetDBInitializer(ctx, deps, nil)
	if err != nil {
		return false
	}
	return inst.CheckAndInit()
}

// ResetDatabase is the module-level reset convenience function.
func ResetDatabase(ctx context.Context, deps Deps, confirm bool) bool {
	inst, err := GetDBInitializer(ctx, deps, nil)
	if err != nil {
		return false
	}
	return inst.ResetDatabase(confirm)
}
