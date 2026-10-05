// Package services ports task_management/infrastructure/services.
package services

import (
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentConverter converts simplified agent data to full Agent entities
// (agent_converter.AgentConverter).
type AgentConverter struct{}

// NewAgentConverter builds a converter (Python's __init__ only creates a logger).
func NewAgentConverter() *AgentConverter { return &AgentConverter{} }

// ConvertSimplifiedAgentToEntity is AgentConverter.convert_simplified_agent_to_entity.
//
// Python constructs Agent(id=agent_data.get("id")), and AgentId rejects non-UUID values,
// so a projects.json id like "coding_agent" raises ValueError here too.
func (c *AgentConverter) ConvertSimplifiedAgentToEntity(agentData map[string]any, projectID string) (*entities.Agent, error) {
	agentID, _ := agentData["id"].(string)
	name, _ := agentData["name"].(string)

	callAgent := ""
	if v, ok := agentData["call_agent"]; ok {
		if s, isString := v.(string); isString {
			callAgent = s
		} else {
			callAgent = value_objects.PyStr(v)
		}
	} else {
		// Python's default f"@{agent_id.replace('_', '-')}-agent".
		callAgent = "@" + strings.ReplaceAll(agentID, "_", "-") + "-agent"
	}

	capabilities, specializations, preferredLanguages := extractAgentDetails(callAgent)

	id, err := value_objects.NewAgentId(agentID)
	if err != nil {
		return nil, err
	}
	now := time.Now().UTC()
	agent := entities.Agent{
		ID:                 &id,
		Name:               name,
		Description:        "Agent " + name + " - " + callAgent,
		Capabilities:       capabilities,
		Specializations:    specializations,
		PreferredLanguages: preferredLanguages,
		Status:             entities.AgentStatusAvailable,
		MaxConcurrentTasks: intPtr(3),
		CurrentWorkload:    0,
		PriorityPreference: "high",
		AssignedProjects:   map[string]struct{}{projectID: {}},
	}
	initialized, err := entities.NewAgent(agent)
	if err != nil {
		return nil, err
	}
	agent = *initialized
	agent.CreatedAt = &now
	agent.UpdatedAt = &now
	if err := agent.Init(&agent); err != nil {
		return nil, err
	}
	return &agent, nil
}

func intPtr(i int) *int { return &i }

// extractAgentDetails is AgentConverter._extract_agent_details.
func extractAgentDetails(callAgent string) (map[entities.AgentCapability]struct{}, []string, []string) {
	agentName := strings.ReplaceAll(strings.TrimLeft(callAgent, "@"), "-", "_")

	type mapping struct {
		capabilities []entities.AgentCapability
		specialized  []string
		languages    []string
	}
	mappings := map[string]mapping{
		"system_architect_agent": {
			capabilities: []entities.AgentCapability{entities.CapabilityArchitecture, entities.CapabilityBackendDevelopment},
			specialized:  []string{"system_design", "architecture_patterns", "scalability"},
			languages:    []string{"python", "java", "typescript"},
		},
		"coding_agent": {
			capabilities: []entities.AgentCapability{entities.CapabilityFrontendDevelopment, entities.CapabilityBackendDevelopment},
			specialized:  []string{"full_stack_development", "api_development", "web_development"},
			languages:    []string{"python", "javascript", "typescript", "html", "css"},
		},
		"documentation_agent": {
			capabilities: []entities.AgentCapability{entities.CapabilityDocumentation},
			specialized:  []string{"technical_writing", "api_documentation", "user_guides"},
			languages:    []string{"markdown", "html"},
		},
		"test_orchestrator_agent": {
			capabilities: []entities.AgentCapability{entities.CapabilityTesting},
			specialized:  []string{"test_automation", "quality_assurance", "integration_testing"},
			languages:    []string{"python", "javascript", "typescript"},
		},
		"devops_agent": {
			capabilities: []entities.AgentCapability{entities.CapabilityDevops},
			specialized:  []string{"ci_cd", "deployment", "infrastructure", "containerization"},
			languages:    []string{"bash", "yaml", "python"},
		},
		"security_auditor_agent": {
			capabilities: []entities.AgentCapability{entities.CapabilitySecurity},
			specialized:  []string{"security_audit", "vulnerability_assessment", "secure_coding"},
			languages:    []string{"python", "bash"},
		},
	}

	m, ok := mappings[agentName]
	if !ok {
		m = mapping{
			capabilities: []entities.AgentCapability{entities.CapabilityBackendDevelopment},
			specialized:  []string{"general_development"},
			languages:    []string{"python"},
		}
	}

	capabilities := map[entities.AgentCapability]struct{}{}
	for _, capability := range m.capabilities {
		capabilities[capability] = struct{}{}
	}
	return capabilities, m.specialized, m.languages
}

// ConvertProjectAgentsToEntities is AgentConverter.convert_project_agents_to_entities.
//
// Python catches any conversion exception, logs it and builds a fallback agent; the
// fallback validates the same id, so an invalid id still surfaces as an error here.
func (c *AgentConverter) ConvertProjectAgentsToEntities(projectData map[string]any) (*entities.OrderedMap[*entities.Agent], error) {
	projectID, _ := projectData["id"].(string)
	registered := mapOfAny(projectData["registered_agents"])

	keys := make([]string, 0, len(registered))
	for k := range registered {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	result := entities.NewOrderedMap[*entities.Agent]()
	for _, agentID := range keys {
		agentData := mapOfAny(registered[agentID])
		entity, err := c.ConvertSimplifiedAgentToEntity(agentData, projectID)
		if err != nil {
			fallback, fbErr := c.createFallbackAgent(agentID, agentData, projectID)
			if fbErr != nil {
				return nil, fbErr
			}
			result.Set(agentID, fallback)
			continue
		}
		result.Set(agentID, entity)
	}
	return result, nil
}

// createFallbackAgent is AgentConverter._create_fallback_agent.
func (c *AgentConverter) createFallbackAgent(agentID string, agentData map[string]any, projectID string) (*entities.Agent, error) {
	name := agentID
	if v, ok := agentData["name"].(string); ok {
		name = v
	}
	id, err := value_objects.NewAgentId(agentID)
	if err != nil {
		return nil, err
	}
	now := time.Now().UTC()
	agent := entities.Agent{
		ID:                 &id,
		Name:               name,
		Description:        "Fallback agent for " + agentID,
		Capabilities:       map[entities.AgentCapability]struct{}{entities.CapabilityBackendDevelopment: {}},
		Specializations:    []string{"general_development"},
		PreferredLanguages: []string{"python"},
		Status:             entities.AgentStatusAvailable,
		MaxConcurrentTasks: intPtr(1),
		CurrentWorkload:    0,
		AssignedProjects:   map[string]struct{}{projectID: {}},
	}
	initialized, err := entities.NewAgent(agent)
	if err != nil {
		return nil, err
	}
	agent = *initialized
	agent.CreatedAt = &now
	agent.UpdatedAt = &now
	if err := agent.Init(&agent); err != nil {
		return nil, err
	}
	return &agent, nil
}

// UpdateAgentAssignments is AgentConverter.update_agent_assignments.
func (c *AgentConverter) UpdateAgentAssignments(agentEntities *entities.OrderedMap[*entities.Agent], agentAssignments map[string]string) error {
	keys := make([]string, 0, len(agentAssignments))
	for k := range agentAssignments {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, gitBranchName := range keys {
		agentID := agentAssignments[gitBranchName]
		if entity, ok := agentEntities.Get(agentID); ok {
			if err := entity.AssignToTree(gitBranchName); err != nil {
				return err
			}
		}
	}
	return nil
}

// mapOfAny coerces a decoded JSON/YAML value to a map, defaulting to an empty one.
func mapOfAny(v any) map[string]any {
	switch x := v.(type) {
	case map[string]any:
		return x
	case *entities.OrderedMap[any]:
		out := map[string]any{}
		for _, k := range x.Keys() {
			val, _ := x.Get(k)
			out[k] = val
		}
		return out
	}
	return map[string]any{}
}
