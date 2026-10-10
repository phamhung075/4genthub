package repositories

// Tests for TaskContextRepository against a real PostgreSQL instance.

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// The read-back the gate demanded, through the REAL repository rather than a fake. The first version of the
// service-level test was green only because the in-memory fake stores the entity itself, so it proved the
// service's shape and nothing about persistence - while a real write and a real read were losing both notes.
// This asserts the column's one home in both directions: create with notes, read them back from the entity's
// own field, and confirm the Metadata route is gone.
func TestTaskContextRepositoryImplementationNotesRoundTrip(t *testing.T) {
	sessions := newTestRepoEnv(t)
	user := "11111111-1111-1111-1111-111111111111"
	taskID, branchID := taskCtxRepoTestSetup(t, sessions, user)
	repo := taskCtxRepoTestNew(t, sessions, &user)
	ctx := context.Background()

	notes := map[string]any{"progress_updates": []any{map[string]any{"content": "first note"}}}
	if _, err := repo.Create(ctx, &entities.TaskContextUnified{
		ID: taskID, BranchID: branchID, ImplementationNotes: notes,
	}); err != nil {
		t.Fatalf("Create: %v", err)
	}

	got, err := repo.Get(ctx, taskID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got == nil {
		t.Fatal("Get returned nil for a row it just created")
	}
	updates, _ := got.ImplementationNotes["progress_updates"].([]any)
	if len(updates) != 1 {
		t.Fatalf("ImplementationNotes[progress_updates]=%#v after a round trip; the column is not the entity field's home",
			got.ImplementationNotes)
	}
	entry := fmt.Sprint(updates[0])
	if !strings.Contains(entry, "first note") {
		t.Fatalf("round-tripped note=%v; the text did not survive the column", updates[0])
	}
	if _, ok := got.Metadata["implementation_notes"]; ok {
		t.Fatal("implementation_notes is still travelling through Metadata: that second route is how a write and a read passed each other")
	}
}

func taskCtxRepoTestNew(t *testing.T, sessions *database.SessionManager, userID *string) *TaskContextRepository {
	t.Helper()
	repo, err := NewTaskContextRepository(sessions, userID)
	if err != nil {
		t.Fatalf("NewTaskContextRepository: %v", err)
	}
	return repo
}

// taskCtxRepoTestSetup creates the projects/project_git_branchs/branch_contexts/tasks rows
// that a task context references, and returns the task and branch context ids.
func taskCtxRepoTestSetup(t *testing.T, sessions *database.SessionManager, user string) (string, string) {
	t.Helper()
	ctx := context.Background()
	now := Now().UTC()

	projects, err := NewORMRepository[database.Project]("projects", sessions)
	if err != nil {
		t.Fatal(err)
	}
	projectID := tmvo.NewUUIDv4()
	if _, err := projects.Create(ctx, NewKwargs("id", projectID, "name", "p", "user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create project: %v", err)
	}

	gitBranches, err := NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		t.Fatal(err)
	}
	branchID := tmvo.NewUUIDv4()
	if _, err := gitBranches.Create(ctx, NewKwargs("id", branchID, "project_id", projectID, "name", "main", "user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create git branch: %v", err)
	}

	branchRepo, err := NewBranchContextRepository(sessions, &user)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := branchRepo.Create(ctx, &entities.BranchContext{ID: branchID, BranchInfo: map[string]any{}, Metadata: map[string]any{}}); err != nil {
		t.Fatalf("create branch context: %v", err)
	}

	tasks, err := NewORMRepository[database.Task]("tasks", sessions)
	if err != nil {
		t.Fatal(err)
	}
	taskID := tmvo.NewUUIDv4()
	if _, err := tasks.Create(ctx, NewKwargs("id", taskID, "title", "t", "description", "", "git_branch_id", branchID, "user_id", user, "created_at", now, "updated_at", now)); err != nil {
		t.Fatalf("create task: %v", err)
	}
	return taskID, branchID
}

func taskCtxRepoTestEntity(taskID, branchID string) *entities.TaskContextUnified {
	return &entities.TaskContextUnified{
		ID: taskID, BranchID: branchID,
		TaskData:  map[string]any{"title": "work"},
		Progress:  10,
		Insights:  []any{map[string]any{"category": "insight"}},
		NextSteps: []any{"next"},
		Metadata: map[string]any{
			"local_overrides":      map[string]any{"l": int64(1)},
			"implementation_notes": map[string]any{"i": int64(1)},
			"delegation_triggers":  map[string]any{"d": int64(1)},
			"inheritance_disabled": true,
			"force_local_only":     true,
		},
	}
}

func TestTaskContextRepoCRUD(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := tmvo.NewUUIDv4()
	repo := taskCtxRepoTestNew(t, sessions, &user)
	taskID, branchID := taskCtxRepoTestSetup(t, sessions, user)

	created, err := repo.Create(ctx, taskCtxRepoTestEntity(taskID, branchID))
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID != taskID || created.BranchID != branchID {
		t.Fatalf("created = %+v", created)
	}
	if created.Progress != 10 {
		t.Fatalf("progress = %d", created.Progress)
	}
	if len(created.Insights) != 1 || len(created.NextSteps) != 1 {
		t.Fatalf("insights/next_steps = %+v / %+v", created.Insights, created.NextSteps)
	}
	if created.TaskData["title"] != "work" {
		t.Fatalf("task_data = %+v", created.TaskData)
	}
	for _, k := range []string{"progress", "insights", "next_steps"} {
		if _, ok := created.TaskData[k]; ok {
			t.Fatalf("task_data still contains %q", k)
		}
	}
	if v, ok := created.Metadata["inheritance_disabled"].(*bool); !ok || v == nil || !*v {
		t.Fatalf("inheritance_disabled = %+v", created.Metadata["inheritance_disabled"])
	}
	if v, ok := created.Metadata["version"].(*int64); !ok || v == nil || *v != 1 {
		t.Fatalf("version = %+v", created.Metadata["version"])
	}

	if _, err := repo.Create(ctx, taskCtxRepoTestEntity(taskID, branchID)); err == nil {
		t.Fatal("duplicate Create must fail")
	}

	got, err := repo.Get(ctx, taskID)
	if err != nil || got == nil || got.ID != taskID {
		t.Fatalf("Get = %+v, %v", got, err)
	}
	if missing, _ := repo.Get(ctx, tmvo.NewUUIDv4()); missing != nil {
		t.Fatalf("Get(missing) = %+v", missing)
	}

	updatedEntity := taskCtxRepoTestEntity(taskID, branchID)
	updatedEntity.TaskData = map[string]any{"title": "work2"}
	updatedEntity.Progress = 50
	updated, err := repo.Update(ctx, taskID, updatedEntity)
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.Progress != 50 || updated.TaskData["title"] != "work2" {
		t.Fatalf("updated = %+v", updated)
	}
	if v, ok := updated.Metadata["version"].(*int64); !ok || v == nil || *v != 2 {
		t.Fatalf("version after update = %+v", updated.Metadata["version"])
	}
	if _, err := repo.Update(ctx, tmvo.NewUUIDv4(), updatedEntity); err == nil {
		t.Fatal("Update of missing context must fail")
	}

	list, err := repo.List(ctx, NewKwargs("branch_id", branchID))
	if err != nil || len(list) != 1 {
		t.Fatalf("List(branch_id) = %d, %v", len(list), err)
	}
	if none, err := repo.List(ctx, NewKwargs("branch_id", tmvo.NewUUIDv4())); err != nil || len(none) != 0 {
		t.Fatalf("List(other) = %d, %v", len(none), err)
	}
	if enabled, err := repo.List(ctx, NewKwargs("inheritance_disabled", true)); err != nil || len(enabled) != 1 {
		t.Fatalf("List(inheritance_disabled=true) = %d, %v", len(enabled), err)
	}
	if disabled, err := repo.List(ctx, NewKwargs("inheritance_disabled", false)); err != nil || len(disabled) != 0 {
		t.Fatalf("List(inheritance_disabled=false) = %d, %v", len(disabled), err)
	}

	deleted, err := repo.Delete(ctx, taskID)
	if err != nil || !deleted {
		t.Fatalf("Delete = %v, %v", deleted, err)
	}
	if deleted, _ := repo.Delete(ctx, taskID); deleted {
		t.Fatal("second Delete should be false")
	}
}

func TestTaskContextRepoUserIsolationAndErrors(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	userA, userB := tmvo.NewUUIDv4(), tmvo.NewUUIDv4()
	repoA := taskCtxRepoTestNew(t, sessions, &userA)
	repoB := taskCtxRepoTestNew(t, sessions, &userB)
	taskA, branchA := taskCtxRepoTestSetup(t, sessions, userA)
	taskB, branchB := taskCtxRepoTestSetup(t, sessions, userB)

	if _, err := repoA.Create(ctx, taskCtxRepoTestEntity(taskA, branchA)); err != nil {
		t.Fatal(err)
	}
	if _, err := repoB.Create(ctx, taskCtxRepoTestEntity(taskB, branchB)); err != nil {
		t.Fatal(err)
	}
	if got, _ := repoA.Get(ctx, taskB); got != nil {
		t.Fatal("user A must not read user B's task context")
	}
	if list, _ := repoA.List(ctx, nil); len(list) != 1 || list[0].ID != taskA {
		t.Fatalf("repoA list = %+v", list)
	}

	// A repository without a user and an entity without metadata.user_id is rejected.
	anon := taskCtxRepoTestNew(t, sessions, nil)
	if _, err := anon.Create(ctx, taskCtxRepoTestEntity(tmvo.NewUUIDv4(), branchA)); err == nil {
		t.Fatal("Create without user_id must fail")
	}
}
