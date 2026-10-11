package database_test

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestSchemaValidatorRealPostgres(t *testing.T) {
	dsn := newTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2, MaxOverflow: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	cfg := &database.DatabaseConfig{Engine: &database.Engine{DB: db, URL: dsn}}
	if err := cfg.CreateTables(ctx); err != nil {
		t.Fatal(err)
	}
	engine := &database.Engine{DB: db, URL: dsn}
	validator := database.NewSchemaValidator(ctx, engine)
	results, err := validator.ValidateAll()
	if err != nil {
		t.Fatal(err)
	}
	status, _ := results.Get("status")
	if status != "PASS" {
		issues, _ := results.Get("issues")
		t.Fatalf("status = %v, issues = %v", status, issues)
	}
	validated, _ := results.Get("validated_models")
	names, ok := validated.([]any)
	// 15, not 16: the agents model was retired with the manage_agent tool (commit 76b800b9), so the
	// ORM declares one model fewer and the validator, which walks the ORM's own list, validates one
	// fewer. A count is an invariant here rather than an incidental number - it is how this case
	// notices a model that was added or dropped without the schema following - which is why the
	// number moves with the ORM instead of the case being deleted.
	if !ok || len(names) != 15 {
		t.Fatalf("validated_models = %v", validated)
	}
	if !database.ValidateSchemaOnStartup(ctx, engine) {
		t.Fatal("ValidateSchemaOnStartup returned false")
	}
}
