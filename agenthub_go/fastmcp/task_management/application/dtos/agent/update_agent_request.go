package agent

import "agenthub/fastmcp/task_management/domain/value_objects"

// UpdateAgentRequest is the request DTO for updating agent information.
type UpdateAgentRequest struct {
	ProjectID string
	AgentID   string
	Name      *string
	CallAgent *string
	UserID    *string
}

// Validate mirrors UpdateAgentRequest.validate.
func (r *UpdateAgentRequest) Validate() error {
	if r.ProjectID == "" {
		return &value_objects.ValueError{Msg: "project_id is required"}
	}
	if r.AgentID == "" {
		return &value_objects.ValueError{Msg: "agent_id is required"}
	}
	nameEmpty := r.Name == nil || *r.Name == ""
	callAgentEmpty := r.CallAgent == nil || *r.CallAgent == ""
	if nameEmpty && callAgentEmpty {
		return &value_objects.ValueError{Msg: "At least one field to update must be provided"}
	}
	return nil
}
