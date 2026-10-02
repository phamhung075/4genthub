package repositories

// Tests for the ported ORMTaskRepository against a real PostgreSQL instance
// (AGENTHUB_TEST_PG_URL), using newTestRepoEnv.

import (
	"context"
	"errors"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	taskRepoTestUserA = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
	taskRepoTestUserB = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
)

func taskRepoTestBranch(t *testing.T, sessions *database.SessionManager, userID string) string {
	t.Helper()
	ctx := context.Background()
	projectID := tmvo.NewUUIDv4()
	projects, err := NewORMRepository[database.Project]("projects", sessions)
	if err != nil {
		t.Fatalf("project repo: %v", err)
	}
	if _, err := projects.Create(ctx, NewKwargs(
		"id", projectID, "name", "Project", "description", "d", "user_id", userID, "status", "active")); err != nil {
		t.Fatalf("create project: %v", err)
	}
	branchID := tmvo.NewUUIDv4()
	branches, err := NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		t.Fatalf("branch repo: %v", err)
	}
	if _, err := branches.Create(ctx, NewKwargs(
		"id", branchID, "project_id", projectID, "name", "Branch", "description", "d",
		"user_id", userID, "priority", "medium", "status", "active")); err != nil {
		t.Fatalf("create branch: %v", err)
	}
	return branchID
}

func taskRepoTestNewRepo(t *testing.T, sessions *database.SessionManager, userID, branchID string, performance bool) *ORMTaskRepository {
	t.Helper()
	repo, err := NewORMTaskRepository(sessions, &branchID, nil, nil, &userID, performance)
	if err != nil {
		t.Fatalf("NewORMTaskRepository: %v", err)
	}
	return repo
}

func taskRepoTestBranchCounts(t *testing.T, sessions *database.SessionManager, branchID string) (int64, int64) {
	t.Helper()
	branches, err := NewORMRepository[database.ProjectGitBranch]("project_git_branchs", sessions)
	if err != nil {
		t.Fatalf("branch repo: %v", err)
	}
	row, err := branches.GetByID(context.Background(), branchID)
	if err != nil || row == nil {
		t.Fatalf("branch get: %v %v", err, row)
	}
	return row.TaskCount, row.CompletedTaskCount
}

func TestTaskRepoCreateAndGet(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	task, err := repo.CreateTask(ctx, "Title", "Desc", "high", []string{"agent-1"}, []string{"backend"}, nil)
	if err != nil {
		t.Fatalf("CreateTask: %v", err)
	}
	if task.Title != "Title" || task.Description != "Desc" || task.Priority.Value != "high" {
		t.Fatalf("unexpected task: %+v", task)
	}
	if len(task.Assignees) != 1 || task.Assignees[0] != "agent-1" {
		t.Fatalf("assignees: %#v", task.Assignees)
	}
	if len(task.Labels) != 1 || task.Labels[0] != "backend" {
		t.Fatalf("labels: %#v", task.Labels)
	}
	tc, cc := taskRepoTestBranchCounts(t, sessions, branchID)
	if tc != 1 || cc != 0 {
		t.Fatalf("branch counts = %d,%d", tc, cc)
	}

	got, err := repo.GetTask(ctx, task.ID.Value)
	if err != nil || got == nil {
		t.Fatalf("GetTask: %v %v", err, got)
	}
	if got.Title != "Title" || len(got.Assignees) != 1 || len(got.Labels) != 1 {
		t.Fatalf("got: %+v", got)
	}
}

func TestTaskRepoUserIsolation(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchA := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repoA := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchA, false)
	task, err := repoA.CreateTask(ctx, "Secret", "Desc", "medium", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	repoB := taskRepoTestNewRepo(t, sessions, taskRepoTestUserB, branchA, false)
	got, err := repoB.GetTask(ctx, task.ID.Value)
	if err != nil {
		t.Fatalf("GetTask B: %v", err)
	}
	if got != nil {
		t.Fatalf("user B saw task: %+v", got)
	}
}

func TestTaskRepoNotFoundAndExists(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	missing := tmvo.NewUUIDv4()
	got, err := repo.GetTask(ctx, missing)
	if err != nil || got != nil {
		t.Fatalf("GetTask missing: %v %v", err, got)
	}
	id, _ := tmvo.NewTaskId(missing)
	ok, err := repo.Exists(ctx, id)
	if err != nil || ok {
		t.Fatalf("Exists missing: %v %v", err, ok)
	}
	deleted, err := repo.Delete(ctx, id)
	if err != nil || deleted {
		t.Fatalf("Delete missing: %v %v", err, deleted)
	}
	next, err := repo.GetNextID(ctx)
	if err != nil || next.Value == "" {
		t.Fatalf("GetNextID: %v %v", err, next)
	}
}

func TestTaskRepoListOrderingPagination(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	for i := 0; i < 3; i++ {
		if _, err := repo.CreateTask(ctx, "T"+string(rune('0'+i)), "D", "medium", nil, nil, nil); err != nil {
			t.Fatal(err)
		}
		time.Sleep(2 * time.Millisecond)
	}
	all, err := repo.ListTasks(ctx, nil, nil, nil, 100, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Fatalf("list len = %d", len(all))
	}
	if all[0].Title != "T2" || all[2].Title != "T0" {
		t.Fatalf("ordering: %s %s", all[0].Title, all[2].Title)
	}
	page, err := repo.ListTasks(ctx, nil, nil, nil, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	if len(page) != 1 || page[0].Title != "T1" {
		t.Fatalf("pagination: %#v", page)
	}
}

func TestTaskRepoFindByStatusPriorityAssignee(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	if _, err := repo.CreateTask(ctx, "A", "D", "high", []string{"agent-x"}, nil, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateTask(ctx, "B", "D", "low", nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	high := tmvo.PriorityHigh()
	byPriority, err := repo.FindByPriority(ctx, high)
	if err != nil || len(byPriority) != 1 || byPriority[0].Title != "A" {
		t.Fatalf("FindByPriority: %v %#v", err, byPriority)
	}
	byAssignee, err := repo.FindByAssignee(ctx, "agent-x")
	if err != nil || len(byAssignee) != 1 || byAssignee[0].Title != "A" {
		t.Fatalf("FindByAssignee: %v %#v", err, byAssignee)
	}
	byStatus, err := repo.FindByStatus(ctx, tmvo.TaskStatus{Value: "todo"})
	if err != nil || len(byStatus) != 2 {
		t.Fatalf("FindByStatus: %v %d", err, len(byStatus))
	}
	empty, err := repo.FindByLabels(ctx, []string{"nope"})
	if err != nil || len(empty) != 0 {
		t.Fatalf("FindByLabels: %v %d", err, len(empty))
	}
}

func TestTaskRepoSearch(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	if _, err := repo.CreateTask(ctx, "Authentication JWT handling", "auth desc", "medium", nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateTask(ctx, "Database migration", "migration desc", "medium", nil, []string{"backend"}, nil); err != nil {
		t.Fatal(err)
	}
	byWord, err := repo.Search(ctx, "JWT", 10)
	if err != nil || len(byWord) != 1 || byWord[0].Title != "Authentication JWT handling" {
		t.Fatalf("Search JWT: %v %#v", err, byWord)
	}
	byLabel, err := repo.Search(ctx, "backend", 10)
	if err != nil || len(byLabel) != 1 || byLabel[0].Title != "Database migration" {
		t.Fatalf("Search label: %v %#v", err, byLabel)
	}
	empty, err := repo.SearchTasks(ctx, "   ", 10)
	if err != nil || len(empty) != 0 {
		t.Fatalf("Search empty: %v %d", err, len(empty))
	}
}

func TestTaskRepoFindByCriteria(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	if _, err := repo.CreateTask(ctx, "A", "D", "high", []string{"agent-x"}, []string{"backend"}, nil); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateTask(ctx, "B", "D", "low", nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	limit := 10
	byAssignee, err := repo.FindByCriteria(ctx, map[string]any{"assignees": []string{"agent-x"}}, &limit)
	if err != nil || len(byAssignee) != 1 || byAssignee[0].Title != "A" {
		t.Fatalf("criteria assignees: %v %#v", err, byAssignee)
	}
	byLabel, err := repo.FindByCriteria(ctx, map[string]any{"labels": []string{"backend"}}, &limit)
	if err != nil || len(byLabel) != 1 || byLabel[0].Title != "A" {
		t.Fatalf("criteria labels: %v %#v", err, byLabel)
	}
	byStatus, err := repo.FindByCriteria(ctx, map[string]any{"status": "low-status"}, &limit)
	if err != nil || len(byStatus) != 0 {
		t.Fatalf("criteria status: %v %d", err, len(byStatus))
	}
}

func TestTaskRepoSaveInsertAndUpdate(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	id := tmvo.GenerateNewTaskId()
	branch := branchID
	task, err := entities.NewTask(entities.Task{
		ID: &id, Title: "Saved", Description: "D", GitBranchID: &branch,
		Assignees: []string{"agent-1"}, Labels: []string{"l1"},
	})
	if err != nil {
		t.Fatal(err)
	}
	saved, err := repo.Save(ctx, task)
	if err != nil {
		t.Fatalf("Save insert: %v", err)
	}
	if saved.CreatedAt == nil || saved.UpdatedAt == nil {
		t.Fatalf("timestamps not synced: %+v", saved)
	}
	depID := tmvo.GenerateNewTaskId()
	// create dependency target row directly
	tasks, _ := NewORMRepository[database.Task]("tasks", sessions)
	if _, err := tasks.Create(ctx, NewKwargs("id", depID.Value, "title", "Dep", "description", "D",
		"git_branch_id", branchID, "status", "todo", "priority", "medium", "user_id", taskRepoTestUserA)); err != nil {
		t.Fatal(err)
	}

	task.Title = "Saved2"
	task.Dependencies = []tmvo.TaskId{depID}
	task.Labels = []string{"l1", "l2"}
	if _, err := repo.Save(ctx, task); err != nil {
		t.Fatalf("Save update: %v", err)
	}
	got, err := repo.GetTask(ctx, id.Value)
	if err != nil || got == nil {
		t.Fatalf("get after save: %v %v", err, got)
	}
	if got.Title != "Saved2" {
		t.Fatalf("title = %s", got.Title)
	}
	if len(got.Dependencies) != 1 || got.Dependencies[0].Value != depID.Value {
		t.Fatalf("dependencies: %#v", got.Dependencies)
	}
	if len(got.Labels) != 2 {
		t.Fatalf("labels: %#v", got.Labels)
	}
	if len(got.Assignees) != 1 {
		t.Fatalf("assignees: %#v", got.Assignees)
	}
}

func TestTaskRepoUpdateTaskDefect(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	task, err := repo.CreateTask(ctx, "T", "D", "medium", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	_, err = repo.UpdateTask(ctx, task.ID.Value, NewKwargs("title", "New"))
	var updateErr *exceptions.TaskUpdateError
	if !errors.As(err, &updateErr) {
		t.Fatalf("expected TaskUpdateError, got %v", err)
	}
	_, err = repo.UpdateTask(ctx, tmvo.NewUUIDv4(), NewKwargs("title", "New"))
	if !errors.As(err, &updateErr) {
		t.Fatalf("expected TaskUpdateError for missing, got %v", err)
	}
}

func TestTaskRepoDeleteCascade(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	task, err := repo.CreateTask(ctx, "T", "D", "medium", []string{"agent-1"}, []string{"l1"}, nil)
	if err != nil {
		t.Fatal(err)
	}
	// insert a task context row
	taskContexts, _ := NewORMRepository[database.TaskContext]("task_contexts", sessions)
	if _, err := taskContexts.Create(ctx, NewKwargs("id", tmvo.NewUUIDv4(), "task_id", task.ID.Value, "user_id", taskRepoTestUserA)); err != nil {
		t.Fatal(err)
	}
	id, _ := tmvo.NewTaskId(task.ID.Value)
	deleted, err := repo.Delete(ctx, id)
	if err != nil || !deleted {
		t.Fatalf("Delete: %v %v", err, deleted)
	}
	got, _ := repo.GetTask(ctx, task.ID.Value)
	if got != nil {
		t.Fatalf("task still present")
	}
	tc, cc := taskRepoTestBranchCounts(t, sessions, branchID)
	if tc != 0 || cc != 0 {
		t.Fatalf("branch counts after delete = %d,%d", tc, cc)
	}
}

func TestTaskRepoCountStatistics(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	if _, err := repo.CreateTask(ctx, "A", "D", "medium", nil, nil, NewKwargs("status", "done")); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateTask(ctx, "B", "D", "medium", nil, nil, NewKwargs("status", "in_progress")); err != nil {
		t.Fatal(err)
	}
	count, err := repo.Count(ctx)
	if err != nil || count != 2 {
		t.Fatalf("Count: %v %d", err, count)
	}
	stats, err := repo.GetStatistics(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats["total_tasks"] != 2 || stats["in_progress_tasks"] != 1 || stats["todo_tasks"] != 0 {
		t.Fatalf("stats: %#v", stats)
	}
	done, err := repo.GetTaskCountOptimized(ctx, taskRepoStrPtr("done"), nil)
	if err != nil || done != 1 {
		t.Fatalf("count optimized: %v %d", err, done)
	}
	repo.PerformanceMode = true
	tc, err := repo.GetTaskCount(ctx, taskRepoStrPtr("done"))
	if err != nil || tc != 1 {
		t.Fatalf("task count done: %v %d", err, tc)
	}
}

func TestTaskRepoListMinimalAndBatch(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	task, err := repo.CreateTask(ctx, "Min", "D", "high", []string{"agent-1", "agent-2"}, []string{"l1"}, nil)
	if err != nil {
		t.Fatal(err)
	}
	rows, err := repo.ListTasksMinimal(ctx, nil, nil, nil, nil, nil, nil)
	if err != nil || len(rows) != 1 {
		t.Fatalf("ListTasksMinimal: %v %d", err, len(rows))
	}
	if rows[0].Len() < 15 {
		t.Fatalf("minimal keys = %d", rows[0].Len())
	}
	got, _ := rows[0].Get("id")
	if got != task.ID.Value {
		t.Fatalf("minimal id = %v", got)
	}
	deps, _ := rows[0].Get("has_dependencies")
	if deps != false {
		t.Fatalf("has_dependencies = %v", deps)
	}
	if _, ok := rows[0].Get("assignees"); ok {
		t.Fatalf("assignees must be omitted without performance mode")
	}
	n, err := repo.BatchUpdateStatus(ctx, []string{task.ID.Value}, "done")
	if err != nil || n != 1 {
		t.Fatalf("BatchUpdateStatus: %v %d", err, n)
	}
	gotTask, _ := repo.GetTask(ctx, task.ID.Value)
	if gotTask.Status.Value != "done" {
		t.Fatalf("status = %s", gotTask.Status.Value)
	}
}

func TestTaskRepoFindByIDAllStatesAndGitBranch(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	task, err := repo.CreateTask(ctx, "T", "D", "medium", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	id, _ := tmvo.NewTaskId(task.ID.Value)
	all, err := repo.FindByIDAllStates(ctx, id)
	if err != nil || all == nil || all.Title != "T" {
		t.Fatalf("FindByIDAllStates: %v %v", err, all)
	}
	exists, err := repo.GitBranchExists(ctx, branchID)
	if err != nil || !exists {
		t.Fatalf("GitBranchExists: %v %v", err, exists)
	}
	byBranch, err := repo.FindByGitBranchID(ctx, branchID)
	if err != nil || len(byBranch) != 1 {
		t.Fatalf("FindByGitBranchID: %v %d", err, len(byBranch))
	}
	dicts, err := repo.GetTasksByGitBranchID(ctx, branchID)
	if err != nil || len(dicts) != 1 {
		t.Fatalf("GetTasksByGitBranchID: %v %d", err, len(dicts))
	}
	if v, _ := dicts[0].Get("assignees_count"); v != 0 {
		t.Fatalf("assignees_count = %v", v)
	}
	if _, ok := dicts[0].Get("created_at"); !ok {
		t.Fatalf("created_at missing")
	}
}

func TestTaskRepoCompletedSubtasks(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	task, err := repo.CreateTask(ctx, "T", "D", "medium", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	subtasks, _ := NewORMRepository[database.Subtask]("subtasks", sessions)
	for i, status := range []string{"done", "done", "todo"} {
		if _, err := subtasks.Create(ctx, NewKwargs("id", tmvo.NewUUIDv4(), "task_id", task.ID.Value,
			"title", "S", "status", status, "user_id", taskRepoTestUserA, "priority", "medium")); err != nil {
			t.Fatalf("subtask %d: %v", i, err)
		}
	}
	counts, err := repo.GetCompletedSubtaskCounts(ctx, []string{task.ID.Value})
	if err != nil || counts[task.ID.Value] != 2 {
		t.Fatalf("counts: %v %#v", err, counts)
	}
	ok, err := repo.AtomicIncrementCompletedSubtasks(ctx, task.ID.Value)
	if err != nil || !ok {
		t.Fatalf("atomic increment: %v %v", err, ok)
	}
	ok, err = repo.AtomicIncrementCompletedSubtasks(ctx, tmvo.NewUUIDv4())
	if err != nil || ok {
		t.Fatalf("atomic increment missing: %v %v", err, ok)
	}
}

func TestTaskRepoGetOverdueTaskDefect(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	if _, err := repo.CreateTask(ctx, "T", "D", "medium", nil, nil, NewKwargs("due_date", "2000-01-01")); err != nil {
		t.Fatal(err)
	}
	// Python compares a VARCHAR column to a datetime; PostgreSQL rejects the comparison.
	if _, err := repo.GetOverdueTasks(ctx); err == nil {
		t.Fatalf("expected a type error from due_date < timestamp")
	}
}

func TestTaskRepoSelectiveFieldsWithoutSelector(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)
	single, err := repo.GetTaskSelectiveFields(ctx, tmvo.NewUUIDv4(), nil)
	if err != nil || single != nil {
		t.Fatalf("selective single: %v %v", err, single)
	}
	list, err := repo.ListTasksSelectiveFields(ctx, nil, nil, nil, nil, 10, 0)
	if err != nil || list != nil {
		t.Fatalf("selective list: %v %v", err, list)
	}
	if len(repo.GetFieldSelectorMetrics()) != 0 || len(repo.EstimateFieldOptimizationSavings(nil)) != 0 {
		t.Fatalf("selector metrics/savings must be empty")
	}
}

func TestTaskRepositoryInterface(t *testing.T) {
	var _ interface {
		Save(context.Context, *entities.Task) (*entities.Task, error)
		FindByID(context.Context, tmvo.TaskId) (*entities.Task, error)
		FindAll(context.Context) ([]*entities.Task, error)
		Delete(context.Context, tmvo.TaskId) (bool, error)
		Exists(context.Context, tmvo.TaskId) (bool, error)
		GetNextID(context.Context) (tmvo.TaskId, error)
		Count(context.Context) (int, error)
		GetStatistics(context.Context) (map[string]any, error)
		FindByCriteria(context.Context, map[string]any, *int) ([]*entities.Task, error)
		FindByIDAllStates(context.Context, tmvo.TaskId) (*entities.Task, error)
	} = (*ORMTaskRepository)(nil)
}

// Duplicate labels/assignees violate the PK; Python rolls back only that optional step and
// still returns the committed task (dev-check L1).
func TestTaskRepoCreateDuplicateOptionalStepsKeepsTask(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	task, err := repo.CreateTask(ctx, "Dup", "Desc", "high", []string{"a1", "a1"}, []string{"l1", "l1"}, nil)
	if err != nil {
		t.Fatalf("CreateTask: %v", err)
	}
	if len(task.Labels) != 0 {
		t.Fatalf("labels: %#v", task.Labels)
	}
	got, err := repo.GetTask(ctx, task.ID.Value)
	if err != nil || got == nil {
		t.Fatalf("GetTask: %v %v", err, got)
	}
}
