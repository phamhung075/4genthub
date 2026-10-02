package repositories

// Tests for GlobalContextRepository against a real PostgreSQL instance.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func globalCtxRepoTestNew(t *testing.T, sessions *database.SessionManager, userID *string) *GlobalContextRepository {
	t.Helper()
	repo, err := NewGlobalContextRepository(sessions, userID)
	if err != nil {
		t.Fatalf("NewGlobalContextRepository: %v", err)
	}
	return repo
}

func globalCtxRepoTestSettings() map[string]any {
	return map[string]any{
		"organization": map[string]any{
			"standards":  map[string]any{"style": "go"},
			"compliance": map[string]any{"gdpr": true},
			"policies":   map[string]any{"delegate": true},
		},
		"security":    map[string]any{"access_control": map[string]any{"mfa": true}},
		"operations":  map[string]any{"resources": map[string]any{"db": "pg"}},
		"development": map[string]any{"patterns": map[string]any{"ddd": true}},
		"preferences": map[string]any{"user_interface": map[string]any{"theme": "dark"}},
	}
}

func TestGlobalContextRepoCRUD(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := globalCtxRepoTestNew(t, sessions, &user)

	id, orgName := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	created, err := repo.Create(ctx, entities.NewGlobalContext(id, orgName, globalCtxRepoTestSettings(), map[string]any{}))
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID != id {
		t.Fatalf("id = %q", created.ID)
	}
	if created.OrganizationName != orgName {
		t.Fatalf("organization_name = %q", created.OrganizationName)
	}
	if v, _ := created.GlobalSettings["organization_standards"].(map[string]any); v["style"] != "go" {
		t.Fatalf("organization_standards = %+v", created.GlobalSettings["organization_standards"])
	}
	if v, _ := created.GlobalSettings["security_policies"].(map[string]any); v["mfa"] != true {
		t.Fatalf("security_policies = %+v", created.GlobalSettings["security_policies"])
	}
	if v, _ := created.GlobalSettings["compliance_requirements"].(map[string]any); v["gdpr"] != true {
		t.Fatalf("compliance_requirements = %+v", created.GlobalSettings["compliance_requirements"])
	}
	if v, _ := created.GlobalSettings["shared_resources"].(map[string]any); v["db"] != "pg" {
		t.Fatalf("shared_resources = %+v", created.GlobalSettings["shared_resources"])
	}
	if v, _ := created.GlobalSettings["reusable_patterns"].(map[string]any); v["ddd"] != true {
		t.Fatalf("reusable_patterns = %+v", created.GlobalSettings["reusable_patterns"])
	}
	if v, _ := created.GlobalSettings["delegation_rules"].(map[string]any); v["delegate"] != true {
		t.Fatalf("delegation_rules = %+v", created.GlobalSettings["delegation_rules"])
	}
	prefs, _ := created.GlobalSettings["user_preferences"].(map[string]any)
	if ui := globalContextRepoAsMap(prefs["user_interface"]); ui["theme"] != "dark" {
		t.Fatalf("user_preferences = %+v", created.GlobalSettings["user_preferences"])
	}
	if created.Metadata["schema_version"] != "1.0" || created.Metadata["is_migrated"] != false {
		t.Fatalf("metadata = %+v", created.Metadata)
	}
	if _, ok := created.Metadata["created_at"].(string); !ok {
		t.Fatalf("created_at = %+v", created.Metadata["created_at"])
	}
	if created.Metadata["version"] != int64(1) {
		t.Fatalf("version = %+v", created.Metadata["version"])
	}

	if _, err := repo.Create(ctx, entities.NewGlobalContext(id, orgName, globalCtxRepoTestSettings(), map[string]any{})); err == nil {
		t.Fatal("duplicate Create must fail")
	}

	got, err := repo.Get(ctx, id)
	if err != nil || got == nil || got.ID != id {
		t.Fatalf("Get = %+v, %v", got, err)
	}
	if missing, _ := repo.Get(ctx, tmvo.NewUUIDv4()); missing != nil {
		t.Fatalf("Get(missing) = %+v", missing)
	}

	updated, err := repo.Update(ctx, id, entities.NewGlobalContext(id, orgName, map[string]any{
		"organization_standards": map[string]any{"style": "rust"},
		"user_preferences":       map[string]any{"theme": "light"},
	}, map[string]any{}))
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if v, _ := updated.GlobalSettings["organization_standards"].(map[string]any); v["style"] != "rust" {
		t.Fatalf("organization_standards after update = %+v", updated.GlobalSettings["organization_standards"])
	}
	if v, _ := updated.GlobalSettings["user_preferences"].(map[string]any); v["theme"] != "light" {
		t.Fatalf("user_preferences after update = %+v", updated.GlobalSettings["user_preferences"])
	}
	if _, err := repo.Update(ctx, tmvo.NewUUIDv4(), entities.NewGlobalContext(tmvo.NewUUIDv4(), orgName, map[string]any{}, nil)); err == nil {
		t.Fatal("Update of missing context must fail")
	}

	list, err := repo.List(ctx, nil)
	if err != nil || len(list) != 1 {
		t.Fatalf("List = %d, %v", len(list), err)
	}
	exists, err := repo.Exists(ctx, id)
	if err != nil || !exists {
		t.Fatalf("Exists = %v, %v", exists, err)
	}
	if exists, _ := repo.Exists(ctx, tmvo.NewUUIDv4()); exists {
		t.Fatal("Exists(missing) must be false")
	}
	count, err := repo.CountUserContexts(ctx)
	if err != nil || count != 1 {
		t.Fatalf("CountUserContexts = %d, %v", count, err)
	}

	deleted, err := repo.Delete(ctx, id)
	if err != nil || !deleted {
		t.Fatalf("Delete = %v, %v", deleted, err)
	}
	if _, err := repo.Delete(ctx, id); err == nil {
		t.Fatal("Delete of missing context must fail")
	}
}

func TestGlobalContextRepoCustomFields(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := globalCtxRepoTestNew(t, sessions, &user)

	id := tmvo.NewUUIDv4()
	_, err := repo.Create(ctx, entities.NewGlobalContext(id, tmvo.NewUUIDv4(), map[string]any{}, map[string]any{}))
	if err != nil {
		t.Fatal(err)
	}
	updated, err := repo.Update(ctx, id, entities.NewGlobalContext(id, tmvo.NewUUIDv4(), map[string]any{
		"custom_thing":      map[string]any{"x": int64(1)},
		"ai_agent_settings": map[string]any{"preferred_agents": []any{"a"}},
	}, map[string]any{}))
	if err != nil {
		t.Fatal(err)
	}
	if v := globalContextRepoAsMap(updated.GlobalSettings["custom_thing"]); v["x"] != int64(1) {
		t.Fatalf("custom_thing = %+v", updated.GlobalSettings["custom_thing"])
	}
	if v := globalContextRepoAsMap(updated.GlobalSettings["ai_agent_settings"]); v == nil {
		t.Fatalf("ai_agent_settings = %+v", updated.GlobalSettings["ai_agent_settings"])
	}
	if v, _ := updated.GlobalSettings["user_preferences"].(map[string]any); len(v) != 0 {
		t.Fatalf("user_preferences = %+v", v)
	}
}

func TestGlobalContextRepoUserIsolationAndSingleton(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	userA, userB := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	repoA := globalCtxRepoTestNew(t, sessions, &userA)
	repoB := globalCtxRepoTestNew(t, sessions, &userB)

	id := tmvo.NewUUIDv4()
	if _, err := repoA.Create(ctx, entities.NewGlobalContext(id, tmvo.NewUUIDv4(), map[string]any{}, nil)); err != nil {
		t.Fatal(err)
	}
	if got, _ := repoB.Get(ctx, id); got != nil {
		t.Fatal("user B must not read user A's global context")
	}
	if list, _ := repoA.List(ctx, nil); len(list) != 1 {
		t.Fatalf("repoA list = %d", len(list))
	}
	if list, _ := repoB.List(ctx, nil); len(list) != 0 {
		t.Fatalf("repoB list = %d", len(list))
	}

	// global_singleton id is rewritten to a deterministic user-specific UUID.
	singleton := repoA.normalizeContextID("global_singleton")
	want := database.Uuid5(database.UserIDNamespace, "global_singleton:"+userA)
	if singleton != want {
		t.Fatalf("normalize(global_singleton) = %q, want %q", singleton, want)
	}
	system := globalCtxRepoTestNew(t, sessions, nil)
	if got := system.normalizeContextID("global_singleton"); got != globalContextRepoGlobalSingletonUUID {
		t.Fatalf("system normalize = %q", got)
	}
	if got := repoA.normalizeContextID("plain-id"); got != "plain-id" {
		t.Fatalf("normalize(plain-id) = %q", got)
	}
}

func TestGlobalContextRepoMigrateQuirk(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := globalCtxRepoTestNew(t, sessions, &user)
	if _, err := repo.Create(ctx, entities.NewGlobalContext(tmvo.NewUUIDv4(), tmvo.NewUUIDv4(), map[string]any{}, nil)); err != nil {
		t.Fatal(err)
	}
	t.Setenv("SYSTEM_USER_ID", "system-user")
	migrated, err := repo.MigrateToUserScoped(ctx)
	if err != nil {
		t.Fatalf("MigrateToUserScoped: %v", err)
	}
	if migrated != 0 {
		t.Fatalf("migrated = %d, want 0 (Python `user_id is None` filter is always false)", migrated)
	}
	t.Setenv("SYSTEM_USER_ID", "")
	if _, err := repo.MigrateToUserScoped(ctx); err == nil {
		t.Fatal("missing SYSTEM_USER_ID must raise ValueError")
	}
}
