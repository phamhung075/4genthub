package facades

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
)

// zpDraftFakeContextService records the last call and returns configured values.
type zpDraftFakeContextService struct {
	lastLevel   string
	lastContext string
	lastData    *entities.OrderedMap[any]
	lastUser    *string
	lastProject *string
	lastCreate  bool

	getResponse *entities.OrderedMap[any]
	getError    error
	listFilters *entities.OrderedMap[any]
}

func (s *zpDraftFakeContextService) CreateContext(_ context.Context, level, contextID string, data *entities.OrderedMap[any], userID, projectID *string, autoCreateParents bool) (*entities.OrderedMap[any], error) {
	s.lastLevel, s.lastContext, s.lastData, s.lastUser, s.lastProject, s.lastCreate = level, contextID, data, userID, projectID, autoCreateParents
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	return out, nil
}

func (s *zpDraftFakeContextService) GetContext(_ context.Context, level, contextID string, _, _ bool, _ *string) (*entities.OrderedMap[any], error) {
	s.lastLevel, s.lastContext = level, contextID
	return s.getResponse, s.getError
}

func (s *zpDraftFakeContextService) UpdateContext(_ context.Context, level, contextID string, data *entities.OrderedMap[any], _ bool, _ *string) (*entities.OrderedMap[any], error) {
	s.lastLevel, s.lastContext, s.lastData = level, contextID, data
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) DeleteContext(_ context.Context, level, contextID string, _ *string) (*entities.OrderedMap[any], error) {
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) ResolveContext(_ context.Context, level, contextID string, _ bool, _ *string) (*entities.OrderedMap[any], error) {
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) DelegateContext(_ context.Context, level, contextID, _ string, data *entities.OrderedMap[any], _ *string) (*entities.OrderedMap[any], error) {
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) AddInsight(_ context.Context, level, contextID, _ string, _, _, _ *string) (*entities.OrderedMap[any], error) {
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) AddProgress(_ context.Context, level, contextID, _ string, _ *string) (*entities.OrderedMap[any], error) {
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) ListContexts(_ context.Context, level string, filters *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	s.lastLevel, s.listFilters = level, filters
	return entities.NewOrderedMap[any](), nil
}

func (s *zpDraftFakeContextService) BootstrapContextHierarchy(_ context.Context, _, _, _ *string) (*entities.OrderedMap[any], error) {
	return entities.NewOrderedMap[any](), nil
}

func zpDraftStr(s string) *string { return &s }

func TestDraftUnifiedFacadeScopeOrder(t *testing.T) {
	svc := &zpDraftFakeContextService{}
	facade := NewUnifiedContextFacade(svc, zpDraftStr("u1"), zpDraftStr("p1"), zpDraftStr("b1"))
	data := entities.NewOrderedMap[any]()
	data.Set("project_id", "existing")
	data.Set("keep", 1)

	scoped := facade.zpUCFAddScopeToData(data)
	if got := scoped.Keys(); len(got) != 4 || got[0] != "project_id" || got[1] != "keep" || got[2] != "user_id" || got[3] != "git_branch_id" {
		t.Fatalf("scope key order = %v", got)
	}
	if v, _ := scoped.Get("project_id"); v != "existing" {
		t.Fatalf("existing project_id overwritten: %v", v)
	}
}

func TestDraftUnifiedFacadeCreatePassesScope(t *testing.T) {
	svc := &zpDraftFakeContextService{}
	facade := NewUnifiedContextFacade(svc, zpDraftStr("u1"), zpDraftStr("p1"), zpDraftStr("b1"))
	_, _ = facade.CreateContext(context.Background(), "task", "t1", nil, nil)
	if svc.lastUser == nil || *svc.lastUser != "u1" {
		t.Fatalf("effective user = %v", svc.lastUser)
	}
	if svc.lastProject == nil || *svc.lastProject != "p1" {
		t.Fatalf("project = %v", svc.lastProject)
	}
	if !svc.lastCreate {
		t.Fatalf("auto_create_parents should default to true")
	}
	if svc.lastData == nil || !svc.lastData.Has("user_id") || !svc.lastData.Has("git_branch_id") {
		t.Fatalf("scope not added: %v", svc.lastData)
	}
}

func TestDraftUnifiedFacadeErrorMapping(t *testing.T) {
	svc := &zpDraftFakeContextService{getError: &exceptions.ValidationException{}}
	facade := NewUnifiedContextFacade(svc, nil, nil, nil)
	res, _ := facade.GetContext(context.Background(), "task", "t1", false, false, nil)
	if v, _ := res.Get("error_type"); v != "validation" {
		t.Fatalf("error_type = %v", v)
	}

	svc.getError = &exceptions.ResourceNotFoundException{}
	res, _ = facade.GetContext(context.Background(), "task", "t1", false, false, nil)
	if v, _ := res.Get("error_type"); v != "not_found" {
		t.Fatalf("error_type = %v", v)
	}
}

func TestDraftUnifiedFacadeContextSummaryMissing(t *testing.T) {
	// get_context returns an unsuccessful dict (not an exception): has_context false.
	svc := &zpDraftFakeContextService{getResponse: func() *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		return m
	}()}
	facade := NewUnifiedContextFacade(svc, nil, nil, nil)
	res, _ := facade.GetContextSummary(context.Background(), "t1")
	if v, _ := res.Get("has_context"); v != false {
		t.Fatalf("has_context = %v", v)
	}
	if v, _ := res.Get("context_size"); v != 0 {
		t.Fatalf("context_size = %v", v)
	}
}

func TestDraftUnifiedFacadeListFilterBranches(t *testing.T) {
	svc := &zpDraftFakeContextService{}
	facade := NewUnifiedContextFacade(svc, zpDraftStr("u1"), zpDraftStr("p1"), zpDraftStr("b1"))

	_, _ = facade.ListContexts(context.Background(), "project", nil)
	if svc.listFilters.Has("project_id") || svc.listFilters.Has("git_branch_id") {
		t.Fatalf("project level should not add hierarchy filters: %v", svc.listFilters.Keys())
	}
	if !svc.listFilters.Has("user_id") {
		t.Fatalf("user_id filter missing")
	}

	_, _ = facade.ListContexts(context.Background(), "branch", nil)
	if svc.listFilters.Has("git_branch_id") {
		t.Fatalf("branch level should not add git_branch_id filter")
	}
	if !svc.listFilters.Has("project_id") {
		t.Fatalf("branch level should add project_id filter")
	}

	_, _ = facade.ListContexts(context.Background(), "task", nil)
	if !svc.listFilters.Has("git_branch_id") || !svc.listFilters.Has("project_id") {
		t.Fatalf("task level should add both filters: %v", svc.listFilters.Keys())
	}
}

func TestDraftTokenFacadeBranches(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "test-secret")
	t.Setenv("JWT_ISSUER", "agenthub")
	facade, err := NewTokenApplicationFacade(nil)
	if err != nil {
		t.Fatalf("NewTokenApplicationFacade: %v", err)
	}

	// generate_mcp_token_from_user quirk: MCPToken has no token_id.
	res := facade.GenerateMCPTokenFromUser(context.Background(), "u1", "a@b.c", 1, nil, nil)
	if v, _ := res.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	if v, _ := res.Get("error"); v != "'MCPToken' object has no attribute 'token_id'" {
		t.Fatalf("error = %v", v)
	}

	// validate_token quirk: JWTService has no decode_token.
	res = facade.ValidateToken(context.Background(), "opaque", nil)
	if v, _ := res.Get("error"); v != "'JWTService' object has no attribute 'decode_token'" {
		t.Fatalf("error = %v", v)
	}

	res = facade.RevokeUserTokens(context.Background(), "nobody")
	if v, _ := res.Get("success"); v != false {
		t.Fatalf("success = %v", v)
	}
	if v, _ := res.Get("message"); v != "No tokens found to revoke" {
		t.Fatalf("message = %v", v)
	}
}
