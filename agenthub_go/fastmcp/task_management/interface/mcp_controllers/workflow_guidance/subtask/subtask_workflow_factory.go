package subtask

// Subtask workflow guidance factory
// (Python workflow_guidance/subtask/subtask_workflow_factory.py).

import "agenthub/fastmcp/task_management/domain/entities"

// SubtaskWorkflowFactory is the factory for subtask workflow guidance instances.
type SubtaskWorkflowFactory struct{}

// Create ports the static create().
func (SubtaskWorkflowFactory) Create() *SubtaskWorkflowGuidance {
	return &SubtaskWorkflowGuidance{}
}

// CreateWithConfig ports create_with_config; config is currently unused.
func (SubtaskWorkflowFactory) CreateWithConfig(config *entities.OrderedMap[any]) *SubtaskWorkflowGuidance {
	return &SubtaskWorkflowGuidance{}
}
