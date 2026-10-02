package factories

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestDraftAgentFacadeFactoryRequiresUser(t *testing.T) {
	factory := NewAgentFacadeFactory(nil)
	_, err := factory.CreateAgentFacade("p1", nil)
	if err == nil || err.Error() != "user_id is required for agent facade creation (no fallback allowed for DDD compliance)" {
		t.Fatalf("err = %v", err)
	}
	_, err = factory.CreateFacade("")
	if err == nil || err.Error() != "Project ID is required. No fallback to default project allowed per DDD principles." {
		t.Fatalf("err = %v", err)
	}
	_, err = factory.Create()
	if err == nil || err.Error() != "Cannot create agent facade: Project ID is required. No fallback to default project allowed per DDD principles." {
		t.Fatalf("err = %v", err)
	}
}

func TestDraftAgentFacadeFactoryMockFallbackAndCache(t *testing.T) {
	factory := NewAgentFacadeFactory(nil)
	user := "user-1"
	facade, err := factory.CreateAgentFacade("p1", &user)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if _, ok := facade.(*MockAgentApplicationFacade); !ok {
		t.Fatalf("expected mock, got %T", facade)
	}
	cached := factory.GetCachedFacade("p1")
	if cached != facade {
		t.Fatalf("facade not cached")
	}
	mock := facade.(*MockAgentApplicationFacade)
	res := mock.ListAgents("p1")
	if v, _ := res.Get("success"); v != true {
		t.Fatalf("success = %v", v)
	}
	agentsAny, _ := res.Get("agents")
	agents := agentsAny.([]any)
	if len(agents) != 2 {
		t.Fatalf("agents len = %d", len(agents))
	}
	first := agents[0].(*entities.OrderedMap[any])
	if got := first.Keys(); len(got) != 4 || got[0] != "id" || got[1] != "name" || got[2] != "project_id" || got[3] != "call_agent" {
		t.Fatalf("agent key order = %v", got)
	}
	if v, _ := first.Get("id"); v != "mock-agent-1" {
		t.Fatalf("id = %v", v)
	}
	factory.ClearCache()
	if factory.GetCachedFacade("p1") != nil {
		t.Fatalf("cache not cleared")
	}
}

func TestDraftProjectFacadeFactoryRequiresProvider(t *testing.T) {
	factory := &ProjectFacadeFactory{facadesCache: map[string]any{}}
	_, err := factory.CreateProjectFacade(context.Background(), "user-1")
	if err == nil || err.Error() != "Repository provider is required for project facade creation" {
		t.Fatalf("err = %v", err)
	}
	_, err = factory.CreateProjectFacade(context.Background(), "")
	if err == nil {
		t.Fatalf("empty user should fail validation")
	}
}

func TestDraftGitBranchFacadeFactoryRequiresProject(t *testing.T) {
	factory := &GitBranchFacadeFactory{facadesCache: map[string]any{}}
	_, err := factory.CreateFacade(context.Background(), nil, nil)
	if err == nil || err.Error() != "project_id is required for git branch facade creation (no fallback allowed for DDD compliance)" {
		t.Fatalf("err = %v", err)
	}
}

func TestDraftTaskFacadeFactoryRequiresUser(t *testing.T) {
	factory := &TaskFacadeFactory{}
	_, err := factory.CreateTaskFacade(context.Background(), nil, nil, nil)
	if err == nil {
		t.Fatalf("nil user should fail validation")
	}
	_, err = factory.CreateTaskFacadeWithGitBranchID(context.Background(), "p1", "main", nil, nil)
	if err == nil {
		t.Fatalf("nil user should fail validation")
	}
}

func TestDraftTokenFacadeFactory(t *testing.T) {
	t.Setenv("JWT_SECRET_KEY", "test-secret")
	factory := &TokenFacadeFactory{}
	facade, err := factory.CreateTokenFacadeWithoutRepository()
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if facade == nil {
		t.Fatalf("nil facade")
	}
}
