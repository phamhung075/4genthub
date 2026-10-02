package context

// Context Workflow Guidance Factory
// (Python workflow_guidance/context/context_workflow_factory.py).

// ContextWorkflowFactory ports ContextWorkflowFactory.
type ContextWorkflowFactory struct{}

// Create ports the static create().
func (ContextWorkflowFactory) Create() *ContextWorkflowGuidance {
	return &ContextWorkflowGuidance{}
}
