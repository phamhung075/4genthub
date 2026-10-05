package value_objects

import (
	"errors"
	"strings"
	"testing"
)

func TestEntityIdNormalizes(t *testing.T) {
	id, err := NewProjectId("  ABCDEF12-3456-7890-ABCD-EF1234567890 ")
	if err != nil || id.Value != "abcdef12-3456-7890-abcd-ef1234567890" {
		t.Fatalf("got %v %v", id, err)
	}
	if id.ToHexFormat() != "abcdef1234567890abcdef1234567890" {
		t.Fatal(id.ToHexFormat())
	}
	hex, _ := NewAgentId("abcdef1234567890abcdef1234567890")
	if hex.Value != "abcdef12-3456-7890-abcd-ef1234567890" {
		t.Fatal(hex.Value)
	}
}

func TestEntityIdErrors(t *testing.T) {
	_, err := NewGitBranchId("   ")
	if err == nil || err.Error() != "GitBranchId cannot be empty or whitespace" {
		t.Fatal(err)
	}
	_, err = NewTemplateId("nope")
	var ve *ValueError
	if !errors.As(err, &ve) || !strings.HasPrefix(err.Error(), "Invalid TemplateId format: 'nope'") {
		t.Fatal(err)
	}
}

func TestTaskIdFormats(t *testing.T) {
	for in, want := range map[string]string{
		"123":                              "123",
		"Task-Abc-12":                      "task-abc-12",
		"ABCDEF1234567890ABCDEF1234567890": "abcdef12-3456-7890-abcd-ef1234567890",
		"abcdef12-3456-7890-abcd-ef1234567890.007": "abcdef12-3456-7890-abcd-ef1234567890.007",
	} {
		id, err := NewTaskId(in)
		if err != nil || id.Value != want {
			t.Errorf("%q -> %q %v, want %q", in, id.Value, err, want)
		}
	}
	if _, err := NewTaskId("bad id!"); err == nil {
		t.Error("expected error")
	}
}

func TestGenerateSubtaskId(t *testing.T) {
	p, _ := NewTaskId("abcdef12-3456-7890-abcd-ef1234567890")
	ps := p.String()
	got := GenerateSubtaskId(p, []string{ps + ".001", ps + ".004", "other.009", ps + ".x"})
	if got.Value != ps+".005" {
		t.Fatal(got.Value)
	}
}

func TestPriority(t *testing.T) {
	if _, err := NewPriority(""); err == nil || err.Error() != "Priority cannot be empty" {
		t.Fatal(err)
	}
	h, _ := PriorityFromString(" high ")
	l, _ := PriorityFromString("")
	if l.Value != "medium" || !h.Gt(l) || h.Order() != 3 || !PriorityCritical().IsHighOrCritical() || PriorityUrgent().IsHighOrCritical() {
		t.Fatal("priority semantics")
	}
}

func TestTaskStatusTransitions(t *testing.T) {
	todo, _ := TaskStatusFromString("")
	if todo.Value != "todo" || !todo.CanTransitionTo("done") || todo.CanTransitionTo("review") {
		t.Fatal("todo transitions")
	}
	arch, _ := NewTaskStatus("archived")
	if arch.GetTransitionErrorMessage("todo") != "Status archived is a final state with no valid transitions." {
		t.Fatal(arch.GetTransitionErrorMessage("todo"))
	}
	blocked, _ := NewTaskStatus("blocked")
	want := "Cannot transition from blocked to done. Valid transitions from blocked: cancelled, in_progress"
	if got := blocked.GetTransitionErrorMessage("done"); got != want {
		t.Fatal(got)
	}
	if _, err := NewTaskStatus("bogus"); err == nil || !strings.HasPrefix(err.Error(), "Invalid task status: bogus. Valid statuses: ") {
		t.Fatal(err)
	}
}

func TestProgressPercentage(t *testing.T) {
	for _, in := range []any{50, "50", 50.9, true} {
		if _, err := ProgressPercentageFromAny(in); err != nil {
			t.Errorf("%v: %v", in, err)
		}
	}
	if p, _ := ProgressPercentageFromAny(50.9); p.Value != 50 {
		t.Error("float should truncate")
	}
	if _, err := ProgressPercentageFromAny(nil); err == nil || err.Error() != "Progress percentage cannot be None" {
		t.Error(err)
	}
	_, err := ProgressPercentageFromAny("abc")
	var te *TypeError
	if !errors.As(err, &te) || err.Error() != "Cannot convert str to progress percentage: abc" {
		t.Error(err)
	}
	if _, err := ProgressPercentageFromAny(101); err == nil || err.Error() != "Progress percentage must be between 0 and 100, got 101" {
		t.Error(err)
	}
}

func TestPaginationOffset(t *testing.T) {
	if r := NewPaginationRequest(3, 10, nil); r.Offset != 20 {
		t.Fatal(r.Offset)
	}
	if r := DefaultPaginationRequest(); r.Page != 1 || r.PageSize != 20 || r.Offset != 0 {
		t.Fatal(r)
	}
}

func TestEntityIdRepeatedUrnPrefix(t *testing.T) {
	if _, err := NewProjectId("urn:urn:abcdef12-3456-7890-abcd-ef1234567890"); err != nil {
		t.Fatal(err) // Python str.replace removes every occurrence
	}
}
