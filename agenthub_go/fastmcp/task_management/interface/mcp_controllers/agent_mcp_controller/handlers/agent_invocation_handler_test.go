package handlers

// Expectations taken from Python
// task_management/interface/mcp_controllers/agent_mcp_controller/handlers/agent_invocation_handler.py

import (
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type stubCallAgentUseCase struct {
	calledWith string
}

func (s *stubCallAgentUseCase) Execute(nameAgent string) *entities.OrderedMap[any] {
	s.calledWith = nameAgent
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("system_prompt", "prompt-for-"+nameAgent)
	return m
}

func TestInvokeAgentMissingName(t *testing.T) {
	h := NewAgentInvocationHandler(&stubCallAgentUseCase{})

	got := h.InvokeAgent("", []string{"coding-agent"})

	wantKeys := []string{"success", "error", "error_code", "field", "expected", "hint", "available_agents"}
	if !reflect.DeepEqual(got.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", got.Keys(), wantKeys)
	}
	if v, _ := got.Get("error"); v != "Missing required field: name_agent" {
		t.Errorf("error = %v", v)
	}
	if v, _ := got.Get("error_code"); v != "MISSING_FIELD" {
		t.Errorf("error_code = %v", v)
	}
	if v, _ := got.Get("field"); v != "name_agent" {
		t.Errorf("field = %v", v)
	}
	if v, _ := got.Get("hint"); v != "Include 'name_agent' in your request body" {
		t.Errorf("hint = %v", v)
	}
	if !reflect.DeepEqual(got.GetAny("available_agents"), []string{"coding-agent"}) {
		t.Errorf("available_agents = %v", got.GetAny("available_agents"))
	}
}

func TestInvokeAgentDelegatesToUseCase(t *testing.T) {
	uc := &stubCallAgentUseCase{}
	h := NewAgentInvocationHandler(uc)

	got := h.InvokeAgent("coding-agent", []string{"coding-agent"})

	if uc.calledWith != "coding-agent" {
		t.Errorf("use case called with %q", uc.calledWith)
	}
	if v, _ := got.Get("success"); v != true {
		t.Errorf("success = %v", v)
	}
	if v, _ := got.Get("system_prompt"); v != "prompt-for-coding-agent" {
		t.Errorf("system_prompt = %v", v)
	}
}
