package rule

// Rule Workflow Guidance Factory
// (Python workflow_guidance/rule/rule_workflow_factory.py).

// RuleWorkflowFactory ports RuleWorkflowFactory.
type RuleWorkflowFactory struct{}

// Create ports the static create().
func (RuleWorkflowFactory) Create() *RuleWorkflowGuidance {
	return &RuleWorkflowGuidance{}
}
