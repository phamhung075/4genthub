package types

// Domain to DTO Converters (Python types/converters.py).
// Helper functions to convert domain entities to API DTOs. Both dict input
// (performance mode) and entity objects are accepted, like Python's isinstance
// checks plus getattr duck typing.

import (
	dom "agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// getValue mirrors _get_value: dict.get for a dict, getattr otherwise.
func getValue(obj any, key string, def any) any {
	if isPyDict(obj) {
		return pyDictGetDefault(obj, key, def)
	}
	return pyGetattr(obj, key, def)
}

// dictIndex mirrors obj[key] on a dict, including the KeyError on a missing key.
func dictIndex(d any, key string) (any, error) {
	if v, ok := pyDictGet(d, key); ok {
		return v, nil
	}
	return nil, &dom.KeyError{Msg: key}
}

func strPtrOrNil(v any) *string {
	if v == nil {
		return nil
	}
	s := v.(string)
	return &s
}

func intPtr(i int) *int { return &i }

// TaskToDTO converts a domain Task entity or dict to TaskDTO.
func TaskToDTO(task any, includeSubtasks bool) (*TaskDTO, error) {
	if isPyDict(task) {
		assignees := listOrEmpty(pyDictGetDefault(task, "assignees", nil))
		dependencies := listOrEmpty(pyDictGetDefault(task, "dependencies", nil))
		labels := listOrEmpty(pyDictGetDefault(task, "labels", nil))
		subtasks := pyAnySlice(pyDictGetDefault(task, "subtasks", nil))

		id, err := dictIndex(task, "id")
		if err != nil {
			return nil, err
		}
		title, err := dictIndex(task, "title")
		if err != nil {
			return nil, err
		}
		status, err := dictIndex(task, "status")
		if err != nil {
			return nil, err
		}
		priority, err := dictIndex(task, "priority")
		if err != nil {
			return nil, err
		}
		gitBranch, err := dictIndex(task, "git_branch_id")
		if err != nil {
			return nil, err
		}

		dto := &TaskDTO{
			ID:                 pyStrOf(id),
			Title:              pyStrOf(title),
			Description:        optStrAny(pyDictGetDefault(task, "description", nil)),
			Status:             pyStrOf(status),
			Priority:           pyStrOf(priority),
			Assignees:          assignees,
			AssigneesCount:     len(assignees),
			SubtaskCount:       asInt(pyDictGetDefault(task, "subtask_count", 0), 0),
			HasDependencies:    len(dependencies) > 0,
			DependencyCount:    intPtr(len(dependencies)),
			Dependencies:       pyStringSlice(dependencies),
			HasContext:         value_objects.PyTruthy(pyDictGetDefault(task, "context_id", nil)),
			ContextID:          optStrAny(pyDictGetDefault(task, "context_id", nil)),
			ContextData:        pyDictGetDefault(task, "context_data", nil),
			GitBranchID:        optStrAny(gitBranch),
			ProjectID:          optStrAny(pyDictGetDefault(task, "project_id", "")),
			CreatedAt:          strPtrOrNil(formatDatetime(pyDictGetDefault(task, "created_at", nil))),
			UpdatedAt:          strPtrOrNil(formatDatetime(pyDictGetDefault(task, "updated_at", nil))),
			DueDate:            strPtrOrNil(formatDatetime(pyDictGetDefault(task, "due_date", nil))),
			EstimatedEffort:    optStrAny(pyDictGetDefault(task, "estimated_effort", nil)),
			Labels:             labels,
			Details:            optStrAny(pyDictGetDefault(task, "details", nil)),
			ProgressPercentage: optIntAny(pyDictGetDefault(task, "progress_percentage", nil)),
			ProgressHistory:    pyDictGetDefault(task, "progress_history", nil),
			ProgressCount:      optIntAny(pyDictGetDefault(task, "progress_count", nil)),
		}
		if includeSubtasks && len(subtasks) > 0 {
			converted := make([]*SubtaskDTO, 0, len(subtasks))
			for _, st := range subtasks {
				sub, err := SubtaskToDTO(st)
				if err != nil {
					return nil, err
				}
				converted = append(converted, sub)
			}
			dto.Subtasks = converted
		}
		return dto, nil
	}

	// Entity object input (standard ORM mode).
	assignees := listOrEmpty(pyGetattr(task, "assignees", nil))
	dependencies := listOrEmpty(pyGetattr(task, "dependencies", nil))
	labels := listOrEmpty(pyGetattr(task, "labels", nil))
	subtasks := pyAnySlice(pyGetattr(task, "subtasks", nil))

	projectVal := pyGetattr(task, "project_id", "")
	projectID := ""
	if value_objects.PyTruthy(projectVal) {
		projectID = pyStrOf(projectVal)
	}
	contextVal := pyGetattr(task, "context_id", nil)
	var contextID *string
	if value_objects.PyTruthy(contextVal) {
		contextID = optStrAny(contextVal)
	}

	dto := &TaskDTO{
		ID: getValueString(task, "id", ""),
		// Python does not call str() on title here.
		Title:              pyStrOf(pyGetattr(task, "title", "")),
		Description:        optStrAny(pyGetattr(task, "description", nil)),
		Status:             pyStrOf(pyGetattr(task, "status", "todo")),
		Priority:           pyStrOf(pyGetattr(task, "priority", "medium")),
		Assignees:          assignees,
		AssigneesCount:     len(assignees),
		SubtaskCount:       asInt(pyGetattr(task, "subtask_count", 0), 0),
		HasDependencies:    len(dependencies) > 0,
		DependencyCount:    intPtr(len(dependencies)),
		Dependencies:       pyStringSlice(dependencies),
		HasContext:         value_objects.PyTruthy(contextVal),
		ContextID:          contextID,
		ContextData:        pyGetattr(task, "context_data", nil),
		GitBranchID:        optStrAny(pyStrOf(pyGetattr(task, "git_branch_id", ""))),
		ProjectID:          optStrAny(projectID),
		CreatedAt:          strPtrOrNil(formatDatetime(pyGetattr(task, "created_at", nil))),
		UpdatedAt:          strPtrOrNil(formatDatetime(pyGetattr(task, "updated_at", nil))),
		DueDate:            strPtrOrNil(formatDatetime(pyGetattr(task, "due_date", nil))),
		EstimatedEffort:    optStrAny(pyGetattr(task, "estimated_effort", nil)),
		Labels:             labels,
		Details:            optStrAny(pyGetattr(task, "details", nil)),
		ProgressPercentage: optIntAny(pyGetattr(task, "progress_percentage", nil)),
		ProgressHistory:    pyGetattr(task, "progress_history", nil),
		ProgressCount:      optIntAny(pyGetattr(task, "progress_count", nil)),
	}
	if includeSubtasks && len(subtasks) > 0 {
		converted := make([]*SubtaskDTO, 0, len(subtasks))
		for _, st := range subtasks {
			sub, err := SubtaskToDTO(st)
			if err != nil {
				return nil, err
			}
			converted = append(converted, sub)
		}
		dto.Subtasks = converted
	}
	return dto, nil
}

// getValueString is str(getattr(obj, key, def)).
func getValueString(obj any, key, def string) string {
	return pyStrOf(pyGetattr(obj, key, def))
}

// SubtaskToDTO converts a domain Subtask entity or dict to SubtaskDTO.
func SubtaskToDTO(subtask any) (*SubtaskDTO, error) {
	if isPyDict(subtask) {
		assignees := listOrEmpty(pyDictGetDefault(subtask, "assignees", nil))
		id, err := dictIndex(subtask, "id")
		if err != nil {
			return nil, err
		}
		title, err := dictIndex(subtask, "title")
		if err != nil {
			return nil, err
		}
		status, err := dictIndex(subtask, "status")
		if err != nil {
			return nil, err
		}
		priority, err := dictIndex(subtask, "priority")
		if err != nil {
			return nil, err
		}
		taskID := pyDictGetDefault(subtask, "parent_task_id", pyDictGetDefault(subtask, "task_id", ""))
		return &SubtaskDTO{
			ID:                 pyStrOf(id),
			TaskID:             pyStrOf(taskID),
			Title:              pyStrOf(title),
			Description:        optStrAny(pyDictGetDefault(subtask, "description", nil)),
			Status:             pyStrOf(status),
			Priority:           pyStrOf(priority),
			Assignees:          assignees,
			AssigneesCount:     len(assignees),
			ProgressPercentage: optIntAny(pyDictGetDefault(subtask, "progress_percentage", nil)),
			ProgressHistory:    pyDictGetDefault(subtask, "progress_history", nil),
			ProgressCount:      optIntAny(pyDictGetDefault(subtask, "progress_count", nil)),
			CreatedAt:          strPtrOrNil(formatDatetime(pyDictGetDefault(subtask, "created_at", nil))),
			UpdatedAt:          strPtrOrNil(formatDatetime(pyDictGetDefault(subtask, "updated_at", nil))),
			ProgressNotes:      optStrAny(pyDictGetDefault(subtask, "progress_notes", nil)),
			CompletionSummary:  optStrAny(pyDictGetDefault(subtask, "completion_summary", nil)),
		}, nil
	}

	// Entity object input (standard ORM mode).
	assignees := listOrEmpty(pyGetattr(subtask, "assignees", nil))
	parent := pyGetattr(subtask, "parent_task_id", nil)
	if !value_objects.PyTruthy(parent) {
		parent = pyGetattr(subtask, "task_id", "")
	}
	return &SubtaskDTO{
		ID:                 pyStrOf(pyGetattr(subtask, "id", "")),
		TaskID:             pyStrOf(parent),
		Title:              pyStrOf(pyGetattr(subtask, "title", "")),
		Description:        optStrAny(pyGetattr(subtask, "description", nil)),
		Status:             pyStrOf(pyGetattr(subtask, "status", "todo")),
		Priority:           pyStrOf(pyGetattr(subtask, "priority", "medium")),
		Assignees:          assignees,
		AssigneesCount:     len(assignees),
		ProgressPercentage: optIntAny(pyGetattr(subtask, "progress_percentage", nil)),
		ProgressHistory:    pyGetattr(subtask, "progress_history", nil),
		ProgressCount:      optIntAny(pyGetattr(subtask, "progress_count", nil)),
		CreatedAt:          strPtrOrNil(formatDatetime(pyGetattr(subtask, "created_at", nil))),
		UpdatedAt:          strPtrOrNil(formatDatetime(pyGetattr(subtask, "updated_at", nil))),
		ProgressNotes:      optStrAny(pyGetattr(subtask, "progress_notes", nil)),
		CompletionSummary:  optStrAny(pyGetattr(subtask, "completion_summary", nil)),
	}, nil
}

// TaskSummaryToDTO converts a domain Task or dict to TaskSummaryDTO.
func TaskSummaryToDTO(task any) (*TaskSummaryDTO, error) {
	// Logging calls in the Python are dropped.
	if isPyDict(task) {
		assignees := listOrEmpty(pyDictGetDefault(task, "assignees", nil))
		dependencies := listOrEmpty(pyDictGetDefault(task, "dependencies", nil))
		id, err := dictIndex(task, "id")
		if err != nil {
			return nil, err
		}
		title, err := dictIndex(task, "title")
		if err != nil {
			return nil, err
		}
		status, err := dictIndex(task, "status")
		if err != nil {
			return nil, err
		}
		priority, err := dictIndex(task, "priority")
		if err != nil {
			return nil, err
		}
		return &TaskSummaryDTO{
			ID:              pyStrOf(id),
			Title:           pyStrOf(title),
			Status:          pyStrOf(status),
			Priority:        pyStrOf(priority),
			SubtaskCount:    asInt(pyDictGetDefault(task, "subtask_count", 0), 0),
			AssigneesCount:  len(assignees),
			Assignees:       assignees,
			HasDependencies: len(dependencies) > 0,
			DependencyCount: intPtr(len(dependencies)),
			HasContext:      value_objects.PyTruthy(pyDictGetDefault(task, "context_id", nil)),
			GitBranchID:     optStrAny(pyDictGetDefault(task, "git_branch_id", nil)),
			ProjectID:       optStrAny(pyDictGetDefault(task, "project_id", nil)),
			CreatedAt:       strPtrOrNil(formatDatetime(pyDictGetDefault(task, "created_at", nil))),
			UpdatedAt:       strPtrOrNil(formatDatetime(pyDictGetDefault(task, "updated_at", nil))),
		}, nil
	}

	// Entity object input (standard ORM mode).
	assignees := listOrEmpty(pyGetattr(task, "assignees", nil))
	dependencies := listOrEmpty(pyGetattr(task, "dependencies", nil))
	var gitBranchID *string
	if v := pyGetattr(task, "git_branch_id", nil); value_objects.PyTruthy(v) {
		gitBranchID = optStrAny(v)
	}
	var projectID *string
	if v := pyGetattr(task, "project_id", nil); value_objects.PyTruthy(v) {
		projectID = optStrAny(v)
	}
	return &TaskSummaryDTO{
		ID:              getValueString(task, "id", ""),
		Title:           pyStrOf(pyGetattr(task, "title", "")),
		Status:          pyStrOf(pyGetattr(task, "status", "todo")),
		Priority:        pyStrOf(pyGetattr(task, "priority", "medium")),
		SubtaskCount:    asInt(pyGetattr(task, "subtask_count", 0), 0),
		AssigneesCount:  len(assignees),
		Assignees:       assignees,
		HasDependencies: len(dependencies) > 0,
		DependencyCount: intPtr(len(dependencies)),
		HasContext:      value_objects.PyTruthy(pyGetattr(task, "context_id", nil)),
		GitBranchID:     gitBranchID,
		ProjectID:       projectID,
		CreatedAt:       strPtrOrNil(formatDatetime(pyGetattr(task, "created_at", nil))),
		UpdatedAt:       strPtrOrNil(formatDatetime(pyGetattr(task, "updated_at", nil))),
	}, nil
}

// SubtaskSummaryToDTO converts a domain Subtask or dict to SubtaskSummaryDTO.
func SubtaskSummaryToDTO(subtask any) (*SubtaskSummaryDTO, error) {
	if isPyDict(subtask) {
		assignees := listOrEmpty(pyDictGetDefault(subtask, "assignees", nil))
		id, err := dictIndex(subtask, "id")
		if err != nil {
			return nil, err
		}
		title, err := dictIndex(subtask, "title")
		if err != nil {
			return nil, err
		}
		status, err := dictIndex(subtask, "status")
		if err != nil {
			return nil, err
		}
		priority, err := dictIndex(subtask, "priority")
		if err != nil {
			return nil, err
		}
		taskID := pyDictGetDefault(subtask, "parent_task_id", pyDictGetDefault(subtask, "task_id", ""))
		return &SubtaskSummaryDTO{
			ID:                 pyStrOf(id),
			TaskID:             pyStrOf(taskID),
			Title:              pyStrOf(title),
			Status:             pyStrOf(status),
			Priority:           pyStrOf(priority),
			AssigneesCount:     len(assignees),
			Assignees:          assignees,
			ProgressPercentage: optIntAny(pyDictGetDefault(subtask, "progress_percentage", nil)),
			CreatedAt:          strPtrOrNil(formatDatetime(pyDictGetDefault(subtask, "created_at", nil))),
			UpdatedAt:          strPtrOrNil(formatDatetime(pyDictGetDefault(subtask, "updated_at", nil))),
		}, nil
	}

	// Entity object input (standard ORM mode).
	assignees := listOrEmpty(pyGetattr(subtask, "assignees", nil))
	parent := pyGetattr(subtask, "parent_task_id", nil)
	if !value_objects.PyTruthy(parent) {
		parent = pyGetattr(subtask, "task_id", "")
	}
	return &SubtaskSummaryDTO{
		ID:                 pyStrOf(pyGetattr(subtask, "id", "")),
		TaskID:             pyStrOf(parent),
		Title:              pyStrOf(pyGetattr(subtask, "title", "")),
		Status:             pyStrOf(pyGetattr(subtask, "status", "todo")),
		Priority:           pyStrOf(pyGetattr(subtask, "priority", "medium")),
		AssigneesCount:     len(assignees),
		Assignees:          assignees,
		ProgressPercentage: optIntAny(pyGetattr(subtask, "progress_percentage", nil)),
		CreatedAt:          strPtrOrNil(formatDatetime(pyGetattr(subtask, "created_at", nil))),
		UpdatedAt:          strPtrOrNil(formatDatetime(pyGetattr(subtask, "updated_at", nil))),
	}, nil
}
