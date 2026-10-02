package use_cases

import (
	"context"
	"errors"
	"fmt"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AITaskCreationRequest is the request for AI-enhanced task creation.
type AITaskCreationRequest struct {
	Title           string
	Description     *string
	GitBranchID     string
	Priority        *string
	Assignees       []string
	EstimatedEffort *string
	Labels          []string
	Dependencies    []string
	UserID          *string

	EnableAIBreakdown     bool
	EnableSmartAssignment bool
	EnableAutoSubtasks    bool
	PlanningContext       string
	AIRequirements        *string
}

// NewAITaskCreationRequest applies the Python dataclass defaults: priority
// "medium" and planning_context "new_feature".
func NewAITaskCreationRequest(title, description, gitBranchID string) *AITaskCreationRequest {
	medium := "medium"
	return &AITaskCreationRequest{
		Title:           title,
		Description:     &description,
		GitBranchID:     gitBranchID,
		Priority:        &medium,
		PlanningContext: "new_feature",
		Assignees:       []string{},
		Labels:          []string{},
		Dependencies:    []string{},
	}
}

// AITaskFacade is the TaskApplicationFacade surface used by the use case.
type AITaskFacade interface {
	GetTask(ctx context.Context, taskID string, includeContext bool) (*entities.OrderedMap[any], error)
}

// AITaskIntegrationService is the AITaskIntegrationService surface used by the use
// case. The Python class does not exist yet in Go, so it is injected.
type AITaskIntegrationService interface {
	EnhanceTaskCreation(ctx context.Context, request *dtostask.CreateTaskRequest,
		enableAIBreakdown, enableSmartAssignment bool) (*entities.OrderedMap[any], error)
	CreateAIEnhancedTaskPlan(ctx context.Context, requirements, title, description,
		gitBranchID, planningContext string, autoCreateTasks bool,
		userID *string) (*entities.OrderedMap[any], error)
	AddAIInsightsToTaskResponse(ctx context.Context, taskResponse *entities.OrderedMap[any],
		action string) (*entities.OrderedMap[any], error)
	GenerateTaskInsights(ctx context.Context, title, description, action string) (*entities.OrderedMap[any], error)
}

// AITaskCreationUseCase ports ai_task_creation_use_case.AITaskCreationUseCase.
type AITaskCreationUseCase struct {
	taskRepository       repositories.TaskRepository
	taskFacade           AITaskFacade
	aiIntegrationService AITaskIntegrationService
}

// NewAITaskCreationUseCase builds the use case. Python constructs its
// AITaskIntegrationService from the facade; the service is injected instead
// because that module has no Go port yet.
func NewAITaskCreationUseCase(taskRepository repositories.TaskRepository,
	taskFacade AITaskFacade, aiIntegrationService AITaskIntegrationService) *AITaskCreationUseCase {
	return &AITaskCreationUseCase{
		taskRepository:       taskRepository,
		taskFacade:           taskFacade,
		aiIntegrationService: aiIntegrationService,
	}
}

// Execute creates a task through the AI integration service and adds the AI
// enhancement metadata.
func (uc *AITaskCreationUseCase) Execute(ctx context.Context,
	request *AITaskCreationRequest) *entities.OrderedMap[any] {

	createRequest, err := dtostask.NewCreateTaskRequest(dtostask.CreateTaskRequest{
		Title:           request.Title,
		Description:     request.Description,
		GitBranchID:     request.GitBranchID,
		Priority:        request.Priority,
		Assignees:       orEmptyStrings(request.Assignees),
		EstimatedEffort: strOrEmpty(request.EstimatedEffort),
		Labels:          orEmptyStrings(request.Labels),
		Dependencies:    orEmptyStrings(request.Dependencies),
		UserID:          request.UserID,
	})
	if err != nil {
		return aiTaskError("AI task creation failed: "+err.Error(), err)
	}

	result, err := uc.aiIntegrationService.EnhanceTaskCreation(ctx, createRequest,
		request.EnableAIBreakdown, request.EnableSmartAssignment)
	if err != nil {
		return aiTaskError("AI task creation failed: "+err.Error(), err)
	}
	if result == nil {
		result = entities.NewOrderedMap[any]()
	}

	if request.AIRequirements != nil && value_objects.PyTruthy(*request.AIRequirements) && request.EnableAutoSubtasks {
		description := "AI-enhanced task"
		if request.Description != nil && value_objects.PyTruthy(*request.Description) {
			description = *request.Description
		}
		planResult, err := uc.aiIntegrationService.CreateAIEnhancedTaskPlan(ctx,
			*request.AIRequirements, request.Title, description, request.GitBranchID,
			request.PlanningContext, false, request.UserID)
		if err != nil {
			return aiTaskError("AI task creation failed: "+err.Error(), err)
		}
		if planResult != nil {
			success, _ := planResult.Get("success")
			if value_objects.PyTruthy(success) {
				if v, ok := planResult.Get("task_plan"); ok {
					result.Set("ai_plan", v)
				}
				if v, ok := planResult.Get("ai_insights"); ok {
					result.Set("ai_planning_insights", v)
				}
			} else {
				v, _ := planResult.Get("error")
				result.Set("ai_plan_error", v)
			}
		}
	}

	features := entities.NewOrderedMap[any]()
	features.Set("breakdown_enabled", request.EnableAIBreakdown)
	features.Set("smart_assignment_enabled", request.EnableSmartAssignment)
	features.Set("auto_subtasks_enabled", request.EnableAutoSubtasks)
	features.Set("ai_requirements_provided",
		request.AIRequirements != nil && value_objects.PyTruthy(*request.AIRequirements))
	result.Set("ai_enhanced_features", features)
	return result
}

// CreateFullAIPlan creates a full AI-generated task plan with auto-created tasks.
func (uc *AITaskCreationUseCase) CreateFullAIPlan(ctx context.Context, requirements, title,
	description, gitBranchID, contextName string, userID *string) *entities.OrderedMap[any] {
	result, err := uc.aiIntegrationService.CreateAIEnhancedTaskPlan(ctx, requirements, title,
		description, gitBranchID, contextName, true, userID)
	if err != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", fmt.Sprintf("AI plan creation failed: %s", err.Error()))
		return out
	}
	return result
}

// EnhanceExistingTask enhances an existing task with AI insights.
func (uc *AITaskCreationUseCase) EnhanceExistingTask(ctx context.Context, taskID string,
	enhancementOptions map[string]any) *entities.OrderedMap[any] {

	taskResult, err := uc.taskFacade.GetTask(ctx, taskID, true)
	if err != nil {
		return aiTaskError("Task enhancement failed: "+err.Error(), err)
	}
	if taskResult == nil {
		return entities.NewOrderedMap[any]()
	}
	success, _ := taskResult.Get("success")
	if !value_objects.PyTruthy(success) {
		return taskResult
	}
	taskData, _ := taskResult.Get("task")

	enhancedResult, err := uc.aiIntegrationService.AddAIInsightsToTaskResponse(ctx, taskResult, "enhance")
	if err != nil {
		return aiTaskError("Task enhancement failed: "+err.Error(), err)
	}
	if enhancedResult == nil {
		enhancedResult = entities.NewOrderedMap[any]()
	}

	if value_objects.PyTruthy(enhancementOptions["analyze_complexity"]) {
		complexity, err := uc.analyzeTaskComplexity(ctx, taskData)
		if err != nil {
			return aiTaskError("Task enhancement failed: "+err.Error(), err)
		}
		enhancedResult.Set("complexity_analysis", complexity)
	}
	if value_objects.PyTruthy(enhancementOptions["suggest_optimizations"]) {
		optimizations, err := uc.suggestTaskOptimizations(ctx, taskData)
		if err != nil {
			return aiTaskError("Task enhancement failed: "+err.Error(), err)
		}
		enhancedResult.Set("optimization_suggestions", optimizations)
	}
	if value_objects.PyTruthy(enhancementOptions["identify_risks"]) {
		risks, err := uc.identifyTaskRisks(ctx, taskData)
		if err != nil {
			return aiTaskError("Task enhancement failed: "+err.Error(), err)
		}
		enhancedResult.Set("risk_analysis", risks)
	}
	return enhancedResult
}

func (uc *AITaskCreationUseCase) analyzeTaskComplexity(ctx context.Context, taskData any) (any, error) {
	title := aiTaskDataString(taskData, "title")
	description := aiTaskDataString(taskData, "description")
	aiInsights, err := uc.aiIntegrationService.GenerateTaskInsights(ctx, title, description, "analyze")
	if err != nil {
		return nil, err
	}
	if aiInsights != nil {
		if v, ok := aiInsights.Get("complexity_analysis"); ok {
			return v, nil
		}
	}
	return entities.NewOrderedMap[any](), nil
}

func (uc *AITaskCreationUseCase) suggestTaskOptimizations(ctx context.Context, taskData any) ([]string, error) {
	title := aiTaskDataString(taskData, "title")
	description := aiTaskDataString(taskData, "description")
	aiInsights, err := uc.aiIntegrationService.GenerateTaskInsights(ctx, title, description, "optimize")
	if err != nil {
		return nil, err
	}
	if aiInsights != nil {
		if v, ok := aiInsights.Get("optimization_suggestions"); ok {
			return useCasePyStringList(v), nil
		}
	}
	return []string{}, nil
}

func (uc *AITaskCreationUseCase) identifyTaskRisks(ctx context.Context, taskData any) ([]string, error) {
	title := aiTaskDataString(taskData, "title")
	description := aiTaskDataString(taskData, "description")
	aiInsights, err := uc.aiIntegrationService.GenerateTaskInsights(ctx, title, description, "analyze")
	if err != nil {
		return nil, err
	}
	if aiInsights != nil {
		if v, ok := aiInsights.Get("potential_risks"); ok {
			return useCasePyStringList(v), nil
		}
	}
	return []string{}, nil
}

func orEmptyStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

func strOrEmpty(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func aiTaskDataString(taskData any, key string) string {
	switch data := taskData.(type) {
	case *entities.OrderedMap[any]:
		if v, ok := data.Get(key); ok && v != nil {
			return value_objects.PyStr(v)
		}
	case map[string]any:
		if v, ok := data[key]; ok && v != nil {
			return value_objects.PyStr(v)
		}
	}
	return ""
}

func aiTaskError(message string, err error) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("error", message)
	out.Set("error_type", aiTaskExceptionName(err))
	return out
}

func aiTaskExceptionName(err error) string {
	var valueErr *value_objects.ValueError
	var typeErr *value_objects.TypeError
	var taskNotFound *exceptions.TaskNotFoundError
	var projectNotFound *exceptions.ProjectNotFoundError
	var validation *exceptions.ValidationException
	switch {
	case errors.As(err, &valueErr):
		return "ValueError"
	case errors.As(err, &typeErr):
		return "TypeError"
	case errors.As(err, &taskNotFound):
		return "TaskNotFoundError"
	case errors.As(err, &projectNotFound):
		return "ProjectNotFoundError"
	case errors.As(err, &validation):
		return "ValidationException"
	default:
		return "Exception"
	}
}
