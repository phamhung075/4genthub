package entities

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestSubtaskBehaviour(t *testing.T) {
	id, parent := value_objects.GenerateNewTaskId(), value_objects.GenerateNewTaskId()
	st, err := CreateSubtask(id, "s", "d", parent, nil, nil, SubtaskOptions{Assignees: []string{"coding-agent", " ", "x"}})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(st.Assignees, ",") != "@coding-agent,x" {
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
