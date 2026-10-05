package repositories

// Real-PostgreSQL tests for the ORM git branch repository and its factory.

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// ---- helpers --------------------------------------------------------------------

func gitBranchRepoTestSetup(t *testing.T, sessions *database.SessionManager, user string) (string, *ORMGitBranchRepository) {
	t.Helper()
	ctx := context.Background()
	projRepo, err := NewORMProjectRepository(sessions, &user)
	if err != nil {
		t.Fatalf("NewORMProjectRepository: %v", err)
	}
	project, err := projRepo.CreateProject(ctx, "P-"+user, "", &user)
	if err != nil {
		t.Fatalf("CreateProject: %v", err)
	}
	repo, err := NewORMGitBranchRepository(sessions, &user, false)
	if err != nil {
		t.Fatalf("NewORMGitBranchRepository: %v", err)
	}
	return project.ID.Value, repo
}

func gitBranchRepoTestCreate[M any](t *testing.T, sessions *database.SessionManager, table string, kwargs Kwargs) {
	t.Helper()
	r, err := NewORMRepository[M](table, sessions)
	if err != nil {
		t.Fatalf("NewORMRepository[%s]: %v", table, err)
	}
	if _, err := r.Create(context.Background(), kwargs); err != nil {
		t.Fatalf("create %s: %v", table, err)
	}
}

func gitBranchRepoTestAddTask(t *testing.T, sessions *database.SessionManager, branchID, userID, status, priority string) string {
	t.Helper()
	id := tmvo.NewUUIDv4()
	gitBranchRepoTestCreate[database.Task](t, sessions, "tasks", NewKwargs(
		"id", id, "title", "T", "description", "d", "git_branch_id", branchID,
		"status", status, "priority", priority, "user_id", userID))
	return id
}

func gitBranchRepoTestSetColumns(t *testing.T, sessions *database.SessionManager, branchID, priority, status string, createdAt time.Time) {
	t.Helper()
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`UPDATE project_git_branchs SET priority = $1, status = $2, created_at = $3 WHERE id = $4`,
			priority, status, createdAt, branchID)
		return err
	})
	if err != nil {
		t.Fatal(err)
	}
}

func gitBranchRepoTestRowExists(t *testing.T, sessions *database.SessionManager, query string, args ...any) bool {
	t.Helper()
	n := 0
	err := sessions.WithSession(context.Background(), func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, query, args...).Scan(&n)
	})
	if err != nil {
		t.Fatal(err)
	}
	return n > 0
}

// ---- CRUD / finders -------------------------------------------------------------

func TestGitBranchRepoCreateFindAndCounts(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "fbaceaf3-6b31-5a01-aa3d-030908a69d35" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)

	gb, err := repo.CreateBranch(ctx, projectID, "main", "the main branch")
	if err != nil {
		t.Fatalf("CreateBranch: %v", err)
	}
	if gb.ID == nil || gb.Name != "main" || gb.Description != "the main branch" || gb.ProjectID != projectID {
		t.Fatalf("unexpected branch: %+v", gb)
	}
	if gb.Status == nil || gb.Status.Value != "todo" || gb.Priority == nil || gb.Priority.Value != "medium" {
		t.Fatalf("defaults wrong: status=%v priority=%v", gb.Status, gb.Priority)
	}
	if gb.CreatedAt == nil || gb.UpdatedAt == nil {
		t.Fatal("timestamps missing")
	}

	got, err := repo.FindByID(ctx, gb.ID.Value, nil)
	if err != nil || got == nil || got.Name != "main" {
		t.Fatalf("FindByID: %v %+v", err, got)
	}
	if _, err := repo.FindByID(ctx, gb.ID.Value, &projectID); err != nil {
		t.Fatalf("FindByID with project: %v", err)
	}
	other := tmvo.NewUUIDv4()
	if got, err := repo.FindByID(ctx, gb.ID.Value, &other); err != nil || got != nil {
		t.Fatalf("FindByID wrong project: %v %+v", err, got)
	}
	if got, err := repo.FindByID(ctx, tmvo.NewUUIDv4(), nil); err != nil || got != nil {
		t.Fatalf("FindByID missing: %v %+v", err, got)
	}

	byName, err := repo.FindByName(ctx, projectID, "main")
	if err != nil || byName == nil || byName.ID.Value != gb.ID.Value {
		t.Fatalf("FindByName: %v %+v", err, byName)
	}
	if got, err := repo.FindByName(ctx, projectID, "nope"); err != nil || got != nil {
		t.Fatalf("FindByName missing: %v %+v", err, got)
	}

	all, err := repo.FindAllByProject(ctx, projectID)
	if err != nil || len(all) != 1 {
		t.Fatalf("FindAllByProject: %v %d", err, len(all))
	}
	every, err := repo.FindAll(ctx)
	if err != nil || len(every) != 1 {
		t.Fatalf("FindAll: %v %d", err, len(every))
	}
	exists, err := repo.Exists(ctx, projectID, gb.ID.Value)
	if err != nil || !exists {
		t.Fatalf("Exists: %v %v", exists, err)
	}
	if exists, _ := repo.Exists(ctx, projectID, tmvo.NewUUIDv4()); exists {
		t.Fatal("Exists should be false")
	}
	count, err := repo.CountByProject(ctx, projectID)
	if err != nil || count != 1 {
		t.Fatalf("CountByProject: %v %d", err, count)
	}
	if n, err := repo.CountAll(ctx); err != nil || n != 1 {
		t.Fatalf("CountAll: %v %d", err, n)
	}
	found, err := repo.CheckNameExistsInProject(ctx, projectID, " main ", nil)
	if err != nil || !found {
		t.Fatalf("CheckNameExistsInProject (strip): %v %v", found, err)
	}
	if found, _ := repo.CheckNameExistsInProject(ctx, projectID, "nope", nil); found {
		t.Fatal("CheckNameExistsInProject should be false")
	}
	if found, _ := repo.CheckNameExistsInProject(ctx, projectID, "main", &gb.ID.Value); found {
		t.Fatal("exclude branch should make it false")
	}

	byIDs := repo.FindByIDs(ctx, []string{gb.ID.Value, tmvo.NewUUIDv4()})
	if byIDs.Len() != 1 {
		t.Fatalf("FindByIDs len=%d", byIDs.Len())
	}
	if got, ok := byIDs.Get(gb.ID.Value); !ok || got.ProjectID != projectID {
		t.Fatalf("FindByIDs entry: %v %+v", ok, got)
	}
	if repo.FindByIDs(ctx, []string{}).Len() != 0 {
		t.Fatal("FindByIDs empty")
	}
}

func TestGitBranchRepoUserIsolation(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	userA, userB := "git-branch-iso-a", "git-branch-iso-b"
	projectA, repoA := gitBranchRepoTestSetup(t, sessions, userA)
	_, repoB := gitBranchRepoTestSetup(t, sessions, userB)

	gb, err := repoA.CreateBranch(ctx, projectA, "iso", "")
	if err != nil {
		t.Fatal(err)
	}
	if got, err := repoB.FindByID(ctx, gb.ID.Value, nil); err != nil || got != nil {
		t.Fatalf("user B should not see user A branch: %v %+v", err, got)
	}
	if found, err := repoB.CheckNameExistsInProject(ctx, projectA, "iso", nil); err != nil || found {
		t.Fatalf("user B name check: %v %v", found, err)
	}
	if list, err := repoB.FindAllByProject(ctx, projectA); err != nil || len(list) != 0 {
		t.Fatalf("user B list: %v %d", err, len(list))
	}
	if deleted, err := repoB.Delete(ctx, projectA, gb.ID.Value); err != nil || deleted {
		t.Fatalf("user B delete: %v %v", deleted, err)
	}
	if deleted, err := repoB.DeleteBranch(ctx, gb.ID.Value); err != nil || deleted {
		t.Fatalf("user B cascade delete: %v %v", deleted, err)
	}
	if got, _ := repoA.FindByID(ctx, gb.ID.Value, nil); got == nil {
		t.Fatal("branch should still exist for user A")
	}
}

// ---- update / get / statistics protocol -----------------------------------------

func TestGitBranchRepoUpdateGetAndWithUser(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "773e4bb0-67bc-5f4e-9bd9-4b912c99460c" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)

	gb, err := repo.CreateBranch(ctx, projectID, "upd", "")
	if err != nil {
		t.Fatal(err)
	}
	gb.Name = "renamed"
	gb.Description = "changed"
	if err := repo.UpdateDomain(ctx, gb); err != nil {
		t.Fatalf("UpdateDomain: %v", err)
	}
	got, err := repo.FindByID(ctx, gb.ID.Value, nil)
	if err != nil || got == nil || got.Name != "renamed" || got.Description != "changed" {
		t.Fatalf("after UpdateDomain: %v %+v", err, got)
	}

	// update (sync direct fields; unknown fields ignored, updated_at refreshed).
	ok, err := repo.Update(gb.ID.Value, map[string]any{
		"task_count": 3, "completed_task_count": 1, "progress_percentage": 33.0, "garbage": 1,
	})
	if err != nil || !ok {
		t.Fatalf("Update: %v %v", ok, err)
	}
	row, err := repo.GetByID(ctx, gb.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if row.TaskCount != 3 || row.CompletedTaskCount != 1 {
		t.Fatalf("row after update: %+v", row)
	}
	if ok, _ := repo.Update(tmvo.NewUUIDv4(), map[string]any{"task_count": 1}); ok {
		t.Fatal("Update missing should be false")
	}

	gotAny, err := repo.Get(gb.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	// Python get() counts the tasks table, not the stored counters (no tasks here)
	simple, ok := gotAny.(*gitBranchRepoBranch)
	if !ok || simple.TaskCount != 0 || simple.CompletedTaskCount != 0 || simple.ProjectID != projectID {
		t.Fatalf("Get: %+v", gotAny)
	}
	if v, err := repo.Get(tmvo.NewUUIDv4()); err != nil || v != nil {
		t.Fatalf("Get missing: %v %v", v, err)
	}

	byProject, err := repo.FindByProjectID(projectID)
	if err != nil || len(byProject) != 1 || byProject[0].BranchID() != gb.ID.Value {
		t.Fatalf("FindByProjectID: %v %+v", err, byProject)
	}
	allBranches, err := repo.GetAll()
	if err != nil || len(allBranches) != 1 {
		t.Fatalf("GetAll: %v %+v", err, allBranches)
	}

	withUser, err := repo.WithUser("git-branch-other")
	if err != nil {
		t.Fatal(err)
	}
	if got, err := withUser.FindByID(ctx, gb.ID.Value, nil); err != nil || got != nil {
		t.Fatalf("WithUser isolation: %v %+v", err, got)
	}
}

func TestGitBranchRepoFindersAgentAndAvailable(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "f05c6f01-ae58-5efc-93b3-a08827f78a01" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)

	base := time.Now().UTC().Add(-time.Hour)
	urgent, err := repo.CreateBranch(ctx, projectID, "urgent", "")
	if err != nil {
		t.Fatal(err)
	}
	high, err := repo.CreateBranch(ctx, projectID, "high", "")
	if err != nil {
		t.Fatal(err)
	}
	gitBranchRepoTestSetColumns(t, sessions, urgent.ID.Value, "urgent", "todo", base)
	gitBranchRepoTestSetColumns(t, sessions, high.ID.Value, "high", "todo", base.Add(time.Minute))

	// assign an agent to high; urgent remains unassigned.
	if ok, err := repo.AssignAgent(ctx, projectID, high.ID.Value, "agent-1"); err != nil || !ok {
		t.Fatalf("AssignAgent: %v %v", ok, err)
	}
	if ok, _ := repo.AssignAgent(ctx, projectID, tmvo.NewUUIDv4(), "agent-1"); ok {
		t.Fatal("AssignAgent missing should be false")
	}
	assigned, err := repo.FindByAssignedAgent(ctx, "agent-1")
	if err != nil || len(assigned) != 1 || assigned[0].ID.Value != high.ID.Value {
		t.Fatalf("FindByAssignedAgent: %v %+v", err, assigned)
	}

	available, err := repo.FindAvailableForAssignment(ctx, projectID)
	if err != nil || len(available) != 1 || available[0].ID.Value != urgent.ID.Value {
		t.Fatalf("FindAvailableForAssignment: %v %+v", err, available)
	}

	if _, err := repo.FindByStatus(ctx, projectID, "todo"); err != nil {
		t.Fatal(err)
	}
	if ok, err := repo.Update(high.ID.Value, map[string]any{"status": "done"}); err != nil || !ok {
		t.Fatalf("set done: %v %v", ok, err)
	}
	done, err := repo.FindByStatus(ctx, projectID, "done")
	if err != nil || len(done) != 1 || done[0].ID.Value != high.ID.Value {
		t.Fatalf("FindByStatus done: %v %+v", err, done)
	}
	if ok, err := repo.UnassignAgent(ctx, projectID, high.ID.Value); err != nil || !ok {
		t.Fatalf("UnassignAgent: %v %v", ok, err)
	}
	if ok, _ := repo.UnassignAgent(ctx, projectID, tmvo.NewUUIDv4()); ok {
		t.Fatal("UnassignAgent missing should be false")
	}
}

// ---- interface methods ----------------------------------------------------------

func TestGitBranchRepoInterfaceMethods(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "1ec16b3c-c469-5f7b-859e-62886b4300ec" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)

	out, err := repo.CreateGitBranch(ctx, projectID, "iface", "d")
	if err != nil || out["success"] != true {
		t.Fatalf("CreateGitBranch: %v %+v", err, out)
	}
	branchDict, _ := out["git_branch"].(map[string]any)
	id, _ := branchDict["id"].(string)
	if id == "" {
		t.Fatalf("no id: %+v", out)
	}

	byID, err := repo.GetGitBranchByID(ctx, id)
	if err != nil || byID["success"] != true {
		t.Fatalf("GetGitBranchByID: %v %+v", err, byID)
	}
	if _, err := repo.GetGitBranchByID(ctx, tmvo.NewUUIDv4()); err != nil {
		t.Fatal(err)
	}
	if r, _ := repo.GetGitBranchByID(ctx, tmvo.NewUUIDv4()); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}

	byName, err := repo.GetGitBranchByName(ctx, projectID, "iface")
	if err != nil || byName["success"] != true {
		t.Fatalf("GetGitBranchByName: %v %+v", err, byName)
	}
	if r, _ := repo.GetGitBranchByName(ctx, projectID, "missing"); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}

	list, err := repo.ListGitBranchs(ctx, projectID)
	if err != nil || list["count"] != 1 {
		t.Fatalf("ListGitBranchs: %v %+v", err, list)
	}

	name := "iface2"
	desc := "new"
	upd, err := repo.UpdateGitBranch(ctx, id, &name, &desc)
	if err != nil || upd["success"] != true {
		t.Fatalf("UpdateGitBranch: %v %+v", err, upd)
	}
	if r, _ := repo.UpdateGitBranch(ctx, tmvo.NewUUIDv4(), &name, nil); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}

	if r, _ := repo.AssignAgentToBranch(ctx, projectID, "agent-x", "iface2"); r["success"] != true {
		t.Fatalf("AssignAgentToBranch: %+v", r)
	}
	if r, _ := repo.AssignAgentToBranch(ctx, projectID, "agent-x", "missing"); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}
	if r, _ := repo.UnassignAgentFromBranch(ctx, projectID, "agent-x", "iface2"); r["success"] != true {
		t.Fatalf("UnassignAgentFromBranch: %+v", r)
	}
	if r, _ := repo.UnassignAgentFromBranch(ctx, projectID, "agent-x", "missing"); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}

	stats, err := repo.GetBranchStatistics(ctx, projectID, id)
	if err != nil || stats["branch_name"] != "iface2" {
		t.Fatalf("GetBranchStatistics: %v %+v", err, stats)
	}
	if missing, _ := repo.GetBranchStatistics(ctx, projectID, tmvo.NewUUIDv4()); missing["error"] != "Branch not found" {
		t.Fatalf("expected Branch not found: %+v", missing)
	}

	if r, _ := repo.ArchiveBranch(ctx, projectID, id); r["success"] != true {
		t.Fatalf("ArchiveBranch: %+v", r)
	}
	row, _ := repo.GetByID(ctx, id)
	if row.Status != "cancelled" {
		t.Fatalf("archive status = %q", row.Status)
	}
	if r, _ := repo.RestoreBranch(ctx, projectID, id); r["success"] != true {
		t.Fatalf("RestoreBranch: %+v", r)
	}
	row, _ = repo.GetByID(ctx, id)
	if row.Status != "todo" {
		t.Fatalf("restore status = %q", row.Status)
	}
	if r, _ := repo.ArchiveBranch(ctx, projectID, tmvo.NewUUIDv4()); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}
	if r, _ := repo.RestoreBranch(ctx, projectID, tmvo.NewUUIDv4()); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}

	if r, _ := repo.DeleteGitBranch(ctx, projectID, id); r["success"] != true {
		t.Fatalf("DeleteGitBranch: %+v", r)
	}
	if r, _ := repo.DeleteGitBranch(ctx, projectID, id); r["error_code"] != "NOT_FOUND" {
		t.Fatalf("expected NOT_FOUND: %+v", r)
	}
}

// ---- statistics / performance methods -------------------------------------------

func TestGitBranchRepoStatsAndSummaries(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "85f293dd-20db-589f-9def-f140770329dc" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)

	gb, err := repo.CreateBranch(ctx, projectID, "stats", "")
	if err != nil {
		t.Fatal(err)
	}
	gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "done", "urgent")
	gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "todo", "high")
	gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "in_progress", "medium")

	stats, err := repo.GetBranchStatistics(ctx, projectID, gb.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if stats["task_count"] != 3 || stats["completed_task_count"] != 1 {
		t.Fatalf("stats: %+v", stats)
	}
	progress, _ := stats["progress_percentage"].(float64)
	if progress < 33.3 || progress > 33.4 {
		t.Fatalf("progress: %v", stats["progress_percentage"])
	}

	branches := repo.GetBranchesWithTaskCounts(projectID)
	if len(branches) != 1 {
		t.Fatalf("GetBranchesWithTaskCounts len=%d", len(branches))
	}
	b := branches[0]
	if v, _ := b.Get("has_tasks"); v != true {
		t.Fatalf("has_tasks: %v", v)
	}
	if v, _ := b.Get("is_active"); v != true {
		t.Fatalf("is_active: %v", v)
	}
	if v, _ := b.Get("is_completed"); v != false {
		t.Fatalf("is_completed: %v", v)
	}
	tcAny, _ := b.Get("task_counts")
	tc, _ := tcAny.(*entities.OrderedMap[any])
	if tc == nil {
		t.Fatalf("task_counts: %+v", tcAny)
	}
	if v, _ := tc.Get("total"); v != 3 {
		t.Fatalf("total: %v", v)
	}
	byStatusAny, _ := tc.Get("by_status")
	byStatus, _ := byStatusAny.(*entities.OrderedMap[any])
	if v, _ := byStatus.Get("done"); v != 1 {
		t.Fatalf("done: %v", v)
	}
	byPriorityAny, _ := tc.Get("by_priority")
	byPriority, _ := byPriorityAny.(*entities.OrderedMap[any])
	if v, _ := byPriority.Get("urgent"); v != 1 {
		t.Fatalf("urgent: %v", v)
	}
	if passed := repo.GetBranchesWithTaskCounts("not-a-uuid"); len(passed) != 0 {
		t.Fatal("invalid uuid should be empty")
	}
	if passed := repo.GetBranchesWithTaskCounts(""); len(passed) != 0 {
		t.Fatal("empty project should be empty")
	}

	summary := repo.GetBranchSummaryStats(projectID)
	if summary == nil {
		t.Fatal("summary nil")
	}
	if v, _ := summary.Get("completion_percentage"); v != float64(33.3) {
		t.Fatalf("completion_percentage: %v", v)
	}
	noProject := repo.GetBranchSummaryStats("")
	if v, _ := noProject.Get("error"); v != "No project_id provided" {
		t.Fatalf("no project error: %v", v)
	}

	single := repo.GetSingleBranchWithCounts(gb.ID.Value)
	if single == nil {
		t.Fatal("single nil")
	}
	if v, _ := single.Get("name"); v != "stats" {
		t.Fatalf("single name: %v", v)
	}
	if repo.GetSingleBranchWithCounts("") != nil {
		t.Fatal("empty branch id should be nil")
	}
	if repo.GetSingleBranchWithCounts(tmvo.NewUUIDv4()) != nil {
		t.Fatal("missing branch should be nil")
	}

	projectSummary, err := repo.GetProjectBranchSummary(ctx, projectID)
	if err != nil {
		t.Fatal(err)
	}
	if v, _ := projectSummary.Get("project_id"); v != projectID {
		t.Fatalf("project summary: %+v", projectSummary)
	}
	smAny, _ := projectSummary.Get("summary")
	sm, _ := smAny.(*entities.OrderedMap[any])
	if v, _ := sm.Get("total_branches"); v != 1 {
		t.Fatalf("total_branches: %v", v)
	}
	tasksAny, _ := projectSummary.Get("tasks")
	tasks, _ := tasksAny.(*entities.OrderedMap[any])
	if v, _ := tasks.Get("total_tasks"); v != 0 {
		t.Fatalf("total_tasks: %v", v)
	}
}

// ---- comprehensive cascade delete -----------------------------------------------

func TestGitBranchRepoDeleteBranchCascade(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "dfa8dcb6-6e5f-5fb8-81cc-e4e9a3acfb5e" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)

	gb, err := repo.CreateBranch(ctx, projectID, "cascade", "")
	if err != nil {
		t.Fatal(err)
	}
	taskID := gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "todo", "high")
	otherTask := gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "todo", "low")
	now := time.Now().UTC()

	// Subtask.
	gitBranchRepoTestCreate[database.Subtask](t, sessions, "subtasks", NewKwargs(
		"id", tmvo.NewUUIDv4(), "task_id", taskID, "title", "S", "description", "",
		"status", "todo", "priority", "medium", "assignees", json.RawMessage("[]"),
		"user_id", user, "created_at", now, "updated_at", now))
	// Task assignee.
	gitBranchRepoTestCreate[database.TaskAssignee](t, sessions, "task_assignees", NewKwargs(
		"id", tmvo.NewUUIDv4(), "task_id", taskID, "assignee_id", "agent-1",
		"user_id", user, "assigned_at", now))
	// Label + task label.
	labelID := "label-cascade"
	gitBranchRepoTestCreate[database.Label](t, sessions, "labels", NewKwargs(
		"id", labelID, "name", labelID, "color", "#fff", "description", "", "user_id", user, "created_at", now, "updated_at", now))
	gitBranchRepoTestCreate[database.TaskLabel](t, sessions, "task_labels", NewKwargs(
		"task_id", taskID, "label_id", labelID, "user_id", user, "applied_at", now))
	// Dependency to another task in the same branch.
	err = sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, e := s.ExecContext(ctx,
			`INSERT INTO task_dependencies (task_id, depends_on_task_id, dependency_type, user_id, created_at)
			 VALUES ($1::uuid,$2::uuid,'blocks',$3,$4)`, taskID, otherTask, user, now)
		return e
	})
	if err != nil {
		t.Fatal(err)
	}
	// BranchContext.
	branchContextID := tmvo.NewUUIDv4()
	gitBranchRepoTestCreate[database.BranchContext](t, sessions, "branch_contexts", NewKwargs(
		"id", branchContextID, "branch_id", gb.ID.Value, "user_id", user))
	// Direct TaskContext (parent_branch_id).
	gitBranchRepoTestCreate[database.TaskContext](t, sessions, "task_contexts", NewKwargs(
		"id", tmvo.NewUUIDv4(), "task_id", taskID, "parent_branch_id", gb.ID.Value, "user_id", user))
	// Indirect TaskContext (parent_branch_context_id).
	gitBranchRepoTestCreate[database.TaskContext](t, sessions, "task_contexts", NewKwargs(
		"id", tmvo.NewUUIDv4(), "task_id", otherTask, "parent_branch_context_id", branchContextID, "user_id", user))
	// ContextInheritanceCache.
	gitBranchRepoTestCreate[database.ContextInheritanceCache](t, sessions, "context_inheritance_cache", NewKwargs(
		"context_id", gb.ID.Value, "context_level", "branch", "context_type", "hierarchical",
		"resolved_context", json.RawMessage("{}"), "resolved_data", json.RawMessage("{}"),
		"dependencies_hash", "h", "resolution_path", "p", "parent_chain", json.RawMessage("[]"),
		"created_at", now, "expires_at", now, "last_hit", now, "cache_size_bytes", int64(0),
		"user_id", user))
	// ContextDelegation (source branch).
	gitBranchRepoTestCreate[database.ContextDelegation](t, sessions, "context_delegations", NewKwargs(
		"id", tmvo.NewUUIDv4(), "source_level", "branch", "source_id", gb.ID.Value, "source_type", "context",
		"target_level", "branch", "target_id", tmvo.NewUUIDv4(), "target_type", "context",
		"delegated_data", json.RawMessage("{}"), "delegation_data", json.RawMessage("{}"),
		"delegation_reason", "r", "trigger_type", "manual", "auto_delegated", false,
		"processed", false, "status", "pending", "user_id", user, "created_at", now))

	deleted, err := repo.DeleteBranch(ctx, gb.ID.Value)
	if err != nil || !deleted {
		t.Fatalf("DeleteBranch: %v %v", deleted, err)
	}
	if row, _ := repo.GetByID(ctx, gb.ID.Value); row != nil {
		t.Fatal("branch not deleted")
	}
	checks := []struct {
		query string
		arg   any
	}{
		{`SELECT count(*) FROM tasks WHERE git_branch_id = $1`, gb.ID.Value},
		{`SELECT count(*) FROM subtasks WHERE task_id = $1`, taskID},
		{`SELECT count(*) FROM task_assignees WHERE task_id = $1`, taskID},
		{`SELECT count(*) FROM task_labels WHERE task_id = $1`, taskID},
		{`SELECT count(*) FROM task_dependencies WHERE task_id = $1`, taskID},
		{`SELECT count(*) FROM task_contexts WHERE parent_branch_id = $1`, gb.ID.Value},
		{`SELECT count(*) FROM task_contexts WHERE parent_branch_context_id = $1`, branchContextID},
		{`SELECT count(*) FROM branch_contexts WHERE branch_id = $1`, gb.ID.Value},
		{`SELECT count(*) FROM context_inheritance_cache WHERE context_id = $1`, gb.ID.Value},
		{`SELECT count(*) FROM context_delegations WHERE source_id = $1`, gb.ID.Value},
	}
	for _, c := range checks {
		if gitBranchRepoTestRowExists(t, sessions, c.query, c.arg) {
			t.Fatalf("row still present: %s", c.query)
		}
	}
	if deleted, err := repo.DeleteBranch(ctx, tmvo.NewUUIDv4()); err != nil || deleted {
		t.Fatalf("DeleteBranch missing: %v %v", deleted, err)
	}
}

func TestGitBranchRepoDeleteNonCascade(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "ddbea7e7-dda9-5a2c-8b03-01475cf60ed5" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)
	gb, err := repo.CreateBranch(ctx, projectID, "del", "")
	if err != nil {
		t.Fatal(err)
	}
	gitBranchRepoTestAddTask(t, sessions, gb.ID.Value, user, "todo", "medium")
	deleted, err := repo.Delete(ctx, projectID, gb.ID.Value)
	if err != nil || !deleted {
		t.Fatalf("Delete: %v %v", deleted, err)
	}
	if deleted, _ := repo.Delete(ctx, projectID, gb.ID.Value); deleted {
		t.Fatal("second delete should be false")
	}
}

// ---- system mode / error paths --------------------------------------------------

func TestGitBranchRepoSystemModeAndErrors(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := "4e27de9a-ff26-534a-b2f3-f8944392a863" // real user ids are UUIDs (Project.user_id stores the normalised id)
	projectID, repo := gitBranchRepoTestSetup(t, sessions, user)
	gb, err := repo.CreateBranch(ctx, projectID, "sys", "")
	if err != nil {
		t.Fatal(err)
	}

	sys, err := NewORMGitBranchRepository(sessions, nil, true)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := sys.FindByID(ctx, gb.ID.Value, nil); err == nil || !strings.Contains(err.Error(), "User authentication required") {
		t.Fatalf("FindByID system: %v", err)
	}
	if _, err := sys.FindAllByProject(ctx, projectID); err == nil {
		t.Fatal("FindAllByProject system should error")
	}
	if _, err := sys.CheckNameExistsInProject(ctx, projectID, "sys", nil); err == nil {
		t.Fatal("CheckNameExistsInProject system should error")
	}
	if _, err := sys.Delete(ctx, projectID, gb.ID.Value); err == nil {
		t.Fatal("Delete system should error")
	}
	ent, err := repo.FindByID(ctx, gb.ID.Value, nil)
	if err != nil || ent == nil {
		t.Fatal(err)
	}
	if err := sys.Save(ctx, ent); err == nil {
		t.Fatal("Save system should error")
	}
	if _, err := sys.CreateBranch(ctx, projectID, "sys2", ""); err == nil {
		t.Fatal("CreateBranch system should error")
	}
	if r, _ := sys.GetGitBranchByID(ctx, gb.ID.Value); r["error_code"] != "GET_FAILED" {
		t.Fatalf("GetGitBranchByID system: %+v", r)
	}
	if deleted, err := sys.DeleteBranch(ctx, gb.ID.Value); err != nil || !deleted {
		t.Fatalf("system DeleteBranch should delete: %v %v", deleted, err)
	}
}

// ---- factory --------------------------------------------------------------------

type gitBranchRepoFakeBackend struct {
	calls int
	repo  domainrepos.GitBranchRepository
}

func (f *gitBranchRepoFakeBackend) GetGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error) {
	f.calls++
	return f.repo, nil
}

func gitBranchRepoFactoryEnv(values map[string]string) func(string) string {
	return func(k string) string { return values[k] }
}

func TestGitBranchRepositoryFactory(t *testing.T) {
	sessions := newTestRepoEnv(t)
	user := "c4c59f10-88dd-5a55-9632-5f8cc7f11939" // real user ids are UUIDs (Project.user_id stores the normalised id)
	f := NewGitBranchRepositoryFactory(sessions, gitBranchRepoFactoryEnv(map[string]string{}))

	if _, err := f.GetDefaultType(); err == nil || !strings.Contains(err.Error(), "DATABASE_TYPE") {
		t.Fatalf("GetDefaultType without DATABASE_TYPE: %v", err)
	}
	f.Getenv = gitBranchRepoFactoryEnv(map[string]string{"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "test"})
	if typ, err := f.GetDefaultType(); err != nil || typ != GitBranchRepositoryTypeMemory {
		t.Fatalf("test env: %v %v", typ, err)
	}
	f.Getenv = gitBranchRepoFactoryEnv(map[string]string{"DATABASE_TYPE": "postgresql"})
	if typ, err := f.GetDefaultType(); err != nil || typ != GitBranchRepositoryTypeORM {
		t.Fatalf("prod env: %v %v", typ, err)
	}
	f.Getenv = gitBranchRepoFactoryEnv(map[string]string{"DATABASE_TYPE": "weird"})
	if typ, err := f.GetDefaultType(); err != nil || typ != GitBranchRepositoryTypeORM {
		t.Fatalf("unknown db: %v %v", typ, err)
	}

	ormRepo, err := NewORMGitBranchRepository(sessions, &user, false)
	if err != nil {
		t.Fatal(err)
	}
	backend := &gitBranchRepoFakeBackend{repo: ormRepo}
	gitBranchRepoFactoryBackend = backend
	defer func() { gitBranchRepoFactoryBackend = nil }()

	f.Getenv = gitBranchRepoFactoryEnv(map[string]string{"DATABASE_TYPE": "postgresql"})
	created, err := f.Create(nil, &user, nil)
	if err != nil || created == nil {
		t.Fatalf("Create: %v %v", created, err)
	}
	again, err := f.Create(nil, &user, nil)
	if err != nil || again != created || backend.calls != 1 {
		t.Fatalf("cache: %v calls=%d", err, backend.calls)
	}
	ormType := GitBranchRepositoryTypeORM
	if _, err := f.Create(&ormType, &user, nil); err != nil {
		t.Fatal(err)
	}

	info, err := f.GetInfo()
	if err != nil {
		t.Fatal(err)
	}
	typesAny, _ := info.Get("available_types")
	types, _ := typesAny.([]any)
	if len(types) != 2 || types[0] != "orm" || types[1] != "memory" {
		t.Fatalf("available_types: %+v", types)
	}
	if v, _ := info.Get("cached_instances"); v != 1 {
		t.Fatalf("cached_instances: %v", v)
	}
	if v, _ := info.Get("default_type"); v != "orm" {
		t.Fatalf("default_type: %v", v)
	}

	f.ClearCache()
	if v, _ := info.Get("cached_instances"); v != 1 {
		t.Fatalf("info snapshot: %v", v)
	}
	info2, _ := f.GetInfo()
	if v, _ := info2.Get("cached_instances"); v != 0 {
		t.Fatal("cache not cleared")
	}

	called := false
	f.RegisterType("custom", func(userID *string, kwargs Kwargs) (domainrepos.GitBranchRepository, error) {
		called = true
		return nil, nil
	})
	if _, ok := f.RepositoryTypes.Get("custom"); !ok {
		t.Fatal("custom type not registered")
	}
	_ = called
}

func TestGitBranchRepositoryFactoryConvenience(t *testing.T) {
	sessions := newTestRepoEnv(t)
	user := "d55d47f0-7b6b-598f-8e08-7d7d6751f8bf" // real user ids are UUIDs (Project.user_id stores the normalised id)
	ormRepo, err := NewORMGitBranchRepository(sessions, &user, false)
	if err != nil {
		t.Fatal(err)
	}
	backend := &gitBranchRepoFakeBackend{repo: ormRepo}
	gitBranchRepoFactoryBackend = backend
	defer func() { gitBranchRepoFactoryBackend = nil }()
	t.Setenv("DATABASE_TYPE", "postgresql")
	t.Setenv("ENVIRONMENT", "production")
	DefaultGitBranchRepositoryFactory.ClearCache()

	if repo, err := GetGitBranchDefaultRepository(&user); err != nil || repo == nil {
		t.Fatalf("GetGitBranchDefaultRepository: %v %v", repo, err)
	}
	DefaultGitBranchRepositoryFactory.ClearCache()
	if repo, err := GetSQLiteGitBranchRepository(&user, nil); err != nil || repo == nil {
		t.Fatalf("GetSQLiteGitBranchRepository: %v %v", repo, err)
	}
	DefaultGitBranchRepositoryFactory.ClearCache()
	if repo, err := GetORMGitBranchRepository(&user, nil); err != nil || repo == nil {
		t.Fatalf("GetORMGitBranchRepository: %v %v", repo, err)
	}
	if backend.calls != 3 { // the cache is cleared before each of the three lookups
		t.Fatalf("backend calls = %d", backend.calls)
	}
}
