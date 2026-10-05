package git_branch

// Git Branch Workflow Guidance Factory
// (Python workflow_guidance/git_branch/git_branch_workflow_factory.py).

// GitBranchWorkflowFactory ports GitBranchWorkflowFactory.
type GitBranchWorkflowFactory struct{}

// Create ports the static create().
func (GitBranchWorkflowFactory) Create() *GitBranchWorkflowGuidance {
	return &GitBranchWorkflowGuidance{}
}
