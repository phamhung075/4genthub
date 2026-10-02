// subtask_api_controller.go ports
// task_management/interface/api_controllers/subtask_api_controller.SubtaskAPIController.
package api_controllers

import (
	"context"
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/types"
)

// SubtaskFacadeProvider is the consumer-side view of FacadeService used by the
// subtask controller. Signatures match services.FacadeService exactly so the
// real facade service satisfies it.
type SubtaskFacadeProvider interface {
	GetTaskFacade(projectID, gitBranchID, userID *string) (any, error)
	GetSubtaskFacade(projectID, gitBranchID, userID, taskID *string) (any, error)
}

// SubtaskManageFacade is the facade surface used by the controller.
type SubtaskManageFacade interface {
	HandleManageSubtask(ctx context.Context, action, taskID string,
		subtaskData *entities.OrderedMap[any], subtaskID *string, suppressBroadcast bool,
		projectID, gitBranchName, userID *string) (*entities.OrderedMap[any], error)
}

// SubtaskAPIController mirrors SubtaskAPIController.
type SubtaskAPIController struct {
	facadeService SubtaskFacadeProvider
	subtaskRepos  SubtaskRepositoryProvider
}

// SubtaskRepositoryProvider builds the per-user subtask repository that Python obtains from
// SubtaskRepositoryFactory().create_orm_subtask_repository(user_id).
type SubtaskRepositoryProvider func(userID *string) (repositories.SubtaskRepository, error)

// WithSubtaskRepositories injects the repository provider (Python reaches the global session).
func (c *SubtaskAPIController) WithSubtaskRepositories(p SubtaskRepositoryProvider) *SubtaskAPIController {
	c.subtaskRepos = p
	return c
}

// NewSubtaskAPIController builds the controller. Python uses
// FacadeService.get_instance(); the Go service is injected.
func NewSubtaskAPIController(facadeService SubtaskFacadeProvider) *SubtaskAPIController {
	return &SubtaskAPIController{facadeService: facadeService}
}

// sacNow is datetime.now(UTC).isoformat().
func sacNow() *string {
	s := value_objects.IsoFormat(time.Now().UTC())
	return &s
}

func sacGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func sacGetDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

func sacSuccess(m *entities.OrderedMap[any]) bool {
	return value_objects.PyTruthy(sacGet(m, "success"))
}

func sacMsg(v any) *string {
	if v == nil {
		return nil
	}
	s := value_objects.PyStr(v)
	return &s
}

func sacPanicStr(r any) *string {
	s := value_objects.PyStr(r)
	return &s
}

func sacAnySlice(v any) []any {
	switch x := v.(type) {
	case []any:
		return x
	case []*entities.OrderedMap[any]:
		out := make([]any, 0, len(x))
		for _, e := range x {
			out = append(out, e)
		}
		return out
	}
	return nil
}

// sacCopy sets every key of src on dst preserving iteration order.
func sacCopy(dst, src *entities.OrderedMap[any]) {
	if src == nil {
		return
	}
	for _, k := range src.Keys() {
		v, _ := src.Get(k)
		dst.Set(k, v)
	}
}

// _get_task_id_from_subtask mirrors the Python helper, including its broad
// except returning None.
func (c *SubtaskAPIController) getTaskIDFromSubtask(ctx context.Context, subtaskID, userID string) (taskID string, found bool) {
	defer func() {
		if r := recover(); r != nil {
			taskID, found = "", false
		}
	}()
	repo, err := c.subtaskRepos(&userID)
	if err != nil {
		return "", false
	}
	subtask, err := repo.FindByID(ctx, subtaskID)
	if err != nil || subtask == nil {
		return "", false
	}
	if subtask.ParentTaskID == nil {
		return "", false
	}
	return subtask.ParentTaskID.String(), true
}

func (c *SubtaskAPIController) subtaskFacade(ctx context.Context, gitBranchID, userID string, taskID *string) (SubtaskManageFacade, error) {
	raw, err := c.facadeService.GetSubtaskFacade(nil, &gitBranchID, &userID, taskID)
	if err != nil {
		return nil, err
	}
	facade, _ := raw.(SubtaskManageFacade)
	return facade, nil
}

// CreateSubtask mirrors create_subtask(task_id, title, description, user_id, session).
func (c *SubtaskAPIController) CreateSubtask(ctx context.Context, taskID, title string, description *string, userID string) (resp *types.SubtaskResponse) {
	resp = &types.SubtaskResponse{Success: false, Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Subtask = nil
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to create subtask")
			resp.Timestamp = sacNow()
		}
	}()
	tempRaw, err := c.facadeService.GetTaskFacade(nil, nil, &userID)
	if err != nil {
		return sacCreateFailure(err.Error())
	}
	tempFacade, ok := tempRaw.(TaskQueryFacade)
	if !ok {
		return sacCreateFailure("Failed to create subtask")
	}
	parentTask := tempFacade.GetTask(ctx, taskID)
	if parentTask == nil || sacGet(parentTask, "task") == nil {
		return sacCreateFailure("Parent task " + taskID + " not found")
	}
	parentTaskData, _ := sacGet(parentTask, "task").(*entities.OrderedMap[any])
	parentGitBranchID := value_objects.PyStr(sacGet(parentTaskData, "git_branch_id"))
	if parentGitBranchID == "" {
		return sacCreateFailure("Parent task " + taskID + " missing git_branch_id required for context derivation")
	}
	facade, err := c.subtaskFacade(ctx, parentGitBranchID, userID, nil)
	if err != nil || facade == nil {
		return sacCreateFailure("Failed to create subtask")
	}
	subtaskData := entities.NewOrderedMap[any]()
	subtaskData.Set("task_id", taskID)
	subtaskData.Set("title", title)
	if description != nil {
		subtaskData.Set("description", *description)
	} else {
		subtaskData.Set("description", "")
	}
	subtaskData.Set("status", "todo")
	subtaskData.Set("priority", "medium")

	result, err := facade.HandleManageSubtask(ctx, "create", taskID, subtaskData, nil, false, nil, nil, &userID)
	if err != nil {
		return sacCreateFailure(err.Error())
	}
	subtaskValue := sacGet(result, "subtask")
	dto, derr := types.SubtaskToDTO(types.AttrObject{Dict: subtaskValue})
	if derr != nil {
		return sacCreateFailure(derr.Error())
	}
	return &types.SubtaskResponse{Success: true, Subtask: dto, Message: sacMsg("Subtask created successfully"), Timestamp: sacNow()}
}

// ListSubtasks mirrors list_subtasks(task_id, user_id, session).
func (c *SubtaskAPIController) ListSubtasks(ctx context.Context, taskID, userID string) (resp *types.SubtasksResponse) {
	resp = &types.SubtasksResponse{Success: false, Subtasks: []*types.SubtaskDTO{}, Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Subtasks = []*types.SubtaskDTO{}
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to list subtasks")
			resp.Timestamp = sacNow()
		}
	}()
	gitBranchID, facade, failMsg := c.resolveSubtaskContext(ctx, taskID, userID)
	if failMsg != "" {
		return sacListFailure(failMsg)
	}
	result, err := facade.HandleManageSubtask(ctx, "list", taskID, nil, nil, false, nil, nil, &userID)
	if err != nil {
		return sacListFailure(err.Error())
	}
	_ = gitBranchID
	return c.buildSubtasksResponse(result, "Retrieved %d subtasks", "Failed to list subtasks")
}

// GetSubtask mirrors get_subtask(subtask_id, user_id, session).
func (c *SubtaskAPIController) GetSubtask(ctx context.Context, subtaskID, userID string) (resp *types.SubtaskResponse) {
	resp = &types.SubtaskResponse{Success: false, Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Subtask = nil
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to get subtask")
			resp.Timestamp = sacNow()
		}
	}()
	taskID, found := c.getTaskIDFromSubtask(ctx, subtaskID, userID)
	if !found {
		return sacSubtaskNotFound("Subtask not found", "Subtask not found or access denied")
	}
	_, facade, failMsg := c.resolveSubtaskContext(ctx, taskID, userID)
	if failMsg != "" {
		return sacGetFailure(failMsg)
	}
	result, err := facade.HandleManageSubtask(ctx, "get", taskID, nil, &subtaskID, false, nil, nil, &userID)
	if err != nil {
		return sacGetFailure(err.Error())
	}
	if !sacSuccess(result) {
		return sacSubtaskNotFound("Subtask not found", "Subtask not found or access denied")
	}
	dto, derr := types.SubtaskToDTO(types.AttrObject{Dict: sacGet(result, "subtask")})
	if derr != nil {
		return sacGetFailure(derr.Error())
	}
	return &types.SubtaskResponse{Success: true, Subtask: dto, Timestamp: sacNow()}
}

// UpdateSubtask mirrors update_subtask(subtask_id, update_data, user_id, session).
func (c *SubtaskAPIController) UpdateSubtask(ctx context.Context, subtaskID string, updateData *entities.OrderedMap[any], userID string) (resp *types.SubtaskResponse) {
	resp = &types.SubtaskResponse{Success: false, Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Subtask = nil
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to update subtask")
			resp.Timestamp = sacNow()
		}
	}()
	taskID, found := c.getTaskIDFromSubtask(ctx, subtaskID, userID)
	if !found {
		return sacSubtaskNotFound("Subtask not found", "Subtask not found or access denied")
	}
	_, facade, failMsg := c.resolveSubtaskContext(ctx, taskID, userID)
	if failMsg != "" {
		return sacUpdateFailure(failMsg)
	}
	updateDataWithID := entities.NewOrderedMap[any]()
	updateDataWithID.Set("subtask_id", subtaskID)
	sacCopy(updateDataWithID, updateData)
	result, err := facade.HandleManageSubtask(ctx, "update", taskID, updateDataWithID, &subtaskID, false, nil, nil, &userID)
	if err != nil {
		return sacUpdateFailure(err.Error())
	}
	if !sacSuccess(result) {
		return sacSubtaskNotFound("Subtask not found", "Subtask not found or access denied")
	}
	dto, derr := types.SubtaskToDTO(types.AttrObject{Dict: sacGet(result, "subtask")})
	if derr != nil {
		return sacUpdateFailure(derr.Error())
	}
	return &types.SubtaskResponse{Success: true, Subtask: dto, Message: sacMsg("Subtask updated successfully"), Timestamp: sacNow()}
}

// DeleteSubtask mirrors delete_subtask(subtask_id, user_id, session).
func (c *SubtaskAPIController) DeleteSubtask(ctx context.Context, subtaskID, userID string) (resp *types.DeleteResponse) {
	resp = &types.DeleteResponse{Success: false, Deleted: boolPtr(false), Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Deleted = boolPtr(false)
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to delete subtask")
			resp.Timestamp = sacNow()
		}
	}()
	taskID, found := c.getTaskIDFromSubtask(ctx, subtaskID, userID)
	if !found {
		return sacDeleteNotFound()
	}
	_, facade, failMsg := c.resolveSubtaskContext(ctx, taskID, userID)
	if failMsg != "" {
		return sacDeleteFailure(failMsg)
	}
	result, err := facade.HandleManageSubtask(ctx, "delete", taskID, nil, &subtaskID, false, nil, nil, &userID)
	if err != nil {
		return sacDeleteFailure(err.Error())
	}
	if !sacSuccess(result) {
		return sacDeleteNotFound()
	}
	id := subtaskID
	return &types.DeleteResponse{Success: true, Deleted: boolPtr(true), ID: &id, Message: sacMsg("Subtask deleted successfully"), Timestamp: sacNow()}
}

// CompleteSubtask mirrors complete_subtask(subtask_id, completion_summary, user_id, session).
func (c *SubtaskAPIController) CompleteSubtask(ctx context.Context, subtaskID, completionSummary, userID string) (resp *types.SubtaskResponse) {
	resp = &types.SubtaskResponse{Success: false, Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Subtask = nil
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to complete subtask")
			resp.Timestamp = sacNow()
		}
	}()
	taskID, found := c.getTaskIDFromSubtask(ctx, subtaskID, userID)
	if !found {
		return sacSubtaskNotFound("Subtask not found", "Subtask not found or access denied")
	}
	_, facade, failMsg := c.resolveSubtaskContext(ctx, taskID, userID)
	if failMsg != "" {
		return sacCompleteFailure(failMsg)
	}
	completionData := entities.NewOrderedMap[any]()
	completionData.Set("subtask_id", subtaskID)
	completionData.Set("completion_summary", completionSummary)
	result, err := facade.HandleManageSubtask(ctx, "complete", taskID, completionData, &subtaskID, false, nil, nil, &userID)
	if err != nil {
		return sacCompleteFailure(err.Error())
	}
	if !sacSuccess(result) {
		return sacSubtaskNotFound("Subtask not found", "Subtask not found or access denied")
	}
	dto, derr := types.SubtaskToDTO(types.AttrObject{Dict: sacGet(result, "subtask")})
	if derr != nil {
		return sacCompleteFailure(derr.Error())
	}
	return &types.SubtaskResponse{Success: true, Subtask: dto, Message: sacMsg("Subtask completed successfully"), Timestamp: sacNow()}
}

// ListSubtasksSummary mirrors list_subtasks_summary(parent_task_id, include_counts, user_id, session).
func (c *SubtaskAPIController) ListSubtasksSummary(ctx context.Context, parentTaskID string, includeCounts bool, userID string) (resp *types.SubtasksResponse) {
	resp = &types.SubtasksResponse{Success: false, Subtasks: []*types.SubtaskDTO{}, Timestamp: sacNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Subtasks = []*types.SubtaskDTO{}
			resp.Error = sacPanicStr(r)
			resp.Message = sacMsg("Failed to list subtask summaries")
			resp.Timestamp = sacNow()
		}
	}()
	_, facade, failMsg := c.resolveSubtaskContext(ctx, parentTaskID, userID)
	if failMsg != "" {
		return sacSummaryFailure(failMsg)
	}
	result, err := facade.HandleManageSubtask(ctx, "list", parentTaskID, nil, nil, false, nil, nil, &userID)
	if err != nil {
		return sacSummaryFailure(err.Error())
	}
	return c.buildSubtasksResponse(result, "Retrieved %d subtask summaries", "Failed to list subtask summaries")
}

// TaskQueryFacade is the minimal get_task surface used for parent lookup.
type TaskQueryFacade interface {
	GetTask(ctx context.Context, taskID string) *entities.OrderedMap[any]
}

// resolveSubtaskContext mirrors the repeated parent-task lookup and derives the
// git_branch_id, returning the subtask facade. failMsg is non-empty on the
// Python exception path.
func (c *SubtaskAPIController) resolveSubtaskContext(ctx context.Context, taskID, userID string) (string, SubtaskManageFacade, string) {
	tempRaw, err := c.facadeService.GetTaskFacade(nil, nil, &userID)
	if err != nil {
		return "", nil, err.Error()
	}
	tempFacade, ok := tempRaw.(TaskQueryFacade)
	if !ok {
		return "", nil, "Parent task " + taskID + " not found"
	}
	parentTask := tempFacade.GetTask(ctx, taskID)
	if parentTask == nil || sacGet(parentTask, "task") == nil {
		return "", nil, "Parent task " + taskID + " not found"
	}
	parentTaskData, _ := sacGet(parentTask, "task").(*entities.OrderedMap[any])
	gitBranchID := value_objects.PyStr(sacGet(parentTaskData, "git_branch_id"))
	if gitBranchID == "" {
		return "", nil, "Parent task " + taskID + " missing git_branch_id"
	}
	facade, err := c.subtaskFacade(ctx, gitBranchID, userID, nil)
	if err != nil || facade == nil {
		return "", nil, "Failed to resolve subtask facade"
	}
	return gitBranchID, facade, ""
}

// buildSubtasksResponse mirrors the shared list conversion loop.
func (c *SubtaskAPIController) buildSubtasksResponse(result *entities.OrderedMap[any], messageFormat, failMessage string) *types.SubtasksResponse {
	subtasks := sacAnySlice(sacGetDefault(result, "subtasks", []any{}))
	dtos := make([]*types.SubtaskDTO, 0, len(subtasks))
	for _, st := range subtasks {
		summary, err := types.SubtaskSummaryToDTO(types.AttrObject{Dict: st})
		if err != nil {
			return sacSummaryFailure(err.Error())
		}
		// Python builds SubtaskSummaryDTO objects here; the Go SubtasksResponse
		// field is typed []*SubtaskDTO, so carry the summary fields over.
		dtos = append(dtos, &types.SubtaskDTO{
			ID:                 summary.ID,
			TaskID:             summary.TaskID,
			Title:              summary.Title,
			Status:             summary.Status,
			Priority:           summary.Priority,
			Assignees:          summary.Assignees,
			AssigneesCount:     summary.AssigneesCount,
			ProgressPercentage: summary.ProgressPercentage,
			CreatedAt:          summary.CreatedAt,
			UpdatedAt:          summary.UpdatedAt,
		})
	}
	total := len(dtos)
	return &types.SubtasksResponse{
		Success:   true,
		Subtasks:  dtos,
		Total:     &total,
		Message:   sacMsg(fmt.Sprintf(messageFormat, total)),
		Timestamp: sacNow(),
	}
}

func sacSubtaskNotFound(errMsg, message string) *types.SubtaskResponse {
	return &types.SubtaskResponse{Success: false, Subtask: nil, Error: sacMsg(errMsg), Message: sacMsg(message), Timestamp: sacNow()}
}

func sacCreateFailure(msg string) *types.SubtaskResponse {
	return &types.SubtaskResponse{Success: false, Subtask: nil, Error: sacMsg(msg), Message: sacMsg("Failed to create subtask"), Timestamp: sacNow()}
}

func sacGetFailure(msg string) *types.SubtaskResponse {
	return &types.SubtaskResponse{Success: false, Subtask: nil, Error: sacMsg(msg), Message: sacMsg("Failed to get subtask"), Timestamp: sacNow()}
}

func sacUpdateFailure(msg string) *types.SubtaskResponse {
	return &types.SubtaskResponse{Success: false, Subtask: nil, Error: sacMsg(msg), Message: sacMsg("Failed to update subtask"), Timestamp: sacNow()}
}

func sacCompleteFailure(msg string) *types.SubtaskResponse {
	return &types.SubtaskResponse{Success: false, Subtask: nil, Error: sacMsg(msg), Message: sacMsg("Failed to complete subtask"), Timestamp: sacNow()}
}

func sacDeleteFailure(msg string) *types.DeleteResponse {
	return &types.DeleteResponse{Success: false, Deleted: boolPtr(false), Error: sacMsg(msg), Message: sacMsg("Failed to delete subtask"), Timestamp: sacNow()}
}

func sacDeleteNotFound() *types.DeleteResponse {
	return &types.DeleteResponse{Success: false, Deleted: boolPtr(false), Error: sacMsg("Subtask not found"), Message: sacMsg("Subtask not found or access denied"), Timestamp: sacNow()}
}

func sacListFailure(msg string) *types.SubtasksResponse {
	return &types.SubtasksResponse{Success: false, Subtasks: []*types.SubtaskDTO{}, Error: sacMsg(msg), Message: sacMsg("Failed to list subtasks"), Timestamp: sacNow()}
}

func sacSummaryFailure(msg string) *types.SubtasksResponse {
	return &types.SubtasksResponse{Success: false, Subtasks: []*types.SubtaskDTO{}, Error: sacMsg(msg), Message: sacMsg("Failed to list subtask summaries"), Timestamp: sacNow()}
}
