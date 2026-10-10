package interfacelayer

import (
	"context"
	"sort"
	"strconv"
	"strings"
	"time"

	authmw "agenthub/fastmcp/auth/middleware"
	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper"
	authservices "agenthub/fastmcp/task_management/interface/mcp_controllers/auth_helper/services"
	branchctl "agenthub/fastmcp/task_management/interface/mcp_controllers/git_branch_mcp_controller"
	projectctl "agenthub/fastmcp/task_management/interface/mcp_controllers/project_mcp_controller"
	projectfactories "agenthub/fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/factories"
	projecthandlers "agenthub/fastmcp/task_management/interface/mcp_controllers/project_mcp_controller/handlers"
	subtaskctl "agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller"
	subtaskhandlers "agenthub/fastmcp/task_management/interface/mcp_controllers/subtask_mcp_controller/handlers"
	taskfactories "agenthub/fastmcp/task_management/interface/mcp_controllers/task_mcp_controller/factories"
	wfbranch "agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_guidance/git_branch"
	wfsubtask "agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_guidance/subtask"
	"agenthub/fastmcp/task_management/interface/mcp_controllers/workflow_hint_enhancer"
	"agenthub/fastmcp/task_management/interface/utils"
)

// This file is Go-only composition glue (no Python module): the Go MCP controllers
// each declare their own consumer-side ResponseFormatter interface, whereas
// Python hands every controller the same StandardResponseFormatter. These
// adapters expose the one utils.MCPResponseFormatter through those interfaces.

// toOrderedData converts the Python `data: dict` argument into an ordered map.
func toOrderedData(data any) *entities.OrderedMap[any] {
	switch d := data.(type) {
	case nil:
		return nil
	case *entities.OrderedMap[any]:
		return d
	case value_objects.OrderedAny:
		m := entities.NewOrderedMap[any]()
		for _, k := range d.KeysAny() {
			m.Set(k, d.GetAny(k))
		}
		return m
	case map[string]any:
		keys := make([]string, 0, len(d))
		for k := range d {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		m := entities.NewOrderedMap[any]()
		for _, k := range keys {
			m.Set(k, d[k])
		}
		return m
	}
	m := entities.NewOrderedMap[any]()
	m.Set("result", data)
	return m
}

// taskResponseFormatter is the task controller flavour: the third argument of
// create_success_response is workflow_guidance.
type taskResponseFormatter struct{ f *utils.MCPResponseFormatter }

func (a taskResponseFormatter) CreateSuccessResponse(operation string, data any, workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.f.CreateSuccessResponse(operation, toOrderedData(data), nil, workflowGuidance, nil, nil)
}

func (a taskResponseFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.f.CreateErrorResponse(operation, errorMessage, errorCode, metadata)
}

func (a taskResponseFormatter) GetTimestamp() string {
	return value_objects.IsoFormat(time.Now().UTC())
}

// metaResponseFormatter is the flavour of the other controllers: the third
// argument of create_success_response is metadata.
type metaResponseFormatter struct{ f *utils.MCPResponseFormatter }

func (a metaResponseFormatter) CreateSuccessResponse(operation string, data any, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.f.CreateSuccessResponse(operation, toOrderedData(data), metadata, nil, nil, nil)
}

func (a metaResponseFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.f.CreateErrorResponse(operation, errorMessage, errorCode, metadata)
}

func (a metaResponseFormatter) FormatContextResponse(facadeResponse *entities.OrderedMap[any], operation string, standardizeFieldNames bool) *entities.OrderedMap[any] {
	return a.f.FormatContextResponse(facadeResponse, operation, standardizeFieldNames, nil, nil)
}

// taskMCPFacade adapts *facades.TaskApplicationFacade to the handlers.TaskFacade
// surface the task MCP handlers declare (pointer request DTOs, (result, error)
// GetTask, optional completion summary).
type taskMCPFacade struct {
	f *facades.TaskApplicationFacade
}

func (a taskMCPFacade) CreateTask(ctx context.Context, request *dtostask.CreateTaskRequest) *entities.OrderedMap[any] {
	return a.f.CreateTask(ctx, *request)
}

func (a taskMCPFacade) UpdateTask(ctx context.Context, request *dtostask.UpdateTaskRequest) *entities.OrderedMap[any] {
	return a.f.UpdateTask(ctx, *request)
}

func (a taskMCPFacade) GetTask(ctx context.Context, taskID string, includeContext bool) (*entities.OrderedMap[any], error) {
	return a.f.GetTask(ctx, taskID, includeContext, true), nil
}

// ResumeBrief is handlers.TaskFacade.ResumeBrief: the brief is built in the application layer and
// this adapter only delegates - the interface layer adds no shape of its own to it.
func (a taskMCPFacade) ResumeBrief(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	return a.f.ResumeBrief(ctx, taskID)
}

func (a taskMCPFacade) DeleteTask(ctx context.Context, taskID string, userID *string) *entities.OrderedMap[any] {
	return a.f.DeleteTask(ctx, taskID, userID)
}

func (a taskMCPFacade) CompleteTask(ctx context.Context, taskID, completionSummary string, testingNotes, userID *string) *entities.OrderedMap[any] {
	return a.f.CompleteTask(ctx, taskID, &completionSummary, testingNotes, userID)
}

func (a taskMCPFacade) AddDependency(ctx context.Context, taskID, dependencyID string) *entities.OrderedMap[any] {
	return a.f.AddDependency(ctx, taskID, dependencyID)
}

func (a taskMCPFacade) RemoveDependency(ctx context.Context, taskID, dependencyID string) *entities.OrderedMap[any] {
	return a.f.RemoveDependency(ctx, taskID, dependencyID)
}

// ListTasks is handlers.TaskSearchFacade.ListTasks (Python search_handler passes include_dependencies=False, minimal=True).
func (a taskMCPFacade) ListTasks(ctx context.Context, request *dtostask.ListTasksRequest) *entities.OrderedMap[any] {
	return a.f.ListTasks(ctx, *request, false, true, false)
}

func (a taskMCPFacade) SearchTasks(ctx context.Context, request *dtostask.SearchTasksRequest) *entities.OrderedMap[any] {
	return a.f.SearchTasks(ctx, *request, false)
}

func (a taskMCPFacade) CountTasks(ctx context.Context, filters map[string]any) *entities.OrderedMap[any] {
	return a.f.CountTasks(ctx, filters)
}

func (a taskMCPFacade) TaskRepository() repositories.TaskRepository {
	repo, _ := a.f.TaskRepository().(repositories.TaskRepository)
	return repo
}

// taskOperationAdapter exposes the task OperationFactory (kwargs map, handler
// facade) through the controller's TaskOperationFactory (explicit user/task ids).
type taskOperationAdapter struct {
	factory *taskfactories.OperationFactory
}

func (a taskOperationAdapter) HandleOperation(ctx context.Context, operation string, facade *facades.TaskApplicationFacade, userID, taskID *string, kwargs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	args := map[string]any{}
	if kwargs != nil {
		for _, k := range kwargs.Keys() {
			v, _ := kwargs.Get(k)
			args[k] = v
		}
	}
	args["user_id"], args["task_id"] = derefOrNil(userID), derefOrNil(taskID)
	return a.factory.HandleOperation(ctx, operation, taskMCPFacade{facade}, args)
}

func derefOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// kwargs helpers: Python passes **kwargs; the Go handlers take typed parameters.

func kwOptString(kw *entities.OrderedMap[any], key string) *string {
	if kw == nil {
		return nil
	}
	v := kw.GetAny(key)
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}

func kwString(kw *entities.OrderedMap[any], key string) string {
	if s := kwOptString(kw, key); s != nil {
		return *s
	}
	return ""
}

func kwOptInt(kw *entities.OrderedMap[any], key string) *int {
	if kw == nil {
		return nil
	}
	switch v := kw.GetAny(key).(type) {
	case int:
		return &v
	case int64:
		n := int(v)
		return &n
	case float64:
		n := int(v)
		return &n
	case string:
		if n, err := strconv.Atoi(strings.TrimSpace(v)); err == nil {
			return &n
		}
	}
	return nil
}

func kwStringList(kw *entities.OrderedMap[any], key string) []string {
	if kw == nil {
		return nil
	}
	switch v := kw.GetAny(key).(type) {
	case []string:
		return v
	case []any:
		out := make([]string, len(v))
		for i, x := range v {
			out[i] = value_objects.PyStr(x)
		}
		return out
	}
	return nil
}

func orderedList(v any) []*entities.OrderedMap[any] {
	switch l := v.(type) {
	case []*entities.OrderedMap[any]:
		return l
	case []any:
		out := make([]*entities.OrderedMap[any], 0, len(l))
		for _, x := range l {
			out = append(out, toOrderedData(x))
		}
		return out
	}
	return nil
}

// subtaskCRUDAdapter exposes handlers.SubtaskCRUDHandler (typed parameters)
// through factories.SubtaskCRUDHandler (kwargs).
type subtaskCRUDAdapter struct {
	h *subtaskhandlers.SubtaskCRUDHandler
}

func (a subtaskCRUDAdapter) CreateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kw *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.h.CreateSubtask(ctx, facade, kwString(kw, "task_id"), kwString(kw, "title"),
		kwOptString(kw, "description"), kwOptString(kw, "status"), kwOptString(kw, "priority"),
		kwStringList(kw, "assignees"), kwOptInt(kw, "progress_percentage"), kwOptString(kw, "progress_notes"), kwOptString(kw, "user_id"))
}

func (a subtaskCRUDAdapter) UpdateSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kw *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.h.UpdateSubtask(ctx, facade, kwString(kw, "task_id"), kwString(kw, "subtask_id"),
		kwOptString(kw, "title"), kwOptString(kw, "description"), kwOptString(kw, "status"), kwOptString(kw, "priority"),
		kwStringList(kw, "assignees"), kwOptInt(kw, "progress_percentage"), kwOptString(kw, "progress_notes"))
}

func (a subtaskCRUDAdapter) DeleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kw *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.h.DeleteSubtask(ctx, facade, kwString(kw, "task_id"), kwString(kw, "subtask_id"), kwOptString(kw, "progress_notes"))
}

func (a subtaskCRUDAdapter) GetSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kw *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.h.GetSubtask(ctx, facade, kwString(kw, "task_id"), kwString(kw, "subtask_id"))
}

func (a subtaskCRUDAdapter) ListSubtasks(ctx context.Context, facade *facades.SubtaskApplicationFacade, kw *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.h.ListSubtasks(ctx, facade, kwString(kw, "task_id"), kwOptString(kw, "status"), kwOptString(kw, "priority"),
		kwOptInt(kw, "limit"), kwOptInt(kw, "offset"))
}

func (a subtaskCRUDAdapter) CompleteSubtask(ctx context.Context, facade *facades.SubtaskApplicationFacade, kw *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	extras := &subtaskhandlers.CompletionExtras{
		TestingNotes: kwOptString(kw, "testing_notes"), InsightsFound: kwOptString(kw, "insights_found"),
		ChallengesOvercome: kwOptString(kw, "challenges_overcome"), SkillsLearned: kwOptString(kw, "skills_learned"),
		NextRecommendations: kwOptString(kw, "next_recommendations"), Deliverables: kwOptString(kw, "deliverables"),
		CompletionQuality: kwOptString(kw, "completion_quality"), ImpactOnParent: kwOptString(kw, "impact_on_parent"),
	}
	return a.h.CompleteSubtask(ctx, facade, kwString(kw, "task_id"), kwString(kw, "subtask_id"),
		kwOptString(kw, "completion_notes"), kwOptString(kw, "completion_summary"), extras)
}

// subtaskProgressAdapter exposes handlers.ProgressHandler (typed subtask lists)
// through factories.ProgressHandler (any).
type subtaskProgressAdapter struct {
	h *subtaskhandlers.ProgressHandler
}

func (a subtaskProgressAdapter) GetProgressSummary(taskID string, subtasks any) any {
	return a.h.GetProgressSummary(taskID, orderedList(subtasks))
}

func (a subtaskProgressAdapter) CalculateTaskProgress(taskID string, subtasks any) any {
	return a.h.CalculateTaskProgress(taskID, orderedList(subtasks))
}

func strOrEmpty(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

// projectCRUDAdapter exposes handlers.ProjectCRUDHandler (string ids) through
// factories.ProjectCRUDHandler (optional ids; a missing id is Python's falsy None).
type projectCRUDAdapter struct {
	h *projecthandlers.ProjectCRUDHandler
}

func (a projectCRUDAdapter) CreateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, name string, description, userID *string) *entities.OrderedMap[any] {
	return a.h.CreateProject(ctx, facade, name, description, userID)
}

func (a projectCRUDAdapter) GetProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, name *string) *entities.OrderedMap[any] {
	return a.h.GetProject(ctx, facade, projectID, name)
}

func (a projectCRUDAdapter) ListProjects(ctx context.Context, facade *facades.ProjectApplicationFacade) *entities.OrderedMap[any] {
	return a.h.ListProjects(ctx, facade)
}

func (a projectCRUDAdapter) UpdateProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, name, description *string) *entities.OrderedMap[any] {
	return a.h.UpdateProject(ctx, facade, strOrEmpty(projectID), name, description)
}

func (a projectCRUDAdapter) DeleteProject(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force *bool) *entities.OrderedMap[any] {
	return a.h.DeleteProject(ctx, facade, strOrEmpty(projectID), force)
}

// projectMaintenanceAdapter does the same for the maintenance handler.
type projectMaintenanceAdapter struct {
	h *projecthandlers.ProjectMaintenanceHandler
}

func (a projectMaintenanceAdapter) ProjectHealthCheck(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID, userID *string) *entities.OrderedMap[any] {
	return a.h.ProjectHealthCheck(ctx, facade, strOrEmpty(projectID), userID)
}

func (a projectMaintenanceAdapter) CleanupObsolete(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force bool, userID *string) *entities.OrderedMap[any] {
	return a.h.CleanupObsolete(ctx, facade, strOrEmpty(projectID), &force, userID)
}

func (a projectMaintenanceAdapter) ValidateIntegrity(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force bool, userID *string) *entities.OrderedMap[any] {
	return a.h.ValidateIntegrity(ctx, facade, strOrEmpty(projectID), &force, userID)
}

func (a projectMaintenanceAdapter) RebalanceAgents(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID *string, force bool, userID *string) *entities.OrderedMap[any] {
	return a.h.RebalanceAgents(ctx, facade, strOrEmpty(projectID), &force, userID)
}

// projectOperationAdapter exposes factories.ProjectOperationFactory through the
// controller's ProjectOperationFactory view (explicit user id, raw handlers).
type projectOperationAdapter struct {
	factory     *projectfactories.ProjectOperationFactory
	crud        *projecthandlers.ProjectCRUDHandler
	maintenance *projecthandlers.ProjectMaintenanceHandler
}

func (a projectOperationAdapter) HandleOperation(ctx context.Context, operation string, facade *facades.ProjectApplicationFacade, userID *string, p projectctl.ProjectOperationParams) *entities.OrderedMap[any] {
	return a.factory.HandleOperation(ctx, operation, facade, projectfactories.ProjectOperationParams{
		ProjectID: p.ProjectID, Name: p.Name, Description: p.Description, UserID: userID, Force: p.Force})
}

func (a projectOperationAdapter) CRUDHandler() projectctl.ProjectCRUDHandler { return a.crud }

func (a projectOperationAdapter) MaintenanceHandler() projectctl.ProjectMaintenanceHandler {
	return a.maintenance
}

// wireAuthHooks binds the controllers' request-context hooks (Python reads the
// request-scoped contextvars) to the auth middleware's ctx accessors.
func wireAuthHooks() {
	userID := func(ctx context.Context) *string { return authmw.GetCurrentUserID(ctx) }
	anyUserID := func(ctx context.Context) any {
		if id := userID(ctx); id != nil {
			return *id
		}
		return nil
	}
	branchctl.GetCurrentUserIDHook = anyUserID
	projectctl.GetAuthenticatedUserID = auth_helper.GetAuthenticatedUserID
	projectctl.GetCurrentAuthInfo = authmw.GetCurrentAuthInfo
	authservices.RequestContextUserIDProvider = userID
}

// hintEnhancerAdapter adapts WorkflowHintEnhancer.EnhanceResponse(response, ctx)
// to the task controller's (response, action, ctx) view; Python passes the
// kwargs as the enhancer's operation context and ignores the action.
type hintEnhancerAdapter struct {
	*workflow_hint_enhancer.WorkflowHintEnhancer
}

func (a hintEnhancerAdapter) EnhanceResponse(response *entities.OrderedMap[any], _ string, ctx *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return a.WorkflowHintEnhancer.EnhanceResponse(response, ctx)
}

type branchGuidanceAdapter struct {
	g *wfbranch.GitBranchWorkflowGuidance
}

func (a branchGuidanceAdapter) GenerateGuidance(action string, ctx *entities.OrderedMap[any]) any {
	return a.g.GenerateGuidance(action, ctx)
}

// wireWorkflowGuidance sets the controllers' workflow-guidance factories (the
// Python *WorkflowFactory.create() calls); it must run before the controllers
// are constructed.
func wireWorkflowGuidance() {
	subtaskctl.DefaultWorkflowGuidanceFactory = func() subtaskctl.SubtaskWorkflowGuidance { return &wfsubtask.SubtaskWorkflowGuidance{} }
	branchctl.DefaultWorkflowGuidanceFactory = func() branchctl.WorkflowGuidance {
		return branchGuidanceAdapter{wfbranch.GitBranchWorkflowFactory{}.Create()}
	}
}
