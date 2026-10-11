package cached

// Tests for the cached repository wrappers: TTL, key namespacing, cache hits and the exact
// invalidation patterns (including their quirks). A MemoryCache with an injectable clock
// stands in for Redis; the base repositories are in-test fakes (no SQL is mocked here because
// the wrappers issue no SQL).

import (
	"context"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

func cachedTestEnv(values map[string]string) func(string) string {
	return func(k string) string { return values[k] }
}

func cachedTestClock(t *testing.T) (*time.Time, func() time.Time) {
	t.Helper()
	now := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	return &now, func() time.Time { return now }
}

func TestMemoryCacheTTLAndGlob(t *testing.T) {
	now, clock := cachedTestClock(t)
	c := NewMemoryCache(clock)
	c.SetEX("a:1", 10, "v")
	if v, ok := c.Get("a:1"); !ok || v != "v" {
		t.Fatalf("Get = %v, %v", v, ok)
	}
	*now = now.Add(11 * time.Second)
	if _, ok := c.Get("a:1"); ok {
		t.Fatal("expired entry still present")
	}

	c.SetEX("a:x", 0, 1)
	c.SetEX("a:y", 0, 2)
	if got := c.Scan("a:*"); len(got) != 2 {
		t.Fatalf("Scan = %v", got)
	}
	c.Delete("a:x")
	if got := c.Scan("a:*"); len(got) != 1 || got[0] != "a:y" {
		t.Fatalf("Scan after delete = %v", got)
	}
	if !cachedGlobMatch("a:?b*", "a:xbc") || cachedGlobMatch("a:?c*", "a:xb") {
		t.Fatal("glob match wrong")
	}
}

func TestCachedTTLFromEnvInvalid(t *testing.T) {
	if _, err := cachedTTLFromEnv(cachedTestEnv(map[string]string{"CACHE_TTL": "abc"})); err == nil {
		t.Fatal("invalid CACHE_TTL must fail")
	}
	if ttl, err := cachedTTLFromEnv(nil); err != nil || ttl != 300 {
		t.Fatalf("default ttl = %d, %v", ttl, err)
	}
}

// ---- git branch -----------------------------------------------------------------

type cachedTestBranchBase struct {
	byID     map[string]*entities.GitBranch
	getCalls int
}

func (f *cachedTestBranchBase) GetByID(_ context.Context, id string) (*entities.GitBranch, error) {
	f.getCalls++
	return f.byID[id], nil
}
func (f *cachedTestBranchBase) GetByProjectID(context.Context, string) ([]*entities.GitBranch, error) {
	return nil, nil
}
func (f *cachedTestBranchBase) FindByName(context.Context, string, string) (*entities.GitBranch, error) {
	return nil, nil
}
func (f *cachedTestBranchBase) CreateBranch(context.Context, string, string, string) (any, error) {
	return nil, nil
}
func (f *cachedTestBranchBase) CreateGitBranch(context.Context, string, string, string) (map[string]any, error) {
	return nil, nil
}
func (f *cachedTestBranchBase) UpdateBranch(_ context.Context, b *entities.GitBranch) (*entities.GitBranch, error) {
	f.byID[b.ID.String()] = b
	return b, nil
}
func (f *cachedTestBranchBase) DeleteBranch(_ context.Context, id string) (bool, error) {
	delete(f.byID, id)
	return true, nil
}
func (f *cachedTestBranchBase) ArchiveBranch(context.Context, string) (bool, error) { return true, nil }
func (f *cachedTestBranchBase) RestoreBranch(context.Context, string) (bool, error) { return true, nil }

func TestCachedGitBranchRepository(t *testing.T) {
	_, clock := cachedTestClock(t)
	cache := NewMemoryCache(clock)
	base := &cachedTestBranchBase{byID: map[string]*entities.GitBranch{}}
	repo, err := NewCachedGitBranchRepository(base, cache, cachedTestEnv(nil))
	if err != nil {
		t.Fatal(err)
	}
	id, err := tmvo.NewGitBranchId(tmvo.NewUUIDv4())
	if err != nil {
		t.Fatal(err)
	}
	branch, err := entities.NewGitBranch(entities.GitBranch{ID: &id, Name: "b", ProjectID: "p1"})
	if err != nil {
		t.Fatal(err)
	}
	base.byID[id.String()] = branch
	ctx := context.Background()
	if _, err := repo.GetByID(ctx, id.String()); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetByID(ctx, id.String()); err != nil {
		t.Fatal(err)
	}
	if base.getCalls != 1 {
		t.Fatalf("get calls = %d", base.getCalls)
	}
	branch.Description = "changed"
	if _, err := repo.UpdateBranch(ctx, branch); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetByID(ctx, id.String()); err != nil {
		t.Fatal(err)
	}
	if base.getCalls != 2 {
		t.Fatalf("after update get calls = %d, want 2", base.getCalls)
	}
}

// ---- project --------------------------------------------------------------------

type cachedTestProjectBase struct {
	byID      map[string]*entities.Project
	byList    []*entities.Project
	getCalls  int
	listCalls int
}

func (f *cachedTestProjectBase) GetByID(_ context.Context, id string) (*entities.Project, error) {
	f.getCalls++
	return f.byID[id], nil
}
func (f *cachedTestProjectBase) GetAll(context.Context) ([]*entities.Project, error) {
	f.listCalls++
	return f.byList, nil
}
func (f *cachedTestProjectBase) CreateProject(_ context.Context, p *entities.Project) (*entities.Project, error) {
	return p, nil
}
func (f *cachedTestProjectBase) UpdateProject(_ context.Context, p *entities.Project) (*entities.Project, error) {
	return p, nil
}
func (f *cachedTestProjectBase) DeleteProject(context.Context, string) (bool, error) {
	return true, nil
}

func TestCachedProjectRepository(t *testing.T) {
	_, clock := cachedTestClock(t)
	cache := NewMemoryCache(clock)
	base := &cachedTestProjectBase{byID: map[string]*entities.Project{}}
	repo, err := NewCachedProjectRepository(base, cache, cachedTestEnv(nil))
	if err != nil {
		t.Fatal(err)
	}
	project, err := entities.CreateProject("P", "")
	if err != nil {
		t.Fatal(err)
	}
	base.byID[project.ID.Value] = project
	base.byList = []*entities.Project{project}
	ctx := context.Background()

	if _, err := repo.GetAll(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetAll(ctx); err != nil {
		t.Fatal(err)
	}
	if base.listCalls != 1 {
		t.Fatalf("list calls = %d", base.listCalls)
	}
	// CreateProject invalidates list:* (which matches list:all).
	if _, err := repo.CreateProject(ctx, project); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetAll(ctx); err != nil {
		t.Fatal(err)
	}
	if base.listCalls != 2 {
		t.Fatalf("after create list calls = %d, want 2", base.listCalls)
	}
}

// ---- subtask --------------------------------------------------------------------

type cachedTestSubtaskBase struct {
	byID     map[string]*entities.Subtask
	getCalls int
}

func (f *cachedTestSubtaskBase) GetByID(_ context.Context, id string) (*entities.Subtask, error) {
	f.getCalls++
	return f.byID[id], nil
}
func (f *cachedTestSubtaskBase) GetByTaskID(context.Context, string) ([]*entities.Subtask, error) {
	return nil, nil
}
func (f *cachedTestSubtaskBase) FindByParentTaskID(context.Context, tmvo.TaskId) ([]*entities.Subtask, error) {
	return nil, nil
}
func (f *cachedTestSubtaskBase) Create(_ context.Context, s *entities.Subtask) (*entities.Subtask, error) {
	return s, nil
}
func (f *cachedTestSubtaskBase) Update(_ context.Context, s *entities.Subtask) (*entities.Subtask, error) {
	return s, nil
}
func (f *cachedTestSubtaskBase) Delete(context.Context, string) (bool, error) { return true, nil }
func (f *cachedTestSubtaskBase) DeleteByParentTaskID(context.Context, string) (int, error) {
	return 0, nil
}
func (f *cachedTestSubtaskBase) RemoveSubtask(context.Context, string) (bool, error) {
	return true, nil
}
func (f *cachedTestSubtaskBase) UpdateProgress(_ context.Context, _ string, _ int, _ *string) (*entities.Subtask, error) {
	return nil, nil
}

func TestCachedSubtaskRepository(t *testing.T) {
	_, clock := cachedTestClock(t)
	cache := NewMemoryCache(clock)
	base := &cachedTestSubtaskBase{byID: map[string]*entities.Subtask{}}
	repo, err := NewCachedSubtaskRepository(base, cache, cachedTestEnv(nil))
	if err != nil {
		t.Fatal(err)
	}
	parent, err := tmvo.NewTaskId(tmvo.NewUUIDv4())
	if err != nil {
		t.Fatal(err)
	}
	sub, err := entities.NewSubtask(entities.Subtask{ID: &parent, ParentTaskID: &parent, Title: "s"})
	if err != nil {
		t.Fatal(err)
	}
	base.byID[sub.ID.Value] = sub
	ctx := context.Background()
	if _, err := repo.GetByID(ctx, sub.ID.Value); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetByID(ctx, sub.ID.Value); err != nil {
		t.Fatal(err)
	}
	if base.getCalls != 1 {
		t.Fatalf("get calls = %d", base.getCalls)
	}
	if _, err := repo.Update(ctx, sub); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.GetByID(ctx, sub.ID.Value); err != nil {
		t.Fatal(err)
	}
	if base.getCalls != 2 {
		t.Fatalf("after update get calls = %d, want 2", base.getCalls)
	}
}

// ---- task -----------------------------------------------------------------------

type cachedTestTaskBase struct {
	byID      map[string]*entities.Task
	findCalls int
}

func (f *cachedTestTaskBase) Create(_ context.Context, task *entities.Task) (*entities.Task, error) {
	return task, nil
}
func (f *cachedTestTaskBase) Update(_ context.Context, task *entities.Task) (*entities.Task, error) {
	return task, nil
}
func (f *cachedTestTaskBase) Delete(context.Context, tmvo.TaskId) (bool, error) { return true, nil }
func (f *cachedTestTaskBase) FindByID(_ context.Context, id tmvo.TaskId) (*entities.Task, error) {
	f.findCalls++
	return f.byID[id.Value], nil
}
func (f *cachedTestTaskBase) FindAll(context.Context) ([]*entities.Task, error) { return nil, nil }

func cachedTestTask(t *testing.T, id string) *entities.Task {
	t.Helper()
	taskID, err := tmvo.NewTaskId(id)
	if err != nil {
		t.Fatal(err)
	}
	status, _ := tmvo.TaskStatusFromString("in_progress")
	priority, _ := tmvo.PriorityFromString("high")
	branch := "branch-1"
	return &entities.Task{ID: &taskID, Title: "T", Description: "D", Status: &status, Priority: &priority, GitBranchID: &branch}
}

func TestCachedTaskRepository(t *testing.T) {
	_, clock := cachedTestClock(t)
	cache := NewMemoryCache(clock)
	base := &cachedTestTaskBase{byID: map[string]*entities.Task{}}
	repo, err := NewCachedTaskRepository(base, cache, cachedTestEnv(nil))
	if err != nil {
		t.Fatal(err)
	}
	id := tmvo.NewUUIDv4()
	base.byID[id] = cachedTestTask(t, id)
	taskID, _ := tmvo.NewTaskId(id)
	ctx := context.Background()

	got, err := repo.FindByID(ctx, taskID)
	if err != nil {
		t.Fatal(err)
	}
	if got.Title != "T" || got.Status.Value != "in_progress" || got.Priority.Value != "high" || *got.GitBranchID != "branch-1" {
		t.Fatalf("task = %+v", got)
	}
	// The second lookup is served by the serialized cache entry.
	got2, err := repo.FindByID(ctx, taskID)
	if err != nil {
		t.Fatal(err)
	}
	if base.findCalls != 1 {
		t.Fatalf("find calls = %d, want 1", base.findCalls)
	}
	if got2.Title != "T" || got2.Status.Value != "in_progress" {
		t.Fatalf("cached task = %+v", got2)
	}

	// Delete invalidates "*" (all task keys).
	if _, err := repo.Delete(ctx, taskID); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.FindByID(ctx, taskID); err != nil {
		t.Fatal(err)
	}
	if base.findCalls != 3 {
		t.Fatalf("after delete find calls = %d, want 3", base.findCalls)
	}
}
