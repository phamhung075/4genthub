// This file ports task_management/application/use_cases/rebalance_agents_use_case.py.
package use_cases

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// RebalanceAgentsUseCase rebalances agent assignments across task trees.
type RebalanceAgentsUseCase struct {
	projectRepository repositories.ProjectRepository
}

// NewRebalanceAgentsUseCase builds the use case around a project repository.
func NewRebalanceAgentsUseCase(projectRepository repositories.ProjectRepository) *RebalanceAgentsUseCase {
	return &RebalanceAgentsUseCase{projectRepository: projectRepository}
}

// rebalanceAgentsError builds Python's {"success": False, "error": msg} result.
func rebalanceAgentsError(message string) (*entities.OrderedMap[any], error) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", message)
	return result, nil
}

// rebalanceProjectAgents mirrors _rebalance_project_agents, preserving the
// Python quirk: `if agent_id not in project.agent_assignments` tests assignment
// KEYS (branch ids) and then writes `agent_assignments[agent_id] = tree_id`,
// reversing the terminal key/value meaning for the new entry.
func rebalanceProjectAgents(project *entities.Project) *entities.OrderedMap[any] {
	changes := []string{}

	availableAgents := []string{}
	if project.RegisteredAgents != nil {
		availableAgents = project.RegisteredAgents.Keys()
	}

	if project.AgentAssignments == nil {
		project.AgentAssignments = entities.NewOrderedMap[string]()
	}

	unassignedTrees := []string{}
	if project.GitBranchs != nil {
		for _, treeID := range project.GitBranchs.Keys() {
			hasAgent := false
			for _, assignedTree := range project.AgentAssignments.Values() {
				if assignedTree == treeID {
					hasAgent = true
					break
				}
			}
			if !hasAgent {
				unassignedTrees = append(unassignedTrees, treeID)
			}
		}
	}

	for i, treeID := range unassignedTrees {
		if i < len(availableAgents) {
			agentID := availableAgents[i]
			if !project.AgentAssignments.Has(agentID) {
				project.AgentAssignments.Set(agentID, treeID)
				changes = append(changes, "Assigned agent "+agentID+" to tree "+treeID)
			}
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("changes_made", len(changes) > 0)
	result.Set("changes", changes)
	return result
}

// Execute runs the rebalance use case. Like Python it never returns an error:
// failures are encoded in the response dict.
func (u *RebalanceAgentsUseCase) Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if projectID != nil && *projectID != "" {
		project, err := u.projectRepository.FindByID(ctx, *projectID)
		if err != nil {
			return rebalanceAgentsError(err.Error())
		}
		if project == nil {
			result := entities.NewOrderedMap[any]()
			result.Set("success", false)
			result.Set("error", "Project "+*projectID+" not found")
			return result, nil
		}

		rebalanceResult := rebalanceProjectAgents(project)
		if changesMade, _ := rebalanceResult.Get("changes_made"); changesMade == true {
			if err := u.projectRepository.Update(ctx, project); err != nil {
				return rebalanceAgentsError(err.Error())
			}
		}

		result := entities.NewOrderedMap[any]()
		result.Set("success", true)
		result.Set("project_id", *projectID)
		result.Set("rebalance_result", rebalanceResult)
		result.Set("message", "Agent rebalancing completed for project "+*projectID)
		return result, nil
	}

	projects, err := u.projectRepository.FindAll(ctx)
	if err != nil {
		return rebalanceAgentsError(err.Error())
	}
	totalChanges := 0
	rebalanceResults := entities.NewOrderedMap[any]()
	for _, project := range projects {
		rebalanceResult := rebalanceProjectAgents(project)
		rebalanceResults.Set(project.GetEntityID(), rebalanceResult)
		if changesMade, _ := rebalanceResult.Get("changes_made"); changesMade == true {
			if changes, ok := rebalanceResult.Get("changes"); ok {
				if list, ok := changes.([]string); ok {
					totalChanges += len(list)
				}
			}
			if err := u.projectRepository.Update(ctx, project); err != nil {
				return rebalanceAgentsError(err.Error())
			}
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("total_changes", totalChanges)
	result.Set("rebalance_results", rebalanceResults)
	result.Set("message", fmt.Sprintf("Agent rebalancing completed for all projects. %d changes made", totalChanges))
	return result, nil
}
