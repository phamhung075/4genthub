package handlers

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/types"
)

// TaskSearchHandler mirrors search_handler.TaskSearchHandler.
type TaskSearchHandler struct {
	facadeService TaskFacadeService
}

// NewTaskSearchHandler builds the handler.
func NewTaskSearchHandler(facadeService TaskFacadeService) *TaskSearchHandler {
	return &TaskSearchHandler{facadeService: facadeService}
}

// thDict reports whether v is a Python dict (OrderedMap or map[string]any).
func thDict(v any) (*entities.OrderedMap[any], bool) {
	switch x := v.(type) {
	case *entities.OrderedMap[any]:
		return x, true
	case map[string]any:
		m := entities.NewOrderedMap[any]()
		for k, val := range x {
			m.Set(k, val)
		}
		return m, true
	}
	return nil, false
}

// thInt mirrors Python int() over a JSON number.
func thInt(v any) int {
	f, ok := value_objects.PyFloat(v)
	if !ok {
		return 0
	}
	return int(f)
}

// thFuncService returns the injected facade service.
func (h *TaskSearchHandler) thFuncService() TaskFacadeService { return h.facadeService }

// CountTasks mirrors TaskSearchHandler.count_tasks.
func (h *TaskSearchHandler) CountTasks(ctx context.Context, filters *entities.OrderedMap[any], userID string) (resp *types.CountResponse) {
	resp = &types.CountResponse{Success: false, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Error = thPanicStr(r)
			resp.Message = thMsg("Failed to count tasks")
			resp.Timestamp = thNow()
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(strPtr("default_project"), nil, &userID)
	if err != nil {
		return thCountFailure(err.Error())
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return thCountFailure("Failed to count tasks")
	}
	if filters == nil {
		filters = entities.NewOrderedMap[any]()
	}
	filters.Set("user_id", userID)
	mapFilters := map[string]any{}
	for _, k := range filters.Keys() {
		v, _ := filters.Get(k)
		mapFilters[k] = v
	}
	result := facade.CountTasks(ctx, mapFilters)
	if m, isDict := thDict(result); isDict {
		if _, has := m.Get("success"); has {
			if thSuccess(m) {
				count := thInt(thOmGetDefault(m, "count", 0))
				return &types.CountResponse{Success: true, Count: &count, Filters: filters, Timestamp: thNow()}
			}
			errorMsg := value_objects.PyStr(thOmGetDefault(m, "error", "Failed to count tasks"))
			return &types.CountResponse{Success: false, Error: &errorMsg, Message: &errorMsg, Timestamp: thNow()}
		}
	}
	count := thInt(result)
	return &types.CountResponse{Success: true, Count: &count, Filters: filters, Timestamp: thNow()}
}

// ListTasksSummary mirrors TaskSearchHandler.list_tasks_summary.
func (h *TaskSearchHandler) ListTasksSummary(ctx context.Context, filters *entities.OrderedMap[any], offset, limit int, userID string) (resp *types.TaskSummariesResponse) {
	resp = &types.TaskSummariesResponse{Success: false, Tasks: []*types.TaskSummaryDTO{}, Timestamp: thNow()}
	defer func() {
		if r := recover(); r != nil {
			resp.Success = false
			resp.Tasks = []*types.TaskSummaryDTO{}
			resp.Error = thPanicStr(r)
			resp.Message = thMsg("Failed to list task summaries")
			resp.Timestamp = thNow()
		}
	}()
	raw, err := h.facadeService.GetTaskFacade(strPtr("default_project"), nil, &userID)
	if err != nil {
		return thSummaryFailure(err.Error())
	}
	facade, ok := raw.(TaskHandlerFacade)
	if !ok {
		return thSummaryFailure("Failed to list task summaries")
	}
	if filters == nil {
		filters = entities.NewOrderedMap[any]()
	}
	filters.Set("user_id", userID)
	mapFilters := map[string]any{}
	for _, k := range filters.Keys() {
		v, _ := filters.Get(k)
		mapFilters[k] = v
	}
	result := facade.ListTasksSummary(ctx, mapFilters, offset, limit)
	if thSuccess(result) {
		tasks := thAnySlice(thOmGetDefault(result, "tasks", []any{}))
		dtos := make([]*types.TaskSummaryDTO, 0, len(tasks))
		for _, t := range tasks {
			dto, derr := types.TaskSummaryToDTO(t)
			if derr != nil {
				return thSummaryFailure(derr.Error())
			}
			dtos = append(dtos, dto)
		}
		total := thInt(thOmGetDefault(result, "total", 0))
		page := 0
		if limit > 0 {
			page = offset / limit
		}
		return &types.TaskSummariesResponse{Success: true, Tasks: dtos, Total: &total, Page: &page, Limit: &limit, Timestamp: thNow()}
	}
	errorMsg := value_objects.PyStr(thOmGetDefault(result, "error", "Failed to list task summaries"))
	return &types.TaskSummariesResponse{Success: false, Tasks: []*types.TaskSummaryDTO{}, Error: &errorMsg, Message: &errorMsg, Timestamp: thNow()}
}

func strPtr(s string) *string { return &s }

func thCountFailure(msg string) *types.CountResponse {
	if msg == "" {
		msg = "Failed to count tasks"
	}
	return &types.CountResponse{Success: false, Error: &msg, Message: &msg, Timestamp: thNow()}
}

func thSummaryFailure(msg string) *types.TaskSummariesResponse {
	if msg == "" {
		msg = "Failed to list task summaries"
	}
	return &types.TaskSummariesResponse{Success: false, Tasks: []*types.TaskSummaryDTO{}, Error: &msg, Message: &msg, Timestamp: thNow()}
}
