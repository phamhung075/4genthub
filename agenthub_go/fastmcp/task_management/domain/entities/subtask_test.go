package entities

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestSubtaskBehaviour(t *testing.T) {
	id, parent := value_objects.GenerateNewTaskId(), value_objects.GenerateNewTaskId()
	st, err := CreateSubtask(id, "s", "d", parent, nil, nil, SubtaskOptions{Assignees: []string{"coding-agent", " ", "@x"}})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(st.Assignees, ",") != "@coding-agent,@x" {
		t.Fatalf("assignees %v", st.Assignees)
	}
	if err := st.UpdateProgressPercentage(50); err != nil || st.Status.Value != "in_progress" {
		t.Fatalf("progress: %v %v", err, st.Status)
	}
	if err := st.UpdateProgressPercentage(101); err == nil || err.Error() != "Progress percentage must be integer between 0-100, got: 101" {
		t.Fatalf("pct err %v", err)
	}
	if err := st.Complete(); err != nil || !st.IsCompleted() || st.ProgressPercentage != 100 {
		t.Fatal("complete")
	}
	_ = st.Reopen()
	if st.Status.Value != "todo" || st.ProgressPercentage != 100 || !st.IsCompleted() {
		t.Fatal("reopen leaves progress 100")
	}
	ev := st.GetEvents()
	last := ev[len(ev)-1].(events.TaskUpdatedEvent)
	if last.TaskID != parent.Value || len(st.Events) != 0 {
		t.Fatal("events")
	}
	if _, err := NewSubtask(Subtask{Title: "x", Description: "d"}); err == nil || err.Error() != "Subtask must have a parent task ID" {
		t.Fatalf("parent: %v", err)
	}
}

// NewSubtask judges the assignees it is given; RestoreSubtask, used for stored rows,
// does not.
func TestRestoreSubtaskKeepsAStoredBareNameThatNewSubtaskRefuses(t *testing.T) {
	parent := value_objects.GenerateNewTaskId()
	in := Subtask{Title: "s", Description: "d", ParentTaskID: &parent, Assignees: []string{"go-dev"}}
	if _, err := NewSubtask(in); err == nil {
		t.Fatal("NewSubtask must refuse a bare name that is no role")
	}
	got, err := RestoreSubtask(in)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(got.Assignees, ",") != "go-dev" {
		t.Fatalf("assignees = %v", got.Assignees)
	}
}

func TestSubtaskAddAssigneeUsesTheOneRule(t *testing.T) {
	parent := value_objects.GenerateNewTaskId()
	st, err := NewSubtask(Subtask{Title: "s", Description: "d", ParentTaskID: &parent})
	if err != nil {
		t.Fatal(err)
	}
	if err := st.AddAssignee("coding-agent"); err != nil {
		t.Fatal(err)
	}
	if err := st.AddAssignee("@go-dev"); err != nil {
		t.Fatal(err)
	}
	if err := st.AddAssignee("@go-dev"); err != nil {
		t.Fatal(err)
	}
	if strings.Join(st.Assignees, ",") != "@coding-agent,@go-dev" {
		t.Fatalf("assignees = %v", st.Assignees)
	}
	if err := st.AddAssignee("go-dev"); err == nil {
		t.Fatal("a bare name that is no role must be refused")
	}
	if strings.Join(st.Assignees, ",") != "@coding-agent,@go-dev" {
		t.Fatalf("a refused add must change nothing: %v", st.Assignees)
	}
}

// What a stored row shows: a known role or '@' name in its '@' form, any other stored
// name as stored, and no assignees as none.
func TestRestoreSubtaskAssigneeForms(t *testing.T) {
	parent := value_objects.GenerateNewTaskId()
	cases := []struct{ in, want []string }{
		{[]string{"go-dev"}, []string{"go-dev"}},
		{[]string{"custom", "@lead"}, []string{"custom", "@lead"}},
		{[]string{"@go-dev"}, []string{"@go-dev"}},
		{[]string{"coding-agent"}, []string{"@coding-agent"}},
		{nil, []string{}},
		{[]string{}, []string{}},
	}
	for _, c := range cases {
		got, err := RestoreSubtask(Subtask{Title: "s", Description: "d", ParentTaskID: &parent, Assignees: c.in})
		if err != nil {
			t.Fatalf("%v: %v", c.in, err)
		}
		if strings.Join(got.Assignees, ",") != strings.Join(c.want, ",") || len(got.Assignees) != len(c.want) {
			t.Errorf("%v restored as %v, want %v", c.in, got.Assignees, c.want)
		}
	}
}
