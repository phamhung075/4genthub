package services

import (
	"context"
	"fmt"

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
	GetContext(ctx context.Context, level, contextID string, includeInherited bool, userID *string) (*entities.OrderedMap[any], error)
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
// context facade internally, Go receives it because FacadeService is ported in
// application/services/facade_service.go and wired from the composition root.
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
			zpTaskCtxSyncGitBranchGetter{repository: gitBranchRepository}, nil),
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

	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskIDStr, false, nil)
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
	// THIS IS THE CREATE PATH'S ONLY TaskContext WRITE, so it carries the WHOLE creation-time
	// picture, not just task_data: the objective's estimated_effort is what the create use case used to
	// mirror in a SECOND UpdateContext, and that second write is what made one create append two
	// context_updated events (hub task 26e857b0).
	//
	// It does NOT mirror the task's own fields (status, priority, labels, assignees, the two timestamps)
	// into a `metadata` map under task_data. Those fields have ONE home: the task's columns, which the
	// context read overlay serves as Metadata. A copy under task_data was written here and read back by
	// nobody - the write path reads none of those keys, and it is a second home a later write could
	// disagree with (hub task 3c2901c6).
	if domainTask.EstimatedEffort != "" {
		taskData.Set("objective", map[string]any{"estimated_effort": domainTask.EstimatedEffort})
	}

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

// SyncSubtaskCounts mirrors sync_subtask_counts. Its own preconditions still swallow: an unusable task
// id, an absent or unusable subtask repository (the nil-repo case pins it) and a failed subtask read
// all return nil, because none of them leaves anything to record. The context work does NOT swallow -
// a read error, an unsuccessful read body and a refused update all reach the caller, which is what
// stopped this defect living behind an hourly staleness.
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

	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskID, false, nil)
	if err != nil {
		return fmt.Errorf("the task context could not be read: %w", err)
	}
	if contextResult == nil || !value_objects.PyTruthy(zpTaskCtxSyncGet(contextResult, "success")) {
		return fmt.Errorf("the task context could not be read: %v", zpTaskCtxSyncGet(contextResult, "error"))
	}
	contextData := zpUCSAsOrdered(zpTaskCtxSyncGet(contextResult, "context"))
	subtasksData := entities.NewOrderedMap[any]()
	subtasksData.Set("items", subtaskItems)
	subtasksData.Set("total_count", totalCount)
	subtasksData.Set("completed_count", completedCount)
	subtasksData.Set("progress_percentage", progressPercentage)
	contextData.Set("subtasks", subtasksData)
	if _, err := s.hierarchicalContextService.UpdateContext(ctx, "task", taskID, contextData, false); err != nil {
		return fmt.Errorf("the subtask counts did not land: %w", err)
	}
	return nil
}

// SyncTaskMetadata mirrors sync_task_metadata. The context owns exactly ONE of the task's fields: the
// objective's estimated_effort. status, priority, labels, assignees and the two timestamps are the TASK row's,
// served to a context read by its overlay (TaskOwnedFieldsFromTask, same package) and never stored on the
// context row - CopyTaskFieldsIntoMetadata used to put them in the context's metadata, where the repository has
// no column to keep them, so the next read composed the metadata without them and every update reported
// `add metadata.status`, `add metadata.assignees`, ... to the ledger, forever (hub row f6328d5a). A write with
// nothing of the context's own to change is not made at all: it would bump the version and append an empty
// change set, which is the same phantom in a quieter shape. SyncTaskStatus wrote the same phantom under its
// own name from the completion path - `metadata.Set("status", ...)`, a key no column keeps - so each
// completion still reported `add metadata.status` after the sync above was fixed; the writer is deleted
// rather than made harmless, because the field it wrote was never the context's. A context read serves the
// status from the task row (TaskOwnedFieldsFromTask, applied by the http app's context lookup).
func (s *TaskContextSyncService) SyncTaskMetadata(ctx context.Context, taskID string, task *entities.Task) error {
	contextResult, err := s.hierarchicalContextService.GetContext(ctx, "task", taskID, false, nil)
	if err != nil {
		return fmt.Errorf("the task context could not be read: %w", err)
	}
	if contextResult == nil || !value_objects.PyTruthy(zpTaskCtxSyncGet(contextResult, "success")) {
		return fmt.Errorf("the task context could not be read: %v", zpTaskCtxSyncGet(contextResult, "error"))
	}
	contextData := zpUCSAsOrdered(zpTaskCtxSyncGet(contextResult, "context"))
	objective := zpUCSAsOrdered(zpTaskCtxSyncGet(contextData, "objective"))

	if task.EstimatedEffort == "" {
		return nil
	}
	if current, _ := objective.Get("estimated_effort"); current == task.EstimatedEffort {
		return nil
	}
	objective.Set("estimated_effort", task.EstimatedEffort)
	contextData.Set("objective", objective)

	if _, err := s.hierarchicalContextService.UpdateContext(ctx, "task", taskID, contextData, false); err != nil {
		return fmt.Errorf("the task metadata did not land in the task context: %w", err)
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
