// Package facades ports task_management/application/facades.
//
// task_application_facade.py: the use cases and services the Python constructor builds
// inline, plus the singletons its methods import lazily, are injected through
// TaskFacadeDeps (built by the composition root).
package facades

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"strings"
	"time"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/performance"
)

// FacadeTaskRepository is the task repository surface the facade needs to build
// ListTasksUseCase: the full TaskRepository plus the batch completed-subtask
// counts. Python constructs the use cases from a concrete ORMTaskRepository.
type FacadeTaskRepository interface {
	repositories.TaskRepository
	use_cases.ListTasksTaskRepository
}

// TaskFacadeContextService is the hierarchical (unified) context service.
type TaskFacadeContextService interface {
	GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error)
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error)
}

// TaskFacadeBranchRepository is the git branch repository the facade reads and auto-creates
// branches in; FirstProjectID is "SELECT id FROM projects LIMIT 1" through its session.
type TaskFacadeBranchRepository interface {
	repositories.GitBranchRepository
	Save(ctx context.Context, branch *entities.GitBranch) error
	FirstProjectID(ctx context.Context) (string, bool, error)
}

// TaskFacadeNotifier is WebSocketNotificationService as the facade uses it.
type TaskFacadeNotifier interface {
	SyncBroadcastTask(ctx context.Context, p services.SyncTaskEventParams) error
	SyncBroadcastBranchEvent(eventType, branchID, projectID string, userID *string, branchData *entities.OrderedMap[any])
	TaskContext(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any]
}

// TaskFacadeContextSync is TaskContextSyncService.sync_context_and_get_task.
type TaskFacadeContextSync interface {
	SyncContextAndGetTask(ctx context.Context, taskID, userID, projectID, gitBranchName string) (any, error)
}

// TaskMinimalLister is the performance-mode ORMTaskRepository.list_tasks_minimal.
type TaskMinimalLister interface {
	ListTasksMinimal(ctx context.Context, status, priority, assigneeID, gitBranchID *string, limit, offset *int) ([]*entities.OrderedMap[any], error)
}

// TaskFacadeDeps carries what Python's constructor builds or imports lazily: the use
// cases, services and the process-wide singletons (context, notifications, user context).
type TaskFacadeDeps struct {
	GitBranchRepository TaskFacadeBranchRepository // may be nil
	ContextService      TaskFacadeContextService
	Notifier            TaskFacadeNotifier

	CreateTask   *use_cases.CreateTaskUseCase
	UpdateTask   *use_cases.UpdateTaskUseCase
	GetTask      *use_cases.GetTaskUseCase
	DeleteTask   *use_cases.DeleteTaskUseCase
	CompleteTask *use_cases.CompleteTaskUseCase
	SearchTasks  *use_cases.SearchTasksUseCase
	NextTask     *use_cases.NextTaskUseCase

	ContextSync        TaskFacadeContextSync
	DependencyResolver *services.DependencyResolverService

	// ApplyContextFormat is ContextResponseFactory.apply_to_task_response (factories imports
	// this package, so it is injected).
	ApplyContextFormat func(*entities.OrderedMap[any]) *entities.OrderedMap[any]
	// CurrentUserID is request_context_middleware.get_current_user_id.
	CurrentUserID func(ctx context.Context) *string
	// ProjectBranchLookup is ProjectManagementService().get_git_branch_by_id.
	ProjectBranchLookup func(ctx context.Context, gitBranchID string) (*entities.OrderedMap[any], error)
	// BranchInfo is FacadeService.get_git_branch_facade(user_id).get_git_branch_by_id.
	BranchInfo func(ctx context.Context, userID, gitBranchID string) *entities.OrderedMap[any]
	// LoadSubtasks is ORMSubtaskRepository(user_id=...).find_by_parent_task_id.
	LoadSubtasks func(ctx context.Context, userID *string, parent value_objects.TaskId) ([]*entities.Subtask, error)
	// NewMinimalLister is ORMTaskRepository(git_branch_id, user_id, performance_mode=True).
	NewMinimalLister func(gitBranchID, userID *string) (TaskMinimalLister, error)
}

// TaskApplicationFacade ports TaskApplicationFacade.
type TaskApplicationFacade struct {
	taskRepository            FacadeTaskRepository
	subtaskRepository         repositories.SubtaskRepository // may be nil
	listTasksUseCase          *use_cases.ListTasksUseCase
	manageDependenciesUseCase *use_cases.ManageDependenciesUseCase
	deps                      TaskFacadeDeps
}

// TaskRepository exposes the repository the facade was built with (Python reads
// facade._task_repository from the AI handler).
func (f *TaskApplicationFacade) TaskRepository() FacadeTaskRepository { return f.taskRepository }

// NewTaskApplicationFacade builds the facade. subtaskRepository may be nil (Python allows
// None).
func NewTaskApplicationFacade(taskRepository FacadeTaskRepository,
	subtaskRepository repositories.SubtaskRepository, deps TaskFacadeDeps) *TaskApplicationFacade {
	var gitBranchBatch dtostask.GitBranchBatchRepository
	if b, ok := deps.GitBranchRepository.(dtostask.GitBranchBatchRepository); ok {
		gitBranchBatch = b
	}
	return &TaskApplicationFacade{
		taskRepository:            taskRepository,
		subtaskRepository:         subtaskRepository,
		listTasksUseCase:          use_cases.NewListTasksUseCase(taskRepository, gitBranchBatch),
		manageDependenciesUseCase: use_cases.NewManageDependenciesUseCase(taskRepository),
		deps:                      deps,
	}
}

func facadeFail(action, msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	if action != "" {
		m.Set("action", action)
	}
	m.Set("error", msg)
	return m
}

// facadeIsValueError is `except ValueError`.
func facadeIsValueError(err error) bool {
	var ve *value_objects.ValueError
	return errors.As(err, &ve)
}

// facadeIsTaskNotFound is `except TaskNotFoundError`.
func facadeIsTaskNotFound(err error) bool {
	var nf *exceptions.TaskNotFoundError
	return errors.As(err, &nf)
}

// facadeTaskID is TaskId(str) used as a lookup key.
func facadeTaskID(id string) (value_objects.TaskId, error) { return value_objects.NewTaskId(id) }

// facadeDictGet is dict.get(key).
func facadeDictGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// facadeOrderedFromMap converts a to_dict() map with its keys sorted.
func facadeOrderedFromMap(m map[string]any) *entities.OrderedMap[any] {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	out := entities.NewOrderedMap[any]()
	for _, k := range keys {
		out.Set(k, m[k])
	}
	return out
}

// facadeStrOrNil is a *string as a JSON value.
func facadeStrOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// facadeStrPtrOf returns the string form of v, or nil for None.
func facadeStrPtrOf(v any) *string {
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}

// facadeOr is `a or b` for strings.
func facadeOr(a any, b string) string {
	if value_objects.PyTruthy(a) {
		return value_objects.PyStr(a)
	}
	return b
}

// taskDictOf is task.to_dict() for a task entity as an OrderedMap.
func taskDictOf(t *entities.Task) (*entities.OrderedMap[any], error) {
	d, err := t.ToDict()
	if err != nil {
		return nil, err
	}
	return facadeOrderedFromMap(d), nil
}

// deriveContextFromGitBranchID is _derive_context_from_git_branch_id.
func (f *TaskApplicationFacade) deriveContextFromGitBranchID(ctx context.Context, gitBranchID string) (projectID *string, gitBranchName *string, err error) {
	if f.deps.GitBranchRepository == nil {
		return nil, nil, value_objects.ValueErrorf("Cannot validate git_branch_id '%s': Git branch repository not available", gitBranchID)
	}
	wrap := func(e error) error {
		var ve *value_objects.ValueError
		if errors.As(e, &ve) {
			return e
		}
		var req *exceptions.UserAuthenticationRequiredError
		var inv *exceptions.InvalidUserIdError
		var auth *exceptions.AuthenticationError
		if errors.As(e, &req) || errors.As(e, &inv) || errors.As(e, &auth) {
			return value_objects.ValueErrorf("Cannot validate git_branch_id '%s': %s\nThis operation requires user authentication context. Ensure user_id is provided when calling task management operations.", gitBranchID, e.Error())
		}
		return value_objects.ValueErrorf("Unexpected error while validating git_branch_id '%s': %s: %s", gitBranchID, facadeTypeName(e), e.Error())
	}
	branch, ferr := f.deps.GitBranchRepository.FindByID(ctx, gitBranchID, nil)
	if ferr != nil {
		return nil, nil, wrap(ferr)
	}
	if branch != nil {
		pid, name := branch.ProjectID, branch.Name
		return &pid, &name, nil
	}
	if f.deps.ProjectBranchLookup != nil {
		result, lerr := f.deps.ProjectBranchLookup(ctx, gitBranchID)
		if lerr != nil {
			return nil, nil, wrap(lerr)
		}
		if value_objects.PyTruthy(facadeDictGet(result, "success")) {
			data, _ := facadeDictGet(result, "git_branch").(*entities.OrderedMap[any])
			return facadeStrPtrOf(facadeDictGet(data, "project_id")), facadeStrPtrOf(facadeDictGet(data, "name")), nil
		}
	}
	return nil, nil, value_objects.ValueErrorf("Git branch does not exist: git_branch_id '%s' was not found in the system.\n"+
		"Solution: Use manage_git_branch(action='list') to see all available branches and their IDs, "+
		"then use the correct git_branch_id. Alternatively, create a new branch using "+
		"manage_git_branch(action='create', git_branch_name='your-branch-name', project_id='your-project-id').", gitBranchID)
}

// facadeTypeName is type(e).__name__.
func facadeTypeName(e error) string {
	t := fmt.Sprintf("%T", e)
	if i := strings.LastIndex(t, "."); i >= 0 {
		t = t[i+1:]
	}
	return strings.TrimPrefix(t, "*")
}

// ensureBranchContextExists is _ensure_branch_context_exists.
func (f *TaskApplicationFacade) ensureBranchContextExists(ctx context.Context, gitBranchID, userID string, projectID *string) *entities.OrderedMap[any] {
	result := func(success bool, extra ...any) *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", success)
		for i := 0; i+1 < len(extra); i += 2 {
			m.Set(extra[i].(string), extra[i+1])
		}
		return m
	}
	gitBranchCreated := false
	if repo := f.deps.GitBranchRepository; repo != nil {
		branchResult, err := repo.GetGitBranchByID(ctx, gitBranchID)
		if err != nil {
			return result(false, "error", "Unexpected error ensuring branch context: "+err.Error(), "git_branch_created", false, "context_created", false)
		}
		if !value_objects.PyTruthy(branchResult["success"]) || !value_objects.PyTruthy(branchResult["git_branch"]) {
			var branchProjectID string
			if projectID != nil && *projectID != "" {
				branchProjectID = *projectID
			}
			if branchProjectID == "" {
				if id, ok, perr := repo.FirstProjectID(ctx); perr == nil && ok {
					branchProjectID = id
				}
			}
			if branchProjectID != "" {
				now := time.Now().UTC()
				gbID, gerr := value_objects.NewGitBranchId(gitBranchID)
				if gerr == nil {
					entity, nerr := entities.NewGitBranch(entities.GitBranch{
						ID: &gbID, Name: "branch-" + gitBranchID, Description: "Auto-created for task creation",
						ProjectID: branchProjectID,
					})
					if nerr == nil {
						entity.CreatedAt, entity.UpdatedAt = &now, &now
						if serr := repo.Save(ctx, entity); serr == nil {
							gitBranchCreated = true
						}
					}
				}
			}
		}
	}

	uid := userID
	got, err := f.deps.ContextService.GetContext(ctx, "branch", gitBranchID, false, false, &uid)
	if err != nil {
		return result(false, "error", "Unexpected error ensuring branch context: "+err.Error(), "git_branch_created", false, "context_created", false)
	}
	if value_objects.PyTruthy(facadeDictGet(got, "success")) && value_objects.PyTruthy(facadeDictGet(got, "context")) {
		return result(true, "context", facadeDictGet(got, "context"), "git_branch_created", gitBranchCreated, "context_created", false)
	}

	data := entities.NewOrderedMap[any]()
	data.Set("auto_created", true)
	data.Set("created_at", value_objects.IsoFormat(time.Now().UTC()))
	data.Set("source", "task_creation_auto_create")
	data.Set("created_by", userID)
	data.Set("git_branch_id", gitBranchID)
	if projectID != nil && *projectID != "" {
		data.Set("project_id", *projectID)
	}
	created, err := f.deps.ContextService.CreateContext(ctx, "branch", gitBranchID, data, &uid)
	if err != nil {
		return result(false, "error", "Unexpected error ensuring branch context: "+err.Error(), "git_branch_created", false, "context_created", false)
	}
	if value_objects.PyTruthy(facadeDictGet(created, "success")) {
		c := facadeDictGet(created, "context")
		if c == nil {
			c = entities.NewOrderedMap[any]()
		}
		return result(true, "context", c, "git_branch_created", gitBranchCreated, "context_created", true)
	}
	errMsg := "Unknown error"
	if v := facadeDictGet(created, "error"); v != nil {
		errMsg = value_objects.PyStr(v)
	}
	return result(false, "error", "Failed to create branch context: "+errMsg, "git_branch_created", gitBranchCreated, "context_created", false)
}

// facadeStringList converts a payload list value (None -> nil).
func facadeStringList(v any) []string {
	switch t := v.(type) {
	case []string:
		return t
	case []any:
		out := make([]string, 0, len(t))
		for _, item := range t {
			out = append(out, value_objects.PyStr(item))
		}
		return out
	}
	return nil
}

// facadeErrString is str(e).
func facadeErrString(err error) string { return err.Error() }

// facadeBranchUserID is the user the facade acts for: the repository's user.
func (f *TaskApplicationFacade) repoUserID() *string {
	if u, ok := f.taskRepository.(interface{ GetCurrentUserID() *string }); ok {
		return u.GetCurrentUserID()
	}
	return nil
}

// checkForDuplicateCreation is _check_for_duplicate_creation.
func (f *TaskApplicationFacade) checkForDuplicateCreation(ctx context.Context, request dtostask.CreateTaskRequest) bool {
	cutoff := time.Now().UTC().Add(-10 * time.Second)
	limit := 20
	gb := request.GitBranchID
	response, err := f.listTasksUseCase.Execute(ctx, &dtostask.ListTasksRequest{GitBranchID: &gb, Limit: &limit})
	if err != nil || len(response.Tasks) == 0 {
		return false
	}
	for _, task := range response.Tasks {
		if task.CreatedAt == nil {
			return false // None < datetime raises TypeError, which Python swallows
		}
		if task.CreatedAt.Before(cutoff) {
			continue
		}
		if request.Title != "" && value_objects.PyStrip(value_objects.PyLower(task.Title)) == value_objects.PyStrip(value_objects.PyLower(request.Title)) {
			return true
		}
	}
	return false
}

// CreateTask is create_task.
func (f *TaskApplicationFacade) CreateTask(ctx context.Context, request dtostask.CreateTaskRequest) *entities.OrderedMap[any] {
	fail := func(err error) *entities.OrderedMap[any] {
		if facadeIsValueError(err) {
			return facadeFail("create", err.Error())
		}
		return facadeFail("create", "Unexpected error: "+err.Error())
	}

	derivedProjectID, derivedBranchName, err := f.deriveContextFromGitBranchID(ctx, request.GitBranchID)
	if err != nil {
		return fail(err)
	}
	gitBranchName := "main"
	if derivedBranchName != nil && *derivedBranchName != "" {
		gitBranchName = *derivedBranchName
	}

	var derivedUserID *string
	if f.deps.CurrentUserID != nil {
		derivedUserID = f.deps.CurrentUserID(ctx)
	}
	if derivedUserID == nil || *derivedUserID == "" {
		derivedUserID = request.UserID
	}
	userID, err := domain.ValidateUserID(derivedUserID, "Task creation")
	if err != nil {
		return fail(err)
	}

	f.ensureBranchContextExists(ctx, request.GitBranchID, userID, derivedProjectID)
	wasAlreadyCreated := f.checkForDuplicateCreation(ctx, request)

	taskResponse, err := f.deps.CreateTask.Execute(ctx, request)
	if err != nil {
		return fail(err)
	}
	if taskResponse == nil || !taskResponse.Success {
		msg := "Unknown error occurred"
		if taskResponse != nil {
			msg = taskResponse.Message
		}
		return facadeFail("create", msg)
	}

	var taskPayload *entities.OrderedMap[any]
	var warning string
	var syncProject string
	if derivedProjectID != nil {
		syncProject = *derivedProjectID
	}
	fullTask := func() (*entities.OrderedMap[any], error) { return taskResponse.Task.ToDict() }
	updated, syncErr := f.deps.ContextSync.SyncContextAndGetTask(ctx, taskResponse.Task.ID, userID, syncProject, gitBranchName)
	if syncErr != nil {
		taskPayload, err = fullTask()
		if err != nil {
			return fail(err)
		}
		warning = "Task created without context: " + syncErr.Error()
	} else if updated != nil {
		if updatedTask, ok := updated.(*dtostask.TaskResponse); ok && updatedTask != nil {
			d, derr := updatedTask.ToDict()
			if derr != nil {
				taskPayload, err = fullTask()
				if err != nil {
					return fail(err)
				}
				warning = "Task created without context: " + derr.Error()
			} else {
				taskPayload = f.deps.ApplyContextFormat(d)
			}
		}
	}
	if taskPayload == nil {
		taskPayload, err = fullTask()
		if err != nil {
			return fail(err)
		}
		if warning == "" {
			warning = "Task created without context synchronization"
		}
	}

	if !wasAlreadyCreated && f.deps.Notifier != nil {
		var data any = taskPayload
		title, status, priority := facadeOr(facadeDictGet(taskPayload, "title"), taskResponse.Task.Title),
			facadeOr(facadeDictGet(taskPayload, "status"), taskResponse.Task.Status),
			facadeOr(facadeDictGet(taskPayload, "priority"), taskResponse.Task.Priority)
		var description *string
		if v := facadeDictGet(taskPayload, "description"); v != nil {
			s := value_objects.PyStr(v)
			description = &s
		}
		data = domain.TaskCreatePayload{
			ID: facadeOr(facadeDictGet(taskPayload, "id"), taskResponse.Task.ID), Title: title, Description: description,
			Status: status, Priority: priority, GitBranchID: request.GitBranchID, ProjectID: derivedProjectID,
			Assignees: facadeStringList(facadeDictGet(taskPayload, "assignees")), Labels: facadeStringList(facadeDictGet(taskPayload, "labels")),
			CreatedAt: facadeStrPtrOf(facadeDictGet(taskPayload, "created_at")),
		}.ModelDump()
		gb := request.GitBranchID
		_ = f.deps.Notifier.SyncBroadcastTask(ctx, services.SyncTaskEventParams{
			EventType: "created", TaskID: taskResponse.Task.ID, UserID: userID, TaskData: data,
			GitBranchID: &gb, ProjectID: derivedProjectID,
		})
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("action", "create")
	result.Set("task", taskPayload)
	result.Set("message", taskResponse.Message)
	if warning != "" {
		result.Set("warning", warning)
	}
	return result
}

// getTaskForUpdateComparison is _get_task_for_update_comparison.
func (f *TaskApplicationFacade) getTaskForUpdateComparison(ctx context.Context, taskID string) *entities.Task {
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil
	}
	t, err := f.taskRepository.FindByID(ctx, id)
	if err != nil {
		return nil
	}
	return t
}

func facadeFloat(v any) (float64, bool) {
	switch t := v.(type) {
	case int:
		return float64(t), true
	case int64:
		return float64(t), true
	case float64:
		return t, true
	}
	return 0, false
}

func facadeSameSet(a, b []string) bool {
	as, bs := map[string]bool{}, map[string]bool{}
	for _, v := range a {
		as[v] = true
	}
	for _, v := range b {
		bs[v] = true
	}
	if len(as) != len(bs) {
		return false
	}
	for k := range as {
		if !bs[k] {
			return false
		}
	}
	return true
}

// checkForMeaningfulUpdate is _check_for_meaningful_update.
func (f *TaskApplicationFacade) checkForMeaningfulUpdate(current *entities.Task, updated *dtostask.TaskResponse, request dtostask.UpdateTaskRequest) bool {
	if current == nil || updated == nil {
		return true
	}
	if request.Title != nil && current.Title != updated.Title {
		return true
	}
	if request.Description != nil && current.Description != updated.Description {
		return true
	}
	if request.Status != nil && current.Status != nil && current.Status.Value != updated.Status {
		return true
	}
	if request.ProgressPercentage != nil {
		cur := current.OverallProgress
		up, ok := facadeFloat(updated.ProgressPercentage)
		if !ok || cur != up {
			return true
		}
	}
	if request.Priority != nil && current.Priority != nil && current.Priority.Value != updated.Priority {
		return true
	}
	if request.EstimatedEffort != nil && current.EstimatedEffort != updated.EstimatedEffort {
		return true
	}
	if request.Assignees != nil && !facadeSameSet(current.Assignees, updated.Assignees) {
		return true
	}
	if request.Labels != nil && !facadeSameSet(current.Labels, updated.Labels) {
		return true
	}
	return false
}

// UpdateTask is update_task.
func (f *TaskApplicationFacade) UpdateTask(ctx context.Context, request dtostask.UpdateTaskRequest) *entities.OrderedMap[any] {
	fail := func(err error) *entities.OrderedMap[any] {
		if facadeIsTaskNotFound(err) || facadeIsValueError(err) {
			return facadeFail("update", err.Error())
		}
		return facadeFail("update", "Unexpected error: "+err.Error())
	}
	taskID := value_objects.PyStr(request.TaskID)
	current := f.getTaskForUpdateComparison(ctx, taskID)

	taskResponse, err := f.deps.UpdateTask.Execute(ctx, request)
	if err != nil {
		return fail(err)
	}
	if taskResponse == nil || !taskResponse.Success {
		msg := "Unknown error occurred"
		if taskResponse != nil {
			msg = taskResponse.Message
		}
		return facadeFail("update", msg)
	}
	wasActuallyUpdated := f.checkForMeaningfulUpdate(current, taskResponse.Task, request)

	completeTask, err := taskResponse.Task.ToDict()
	if err != nil {
		return fail(err)
	}
	taskDict, err := services.MinimalResponseSerializer{}.SerializeTaskMinimal(completeTask, "update")
	if err != nil {
		return fail(err)
	}

	if wasActuallyUpdated && f.deps.Notifier != nil {
		const userID = "system" // UpdateTaskRequest has no user_id
		var full *entities.OrderedMap[any]
		if current != nil {
			full, err = taskDictOf(current)
			if err != nil {
				full = completeTask
			}
		} else {
			full = completeTask
		}
		var validated any = taskDict
		title, status, priority, branch := facadeDictGet(full, "title"), facadeDictGet(full, "status"), facadeDictGet(full, "priority"), facadeDictGet(full, "git_branch_id")
		if title != nil && status != nil && priority != nil && branch != nil {
			updatedAt := facadeDictGet(taskDict, "updated_at")
			if !value_objects.PyTruthy(updatedAt) {
				updatedAt = facadeDictGet(full, "updated_at")
			}
			var description *string
			if v := facadeDictGet(full, "description"); v != nil {
				s := value_objects.PyStr(v)
				description = &s
			}
			validated = domain.TaskUpdatePayload{
				ID: facadeOr(facadeDictGet(full, "id"), taskID), Title: value_objects.PyStr(title), Description: description,
				Status: value_objects.PyStr(status), Priority: value_objects.PyStr(priority), GitBranchID: value_objects.PyStr(branch),
				Assignees: facadeStringList(facadeDictGet(full, "assignees")), Labels: facadeStringList(facadeDictGet(full, "labels")),
				UpdatedAt: facadeStrPtrOf(updatedAt),
			}.ModelDump()
		}
		_ = f.deps.Notifier.SyncBroadcastTask(ctx, services.SyncTaskEventParams{
			EventType: "updated", TaskID: taskID, UserID: userID, TaskData: validated,
		})
		if request.ProgressPercentage != nil {
			// task_dict is the minimal serialization, which carries no git_branch_id for
			// updates, so Python never reaches the branch broadcast either.
			if gb := facadeDictGet(taskDict, "git_branch_id"); value_objects.PyTruthy(gb) && f.deps.BranchInfo != nil {
				branchID := value_objects.PyStr(gb)
				result := f.deps.BranchInfo(ctx, userID, branchID)
				if value_objects.PyTruthy(facadeDictGet(result, "success")) {
					data, _ := facadeDictGet(result, "git_branch").(*entities.OrderedMap[any])
					if data == nil {
						data = entities.NewOrderedMap[any]()
					}
					uid := userID
					f.deps.Notifier.SyncBroadcastBranchEvent("updated", branchID, facadeOr(facadeDictGet(data, "project_id"), ""), &uid, data)
				}
			}
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("action", "update")
	result.Set("task", completeTask)
	return result
}

// count_tasks ports count_tasks(filters).
func (f *TaskApplicationFacade) CountTasks(ctx context.Context, filters map[string]any) *entities.OrderedMap[any] {
	limit := 0
	request := &dtostask.ListTasksRequest{
		Status:      facadeStringPtr(filters, "status"),
		Priority:    facadeStringPtr(filters, "priority"),
		Assignees:   facadeStringSlice(filters, "assignees"),
		Labels:      facadeStringSlice(filters, "labels"),
		Limit:       &limit,
		GitBranchID: facadeStringPtr(filters, "git_branch_id"),
	}

	response, err := f.listTasksUseCase.Execute(ctx, request)
	if err != nil {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", err.Error())
		m.Set("count", 0)
		return m
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("count", response.Count)
	return m
}

// get_dependencies ports get_dependencies(task_id, user_id).
func (f *TaskApplicationFacade) GetDependencies(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	if strings.TrimSpace(taskID) == "" {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "get_dependencies")
		m.Set("error", "Task ID is required")
		return m
	}

	data, err := f.manageDependenciesUseCase.GetDependencies(ctx, taskID)
	if err != nil {
		var notFound *exceptions.TaskNotFoundError
		if errors.As(err, &notFound) {
			m := entities.NewOrderedMap[any]()
			m.Set("success", false)
			m.Set("action", "get_dependencies")
			m.Set("error", err.Error())
			return m
		}
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "get_dependencies")
		m.Set("error", "Failed to get dependencies: "+err.Error())
		return m
	}

	dependencies, _ := data.Get("dependencies")
	dependencyIDs, _ := data.Get("dependency_ids")
	canStart, ok := data.Get("can_start")
	if !ok {
		canStart = true
	}
	depList, _ := dependencies.([]any)

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "get_dependencies")
	m.Set("task_id", taskID)
	m.Set("dependencies", depList)
	m.Set("dependency_ids", dependencyIDs)
	m.Set("can_start", canStart)
	m.Set("message", fmt.Sprintf("Retrieved %d dependencies for task %s", len(depList), taskID))
	return m
}

// clear_dependencies ports clear_dependencies(task_id, user_id).
func (f *TaskApplicationFacade) ClearDependencies(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	if strings.TrimSpace(taskID) == "" {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "clear_dependencies")
		m.Set("error", "Task ID is required")
		return m
	}

	response, err := f.manageDependenciesUseCase.ClearDependencies(ctx, taskID)
	if err != nil {
		var notFound *exceptions.TaskNotFoundError
		if errors.As(err, &notFound) {
			m := entities.NewOrderedMap[any]()
			m.Set("success", false)
			m.Set("action", "clear_dependencies")
			m.Set("error", err.Error())
			return m
		}
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "clear_dependencies")
		m.Set("error", "Failed to clear dependencies: "+err.Error())
		return m
	}

	dependenciesCleared := "0"
	if strings.Contains(response.Message, "Cleared") {
		parts := strings.Fields(response.Message)
		if len(parts) > 1 {
			dependenciesCleared = parts[1]
		}
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", response.Success)
	m.Set("action", "clear_dependencies")
	m.Set("task_id", response.TaskID)
	m.Set("message", response.Message)
	m.Set("dependencies_cleared", dependenciesCleared)
	return m
}

// get_blocking_tasks ports get_blocking_tasks(task_id, user_id).
func (f *TaskApplicationFacade) GetBlockingTasks(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	if strings.TrimSpace(taskID) == "" {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "get_blocking_tasks")
		m.Set("error", "Task ID is required")
		return m
	}

	data, err := f.manageDependenciesUseCase.GetBlockingTasks(ctx, taskID)
	if err != nil {
		var notFound *exceptions.TaskNotFoundError
		if errors.As(err, &notFound) {
			m := entities.NewOrderedMap[any]()
			m.Set("success", false)
			m.Set("action", "get_blocking_tasks")
			m.Set("error", err.Error())
			return m
		}
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "get_blocking_tasks")
		m.Set("error", "Failed to get blocking tasks: "+err.Error())
		return m
	}

	blockingTasks, _ := data.Get("blocking_tasks")
	blockingCount, _ := data.Get("blocking_count")
	resolvedTaskID, ok := data.Get("task_id")
	if !ok {
		resolvedTaskID = taskID
	}
	count := 0
	switch v := blockingCount.(type) {
	case int:
		count = v
	case int64:
		count = int(v)
	}

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "get_blocking_tasks")
	m.Set("task_id", resolvedTaskID)
	m.Set("blocking_tasks", blockingTasks)
	m.Set("blocking_count", blockingCount)
	m.Set("message", fmt.Sprintf("Found %d tasks blocked by task %s", count, taskID))
	return m
}

// facadeStringPtr mirrors Python filters.get(key) for optional string filters.
func facadeStringPtr(filters map[string]any, key string) *string {
	value, ok := filters[key]
	if !ok || value == nil {
		return nil
	}
	switch v := value.(type) {
	case string:
		return &v
	case *string:
		return v
	}
	s := fmt.Sprint(value)
	return &s
}

// facadeStringSlice mirrors Python filters.get(key, []) for list filters.
func facadeStringSlice(filters map[string]any, key string) []string {
	value, ok := filters[key]
	if !ok || value == nil {
		return []string{}
	}
	switch v := value.(type) {
	case []string:
		return v
	case []any:
		out := make([]string, 0, len(v))
		for _, item := range v {
			out = append(out, fmt.Sprint(item))
		}
		return out
	}
	return []string{}
}

// depInfoDict is the per-dependency dict of get_task's dependency_relationships.
func depInfoDict(d dtostask.DependencyInfo) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", d.TaskID)
	m.Set("title", d.Title)
	m.Set("status", d.Status)
	m.Set("priority", d.Priority)
	m.Set("completion_percentage", d.CompletionPercentage)
	m.Set("is_blocking", d.IsBlocking)
	m.Set("is_blocked", d.IsBlocked)
	m.Set("estimated_effort", facadeOrEmpty(d.EstimatedEffort))
	assignees := d.Assignees
	if assignees == nil {
		assignees = []string{}
	}
	m.Set("assignees", assignees)
	if d.UpdatedAt != nil {
		m.Set("updated_at", value_objects.IsoFormat(*d.UpdatedAt))
	} else {
		m.Set("updated_at", nil)
	}
	return m
}

// facadeOrEmpty is getattr(dep, "estimated_effort", "") for a None value.
func facadeOrEmpty(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// dependencyRelationshipsDict is the task_dict["dependency_relationships"] block.
func dependencyRelationshipsDict(r *dtostask.DependencyRelationships) *entities.OrderedMap[any] {
	list := func(items []dtostask.DependencyInfo) []any {
		out := make([]any, 0, len(items))
		for _, d := range items {
			out = append(out, depInfoDict(d))
		}
		return out
	}
	chains := make([]any, 0, len(r.UpstreamChains))
	for _, c := range r.UpstreamChains {
		cm := entities.NewOrderedMap[any]()
		cm.Set("chain_id", c.ChainID)
		cm.Set("chain_status", c.ChainStatus)
		cm.Set("task_count", 0) // DependencyChain has no task_count attribute
		cm.Set("completed_tasks", c.CompletedTasks)
		cm.Set("blocked_tasks", c.BlockedTasks)
		cm.Set("completion_percentage", c.CompletionPercentage())
		cm.Set("is_blocked", c.IsBlocked())
		if next := c.NextTask(); next != nil {
			nm := entities.NewOrderedMap[any]()
			nm.Set("task_id", next.TaskID)
			nm.Set("title", next.Title)
			nm.Set("status", next.Status)
			cm.Set("next_task", nm)
		} else {
			cm.Set("next_task", nil)
		}
		chains = append(chains, cm)
	}
	summary := entities.NewOrderedMap[any]()
	summary.Set("total_dependencies", r.TotalDependencies)
	summary.Set("completed_dependencies", r.CompletedDependencies)
	summary.Set("blocked_dependencies", r.BlockedDependencies)
	summary.Set("can_start", r.CanStart)
	summary.Set("is_blocked", r.IsBlocked)
	summary.Set("is_blocking_others", r.IsBlockingOthers)
	summary.Set("dependency_summary", r.DependencySummary)
	summary.Set("dependency_completion_percentage", r.DependencyCompletionPercentage())
	workflow := entities.NewOrderedMap[any]()
	workflow.Set("next_actions", r.NextActions)
	workflow.Set("blocking_reasons", r.BlockingReasons)
	workflow.Set("blocking_info", r.GetBlockingChainInfo())
	workflow.Set("workflow_guidance", r.GetWorkflowGuidance())
	m := entities.NewOrderedMap[any]()
	m.Set("task_id", r.TaskID)
	m.Set("depends_on", list(r.DependsOn))
	m.Set("blocks", list(r.Blocks))
	m.Set("dependency_chains", chains)
	m.Set("summary", summary)
	m.Set("workflow", workflow)
	return m
}

// loadSubtasksInto replaces task_dict["subtasks"] with full subtask dicts, keeping an
// existing list when loading fails.
func (f *TaskApplicationFacade) loadSubtasksInto(ctx context.Context, taskDict *entities.OrderedMap[any], taskID string) {
	subtasks, err := f.loadSubtasks(ctx, taskID)
	if err != nil {
		if _, ok := facadeDictGet(taskDict, "subtasks").([]any); !ok {
			taskDict.Set("subtasks", []any{})
		}
		return
	}
	out := make([]any, 0, len(subtasks))
	for _, st := range subtasks {
		d, derr := st.ToDict(false)
		if derr != nil {
			if _, ok := facadeDictGet(taskDict, "subtasks").([]any); !ok {
				taskDict.Set("subtasks", []any{})
			}
			return
		}
		out = append(out, facadeOrderedFromMap(d))
	}
	taskDict.Set("subtasks", out)
}

func (f *TaskApplicationFacade) loadSubtasks(ctx context.Context, taskID string) ([]*entities.Subtask, error) {
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil, err
	}
	if f.deps.LoadSubtasks == nil {
		return nil, errors.New("subtask repository not available")
	}
	return f.deps.LoadSubtasks(ctx, f.repoUserID(), id)
}

// GetTask is get_task.
func (f *TaskApplicationFacade) GetTask(ctx context.Context, taskID string, includeContext, includeDependencies bool) *entities.OrderedMap[any] {
	notFound := func() *entities.OrderedMap[any] {
		return facadeFail("get", fmt.Sprintf("Task with ID %s not found", taskID))
	}
	unexpected := func(err error) *entities.OrderedMap[any] {
		return facadeFail("get", "Unexpected error: "+err.Error())
	}
	if strings.TrimSpace(taskID) == "" {
		return unexpected(value_objects.ValueErrorf("Task ID is required"))
	}
	domainID, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return unexpected(err)
	}
	entity, err := f.taskRepository.FindByID(ctx, domainID)
	if err != nil {
		return unexpected(err)
	}
	if entity == nil {
		return notFound()
	}

	taskResponse, err := f.deps.GetTask.Execute(ctx, taskID, false, includeContext)
	if err != nil {
		var autoRule *exceptions.AutoRuleGenerationError
		switch {
		case facadeIsTaskNotFound(err):
			return facadeFail("get", err.Error())
		case errors.As(err, &autoRule):
			return f.getTaskAfterRuleFailure(ctx, taskID, includeContext, err)
		}
		return unexpected(err)
	}
	if taskResponse == nil {
		return notFound()
	}

	var relationships *dtostask.DependencyRelationships
	if includeDependencies && f.deps.DependencyResolver != nil {
		if r, rerr := f.deps.DependencyResolver.ResolveDependencies(ctx, taskID); rerr == nil {
			relationships = r
		}
	}
	taskDict, err := taskResponse.ToDict()
	if err != nil {
		return unexpected(err)
	}
	if relationships != nil {
		taskDict.Set("dependency_relationships", dependencyRelationshipsDict(relationships))
	}
	f.loadSubtasksInto(ctx, taskDict, taskID)
	taskDict = f.deps.ApplyContextFormat(taskDict)

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("action", "get")
	result.Set("task", taskDict)
	return result
}

// getTaskAfterRuleFailure is get_task's `except AutoRuleGenerationError` branch.
func (f *TaskApplicationFacade) getTaskAfterRuleFailure(ctx context.Context, taskID string, includeContext bool, cause error) *entities.OrderedMap[any] {
	var taskResponse *dtostask.TaskResponse
	if domainID, err := value_objects.NewTaskId(taskID); err == nil {
		if entity, ferr := f.taskRepository.FindByID(ctx, domainID); ferr == nil && entity != nil {
			if r, rerr := f.deps.GetTask.Execute(ctx, taskID, false, includeContext); rerr == nil {
				taskResponse = r
			}
		}
	}
	if taskResponse == nil {
		return facadeFail("get", cause.Error())
	}
	taskDict, err := taskResponse.ToDict()
	if err != nil {
		return facadeFail("get", "Unexpected error: "+err.Error())
	}
	f.loadSubtasksInto(ctx, taskDict, taskID)
	taskDict = f.deps.ApplyContextFormat(taskDict)
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("action", "get")
	result.Set("task", taskDict)
	result.Set("warning", "Auto rule generation failed: "+cause.Error())
	return result
}

func facadeShort(taskID string) string {
	r := []rune(taskID)
	if len(r) > 8 {
		r = r[:8]
	}
	return string(r)
}

// DeleteTask is delete_task.
func (f *TaskApplicationFacade) DeleteTask(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	fail := func(err error) *entities.OrderedMap[any] {
		if facadeIsTaskNotFound(err) || facadeIsValueError(err) {
			return facadeFail("delete", err.Error())
		}
		return facadeFail("delete", "Unexpected error: "+err.Error())
	}
	if strings.TrimSpace(taskID) == "" {
		return fail(value_objects.ValueErrorf("Task ID is required"))
	}

	var snapshot, taskContext *entities.OrderedMap[any]
	prefetch := func() error {
		domainID, err := value_objects.NewTaskId(taskID)
		if err != nil {
			return err
		}
		entity, err := f.taskRepository.FindByID(ctx, domainID)
		if err != nil {
			return err
		}
		if entity != nil {
			if snapshot, err = taskDictOf(entity); err != nil {
				return err
			}
		}
		taskContext = f.deps.Notifier.TaskContext(ctx, taskID, userID)
		if snapshot != nil && taskContext != nil {
			snapshot.Set("project_id", facadeDictGet(taskContext, "parent_project_id"))
		}
		return nil
	}
	if f.deps.Notifier == nil || prefetch() != nil {
		taskContext = entities.NewOrderedMap[any]()
		taskContext.Set("task_title", "Task "+facadeShort(taskID))
		taskContext.Set("parent_branch_id", nil)
		taskContext.Set("parent_branch_title", "Unknown Branch")
		taskContext.Set("task_user_id", nil)
	}

	result, err := f.deps.DeleteTask.Execute(ctx, taskID, true, userID)
	if err != nil {
		return fail(err)
	}
	success := value_objects.PyTruthy(facadeDictGet(result, "success"))

	if success && snapshot == nil && value_objects.PyTruthy(facadeDictGet(result, "title")) {
		snapshot = entities.NewOrderedMap[any]()
		snapshot.Set("id", taskID)
		snapshot.Set("title", facadeDictGet(result, "title"))
		snapshot.Set("git_branch_id", facadeDictGet(taskContext, "parent_branch_id"))
		snapshot.Set("project_id", facadeDictGet(taskContext, "parent_project_id"))
	}

	if !success {
		msg := fmt.Sprintf("Failed to delete task %s", taskID)
		if v, ok := result.Get("message"); ok {
			msg = value_objects.PyStr(v)
		}
		return facadeFail("delete", msg)
	}

	if f.deps.Notifier != nil {
		owner := facadeDictGet(taskContext, "task_user_id")
		notificationUser := "system"
		if value_objects.PyTruthy(owner) {
			notificationUser = value_objects.PyStr(owner)
		} else if userID != nil && *userID != "" {
			notificationUser = *userID
		}
		var typed any
		if snapshot != nil {
			if payload, cerr := domain.ConvertTaskDeleteLegacy(snapshot); cerr == nil {
				typed = payload.ModelDump()
			} else {
				typed = snapshot
			}
		} else {
			title := "Task " + facadeShort(taskID)
			if taskContext.Has("task_title") {
				title = value_objects.PyStr(facadeDictGet(taskContext, "task_title"))
			}
			payload, perr := domain.NewTaskDeletePayload(taskID, title, facadeStrPtrOf(facadeDictGet(taskContext, "parent_branch_id")), facadeStrPtrOf(facadeDictGet(taskContext, "parent_project_id")))
			if perr == nil {
				typed = payload.ModelDump()
			}
		}
		if typed != nil {
			_ = f.deps.Notifier.SyncBroadcastTask(ctx, services.SyncTaskEventParams{
				EventType: "deleted", TaskID: taskID, UserID: notificationUser, TaskData: typed, PreFetchedContext: taskContext,
			})
		}
	}

	stats := entities.NewOrderedMap[any]()
	subtasksDeleted, contextsDeleted := any(0), any(0)
	if v, ok := result.Get("subtasks_deleted"); ok {
		subtasksDeleted = v
	}
	if v, ok := result.Get("contexts_deleted"); ok {
		contextsDeleted = v
	}
	stats.Set("subtasks_deleted", subtasksDeleted)
	stats.Set("contexts_deleted", contextsDeleted)
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("action", "delete")
	out.Set("message", fmt.Sprintf("Task %s deleted successfully", taskID))
	out.Set("cascade_stats", stats)
	return out
}

// CompleteTask is complete_task.
func (f *TaskApplicationFacade) CompleteTask(ctx context.Context, taskID string, completionSummary, testingNotes *string, userID *string) *entities.OrderedMap[any] {
	fail := func(err error) *entities.OrderedMap[any] {
		if facadeIsTaskNotFound(err) || facadeIsValueError(err) {
			return facadeFail("complete", err.Error())
		}
		return facadeFail("complete", "Unexpected error: "+err.Error())
	}
	if strings.TrimSpace(taskID) == "" {
		return fail(value_objects.ValueErrorf("Task ID is required"))
	}
	result, err := f.deps.CompleteTask.Execute(ctx, taskID, completionSummary, testingNotes, nil)
	if err != nil {
		return fail(err)
	}

	response := entities.NewOrderedMap[any]()
	response.Set("success", value_objects.PyTruthy(facadeDictGet(result, "success")))
	response.Set("action", "complete")
	response.Set("task_id", taskID)
	if v, ok := result.Get("message"); ok {
		response.Set("message", v)
	} else {
		response.Set("message", "")
	}
	if v, ok := result.Get("context"); ok {
		response.Set("context", v)
	} else {
		response.Set("context", entities.NewOrderedMap[any]())
	}
	for _, k := range result.Keys() {
		if !response.Has(k) {
			v, _ := result.Get(k)
			response.Set(k, v)
		}
	}

	if value_objects.PyTruthy(facadeDictGet(response, "success")) && !value_objects.PyTruthy(facadeDictGet(response, "was_already_completed")) && f.deps.Notifier != nil {
		f.broadcastCompletion(ctx, taskID, response, userID)
	}
	return response
}

// broadcastCompletion is complete_task's WebSocket block (failures only logged).
func (f *TaskApplicationFacade) broadcastCompletion(ctx context.Context, taskID string, response *entities.OrderedMap[any], userID *string) {
	var taskData *entities.OrderedMap[any]
	fallback := func() *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("task_id", taskID)
		status := any("done")
		if v, ok := response.Get("status"); ok {
			status = v
		}
		m.Set("status", status)
		m.Set("title", facadeDictGet(response, "title"))
		return m
	}
	if getter, ok := f.taskRepository.(interface {
		GetTask(ctx context.Context, taskID string) (*entities.Task, error)
	}); ok {
		if completed, err := getter.GetTask(ctx, taskID); err == nil && completed != nil {
			if d, derr := taskDictOf(completed); derr == nil {
				taskData = d
			}
		}
	}
	if taskData == nil {
		taskData = fallback()
	}

	var gitBranchID, projectID *string
	if gb := facadeDictGet(taskData, "git_branch_id"); value_objects.PyTruthy(gb) {
		gitBranchID = facadeStrPtrOf(gb)
		if f.deps.GitBranchRepository != nil {
			if pid, _, err := f.deriveContextFromGitBranchID(ctx, *gitBranchID); err == nil {
				projectID = pid
			}
		}
	}

	var validated any = taskData
	title := facadeDictGet(taskData, "title")
	if !taskData.Has("title") {
		title = "Task " + facadeShort(taskID)
	}
	if title != nil {
		validated = domain.TaskCompletePayload{
			ID: facadeOr(facadeDictGet(taskData, "id"), taskID), Title: value_objects.PyStr(title),
			CompletionSummary: facadeStrPtrOf(facadeDictGet(taskData, "completion_summary")),
			TestingNotes:      facadeStrPtrOf(facadeDictGet(taskData, "testing_notes")),
			CompletedAt:       facadeStrPtrOf(facadeDictGet(taskData, "completed_at")),
		}.ModelDump()
	}
	user := "system"
	if userID != nil && *userID != "" {
		user = *userID
	}
	_ = f.deps.Notifier.SyncBroadcastTask(ctx, services.SyncTaskEventParams{
		EventType: "completed", TaskID: taskID, UserID: user, TaskData: validated, GitBranchID: gitBranchID, ProjectID: projectID,
	})
}

// addContextToTask is _add_context_to_task.
func (f *TaskApplicationFacade) addContextToTask(ctx context.Context, taskDict *entities.OrderedMap[any], taskID string) *entities.OrderedMap[any] {
	resp := f.GetTask(ctx, taskID, true, true)
	if value_objects.PyTruthy(facadeDictGet(resp, "success")) {
		if data, ok := facadeDictGet(resp, "task").(*entities.OrderedMap[any]); ok && data != nil {
			taskDict.Set("context_data", facadeDictGet(data, "context_data"))
			available := any(false)
			if v, ok := data.Get("context_available"); ok {
				available = v
			}
			taskDict.Set("context_available", available)
			return taskDict
		}
	}
	taskDict.Set("context_data", nil)
	taskDict.Set("context_available", false)
	return taskDict
}

// dependencySummaryDict is list_tasks' non-minimal dependency_summary block.
func dependencySummaryDict(r *dtostask.DependencyRelationships) *entities.OrderedMap[any] {
	reasons := r.BlockingReasons
	if len(reasons) > 3 {
		reasons = reasons[:3]
	}
	if reasons == nil {
		reasons = []string{}
	}
	m := entities.NewOrderedMap[any]()
	m.Set("total_dependencies", r.TotalDependencies)
	m.Set("completed_dependencies", r.CompletedDependencies)
	m.Set("can_start", r.CanStart)
	m.Set("is_blocked", r.IsBlocked)
	m.Set("is_blocking_others", r.IsBlockingOthers)
	m.Set("dependency_completion_percentage", r.DependencyCompletionPercentage())
	m.Set("dependency_text", r.DependencySummary)
	m.Set("blocking_reasons", reasons)
	return m
}

// ListTasks is list_tasks. minimal defaults to true in Python; includeDependencies and
// includeContext default to false.
func (f *TaskApplicationFacade) ListTasks(ctx context.Context, request dtostask.ListTasksRequest, includeDependencies, minimal, includeContext bool) *entities.OrderedMap[any] {
	unexpected := func(err error) *entities.OrderedMap[any] {
		return facadeFail("list", "Unexpected error: "+err.Error())
	}
	// The minimal lister expresses one assignee and no labels. A request carrying more than
	// that falls through to the full path rather than silently returning rows the caller
	// asked to exclude - the bug that made a filtered list answer with other seats' work.
	if performance.Settings.IsPerformanceMode() && minimal && len(request.Labels) == 0 && len(request.Assignees) <= 1 {
		if f.deps.NewMinimalLister == nil {
			return unexpected(errors.New("performance-mode repository is not wired"))
		}
		lister, err := f.deps.NewMinimalLister(request.GitBranchID, f.repoUserID())
		if err != nil {
			return unexpected(err)
		}
		var assigneeID *string
		if len(request.Assignees) == 1 {
			assigneeID = &request.Assignees[0]
		}
		offset := 0
		tasks, err := lister.ListTasksMinimal(ctx, request.Status, request.Priority, assigneeID, request.GitBranchID, request.Limit, &offset)
		if err != nil {
			return unexpected(err)
		}
		list := make([]any, 0, len(tasks))
		for _, task := range tasks {
			if includeDependencies {
				blocked := false
				if f.deps.DependencyResolver != nil {
					if r, rerr := f.deps.DependencyResolver.ResolveDependencies(ctx, value_objects.PyStr(facadeDictGet(task, "id"))); rerr == nil {
						blocked = r.IsBlocked
					}
				}
				task.Set("is_blocked", blocked)
			}
			list = append(list, task)
		}
		filters := entities.NewOrderedMap[any]()
		filters.Set("status", facadeStrOrNil(request.Status))
		filters.Set("priority", facadeStrOrNil(request.Priority))
		var appliedAssignee any
		if len(request.Assignees) > 0 {
			appliedAssignee = request.Assignees
		}
		filters.Set("assignees", appliedAssignee)
		filters.Set("git_branch_id", facadeStrOrNil(request.GitBranchID))
		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		out.Set("action", "list")
		out.Set("tasks", list)
		out.Set("count", len(list))
		out.Set("filters_applied", filters)
		out.Set("minimal", minimal)
		out.Set("performance_mode", true)
		return out
	}

	response, err := f.listTasksUseCase.Execute(ctx, &request)
	if err != nil {
		return unexpected(err)
	}
	list := make([]any, 0, len(response.Tasks))
	for _, task := range response.Tasks {
		if minimal {
			item := dtostask.TaskListItemResponseFromTaskResponse(task)
			if includeDependencies && len(task.Dependencies) > 0 {
				item.IsBlocked = false
				if f.deps.DependencyResolver != nil {
					if r, rerr := f.deps.DependencyResolver.ResolveDependencies(ctx, task.ID); rerr == nil {
						item.IsBlocked = r.IsBlocked
					}
				}
			}
			d := item.ToDict()
			if includeContext {
				d = f.addContextToTask(ctx, d, task.ID)
			}
			list = append(list, d)
			continue
		}
		d, derr := task.ToDict()
		if derr != nil {
			return unexpected(derr)
		}
		if includeDependencies {
			summary := entities.NewOrderedMap[any]()
			summary.Set("total_dependencies", 0)
			summary.Set("completed_dependencies", 0)
			summary.Set("can_start", true)
			summary.Set("is_blocked", false)
			summary.Set("is_blocking_others", false)
			summary.Set("dependency_completion_percentage", 100.0)
			summary.Set("dependency_text", "No dependencies")
			summary.Set("blocking_reasons", []string{})
			if f.deps.DependencyResolver != nil {
				if r, rerr := f.deps.DependencyResolver.ResolveDependencies(ctx, task.ID); rerr == nil {
					summary = dependencySummaryDict(r)
				}
			}
			d.Set("dependency_summary", summary)
		}
		if includeContext {
			d = f.addContextToTask(ctx, d, task.ID)
		}
		list = append(list, d)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("action", "list")
	out.Set("tasks", list)
	out.Set("count", response.Count)
	out.Set("filters_applied", response.FiltersApplied)
	out.Set("minimal", minimal)
	return out
}

// SearchTasks is search_tasks.
func (f *TaskApplicationFacade) SearchTasks(ctx context.Context, request dtostask.SearchTasksRequest, includeContext bool) *entities.OrderedMap[any] {
	if strings.TrimSpace(request.Query) == "" {
		return facadeFail("search", "Search query is required")
	}
	response, err := f.deps.SearchTasks.Execute(ctx, &request)
	if err != nil {
		if facadeIsValueError(err) {
			return facadeFail("search", err.Error())
		}
		return facadeFail("search", "Unexpected error: "+err.Error())
	}
	list := make([]any, 0, len(response.Tasks))
	for _, task := range response.Tasks {
		d, derr := task.ToDict()
		if derr != nil {
			return facadeFail("search", "Unexpected error: "+derr.Error())
		}
		if includeContext {
			d = f.addContextToTask(ctx, d, task.ID)
		}
		list = append(list, d)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("action", "search")
	out.Set("tasks", list)
	out.Set("count", response.Count)
	if response.Query != nil {
		out.Set("query", *response.Query)
	} else {
		out.Set("query", nil)
	}
	return out
}

// GetNextTask is get_next_task (Python defaults: include_context=True, project_id="",
// git_branch_id="main").
func (f *TaskApplicationFacade) GetNextTask(ctx context.Context, includeContext bool, userID *string, projectID, gitBranchID string, assignee *string, labels []string) *entities.OrderedMap[any] {
	taskResponse, err := f.deps.NextTask.Execute(ctx, assignee, &projectID, labels, &gitBranchID, userID, includeContext)
	if err != nil {
		return facadeFail("next", "Unexpected error: "+err.Error())
	}
	if taskResponse == nil {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "next")
		m.Set("message", "No tasks found. Create a task to get started!")
		m.Set("error", "No actionable tasks found. Create tasks or update context for existing tasks.")
		return m
	}
	task := entities.NewOrderedMap[any]()
	task.Set("has_next", taskResponse.HasNext)
	task.Set("next_item", taskResponse.NextItem)
	task.Set("context", taskResponse.Context)
	task.Set("context_info", taskResponse.ContextInfo)
	task.Set("message", taskResponse.Message)
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("action", "next")
	out.Set("task", task)
	return out
}

// ListTasksSummary is list_tasks_summary (Python defaults offset=0, limit=20,
// include_counts=True).
func (f *TaskApplicationFacade) ListTasksSummary(ctx context.Context, filters map[string]any, offset, limit int, includeCounts bool) *entities.OrderedMap[any] {
	failure := func(err error) *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", err.Error())
		m.Set("tasks", []any{})
		return m
	}
	requestLimit := limit
	if offset > 0 {
		requestLimit = offset + limit
	}
	response, err := f.listTasksUseCase.Execute(ctx, &dtostask.ListTasksRequest{
		Status: facadeStringPtr(filters, "status"), Priority: facadeStringPtr(filters, "priority"),
		Assignees: facadeStringSlice(filters, "assignees"), Labels: facadeStringSlice(filters, "labels"),
		Limit: &requestLimit, GitBranchID: facadeStringPtr(filters, "git_branch_id"),
	})
	if err != nil {
		return failure(err)
	}
	// response.tasks[offset : offset + limit] if offset > 0 else response.tasks[:limit]
	tasks := response.Tasks
	var start, end int
	if offset > 0 {
		start, end = facadeSliceBounds(len(tasks), &offset, offset+limit)
	} else {
		start, end = facadeSliceBounds(len(tasks), nil, limit)
	}
	summaries := make([]any, 0)
	for _, task := range tasks[start:end] {
		summary := entities.NewOrderedMap[any]()
		summary.Set("id", task.ID)
		summary.Set("title", task.Title)
		summary.Set("status", task.Status)
		summary.Set("priority", task.Priority)
		summary.Set("git_branch_id", facadeStrOrNil(task.GitBranchID))
		summary.Set("project_id", facadeStrOrNil(task.ProjectID))
		summary.Set("created_at", facadeTimeStr(task.CreatedAt))
		summary.Set("updated_at", facadeTimeStr(task.UpdatedAt))
		if includeCounts {
			summary.Set("subtasks", task.Subtasks)
			summary.Set("assignees", task.Assignees)
			summary.Set("dependencies", task.Dependencies)
		}
		summaries = append(summaries, summary)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("tasks", summaries)
	out.Set("count", response.Count)
	return out
}

// facadeSliceBounds resolves Python's seq[start:stop] bounds for a sequence of length n:
// negative indexes count from the end and out-of-range values clamp (never panic).
func facadeSliceBounds(n int, start *int, stop int) (int, int) {
	clamp := func(i int) int {
		if i < 0 {
			i += n
		}
		if i < 0 {
			return 0
		}
		if i > n {
			return n
		}
		return i
	}
	lo := 0
	if start != nil {
		lo = clamp(*start)
	}
	hi := clamp(stop)
	if hi < lo {
		hi = lo
	}
	return lo, hi
}

// facadeTimeStr is `x.isoformat() if hasattr(x, "isoformat") else str(x)`.
func facadeTimeStr(t *time.Time) string {
	if t == nil {
		return "None"
	}
	return value_objects.IsoFormat(*t)
}

// ListSubtasksSummary is list_subtasks_summary (Python default include_counts=True).
func (f *TaskApplicationFacade) ListSubtasksSummary(ctx context.Context, parentTaskID string, includeCounts bool) *entities.OrderedMap[any] {
	failure := func(msg string) *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("error", msg)
		m.Set("subtasks", []any{})
		return m
	}
	if f.subtaskRepository == nil {
		return failure("Subtask repository not configured")
	}
	parentID, err := value_objects.NewTaskId(parentTaskID)
	if err != nil {
		return failure(err.Error())
	}
	subtasks, err := f.subtaskRepository.FindByParentTaskID(ctx, parentID)
	if err != nil {
		return failure(err.Error())
	}
	summaries := make([]any, 0, len(subtasks))
	for _, st := range subtasks {
		summary := entities.NewOrderedMap[any]()
		id := ""
		if st.ID != nil {
			id = st.ID.Value
		}
		status, priority := "", "medium"
		if st.Status != nil {
			status = st.Status.Value
		}
		if st.Priority != nil {
			priority = st.Priority.Value
		}
		summary.Set("id", id)
		summary.Set("title", st.Title)
		summary.Set("status", status)
		summary.Set("priority", priority)
		summary.Set("progress_percentage", st.ProgressPercentage)
		if includeCounts {
			assignees := st.Assignees
			if assignees == nil {
				assignees = []string{}
			}
			summary.Set("assignees", assignees)
		}
		summaries = append(summaries, summary)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("subtasks", summaries)
	return out
}

// dependencyUpdateBroadcast is the shared WebSocket block of add/remove_dependency.
func (f *TaskApplicationFacade) dependencyUpdateBroadcast(ctx context.Context, task *entities.Task, taskID string, taskDict *entities.OrderedMap[any]) {
	if f.deps.Notifier == nil {
		return
	}
	status, priority := "", ""
	if task.Status != nil {
		status = task.Status.Value
	}
	if task.Priority != nil {
		priority = task.Priority.Value
	}
	branch := ""
	if task.GitBranchID != nil {
		branch = *task.GitBranchID
	} else {
		branch = "None"
	}
	assignees, labels := facadeStringList(facadeDictGet(taskDict, "assignees")), facadeStringList(facadeDictGet(taskDict, "labels"))
	if len(assignees) == 0 {
		assignees = task.Assignees
	}
	if len(labels) == 0 {
		labels = task.Labels
	}
	var description *string
	desc := facadeOr(facadeDictGet(taskDict, "description"), task.Description)
	description = &desc
	payload := domain.TaskUpdatePayload{
		ID: facadeOr(facadeDictGet(taskDict, "id"), taskID), Title: facadeOr(facadeDictGet(taskDict, "title"), task.Title),
		Description: description, Status: facadeOr(facadeDictGet(taskDict, "status"), status),
		Priority: facadeOr(facadeDictGet(taskDict, "priority"), priority), GitBranchID: facadeOr(facadeDictGet(taskDict, "git_branch_id"), branch),
		Assignees: assignees, Labels: labels, UpdatedAt: facadeStrPtrOf(facadeDictGet(taskDict, "updated_at")),
	}
	_ = f.deps.Notifier.SyncBroadcastTask(ctx, services.SyncTaskEventParams{
		EventType: "updated", TaskID: taskID, UserID: "system", TaskData: payload.ModelDump(),
	})
}

type facadeAcrossContexts interface {
	FindByIDAcrossContexts(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
}

// AddDependency is add_dependency.
func (f *TaskApplicationFacade) AddDependency(ctx context.Context, taskID, dependencyID string) *entities.OrderedMap[any] {
	failure := func(err error) *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		if facadeIsTaskNotFound(err) || facadeIsValueError(err) {
			m.Set("error", err.Error())
		} else {
			m.Set("error", "Failed to add dependency: "+err.Error())
		}
		return m
	}
	noop := func(msg string) *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", true)
		m.Set("message", msg)
		m.Set("task", nil)
		return m
	}
	if strings.TrimSpace(taskID) == "" {
		return noop("No-op: task_id not provided (validation pending)")
	}
	if strings.TrimSpace(dependencyID) == "" {
		return noop("No-op: dependency_id not provided (validation pending)")
	}
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return failure(err)
	}
	task, err := f.taskRepository.FindByID(ctx, id)
	if err != nil {
		return failure(err)
	}
	if task == nil {
		return failure(exceptions.NewTaskNotFoundError(fmt.Sprintf("Task with ID %s not found", taskID)))
	}
	depID, err := value_objects.NewTaskId(dependencyID)
	if err != nil {
		return failure(err)
	}
	dependencyTask, err := f.taskRepository.FindByID(ctx, depID)
	if err != nil {
		return failure(err)
	}
	if dependencyTask == nil {
		if dependencyTask, err = f.taskRepository.FindByIDAllStates(ctx, depID); err != nil {
			return failure(err)
		}
	}
	if dependencyTask == nil {
		if across, ok := f.taskRepository.(facadeAcrossContexts); ok {
			if dependencyTask, err = across.FindByIDAcrossContexts(ctx, depID); err != nil {
				return failure(err)
			}
		}
	}
	if dependencyTask == nil {
		return failure(exceptions.NewTaskNotFoundError(fmt.Sprintf("Dependency task with ID %s not found", dependencyID)))
	}

	var message string
	addErr := task.AddDependency(*dependencyTask.ID)
	if addErr == nil {
		_, addErr = f.taskRepository.Save(ctx, task)
	}
	switch {
	case addErr == nil:
		message = fmt.Sprintf("Dependency %s added to task %s", dependencyID, taskID)
	case facadeIsValueError(addErr):
		if strings.Contains(strings.ToLower(addErr.Error()), "cannot depend on itself") {
			m := entities.NewOrderedMap[any]()
			m.Set("success", false)
			m.Set("error", addErr.Error())
			return m
		}
		message = fmt.Sprintf("Dependency %s already exists for task %s", dependencyID, taskID)
	default:
		return failure(addErr)
	}

	full, err := taskDictOf(task)
	if err != nil {
		return failure(err)
	}
	taskDict, err := services.MinimalResponseSerializer{}.SerializeTaskMinimal(full, "update")
	if err != nil {
		return failure(err)
	}
	f.dependencyUpdateBroadcast(ctx, task, taskID, taskDict)

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", message)
	out.Set("task", taskDict)
	return out
}

// RemoveDependency is remove_dependency.
func (f *TaskApplicationFacade) RemoveDependency(ctx context.Context, taskID, dependencyID string) *entities.OrderedMap[any] {
	failure := func(err error) *entities.OrderedMap[any] {
		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		if facadeIsTaskNotFound(err) || facadeIsValueError(err) {
			m.Set("error", err.Error())
		} else {
			m.Set("error", "Failed to remove dependency: "+err.Error())
		}
		return m
	}
	if strings.TrimSpace(taskID) == "" {
		return failure(value_objects.ValueErrorf("Task ID cannot be empty or whitespace"))
	}
	if strings.TrimSpace(dependencyID) == "" {
		return failure(value_objects.ValueErrorf("Dependency ID cannot be empty or whitespace"))
	}
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return failure(err)
	}
	task, err := f.taskRepository.FindByID(ctx, id)
	if err != nil {
		return failure(err)
	}
	if task == nil {
		return failure(exceptions.NewTaskNotFoundError(fmt.Sprintf("Task with ID %s not found", taskID)))
	}
	depID, err := value_objects.NewTaskId(dependencyID)
	if err != nil {
		return failure(err)
	}
	message := fmt.Sprintf("Dependency %s removed from task %s", dependencyID, taskID)
	removeErr := task.RemoveDependency(depID)
	if removeErr == nil {
		_, removeErr = f.taskRepository.Save(ctx, task)
	}
	if removeErr != nil {
		message = fmt.Sprintf("Dependency %s not found on task %s", dependencyID, taskID)
	}

	full, err := taskDictOf(task)
	if err != nil {
		return failure(err)
	}
	taskDict, err := services.MinimalResponseSerializer{}.SerializeTaskMinimal(full, "update")
	if err != nil {
		return failure(err)
	}
	f.dependencyUpdateBroadcast(ctx, task, taskID, taskDict)

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", message)
	out.Set("task", taskDict)
	return out
}
