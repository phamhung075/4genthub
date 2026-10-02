package facades

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

type rafFakeResolver struct {
	autoRule string
	rulesDir string
}

func (r rafFakeResolver) GetAutoRulePath() string               { return r.autoRule }
func (r rafFakeResolver) GetRulesDirectoryFromSettings() string { return r.rulesDir }

func TestRuleFacadeManageAndValidate(t *testing.T) {
	dir := t.TempDir()
	ruleFile := filepath.Join(dir, "x.mdc")
	if err := os.WriteFile(ruleFile, []byte("héllo"), 0o644); err != nil {
		t.Fatal(err)
	}
	missing := filepath.Join(dir, "missing.mdc")
	f := NewRuleApplicationFacade(rafFakeResolver{autoRule: missing, rulesDir: dir})

	if got := f.ValidateRules("auto_rule"); got.GetAny("success") != false || got.GetAny("error") != "Auto rule file does not exist" {
		t.Fatalf("auto_rule missing: %v", got.KeysAny())
	}
	if got := f.ValidateRules("specific"); got.GetAny("success") != false {
		t.Fatalf("missing specific should fail")
	}
	got := f.ValidateRules(ruleFile)
	if got.GetAny("success") != true || got.GetAny("content_length") != 5 {
		t.Fatalf("specific validate: %v", got.KeysAny())
	}
	all := f.ValidateRules("all")
	if all.GetAny("success") != true || all.GetAny("message") != "Validated 1 rule files" {
		t.Fatalf("all validate: %v", all.GetAny("message"))
	}
	m := f.ManageRule("write", "t", "abcd")
	if m.GetAny("success") != false || m.GetAny("content_length") != 4 || m.GetAny("action") != "write" {
		t.Fatalf("manage_rule: %v", m.KeysAny())
	}
	if md := m.GetAny("metadata"); md == nil {
		t.Fatalf("metadata missing")
	}
}

type pafFakeRepo struct {
	repositories.ProjectRepository
	existing *entities.Project
}

func (r *pafFakeRepo) FindByName(ctx context.Context, name string) (*entities.Project, error) {
	return r.existing, nil
}

type pafFakeManager struct {
	repo repositories.ProjectRepository
}

func (m pafFakeManager) GetForUser(userID string) repositories.ProjectRepository { return m.repo }

type pafFakeService struct {
	createdName string
	createdDesc string
}

func (s *pafFakeService) WithUser(userID string) projectServiceWithUser { return s }

func (s *pafFakeService) CreateProject(ctx context.Context, name, description string) (*entities.OrderedMap[any], error) {
	s.createdName, s.createdDesc = name, description
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("name", name)
	return m, nil
}
func (s *pafFakeService) GetProject(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	return gbFail("get:" + projectID), nil
}
func (s *pafFakeService) GetProjectByName(ctx context.Context, name string) (*entities.OrderedMap[any], error) {
	return gbFail("getbyname:" + name), nil
}
func (s *pafFakeService) ListProjects(ctx context.Context, includeBranches bool) (*entities.OrderedMap[any], error) {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("include_branches", includeBranches)
	return m, nil
}
func (s *pafFakeService) UpdateProject(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error) {
	return gbFail("updated"), nil
}
func (s *pafFakeService) ProjectHealthCheck(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	return gbFail("health"), nil
}
func (s *pafFakeService) CleanupObsolete(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	return gbFail("cleanup"), nil
}
func (s *pafFakeService) ValidateIntegrity(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	return gbFail("integrity"), nil
}
func (s *pafFakeService) RebalanceAgents(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	return gbFail("rebalance"), nil
}
func (s *pafFakeService) DeleteProject(ctx context.Context, projectID string, force bool) (*entities.OrderedMap[any], error) {
	return gbFail("delete:" + projectID), nil
}

func TestProjectFacadeRouting(t *testing.T) {
	svc := &pafFakeService{}
	uid := "user-1"
	f := NewProjectApplicationFacade(svc, pafFakeManager{repo: &pafFakeRepo{}}, &uid)
	ctx := context.Background()

	if got, _ := f.ManageProject(ctx, "create", nil, nil, nil, nil, false); got.GetAny("error") != "Missing required field: name" {
		t.Fatalf("missing name: %v", got.GetAny("error"))
	}
	name := "proj"
	if got, _ := f.ManageProject(ctx, "create", nil, &name, nil, nil, false); got.GetAny("success") != true {
		t.Fatalf("create: %v", got.KeysAny())
	}
	if svc.createdName != "proj" || svc.createdDesc != "" {
		t.Fatalf("create passthrough: %q %q", svc.createdName, svc.createdDesc)
	}
	if got, _ := f.ManageProject(ctx, "create", nil, &name, nil, nil, false); got.GetAny("success") != true || got.GetAny("error_code") != nil {
		t.Fatalf("dup response order: %v", got.KeysAny())
	}
	if got, _ := f.ManageProject(ctx, "nope", nil, nil, nil, nil, false); got.GetAny("error") != "Invalid action: nope" {
		t.Fatalf("invalid action")
	}
	if got, _ := f.ListProjects(ctx); got.GetAny("include_branches") != true {
		t.Fatalf("list must include branches")
	}
	// route with an explicit effective user id and no instance user id
	f2 := NewProjectApplicationFacade(&pafFakeService{}, pafFakeManager{repo: &pafFakeRepo{}}, nil)
	if got, _ := f2.ManageProject(ctx, "create", nil, &name, nil, nil, false); got.GetAny("error") != "User authentication required" {
		// name is used as projectID param here; verify auth error instead
		t.Fatalf("auth: %v", got.GetAny("error"))
	}
}

func TestProjectFacadeDuplicateHint(t *testing.T) {
	existing := &entities.Project{}
	existing.Name = "dup"
	f := NewProjectApplicationFacade(&pafFakeService{}, pafFakeManager{repo: &pafFakeRepo{existing: existing}}, nil)
	uid := "u"
	f.userID = &uid
	name := "dup"
	got, _ := f.ManageProject(context.Background(), "create", nil, &name, nil, nil, false)
	if got.GetAny("error_code") != "DUPLICATE_PROJECT_NAME" {
		t.Fatalf("expected duplicate code, got %v", got.GetAny("error"))
	}
	actions := got.GetAny("suggested_actions")
	if len(actions.([]any)) != 2 {
		t.Fatalf("suggested_actions len")
	}
}
