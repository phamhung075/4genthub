package repositories

// Tests for the ported ORMTaskRepository against a real PostgreSQL instance
// (AGENTHUB_TEST_PG_URL), using newTestRepoEnv.

import (
	"context"
	"errors"
	"fmt"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	tmrepo "agenthub/fastmcp/task_management/domain/repositories"
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

// Filtering tasks by an @seat_key assignee is an exact match on
// task_assignees.assignee_id (task_repository.go:735/1575) and stays inside the tenant.
func TestTaskRepoFindBySeatKeyAssigneeIsTenantScoped(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()

	branchA := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repoA := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchA, false)
	if _, err := repoA.CreateTask(ctx, "A", "D", "high", []string{"@go-dev"}, nil, nil); err != nil {
		t.Fatal(err)
	}
	branchB := taskRepoTestBranch(t, sessions, taskRepoTestUserB)
	repoB := taskRepoTestNewRepo(t, sessions, taskRepoTestUserB, branchB, false)
	if _, err := repoB.CreateTask(ctx, "B", "D", "high", []string{"@go-dev"}, nil, nil); err != nil {
		t.Fatal(err)
	}

	gotA, err := repoA.FindByAssignee(ctx, "@go-dev")
	if err != nil || len(gotA) != 1 || gotA[0].Title != "A" {
		t.Fatalf("FindByAssignee(A, @go-dev) = %v %#v, want only A's task", err, gotA)
	}
	gotB, err := repoB.FindByAssignee(ctx, "@go-dev")
	if err != nil || len(gotB) != 1 || gotB[0].Title != "B" {
		t.Fatalf("FindByAssignee(B, @go-dev) = %v %#v, want only B's task", err, gotB)
	}

	limit := 10
	critA, err := repoA.FindByCriteria(ctx, map[string]any{"assignees": []string{"@go-dev"}}, tmrepo.ListQuery{Limit: &limit})
	if err != nil || len(critA) != 1 || critA[0].Title != "A" {
		t.Fatalf("FindByCriteria(A, @go-dev) = %v %#v", err, critA)
	}
	// A bare seat key (no '@') must not match the stored '@go-dev'.
	none, err := repoA.FindByAssignee(ctx, "go-dev")
	if err != nil || len(none) != 0 {
		t.Fatalf("FindByAssignee(A, go-dev) = %v %#v, want none", err, none)
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
	byWord, err := repo.Search(ctx, "JWT", nil, 10, 0)
	if err != nil || len(byWord) != 1 || byWord[0].Title != "Authentication JWT handling" {
		t.Fatalf("Search JWT: %v %#v", err, byWord)
	}
	byLabel, err := repo.Search(ctx, "backend", nil, 10, 0)
	if err != nil || len(byLabel) != 1 || byLabel[0].Title != "Database migration" {
		t.Fatalf("Search label: %v %#v", err, byLabel)
	}
	// search pages too: the same query at offset 0 and offset 1 returns different rows.
	if _, err := repo.CreateTask(ctx, "Second migration note", "migration again", "medium", nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	first, err := repo.Search(ctx, "migration", nil, 1, 0)
	if err != nil || len(first) != 1 {
		t.Fatalf("search page 1: %v %#v", err, first)
	}
	second, err := repo.Search(ctx, "migration", nil, 1, 1)
	if err != nil || len(second) != 1 {
		t.Fatalf("search page 2: %v %#v", err, second)
	}
	if second[0].ID.Value == first[0].ID.Value {
		t.Fatalf("search offset ignored: pages 1 and 2 both returned %s", first[0].ID.Value)
	}
	empty, err := repo.SearchTasks(ctx, "   ", nil, 10, 0)
	if err != nil || len(empty) != 0 {
		t.Fatalf("Search empty: %v %d", err, len(empty))
	}
}

// TestTaskRepoSearchSurfacesIdPrefixAndTitlePhrase pins the lookup a seat actually makes on the
// board: a query that is a task's own id prefix, or its exact title, returns THAT task even with no
// status filter and a limit too small for a created_at-only ordering to reach it. The decoys are
// newer and mention the target's id and title words in their description, which is exactly the
// false negative measured on the live hub (row ea443b29).
func TestTaskRepoSearchSurfacesIdPrefixAndTitlePhrase(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	const title = "The rig's sanctioned seat channel delivers nothing"
	target, err := repo.CreateTask(ctx, title, "target desc", "medium", nil, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	for i := range 5 {
		desc := fmt.Sprintf("channel delivers nothing; quoted row %s", target.ID.Value)
		if _, err := repo.CreateTask(ctx, fmt.Sprintf("mention %d", i), desc, "medium", nil, nil, nil); err != nil {
			t.Fatal(err)
		}
	}

	byID, err := repo.Search(ctx, target.ID.Value[:8], nil, 3, 0)
	if err != nil {
		t.Fatalf("Search id prefix: %v", err)
	}
	if len(byID) == 0 || byID[0].ID.Value != target.ID.Value {
		t.Fatalf("Search id prefix %s did not surface the task first: %#v", target.ID.Value[:8], byID)
	}

	byTitle, err := repo.Search(ctx, title, nil, 3, 0)
	if err != nil {
		t.Fatalf("Search title: %v", err)
	}
	if len(byTitle) == 0 || byTitle[0].ID.Value != target.ID.Value {
		t.Fatalf("Search title %q did not surface the task first: %#v", title, byTitle)
	}
}

// TestTaskRepoListPagingHasNoOverlap is the enumeration contract: two consecutive pages share NO
// row, a known-old row is reachable by paging, and the total the caller is told is the count of the
// rows the filters select, not the length of the page. Before the fix offset was never bound into
// the query and the page length was reported as the total, so page 2 was page 1.
func TestTaskRepoListPagingHasNoOverlap(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	titles := []string{"page-a", "page-b", "page-c", "page-d", "page-e"}
	for _, title := range titles {
		if _, err := repo.CreateTask(ctx, title, "paging", "medium", nil, nil, nil); err != nil {
			t.Fatal(err)
		}
	}

	seen := map[string]bool{}
	for offset := 0; offset < len(titles); offset += 2 {
		limit, off := 2, offset
		page, err := repo.FindByCriteria(ctx, map[string]any{}, tmrepo.ListQuery{Limit: &limit, Offset: &off})
		if err != nil {
			t.Fatalf("page at offset %d: %v", offset, err)
		}
		for _, task := range page {
			if seen[task.ID.Value] {
				t.Fatalf("row %s appears on two pages: offset %d returned a row an earlier page already returned", task.ID.Value, offset)
			}
			seen[task.ID.Value] = true
		}
	}
	if len(seen) != len(titles) {
		t.Fatalf("paging covered %d of %d rows: %v", len(seen), len(titles), seen)
	}

	total, err := repo.CountByCriteria(ctx, map[string]any{})
	if err != nil || total != len(titles) {
		t.Fatalf("CountByCriteria = %d, %v; want %d", total, err, len(titles))
	}

	// The oldest row is only reachable past the first page under the default ordering.
	limit, off := 2, len(titles)-1
	last, err := repo.FindByCriteria(ctx, map[string]any{}, tmrepo.ListQuery{Limit: &limit, Offset: &off})
	if err != nil || len(last) != 1 || last[0].Title != titles[0] {
		t.Fatalf("last page = %#v, %v; want the oldest row %q", last, err, titles[0])
	}

	// An ordering is honoured, not silently replaced: created_at ASC puts the oldest row first.
	limit, off, sortBy := 1, 0, "created_at"
	oldestFirst, err := repo.FindByCriteria(ctx, map[string]any{}, tmrepo.ListQuery{Limit: &limit, Offset: &off, SortBy: sortBy, SortOrder: "asc"})
	if err != nil || len(oldestFirst) != 1 || oldestFirst[0].Title != titles[0] {
		t.Fatalf("created_at asc page = %#v, %v; want %q", oldestFirst, err, titles[0])
	}

	// An ordering the repository cannot serve is an ERROR, never a fallback to the default.
	if _, err := repo.FindByCriteria(ctx, map[string]any{}, tmrepo.ListQuery{SortBy: "no_such_column"}); err == nil {
		t.Fatal("FindByCriteria accepted sort_by=no_such_column")
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
	byAssignee, err := repo.FindByCriteria(ctx, map[string]any{"assignees": []string{"agent-x"}}, tmrepo.ListQuery{Limit: &limit})
	if err != nil || len(byAssignee) != 1 || byAssignee[0].Title != "A" {
		t.Fatalf("criteria assignees: %v %#v", err, byAssignee)
	}
	byLabel, err := repo.FindByCriteria(ctx, map[string]any{"labels": []string{"backend"}}, tmrepo.ListQuery{Limit: &limit})
	if err != nil || len(byLabel) != 1 || byLabel[0].Title != "A" {
		t.Fatalf("criteria labels: %v %#v", err, byLabel)
	}
	byStatus, err := repo.FindByCriteria(ctx, map[string]any{"status": "low-status"}, tmrepo.ListQuery{Limit: &limit})
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
	if gitBranchRepoTestRowExists(t, sessions, `SELECT count(*) FROM task_contexts WHERE task_id = $1`, task.ID.Value) {
		t.Fatal("task_contexts row still present")
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

// GetOverdueTasks means the tasks that are PAST DUE AND NOT COMPLETED - the filter the Python
// original applied (Task.due_date < datetime.now(UTC) AND Task.status != "completed"), and the
// only reading of "overdue" this repository defines. The port preserved a DEFECT instead of the
// behaviour: due_date is a text column, comparing it with a timestamp raises on PostgreSQL, and
// so the method always failed and this test pinned the failure.
//
// It asserts the INTENT now - the three cases that distinguish it - rather than whatever the
// driver happens to return, because a security bump that made a broken query merely stop
// erroring would otherwise be recorded as the behaviour.
func TestTaskRepoGetOverdueTasksReturnsPastDueUnfinished(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	pastDue, err := repo.CreateTask(ctx, "past due", "D", "medium", nil, nil, NewKwargs("due_date", "2000-01-01"))
	if err != nil {
		t.Fatal(err)
	}
	future, err := repo.CreateTask(ctx, "future due", "D", "medium", nil, nil, NewKwargs("due_date", "2999-01-01"))
	if err != nil {
		t.Fatal(err)
	}
	finished, err := repo.CreateTask(ctx, "past due but finished", "D", "medium", nil, nil, NewKwargs("due_date", "2000-01-01"))
	if err != nil {
		t.Fatal(err)
	}
	// Set the finished task's status directly: UpdateTask is itself a transcription with its own
	// defects ("'str' object has no attribute 'touch'"), and this fixture needs the row, not that
	// code path.
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `UPDATE tasks SET status = 'completed' WHERE id = $1::uuid`, finished.ID.String())
		return err
	}); err != nil {
		t.Fatal(err)
	}

	got, err := repo.GetOverdueTasks(ctx)
	if err != nil {
		t.Fatalf("GetOverdueTasks: %v", err)
	}
	titles := make([]string, 0, len(got))
	for _, task := range got {
		titles = append(titles, task.Title)
	}
	if len(got) != 1 || got[0].ID.String() != pastDue.ID.String() {
		t.Fatalf("overdue = %v, want exactly the past-due unfinished task; future due is %q, past due but completed is %q",
			titles, future.Title, finished.Title)
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
		FindByCriteria(context.Context, map[string]any, tmrepo.ListQuery) ([]*entities.Task, error)
		CountByCriteria(context.Context, map[string]any) (int, error)
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

// TestTaskRepoLatestInProgressByAssigneeIsTheRuledResumeRead pins 4/8's resolution against the real
// schema: the most recently UPDATED in_progress item assigned to the seat, id ascending on a tie, and
// never a row in another status, for another seat, or in another tenant.
func TestTaskRepoLatestInProgressByAssigneeIsTheRuledResumeRead(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	branchID := taskRepoTestBranch(t, sessions, taskRepoTestUserA)
	repo := taskRepoTestNewRepo(t, sessions, taskRepoTestUserA, branchID, false)

	mk := func(title string, assignees []string, statusRaw string) *entities.Task {
		t.Helper()
		id := tmvo.GenerateNewTaskId()
		branch := branchID
		status := tmvo.TaskStatus{Value: statusRaw}
		task, err := entities.NewTask(entities.Task{
			ID: &id, Title: title, Description: "D", GitBranchID: &branch,
			Assignees: assignees, Status: &status,
		})
		if err != nil {
			t.Fatalf("NewTask(%s): %v", title, err)
		}
		saved, err := repo.Save(ctx, task)
		if err != nil {
			t.Fatalf("Save(%s): %v", title, err)
		}
		return saved
	}

	mk("older", []string{"@go-dev"}, "in_progress")
	time.Sleep(3 * time.Millisecond)
	newer := mk("newer", []string{"@go-dev"}, "in_progress")
	mk("todo", []string{"@go-dev"}, "todo")
	mk("other seat", []string{"@fe-dev"}, "in_progress")

	got, err := repo.LatestInProgressByAssignee(ctx, "@go-dev")
	if err != nil {
		t.Fatalf("LatestInProgressByAssignee: %v", err)
	}
	if got == nil || got.Title != newer.Title {
		t.Fatalf("resolved %v, want the most recently updated in_progress @go-dev task %q", got, newer.Title)
	}

	// A later UPDATE of the older row outranks the newer row's creation: the rule is updated_at, not
	// created_at.
	older := mk("older again", []string{"@go-dev"}, "in_progress")
	time.Sleep(3 * time.Millisecond)
	older.Title = "older, touched last"
	if _, err := repo.Save(ctx, older); err != nil {
		t.Fatalf("re-Save(older): %v", err)
	}
	got, err = repo.LatestInProgressByAssignee(ctx, "@go-dev")
	if err != nil || got == nil || got.Title != "older, touched last" {
		t.Fatalf("after the update, resolved %v (%v), want the last-touched row", got, err)
	}

	// A tie on updated_at is broken by id ascending, which makes the answer stable rather than
	// dependent on the scan order.
	tieA := mk("tie a", []string{"@go-dev"}, "in_progress")
	time.Sleep(3 * time.Millisecond)
	tieB := mk("tie b", []string{"@go-dev"}, "in_progress")
	tieStamp := time.Now().UTC()
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `UPDATE tasks SET updated_at = $1 WHERE id = $2::uuid OR id = $3::uuid`,
			tieStamp, tieA.ID.Value, tieB.ID.Value)
		return err
	}); err != nil {
		t.Fatalf("forcing the tie: %v", err)
	}
	wantTitle := tieA.Title
	if tieB.ID.Value < tieA.ID.Value {
		wantTitle = tieB.Title
	}
	got, err = repo.LatestInProgressByAssignee(ctx, "@go-dev")
	if err != nil || got == nil || got.Title != wantTitle {
		t.Fatalf("tie resolved %v (%v), want the lower id %q", got, err, wantTitle)
	}

	// The seat read is the repository's scope, so another tenant's @go-dev row is never a candidate.
	branchB := taskRepoTestBranch(t, sessions, taskRepoTestUserB)
	repoB := taskRepoTestNewRepo(t, sessions, taskRepoTestUserB, branchB, false)
	idB := tmvo.GenerateNewTaskId()
	branchBB := branchB
	statusB := tmvo.TaskStatus{Value: "in_progress"}
	taskB, err := entities.NewTask(entities.Task{
		ID: &idB, Title: "tenant B", Description: "D", GitBranchID: &branchBB,
		Assignees: []string{"@go-dev"}, Status: &statusB,
	})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := repoB.Save(ctx, taskB); err != nil {
		t.Fatalf("tenant B save: %v", err)
	}
	gotA, err := repo.LatestInProgressByAssignee(ctx, "@go-dev")
	if err != nil || gotA == nil || gotA.Title == "tenant B" {
		t.Fatalf("tenant A resolved %v (%v), want a row of its own tree", gotA, err)
	}
	gotB, err := repoB.LatestInProgressByAssignee(ctx, "@go-dev")
	if err != nil || gotB == nil || gotB.Title != "tenant B" {
		t.Fatalf("tenant B resolved %v (%v), want its own row", gotB, err)
	}
}
