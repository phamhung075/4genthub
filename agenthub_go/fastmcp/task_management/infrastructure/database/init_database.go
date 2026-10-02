package database

// Database Initialization Script using SQLAlchemy (Python
// task_management/infrastructure/database/init_database.py).
//
// init_database() maps to InitDatabase. The private async migration runner
// (_run_migrations) drives the Alembic-style migration_runner over an async driver; it is not
// in this slice and has no Go counterpart (async drivers are Python-only), so the call is
// dropped. Because init_database() swallows migration errors and continues, this does not
// change the success path. migrate_from_sqlite_to_postgresql is a SQLite migration and is not
// ported.

import (
	"context"
	"os"
)

// autoMigrateEnabled reports whether the opt-in AUTO_MIGRATE=true switch is set. Every startup
// DDL path (create_all, the AI column safety net, the automatic migrations and the init SQL
// file) runs only under this explicit opt-in, so a default boot never creates or alters tables
// in an existing database. There is no other mode and no fallback.
func autoMigrateEnabled() bool {
	v, ok := os.LookupEnv("AUTO_MIGRATE")
	return ok && v == "true"
}

// InitDatabase gets the singleton configuration and, when AUTO_MIGRATE=true, creates the schema.
// Without the opt-in the configuration is still validated and the existing schema is left
// untouched. It returns the first configuration error.
func InitDatabase(ctx context.Context, deps Deps) error {
	cfg, err := GetInstance(ctx, deps)
	if err != nil {
		return err
	}
	if _, err := cfg.GetDatabaseInfo(); err != nil {
		return err
	}
	if !autoMigrateEnabled() {
		return nil
	}
	return cfg.CreateTables(ctx)
}
