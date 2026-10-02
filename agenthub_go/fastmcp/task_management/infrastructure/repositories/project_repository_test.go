package repositories

// Tests for the ported ORMProjectRepository against a real PostgreSQL instance
// (AGENTHUB_TEST_PG_URL), using newTestRepoEnv.

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	projectRepoTestUserA = "11111111-1111-1111-1111-111111111111"
	projectRepoTestUserB = "22222222-2222-2222-2222-222222222222"
)

func projectRepoTestNewRepo(t *testing.T, sessions *database.SessionManager, userID string) *ORMProjectRepository {
	t.Helper()
	repo, err := NewORMProjectRepository(sessions, &userID)
	if err != nil {
		t.Fatalf("NewORMProjectRepository: %v", err)
	}
	return repo
}

func projectRepoTestCreateTask(t *testing.T, sessions *database.SessionManager, branchID, userID, status string) string {
	t.Helper()
	repo, err := NewORMRepository[database.Task]("tasks", sessions)
	if err != nil {
		t.Fatalf("task repo: %v", err)
	}
	id := tmvo.NewUUIDv4()
	_, err = repo.Create(context.Background(), NewKwargs(
		"id", id, "title", "Task", "description", "desc",
		"git_branch_id", branchID, "status", status, "priority", "high", "user_id", userID))
	if err != nil {
		t.Fatalf("create task: %v", err)
	}
	return id
}

func TestProjectRepoSaveFindDelete(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	project, err := entities.CreateProject("Alpha", "first")
	if err != nil {
		t.Fatal(err)
	}
	branch, err := project.CreateGitBranch("git-main", "Main branch", "desc")
	if err != nil {
		t.Fatal(err)
	}
	if err := repo.Save(ctx, project); err != nil {
		t.Fatalf("Save: %v", err)
	}
	projectRepoTestCreateTask(t, sessions, branch.ID.Value, user, "done")

	got, err := repo.FindByID(ctx, project.ID.Value)
	if err != nil {
		t.Fatalf("FindByID: %v", err)
	}
	if got == nil {
		t.Fatal("FindByID returned nil")
	}
	if got.Name != "Alpha" || got.Description != "first" {
		t.Fatalf("unexpected project: %+v", got)
	}
	if got.GitBranchs.Len() != 1 {
		t.Fatalf("branches = %d, want 1", got.GitBranchs.Len())
	}
	gb, _ := got.GitBranchs.Get(branch.ID.Value)
	if gb == nil {
		t.Fatal("branch not loaded")
	}
	if gb.GetCompletedTaskCount() != 1 || gb.AllTasks.Len() != 1 {
		t.Fatalf("branch stats: completed=%d all=%d", gb.GetCompletedTaskCount(), gb.AllTasks.Len())
	}
	branchRow, err := repo.projectRepoBranches.GetByID(ctx, branch.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if branchRow.TaskCount != 0 {
		t.Fatalf("branch task_count should stay 0 (Python quirk), got %d", branchRow.TaskCount)
	}

	ok, err := repo.Exists(ctx, project.ID.Value)
	if err != nil || !ok {
		t.Fatalf("Exists = %v, %v", ok, err)
	}
	n, err := repo.Count(ctx)
	if err != nil || n != 1 {
		t.Fatalf("Count = %d, %v", n, err)
	}
	all, err := repo.FindAll(ctx)
	if err != nil || len(all) != 1 {
		t.Fatalf("FindAll = %d, %v", len(all), err)
	}

	deleted, err := repo.Delete(ctx, project.ID.Value)
	if err != nil || !deleted {
		t.Fatalf("Delete = %v, %v", deleted, err)
	}
	gone, err := repo.FindByID(ctx, project.ID.Value)
	if err != nil || gone != nil {
		t.Fatalf("FindByID after delete = %v, %v", gone, err)
	}
	if deleted, _ := repo.Delete(ctx, project.ID.Value); deleted {
		t.Fatal("second Delete should be false")
	}
}

func TestProjectRepoUserIsolation(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	repoA := projectRepoTestNewRepo(t, sessions, projectRepoTestUserA)
	repoB := projectRepoTestNewRepo(t, sessions, projectRepoTestUserB)
	userA, userB := projectRepoTestUserA, projectRepoTestUserB

	if _, err := repoA.CreateProject(ctx, "Alpha", "a", &userA); err != nil {
		t.Fatal(err)
	}
	b, err := repoB.CreateProject(ctx, "Beta", "b", &userB)
	if err != nil {
		t.Fatal(err)
	}

	if got, _ := repoA.FindByID(ctx, b.ID.Value); got != nil {
		t.Fatal("user A must not see user B's project")
	}
	if got, _ := repoA.FindByName(ctx, "Beta"); got != nil {
		t.Fatal("user A must not find user B's project by name")
	}
	all, err := repoA.FindAll(ctx)
	if err != nil || len(all) != 1 || all[0].Name != "Alpha" {
		t.Fatalf("FindAll for A = %+v, %v", all, err)
	}
	// count/exists on the Python ORM repository are not user scoped.
	if n, _ := repoA.Count(ctx); n != 2 {
		t.Fatalf("unfiltered Count = %d, want 2", n)
	}
	if ok, _ := repoA.Exists(ctx, b.ID.Value); !ok {
		t.Fatal("unfiltered Exists should be true")
	}
	byStatus, err := repoA.FindProjectsByStatus(ctx, "active")
	if err != nil || len(byStatus) != 1 {
		t.Fatalf("FindProjectsByStatus = %d, %v", len(byStatus), err)
	}
}

func TestProjectRepoUpdateDomain(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	created, err := repo.CreateProject(ctx, "Before", "d", &user)
	if err != nil {
		t.Fatal(err)
	}
	created.Name = "After"
	if err := repo.Update(ctx, created); err != nil {
		t.Fatalf("Update: %v", err)
	}
	got, _ := repo.FindByID(ctx, created.ID.Value)
	if got == nil || got.Name != "After" {
		t.Fatalf("Update did not persist: %+v", got)
	}

	missing := tmvo.GenerateNewProjectId()
	phantom, _ := entities.NewProject(entities.Project{ID: &missing, Name: "ghost"})
	if err := repo.Update(ctx, phantom); err == nil {
		t.Fatal("Update of a missing project must fail")
	}
}

func TestProjectRepoUpdateProject(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	created, err := repo.CreateProject(ctx, "Before", "d", &user)
	if err != nil {
		t.Fatal(err)
	}
	updated, err := repo.UpdateProject(ctx, created.ID.Value, NewKwargs("name", "Direct", "description", "x"))
	if err != nil {
		t.Fatalf("UpdateProject: %v", err)
	}
	if updated.Name != "Direct" || updated.Description != "x" {
		t.Fatalf("unexpected update: %+v", updated)
	}

	entity, err := entities.CreateProject("FromEntity", "entity desc")
	if err != nil {
		t.Fatal(err)
	}
	entity.ID = created.ID
	updated2, err := repo.UpdateProject(ctx, created.ID.Value, NewKwargs("entity", entity))
	if err != nil {
		t.Fatalf("UpdateProject(entity): %v", err)
	}
	if updated2.Name != "FromEntity" {
		t.Fatalf("entity update name = %q", updated2.Name)
	}
	if _, err := repo.UpdateProject(ctx, tmvo.NewUUIDv4(), NewKwargs()); err == nil {
		t.Fatal("UpdateProject of missing project must fail")
	}
}

func TestProjectRepoFindProjectsWithAgentAndHealth(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	project, err := entities.CreateProject("Agent project", "d")
	if err != nil {
		t.Fatal(err)
	}
	branch, err := project.CreateGitBranch("git-main", "Main", "d")
	if err != nil {
		t.Fatal(err)
	}
	agent := tmvo.NewUUIDv4()
	branch.AssignedAgentID = &agent
	if err := repo.Save(ctx, project); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateProject(ctx, "Plain project", "d", &user); err != nil {
		t.Fatal(err)
	}

	// Python's find_projects_with_agent uses SELECT DISTINCT over the entity, which
	// PostgreSQL rejects for the json metadata column; that quirk is preserved.
	if _, err := repo.FindProjectsWithAgent(ctx, agent); err == nil {
		t.Fatal("FindProjectsWithAgent must fail on json DISTINCT (Python quirk)")
	}

	summary, err := repo.GetProjectHealthSummary(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if summary["total_projects"] != 2 || summary["total_branches"] != 1 || summary["projects_with_branches"] != 1 {
		t.Fatalf("health summary = %+v", summary)
	}
	if summary["assigned_branches"] != 1 || summary["unassigned_branches"] != 0 {
		t.Fatalf("health branches = %+v", summary)
	}
}

func TestProjectRepoUnassignAgentFromTree(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	project, _ := entities.CreateProject("Unassign", "d")
	branch, _ := project.CreateGitBranch("git-main", "Main", "d")
	agent := tmvo.NewUUIDv4()
	branch.AssignedAgentID = &agent
	if err := repo.Save(ctx, project); err != nil {
		t.Fatal(err)
	}

	result, err := repo.UnassignAgentFromTree(ctx, project.ID.Value, agent, branch.ID.Value)
	if err != nil {
		t.Fatalf("UnassignAgentFromTree: %v", err)
	}
	if result["success"] != true || result["unassigned_agent_id"] != agent {
		t.Fatalf("unexpected result: %+v", result)
	}
	got, _ := repo.FindByID(ctx, project.ID.Value)
	gb, _ := got.GitBranchs.Get(branch.ID.Value)
	if gb.AssignedAgentID != nil {
		t.Fatal("assigned_agent_id should be cleared")
	}

	if _, err := repo.UnassignAgentFromTree(ctx, project.ID.Value, agent, branch.ID.Value); err == nil {
		t.Fatal("second unassign must fail (DatabaseException)")
	}
}

func TestProjectRepoListProjectsPagination(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	base := time.Date(2025, 1, 1, 0, 0, 0, 0, time.UTC)
	var ids []string
	for i := 0; i < 3; i++ {
		p, err := repo.CreateProject(ctx, "P"+string(rune('A'+i)), "d", &user)
		if err != nil {
			t.Fatal(err)
		}
		ts := base.Add(time.Duration(i) * time.Hour)
		if _, err := repo.ORMRepository.Update(ctx, p.ID.Value, NewKwargs("created_at", ts)); err != nil {
			t.Fatal(err)
		}
		ids = append(ids, p.ID.Value)
	}

	page, err := repo.ListProjects(ctx, nil, 2, 0)
	if err != nil || len(page) != 2 {
		t.Fatalf("page0 = %d, %v", len(page), err)
	}
	if page[0].ID.Value != ids[2] || page[1].ID.Value != ids[1] {
		t.Fatalf("ordering wrong: %s, %s", page[0].ID.Value, page[1].ID.Value)
	}
	page2, err := repo.ListProjects(ctx, nil, 2, 2)
	if err != nil || len(page2) != 1 || page2[0].ID.Value != ids[0] {
		t.Fatalf("page2 = %+v, %v", page2, err)
	}
	status := "active"
	filtered, err := repo.ListProjects(ctx, &status, 100, 0)
	if err != nil || len(filtered) != 3 {
		t.Fatalf("status filter = %d, %v", len(filtered), err)
	}
	missing := "missing"
	empty, err := repo.ListProjects(ctx, &missing, 100, 0)
	if err != nil || len(empty) != 0 {
		t.Fatalf("missing status = %d, %v", len(empty), err)
	}
}

func TestProjectRepoSearchNamesAndStats(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	project, _ := entities.CreateProject("Alpha One", "searchable")
	branch, _ := project.CreateGitBranch("git-main", "Main", "d")
	if err := repo.Save(ctx, project); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.CreateProject(ctx, "Beta Two", "other", &user); err != nil {
		t.Fatal(err)
	}

	found, err := repo.SearchProjects(ctx, "alpha", 50)
	if err != nil || len(found) != 1 || found[0].Name != "Alpha One" {
		t.Fatalf("SearchProjects = %+v, %v", found, err)
	}
	desc, err := repo.SearchProjects(ctx, "other", 50)
	if err != nil || len(desc) != 1 || desc[0].Name != "Beta Two" {
		t.Fatalf("SearchProjects description = %+v, %v", desc, err)
	}
	byName, err := repo.GetProjectByName(ctx, "Beta Two")
	if err != nil || byName == nil {
		t.Fatalf("GetProjectByName = %+v, %v", byName, err)
	}
	byID, err := repo.GetProject(ctx, project.ID.Value)
	if err != nil || byID == nil || byID.Name != "Alpha One" {
		t.Fatalf("GetProject = %+v, %v", byID, err)
	}

	// task_count columns are 0; set them to exercise the statistics sums.
	if _, err := repo.projectRepoBranches.Update(ctx, branch.ID.Value,
		NewKwargs("task_count", 5, "completed_task_count", 2)); err != nil {
		t.Fatal(err)
	}
	stats, err := repo.GetProjectStatistics(ctx, project.ID.Value)
	if err != nil {
		t.Fatal(err)
	}
	if stats.GetAny("total_tasks") != int64(5) || stats.GetAny("completed_tasks") != int64(2) {
		t.Fatalf("stats = %+v", stats)
	}
	if stats.GetAny("completion_percentage") != float64(40) {
		t.Fatalf("completion = %v", stats.GetAny("completion_percentage"))
	}
	if _, err := repo.GetProjectStatistics(ctx, tmvo.NewUUIDv4()); err == nil {
		t.Fatal("statistics of missing project must fail")
	}
}

func TestProjectRepoCheckNameExistsAndWithUser(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	p, err := repo.CreateProject(ctx, "Spaced Name", "d", &user)
	if err != nil {
		t.Fatal(err)
	}
	taken, err := repo.CheckNameExists(ctx, "  Spaced Name  ", nil)
	if err != nil || !taken {
		t.Fatalf("CheckNameExists = %v, %v", taken, err)
	}
	excluded, err := repo.CheckNameExists(ctx, "Spaced Name", &p.ID.Value)
	if err != nil || excluded {
		t.Fatalf("CheckNameExists exclude = %v, %v", excluded, err)
	}

	scoped, err := repo.WithUser(projectRepoTestUserB)
	if err != nil {
		t.Fatal(err)
	}
	all, err := scoped.FindAll(ctx)
	if err != nil || len(all) != 0 {
		t.Fatalf("WithUser FindAll = %d, %v", len(all), err)
	}
}

func TestProjectRepoUpdateStatistics(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	p, err := repo.CreateProject(ctx, "Stats", "d", &user)
	if err != nil {
		t.Fatal(err)
	}
	branchCount := 2
	ok, err := repo.UpdateStatistics(ctx, p.ID.Value, &branchCount, nil, nil, nil, nil, nil)
	if err != nil || !ok {
		t.Fatalf("UpdateStatistics = %v, %v", ok, err)
	}
	ok, err = repo.UpdateStatistics(ctx, tmvo.NewUUIDv4(), nil, nil, nil, nil, nil, nil)
	if err != nil || ok {
		t.Fatalf("UpdateStatistics(missing) = %v, %v", ok, err)
	}
}

func TestProjectRepoSaveUpdatesExistingAndAddsBranch(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)

	project, _ := entities.CreateProject("Original", "d")
	if _, err := project.CreateGitBranch("git-main", "Main", "d"); err != nil {
		t.Fatal(err)
	}
	if err := repo.Save(ctx, project); err != nil {
		t.Fatal(err)
	}
	project.Name = "Renamed"
	if _, err := project.CreateGitBranch("git-second", "Second", "d"); err != nil {
		t.Fatal(err)
	}
	if err := repo.Save(ctx, project); err != nil {
		t.Fatal(err)
	}
	got, _ := repo.FindByID(ctx, project.ID.Value)
	if got.Name != "Renamed" || got.GitBranchs.Len() != 2 {
		t.Fatalf("after second save: name=%q branches=%d", got.Name, got.GitBranchs.Len())
	}
	row, _ := repo.ORMRepository.GetByID(ctx, project.ID.Value)
	var meta map[string]any
	if err := json.Unmarshal(row.Metadata, &meta); err != nil {
		t.Fatal(err)
	}
	if meta["git_branchs_count"] != float64(2) {
		t.Fatalf("model_metadata = %+v", meta)
	}
}

// ---- selective fields ----------------------------------------------------------

type projectRepoTestFieldSelector struct {
	fields    []string
	optimized bool
	cached    *entities.OrderedMap[any]
	metrics   map[string]int
}

func (s *projectRepoTestFieldSelector) GetProjectFields(projectID string, fields any) *entities.OrderedMap[any] {
	spec := entities.NewOrderedMap[any]()
	spec.Set("entity_type", "project")
	spec.Set("entity_id", projectID)
	spec.Set("fields", s.fields)
	spec.Set("optimized", s.optimized)
	return spec
}

func (s *projectRepoTestFieldSelector) GetCachedFields(projectID string, fields []string) *entities.OrderedMap[any] {
	return s.cached
}

func (s *projectRepoTestFieldSelector) CacheFieldMapping(projectID string, fields []string, data *entities.OrderedMap[any]) {
	s.cached = data
}

func (s *projectRepoTestFieldSelector) GetOptimalFieldSet(operation, entityType string) any {
	return "minimal"
}

func (s *projectRepoTestFieldSelector) GetMetrics() map[string]int { return s.metrics }

func (s *projectRepoTestFieldSelector) EstimateSavings(entityType string, fieldSet any) map[string]float64 {
	return map[string]float64{"field_reduction": 33.33}
}

func TestProjectRepoSelectiveFields(t *testing.T) {
	sessions := newTestRepoEnv(t)
	ctx := context.Background()
	user := projectRepoTestUserA
	repo := projectRepoTestNewRepo(t, sessions, user)
	if _, err := repo.CreateProject(ctx, "Selective", "d", &user); err != nil {
		t.Fatal(err)
	}
	if repo.FieldSelector == nil {
		if _, err := repo.GetProjectSelectiveFields(ctx, tmvo.NewUUIDv4(), nil); err != nil {
			t.Fatalf("nil selector should return nil: %v", err)
		}
	}

	selector := &projectRepoTestFieldSelector{
		fields: []string{"id", "name", "status"}, optimized: true,
		metrics: map[string]int{"queries_optimized": 3},
	}
	repo.FieldSelector = selector
	got, err := repo.FindByName(ctx, "Selective")
	if err != nil || got == nil {
		t.Fatal(err)
	}
	data, err := repo.GetProjectSelectiveFields(ctx, got.ID.Value, nil)
	if err != nil || data == nil {
		t.Fatalf("GetProjectSelectiveFields = %+v, %v", data, err)
	}
	if data.Len() != 3 || data.GetAny("name") != "Selective" {
		t.Fatalf("selective data = %+v", data)
	}
	if selector.cached == nil {
		t.Fatal("expected cache write")
	}
	// cached path
	again, err := repo.GetProjectSelectiveFields(ctx, got.ID.Value, nil)
	if err != nil || again == nil {
		t.Fatal(err)
	}

	list, err := repo.ListProjectsSelectiveFields(ctx, nil, nil, 100, 0)
	if err != nil || len(list) != 1 || list[0].GetAny("name") != "Selective" {
		t.Fatalf("ListProjectsSelectiveFields = %+v, %v", list, err)
	}
	if m := repo.GetFieldSelectorMetrics(); m["queries_optimized"] != 3 {
		t.Fatalf("metrics = %+v", m)
	}
	if savings := repo.EstimateFieldOptimizationSavings("minimal"); savings["field_reduction"] != 33.33 {
		t.Fatalf("savings = %+v", savings)
	}

	// non-optimized fallback path
	repo.FieldSelector = &projectRepoTestFieldSelector{optimized: false}
	fallback, err := repo.GetProjectSelectiveFields(ctx, got.ID.Value, nil)
	if err != nil || fallback == nil || fallback.GetAny("status") != "active" {
		t.Fatalf("fallback = %+v, %v", fallback, err)
	}
	if _, err := repo.GetProjectSelectiveFields(ctx, tmvo.NewUUIDv4(), nil); err != nil {
		t.Fatalf("missing fallback: %v", err)
	}
}
