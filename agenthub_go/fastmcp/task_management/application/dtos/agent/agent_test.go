package agent

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestRegisterAgentRequestValidation(t *testing.T) {
	if _, err := NewRegisterAgentRequest("", nil, strPtr("n"), nil); err == nil || err.Error() != "Project ID is required" {
		t.Fatalf("empty project err = %v", err)
	}
	if _, err := NewRegisterAgentRequest("p", nil, strPtr("  "), nil); err == nil || err.Error() != "Agent name is required" {
		t.Fatalf("blank name err = %v", err)
	}
	_, err := NewRegisterAgentRequest("4d5935de-d191-4c8f-ba89-802671fba5f6", strPtr("not-a-uuid"), strPtr("n"), nil)
	if err == nil || !strings.HasPrefix(err.Error(), "AGENT ID FORMAT ERROR: 'not-a-uuid' is not a valid UUID.") {
		t.Fatalf("invalid agent id err = %v", err)
	}
}

func TestRegisterAgentRequestAutoID(t *testing.T) {
	project := "4d5935de-d191-4c8f-ba89-802671fba5f6"
	r, err := NewRegisterAgentRequest(project, nil, strPtr("My Agent"), nil)
	if err != nil {
		t.Fatalf("err = %v", err)
	}
	if _, ok := value_objects.PyParseUUID(r.AgentID); !ok {
		t.Fatalf("generated id %q is not a UUID", r.AgentID)
	}
	if len(r.AgentID) != 36 {
		t.Fatalf("generated id = %q", r.AgentID)
	}
}

func TestAgentResponseFromDict(t *testing.T) {
	data := entities.NewOrderedMap[any]()
	data.Set("id", "a")
	data.Set("name", "n")
	data.Set("call_agent", "c")
	data.Set("assignments", []any{"x", "y"})
	r := AgentResponseFromDict(data)
	if r.ID != "a" || r.Name != "n" || r.CallAgent != "c" {
		t.Fatalf("resp = %+v", r)
	}
	if len(r.Assignments) != 2 || r.Assignments[0] != "x" || r.Assignments[1] != "y" {
		t.Fatalf("assignments = %v", r.Assignments)
	}
	empty := AgentResponseFromDict(entities.NewOrderedMap[any]())
	if empty.ID != "" || len(empty.Assignments) != 0 {
		t.Fatalf("empty = %+v", empty)
	}
}

func TestRequestValidators(t *testing.T) {
	if err := (&AssignAgentRequest{ProjectID: ""}).Validate(); err == nil || err.Error() != "project_id is required" {
		t.Fatalf("assign err = %v", err)
	}
	if err := (&UpdateAgentRequest{ProjectID: "p", AgentID: "a"}).Validate(); err == nil || err.Error() != "At least one field to update must be provided" {
		t.Fatalf("update err = %v", err)
	}
	empty := ""
	if err := (&UpdateAgentRequest{ProjectID: "p", AgentID: "a", Name: &empty}).Validate(); err == nil {
		t.Fatalf("update empty name should fail")
	}
}

func TestRegisterAgentResponse(t *testing.T) {
	ok := NewRegisterAgentResponseSuccess(&AgentResponse{ID: "1"}, nil)
	if !ok.Success || ok.Message == nil || *ok.Message != "Agent registered successfully" {
		t.Fatalf("ok = %+v", ok)
	}
	bad := NewRegisterAgentResponseError("e")
	if bad.Success || bad.Error == nil || *bad.Error != "e" {
		t.Fatalf("bad = %+v", bad)
	}
}

func strPtr(s string) *string { return &s }
