// This file ports task_management/application/use_cases/cleanup_obsolete_use_case.py.
package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// CleanupObsoleteUseCase removes obsolete assignment data from projects.
type CleanupObsoleteUseCase struct {
	projectRepository repositories.ProjectRepository
}

// NewCleanupObsoleteUseCase builds the use case around a project repository.
func NewCleanupObsoleteUseCase(projectRepository repositories.ProjectRepository) *CleanupObsoleteUseCase {
	return &CleanupObsoleteUseCase{projectRepository: projectRepository}
}

// cleanupObsoleteError builds Python's {"success": False, "error": msg} result.
func cleanupObsoleteError(message string) (*entities.OrderedMap[any], error) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", message)
	return result, nil
}

// cleanupObsoleteProjectData mirrors _cleanup_project_data. Note the Python
// variable naming: the first loop unpacks (agent_id, tree_id) from
// agent_assignments, but the dict is actually git_branch_id -> agent_id, so the
// "tree_id" compared against git_branchs is really the agent id. That quirk is
// preserved (keys are deleted literally).
func cleanupObsoleteProjectData(project *entities.Project) []string {
	cleanedItems := []string{}

	// Remove assignments to non-existent trees.
	assignmentsToRemove := []string{}
	if project.AgentAssignments != nil {
		for _, assignmentKey := range project.AgentAssignments.Keys() {
			assignedValue, _ := project.AgentAssignments.Get(assignmentKey)
			if project.GitBranchs == nil || !project.GitBranchs.Has(assignedValue) {
				assignmentsToRemove = append(assignmentsToRemove, assignmentKey)
				cleanedItems = append(cleanedItems,
					"Removed assignment of agent "+assignmentKey+" to non-existent tree "+assignedValue)
			}
		}
	}
	for _, assignmentKey := range assignmentsToRemove {
		project.AgentAssignments.Delete(assignmentKey)
	}

	// Remove unregistered agents from assignments (checks the dict keys).
	unregisteredAgents := []string{}
	if project.AgentAssignments != nil {
		for _, assignmentKey := range project.AgentAssignments.Keys() {
			if project.RegisteredAgents == nil || !project.RegisteredAgents.Has(assignmentKey) {
				unregisteredAgents = append(unregisteredAgents, assignmentKey)
				cleanedItems = append(cleanedItems,
					"Removed unregistered agent "+assignmentKey+" from assignments")
			}
		}
	}
	for _, assignmentKey := range unregisteredAgents {
		project.AgentAssignments.Delete(assignmentKey)
	}

	return cleanedItems
}

// Execute runs the cleanup use case. Like Python it never returns an error:
// failures are encoded in the response dict.
func (u *CleanupObsoleteUseCase) Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if projectID != nil && *projectID != "" {
		project, err := u.projectRepository.FindByID(ctx, *projectID)
		if err != nil {
			return cleanupObsoleteError(err.Error())
		}
		if project == nil {
			result := entities.NewOrderedMap[any]()
			result.Set("success", false)
			result.Set("error", "Project "+*projectID+" not found")
			return result, nil
		}

		cleanedItems := cleanupObsoleteProjectData(project)
		if len(cleanedItems) > 0 {
			if err := u.projectRepository.Update(ctx, project); err != nil {
				return cleanupObsoleteError(err.Error())
			}
		}

		result := entities.NewOrderedMap[any]()
		result.Set("success", true)
		result.Set("project_id", *projectID)
		result.Set("cleaned_items", cleanedItems)
		result.Set("message", "Cleanup completed for project "+*projectID)
		return result, nil
	}

	projects, err := u.projectRepository.FindAll(ctx)
	if err != nil {
		return cleanupObsoleteError(err.Error())
	}
	totalCleaned := 0
	cleanupResults := entities.NewOrderedMap[any]()
	for _, project := range projects {
		cleanedItems := cleanupObsoleteProjectData(project)
		cleanupResults.Set(project.GetEntityID(), cleanedItems)
		totalCleaned += len(cleanedItems)
		if len(cleanedItems) > 0 {
			if err := u.projectRepository.Update(ctx, project); err != nil {
				return cleanupObsoleteError(err.Error())
			}
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("total_cleaned", totalCleaned)
	result.Set("cleanup_results", cleanupResults)
	result.Set("message", fmt.Sprintf("Cleanup completed for all projects. %d items cleaned", totalCleaned))
	return result, nil
}
