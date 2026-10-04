package repositories

import (
	"context"
	"errors"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type subtaskRepoFixture struct {
	sm     *database.SessionManager
	userID string
	parent value_objects.TaskId
}

// newSubtaskRepoFixture builds an isolated database and the project/branch/task chain the
// subtasks need for their foreign keys.
func newSubtaskRepoFixture(t *testing.T) *subtaskRepoFixture {
	t.Helper()
	sm := newTestRepoEnv(t)
	ctx := context.Background()
	userID := value_objects.NewUUIDv4()
	projectID := value_objects.NewUUIDv4()
	branchID := value_objects.NewUUIDv4()
	taskID := value_objects.NewUUIDv4()

	projects, err := NewORMRepository[database.Project]("projects", sm)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := projects.Create(ctx, NewKwargs("id", projectID, "name", "p", "user_id", userID)); err != nil {
		t.Fatal(err)
	}
	branches, err := NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sm)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := branches.Create(ctx, NewKwargs("id", branchID, "project_id", projectID, "name", "main", "user_id", userID)); err != nil {
		t.Fatal(err)
	}
	tasks, err := NewORMRepository[database.Task]("tasks", sm)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := tasks.Create(ctx, NewKwargs("id", taskID, "title", "t", "description", "d", "git_branch_id", branchID, "user_id", userID)); err != nil {
		t.Fatal(err)
	}
	parent, err := value_objects.NewTaskId(taskID)
	if err != nil {
		t.Fatal(err)
	}
	return &subtaskRepoFixture{sm: sm, userID: userID, parent: parent}
}

func subtaskRepoNewEntity(t *testing.T, parent value_objects.TaskId, title, status string, progress int, assignees []string) *entities.Subtask {
	t.Helper()
	ts, err := value_objects.TaskStatusFromString(status)
	if err != nil {
		t.Fatal(err)
	}
	priority := value_objects.PriorityMedium()
	st := entities.Subtask{
		Title: title, ParentTaskID: &parent, Status: &ts, Priority: &priority,
		Assignees: assignees, ProgressPercentage: progress,
	}
	entity, err := entities.NewSubtask(st)
	if err != nil {
		t.Fatal(err)
	}
	return entity
}

func subtaskRepoMustSave(t *testing.T, repo *ORMSubtaskRepository, entity *entities.Subtask) {
	t.Helper()
	ok, err := repo.Save(context.Background(), entity)
	if err != nil || !ok {
		t.Fatalf("save: ok=%v err=%v", ok, err)
	}
}

func subtaskRepoNewRepo(t *testing.T, fx *subtaskRepoFixture, userID string) *ORMSubtaskRepository {
	t.Helper()
	repo, err := NewORMSubtaskRepository(fx.sm, &userID)
	if err != nil {
		t.Fatal(err)
	}
	return repo
}

func TestSubtaskRepositorySaveFindByIDAndIsolation(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)

	entity := subtaskRepoNewEntity(t, fx.parent, "first", "todo", 0, []string{"coding-agent"})
	if entity.ID != nil {
		t.Fatal("expected a generated id to be absent before save")
	}
	ok, err := repo.Save(ctx, entity)
	if err != nil || !ok {
		t.Fatalf("save: ok=%v err=%v", ok, err)
	}
	if entity.ID == nil || entity.CreatedAt == nil || entity.UpdatedAt == nil {
		t.Fatalf("save did not populate id/timestamps: %+v", entity)
	}

	got, err := repo.FindByID(ctx, entity.ID.Value)
	if err != nil || got == nil {
		t.Fatalf("find: %v %+v", err, got)
	}
	if got.Title != "first" || got.Status.Value != "todo" || got.Priority.Value != "medium" || got.ProgressPercentage != 0 {
		t.Fatalf("round trip mismatch: %+v", got)
	}
	if !reflect.DeepEqual(got.Assignees, entity.Assignees) {
		t.Fatalf("assignees %v vs %v", got.Assignees, entity.Assignees)
	}

	other := value_objects.NewUUIDv4()
	repo2 := subtaskRepoNewRepo(t, fx, other)
	if row, _ := repo2.FindByID(ctx, entity.ID.Value); row != nil {
		t.Fatal("user isolation broken")
	}
	if row, _ := repo.FindByID(ctx, value_objects.NewUUIDv4()); row != nil {
		t.Fatal("expected not-found nil")
	}
}

func TestSubtaskRepositorySaveUpdateBranch(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)

	entity := subtaskRepoNewEntity(t, fx.parent, "before", "todo", 0, nil)
	id := value_objects.GenerateNewTaskId()
	entity.ID = &id
	subtaskRepoMustSave(t, repo, entity)
	before := *entity.UpdatedAt
	time.Sleep(2 * time.Millisecond)

	entity.Title = "after"
	ok, err := repo.Save(ctx, entity)
	if err != nil || !ok {
		t.Fatalf("update save: %v %v", ok, err)
	}
	if !entity.UpdatedAt.After(before) {
		t.Fatal("updated_at was not refreshed")
	}
	got, _ := repo.FindByID(ctx, id.Value)
	if got == nil || got.Title != "after" {
		t.Fatalf("update not persisted: %+v", got)
	}
}

func TestSubtaskRepositoryFindByParentTaskIDOrderingAndIsolation(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)

	base := time.Now().UTC().Add(-4 * time.Hour)
	for i, title := range []string{"oldest", "middle", "newest"} {
		entity := subtaskRepoNewEntity(t, fx.parent, title, "todo", 0, nil)
		ts := base.Add(time.Duration(i) * time.Hour)
		entity.CreatedAt = &ts
		entity.UpdatedAt = &ts
		subtaskRepoMustSave(t, repo, entity)
	}
	// Another user's subtask under the same parent must not leak into the result.
	other := value_objects.NewUUIDv4()
	repo2 := subtaskRepoNewRepo(t, fx, other)
	foreign := subtaskRepoNewEntity(t, fx.parent, "foreign", "todo", 0, nil)
	subtaskRepoMustSave(t, repo2, foreign)

	rows, err := repo.FindByParentTaskID(ctx, fx.parent)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 3 {
		t.Fatalf("expected 3, got %d", len(rows))
	}
	for i, want := range []string{"oldest", "middle", "newest"} {
		if rows[i].Title != want {
			t.Fatalf("order[%d]=%q want %q", i, rows[i].Title, want)
		}
	}
	if empty, _ := repo.FindByParentTaskID(ctx, value_objects.GenerateNewTaskId()); len(empty) != 0 {
		t.Fatalf("expected empty, got %d", len(empty))
	}
}

func TestSubtaskRepositoryFindByStatusCompletedPending(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)

	base := time.Now().UTC().Add(-4 * time.Hour)
	specs := []struct {
		title, status string
		progress      int
	}{
		{"todo", "todo", 0},
		{"running", "in_progress", 50},
		{"blocked", "blocked", 10},
		{"done", "done", 100},
	}
	for i, spec := range specs {
		entity := subtaskRepoNewEntity(t, fx.parent, spec.title, spec.status, spec.progress, nil)
		ts := base.Add(time.Duration(i) * time.Hour)
		entity.CreatedAt = &ts
		entity.UpdatedAt = &ts
		subtaskRepoMustSave(t, repo, entity)
	}
	todos, err := repo.FindByStatus(ctx, "todo")
	if err != nil || len(todos) != 1 || todos[0].Title != "todo" {
		t.Fatalf("FindByStatus: %v %d", err, len(todos))
	}
	completed, err := repo.FindCompleted(ctx, fx.parent)
	if err != nil || len(completed) != 1 || completed[0].Title != "done" {
		t.Fatalf("FindCompleted: %v %d", err, len(completed))
	}
	pending, err := repo.FindPending(ctx, fx.parent)
	if err != nil || len(pending) != 3 {
		t.Fatalf("FindPending: %v %d", err, len(pending))
	}
	for i, want := range []string{"todo", "running", "blocked"} {
		if pending[i].Title != want {
			t.Fatalf("pending order[%d]=%q want %q", i, pending[i].Title, want)
		}
	}
}

func TestSubtaskRepositoryDeleteAndExists(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)

	entity := subtaskRepoNewEntity(t, fx.parent, "doomed", "todo", 0, nil)
	subtaskRepoMustSave(t, repo, entity)

	if exists, err := repo.Exists(ctx, entity.ID.Value); err != nil || !exists {
		t.Fatalf("exists: %v %v", exists, err)
	}
	if exists, _ := repo.Exists(ctx, value_objects.NewUUIDv4()); exists {
		t.Fatal("exists on missing id")
	}
	other := value_objects.NewUUIDv4()
	repo2 := subtaskRepoNewRepo(t, fx, other)
	if exists, _ := repo2.Exists(ctx, entity.ID.Value); exists {
		t.Fatal("cross-user exists")
	}
	if deleted, _ := repo2.Delete(ctx, entity.ID.Value); deleted {
		t.Fatal("cross-user delete must be a no-op")
	}
	if deleted, err := repo.Delete(ctx, entity.ID.Value); err != nil || !deleted {
		t.Fatalf("delete: %v %v", deleted, err)
	}
	if deleted, _ := repo.Delete(ctx, entity.ID.Value); deleted {
		t.Fatal("second delete must report false")
	}
}

func TestSubtaskRepositoryDeleteByParentTaskID(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)
	for _, title := range []string{"a", "b", "c"} {
		entity := subtaskRepoNewEntity(t, fx.parent, title, "todo", 0, nil)
		subtaskRepoMustSave(t, repo, entity)
	}
	if deleted, err := repo.DeleteByParentTaskID(ctx, fx.parent); err != nil || !deleted {
		t.Fatalf("delete by parent: %v %v", deleted, err)
	}
	if n, _ := repo.CountByParentTaskID(ctx, fx.parent); n != 0 {
		t.Fatalf("expected 0 after delete, got %d", n)
	}
	if deleted, _ := repo.DeleteByParentTaskID(ctx, fx.parent); deleted {
		t.Fatal("second delete must report false")
	}
}

func TestSubtaskRepositoryCountsHaveNoUserFilter(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)
	other := value_objects.NewUUIDv4()
	repo2 := subtaskRepoNewRepo(t, fx, other)

	subtaskRepoMustSave(t, repo, subtaskRepoNewEntity(t, fx.parent, "mine-1", "todo", 0, nil))
	subtaskRepoMustSave(t, repo, subtaskRepoNewEntity(t, fx.parent, "mine-2", "done", 100, nil))
	subtaskRepoMustSave(t, repo2, subtaskRepoNewEntity(t, fx.parent, "other-done", "done", 100, nil))

	if n, err := repo.CountByParentTaskID(ctx, fx.parent); err != nil || n != 3 {
		t.Fatalf("count: %v %d", err, n)
	}
	if n, err := repo.CountCompletedByParentTaskID(ctx, fx.parent); err != nil || n != 2 {
		t.Fatalf("count completed: %v %d", err, n)
	}
	// A different user's repository still counts every user's rows (no user filter).
	if n, _ := repo2.CountByParentTaskID(ctx, fx.parent); n != 3 {
		t.Fatalf("other user count %d", n)
	}
}

func TestSubtaskRepositoryAssigneeQueriesReproducePythonJsonLikeDefect(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)
	subtaskRepoMustSave(t, repo, subtaskRepoNewEntity(t, fx.parent, "assigned", "todo", 0, []string{"coding-agent"}))

	if _, err := repo.FindByAssignee(ctx, "coding-agent"); err == nil {
		t.Fatal("expected the PostgreSQL json LIKE error that Python also raises")
	}
	limit := 5
	if _, err := repo.GetSubtasksByAssignee(ctx, "coding-agent", &limit); err == nil {
		t.Fatal("expected the PostgreSQL json LIKE error that Python also raises")
	}
}

func TestSubtaskRepositoryGetSubtaskProgress(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)
	specs := []struct {
		title, status string
		progress      int
	}{
		{"done", "done", 100},
		{"running", "in_progress", 50},
		{"blocked", "blocked", 25},
		{"todo", "todo", 0},
	}
	for _, spec := range specs {
		subtaskRepoMustSave(t, repo, subtaskRepoNewEntity(t, fx.parent, spec.title, spec.status, spec.progress, nil))
	}
	progress, err := repo.GetSubtaskProgress(ctx, fx.parent)
	if err != nil {
		t.Fatal(err)
	}
	if progress["total_subtasks"] != 4 || progress["completed_subtasks"] != 1 ||
		progress["in_progress_subtasks"] != 1 || progress["blocked_subtasks"] != 1 ||
		progress["pending_subtasks"] != 1 {
		t.Fatalf("counts: %+v", progress)
	}
	if progress["completion_percentage"] != 25.0 {
		t.Fatalf("completion %v", progress["completion_percentage"])
	}
	if progress["average_progress"] != 43.8 {
		t.Fatalf("average %v", progress["average_progress"])
	}
	if progress["has_blockers"] != true {
		t.Fatalf("has_blockers %v", progress["has_blockers"])
	}

	empty, err := repo.GetSubtaskProgress(ctx, value_objects.GenerateNewTaskId())
	if err != nil {
		t.Fatal(err)
	}
	if empty["total_subtasks"] != 0 || empty["completion_percentage"] != 0 || empty["average_progress"] != 0.0 {
		t.Fatalf("empty progress: %+v", empty)
	}
}

func TestSubtaskRepositoryBulkRemoveProgressComplete(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)
	first := subtaskRepoNewEntity(t, fx.parent, "first", "todo", 0, nil)
	subtaskRepoMustSave(t, repo, first)
	second := subtaskRepoNewEntity(t, fx.parent, "second", "todo", 0, nil)
	subtaskRepoMustSave(t, repo, second)

	if updated, err := repo.BulkUpdateStatus(ctx, fx.parent, "done"); err != nil || !updated {
		t.Fatalf("bulk update done: %v %v", updated, err)
	}
	rows, _ := repo.FindByParentTaskID(ctx, fx.parent)
	for _, row := range rows {
		if row.Status.Value != "done" || row.ProgressPercentage != 100 {
			t.Fatalf("bulk update not applied: %+v", row)
		}
	}
	// status done sets completed_at via the SQL NULL branch only for todo/in_progress/blocked.
	if updated, err := repo.BulkUpdateStatus(ctx, fx.parent, "blocked"); err != nil || !updated {
		t.Fatalf("bulk update blocked: %v %v", updated, err)
	}
	row, _ := repo.GetByID(ctx, first.ID.Value)
	if row == nil || row.Status != "blocked" || row.CompletedAt != nil {
		t.Fatalf("blocked row: %+v", row)
	}
	if completed, err := repo.BulkComplete(ctx, fx.parent); err != nil || !completed {
		t.Fatalf("bulk complete: %v %v", completed, err)
	}
	if removed, err := repo.RemoveSubtask(ctx, fx.parent.Value, second.ID.Value); err != nil || !removed {
		t.Fatalf("remove: %v %v", removed, err)
	}
	if removed, _ := repo.RemoveSubtask(ctx, fx.parent.Value, second.ID.Value); removed {
		t.Fatal("second remove must report false")
	}

	if updated, err := repo.UpdateProgress(ctx, first.ID.Value, 150, "notes"); err != nil || !updated {
		t.Fatalf("update progress: %v %v", updated, err)
	}
	if row, _ := repo.GetByID(ctx, first.ID.Value); row.ProgressNotes != "notes" || row.ProgressPercentage != 100 {
		t.Fatalf("progress clamp high: %+v", row)
	}
	if updated, _ := repo.UpdateProgress(ctx, first.ID.Value, -5, "low"); !updated {
		t.Fatal("update progress negative")
	}
	if row, _ := repo.GetByID(ctx, first.ID.Value); row.ProgressPercentage != 0 {
		t.Fatalf("progress clamp low: %+v", row)
	}
	other := value_objects.NewUUIDv4()
	repo2 := subtaskRepoNewRepo(t, fx, other)
	if updated, _ := repo2.UpdateProgress(ctx, first.ID.Value, 10, "evil"); updated {
		t.Fatal("cross-user progress update")
	}

	if completed, err := repo.CompleteSubtask(ctx, first.ID.Value, "summary", "impact", []string{"insight"}); err != nil || !completed {
		t.Fatalf("complete subtask: %v %v", completed, err)
	}
	completedRow, _ := repo.GetByID(ctx, first.ID.Value)
	if completedRow.Status != "done" || completedRow.ProgressPercentage != 100 ||
		completedRow.CompletionSummary != "summary" || completedRow.ImpactOnParent != "impact" {
		t.Fatalf("complete row: %+v", completedRow)
	}
	if string(completedRow.InsightsFound) != `["insight"]` {
		t.Fatalf("insights: %s", completedRow.InsightsFound)
	}
	if completed, _ := repo2.CompleteSubtask(ctx, first.ID.Value, "x", "y", nil); completed {
		t.Fatal("cross-user complete")
	}
}

func TestSubtaskRepositoryGetNextID(t *testing.T) {
	repo := &ORMSubtaskRepository{}
	id, err := repo.GetNextID(context.Background(), value_objects.GenerateNewTaskId())
	if err != nil {
		t.Fatal(err)
	}
	if id.Value == "" {
		t.Fatal("expected a generated id")
	}
}

func TestSubtaskRepositorySaveWithoutUserRaisesValueErrorInsideSaveOnce(t *testing.T) {
	// Python raises ValueError inside the transaction, which its save swallows after ten
	// retries and reports as False. The full backoff is skipped here; only the inner error is
	// asserted (the retry loop itself is exercised by the successful paths).
	fx := newSubtaskRepoFixture(t)
	repo, err := NewORMSubtaskRepository(fx.sm, nil)
	if err != nil {
		t.Fatal(err)
	}
	entity := subtaskRepoNewEntity(t, fx.parent, "no-user", "todo", 0, nil)
	_, err = repo.subtaskRepoSaveOnce(context.Background(), entity)
	var ve *ValueError
	if !errors.As(err, &ve) {
		t.Fatalf("expected ValueError, got %T %v", err, err)
	}
}

// A row stored under an older assignee rule (a bare name that is no role) must still
// load, alone and in a list: one such row must not fail every list that contains it.
func TestSubtaskRepositoryLoadsAStoredBareAssigneeName(t *testing.T) {
	fx := newSubtaskRepoFixture(t)
	ctx := context.Background()
	repo := subtaskRepoNewRepo(t, fx, fx.userID)

	legacy, err := entities.RestoreSubtask(entities.Subtask{Title: "legacy", ParentTaskID: &fx.parent, Assignees: []string{"go-dev"}})
	if err != nil {
		t.Fatal(err)
	}
	subtaskRepoMustSave(t, repo, legacy)
	subtaskRepoMustSave(t, repo, subtaskRepoNewEntity(t, fx.parent, "current", "todo", 0, []string{"@lead"}))

	got, err := repo.FindByID(ctx, legacy.ID.Value)
	if err != nil || got == nil {
		t.Fatalf("find legacy row: %v %v", err, got)
	}
	if !reflect.DeepEqual(got.Assignees, []string{"go-dev"}) {
		t.Fatalf("assignees = %v, want the stored [go-dev] untouched", got.Assignees)
	}
	rows, err := repo.FindByParentTaskID(ctx, fx.parent)
	if err != nil || len(rows) != 2 {
		t.Fatalf("list with a legacy row: %v, %d rows, want 2", err, len(rows))
	}
}
