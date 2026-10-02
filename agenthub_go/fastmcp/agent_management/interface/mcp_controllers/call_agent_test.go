package mcp_controllers

import (
	"context"
	"testing"

	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

type fakeAuth struct {
	id  string
	err error
}

func (a *fakeAuth) GetAuthenticatedUserID(context.Context, *string, string) (string, error) {
	return a.id, a.err
}

type fakeProvider struct {
	config *tmentities.OrderedMap[any]
	err    error
}

func (p *fakeProvider) GetAgentForCall(context.Context, *amvo.UserId, string) (*tmentities.OrderedMap[any], error) {
	return p.config, p.err
}

func TestCallAgentMCPToolSuccess(t *testing.T) {
	config := tmentities.NewOrderedMap[any]()
	config.Set("name", "Coding Agent")
	config.Set("slug", "coding-agent")
	resp := CallAgentMCPTool(context.Background(), "coding-agent", nil, &fakeAuth{id: "11111111-1111-4111-8111-111111111111"}, &fakeProvider{config: config})
	want := []string{"success", "agent", "source"}
	if keys := resp.Keys(); len(keys) != 3 || keys[0] != want[0] || keys[1] != want[1] || keys[2] != want[2] {
		t.Fatalf("keys = %v", keys)
	}
	if v, _ := resp.Get("success"); v != true {
		t.Errorf("success = %v", v)
	}
	if v, _ := resp.Get("source"); v != "agent-management-system" {
		t.Errorf("source = %v", v)
	}
}

func TestCallAgentMCPToolValueError(t *testing.T) {
	resp := CallAgentMCPTool(context.Background(), "ghost", nil, &fakeAuth{id: "11111111-1111-4111-8111-111111111111"}, &fakeProvider{err: tmvo.ValueErrorf("Agent template not found: ghost")})
	want := []string{"success", "error", "message"}
	if keys := resp.Keys(); len(keys) != 3 || keys[0] != want[0] || keys[1] != want[1] || keys[2] != want[2] {
		t.Fatalf("keys = %v", keys)
	}
	if v, _ := resp.Get("error"); v != "Agent not found: ghost" {
		t.Errorf("error = %v", v)
	}
	if v, _ := resp.Get("message"); v != "Agent template not found: ghost" {
		t.Errorf("message = %v", v)
	}
}

func TestCallAgentMCPToolAuthFailure(t *testing.T) {
	resp := CallAgentMCPTool(context.Background(), "coding-agent", nil, &fakeAuth{err: tmvo.ValueErrorf("no token")}, &fakeProvider{})
	if v, _ := resp.Get("error"); v != "Failed to load agent" {
		t.Errorf("error = %v", v)
	}
	if v, _ := resp.Get("message"); v != "no token" {
		t.Errorf("message = %v", v)
	}
}
