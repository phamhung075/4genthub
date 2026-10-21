package repositories

import (
	"encoding/json"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// mustJSON is the fixture's encoder for a json.RawMessage column.
func mustJSON(t *testing.T, value any) json.RawMessage {
	t.Helper()
	body, err := json.Marshal(value)
	if err != nil {
		t.Fatalf("marshal fixture: %v", err)
	}
	return body
}

// The read side of hub task 3c2901c6: a task context whose task_data carries a `metadata` copy of the
// task's own fields (status, priority, labels, assignees, the two timestamps) - which every create before
// the write was removed left in the column - must not serve that copy back. The fields have ONE home: the
// task's columns, which the context read overlay serves as Metadata. No migration runs; the key is dropped
// where it is read, exactly as an absent one would be.
func TestTaskDataMetadataCopyIsNotServedBack(t *testing.T) {
	row := &database.TaskContext{
		TaskData: mustJSON(t, map[string]any{
			"metadata": map[string]any{
				"status":     "todo",
				"priority":   "medium",
				"labels":     []any{"defect"},
				"assignees":  []any{"@go-dev"},
				"created_at": "2026-10-21T00:00:00",
			},
			"task_data": map[string]any{"title": "a task"},
			"progress":  0,
		}),
	}

	context := taskContextRepoToEntity(row)
	if copied, present := context.TaskData["metadata"]; present {
		t.Fatalf("task_data.metadata is still served back: %v", copied)
	}
	if _, present := context.TaskData["task_data"]; !present {
		t.Fatalf("the read dropped task_data itself: %v", context.TaskData)
	}
	if context.Progress != 0 {
		t.Fatalf("progress = %d; it belongs outside task_data", context.Progress)
	}
	// The entity's Metadata comes from the columns, not from the copy under task_data.
	if _, present := context.Metadata["status"]; present {
		t.Fatalf("status reached Metadata from the task_data copy: %v", context.Metadata)
	}
	if _, present := context.Metadata["version"]; !present {
		t.Fatalf("Metadata lost its column-derived keys: %v", context.Metadata)
	}
}
