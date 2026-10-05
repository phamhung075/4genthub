package database

// Centralized Database Initializer (Python
// task_management/infrastructure/database/database_initializer.py).
//
// The SQLite path resolution and the pytest test-mode branch are not ported: SQLite is not
// a Go backend. Everything else, including the initialized-database cache and lock, is kept.

import (
	"context"
	"strings"
	"sync"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

var (
	centralizedDBInitLock sync.Mutex
	centralizedInitDBs    = map[string]bool{}
)

// InitializeDatabaseCentralized initializes the PostgreSQL database once per identifier.
// dbPath is accepted for signature parity; it is only used by the SQLite branch in Python.
func InitializeDatabaseCentralized(ctx context.Context, deps Deps, dbPath string) error {
	databaseType := strings.ToLower(deps.Getenv.get("DATABASE_TYPE", "postgresql"))
	if databaseType == "sqlite" {
		return &tmvo.ValueError{Msg: "PostgreSQL is required for production. Set DATABASE_TYPE=postgresql or supabase."}
	}
	_ = dbPath
	identifier := databaseType

	centralizedDBInitLock.Lock()
	defer centralizedDBInitLock.Unlock()
	if centralizedInitDBs[identifier] {
		return nil
	}
	if err := InitDatabase(ctx, deps); err != nil {
		return err
	}
	centralizedInitDBs[identifier] = true
	return nil
}

// ResetDatabaseInitializationCache clears the initialized-database cache (testing aid).
func ResetDatabaseInitializationCache() {
	centralizedDBInitLock.Lock()
	centralizedInitDBs = map[string]bool{}
	centralizedDBInitLock.Unlock()
}
