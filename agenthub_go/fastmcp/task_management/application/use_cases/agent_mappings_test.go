package use_cases

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestResolveAgentName(t *testing.T) {
	cases := map[string]string{
		"":                       "",
		"coding-agent":           "coding-agent",
		"@coding-agent":          "coding-agent",
		"tech_spec_agent":        "documentation-agent",
		"tech-spec-agent":        "documentation-agent",
		"unknown-agent":          "unknown-agent",
		"some_thing":             "some-thing-agent",
		"llm-ai-agents-research": "llm-ai-agents-research",
		"agent123":               "agent123",
		"AGENT-Thing":            "agent-thing",
	}
	for in, want := range cases {
		if got := ResolveAgentName(in); got != want {
			t.Fatalf("resolve(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestIsDeprecatedAgent(t *testing.T) {
	if !IsDeprecatedAgent("tech_spec_agent") {
		t.Fatalf("tech_spec_agent should be deprecated")
	}
	if IsDeprecatedAgent("coding-agent") {
		t.Fatalf("coding-agent should not be deprecated")
	}
	if IsDeprecatedAgent("unknown-agent") {
		t.Fatalf("unknown-agent should not be deprecated")
	}
}

func TestResolverRegistered(t *testing.T) {
	if entities.AgentNameResolver == nil {
		t.Fatalf("AgentNameResolver not registered")
	}
	if got := entities.AgentNameResolver("@coding-agent"); got != "coding-agent" {
		t.Fatalf("resolver = %q", got)
	}
}
