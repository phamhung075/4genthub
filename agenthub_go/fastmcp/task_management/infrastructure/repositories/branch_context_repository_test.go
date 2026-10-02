package repositories

// Tests for BranchContextRepository against a real PostgreSQL instance.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func branchCtxRepoTestNew(t *testing.T, sessions *database.SessionManager, userID string) *BranchContextRepository {
	t.Helper()
	repo, err := NewBranchContextRepository(sessions, &userID)
	if err != nil {
		t.Fatalf("NewBranchContextRepository: %v", err)
	}
	return repo
}

// branchCtxRepoTestProjectContext creates the project_contexts row a branch context points
// at through parent_project_id.
func branchCtxRepoTestProjectContext(t *testing.T, sessions *database.SessionManager, user, id string) {
	t.Helper()
	repo, err := NewProjectContextRepository(sessions, &user)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Create(context.Background(), &entities.ProjectContext{
		ID: id, ProjectInfo: map[string]any{}, Metadata: map[string]any{},
	}); err != nil {
		t.Fatalf("create project context: %v", err)
	}
}

func branchCtxRepoTestEntity(id, projectID string) *entities.BranchContext {
	return &entities.BranchContext{
		ID: id, ProjectID: projectID, GitBranchName: "ignored",
		BranchInfo:         map[string]any{"name": "feature/x"},
		BranchWorkflow:     map[string]any{"status": "started"},
		FeatureFlags:       map[string]any{"flag": true},
		DiscoveredPatterns: map[string]any{"pattern": int64(1)},
		BranchDecisions:    map[string]any{"decision": int64(2)},
		BranchSettings:     map[string]any{"branch_standards": map[string]any{"standard": int64(3)}},
		Metadata: map[string]any{
			"active_patterns":  map[string]any{"active": int64(4)},
			"local_overrides":  map[string]any{"override": int64(5)},
			"delegation_rules": map[string]any{"rule": int64(6)},
			"custom_meta":      "kept-in-data",
		},
	}
}

func TestBranchContextRepoCRUD(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := branchCtxRepoTestNew(t, sessions, user)

	projectContextID := tmvo.NewUUIDv4()
	branchCtxRepoTestProjectContext(t, sessions, user, projectContextID)

	id := tmvo.NewUUIDv4()
	created, err := repo.Create(ctx, branchCtxRepoTestEntity(id, projectContextID))
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID != id || created.ProjectID != projectContextID {
		t.Fatalf("created = %+v", created)
	}
	if created.GitBranchName != "feature/x" {
		t.Fatalf("git_branch_name = %q", created.GitBranchName)
	}
	if v := globalContextRepoAsMap(created.BranchDecisions); v["standard"] != int64(3) {
		t.Fatalf("branch_decisions = %+v", created.BranchDecisions)
	}
	if v := globalContextRepoAsMap(created.Metadata["active_patterns"]); v["active"] != int64(4) {
		t.Fatalf("active_patterns = %+v", created.Metadata["active_patterns"])
	}
	// BranchContext timestamps are nullable and the Python create() never sets them.
	if created.Metadata["created_at"] != nil {
		t.Fatalf("created_at = %+v, want nil", created.Metadata["created_at"])
	}

	// Create is idempotent: an existing (id, user) returns the stored entity.
	again, err := repo.Create(ctx, branchCtxRepoTestEntity(id, projectContextID))
	if err != nil || again == nil || again.ID != id {
		t.Fatalf("idempotent Create = %+v, %v", again, err)
	}

	got, err := repo.Get(ctx, id)
	if err != nil || got == nil || got.ID != id {
		t.Fatalf("Get = %+v, %v", got, err)
	}
	if missing, _ := repo.Get(ctx, tmvo.NewUUIDv4()); missing != nil {
		t.Fatalf("Get(missing) = %+v", missing)
	}

	updatedEntity := branchCtxRepoTestEntity(id, projectContextID)
	updatedEntity.BranchInfo = map[string]any{"name": "feature/y"}
	updated, err := repo.Update(ctx, id, updatedEntity)
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.GitBranchName != "feature/y" {
		t.Fatalf("git_branch_name after update = %q", updated.GitBranchName)
	}
	if _, err := repo.Update(ctx, tmvo.NewUUIDv4(), updatedEntity); err == nil {
		t.Fatal("Update of missing context must fail")
	}

	list, err := repo.List(ctx, NewKwargs("project_id", projectContextID))
	if err != nil || len(list) != 1 {
		t.Fatalf("List(project_id) = %d, %v", len(list), err)
	}
	if none, err := repo.List(ctx, NewKwargs("project_id", tmvo.NewUUIDv4())); err != nil || len(none) != 0 {
		t.Fatalf("List(other) = %d, %v", len(none), err)
	}
	if all, err := repo.List(ctx, NewKwargs("git_branch_name", "ignored")); err != nil || len(all) != 1 {
		t.Fatalf("List(git_branch_name) = %d, %v", len(all), err)
	}

	deleted, err := repo.Delete(ctx, id)
	if err != nil || !deleted {
		t.Fatalf("Delete = %v, %v", deleted, err)
	}
	if deleted, _ := repo.Delete(ctx, id); deleted {
		t.Fatal("second Delete should be false")
	}
}

func TestBranchContextRepoNormalizationAndFallback(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := branchCtxRepoTestNew(t, sessions, user)

	// An invalid UUID id is replaced by a fresh uuid4.
	invalid := branchCtxRepoTestEntity("not-a-uuid", "")
	created, err := repo.Create(ctx, invalid)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, ok := tmvo.PyParseUUID(created.ID); !ok {
		t.Fatalf("normalized id = %q, want a UUID", created.ID)
	}

	// With no branch_id and no branch_info name, git_branch_name falls back to branch-<id>.
	noName := tmvo.NewUUIDv4()
	plain := branchCtxRepoTestEntity(noName, "")
	plain.BranchInfo = map[string]any{}
	got, err := repo.Create(ctx, plain)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if got.GitBranchName != "branch-"+noName {
		t.Fatalf("git_branch_name = %q", got.GitBranchName)
	}

	// A missing user_id is rejected.
	anon, err := NewBranchContextRepository(sessions, nil)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := anon.Create(ctx, branchCtxRepoTestEntity(tmvo.NewUUIDv4(), "")); err == nil {
		t.Fatal("Create without user_id must fail")
	}
}

func TestBranchContextRepoUserIsolation(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	userA, userB := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	repoA, repoB := branchCtxRepoTestNew(t, sessions, userA), branchCtxRepoTestNew(t, sessions, userB)

	idA, idB := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	if _, err := repoA.Create(ctx, branchCtxRepoTestEntity(idA, "")); err != nil {
		t.Fatal(err)
	}
	if _, err := repoB.Create(ctx, branchCtxRepoTestEntity(idB, "")); err != nil {
		t.Fatal(err)
	}
	if got, _ := repoA.Get(ctx, idB); got != nil {
		t.Fatal("user A must not read user B's branch context")
	}
	if list, _ := repoA.List(ctx, nil); len(list) != 1 || list[0].ID != idA {
		t.Fatalf("repoA list = %+v", list)
	}
	scoped := repoA.WithUser(userB)
	if got, _ := scoped.Get(ctx, idB); got == nil {
		t.Fatal("WithUser should see user B's branch context")
	}
}
