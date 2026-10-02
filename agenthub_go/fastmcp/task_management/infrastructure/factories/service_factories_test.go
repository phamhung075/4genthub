package factories

import (
	"strings"
	"testing"

	domainrepositories "agenthub/fastmcp/task_management/domain/repositories"
)

func TestRuleServiceFactoryRequiresRepository(t *testing.T) {
	f := NewRuleServiceFactory(nil)
	_, err := f.CreateRuleApplicationService()
	if err == nil || !strings.Contains(err.Error(), "RuleRepository is required") {
		t.Fatalf("err = %v", err)
	}
}

func TestProjectServiceFactoryRepositoryAccessors(t *testing.T) {
	f := NewProjectServiceFactory(nil, nil)
	if f.GetProjectRepository() != nil {
		t.Fatal("expected nil repository")
	}
	var repo domainrepositories.ProjectRepository
	f.SetProjectRepository(repo)
	if f.GetProjectRepository() != nil {
		t.Fatal("expected still nil")
	}
}
