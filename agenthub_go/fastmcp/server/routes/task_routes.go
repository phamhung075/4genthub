// task_routes.go ports server/routes/task_routes.py. The FastAPI APIRouter,
// Depends, redis_cache decorator and Request plumbing have no Go meaning; the
// handler logic, validation branches, response dicts (Python insertion order)
// and HTTP status codes are ported. The TaskAPIController/SubtaskAPIController
// have no Go port yet, so the minimal surfaces used here are declared below.
package routes

import (
	"context"
	"math"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	taskdomain "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskRoutesController is the minimal TaskAPIController surface.
type TaskRoutesController interface {
	CountTasks(ctx context.Context, filters *taskdomain.OrderedMap[any], userID string) (TaskCountResult, error)
	ListTasksSummary(ctx context.Context, filters *taskdomain.OrderedMap[any], offset, limit int, userID string) (TaskListSummaryResult, error)
	GetFullTask(ctx context.Context, taskID, userID string) (FullTaskResult, error)
}

// TaskCountResult mirrors the count response attributes.
type TaskCountResult struct {
	Success bool
	Error   *string
	Count   int
}

// TaskListSummaryResult mirrors model_dump() summaries.
type TaskListSummaryResult struct {
	Success bool
	Error   *string
	Tasks   []*taskdomain.OrderedMap[any]
}

// FullTaskResult mirrors get_full_task's result.
type FullTaskResult struct {
	Success bool
	Error   *string
	Task    *taskdomain.OrderedMap[any]
}

// SubtaskRoutesController is the minimal SubtaskAPIController surface for
// task_routes.list_subtasks_summary.
type SubtaskRoutesController interface {
	ListSubtasksSummary(ctx context.Context, parentTaskID string, includeCounts bool, userID string) (SubtaskSummaryResult, error)
}

// SubtaskSummaryResult mirrors the subtask summary list response.
type SubtaskSummaryResult struct {
	Success  bool
	Error    *string
	Subtasks []*taskdomain.OrderedMap[any]
}

// TaskSummariesRequest mirrors the JSON body of POST /tasks/summaries.
type TaskSummariesRequest struct {
	GitBranchID    *string
	Page           *int
	Limit          *int
	StatusFilter   *string
	PriorityFilter *string
}

// trStr is Python str() over a JSON value (None -> "None").
func trStr(v any) string {
	if v == nil {
		return "None"
	}
	if s, ok := v.(string); ok {
		return s
	}
	if n, ok := v.(float64); ok {
		return value_objects.PyStr(n)
	}
	return value_objects.PyStr(v)
}

// GetTaskSummaries ports get_task_summaries (POST /tasks/summaries).
func GetTaskSummaries(ctx context.Context, req TaskSummariesRequest, currentUser *authdomain.User, taskC TaskRoutesController, ctxC ContextController) (*taskdomain.OrderedMap[any], error) {
	gitBranchID := ""
	if req.GitBranchID != nil {
		gitBranchID = *req.GitBranchID
	}
	page := 1
	if req.Page != nil {
		page = *req.Page
	}
	limit := 20
	if req.Limit != nil {
		limit = *req.Limit
	}
	if gitBranchID == "" {
		return trErrorMap("git_branch_id is required"), nil
	}
	userID := currentUserID(currentUser)
	offset := (page - 1) * limit

	filters := taskdomain.NewOrderedMap[any]()
	filters.Set("git_branch_id", gitBranchID)
	if req.StatusFilter != nil && *req.StatusFilter != "" {
		filters.Set("status", *req.StatusFilter)
	}
	if req.PriorityFilter != nil && *req.PriorityFilter != "" {
		filters.Set("priority", *req.PriorityFilter)
	}

	countResult, err := taskC.CountTasks(ctx, filters, userID)
	if err != nil {
		return nil, err
	}
	totalCount := 0
	if countResult.Success {
		totalCount = countResult.Count
	}

	taskResult, err := taskC.ListTasksSummary(ctx, filters, offset, limit, userID)
	if err != nil {
		return nil, err
	}
	if !taskResult.Success {
		return trErrorMap(pyOrStr(taskResult.Error, "Failed to fetch tasks")), nil
	}

	summaries := []any{}
	for _, taskDict := range taskResult.Tasks {
		if taskDict == nil {
			continue
		}
		contextResult, err := ctxC.GetContext(ctx, "task", trOmStr(taskDict, "id"), false, userID)
		if err != nil {
			return nil, err
		}
		hasContext := contextResult.Success

		summary := taskdomain.NewOrderedMap[any]()
		summary.Set("id", trOmGet(taskDict, "id"))
		summary.Set("title", trOmGet(taskDict, "title"))
		summary.Set("status", trOmGet(taskDict, "status"))
		summary.Set("priority", trOmGet(taskDict, "priority"))
		summary.Set("subtask_count", trOmGetDefault(taskDict, "subtask_count", 0))
		summary.Set("assignees_count", trOmGetDefault(taskDict, "assignees_count", 0))
		summary.Set("has_dependencies", trOmGetDefault(taskDict, "has_dependencies", false))
		summary.Set("has_context", hasContext)
		summary.Set("git_branch_id", trOmGet(taskDict, "git_branch_id"))
		summary.Set("project_id", trOmGet(taskDict, "project_id"))
		summary.Set("created_at", trOmGet(taskDict, "created_at"))
		summary.Set("updated_at", trOmGet(taskDict, "updated_at"))
		summaries = append(summaries, summary)
	}

	response := taskdomain.NewOrderedMap[any]()
	response.Set("tasks", summaries)
	response.Set("total", totalCount)
	response.Set("page", page)
	response.Set("limit", limit)
	response.Set("has_more", (offset+limit) < totalCount)
	return response, nil
}

// GetFullTask ports get_full_task (GET /tasks/{task_id}).
func GetFullTask(ctx context.Context, taskID string, currentUser *authdomain.User, taskC TaskRoutesController) (*taskdomain.OrderedMap[any], error) {
	if taskID == "" {
		return nil, httpErr(400, "task_id is required")
	}
	result, err := taskC.GetFullTask(ctx, taskID, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		if result.Error != nil && strings.Contains(strings.ToLower(*result.Error), "not found") {
			return nil, httpErr(404, "Task "+taskID+" not found")
		}
		return nil, httpErr(500, pyOrStr(result.Error, "Failed to fetch task"))
	}
	if result.Task == nil {
		return nil, httpErr(404, "Task "+taskID+" not found")
	}
	return result.Task, nil
}

// GetTaskRouteSubtaskSummaries ports get_subtask_summaries (POST /subtasks/summaries).
func GetTaskRouteSubtaskSummaries(ctx context.Context, parentTaskID string, includeCounts bool, currentUser *authdomain.User, subC SubtaskRoutesController) (*taskdomain.OrderedMap[any], error) {
	if parentTaskID == "" {
		return nil, httpErr(400, "parent_task_id is required")
	}
	if currentUser == nil {
		return nil, httpErr(401, "Authentication required")
	}
	userID := currentUserID(currentUser)
	result, err := subC.ListSubtasksSummary(ctx, parentTaskID, includeCounts, userID)
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		return nil, httpErr(500, pyOrStr(result.Error, "Failed to fetch subtasks"))
	}
	summaries, statusCounts := trBuildSubtaskSummaries(result.Subtasks, false)
	progress := trBuildProgressSummary(summaries, statusCounts)
	response := taskdomain.NewOrderedMap[any]()
	response.Set("subtasks", summaries)
	response.Set("parent_task_id", parentTaskID)
	response.Set("total_count", len(summaries))
	response.Set("progress_summary", progress)
	return response, nil
}

// GetTaskContextSummary ports get_task_context_summary.
func GetTaskContextSummary(ctx context.Context, taskID string, currentUser *authdomain.User, ctxC ContextController) (*taskdomain.OrderedMap[any], error) {
	if taskID == "" {
		return nil, httpErr(400, "task_id is required")
	}
	result, err := ctxC.GetContext(ctx, "task", taskID, false, currentUserID(currentUser))
	if err != nil {
		return nil, httpErr(500, err.Error())
	}
	if !result.Success {
		out := taskdomain.NewOrderedMap[any]()
		out.Set("has_context", false)
		out.Set("error", result.Error)
		return out, nil
	}
	contextData := result.Body
	out := taskdomain.NewOrderedMap[any]()
	out.Set("has_context", contextData != nil && contextData.Len() > 0)
	size := 0
	var updated any
	if contextData != nil && contextData.Len() > 0 {
		size = len(value_objects.PyStr(contextData))
		updated = trOmGet(contextData, "updated_at")
	}
	out.Set("context_size", size)
	out.Set("last_updated", updated)
	return out, nil
}

// GetPerformanceMetrics ports get_performance_metrics (GET /performance/metrics).
func GetPerformanceMetrics(redisEnabled bool, cacheStats *taskdomain.OrderedMap[any]) *taskdomain.OrderedMap[any] {
	actualMetrics := taskdomain.NewOrderedMap[any]()
	cacheStatus := "disabled"
	hitRate := "N/A"
	if redisEnabled && cacheStats != nil {
		actualMetrics = cacheStats
		cacheStatus = "enabled"
		hitRate = "0.00%"
		if v, ok := cacheStats.Get("hit_rate"); ok {
			hitRate = trStr(v)
		}
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("cache_status", cacheStatus)
	out.Set("cache_metrics", actualMetrics)
	endpoints := taskdomain.NewOrderedMap[any]()
	for _, ep := range [][3]string{{"task_summaries", "45ms", "0.2%"}, {"subtask_summaries", "23ms", "0.1%"}, {"full_task", "30ms", "0.1%"}} {
		m := taskdomain.NewOrderedMap[any]()
		m.Set("average_response_time", ep[1])
		m.Set("cache_hit_rate", hitRate)
		m.Set("error_rate", ep[2])
		endpoints.Set(ep[0], m)
	}
	out.Set("endpoints", endpoints)
	redisCache := taskdomain.NewOrderedMap[any]()
	redisCache.Set("enabled", redisEnabled)
	redisCache.Set("ttl", "300 seconds (5 minutes)")
	redisCache.Set("invalidation", "Automatic on data changes")
	out.Set("redis_cache", redisCache)
	out.Set("recommendations", []any{
		"Redis caching is now implemented with 5-minute TTL",
		"Cache invalidation triggers on task/subtask modifications",
		"Monitor cache hit rate via /api/performance/metrics endpoint",
		"Expected 30-40% improvement for repeat requests",
	})
	return out
}

// --- helpers shared by task_routes and task_user_routes ---

func trErrorMap(msg string) *taskdomain.OrderedMap[any] {
	m := taskdomain.NewOrderedMap[any]()
	m.Set("error", msg)
	return m
}

func trOmGet(m *taskdomain.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func trOmGetDefault(m *taskdomain.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}

func trOmStr(m *taskdomain.OrderedMap[any], key string) string {
	v := trOmGet(m, key)
	if v == nil {
		return "None"
	}
	if s, ok := v.(string); ok {
		return s
	}
	return value_objects.PyStr(v)
}

func trOmLen(m *taskdomain.OrderedMap[any], key string) int {
	v := trOmGet(m, key)
	switch x := v.(type) {
	case []any:
		return len(x)
	case *taskdomain.OrderedMap[any]:
		return x.Len()
	case []string:
		return len(x)
	}
	return 0
}

// trBuildSubtaskSummaries ports the per-subtask summary loop. useZeroDefault
// selects task_user_routes' progress_percentage default of 0 over None.
func trBuildSubtaskSummaries(subtasks []*taskdomain.OrderedMap[any], useZeroDefault bool) ([]any, map[string]int) {
	statusCounts := map[string]int{"todo": 0, "in_progress": 0, "done": 0, "blocked": 0}
	summaries := []any{}
	for _, s := range subtasks {
		if s == nil {
			continue
		}
		id := trOmGet(s, "id")
		if inner, ok := id.(*taskdomain.OrderedMap[any]); ok {
			if v, ok := inner.Get("value"); ok {
				id = v
			}
		}
		status := trOmGet(s, "status")
		if inner, ok := status.(*taskdomain.OrderedMap[any]); ok {
			if v, ok := inner.Get("value"); ok {
				status = v
			}
		}
		priority := trOmGet(s, "priority")
		if inner, ok := priority.(*taskdomain.OrderedMap[any]); ok {
			if v, ok := inner.Get("value"); ok {
				priority = v
			}
		}
		summary := taskdomain.NewOrderedMap[any]()
		summary.Set("id", trStr(id))
		summary.Set("title", trOmGet(s, "title"))
		summary.Set("status", trStr(status))
		summary.Set("priority", trStr(priority))
		summary.Set("assignees_count", trOmLen(s, "assignees"))
		if useZeroDefault {
			summary.Set("progress_percentage", trOmGetDefault(s, "progress_percentage", 0))
		} else {
			summary.Set("progress_percentage", trOmGet(s, "progress_percentage"))
		}
		summaries = append(summaries, summary)
		key, _ := status.(string)
		if _, ok := statusCounts[key]; ok {
			statusCounts[key]++
		}
	}
	return summaries, statusCounts
}

// trBuildProgressSummary ports the progress_summary dict.
func trBuildProgressSummary(summaries []any, statusCounts map[string]int) *taskdomain.OrderedMap[any] {
	total := len(summaries)
	completion := 0
	if total > 0 {
		completion = int(math.RoundToEven((float64(statusCounts["done"]) / float64(total)) * 100))
	}
	out := taskdomain.NewOrderedMap[any]()
	out.Set("total", total)
	out.Set("completed", statusCounts["done"])
	out.Set("in_progress", statusCounts["in_progress"])
	out.Set("todo", statusCounts["todo"])
	out.Set("blocked", statusCounts["blocked"])
	out.Set("completion_percentage", completion)
	return out
}
