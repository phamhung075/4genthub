package types

// API Response Wrappers (Python types/responses.py).
// Standard response formats matching frontend api.types.ts.

import "agenthub/fastmcp/task_management/domain/entities"

// ApiResponse is the base API response (Python success has no default).
type ApiResponse struct {
	Success   bool
	Data      any
	Error     *string
	Message   *string
	Timestamp *string
}

func (r *ApiResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"data", r.Data,
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// TaskResponse matches the frontend TaskResponse interface.
type TaskResponse struct {
	Success   bool
	Task      *TaskDTO
	Error     *string
	Message   *string
	Timestamp *string
}

// NewTaskResponse applies the pydantic default success=True.
func NewTaskResponse() *TaskResponse { return &TaskResponse{Success: true} }

func (r *TaskResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"task", dtoModelOrNil(r.Task),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// TasksResponse matches the frontend TasksResponse interface.
type TasksResponse struct {
	Success   bool
	Tasks     []*TaskDTO
	Total     *int
	Page      *int
	Limit     *int
	Error     *string
	Message   *string
	Timestamp *string
}

func NewTasksResponse() *TasksResponse { return &TasksResponse{Success: true} }

func (r *TasksResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"tasks", dtoModelList(r.Tasks),
		"total", dtoInt(r.Total),
		"page", dtoInt(r.Page),
		"limit", dtoInt(r.Limit),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// TaskSummariesResponse is the lightweight task-list response.
type TaskSummariesResponse struct {
	Success   bool
	Tasks     []*TaskSummaryDTO
	Total     *int
	Page      *int
	Limit     *int
	Error     *string
	Message   *string
	Timestamp *string
}

func NewTaskSummariesResponse() *TaskSummariesResponse { return &TaskSummariesResponse{Success: true} }

func (r *TaskSummariesResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"tasks", dtoModelList(r.Tasks),
		"total", dtoInt(r.Total),
		"page", dtoInt(r.Page),
		"limit", dtoInt(r.Limit),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// SubtaskResponse matches the frontend SubtaskResponse interface.
type SubtaskResponse struct {
	Success   bool
	Subtask   *SubtaskDTO
	Error     *string
	Message   *string
	Timestamp *string
}

func NewSubtaskResponse() *SubtaskResponse { return &SubtaskResponse{Success: true} }

func (r *SubtaskResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"subtask", dtoModelOrNil(r.Subtask),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// SubtasksResponse matches the frontend SubtasksResponse interface.
type SubtasksResponse struct {
	Success   bool
	Subtasks  []*SubtaskDTO
	Total     *int
	Error     *string
	Message   *string
	Timestamp *string
}

func NewSubtasksResponse() *SubtasksResponse { return &SubtasksResponse{Success: true} }

func (r *SubtasksResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"subtasks", dtoModelList(r.Subtasks),
		"total", dtoInt(r.Total),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// ProjectResponse matches the frontend ProjectResponse interface.
type ProjectResponse struct {
	Success   bool
	Project   *ProjectDTO
	Error     *string
	Message   *string
	Timestamp *string
}

func NewProjectResponse() *ProjectResponse { return &ProjectResponse{Success: true} }

func (r *ProjectResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"project", dtoModelOrNil(r.Project),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// ProjectsResponse matches the frontend ProjectsResponse interface.
type ProjectsResponse struct {
	Success   bool
	Projects  []*ProjectDTO
	Total     *int
	Error     *string
	Message   *string
	Timestamp *string
}

func NewProjectsResponse() *ProjectsResponse { return &ProjectsResponse{Success: true} }

func (r *ProjectsResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"projects", dtoModelList(r.Projects),
		"total", dtoInt(r.Total),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// BranchResponse matches the frontend BranchResponse interface.
type BranchResponse struct {
	Success   bool
	Branch    *BranchDTO
	Error     *string
	Message   *string
	Timestamp *string
}

func NewBranchResponse() *BranchResponse { return &BranchResponse{Success: true} }

func (r *BranchResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"branch", dtoModelOrNil(r.Branch),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// BranchesResponse matches the frontend BranchesResponse interface.
type BranchesResponse struct {
	Success   bool
	Branches  []*BranchDTO
	Total     *int
	Error     *string
	Message   *string
	Timestamp *string
}

func NewBranchesResponse() *BranchesResponse { return &BranchesResponse{Success: true} }

func (r *BranchesResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"branches", dtoModelList(r.Branches),
		"total", dtoInt(r.Total),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// ContextResponse matches the frontend ContextResponse interface.
type ContextResponse struct {
	Success   bool
	Context   any
	Level     *string
	Inherited any
	Error     *string
	Message   *string
	Timestamp *string
}

func NewContextResponse() *ContextResponse { return &ContextResponse{Success: true} }

func (r *ContextResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"context", r.Context,
		"level", dtoOpt(r.Level),
		"inherited", r.Inherited,
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// DeleteResponse matches the frontend DeleteResponse interface.
type DeleteResponse struct {
	Success   bool
	Deleted   *bool
	ID        *string
	Error     *string
	Message   *string
	Timestamp *string
}

func NewDeleteResponse() *DeleteResponse { return &DeleteResponse{Success: true} }

func (r *DeleteResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"deleted", dtoBool(r.Deleted),
		"id", dtoOpt(r.ID),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// HealthResponse matches the frontend HealthResponse interface.
type HealthResponse struct {
	Success   bool
	Status    string
	Version   *string
	Timestamp string
	Error     *string
	Message   *string
}

func NewHealthResponse() *HealthResponse { return &HealthResponse{Success: true} }

func (r *HealthResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"status", r.Status,
		"version", dtoOpt(r.Version),
		"timestamp", r.Timestamp,
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
	)
}

// AgentsResponse matches the frontend AgentsResponse interface.
type AgentsResponse struct {
	Success   bool
	Agents    []any
	Total     *int
	Error     *string
	Message   *string
	Timestamp *string
}

func NewAgentsResponse() *AgentsResponse { return &AgentsResponse{Success: true} }

func (r *AgentsResponse) ModelDump() *entities.OrderedMap[any] {
	agents := any(nil)
	if r.Agents != nil {
		agents = r.Agents
	}
	return dtoMap(
		"success", r.Success,
		"agents", agents,
		"total", dtoInt(r.Total),
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}

// CountResponse is the filtered-count response.
type CountResponse struct {
	Success   bool
	Count     *int
	Filters   any
	Error     *string
	Message   *string
	Timestamp *string
}

func NewCountResponse() *CountResponse { return &CountResponse{Success: true} }

func (r *CountResponse) ModelDump() *entities.OrderedMap[any] {
	return dtoMap(
		"success", r.Success,
		"count", dtoInt(r.Count),
		"filters", r.Filters,
		"error", dtoOpt(r.Error),
		"message", dtoOpt(r.Message),
		"timestamp", dtoOpt(r.Timestamp),
	)
}
