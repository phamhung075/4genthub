package database_test

// THE ASSET RUN ON AN EMPTY DATABASE - the half that answers the row this was filed for.
//
// The scripted-fake cases in db_initializer_init_sql_test.go prove which statements reach the driver
// and that they run in one transaction. They cannot prove the asset is APPLICABLE: the fake enforces
// no names and no types, so an asset that collides with itself (see init_sql_object_names_test.go)
// passes there and fails on the first real boot - where the failure is not partial, because
// ExecuteInitSQLFile runs every statement in ONE transaction: the rollback takes the whole schema with
// it, and a fresh database is left with whatever createAll builds on its own.
//
// So this case drives the real path: the embedded asset, on an empty database, through
// ExecuteInitSQLFile, and then asks the CATALOGUE what exists. It skips loudly without
// AGENTHUB_TEST_PG_URL, like its neighbours, because that is the only way to run it.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestTheEmbeddedInitSQLBuildsAFreshDatabase(t *testing.T) {
	dsn := newTestDatabase(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2, PoolRecycle: 60})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })

	inst, err := database.NewDatabaseInitializer(context.Background(), database.OSDeps(),
		&database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}})
	if err != nil {
		t.Fatal(err)
	}
	if !inst.ExecuteInitSQLFile() {
		t.Fatal("the embedded init SQL did not run to completion on an empty database - the log above names the statement that failed, and its whole transaction rolled back")
	}
	if !inst.VerifyTableStructure() {
		t.Error("the asset ran but the tables VerifyTableStructure requires are not all there")
	}

	// The asset creates its tables WITHOUT the unique constraints inline and adds them in one
	// ALTER section at the end; a unique constraint is backed by an index carrying its name. That is
	// the shape the collision broke, so the catalogue is asked for the constraint itself rather than
	// for the index it implies.
	ctx := context.Background()
	var constraints int
	if err := db.QueryRowContext(ctx, `
		SELECT count(*) FROM pg_constraint k
		JOIN pg_class r ON r.oid = k.conrelid
		WHERE r.relname = 'context_inheritance_cache' AND k.conname = 'uq_cache_context' AND k.contype = 'u'`).Scan(&constraints); err != nil {
		t.Fatal(err)
	}
	if constraints != 1 {
		t.Errorf("uq_cache_context is not one unique constraint on context_inheritance_cache (found %d): the asset's ALTER section did not reach the end of the file", constraints)
	}

	// A table only this asset creates, so a run that returned true without executing the tail cannot
	// pass: token_transactions comes from the production set, not from createAll's registry.
	var exists bool
	if err := db.QueryRowContext(ctx, `SELECT to_regclass('token_transactions') IS NOT NULL`).Scan(&exists); err != nil {
		t.Fatal(err)
	}
	if !exists {
		t.Error("token_transactions, which only the asset creates, is absent - the file did not reach its end")
	}

	var tables int
	if err := db.QueryRowContext(ctx, `
		SELECT count(*) FROM information_schema.tables
		WHERE table_schema = 'public' AND table_type = 'BASE TABLE'`).Scan(&tables); err != nil {
		t.Fatal(err)
	}
	t.Logf("the embedded init SQL built %d base tables on an empty database", tables)
}
