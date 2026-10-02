package agent

import "agenthub/fastmcp/task_management/domain/value_objects"

// AssignAgentRequest is the request DTO for assigning an agent to a git branch.
type AssignAgentRequest struct {
	ProjectID   string
	AgentID     string
	GitBranchID string
	UserID      *string
}

// Validate mirrors AssignAgentRequest.validate.
func (r *AssignAgentRequest) Validate() error {
	if r.ProjectID == "" {
		return &value_objects.ValueError{Msg: "project_id is required"}
	}
	if r.AgentID == "" {
		return &value_objects.ValueError{Msg: "agent_id is required"}
	}
	if r.GitBranchID == "" {
		return &value_objects.ValueError{Msg: "git_branch_id is required"}
	}
	return nil
}
