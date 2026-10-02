// This file ports task_management/application/use_cases/get_project.py.
package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GetProjectUseCase retrieves a project by ID and builds the JSON response dict.
type GetProjectUseCase struct {
	projectRepository repositories.ProjectRepository
}

// NewGetProjectUseCase builds the use case around a project repository.
func NewGetProjectUseCase(projectRepository repositories.ProjectRepository) *GetProjectUseCase {
	return &GetProjectUseCase{projectRepository: projectRepository}
}

// getProjectBranchFallback builds the 14-key minimal branch dict used by the
// Python per-branch except branch.
func getProjectBranchFallback(treeID string, tree *entities.GitBranch) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	projectID := ""
	name := "unknown"
	if tree != nil {
		projectID = tree.ProjectID
		name = tree.Name
	}
	result.Set("id", treeID)
	result.Set("project_id", projectID)
	result.Set("name", name)
	result.Set("git_branch_name", name)
	result.Set("description", "")
	result.Set("created_at", "")
	result.Set("updated_at", "")
	result.Set("status", "active")
	result.Set("task_count", 0)
	result.Set("completed_tasks", 0)
	result.Set("in_progress_tasks", 0)
	result.Set("blocked_tasks", 0)
	result.Set("todo_tasks", 0)
	result.Set("progress_percentage", 0)
	return result
}

// getProjectBuildGitBranchsDict mirrors _build_git_branchs_dict: an OrderedMap of
// branch_id -> branch OrderedMap in project iteration order.
func getProjectBuildGitBranchsDict(gitBranchs *entities.OrderedMap[*entities.GitBranch]) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	if gitBranchs == nil {
		return result
	}
	for _, treeID := range gitBranchs.Keys() {
		tree, _ := gitBranchs.Get(treeID)
		// Python's outer except catches AttributeErrors raised while reading the
		// branch. The only unwinding cases in Go are a nil branch or missing
		// timestamps; both fall back to the same minimal dict.
		if tree == nil || tree.CreatedAt == nil || tree.UpdatedAt == nil {
			result.Set(treeID, getProjectBranchFallback(treeID, tree))
			continue
		}

		treeStatus := tree.GetTreeStatus()
		statusBreakdown := map[string]int{}
		if sb, ok := treeStatus["status_breakdown"].(map[string]int); ok {
			statusBreakdown = sb
		}

		gitBranchName := tree.Name
		if tree.GitBranchName != nil && *tree.GitBranchName != "" {
			gitBranchName = *tree.GitBranchName
		}

		// Python: str(tree.status) if hasattr(tree, "status") else "active".
		// GitBranch always has the attribute, so a nil status stringifies to "None".
		status := "None"
		if tree.Status != nil {
			status = tree.Status.Value
		}

		branchID := ""
		if tree.ID != nil {
			branchID = tree.ID.Value
		}

		entry := entities.NewOrderedMap[any]()
		entry.Set("id", branchID)
		entry.Set("project_id", tree.ProjectID)
		entry.Set("name", tree.Name)
		entry.Set("git_branch_name", gitBranchName)
		entry.Set("description", tree.Description)
		entry.Set("created_at", value_objects.IsoFormat(*tree.CreatedAt))
		entry.Set("updated_at", value_objects.IsoFormat(*tree.UpdatedAt))
		entry.Set("status", status)
		entry.Set("task_count", tree.GetTaskCount())
		entry.Set("completed_tasks", tree.GetCompletedTaskCount())
		entry.Set("in_progress_tasks", tree.GetActiveTaskCount())
		entry.Set("blocked_tasks", statusBreakdown["blocked"])
		entry.Set("todo_tasks", statusBreakdown["todo"])
		entry.Set("progress_percentage", tree.GetProgressPercentage())
		result.Set(treeID, entry)
	}
	return result
}

// getProjectRegisteredAgentsDict mirrors the registered_agents dict comprehension.
// Python capabilities is a set (iteration order unspecified); Go emits the
// capabilities in AgentCapabilityValues declaration order (Agent.sortedCapabilities).
func getProjectRegisteredAgentsDict(registeredAgents *entities.OrderedMap[*entities.Agent]) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	if registeredAgents == nil {
		return result
	}
	for _, agentID := range registeredAgents.Keys() {
		agent, _ := registeredAgents.Get(agentID)
		if agent == nil {
			result.Set(agentID, nil)
			continue
		}
		entry := entities.NewOrderedMap[any]()
		id := ""
		if agent.ID != nil {
			id = agent.ID.Value
		}
		entry.Set("id", id)
		entry.Set("name", agent.Name)
		capabilities := []string{}
		for _, capability := range entities.AgentCapabilityValues {
			if _, ok := agent.Capabilities[capability]; ok {
				capabilities = append(capabilities, string(capability))
			}
		}
		entry.Set("capabilities", capabilities)
		createdAt := ""
		if agent.CreatedAt != nil {
			createdAt = value_objects.IsoFormat(*agent.CreatedAt)
		}
		entry.Set("created_at", createdAt)
		result.Set(agentID, entry)
	}
	return result
}

// Execute runs the get-project use case.
func (u *GetProjectUseCase) Execute(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	project, err := u.projectRepository.FindByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project == nil {
		result := entities.NewOrderedMap[any]()
		result.Set("success", false)
		result.Set("error", "Project with ID '"+projectID+"' not found")
		return result, nil
	}

	// Project-level aggregations.
	branchCount := 0
	taskCount := 0
	if project.GitBranchs != nil {
		branchCount = project.GitBranchs.Len()
		for _, tree := range project.GitBranchs.Values() {
			if tree != nil {
				taskCount += tree.GetTaskCount()
			}
		}
	}

	projectIDOut := ""
	if project.ID != nil {
		projectIDOut = project.ID.Value
	}
	createdAt := ""
	if project.CreatedAt != nil {
		createdAt = value_objects.IsoFormat(*project.CreatedAt)
	}
	updatedAt := ""
	if project.UpdatedAt != nil {
		updatedAt = value_objects.IsoFormat(*project.UpdatedAt)
	}

	projectDict := entities.NewOrderedMap[any]()
	projectDict.Set("id", projectIDOut)
	projectDict.Set("name", project.Name)
	projectDict.Set("description", project.Description)
	projectDict.Set("created_at", createdAt)
	projectDict.Set("updated_at", updatedAt)
	projectDict.Set("branch_count", branchCount)
	projectDict.Set("task_count", taskCount)
	projectDict.Set("git_branchs", getProjectBuildGitBranchsDict(project.GitBranchs))
	projectDict.Set("registered_agents", getProjectRegisteredAgentsDict(project.RegisteredAgents))
	if project.AgentAssignments != nil {
		projectDict.Set("agent_assignments", project.AgentAssignments)
	} else {
		projectDict.Set("agent_assignments", nil)
	}
	projectDict.Set("orchestration_status", project.GetOrchestrationStatus())

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("project", projectDict)
	return result, nil
}
