package agent

// Agent Workflow Guidance Factory
// (Python workflow_guidance/agent/agent_workflow_factory.py).

import "agenthub/fastmcp/task_management/domain/entities"

// AgentWorkflowGuidance is the minimal view of
// workflow_guidance/agent/agent_workflow_guidance.py. The implementation is
// AgentWorkflowGuidanceImpl (agent_workflow_guidance.go), and its init() ALREADY
// assigns the constructor hook below to build it.
type AgentWorkflowGuidance interface {
	GenerateGuidance(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// NewAgentWorkflowGuidanceFunc constructs an AgentWorkflowGuidance, mirroring
// `AgentWorkflowGuidance()`. Reassigned once agent_workflow_guidance.go exists.
var NewAgentWorkflowGuidanceFunc = func() AgentWorkflowGuidance { return nil }

// AgentWorkflowFactory creates Agent workflow guidance instances.
type AgentWorkflowFactory struct{}

// Create ports the static create().
func (AgentWorkflowFactory) Create() AgentWorkflowGuidance {
	return NewAgentWorkflowGuidanceFunc()
}
