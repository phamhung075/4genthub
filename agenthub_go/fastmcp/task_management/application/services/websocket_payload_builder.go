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

// WebSocketTaskPayloadCap is the per-event size ceiling on payload.data.primary, in bytes of the
// compact JSON a client must hold. PERF-05's ruling: every task event's primary serialises to at
// most 2048 bytes, and a delta that would exceed it becomes {"id", "refetch": true}.
const WebSocketTaskPayloadCap = 2048

// BuildTaskPayload builds the task seed payload a `created` event carries.
//
// task_response is the Python `task_response=None` optional TaskResponse DTO. details is never
// carried: a note is unbounded (a hub task held 41k chars of its own history), so an update names
// it with details_changed and the client refetches it.
func (WebSocketPayloadBuilder) BuildTaskPayload(
	task *entities.Task,
	taskResponse *taskdtos.TaskResponse,
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
	} else {
		payload.Set("project_id", nil)
		payload.Set("git_branch_id", ptrStringOrNil(task.GitBranchID))
		payload.Set("subtask_count", len(task.Subtasks))
		payload.Set("completed_subtasks", 0)
		// Python has no `progress_percentage` attribute on Task, so hasattr is False -> 0.
		payload.Set("progress_percentage", 0)
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

// BuildTaskDelta builds the flat field delta an `updated` or `completed` event carries: id,
// updated_at, and each changed field at the top level of the payload (never a `changed` wrapper).
// A changed field the payload does not carry is omitted; details is never carried, only named by
// details_changed so the client refetches the ledger note.
func (WebSocketPayloadBuilder) BuildTaskDelta(full *entities.OrderedMap[any], changed []string) *entities.OrderedMap[any] {
	delta := entities.NewOrderedMap[any]()
	if full == nil {
		return delta
	}
	id, _ := full.Get("id")
	delta.Set("id", id)
	if updatedAt, ok := full.Get("updated_at"); ok {
		delta.Set("updated_at", updatedAt)
	}
	for _, name := range changed {
		switch name {
		case "id", "updated_at":
			continue
		case "details":
			delta.Set("details_changed", true)
		default:
			if v, ok := full.Get(name); ok {
				delta.Set(name, v)
			}
		}
	}
	return delta
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
