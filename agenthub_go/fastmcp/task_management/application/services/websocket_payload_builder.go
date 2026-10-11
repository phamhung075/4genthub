package services

import (
	"time"

	taskdtos "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// WebSocketPayloadBuilder mirrors websocket_payload_builder.WebSocketPayloadBuilder.
// Python builds a plain dict whose key order is sent to clients, so the Go shape is an
// OrderedMap in the same insertion order.
type WebSocketPayloadBuilder struct{}

// BuildTaskPayload mirrors WebSocketPayloadBuilder.build_task_payload.
//
// task_response is the Python `task_response=None` optional TaskResponse DTO.
// includeProgressHistory mirrors the Python default-True flag; with the history gone from the
// payload it now gates the details string alone.
func (WebSocketPayloadBuilder) BuildTaskPayload(
	task *entities.Task,
	taskResponse *taskdtos.TaskResponse,
	includeProgressHistory bool,
) *entities.OrderedMap[any] {
	payload := entities.NewOrderedMap[any]()

	// Core identifiers from domain task.
	payload.Set("id", taskIDString(task))
	payload.Set("title", task.Title)
	payload.Set("status", taskStatusString(task))
	payload.Set("priority", taskPriorityString(task))

	// Relationship data (from task_response if available, else from task).
	if taskResponse != nil {
		payload.Set("project_id", ptrStringOrNil(taskResponse.ProjectID))
		payload.Set("git_branch_id", ptrStringOrNil(taskResponse.GitBranchID))
		payload.Set("subtask_count", taskResponse.SubtaskCount())
		payload.Set("completed_subtasks", taskResponse.CompletedSubtasks)
		payload.Set("progress_percentage", taskResponse.ProgressPercentage)

		if includeProgressHistory {
			payload.Set("details", taskResponse.Details)
		} else {
			payload.Set("details", "")
		}
	} else {
		payload.Set("project_id", nil)
		payload.Set("git_branch_id", ptrStringOrNil(task.GitBranchID))
		payload.Set("subtask_count", len(task.Subtasks))
		payload.Set("completed_subtasks", 0)
		// Python has no `progress_percentage` attribute on Task, so hasattr is False -> 0.
		payload.Set("progress_percentage", 0)

		if includeProgressHistory {
			payload.Set("details", task.GetProgressHistoryText())
		} else {
			payload.Set("details", "")
		}
	}

	// Team & assignment (from task entity).
	assignees := task.Assignees
	if len(assignees) == 0 {
		assignees = []string{}
	}
	payload.Set("assignees", assignees)

	// Metadata (from task entity).
	payload.Set("has_dependencies", len(task.Dependencies) > 0)
	payload.Set("has_context", task.ContextID != nil)
	labels := task.Labels
	if len(labels) == 0 {
		labels = []string{}
	}
	payload.Set("labels", labels)

	// Timestamps (from task entity).
	payload.Set("created_at", timeISOOrNil(task.CreatedAt))
	payload.Set("updated_at", timeISOOrNil(task.UpdatedAt))

	// Optional rich fields (truncated to keep message size reasonable).
	description := task.Description
	if len([]rune(description)) > 200 {
		payload.Set("description", string([]rune(description)[:200])+"...")
	} else {
		payload.Set("description", description)
	}

	return payload
}

// EstimatePayloadSize mirrors WebSocketPayloadBuilder.estimate_payload_size:
// len(json.dumps(payload).encode("utf-8")). PyJSONDumps with indent -1 reproduces the
// default json.dumps separators; an unsupported value yields Python's TypeError, which we
// surface as 0 bytes (the size is unknowable).
func (WebSocketPayloadBuilder) EstimatePayloadSize(payload *entities.OrderedMap[any]) int {
	s, err := value_objects.PyJSONDumps(payload, -1)
	if err != nil {
		return 0
	}
	return len([]byte(s))
}

// BuildLightweightPayload mirrors WebSocketPayloadBuilder.build_lightweight_payload.
func (WebSocketPayloadBuilder) BuildLightweightPayload(
	task *entities.Task,
	taskResponse *taskdtos.TaskResponse,
) *entities.OrderedMap[any] {
	return WebSocketPayloadBuilder{}.BuildTaskPayload(task, taskResponse, false)
}

// -- local helpers (unique names to avoid colliding with the services package) --

func taskIDString(task *entities.Task) string {
	if task == nil || task.ID == nil {
		return "None"
	}
	return task.ID.Value
}

func taskStatusString(task *entities.Task) string {
	if task == nil || task.Status == nil {
		return "None"
	}
	return task.Status.Value
}

func taskPriorityString(task *entities.Task) string {
	if task == nil || task.Priority == nil {
		return "None"
	}
	return task.Priority.Value
}

func ptrStringOrNil(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

func timeISOOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return value_objects.IsoFormat(*t)
}
