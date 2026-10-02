package task

// Task workflow guidance factory
// (Python workflow_guidance/task/task_workflow_factory.py).

import "agenthub/fastmcp/task_management/domain/entities"

// TaskWorkflowFactory is the factory for task workflow guidance instances.
type TaskWorkflowFactory struct{}

// Create ports the static create().
func (TaskWorkflowFactory) Create() *TaskWorkflowGuidance {
	return NewTaskWorkflowGuidance()
}

// CreateWithConfig ports create_with_config; config is currently unused.
func (TaskWorkflowFactory) CreateWithConfig(config *entities.OrderedMap[any]) *TaskWorkflowGuidance {
	return NewTaskWorkflowGuidance()
}
