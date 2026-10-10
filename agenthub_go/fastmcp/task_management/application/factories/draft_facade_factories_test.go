package factories

import (
	"context"
	"testing"
)

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
