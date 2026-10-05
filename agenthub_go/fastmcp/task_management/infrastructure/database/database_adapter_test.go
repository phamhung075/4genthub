package database_test

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestDatabaseAdapterJSONExpressions(t *testing.T) {
	adapter := database.NewDatabaseAdapter(nil)
	if got := adapter.JSONExtract("data", "key"); got != "data->>'key'" {
		t.Fatalf("JSONExtract = %q", got)
	}
	if got, err := adapter.JSONSet("data", "key", "x"); err != nil || got != `jsonb_set(data, '{key}', '"x"')` {
		t.Fatalf("JSONSet = %q, %v", got, err)
	}
	if got := adapter.GetJSONKeys("data"); got != "jsonb_object_keys(data)" {
		t.Fatalf("GetJSONKeys = %q", got)
	}
	if got := adapter.GetSchemaType(); got != "JSONB" {
		t.Fatalf("GetSchemaType = %q", got)
	}
	search := entities.NewOrderedMap[any]()
	search.Set("a", 1)
	if got, err := adapter.CreateJSONContainsCondition("data", search); err != nil || got != `data @> '{"a": 1}'::jsonb` {
		t.Fatalf("CreateJSONContainsCondition = %q, %v", got, err)
	}
}

func TestDatabaseAdapterPrepareAndParse(t *testing.T) {
	adapter := database.NewDatabaseAdapter(nil)
	val := entities.NewOrderedMap[any]()
	val.Set("k", "v")
	if got, err := adapter.PrepareJSONValue(val); err != nil || got != `{"k": "v"}` {
		t.Fatalf("PrepareJSONValue = %q, %v", got, err)
	}
	if got, _ := adapter.PrepareJSONValue(42); got != "42" {
		t.Fatalf("PrepareJSONValue int = %q", got)
	}
	parsed := adapter.ParseJSONValue(`{"k": "v"}`)
	om, ok := parsed.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("ParseJSONValue type = %T", parsed)
	}
	if v, _ := om.Get("k"); v != "v" {
		t.Fatalf("ParseJSONValue value = %v", v)
	}
	if got := adapter.ParseJSONValue("not json"); got != "not json" {
		t.Fatalf("ParseJSONValue passthrough = %v", got)
	}
	if got := adapter.ParseJSONValue(nil); got != nil {
		t.Fatalf("ParseJSONValue nil = %v", got)
	}
}

func TestDatabaseAdapterExecuteWithJSONResult(t *testing.T) {
	dsn := newTestDatabase(t)
	db, err := database.PgxOpener(dsn, database.EngineOptions{PoolSize: 2})
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	adapter := database.NewDatabaseAdapter(&database.Engine{DB: db, URL: dsn})
	rows, err := adapter.ExecuteWithJSONResult(ctx, `SELECT '{"a": 1}'::json AS payload, 'plain' AS label`)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 {
		t.Fatalf("rows = %d", len(rows))
	}
	payload, _ := rows[0].Get("payload")
	om, ok := payload.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("payload type = %T", payload)
	}
	if v, _ := om.Get("a"); !tmvo.PyEqual(v, 1) {
		t.Fatalf("payload.a = %v", v)
	}
	if label, _ := rows[0].Get("label"); label != "plain" {
		t.Fatalf("label = %v", label)
	}
}
