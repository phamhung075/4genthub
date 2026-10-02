package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func defaultsData(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// Python: project_id or base.get("project_id") - an empty argument falls through.
func TestBuildDefaultContextDataBranchProjectIDTruthiness(t *testing.T) {
	s := &UnifiedContextService{}
	empty := ""
	out := s.buildDefaultContextData("branch", "c", defaultsData("project_id", "base-p"), &empty, nil)
	if v, _ := out.Get("project_id"); v != "base-p" {
		t.Fatalf("project_id = %v, want base-p", v)
	}
	out = s.buildDefaultContextData("branch", "c", nil, &empty, nil)
	if v, ok := out.Get("project_id"); !ok || v != nil {
		t.Fatalf("project_id = %v, %v, want present nil", v, ok)
	}
}

// Python: git_branch_id or base.get("branch_id") or base.get("parent_branch_id").
func TestBuildDefaultContextDataTaskBranchChain(t *testing.T) {
	s := &UnifiedContextService{}
	empty := ""
	out := s.buildDefaultContextData("task", "c", defaultsData("branch_id", 0, "parent_branch_id", "par"), &empty, &empty)
	if v, _ := out.Get("branch_id"); v != "par" {
		t.Fatalf("branch_id = %v, want par", v)
	}
	out = s.buildDefaultContextData("task", "c", defaultsData("branch_id", 0), nil, nil)
	if v, ok := out.Get("branch_id"); !ok || v != nil {
		t.Fatalf("branch_id = %v, want nil (parent_branch_id absent)", v)
	}
}

// Python dict.get(key, default) keeps an explicit null; the default only covers an absent key.
func TestBuildDefaultContextDataExplicitNullKept(t *testing.T) {
	s := &UnifiedContextService{}
	out := s.buildDefaultContextData("global", "c", defaultsData("global_settings", nil), nil, nil)
	if v, ok := out.Get("global_settings"); !ok || v != nil {
		t.Fatalf("global_settings = %v, want explicit nil", v)
	}
	out = s.buildDefaultContextData("global", "c", nil, nil, nil)
	if v, _ := out.Get("global_settings"); v == nil {
		t.Fatal("absent global_settings must take the default")
	}
}

type zucsErrRepo struct{ zucsFakeRepo }

func (*zucsErrRepo) Get(context.Context, string) (any, error) { return nil, errors.New("db down") }

// Python reports a repository exception as str(e), not "Context not found".
func TestGetContextRepositoryErrorIsReported(t *testing.T) {
	s := &UnifiedContextService{repositories: map[value_objects.ContextLevel]UnifiedContextRepository{value_objects.ContextLevelProject: &zucsErrRepo{}}}
	res, _ := s.GetContext(context.Background(), "project", "p1", false, false, nil)
	if v, _ := res.Get("error"); v != "db down" {
		t.Fatalf("error = %v, want db down", v)
	}
}

func TestUpdateAndDeleteContextRepositoryErrorIsReported(t *testing.T) {
	s := &UnifiedContextService{repositories: map[value_objects.ContextLevel]UnifiedContextRepository{value_objects.ContextLevelProject: &zucsErrRepo{}}}
	upd, _ := s.UpdateContext(context.Background(), "project", "p1", defaultsData("k", "v"), false, nil)
	if v, _ := upd.Get("error"); v != "db down" {
		t.Fatalf("update error = %v, want db down", v)
	}
	del, _ := s.DeleteContext(context.Background(), "project", "p1", nil)
	if v, _ := del.Get("error"); v != "db down" {
		t.Fatalf("delete error = %v, want db down", v)
	}
}

func TestUserOrDefaultTreatsEmptyAsAbsent(t *testing.T) {
	svc, empty, set := "svc", "", "u"
	if got := userOrDefault(&empty, &svc); got != &svc {
		t.Fatal("empty user must fall back to the service user")
	}
	if got := userOrDefault(&set, &svc); got != &set {
		t.Fatal("non-empty user must win")
	}
	if got := userOrDefault(nil, &svc); got != &svc {
		t.Fatal("nil user must fall back")
	}
}

type fakeEntityLookup struct {
	project, branch string
	err             error
}

func (f fakeEntityLookup) BranchProjectID(context.Context, *string, string) (string, error) {
	return f.project, f.err
}

func (f fakeEntityLookup) TaskGitBranchID(context.Context, *string, string) (string, error) {
	return f.branch, f.err
}

func TestAutoDetectCreateIDs(t *testing.T) {
	ctx := context.Background()
	s := (&UnifiedContextService{}).WithEntityLookup(fakeEntityLookup{project: "proj-1", branch: "br-1"})

	d := defaultsData()
	s.autoDetectCreateIDs(ctx, value_objects.ContextLevelBranch, "b", d, nil)
	if v, _ := d.Get("project_id"); v != "proj-1" {
		t.Fatalf("branch project_id = %v", v)
	}
	d = defaultsData("project_id", "given")
	s.autoDetectCreateIDs(ctx, value_objects.ContextLevelBranch, "b", d, nil)
	if v, _ := d.Get("project_id"); v != "given" {
		t.Fatalf("given project_id overwritten: %v", v)
	}

	d = defaultsData()
	s.autoDetectCreateIDs(ctx, value_objects.ContextLevelTask, "t", d, nil)
	if v, _ := d.Get("git_branch_id"); v != "br-1" {
		t.Fatalf("task git_branch_id = %v", v)
	}
	d = defaultsData("parent_branch_id", "par")
	s.autoDetectCreateIDs(ctx, value_objects.ContextLevelTask, "t", d, nil)
	if _, ok := d.Get("git_branch_id"); ok {
		t.Fatal("task with parent_branch_id must not be auto-detected")
	}

	// Lookup failure and a nil lookup are swallowed: validation reports the missing id.
	d = defaultsData()
	(&UnifiedContextService{}).WithEntityLookup(fakeEntityLookup{err: errors.New("boom")}).autoDetectCreateIDs(ctx, value_objects.ContextLevelBranch, "b", d, nil)
	(&UnifiedContextService{}).autoDetectCreateIDs(ctx, value_objects.ContextLevelBranch, "b", d, nil)
	if _, ok := d.Get("project_id"); ok {
		t.Fatal("failed lookup must leave project_id unset")
	}
}

// Computed with the Python project venv: uuid5(a47ae7b9-..., "def").
func TestCompositeGlobalID(t *testing.T) {
	if got := zpUCSCompositeGlobalID("abc_def"); got != "9a92a81f-bef0-512e-a68b-14a983761efb" {
		t.Fatalf("abc_def -> %s", got)
	}
	for _, same := range []string{"plain", "a_b_c", ""} {
		if got := zpUCSCompositeGlobalID(same); got != same {
			t.Errorf("%q changed to %q", same, got)
		}
	}
}

func TestResolveProjectIDFromBranch(t *testing.T) {
	ctx := context.Background()
	if got := (&UnifiedContextService{}).resolveProjectIDFromBranch(ctx, "b"); got != "" {
		t.Fatalf("nil lookup = %q", got)
	}
	s := (&UnifiedContextService{}).WithEntityLookup(fakeEntityLookup{project: "p1"})
	if got := s.resolveProjectIDFromBranch(ctx, "b"); got != "p1" {
		t.Fatalf("got %q", got)
	}
	s = (&UnifiedContextService{}).WithEntityLookup(fakeEntityLookup{err: errors.New("x")})
	if got := s.resolveProjectIDFromBranch(ctx, "b"); got != "" {
		t.Fatalf("error lookup = %q", got)
	}
}

type zucsDupRepo struct{ zucsFakeRepo }

func (*zucsDupRepo) Get(context.Context, string) (any, error) { return nil, nil }
func (*zucsDupRepo) Create(context.Context, any) (any, error) {
	return nil, errors.New(`ERROR: duplicate key value violates unique constraint "x" (SQLSTATE 23505)`)
}

// Python treats a duplicate-key IntegrityError from a concurrent creator as success.
func TestCreateContextAtomicallyDuplicateKeyIsSuccess(t *testing.T) {
	user := "u1"
	s := &UnifiedContextService{UserID: &user, repositories: map[value_objects.ContextLevel]UnifiedContextRepository{value_objects.ContextLevelProject: &zucsDupRepo{}}}
	if !s.createContextAtomically(context.Background(), value_objects.ContextLevelProject, "p1", defaultsData("project_name", "n")) {
		t.Fatal("duplicate key must count as success")
	}
}
