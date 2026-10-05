package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ListProjectsUseCase ports list_projects.ListProjectsUseCase.
type ListProjectsUseCase struct {
	projectRepository repositories.ProjectRepository
}

// NewListProjectsUseCase builds the use case.
func NewListProjectsUseCase(projectRepository repositories.ProjectRepository) *ListProjectsUseCase {
	return &ListProjectsUseCase{projectRepository: projectRepository}
}

// Execute ports execute(): the returned dict keeps the Python key order.
func (uc *ListProjectsUseCase) Execute(ctx context.Context, includeBranches bool) (*entities.OrderedMap[any], error) {
	projects, err := uc.projectRepository.FindAll(ctx)
	if err != nil {
		return nil, err
	}

	projectList := make([]any, 0, len(projects))
	for _, project := range projects {
		branchCount := project.GitBranchs.Len()
		taskCount := 0
		for _, tree := range project.GitBranchs.Values() {
			taskCount += tree.GetTaskCount()
		}

		info := entities.NewOrderedMap[any]()
		info.Set("id", projectIDStr(project))
		info.Set("name", project.Name)
		info.Set("description", project.Description)
		info.Set("created_at", projectCreatedAt(project))
		info.Set("updated_at", projectUpdatedAt(project))
		info.Set("branch_count", branchCount)
		info.Set("task_count", taskCount)
		info.Set("registered_agents_count", project.RegisteredAgents.Len())
		info.Set("active_assignments", project.AgentAssignments.Len())
		info.Set("active_sessions", project.ActiveWorkSessions.Len())

		if includeBranches && project.GitBranchs.Len() > 0 {
			branches := entities.NewOrderedMap[any]()
			for _, branchID := range project.GitBranchs.Keys() {
				branch, _ := project.GitBranchs.Get(branchID)
				branches.Set(branchID, listProjectsBranchDict(branch))
			}
			info.Set("git_branchs", branches)
		}
		projectList = append(projectList, info)
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("projects", projectList)
	result.Set("count", len(projectList))
	return result, nil
}

func projectIDStr(p *entities.Project) string {
	if p.ID == nil {
		return "None"
	}
	return p.ID.Value
}

func projectCreatedAt(p *entities.Project) string {
	if p.CreatedAt == nil {
		return ""
	}
	return value_objects.IsoFormat(*p.CreatedAt)
}

func projectUpdatedAt(p *entities.Project) string {
	if p.UpdatedAt == nil {
		return ""
	}
	return value_objects.IsoFormat(*p.UpdatedAt)
}

// listProjectsBranchDict ports the inline branch dict. The Python
// `isinstance(t, dict)` status counts are always false for Task objects, so the
// four counters and the progress percentage stay 0 (quirk preserved).
func listProjectsBranchDict(branch *entities.GitBranch) *entities.OrderedMap[any] {
	branchTaskCount := branch.AllTasks.Len()
	branchCompleted := 0
	branchInProgress := 0
	branchBlocked := 0
	branchTodo := 0
	branchProgress := 0

	gitBranchName := branch.Name
	if branch.GitBranchName != nil && *branch.GitBranchName != "" {
		gitBranchName = *branch.GitBranchName
	}
	status := "None"
	if branch.Status != nil {
		status = branch.Status.String()
	}

	branchIDStr := "None"
	if branch.ID != nil {
		branchIDStr = branch.ID.Value
	}

	dict := entities.NewOrderedMap[any]()
	dict.Set("id", branchIDStr)
	dict.Set("project_id", branch.ProjectID)
	dict.Set("name", branch.Name)
	dict.Set("git_branch_name", gitBranchName)
	dict.Set("description", branch.Description)
	dict.Set("created_at", branchCreatedAt(branch))
	dict.Set("updated_at", branchUpdatedAt(branch))
	dict.Set("status", status)
	dict.Set("task_count", branchTaskCount)
	dict.Set("completed_tasks", branchCompleted)
	dict.Set("in_progress_tasks", branchInProgress)
	dict.Set("blocked_tasks", branchBlocked)
	dict.Set("todo_tasks", branchTodo)
	dict.Set("progress_percentage", branchProgress)
	// Python has no agent_assignments attribute, so len(...) is 0.
	dict.Set("agent_assignments", 0)
	return dict
}

func branchCreatedAt(branch *entities.GitBranch) string {
	if branch.CreatedAt == nil {
		return ""
	}
	return value_objects.IsoFormat(*branch.CreatedAt)
}

func branchUpdatedAt(branch *entities.GitBranch) string {
	if branch.UpdatedAt == nil {
		return ""
	}
	return value_objects.IsoFormat(*branch.UpdatedAt)
}
