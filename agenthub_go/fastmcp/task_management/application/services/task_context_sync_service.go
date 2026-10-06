package services

import (
	"context"

	appexceptions "agenthub/fastmcp/task_management/application"
	usecases "agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpTaskCtxSyncContextService is the minimal hierarchical-context facade surface
// used by this module (Python: FacadeService.get_unified_context_facade). The Go
// application layer cannot import the facades package (import cycle), so the
// concrete *facades.UnifiedContextFacade is injected by the caller.
type zpTaskCtxSyncContextService interface {
	GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error)
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error)
	UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool) (*entities.OrderedMap[any], error)
}

// zpTaskCtxSyncGitBranchGetter adapts a domain GitBranchRepository to the
// GetTaskUseCase GitBranchGetter surface (dtos.GitBranchGetter).
type zpTaskCtxSyncGitBranchGetter struct {
	repository repositories.GitBranchRepository
}

func (g zpTaskCtxSyncGitBranchGetter) GetByID(ctx context.Context, branchID string) (*entities.GitBranch, error) {
	if g.repository == nil {
		return nil, nil
	}
	return g.repository.FindByID(ctx, branchID, nil)
}

// TaskContextSyncService ports
// application/services/task_context_sync_service.TaskContextSyncService.
type TaskContextSyncService struct {
	userID                     *string
	taskRepository             repositories.TaskRepository
	hierarchicalContextService zpTaskCtxSyncContextService
	gitBranchRepository        repositories.GitBranchRepository
	getTaskUseCase             *usecases.GetTaskUseCase
}

// NewTaskContextSyncService mirrors __init__; the Python builds the hierarchical
// context facade internally, Go receives it because FacadeService has no Go port.
// It also resolves the git branch repository from RepositoryProviderService with the
// same fail-fast behaviour as _get_git_branch_repository.
func NewTaskContextSyncService(taskRepository repositories.TaskRepository,
	contextService usecases.GetTaskContextService, userID *string,
	hierarchicalContextService zpTaskCtxSyncContextService) (*TaskContextSyncService, error) {
	gitBranchRepository, err := zpTaskCtxSyncGetGitBranchRepository(userID)
	if err != nil {
		return nil, err
	}
	return zpTaskCtxSyncNew(taskRepository, contextService, userID, hierarchicalContextService, gitBranchRepository), nil
}

// zpTaskCtxSyncNew builds the service without resolving the git branch repository.
func zpTaskCtxSyncNew(taskRepository repositories.TaskRepository,
	contextService usecases.GetTaskContextService, userID *string,
	hierarchicalContextService zpTaskCtxSyncContextService,
	gitBranchRepository repositories.GitBranchRepository) *TaskContextSyncService {
	return &TaskContextSyncService{
		userID:                     userID,
		taskRepository:             taskRepository,
		hierarchicalContextService: hierarchicalContextService,
		gitBranchRepository:        gitBranchRepository,
		getTaskUseCase: usecases.NewGetTaskUseCase(taskRepository, contextService,
			zpTaskCtxSyncGitBranchGetter{repository: gitBranchRepository}),
	}
}

// zpTaskCtxSyncGetGitBranchRepository mirrors _get_git_branch_repository.
func zpTaskCtxSyncGetGitBranchRepository(userID *string) (repositories.GitBranchRepository, error) {
	provider := RepositoryProviderService{}.GetInstance()
	if provider.repoProviderFactories == nil {
		return nil, appexceptions.NewRepositoryProviderError(
			"Cannot fetch project_id without git_branch_repository: repository provider is not wired", nil)
	}
	gitBranchRepository, err := provider.GetGitBranchRepository(nil, userID)
	if err != nil {
		return nil, appexceptions.NewRepositoryProviderError(
			"Cannot fetch project_id without git_branch_repository: "+err.Error(), nil)
	}
	if gitBranchRepository == nil {
		return nil, appexceptions.NewRepositoryProviderError(
			"git_branch_repository is None - cannot lookup project_id", nil)
	}
	return gitBranchRepository, nil
}

// WithUser mirrors with_user.
func (s *TaskContextSyncService) WithUser(userID string) *TaskContextSyncService {
	return zpTaskCtxSyncNew(s.taskRepository, nil, &userID, s.hierarchicalContextService, s.gitBranchRepository)
}

// SyncContextAndGetTask mirrors sync_context_and_get_task. Empty userID/"" mirrors
// Python user_id=None. The GetTaskUseCase context service cannot be re-derived here,
// so it is held by getTaskUseCase from construction.
func (s *TaskContextSyncService) SyncContextAndGetTask(ctx context.Context, taskID, userID,
	projectID, gitBranchName string) (any, error) {
	if userID == "" {
		return nil, exceptions.NewUserAuthenticationRequiredError("Task context sync")
	}
	if _, err := domain.ValidateUserID(&userID, "Task context sync"); err != nil {
		return nil, err
	}

	taskIDObj, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil, err
	}
	domainTask, err := s.taskRepository.FindByID(ctx, taskIDObj)
	if err != nil {
		// Python's generic except swallows repository failures and returns None.
		return nil, nil
	}
	if domainTask == nil {
		return nil, nil
	}

	taskIDStr := taskID
	if domainTask.ID != nil {
		taskIDStr = domainTask.ID.Value
	}

	if projectID == "" && domainTask.GitBranchID != nil {
		// Python: project_id = getattr(domain_task, "project_id", None); Task has no such field.
		projectID = ""
	}
	if projectID == "" {
		return nil, &value_objects.ValueError{Msg: "project_id is required for context sync (no fallback allowed for DDD compliance)"}
	}

	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskIDStr, false, false, nil)
	if err != nil {
		return nil, err
	}

	taskData := entities.NewOrderedMap[any]()
	inner := entities.NewOrderedMap[any]()
	inner.Set("title", domainTask.Title)
	inner.Set("description", domainTask.Description)
	inner.Set("status", zpTaskCtxSyncStringValue(domainTask.Status))
	inner.Set("priority", zpTaskCtxSyncStringValue(domainTask.Priority))
	inner.Set("assignees", domainTask.Assignees)
	inner.Set("labels", domainTask.Labels)
	inner.Set("estimated_effort", domainTask.EstimatedEffort)
	if domainTask.DueDate != nil {
		inner.Set("due_date", *domainTask.DueDate)
	} else {
		inner.Set("due_date", nil)
	}
	taskData.Set("task_data", inner)
	taskData.Set("parent_branch_id", domainTask.GitBranchID)
	taskData.Set("parent_branch_context_id", domainTask.GitBranchID)

	if contextResult == nil {
		if _, err := s.hierarchicalContextService.CreateContext(ctx, "task", taskIDStr, taskData, nil); err != nil {
			return nil, err
		}
	} else {
		if _, err := s.hierarchicalContextService.UpdateContext(ctx, "task", taskIDStr, taskData, false); err != nil {
			return nil, err
		}
	}

	return s.getTaskUseCase.Execute(ctx, taskID, false, true)
}

// zpTaskCtxSyncStringValue mirrors `.value if hasattr(..., "value") else str(...)`.
func zpTaskCtxSyncStringValue(v any) string {
	switch t := v.(type) {
	case nil:
		return ""
	case value_objects.TaskStatus:
		return t.Value
	case *value_objects.TaskStatus:
		if t == nil {
			return ""
		}
		return t.Value
	case value_objects.Priority:
		return t.Value
	case *value_objects.Priority:
		if t == nil {
			return ""
		}
		return t.Value
	case string:
		return t
	default:
		return value_objects.PyStr(v)
	}
}

// SyncSubtaskCounts mirrors sync_subtask_counts. Python swallows all exceptions
// (logging is dropped), so failures return nil.
func (s *TaskContextSyncService) SyncSubtaskCounts(ctx context.Context, taskID string, subtaskRepository repositories.SubtaskRepository) error {
	taskIDObj, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil
	}
	repo := subtaskRepository
	if s.userID != nil && repo == nil {
		return nil
	}
	if repo == nil {
		return nil
	}
	subtasks, err := repo.FindByParentTaskID(ctx, taskIDObj)
	if err != nil {
		return nil
	}

	totalCount := len(subtasks)
	completedCount := 0
	for _, st := range subtasks {
		status := ""
		if st.Status != nil {
			status = st.Status.Value
		}
		if status == "done" || status == "completed" {
			completedCount++
		}
	}
	progressPercentage := 0.0
	if totalCount > 0 {
		progressPercentage = float64(completedCount) / float64(totalCount) * 100.0
	}

	subtaskItems := make([]any, 0, len(subtasks))
	for _, st := range subtasks {
		item := entities.NewOrderedMap[any]()
		id := ""
		if st.ID != nil {
			id = st.ID.Value
		}
		status := ""
		if st.Status != nil {
			status = st.Status.Value
		}
		item.Set("id", id)
		item.Set("title", st.Title)
		item.Set("description", st.Description)
		item.Set("status", status)
		item.Set("assignees", st.Assignees)
		item.Set("completed", status == "done" || status == "completed")
		item.Set("progress_notes", "")
		subtaskItems = append(subtaskItems, item)
	}

	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskID, false, false, nil)
	if err != nil {
		return nil
	}
	if contextResult != nil && value_objects.PyTruthy(zpTaskCtxSyncGet(contextResult, "success")) {
		contextData, _ := zpTaskCtxSyncGet(contextResult, "context_data").(*entities.OrderedMap[any])
		if contextData == nil {
			contextData = entities.NewOrderedMap[any]()
		}
		subtasksData := entities.NewOrderedMap[any]()
		subtasksData.Set("items", subtaskItems)
		subtasksData.Set("total_count", totalCount)
		subtasksData.Set("completed_count", completedCount)
		subtasksData.Set("progress_percentage", progressPercentage)
		contextData.Set("subtasks", subtasksData)
		if _, err := s.hierarchicalContextService.UpdateContext(ctx, "task", taskID, contextData, false); err != nil {
			return nil
		}
	}
	return nil
}

// SyncTaskStatus mirrors sync_task_status.
func (s *TaskContextSyncService) SyncTaskStatus(ctx context.Context, taskID string, newStatus string) error {
	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskID, false, false, nil)
	if err != nil {
		return nil
	}
	if contextResult != nil && value_objects.PyTruthy(zpTaskCtxSyncGet(contextResult, "success")) {
		contextData, _ := zpTaskCtxSyncGet(contextResult, "context_data").(*entities.OrderedMap[any])
		if contextData == nil {
			contextData = entities.NewOrderedMap[any]()
		}
		metadata, ok := zpTaskCtxSyncGet(contextData, "metadata").(*entities.OrderedMap[any])
		if !ok || metadata == nil {
			metadata = entities.NewOrderedMap[any]()
			contextData.Set("metadata", metadata)
		}
		metadata.Set("status", newStatus)
		if _, err := s.hierarchicalContextService.UpdateContext(ctx, "task", taskID, contextData, false); err != nil {
			return nil
		}
	}
	return nil
}

// SyncTaskMetadata mirrors sync_task_metadata.
func (s *TaskContextSyncService) SyncTaskMetadata(ctx context.Context, taskID string, task *entities.Task) error {
	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskID, false, false, nil)
	if err != nil {
		return nil
	}
	if contextResult == nil || !value_objects.PyTruthy(zpTaskCtxSyncGet(contextResult, "success")) {
		return nil
	}
	contextData, _ := zpTaskCtxSyncGet(contextResult, "context_data").(*entities.OrderedMap[any])
	if contextData == nil {
		contextData = entities.NewOrderedMap[any]()
	}

	metadata, ok := zpTaskCtxSyncGet(contextData, "metadata").(*entities.OrderedMap[any])
	if !ok || metadata == nil {
		metadata = entities.NewOrderedMap[any]()
		contextData.Set("metadata", metadata)
	}
	objective, ok := zpTaskCtxSyncGet(contextData, "objective").(*entities.OrderedMap[any])
	if !ok || objective == nil {
		objective = entities.NewOrderedMap[any]()
		contextData.Set("objective", objective)
	}

	metadata.Set("status", zpTaskCtxSyncStringValue(task.Status))
	metadata.Set("priority", zpTaskCtxSyncStringValue(task.Priority))
	metadata.Set("labels", task.Labels)

	assignees := make([]string, 0, len(task.Assignees))
	for _, a := range task.Assignees {
		if len(a) > 0 && a[0] == '@' {
			assignees = append(assignees, a)
		} else {
			assignees = append(assignees, "@"+a)
		}
	}
	metadata.Set("assignees", assignees)

	if task.CreatedAt != nil {
		metadata.Set("created_at", value_objects.IsoFormat(*task.CreatedAt))
	}
	if task.UpdatedAt != nil {
		metadata.Set("updated_at", value_objects.IsoFormat(*task.UpdatedAt))
	}
	if task.EstimatedEffort != "" {
		objective.Set("estimated_effort", task.EstimatedEffort)
	}

	if _, err := s.hierarchicalContextService.UpdateContext(ctx, "task", taskID, contextData, false); err != nil {
		return nil
	}
	return nil
}

// zpTaskCtxSyncGet reads a key from an OrderedMap; missing keys yield nil.
func zpTaskCtxSyncGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}
