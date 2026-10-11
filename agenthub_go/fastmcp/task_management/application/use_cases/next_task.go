package use_cases

import (
	"context"
	"errors"
	"fmt"
	"math"
	"sort"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// NextTaskResponse is the response containing the next item to work on. Its
// Context field is a dict for error/blocking cases and a string for the task case,
// mirroring the Python dataclass.
type NextTaskResponse struct {
	HasNext     bool
	NextItem    *entities.OrderedMap[any]
	Context     any
	ContextInfo *entities.OrderedMap[any]
	Message     string
}

// NextTaskTaskRepository is the task repository surface used by NextTaskUseCase.
type NextTaskTaskRepository interface {
	FindAll(ctx context.Context) ([]*entities.Task, error)
}

// nextTaskRepositoryAttrs mirrors the Python getattr fallbacks for the repository
// context attributes. Python repositories expose these; the Go domain interface
// does not, so implementations may optionally provide them.
type nextTaskRepositoryAttrs interface {
	GitBranchID() string
	UserID() *string
	ProjectID() string
}

// NextTaskContextService is the sync unified context service surface.
type NextTaskContextService interface {
	ResolveContext(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error)
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any]) (*entities.OrderedMap[any], error)
}

// NextTaskContextFactory creates the unified context service. Python's
// UnifiedContextFacadeFactory is ported in
// application/factories/unified_context_facade_factory.go, so it is injected.
type NextTaskContextFactory interface {
	CreateUnifiedService() NextTaskContextService
}

// NextTaskUseCase ports next_task.NextTaskUseCase. The Python context_service
// argument is stored but never used, so it is dropped.
type NextTaskUseCase struct {
	taskRepository NextTaskTaskRepository
	contextFactory NextTaskContextFactory // may be nil
}

// NewNextTaskUseCase builds the use case.
func NewNextTaskUseCase(taskRepository NextTaskTaskRepository,
	contextFactory NextTaskContextFactory) *NextTaskUseCase {
	return &NextTaskUseCase{taskRepository: taskRepository, contextFactory: contextFactory}
}

// Execute finds the next task or subtask to work on.
func (uc *NextTaskUseCase) Execute(ctx context.Context, assignee *string, projectID *string,
	labels []string, gitBranchID *string, userID *string,
	includeContext bool) (*NextTaskResponse, error) {

	attrs, _ := uc.taskRepository.(nextTaskRepositoryAttrs)

	if gitBranchID == nil {
		value := "main"
		if attrs != nil {
			value = attrs.GitBranchID()
		}
		gitBranchID = &value
	}
	if userID == nil {
		if attrs != nil {
			userID = attrs.UserID()
		}
		if userID == nil {
			return nil, value_objects.ValueErrorf(
				"user_id is required for next task operation (no fallback allowed for DDD compliance)")
		}
	}
	if projectID == nil {
		value := ""
		if attrs != nil {
			value = attrs.ProjectID()
		}
		projectID = &value
	}

	allTasks, err := uc.taskRepository.FindAll(ctx)
	if err != nil {
		return nil, err
	}
	if len(allTasks) == 0 {
		return &NextTaskResponse{HasNext: false, Message: "No tasks found. Create a task to get started!"}, nil
	}

	filteredTasks := applyNextTaskFilters(allTasks, assignee, labels)
	if len(filteredTasks) == 0 {
		return &NextTaskResponse{HasNext: false, Message: "No tasks match the specified filters."}, nil
	}

	statusMismatches := uc.validateTaskContextAlignment(ctx, filteredTasks)
	if len(statusMismatches) > 0 {
		contextMap := entities.NewOrderedMap[any]()
		contextMap.Set("error_type", "status_mismatch")
		contextMap.Set("mismatches", statusMismatches)
		contextMap.Set("fix_required", true)
		return &NextTaskResponse{
			HasNext: false,
			Context: contextMap,
			Message: fmt.Sprintf(
				"❌ CRITICAL: Found %d task(s) with mismatched task/context status. Fix required before proceeding.",
				len(statusMismatches)),
		}, nil
	}

	activeTasks := []*entities.Task{}
	for _, task := range filteredTasks {
		if task.Status != nil && (task.Status.Value == "todo" || task.Status.Value == "in_progress") {
			activeTasks = append(activeTasks, task)
		}
	}

	if len(activeTasks) == 0 {
		completedTasks := []*entities.Task{}
		for _, task := range filteredTasks {
			if task.Status != nil && task.Status.IsDone() {
				completedTasks = append(completedTasks, task)
			}
		}
		if len(completedTasks) == len(filteredTasks) {
			return &NextTaskResponse{HasNext: false, Context: nextTaskCompletionContext(filteredTasks),
				Message: "🎉 All tasks completed! Great job!"}, nil
		}
		return &NextTaskResponse{HasNext: false, Message: "No actionable tasks found."}, nil
	}

	sortedTasks := sortNextTasksByPriority(activeTasks)

	for _, task := range sortedTasks {
		if !canTaskBeStarted(task, allTasks) {
			continue
		}

		nextSubtask, err := uc.findNextSubtask(task)
		if err != nil {
			return nil, err
		}
		taskID := nextTaskIDString(task)

		if nextSubtask != nil {
			nextItem := entities.NewOrderedMap[any]()
			nextItem.Set("type", "subtask")
			taskDict, err := uc.taskToDict(ctx, task, includeContext)
			if err != nil {
				return nil, err
			}
			nextItem.Set("task", taskDict)
			nextItem.Set("subtask", nextSubtask)
			nextItem.Set("context", nextTaskContext(task, allTasks))
			title := value_objects.PyStr(nextSubtask["title"])
			return &NextTaskResponse{HasNext: true, NextItem: nextItem,
				Message: fmt.Sprintf("Next action: Work on subtask '%s' in task '%s'", title, task.Title)}, nil
		}

		var contextInfo *entities.OrderedMap[any]
		if shouldGenerateContextInfo(task) {
			contextInfo = uc.buildContextInfo(ctx, task, *projectID)
		}

		nextItem := entities.NewOrderedMap[any]()
		nextItem.Set("type", "task")
		taskDict, err := uc.taskToDict(ctx, task, includeContext)
		if err != nil {
			return nil, err
		}
		nextItem.Set("task", taskDict)
		nextItem.Set("context", nextTaskContext(task, allTasks))

		var contextValue any = taskID
		if task.ContextID != nil && value_objects.PyTruthy(*task.ContextID) {
			contextValue = *task.ContextID
		}
		return &NextTaskResponse{
			HasNext:     true,
			NextItem:    nextItem,
			Context:     contextValue,
			ContextInfo: contextInfo,
			Message:     fmt.Sprintf("Next action: Work on task '%s'", task.Title),
		}, nil
	}

	blockedTasks := []*entities.Task{}
	for _, task := range activeTasks {
		if !canTaskBeStarted(task, allTasks) {
			blockedTasks = append(blockedTasks, task)
		}
	}
	if len(blockedTasks) > 0 {
		return &NextTaskResponse{
			HasNext: false,
			Context: nextTaskBlockingInfo(blockedTasks, allTasks),
			Message: "All remaining tasks are blocked by dependencies. Complete prerequisite tasks first.",
		}, nil
	}

	return &NextTaskResponse{HasNext: false, Message: "No actionable tasks found."}, nil
}

func applyNextTaskFilters(tasks []*entities.Task, assignee *string, labels []string) []*entities.Task {
	if len(tasks) == 0 {
		return []*entities.Task{}
	}
	filtered := append([]*entities.Task{}, tasks...)

	if assignee != nil && *assignee != "" {
		out := []*entities.Task{}
		for _, task := range filtered {
			if indexOfString(task.Assignees, *assignee) {
				out = append(out, task)
			}
		}
		filtered = out
	}

	if len(labels) > 0 {
		out := []*entities.Task{}
		for _, task := range filtered {
			for _, label := range labels {
				if indexOfString(task.Labels, label) {
					out = append(out, task)
					break
				}
			}
		}
		filtered = out
	}
	return filtered
}

func sortNextTasksByPriority(tasks []*entities.Task) []*entities.Task {
	if len(tasks) == 0 {
		return []*entities.Task{}
	}
	priorityOrder := map[string]int{"critical": 0, "urgent": 1, "high": 2, "medium": 3, "low": 4}
	statusOrder := map[string]int{"todo": 0, "in_progress": 1}
	out := append([]*entities.Task{}, tasks...)
	sort.SliceStable(out, func(i, j int) bool {
		pi, si := nextTaskSortKey(out[i], priorityOrder, statusOrder)
		pj, sj := nextTaskSortKey(out[j], priorityOrder, statusOrder)
		if pi != pj {
			return pi < pj
		}
		return si < sj
	})
	return out
}

func nextTaskSortKey(task *entities.Task, priorityOrder, statusOrder map[string]int) (int, int) {
	priorityVal := "medium"
	if task.Priority != nil {
		priorityVal = task.Priority.Value
	}
	priorityScore, ok := priorityOrder[priorityVal]
	if !ok {
		priorityScore = 5
	}
	statusVal := "todo"
	if task.Status != nil {
		statusVal = task.Status.Value
	}
	statusScore, ok := statusOrder[statusVal]
	if !ok {
		statusScore = 2
	}
	return priorityScore, statusScore
}

func canTaskBeStarted(task *entities.Task, allTasks []*entities.Task) bool {
	if len(task.Dependencies) == 0 {
		return true
	}
	for _, depID := range task.Dependencies {
		var depTask *entities.Task
		for _, candidate := range allTasks {
			if candidate.ID != nil && candidate.ID.Value == depID.Value {
				depTask = candidate
				break
			}
		}
		if depTask == nil || depTask.Status == nil || !depTask.Status.IsDone() {
			return false
		}
	}
	return true
}

// findNextSubtask mirrors the Python helper. task.subtasks is list[str]; the
// Python subtask.get("completed", False) raises AttributeError for a string, which
// _find_next_subtask does not catch. The Go port returns that error.
func (uc *NextTaskUseCase) findNextSubtask(task *entities.Task) (map[string]any, error) {
	if len(task.Subtasks) == 0 {
		return nil, nil
	}
	return nil, errors.New("'str' object has no attribute 'get'")
}

// shouldGenerateContextInfo mirrors _should_generate_context_info: a task whose
// subtasks list is non-empty takes the AttributeError path and returns False.
func shouldGenerateContextInfo(task *entities.Task) bool {
	if task == nil || task.Status == nil {
		return false
	}
	if task.Status.Value != "todo" {
		return false
	}
	if len(task.Subtasks) > 0 {
		return false
	}
	return true
}

func (uc *NextTaskUseCase) buildContextInfo(ctx context.Context, task *entities.Task,
	projectID string) *entities.OrderedMap[any] {

	taskID := nextTaskIDString(task)
	service := uc.contextService()
	if service == nil {
		return nextTaskContextErrorInfo(taskID, errors.New("context factory unavailable"))
	}

	contextResult, err := service.ResolveContext(ctx, "task", taskID)
	if err != nil {
		contextResult = nil
	}

	success := false
	if contextResult != nil {
		raw, _ := contextResult.Get("success")
		success = value_objects.PyTruthy(raw)
	}
	if !success {
		data := entities.NewOrderedMap[any]()
		data.Set("parent_project_id", projectID)
		taskData := entities.NewOrderedMap[any]()
		taskData.Set("title", task.Title)
		taskData.Set("description", task.Description)
		status := "todo"
		if task.Status != nil {
			status = task.Status.Value
		}
		taskData.Set("status", status)
		priority := "medium"
		if task.Priority != nil {
			priority = task.Priority.Value
		}
		taskData.Set("priority", priority)
		taskData.Set("assignees", task.Assignees)
		taskData.Set("labels", task.Labels)
		data.Set("task_data", taskData)
		if _, createErr := service.CreateContext(ctx, "task", taskID, data); createErr == nil {
			contextResult, _ = service.ResolveContext(ctx, "task", taskID)
		}
	}

	if contextResult != nil {
		raw, _ := contextResult.Get("success")
		if value_objects.PyTruthy(raw) {
			contextValue, _ := contextResult.Get("context")
			info := entities.NewOrderedMap[any]()
			info.Set("context", contextValue)
			info.Set("created", true)
			info.Set("message", fmt.Sprintf("Context resolved for task %s", taskID))
			return info
		}
	}

	info := entities.NewOrderedMap[any]()
	info.Set("context", nil)
	info.Set("created", false)
	info.Set("message", fmt.Sprintf("Context not available for task %s (continuing without context)", taskID))
	return info
}

func nextTaskContextErrorInfo(taskID string, err error) *entities.OrderedMap[any] {
	info := entities.NewOrderedMap[any]()
	info.Set("context", nil)
	info.Set("created", false)
	info.Set("message", fmt.Sprintf("Context error for task %s: %s", taskID, err.Error()))
	return info
}

func (uc *NextTaskUseCase) contextService() NextTaskContextService {
	if uc.contextFactory == nil {
		return nil
	}
	return uc.contextFactory.CreateUnifiedService()
}

// taskToDict mirrors _task_to_dict. The returned dict is the entity's map with the
// context_data/context_available keys appended.
func (uc *NextTaskUseCase) taskToDict(ctx context.Context, task *entities.Task,
	includeContext bool) (map[string]any, error) {

	taskDict, err := task.ToDict()
	if err != nil {
		return nil, err
	}
	if includeContext {
		service := uc.contextService()
		var contextResult *entities.OrderedMap[any]
		if service != nil {
			contextResult, _ = service.ResolveContext(ctx, "task", nextTaskIDString(task))
		}
		success := false
		if contextResult != nil {
			raw, _ := contextResult.Get("success")
			success = value_objects.PyTruthy(raw)
		}
		if success {
			contextValue, _ := contextResult.Get("context")
			if contextEntity, ok := contextValue.(*entities.TaskContext); ok {
				taskDict["context_data"] = contextEntity.ToDict(true)
			} else {
				taskDict["context_data"] = contextValue
			}
			taskDict["context_available"] = true
		} else {
			taskDict["context_data"] = nil
			taskDict["context_available"] = false
		}
	} else {
		taskDict["context_data"] = nil
		taskDict["context_available"] = false
	}
	return taskDict, nil
}

// nextTaskContext mirrors _get_task_context.
func nextTaskContext(task *entities.Task, allTasks []*entities.Task) *entities.OrderedMap[any] {
	dependencyCount := len(task.Dependencies)
	blockingCount := 0
	for _, candidate := range allTasks {
		for _, dep := range candidate.Dependencies {
			if task.ID != nil && dep.Value == task.ID.Value {
				blockingCount++
				break
			}
		}
	}
	totalTasks := len(allTasks)
	completedTasks := 0
	for _, candidate := range allTasks {
		if candidate.Status != nil && candidate.Status.IsDone() {
			completedTasks++
		}
	}
	overall := entities.NewOrderedMap[any]()
	overall.Set("completed", completedTasks)
	overall.Set("total", totalTasks)
	var percentage any = 0
	if totalTasks > 0 {
		percentage = math.Round(float64(completedTasks)/float64(totalTasks)*100*10) / 10
	}
	overall.Set("percentage", percentage)

	out := entities.NewOrderedMap[any]()
	out.Set("task_id", nextTaskIDString(task))
	out.Set("can_start", canTaskBeStarted(task, allTasks))
	out.Set("dependency_count", dependencyCount)
	out.Set("blocking_count", blockingCount)
	out.Set("overall_progress", overall)
	if len(task.Subtasks) > 0 {
		out.Set("subtask_progress", task.GetSubtaskProgress())
	}
	return out
}

// nextTaskCompletionContext mirrors _get_completion_context.
func nextTaskCompletionContext(allTasks []*entities.Task) *entities.OrderedMap[any] {
	priorityCounts := entities.NewOrderedMap[any]()
	for _, task := range allTasks {
		priority := "None"
		if task.Priority != nil {
			priority = task.Priority.String()
		}
		if v, ok := priorityCounts.Get(priority); ok {
			priorityCounts.Set(priority, v.(int)+1)
		} else {
			priorityCounts.Set(priority, 1)
		}
	}
	out := entities.NewOrderedMap[any]()
	out.Set("total_completed", len(allTasks))
	out.Set("priority_breakdown", priorityCounts)
	out.Set("completion_rate", 100.0)
	return out
}

// nextTaskBlockingInfo mirrors _get_blocking_info.
func nextTaskBlockingInfo(blockedTasks, allTasks []*entities.Task) *entities.OrderedMap[any] {
	blocked := []any{}
	required := []any{}
	requiredIDs := map[string]bool{}

	for _, task := range blockedTasks {
		taskInfo := entities.NewOrderedMap[any]()
		taskInfo.Set("id", nextTaskIDString(task))
		taskInfo.Set("title", task.Title)
		priority := "None"
		if task.Priority != nil {
			priority = task.Priority.String()
		}
		taskInfo.Set("priority", priority)
		blockedBy := []any{}
		for _, depID := range task.Dependencies {
			var depTask *entities.Task
			for _, candidate := range allTasks {
				if candidate.ID != nil && candidate.ID.Value == depID.Value {
					depTask = candidate
					break
				}
			}
			if depTask == nil || (depTask.Status != nil && depTask.Status.IsDone()) {
				continue
			}
			depStatus := "None"
			if depTask.Status != nil {
				depStatus = depTask.Status.String()
			}
			blockedBy = append(blockedBy, nextTaskBlocker(depTask, depStatus))
			depTaskID := nextTaskIDString(depTask)
			if !requiredIDs[depTaskID] {
				requiredIDs[depTaskID] = true
				depPriority := "None"
				if depTask.Priority != nil {
					depPriority = depTask.Priority.String()
				}
				requirement := entities.NewOrderedMap[any]()
				requirement.Set("id", depTaskID)
				requirement.Set("title", depTask.Title)
				requirement.Set("status", depStatus)
				requirement.Set("priority", depPriority)
				required = append(required, requirement)
			}
		}
		taskInfo.Set("blocked_by", blockedBy)
		blocked = append(blocked, taskInfo)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("blocked_tasks", blocked)
	out.Set("required_completions", required)
	return out
}

func nextTaskBlocker(depTask *entities.Task, status string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", nextTaskIDString(depTask))
	m.Set("title", depTask.Title)
	m.Set("status", status)
	return m
}

func nextTaskIDString(task *entities.Task) string {
	if task.ID == nil {
		return "None"
	}
	return task.ID.Value
}

// validateTaskContextAlignment mirrors _validate_task_context_alignment; every
// failure is swallowed and simply skips the task.
func (uc *NextTaskUseCase) validateTaskContextAlignment(ctx context.Context,
	tasks []*entities.Task) []any {

	mismatches := []any{}
	if uc.contextFactory == nil {
		return mismatches
	}
	service := uc.contextFactory.CreateUnifiedService()
	if service == nil {
		return mismatches
	}

	for _, task := range tasks {
		taskID := nextTaskIDString(task)
		contextResult, err := service.ResolveContext(ctx, "task", taskID)
		if err != nil || contextResult == nil {
			continue
		}
		rawSuccess, _ := contextResult.Get("success")
		if !value_objects.PyTruthy(rawSuccess) {
			continue
		}
		contextValue, ok := contextResult.Get("context")
		if !ok || contextValue == nil {
			continue
		}
		contextData := getTaskToOrderedMap(contextValue)
		if contextData == nil {
			continue
		}

		contextStatus := ""
		if metadataValue, ok := contextData.Get("metadata"); ok {
			if metadata := getTaskToOrderedMap(metadataValue); metadata != nil {
				if raw, ok := metadata.Get("status"); ok && raw != nil {
					contextStatus = value_objects.PyStr(raw)
				}
			}
		}
		taskStatus := "todo"
		if task.Status != nil {
			taskStatus = task.Status.Value
		}

		if contextStatus != "" && contextStatus != taskStatus {
			mismatch := entities.NewOrderedMap[any]()
			mismatch.Set("task_id", taskID)
			mismatch.Set("title", task.Title)
			mismatch.Set("task_status", taskStatus)
			mismatch.Set("context_status", contextStatus)
			mismatch.Set("fix_action", fmt.Sprintf(
				"Update context status from '%s' to '%s' or vice versa", contextStatus, taskStatus))
			mismatch.Set("suggested_command", fmt.Sprintf(
				"manage_context(action='update_property', level='task', context_id='%s', property_path='metadata.status', value='%s')",
				taskID, taskStatus))
			mismatches = append(mismatches, mismatch)
		}

		if taskStatus == "done" {
			if subtasksValue, ok := contextData.Get("subtasks"); ok {
				if subtasks := getTaskToOrderedMap(subtasksValue); subtasks != nil {
					if itemsValue, ok := subtasks.Get("items"); ok && value_objects.PyTruthy(itemsValue) {
						incomplete := []any{}
						for _, item := range orderedListAny(itemsValue) {
							itemMap := getTaskToOrderedMap(item)
							if itemMap == nil {
								continue
							}
							completed, _ := itemMap.Get("completed")
							if !value_objects.PyTruthy(completed) {
								incomplete = append(incomplete, itemMap)
							}
						}
						if len(incomplete) > 0 {
							mismatch := entities.NewOrderedMap[any]()
							mismatch.Set("task_id", taskID)
							mismatch.Set("title", task.Title)
							mismatch.Set("task_status", taskStatus)
							mismatch.Set("context_status", contextStatus)
							mismatch.Set("issue", "task_done_but_subtasks_incomplete")
							mismatch.Set("incomplete_subtasks", len(incomplete))
							mismatch.Set("fix_action", fmt.Sprintf(
								"Complete %d remaining subtasks or update task status", len(incomplete)))
							details := []any{}
							limit := len(incomplete)
							if limit > 3 {
								limit = 3
							}
							for _, item := range incomplete[:limit] {
								itemMap, _ := item.(*entities.OrderedMap[any])
								detail := entities.NewOrderedMap[any]()
								if itemMap != nil {
									id, _ := itemMap.Get("id")
									title, _ := itemMap.Get("title")
									detail.Set("id", id)
									detail.Set("title", title)
								} else {
									detail.Set("id", nil)
									detail.Set("title", nil)
								}
								details = append(details, detail)
							}
							mismatch.Set("incomplete_subtask_details", details)
							mismatches = append(mismatches, mismatch)
						}
					}
				}
			}
		}
	}
	return mismatches
}

func indexOfString(list []string, value string) bool {
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}

// orderedListAny coerces a Python-list value to []any.
func orderedListAny(v any) []any {
	switch xs := v.(type) {
	case []any:
		return xs
	case []string:
		out := make([]any, 0, len(xs))
		for _, x := range xs {
			out = append(out, x)
		}
		return out
	case []*entities.OrderedMap[any]:
		out := make([]any, 0, len(xs))
		for _, x := range xs {
			out = append(out, x)
		}
		return out
	case []map[string]any:
		out := make([]any, 0, len(xs))
		for _, x := range xs {
			out = append(out, x)
		}
		return out
	}
	return nil
}
