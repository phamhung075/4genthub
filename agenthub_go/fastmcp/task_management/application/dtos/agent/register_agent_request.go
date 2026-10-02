package agent

import (
	"fmt"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RegisterAgentRequest is the request DTO for registering an agent.
type RegisterAgentRequest struct {
	ProjectID string
	AgentID   string
	Name      string
	CallAgent *string
}

// NewRegisterAgentRequest mirrors RegisterAgentRequest.__post_init__: it validates
// project_id and name, auto-generates agent_id when empty, and rejects a
// non-UUID agent_id with the Python format message.
func NewRegisterAgentRequest(projectID string, agentID, name, callAgent *string) (*RegisterAgentRequest, error) {
	if value_objects.PyStrip(projectID) == "" {
		return nil, &value_objects.ValueError{Msg: "Project ID is required"}
	}

	normalizedID, err := validateAndNormalizeAgentID(agentID)
	if err != nil {
		return nil, err
	}

	if name == nil || value_objects.PyStrip(*name) == "" {
		return nil, &value_objects.ValueError{Msg: "Agent name is required"}
	}

	if _, ok := value_objects.PyParseUUID(projectID); !ok {
		return nil, &value_objects.ValueError{Msg: fmt.Sprintf("Project ID '%s' is not a valid UUID", projectID)}
	}

	return &RegisterAgentRequest{ProjectID: projectID, AgentID: normalizedID, Name: *name, CallAgent: callAgent}, nil
}

// validateAndNormalizeAgentID is _validate_and_normalize_agent_id.
func validateAndNormalizeAgentID(agentID *string) (string, error) {
	if agentID == nil || value_objects.PyStrip(*agentID) == "" {
		return value_objects.NewUUIDv4(), nil
	}
	if _, ok := value_objects.PyParseUUID(*agentID); ok {
		return *agentID, nil
	}
	newID := value_objects.NewUUIDv4()
	return "", &value_objects.ValueError{Msg: fmt.Sprintf(
		"AGENT ID FORMAT ERROR: '%s' is not a valid UUID.\n\n"+
			"REQUIREMENT: Agent IDs must be valid UUIDs (Universally Unique Identifiers).\n\n"+
			"VALID UUID FORMAT:\n"+
			"  \u2022 Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx\n"+
			"  \u2022 Example: 4d5935de-d191-4c8f-ba89-802671fba5f6\n"+
			"  \u2022 Length: 36 characters (32 hex digits + 4 hyphens)\n\n"+
			"INVALID EXAMPLES:\n"+
			"  \u2717 'coding-agent-001' (string with hyphens, not UUID)\n"+
			"  \u2717 'agent123' (simple string)\n"+
			"  \u2717 '12345' (number as string)\n\n"+
			"SOLUTIONS:\n"+
			"  1. Use auto-generated UUID: '%s'\n"+
			"  2. Generate your own UUID using standard UUID generators\n"+
			"  3. Omit agent_id parameter to auto-generate (recommended)\n\n"+
			"HOW TO GENERATE UUIDs:\n"+
			"  \u2022 Python: import uuid; str(uuid.uuid4())\n"+
			"  \u2022 Online: https://www.uuidgenerator.net/\n"+
			"  \u2022 Command line: uuidgen (macOS/Linux)",
		*agentID, newID)}
}
