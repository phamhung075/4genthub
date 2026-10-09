package database

// Database Initializer for Automatic Setup and Verification (Python
// task_management/infrastructure/database/db_initializer.py).
//
// Base.metadata.create_all/drop_all map to createAll and dropAllSchemaTables over Tables.
// The init SQL file is read from the Python source tree (the generated SQL has no Go copy),
// exactly as the Python reads it from its own directory. The naive "split on ;" and the
// "skip statements starting with -- or /*" rule are kept verbatim.

import (
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"runtime"
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
	if d.ExecuteInitSQLFile("init_schema_postgresql.sql") {
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

// ExecuteInitSQLFile runs the init SQL file's statements in one transaction.
func (d *DatabaseInitializer) ExecuteInitSQLFile(filename string) bool {
	path := databaseInitializerSQLFilePath(filename)
	data, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	tx, err := d.cfg.Engine.DB.BeginTx(d.ctx, nil)
	if err != nil {
		return false
	}
	statements := strings.Split(string(data), ";")
	for _, raw := range statements {
		statement := strings.TrimSpace(raw)
		if statement == "" {
			continue
		}
		lower := strings.ToLower(statement)
		if strings.HasPrefix(lower, "--") || strings.HasPrefix(lower, "/*") {
			continue
		}
		if _, err := tx.ExecContext(d.ctx, statement); err != nil {
			_ = tx.Rollback()
			return false
		}
	}
	if err := tx.Commit(); err != nil {
		return false
	}
	return true
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

// databaseInitializerSQLFilePath resolves the init SQL next to this Go source file.
func databaseInitializerSQLFilePath(filename string) string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return filename
	}
	return filepath.Join(filepath.Dir(file), filename)
}
