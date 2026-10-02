package subtask

import (
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestAddSubtaskRequestValidation(t *testing.T) {
	cases := []struct {
		r    AddSubtaskRequest
		want string
	}{
		{AddSubtaskRequest{Title: ""}, "Title cannot be empty"},
		{AddSubtaskRequest{Title: "   "}, "Title cannot be empty"},
		{AddSubtaskRequest{Title: longString(256)}, "Title too long (maximum 255 characters)"},
		{AddSubtaskRequest{Title: "t", Description: longString(2001)}, "Description too long (maximum 2000 characters)"},
		{AddSubtaskRequest{Title: "t", Assignees: []string{""}}, "Assignee cannot be empty"},
	}
	for _, c := range cases {
		_, err := NewAddSubtaskRequest(c.r)
		if err == nil || err.Error() != c.want {
			t.Fatalf("case %+v: err = %v", c.r, err)
		}
	}
	if _, err := NewAddSubtaskRequest(AddSubtaskRequest{Title: "t", Assignees: []string{"a"}}); err != nil {
		t.Fatalf("valid err = %v", err)
	}
}

func TestCreateSubtaskRequestDefaultsAndValidate(t *testing.T) {
	r, err := NewCreateSubtaskRequest(CreateSubtaskRequest{TaskID: "t", Title: "x"})
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if r.Status == nil || *r.Status != "todo" || r.Priority == nil || *r.Priority != "medium" {
		t.Fatalf("defaults = %+v", r)
	}
	bad := "bad"
	_, err = NewCreateSubtaskRequest(CreateSubtaskRequest{TaskID: "t", Title: "x", Status: &bad})
	if err == nil || err.Error() != "Invalid status: bad" {
		t.Fatalf("bad status err = %v", err)
	}
	if _, err := NewCreateSubtaskRequest(CreateSubtaskRequest{TaskID: "", Title: "x"}); err == nil || err.Error() != "task_id is required" {
		t.Fatalf("empty task err = %v", err)
	}
}

func TestSubtaskInfoToDictNestedQuirk(t *testing.T) {
	inner := SubtaskInfo{ID: 2, Title: "c", Status: value_objects.TaskStatus{Value: "done"}, Priority: value_objects.Priority{Value: "high"}}
	outer := SubtaskInfo{ID: 1, Title: "t", Status: value_objects.TaskStatus{Value: "todo"}, Priority: value_objects.Priority{Value: "medium"}, Subtasks: []SubtaskInfo{inner}}
	m := outer.ToDict()
	if v, _ := m.Get("status"); v != "todo" {
		t.Fatalf("top status = %v", v)
	}
	if v, _ := m.Get("priority"); v != "medium" {
		t.Fatalf("top priority = %v", v)
	}
	nested, _ := m.Get("subtasks")
	list, ok := nested.([]any)
	if !ok || len(list) != 1 {
		t.Fatalf("subtasks = %#v", nested)
	}
	child := list[0].(*entities.OrderedMap[any])
	childStatus, _ := child.Get("status")
	cs, ok := childStatus.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("nested status = %#v", childStatus)
	}
	if v, _ := cs.Get("value"); v != "done" {
		t.Fatalf("nested status value = %v", v)
	}
}

func TestSubtaskResponseToDict(t *testing.T) {
	r := &SubtaskResponse{TaskID: "t", Subtask: entities.NewOrderedMap[any](), Progress: entities.NewOrderedMap[any]()}
	m := r.ToDict(false)
	if !reflect.DeepEqual(m.Keys(), []string{"task_id", "subtask", "progress"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
	r.AgentInheritanceApplied = true
	r.InheritedAssignees = []string{"x"}
	m = r.ToDict(true)
	if !reflect.DeepEqual(m.Keys(), []string{"task_id", "subtask", "progress", "agent_inheritance_applied", "inherited_assignees"}) {
		t.Fatalf("keys = %v", m.Keys())
	}
}

func longString(n int) string {
	b := make([]byte, n)
	for i := range b {
		b[i] = 'a'
	}
	return string(b)
}
