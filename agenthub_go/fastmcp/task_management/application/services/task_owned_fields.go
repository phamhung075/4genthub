package services

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// TaskOwnedFieldsFromTask returns the live task's own fields in the shape a task context serves:
// status, priority, labels, assignees, created_at and updated_at. The task entity is their source
// of truth, so both the context sync and the context read overlay take them from here instead of
// from the copy the context record was created with. Nil timestamps are omitted, as in
// sync_task_metadata. estimated_effort is deliberately absent: it belongs to the context's
// objective, which the context owns.
func TaskOwnedFieldsFromTask(task *entities.Task) map[string]any {
	if task == nil {
		return nil
	}
	out := map[string]any{
		"status":    zpTaskCtxSyncStringValue(task.Status),
		"priority":  zpTaskCtxSyncStringValue(task.Priority),
		"labels":    task.Labels,
		"assignees": taskAssigneeHandles(task.Assignees),
	}
	if task.CreatedAt != nil {
		out["created_at"] = value_objects.IsoFormat(*task.CreatedAt)
	}
	if task.UpdatedAt != nil {
		out["updated_at"] = value_objects.IsoFormat(*task.UpdatedAt)
	}
	return out
}

// taskAssigneeHandles mirrors the "@" normalization sync_task_metadata applies, so a handle
// written into a context record and a handle read from the task look the same.
func taskAssigneeHandles(assignees []string) []string {
	out := make([]string, 0, len(assignees))
	for _, a := range assignees {
		if len(a) > 0 && a[0] == '@' {
			out = append(out, a)
			continue
		}
		out = append(out, "@"+a)
	}
	return out
}
