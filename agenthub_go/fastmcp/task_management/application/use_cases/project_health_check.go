package use_cases

import (
	"context"
	"fmt"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProjectHealthCheckUseCase ports project_health_check.ProjectHealthCheckUseCase.
type ProjectHealthCheckUseCase struct {
	projectRepository repositories.ProjectRepository
}

// NewProjectHealthCheckUseCase mirrors __init__(project_repository).
func NewProjectHealthCheckUseCase(projectRepository repositories.ProjectRepository) *ProjectHealthCheckUseCase {
	return &ProjectHealthCheckUseCase{projectRepository: projectRepository}
}

// projectHealthError builds {"success": False, "error": msg}.
func projectHealthError(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// Execute mirrors ProjectHealthCheckUseCase.execute. projectID nil means Python None.
func (u *ProjectHealthCheckUseCase) Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if projectID != nil && *projectID != "" {
		project, err := u.projectRepository.FindByID(ctx, *projectID)
		if err != nil {
			return nil, err
		}
		if project == nil {
			return projectHealthError(fmt.Sprintf("Project with ID '%s' not found", *projectID)), nil
		}

		result := entities.NewOrderedMap[any]()
		result.Set("success", true)
		result.Set("project_id", *projectID)
		result.Set("health_status", u.checkProjectHealth(project))
		result.Set("message", fmt.Sprintf("Health check completed for project '%s'", *projectID))
		return result, nil
	}

	projects, err := u.projectRepository.FindAll(ctx)
	if err != nil {
		return nil, err
	}

	healthResults := entities.NewOrderedMap[any]()
	overallHealth := "healthy"
	for _, project := range projects {
		healthStatus := u.checkProjectHealth(project)
		healthResults.Set(project.ID.Value, healthStatus)
		if status, _ := healthStatus.Get("status"); status != "healthy" {
			overallHealth = "warning"
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("overall_health", overallHealth)
	result.Set("project_health", healthResults)
	result.Set("total_projects", len(projects))
	result.Set("message", "Health check completed for all projects")
	return result, nil
}

// checkProjectHealth mirrors _check_project_health. checked_at uses datetime.now(UTC).
func (u *ProjectHealthCheckUseCase) checkProjectHealth(project *entities.Project) *entities.OrderedMap[any] {
	issues := []string{}
	warnings := []string{}

	if project.GitBranchs.Len() == 0 {
		warnings = append(warnings, "No task trees defined")
	}

	if project.CrossTreeDependencies.Len() > 0 {
		if u.hasCircularDependencies(project.CrossTreeDependencies) {
			issues = append(issues, "Circular dependencies detected in cross-tree dependencies")
		}
	}

	for _, branchName := range project.AgentAssignments.Keys() {
		agentID, _ := project.AgentAssignments.Get(branchName)
		if !project.RegisteredAgents.Has(agentID) {
			issues = append(issues, fmt.Sprintf("Agent '%s' assigned to tree '%s' but not registered", agentID, branchName))
		}
		if !project.GitBranchs.Has(branchName) {
			issues = append(issues, fmt.Sprintf("Agent '%s' assigned to non-existent tree '%s'", agentID, branchName))
		}
	}

	for _, sessionID := range project.ActiveWorkSessions.Keys() {
		session, _ := project.ActiveWorkSessions.Get(sessionID)
		if !project.RegisteredAgents.Has(session.AgentID) {
			issues = append(issues, fmt.Sprintf("Active work session '%s' references unregistered agent '%s'", sessionID, session.AgentID))
		}
	}

	for _, resource := range project.ResourceLocks.Keys() {
		agentID, _ := project.ResourceLocks.Get(resource)
		if !project.RegisteredAgents.Has(agentID) {
			issues = append(issues, fmt.Sprintf("Resource '%s' locked by unregistered agent '%s'", resource, agentID))
		}
	}

	status := "healthy"
	if len(issues) > 0 {
		status = "critical"
	} else if len(warnings) > 0 {
		status = "warning"
	}

	crossTreeDeps := 0
	for _, deps := range project.CrossTreeDependencies.Values() {
		if deps != nil {
			crossTreeDeps += deps.Len()
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("status", status)
	result.Set("issues", issues)
	result.Set("warnings", warnings)
	result.Set("checked_at", value_objects.IsoFormat(time.Now().UTC().Truncate(time.Microsecond)))
	result.Set("registered_agents_count", project.RegisteredAgents.Len())
	result.Set("active_assignments", project.AgentAssignments.Len())
	result.Set("active_sessions", project.ActiveWorkSessions.Len())
	result.Set("cross_tree_dependencies", crossTreeDeps)
	return result
}

// hasCircularDependencies mirrors _has_circular_dependencies (recursive DFS).
func (u *ProjectHealthCheckUseCase) hasCircularDependencies(dependencies *entities.OrderedMap[*entities.StringSet]) bool {
	visited := map[string]bool{}
	recStack := map[string]bool{}

	var dfs func(node string) bool
	dfs = func(node string) bool {
		if recStack[node] {
			return true
		}
		if visited[node] {
			return false
		}
		visited[node] = true
		recStack[node] = true

		if neighbors, ok := dependencies.Get(node); ok && neighbors != nil {
			for _, neighbor := range neighbors.Items() {
				if dfs(neighbor) {
					return true
				}
			}
		}

		delete(recStack, node)
		return false
	}

	for _, node := range dependencies.Keys() {
		if !visited[node] {
			if dfs(node) {
				return true
			}
		}
	}
	return false
}
