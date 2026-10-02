package repositories

// Tests for the ported ProjectContextRepository against a real PostgreSQL instance.

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func projectContextTestNewRepo(t *testing.T, sessions *database.SessionManager, userID string) *ProjectContextRepository {
	t.Helper()
	repo, err := NewProjectContextRepository(sessions, &userID)
	if err != nil {
		t.Fatalf("NewProjectContextRepository: %v", err)
	}
	return repo
}

func projectContextTestEntity(id string) *entities.ProjectContext {
	return &entities.ProjectContext{
		ID:                      id,
		ProjectName:             "ignored",
		ProjectInfo:             map[string]any{"name": "Project X", "status": "active"},
		TeamPreferences:         map[string]any{"review": true},
		TechnologyStack:         map[string]any{"backend": "go"},
		ProjectWorkflow:         map[string]any{},
		LocalStandards:          map[string]any{},
		ProjectSettings:         map[string]any{},
		TechnicalSpecifications: map[string]any{},
		Metadata: map[string]any{
			"global_overrides": map[string]any{"theme": "dark"},
			"delegation_rules": map[string]any{"allow": true},
		},
	}
}

func TestProjectContextRepoCRUD(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectContextTestNewRepo(t, sessions, user)

	id := tmvo.NewUUIDv4()
	created, err := repo.Create(ctx, projectContextTestEntity(id))
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ProjectName != "Project X" {
		t.Fatalf("project_name = %q", created.ProjectName)
	}
	if created.ProjectInfo["status"] != "active" {
		t.Fatalf("project_info = %+v", created.ProjectInfo)
	}
	overrides, _ := created.Metadata["global_overrides"].(map[string]any)
	if overrides["theme"] != "dark" {
		t.Fatalf("global_overrides = %+v", created.Metadata["global_overrides"])
	}
	if created.Metadata["created_at"] != nil || created.Metadata["updated_at"] != nil {
		t.Fatalf("timestamps should be nil: %+v", created.Metadata)
	}
	if v, ok := created.Metadata["version"].(*int64); !ok || v == nil || *v != 1 {
		t.Fatalf("version = %+v", created.Metadata["version"])
	}

	if _, err := repo.Create(ctx, projectContextTestEntity(id)); err == nil {
		t.Fatal("duplicate Create must fail")
	}

	got, err := repo.Get(ctx, id)
	if err != nil || got == nil || got.ID != id {
		t.Fatalf("Get = %+v, %v", got, err)
	}
	missing, err := repo.Get(ctx, tmvo.NewUUIDv4())
	if err != nil || missing != nil {
		t.Fatalf("Get(missing) = %+v, %v", missing, err)
	}

	updated := projectContextTestEntity(id)
	updated.TeamPreferences = map[string]any{"review": false}
	got, err = repo.Update(ctx, id, updated)
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if got.TeamPreferences["review"] != false {
		t.Fatalf("team_preferences = %+v", got.TeamPreferences)
	}
	if _, err := repo.Update(ctx, tmvo.NewUUIDv4(), updated); err == nil {
		t.Fatal("Update of missing context must fail")
	}

	list, err := repo.List(ctx, nil)
	if err != nil || len(list) != 1 {
		t.Fatalf("List = %d, %v", len(list), err)
	}
	filtered, err := repo.List(ctx, NewKwargs("project_id", id))
	if err != nil || len(filtered) != 1 {
		t.Fatalf("List(project_id) = %d, %v", len(filtered), err)
	}
	none, err := repo.List(ctx, NewKwargs("project_id", tmvo.NewUUIDv4()))
	if err != nil || len(none) != 0 {
		t.Fatalf("List(other) = %d, %v", len(none), err)
	}

	deleted, err := repo.Delete(ctx, id)
	if err != nil || !deleted {
		t.Fatalf("Delete = %v, %v", deleted, err)
	}
	if deleted, _ := repo.Delete(ctx, id); deleted {
		t.Fatal("second Delete should be false")
	}
}

func TestProjectContextRepoUserIsolation(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	repoA := projectContextTestNewRepo(t, sessions, projectRepoTestUserA)
	repoB := projectContextTestNewRepo(t, sessions, projectRepoTestUserB)

	idA, idB := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	if _, err := repoA.Create(ctx, projectContextTestEntity(idA)); err != nil {
		t.Fatal(err)
	}
	if _, err := repoB.Create(ctx, projectContextTestEntity(idB)); err != nil {
		t.Fatal(err)
	}

	if got, _ := repoA.Get(ctx, idB); got != nil {
		t.Fatal("user A must not read user B's context")
	}
	list, err := repoA.List(ctx, nil)
	if err != nil || len(list) != 1 || list[0].ID != idA {
		t.Fatalf("List for A = %+v, %v", list, err)
	}

	// system mode (user_id nil) lists every context.
	system, err := NewProjectContextRepository(sessions, nil)
	if err != nil {
		t.Fatal(err)
	}
	all, err := system.List(ctx, nil)
	if err != nil || len(all) != 2 {
		t.Fatalf("system List = %d, %v", len(all), err)
	}

	scoped := repoA.WithUser(projectRepoTestUserB)
	if got, _ := scoped.Get(ctx, idB); got == nil {
		t.Fatal("WithUser should see user B's context")
	}
}

func TestProjectContextRepoToEntityUsesProjectID(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectContextTestNewRepo(t, sessions, user)

	rowID := tmvo.NewUUIDv4()
	projectID := tmvo.NewUUIDv4()
	err := repo.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := repo.ORMRepository.insert(ctx, s, NewKwargs(
			"id", rowID, "project_id", projectID, "user_id", user,
			"project_info", map[string]any{},
		))
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
	got, err := repo.Get(ctx, rowID)
	if err != nil || got == nil {
		t.Fatalf("Get = %+v, %v", got, err)
	}
	if got.ID != projectID {
		t.Fatalf("entity id = %q, want project_id %q", got.ID, projectID)
	}
	if got.ProjectName != "Project-"+projectID {
		t.Fatalf("project_name = %q", got.ProjectName)
	}
	if v, ok := got.Metadata["version"].(*int64); !ok || v == nil {
		t.Fatalf("version = %+v", got.Metadata["version"])
	}
}
