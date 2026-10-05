package intelligence

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	domainintel "agenthub/fastmcp/task_management/domain/services/intelligence"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type draftIntelTaskRepo struct {
	tasks []*entities.Task
}

func (r *draftIntelTaskRepo) GetTasksByBranch(ctx context.Context, gitBranchID string) ([]*entities.Task, error) {
	return r.tasks, nil
}
func (r *draftIntelTaskRepo) GetTaskByID(ctx context.Context, taskID string) (*entities.Task, error) {
	return nil, nil
}

type draftIntelProjectRepo struct{}

func (r *draftIntelProjectRepo) GetProjectByID(ctx context.Context, projectID string) (*entities.Project, error) {
	return nil, nil
}

func draftIntelSelector(t *testing.T) *domainintel.IntelligentContextSelector {
	t.Helper()
	selector, err := domainintel.NewIntelligentContextSelector(domainintel.SelectorConfig{
		SemanticModel:       "all-MiniLM-L6-v2",
		SimilarityThreshold: 0.5,
		DefaultTokenBudget:  2000,
		MaxSelectionTimeMs:  200.0,
		TargetHitRate:       0.9,
		TargetSizeReduction: 0.5,
		EnableCaching:       true,
		CacheTTLSeconds:     300,
		EnableMetrics:       true,
		CacheDir:            t.TempDir(),
	})
	if err != nil {
		t.Fatalf("selector: %v", err)
	}
	return selector
}

func TestDraftIntelRequestDefaultTokens(t *testing.T) {
	request := NewIntelligentSelectionRequest("q")
	if request.MaxTokens != 2000 {
		t.Fatalf("max_tokens = %d", request.MaxTokens)
	}
}

func TestDraftIntelTaskDetailsQuirk(t *testing.T) {
	taskID := value_objects.GenerateNewTaskId()
	task, err := entities.NewTask(entities.Task{ID: &taskID, Title: "T", Description: "d"})
	if err != nil {
		t.Fatalf("NewTask: %v", err)
	}
	uc, err := NewIntelligentContextSelectionUseCase(nil,
		&draftIntelTaskRepo{tasks: []*entities.Task{task}},
		&draftIntelProjectRepo{}, draftIntelSelector(t))
	if err != nil {
		t.Fatalf("NewIntelligentContextSelectionUseCase: %v", err)
	}

	gitBranchID := "branch-1"
	request := NewIntelligentSelectionRequest("query")
	request.GitBranchID = &gitBranchID
	response := uc.Execute(context.Background(), request)

	if response.Success {
		t.Fatal("expected failure")
	}
	if response.ErrorMessage == nil || *response.ErrorMessage != "'Task' object has no attribute 'details'" {
		t.Fatalf("error_message = %v", response.ErrorMessage)
	}
	if response.PerformanceMetrics == nil || response.PerformanceMetrics.Len() != 0 {
		t.Fatalf("performance_metrics = %+v", response.PerformanceMetrics)
	}
	if len(response.Recommendations) != 0 || len(response.SelectedContexts) != 0 {
		t.Fatalf("response = %+v", response)
	}
}
