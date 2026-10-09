// Package facades ports the subtask application facade.
package facades

import (
	"context"
	"strconv"

	"agenthub/fastmcp/task_management/application/dtos/subtask"
	"agenthub/fastmcp/task_management/application/services"
	usecases "agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskRepositoryFactory mirrors Python TaskRepositoryFactory.create_repository.
// Note: the existing infrastructure RepositoryFactory exposes GetTaskRepository,
// not CreateRepository, so an adapter is required (see report).
type TaskRepositoryFactory interface {
	CreateRepository(projectID, gitBranchName string, userID *string) (repositories.TaskRepository, error)
}

// SubtaskRepositoryFactory mirrors SubtaskRepositoryFactory.create_subtask_repository.
// Existing infrastructure SubtaskRepositoryFactory.CreateSubtaskRepository matches.
type SubtaskRepositoryFactory interface {
	CreateSubtaskRepository(projectID, gitBranchName string, userID *string) (repositories.SubtaskRepository, error)
}

// SubtaskContextResolver covers the DB-backed context derivation helpers in the
// Python module (get_session + ORM models + auth_helper); their Go ports are
// infrastructure/database/session_manager.go, infrastructure/database/models.go and
// interface/mcp_controllers/auth_helper/auth_helper.go.
type SubtaskContextResolver interface {
	DeriveContextFromTask(ctx context.Context, taskID string) (*entities.OrderedMap[any], error)
	DeriveContextFromGitBranchID(ctx context.Context, gitBranchID string) (*entities.OrderedMap[any], error)
}

// SubtaskEventBroadcaster covers WebSocketNotificationService static broadcasts.
type SubtaskEventBroadcaster interface {
	SyncBroadcastSubtaskEvent(ctx context.Context, eventType, subtaskID, taskID, userID string, subtaskData any) error
	SyncBroadcastTaskEvent(ctx context.Context, eventType, taskID, userID string, taskData any, metadata *entities.OrderedMap[any]) error
}

// SubtaskContextSyncService covers TaskContextSyncService.sync_subtask_counts.
type SubtaskContextSyncService interface {
	SyncSubtaskCounts(ctx context.Context, taskID string, subtaskRepository repositories.SubtaskRepository) error
}

// SubtaskApplicationFacade is the Go port of SubtaskApplicationFacade.
type SubtaskApplicationFacade struct {
	taskRepository           repositories.TaskRepository
	subtaskRepository        repositories.SubtaskRepository
	taskRepositoryFactory    TaskRepositoryFactory
	subtaskRepositoryFactory SubtaskRepositoryFactory
	userID                   *string

	agentInheritanceService *services.AgentInheritanceService

	addSubtaskUseCase      *usecases.AddSubtaskUseCase
	updateSubtaskUseCase   *usecases.UpdateSubtaskUseCase
	removeSubtaskUseCase   *usecases.RemoveSubtaskUseCase
	getSubtaskUseCase      *usecases.GetSubtaskUseCase
	getSubtasksUseCase     *usecases.GetSubtasksUseCase
	completeSubtaskUseCase *usecases.CompleteSubtaskUseCase

	// Optional collaborators, nil-guarded. ContextResolver has NO Go implementation yet;
	// ContextSync and EventBroadcaster do.
	ContextResolver  SubtaskContextResolver
	EventBroadcaster SubtaskEventBroadcaster
	ContextSync      SubtaskContextSyncService
}

// NewSubtaskApplicationFacade mirrors __init__.
func NewSubtaskApplicationFacade(
	taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository,
	taskRepositoryFactory TaskRepositoryFactory,
	subtaskRepositoryFactory SubtaskRepositoryFactory,
	userID *string,
) *SubtaskApplicationFacade {
	f := &SubtaskApplicationFacade{
		taskRepository:           taskRepository,
		subtaskRepository:        subtaskRepository,
		taskRepositoryFactory:    taskRepositoryFactory,
		subtaskRepositoryFactory: subtaskRepositoryFactory,
		userID:                   userID,
	}
	if taskRepository != nil && subtaskRepository != nil {
		f.agentInheritanceService = services.NewAgentInheritanceService(taskRepository, subtaskRepository)
	}
	if taskRepository != nil {
		f.addSubtaskUseCase = usecases.NewAddSubtaskUseCase(taskRepository, subtaskRepository)
		f.updateSubtaskUseCase = usecases.NewUpdateSubtaskUseCase(taskRepository, subtaskRepository)
		f.removeSubtaskUseCase = usecases.NewRemoveSubtaskUseCase(taskRepository, subtaskRepository)
		f.getSubtaskUseCase = usecases.NewGetSubtaskUseCase(taskRepository, subtaskRepository)
		f.getSubtasksUseCase = usecases.NewGetSubtasksUseCase(taskRepository, subtaskRepository)
		f.completeSubtaskUseCase = usecases.NewCompleteSubtaskUseCase(taskRepository, subtaskRepository)
	}
	return f
}

// WithProgressStore wires the parent-task progress update the add/update/remove use cases
// perform through TaskProgressService(task_repository, subtask_repository).
func (f *SubtaskApplicationFacade) WithProgressStore(store services.TaskProgressStore) *SubtaskApplicationFacade {
	if f.taskRepository == nil {
		return f
	}
	updater := services.NewTaskProgressService(f.taskRepository, f.subtaskRepository, nil, store)
	f.addSubtaskUseCase.ProgressUpdater = updater
	f.updateSubtaskUseCase.ProgressUpdater = updater
	f.removeSubtaskUseCase.ProgressUpdater = updater
	return f
}

// deriveContextFromTask delegates to the resolver (Python queries the DB directly).
func (f *SubtaskApplicationFacade) deriveContextFromTask(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	if f.ContextResolver != nil {
		return f.ContextResolver.DeriveContextFromTask(ctx, taskID)
	}
	return nil, exceptions.NewTaskNotFoundError("Task " + taskID + " not found")
}

func (f *SubtaskApplicationFacade) getContextRepositories(ctx context.Context,
	projectID, gitBranchName, userID *string) (repositories.TaskRepository, repositories.SubtaskRepository, error) {
	if f.taskRepositoryFactory != nil && f.subtaskRepositoryFactory != nil &&
		nonEmpty(projectID) && nonEmpty(gitBranchName) && nonEmpty(userID) {
		tr, err := f.taskRepositoryFactory.CreateRepository(*projectID, *gitBranchName, userID)
		if err != nil {
			return nil, nil, err
		}
		sr, err := f.subtaskRepositoryFactory.CreateSubtaskRepository(*projectID, *gitBranchName, userID)
		if err != nil {
			return nil, nil, err
		}
		return tr, sr, nil
	}
	return f.taskRepository, f.subtaskRepository, nil
}

func nonEmpty(s *string) bool { return s != nil && *s != "" }

// HandleManageSubtask mirrors handle_manage_subtask. The legacy positional
// argument shuffle cannot be expressed in Go (statically typed) and is omitted.
func (f *SubtaskApplicationFacade) HandleManageSubtask(ctx context.Context, action, taskID string,
	subtaskData *entities.OrderedMap[any], subtaskID *string, suppressBroadcast bool,
	projectID, gitBranchName, userID *string) (*entities.OrderedMap[any], error) {

	if taskID == "" {
		return nil, &value_objects.ValueError{Msg: "Task ID is required"}
	}

	var taskRepository repositories.TaskRepository
	var subtaskRepository repositories.SubtaskRepository
	var err error

	if f.taskRepositoryFactory != nil && f.subtaskRepositoryFactory != nil {
		contextMap, derr := f.deriveContextFromTask(ctx, taskID)
		if derr != nil {
			return nil, derr
		}
		effectiveUserID := userID
		if effectiveUserID == nil {
			effectiveUserID = omStringPtr(contextMap, "user_id")
		}
		taskRepository, subtaskRepository, err = f.getContextRepositories(ctx,
			omStringPtr(contextMap, "project_id"), omStringPtr(contextMap, "git_branch_name"), effectiveUserID)
		if err != nil {
			return nil, err
		}
	} else {
		taskRepository, subtaskRepository, err = f.getContextRepositories(ctx, projectID, gitBranchName, userID)
		if err != nil {
			return nil, err
		}
	}

	action = value_objects.PyLower(action)
	if action == "add" {
		action = "create"
	}
	switch action {
	case "create":
		return f.handleCreateSubtask(ctx, taskID, subtaskData, taskRepository, subtaskRepository)
	case "update":
		return f.handleUpdateSubtask(ctx, taskID, subtaskData, taskRepository, subtaskRepository, subtaskID, suppressBroadcast)
	case "delete":
		return f.handleDeleteSubtask(ctx, taskID, subtaskData, taskRepository, subtaskRepository, subtaskID)
	case "list":
		return f.handleListSubtasks(ctx, taskID, taskRepository, subtaskRepository)
	case "get":
		return f.handleGetSubtask(ctx, taskID, subtaskData, taskRepository, subtaskRepository, subtaskID)
	case "complete":
		return f.handleCompleteSubtask(ctx, taskID, subtaskData, taskRepository, subtaskRepository, subtaskID)
	default:
		return nil, &value_objects.ValueError{Msg: "Unsupported subtask action: " + action}
	}
}

func (f *SubtaskApplicationFacade) handleCreateSubtask(ctx context.Context, taskID string,
	subtaskData *entities.OrderedMap[any], taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository) (*entities.OrderedMap[any], error) {

	// `not subtask_data or "title" not in subtask_data`: an empty title passes and is
	// rejected later by the use case/entity ("Title cannot be empty").
	if subtaskData == nil || len(subtaskData.Keys()) == 0 || !subtaskData.Has("title") {
		return nil, &value_objects.ValueError{Msg: "subtask_data with title is required"}
	}
	title := omStringDefault(subtaskData, "title", "")

	addUseCase := f.addSubtaskUseCase
	if addUseCase == nil {
		addUseCase = usecases.NewAddSubtaskUseCase(taskRepository, subtaskRepository)
	}

	request, err := subtask.NewAddSubtaskRequest(subtask.AddSubtaskRequest{
		TaskID:      taskID,
		Title:       title,
		Description: omStringDefault(subtaskData, "description", ""),
		Assignees:   omStrings(subtaskData, "assignees"),
		Priority:    omStringPtr(subtaskData, "priority"),
	})
	if err != nil {
		return nil, err
	}
	response, err := addUseCase.Execute(ctx, request)
	if err != nil {
		return nil, err
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("action", "create")
	result.Set("message", "Subtask '"+title+"' created for task "+taskID)
	result.Set("subtask", response.Subtask)
	result.Set("task_id", response.TaskID)
	result.Set("progress", response.Progress)
	if response.AgentInheritanceApplied {
		result.Set("agent_inheritance_applied", true)
		result.Set("inherited_assignees", response.InheritedAssignees)
		result.Set("message", "Subtask '"+title+"' created for task "+taskID+" with "+
			strconv.Itoa(len(response.InheritedAssignees))+" agent(s) inherited from parent")
	}

	f.broadcastCreated(ctx, taskID, response, taskRepository)
	return result, nil
}

func (f *SubtaskApplicationFacade) broadcastCreated(ctx context.Context, taskID string,
	response *subtask.SubtaskResponse, taskRepository repositories.TaskRepository) {
	if f.EventBroadcaster == nil {
		return
	}
	contextMap, err := f.deriveContextFromTask(ctx, taskID)
	if err != nil {
		return
	}
	userID := omStringDefault(contextMap, "user_id", "system")
	sub := response.Subtask
	payload := domain.SubtaskCreatePayload{
		ID:                 omStringDefault(sub, "id", ""),
		Title:              omStringDefault(sub, "title", ""),
		Description:        omStringPtr(sub, "description"),
		Status:             omStringDefault(sub, "status", "todo"),
		TaskID:             taskID,
		ProgressPercentage: omIntPtr(sub, "progress_percentage"),
		CreatedAt:          omStringPtr(sub, "created_at"),
		UpdatedAt:          omStringPtr(sub, "updated_at"),
	}
	_ = f.EventBroadcaster.SyncBroadcastSubtaskEvent(ctx, "created", payload.ID, taskID, userID, payload.ModelDump())
}

func (f *SubtaskApplicationFacade) handleUpdateSubtask(ctx context.Context, taskID string,
	subtaskData *entities.OrderedMap[any], taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository, subtaskID *string,
	suppressBroadcast bool) (*entities.OrderedMap[any], error) {

	actualSubtaskID := ""
	if nonEmpty(subtaskID) {
		actualSubtaskID = *subtaskID
	} else if subtaskData != nil {
		actualSubtaskID = omStringDefault(subtaskData, "subtask_id", "")
	}
	if actualSubtaskID == "" {
		return nil, &value_objects.ValueError{Msg: "subtask_id is required (either as parameter or in subtask_data)"}
	}

	updateUseCase := f.updateSubtaskUseCase
	if updateUseCase == nil {
		updateUseCase = usecases.NewUpdateSubtaskUseCase(taskRepository, subtaskRepository)
	}

	request := &subtask.UpdateSubtaskRequest{
		TaskID:             taskID,
		ID:                 actualSubtaskID,
		Title:              omStringPtr(subtaskData, "title"),
		Description:        omStringPtr(subtaskData, "description"),
		Status:             omStringPtr(subtaskData, "status"),
		Priority:           omStringPtr(subtaskData, "priority"),
		Assignees:          omAnySlice(subtaskData, "assignees"),
		ProgressPercentage: omIntPtr(subtaskData, "progress_percentage"),
		ProgressNotes:      omStringPtr(subtaskData, "progress_notes"),
	}
	response, err := updateUseCase.Execute(ctx, request)
	if err != nil {
		return nil, err
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("action", "update")
	result.Set("message", "Subtask "+actualSubtaskID+" updated")
	result.Set("subtask", response.Subtask)

	if !suppressBroadcast && f.EventBroadcaster != nil {
		if contextMap, derr := f.deriveContextFromTask(ctx, taskID); derr == nil {
			userID := omStringDefault(contextMap, "user_id", "system")
			minimal, merr := (services.MinimalResponseSerializer{}).SerializeSubtaskMinimal(response.Subtask, "update")
			if merr == nil {
				_ = f.EventBroadcaster.SyncBroadcastSubtaskEvent(ctx, "updated", actualSubtaskID, taskID, userID, minimal)
			}
		}
	}
	f.syncSubtaskCounts(ctx, taskID, subtaskRepository)
	return result, nil
}

func (f *SubtaskApplicationFacade) handleDeleteSubtask(ctx context.Context, taskID string,
	subtaskData *entities.OrderedMap[any], taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository, subtaskID *string) (*entities.OrderedMap[any], error) {

	actualSubtaskID := ""
	if nonEmpty(subtaskID) {
		actualSubtaskID = *subtaskID
	} else if subtaskData != nil {
		actualSubtaskID = omStringDefault(subtaskData, "subtask_id", "")
	}
	if actualSubtaskID == "" {
		return nil, &value_objects.ValueError{Msg: "subtask_id is required (either as parameter or in subtask_data)"}
	}

	removeUseCase := f.removeSubtaskUseCase
	if removeUseCase == nil {
		removeUseCase = usecases.NewRemoveSubtaskUseCase(taskRepository, subtaskRepository)
	}

	removeResult, err := removeUseCase.Execute(ctx, taskID, actualSubtaskID, nil)
	if err != nil {
		return nil, err
	}
	success, _ := removeResult.Get("success")
	successBool, _ := success.(bool)
	progress, ok := removeResult.Get("progress")
	if !ok {
		progress = entities.NewOrderedMap[any]()
	}
	response := entities.NewOrderedMap[any]()
	response.Set("success", successBool)
	response.Set("action", "delete")
	response.Set("message", "Subtask "+actualSubtaskID+" deleted from task "+taskID)
	response.Set("progress", progress)

	if successBool {
		if f.EventBroadcaster != nil {
			userID := "system"
			var parentTask *entities.Task
			if taskIDObj, terr := value_objects.NewTaskId(taskID); terr == nil {
				parentTask, _ = taskRepository.FindByID(ctx, taskIDObj)
			}
			if parentTask != nil && parentTask.UserID != nil {
				userID = *parentTask.UserID
			}
			subtaskTitle := ""
			if subMap, ok := removeResult.Get("subtask"); ok {
				if m, ok := subMap.(*entities.OrderedMap[any]); ok {
					subtaskTitle = omStringDefault(m, "title", "")
				}
			}
			if subtaskTitle == "" {
				prefix := actualSubtaskID
				if len(prefix) > 8 {
					prefix = prefix[:8]
				}
				subtaskTitle = "Subtask " + prefix
			}
			title := subtaskTitle
			payload, perr := domain.NewSubtaskDeletePayload(actualSubtaskID, taskID, &title)
			if perr == nil {
				_ = f.EventBroadcaster.SyncBroadcastSubtaskEvent(ctx, "deleted", actualSubtaskID, taskID, userID, payload.ModelDump())
			}
		}
		f.syncSubtaskCounts(ctx, taskID, subtaskRepository)
	}
	return response, nil
}

func (f *SubtaskApplicationFacade) handleListSubtasks(ctx context.Context, taskID string,
	taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) (*entities.OrderedMap[any], error) {
	getSubtasks := f.getSubtasksUseCase
	if getSubtasks == nil {
		getSubtasks = usecases.NewGetSubtasksUseCase(taskRepository, subtaskRepository)
	}
	result, err := getSubtasks.Execute(ctx, taskID)
	if err != nil {
		return nil, err
	}
	subtasks, _ := result.Get("subtasks")
	progress, _ := result.Get("progress")
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("action", "list")
	out.Set("message", "Subtasks retrieved for task "+taskID)
	out.Set("subtasks", subtasks)
	out.Set("progress", progress)
	return out, nil
}

func (f *SubtaskApplicationFacade) handleGetSubtask(ctx context.Context, taskID string,
	subtaskData *entities.OrderedMap[any], taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository, subtaskID *string) (*entities.OrderedMap[any], error) {

	actualSubtaskID := ""
	if nonEmpty(subtaskID) {
		actualSubtaskID = *subtaskID
	} else if subtaskData != nil {
		actualSubtaskID = omStringDefault(subtaskData, "subtask_id", "")
	}
	if actualSubtaskID == "" {
		return nil, &value_objects.ValueError{Msg: "subtask_id is required (either as parameter or in subtask_data)"}
	}
	getSubtask := f.getSubtaskUseCase
	if getSubtask == nil {
		getSubtask = usecases.NewGetSubtaskUseCase(taskRepository, subtaskRepository)
	}
	result, err := getSubtask.Execute(ctx, taskID, actualSubtaskID)
	if err != nil {
		return nil, err
	}
	subtaskValue, _ := result.Get("subtask")
	progress, _ := result.Get("progress")
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("action", "get")
	out.Set("message", "Subtask "+actualSubtaskID+" retrieved")
	out.Set("subtask", subtaskValue)
	out.Set("progress", progress)
	return out, nil
}

func (f *SubtaskApplicationFacade) handleCompleteSubtask(ctx context.Context, taskID string,
	subtaskData *entities.OrderedMap[any], taskRepository repositories.TaskRepository,
	subtaskRepository repositories.SubtaskRepository, subtaskID *string) (*entities.OrderedMap[any], error) {

	actualSubtaskID := ""
	if nonEmpty(subtaskID) {
		actualSubtaskID = *subtaskID
	} else if subtaskData != nil {
		actualSubtaskID = omStringDefault(subtaskData, "subtask_id", "")
	}
	if actualSubtaskID == "" {
		return nil, &value_objects.ValueError{Msg: "subtask_id is required (either as parameter or in subtask_data)"}
	}

	userID := omStringPtr(subtaskData, "user_id")
	completionSummary := omStringPtr(subtaskData, "completion_summary")
	insightsFound := omAnySlice(subtaskData, "insights_found")
	testingNotes := omStringPtr(subtaskData, "testing_notes")

	completeUseCase := f.completeSubtaskUseCase
	if completeUseCase == nil {
		completeUseCase = usecases.NewCompleteSubtaskUseCase(taskRepository, subtaskRepository)
	}
	result, err := completeUseCase.Execute(ctx, taskID, actualSubtaskID, userID, completionSummary, insightsFound, testingNotes)
	if err != nil {
		return nil, err
	}

	f.syncSubtaskCounts(ctx, taskID, subtaskRepository)

	success, _ := result.Get("success")
	successBool, _ := success.(bool)
	progress, _ := result.Get("progress")

	subtaskObj := entities.NewOrderedMap[any]()
	subtaskObj.Set("id", actualSubtaskID)
	subtaskObj.Set("completed", true)

	response := entities.NewOrderedMap[any]()
	response.Set("success", successBool)
	response.Set("action", "complete")
	response.Set("message", "Subtask "+actualSubtaskID+" completed")
	response.Set("subtask", subtaskObj)
	response.Set("progress", progress)

	if successBool && f.EventBroadcaster != nil {
		if contextMap, derr := f.deriveContextFromTask(ctx, taskID); derr == nil {
			broadcastUserID := omStringDefault(contextMap, "user_id", "system")
			enriched := f.completeEnriched(ctx, actualSubtaskID, subtaskRepository, completionSummary, testingNotes, insightsFound)
			_ = f.EventBroadcaster.SyncBroadcastSubtaskEvent(ctx, "completed", actualSubtaskID, taskID, broadcastUserID, enriched)
		}
	}
	return response, nil
}

// completeEnriched ports the enrichment block. The Python code queries the ORM
// model directly for persistence-only fields (blockers, progress_history,
// completion_summary, insights_found, impact_on_parent); those have no Go port,
// so they are taken from the request or defaulted.
func (f *SubtaskApplicationFacade) completeEnriched(ctx context.Context, subtaskID string,
	subtaskRepository repositories.SubtaskRepository, completionSummary, testingNotes *string,
	insightsFound []any) *entities.OrderedMap[any] {

	title := "Subtask " + safePrefix(subtaskID, 8)
	description := ""
	assignees := []string{}
	if subtaskRepository != nil {
		if st, err := subtaskRepository.FindByID(ctx, subtaskID); err == nil && st != nil {
			title = st.Title
			description = st.Description
			assignees = st.Assignees
		}
	}
	summary := ""
	if completionSummary != nil {
		summary = *completionSummary
	}
	notes := ""
	if testingNotes != nil {
		notes = *testingNotes
	}
	insights := insightsFound
	if insights == nil {
		insights = []any{}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("id", subtaskID)
	out.Set("status", "done")
	out.Set("title", title)
	out.Set("description", description)
	out.Set("completion_summary", summary)
	out.Set("testing_notes", notes)
	out.Set("progress_percentage", 100)
	out.Set("assignees", assignees)
	out.Set("insights_found", insights)
	out.Set("blockers", []any{})
	out.Set("progress_history", entities.NewOrderedMap[any]())
	out.Set("progress_count", 0)
	out.Set("impact_on_parent", "")
	return out
}

func safePrefix(s string, n int) string {
	if len(s) < n {
		return s
	}
	return s[:n]
}

func (f *SubtaskApplicationFacade) syncSubtaskCounts(ctx context.Context, taskID string,
	subtaskRepository repositories.SubtaskRepository) {
	if f.ContextSync == nil {
		return
	}
	_ = f.ContextSync.SyncSubtaskCounts(ctx, taskID, subtaskRepository)
}

// CreateSubtaskParams mirrors the keyword arguments of create_subtask.
type CreateSubtaskParams struct {
	TaskID      *string
	Title       *string
	Description *string
	Assignees   *string
	Priority    *string
	UserID      *string
}

// CreateSubtask ports the keyword-argument call style. The Python
// CreateSubtaskRequest positional style maps to CreateSubtaskFromRequest.
func (f *SubtaskApplicationFacade) CreateSubtask(ctx context.Context, params CreateSubtaskParams) (*entities.OrderedMap[any], error) {
	if params.TaskID == nil {
		return nil, &value_objects.TypeError{Msg: "create_subtask() missing required argument: 'task_id' (use task_id=... or pass CreateSubtaskRequest)"}
	}
	if params.Title == nil {
		return nil, &value_objects.TypeError{Msg: "create_subtask() missing required argument: 'title'"}
	}
	subtaskData := entities.NewOrderedMap[any]()
	subtaskData.Set("title", *params.Title)
	subtaskData.Set("description", ptrValue(params.Description))
	subtaskData.Set("assignees", ptrValue(params.Assignees))
	priority := "medium"
	if params.Priority != nil {
		priority = *params.Priority
	}
	subtaskData.Set("priority", priority)
	return f.HandleManageSubtask(ctx, "create", *params.TaskID, subtaskData, nil, false, nil, nil, params.UserID)
}

// CreateSubtaskFromRequest ports the positional CreateSubtaskRequest style.
func (f *SubtaskApplicationFacade) CreateSubtaskFromRequest(ctx context.Context,
	request *subtask.CreateSubtaskRequest) (*entities.OrderedMap[any], error) {
	subtaskData := entities.NewOrderedMap[any]()
	subtaskData.Set("title", request.Title)
	subtaskData.Set("description", ptrValue(request.Description))
	subtaskData.Set("assignees", request.Assignees)
	priority := "medium"
	if request.Priority != nil {
		priority = *request.Priority
	}
	subtaskData.Set("priority", priority)
	status := ptrValue(request.Status)
	if status != nil {
		subtaskData.Set("status", status)
	}
	return f.HandleManageSubtask(ctx, "create", request.TaskID, subtaskData, nil, false, nil, nil, nil)
}

// CompleteSubtask ports the individual-parameter call style.
func (f *SubtaskApplicationFacade) CompleteSubtask(ctx context.Context, taskID, subtaskID string,
	completionSummary, testingNotes *string) (*entities.OrderedMap[any], error) {
	if taskID == "" || subtaskID == "" {
		return nil, &value_objects.ValueError{Msg: "task_id and subtask_id are required"}
	}
	subtaskData := entities.NewOrderedMap[any]()
	subtaskData.Set("completion_summary", ptrValue(completionSummary))
	subtaskData.Set("testing_notes", ptrValue(testingNotes))
	sid := subtaskID
	return f.HandleManageSubtask(ctx, "complete", taskID, subtaskData, &sid, false, nil, nil, nil)
}

// DeleteSubtask ports the individual-parameter call style.
func (f *SubtaskApplicationFacade) DeleteSubtask(ctx context.Context, taskID, subtaskID string,
	extra *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	if taskID == "" || subtaskID == "" {
		return nil, &value_objects.ValueError{Msg: "task_id and subtask_id are required"}
	}
	if extra == nil {
		extra = entities.NewOrderedMap[any]()
	}
	sid := subtaskID
	return f.HandleManageSubtask(ctx, "delete", taskID, extra, &sid, false, nil, nil, nil)
}

func ptrValue(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// ---- OrderedMap field helpers ----

func omString(m *entities.OrderedMap[any], key string) (string, bool) {
	if m == nil {
		return "", false
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return "", false
	}
	s, ok := v.(string)
	return s, ok
}

func omStringDefault(m *entities.OrderedMap[any], key, def string) string {
	if s, ok := omString(m, key); ok {
		return s
	}
	return def
}

func omStringPtr(m *entities.OrderedMap[any], key string) *string {
	if s, ok := omString(m, key); ok {
		return &s
	}
	return nil
}

func omIntPtr(m *entities.OrderedMap[any], key string) *int {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return nil
	}
	switch n := v.(type) {
	case int:
		return &n
	case *int:
		return n
	}
	return nil
}

func omStrings(m *entities.OrderedMap[any], key string) []string {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return nil
	}
	switch s := v.(type) {
	case []string:
		return s
	case []any:
		out := make([]string, 0, len(s))
		for _, item := range s {
			if str, ok := item.(string); ok {
				out = append(out, str)
			}
		}
		return out
	}
	return nil
}

func omAnySlice(m *entities.OrderedMap[any], key string) []any {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok || v == nil {
		return nil
	}
	switch s := v.(type) {
	case []any:
		return s
	case []string:
		out := make([]any, 0, len(s))
		for _, item := range s {
			out = append(out, item)
		}
		return out
	}
	return nil
}
