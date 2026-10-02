package types

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// A completed-subtask result without title/status/priority (the Python
// `SubtaskObj(subtask_dict)` path) converts with getattr defaults, not KeyError.
func TestSubtaskToDTOAttrObjectUsesGetattrDefaults(t *testing.T) {
	d := entities.NewOrderedMap[any]()
	d.Set("id", "s1")
	dto, err := SubtaskToDTO(AttrObject{Dict: d})
	if err != nil {
		t.Fatal(err)
	}
	if dto.Title != "" || dto.Status != "todo" || dto.Priority != "medium" || dto.TaskID != "" {
		t.Fatalf("%+v", dto)
	}
}
