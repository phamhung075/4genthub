package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

const testAgentUUID = "123e4567-e89b-12d3-a456-426614174000"

func hasCapability(caps map[entities.AgentCapability]struct{}, c entities.AgentCapability) bool {
	_, ok := caps[c]
	return ok
}

func TestExtractAgentDetailsMappings(t *testing.T) {
	cases := []struct {
		callAgent    string
		capabilities []entities.AgentCapability
		specialized  []string
		languages    []string
	}{
		{"@system-architect-agent", []entities.AgentCapability{entities.CapabilityArchitecture, entities.CapabilityBackendDevelopment},
			[]string{"system_design", "architecture_patterns", "scalability"}, []string{"python", "java", "typescript"}},
		{"@coding-agent", []entities.AgentCapability{entities.CapabilityFrontendDevelopment, entities.CapabilityBackendDevelopment},
			[]string{"full_stack_development", "api_development", "web_development"}, []string{"python", "javascript", "typescript", "html", "css"}},
		{"@documentation-agent", []entities.AgentCapability{entities.CapabilityDocumentation},
			[]string{"technical_writing", "api_documentation", "user_guides"}, []string{"markdown", "html"}},
		{"@test-orchestrator-agent", []entities.AgentCapability{entities.CapabilityTesting},
			[]string{"test_automation", "quality_assurance", "integration_testing"}, []string{"python", "javascript", "typescript"}},
		{"@devops-agent", []entities.AgentCapability{entities.CapabilityDevops},
			[]string{"ci_cd", "deployment", "infrastructure", "containerization"}, []string{"bash", "yaml", "python"}},
		{"@security-auditor-agent", []entities.AgentCapability{entities.CapabilitySecurity},
			[]string{"security_audit", "vulnerability_assessment", "secure_coding"}, []string{"python", "bash"}},
	}
	for _, tc := range cases {
		caps, spec, langs := extractAgentDetails(tc.callAgent)
		if len(caps) != len(tc.capabilities) {
			t.Errorf("%s: caps = %v", tc.callAgent, caps)
		}
		for _, c := range tc.capabilities {
			if !hasCapability(caps, c) {
				t.Errorf("%s: missing capability %q", tc.callAgent, c)
			}
		}
		if len(spec) != len(tc.specialized) || spec[0] != tc.specialized[0] || spec[len(spec)-1] != tc.specialized[len(tc.specialized)-1] {
			t.Errorf("%s: specializations = %v", tc.callAgent, spec)
		}
		if len(langs) != len(tc.languages) {
			t.Errorf("%s: languages = %v", tc.callAgent, langs)
		}
	}

	// Unknown agent falls back to backend development / general development / python.
	caps, spec, langs := extractAgentDetails("@unknown-agent")
	if !hasCapability(caps, entities.CapabilityBackendDevelopment) || len(caps) != 1 {
		t.Errorf("default caps = %v", caps)
	}
	if len(spec) != 1 || spec[0] != "general_development" {
		t.Errorf("default specializations = %v", spec)
	}
	if len(langs) != 1 || langs[0] != "python" {
		t.Errorf("default languages = %v", langs)
	}
}

func TestConvertSimplifiedAgentToEntity(t *testing.T) {
	converter := NewAgentConverter()
	agentData := map[string]any{
		"id":         testAgentUUID,
		"name":       "Coding Agent",
		"call_agent": "@coding-agent",
	}
	agent, err := converter.ConvertSimplifiedAgentToEntity(agentData, "project-1")
	if err != nil {
		t.Fatal(err)
	}
	if agent.ID == nil || agent.ID.String() != testAgentUUID {
		t.Fatalf("id = %v", agent.ID)
	}
	if agent.Name != "Coding Agent" {
		t.Fatalf("name = %q", agent.Name)
	}
	if agent.Description != "Agent Coding Agent - @coding-agent" {
		t.Fatalf("description = %q", agent.Description)
	}
	if agent.Status != entities.AgentStatusAvailable {
		t.Fatalf("status = %q", agent.Status)
	}
	if agent.MaxConcurrentTasks == nil || *agent.MaxConcurrentTasks != 3 || agent.CurrentWorkload != 0 {
		t.Fatalf("workload = %v/%v", agent.CurrentWorkload, agent.MaxConcurrentTasks)
	}
	if agent.PriorityPreference != "high" {
		t.Fatalf("priority = %q", agent.PriorityPreference)
	}
	if _, ok := agent.AssignedProjects["project-1"]; !ok {
		t.Fatalf("assigned projects = %v", agent.AssignedProjects)
	}
	if !agent.HasCapability(entities.CapabilityFrontendDevelopment) || !agent.HasCapability(entities.CapabilityBackendDevelopment) {
		t.Fatalf("capabilities = %v", agent.Capabilities)
	}
}

// Python's AgentId validates UUIDs, so a simplified agent id from projects.json such as
// "coding_agent" makes the converter raise ValueError.
func TestConvertSimplifiedAgentToEntityRejectsNonUUID(t *testing.T) {
	_, err := NewAgentConverter().ConvertSimplifiedAgentToEntity(map[string]any{"id": "coding_agent", "name": "Coding Agent"}, "p")
	if err == nil {
		t.Fatal("expected an error for a non-UUID id")
	}
	if err.Error() != "Invalid AgentId format: 'coding_agent'. Expected canonical UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" {
		t.Fatalf("unexpected error: %q", err)
	}
}

func TestConvertProjectAgentsToEntitiesAndAssignments(t *testing.T) {
	converter := NewAgentConverter()
	project := map[string]any{
		"id": "project-9",
		"registered_agents": map[string]any{
			"a": map[string]any{"id": testAgentUUID, "name": "A", "call_agent": "@coding-agent"},
		},
	}
	entitiesMap, err := converter.ConvertProjectAgentsToEntities(project)
	if err != nil {
		t.Fatal(err)
	}
	if entitiesMap.Len() != 1 {
		t.Fatalf("agents = %d", entitiesMap.Len())
	}
	agent, _ := entitiesMap.Get("a")
	if agent.Name != "A" {
		t.Fatalf("agent = %+v", agent)
	}

	if err := converter.UpdateAgentAssignments(entitiesMap, map[string]string{"main": "a", "missing": "b"}); err != nil {
		t.Fatal(err)
	}
	if _, ok := agent.AssignedTrees["main"]; !ok {
		t.Fatalf("assigned trees = %v", agent.AssignedTrees)
	}
}
