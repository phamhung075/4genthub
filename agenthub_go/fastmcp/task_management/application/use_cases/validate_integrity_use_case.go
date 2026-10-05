package use_cases

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
)

// ValidateIntegrityUseCase ports validate_integrity_use_case.ValidateIntegrityUseCase.
type ValidateIntegrityUseCase struct {
	projectRepo repositories.ProjectRepository
}

// NewValidateIntegrityUseCase builds the use case.
func NewValidateIntegrityUseCase(projectRepo repositories.ProjectRepository) *ValidateIntegrityUseCase {
	return &ValidateIntegrityUseCase{projectRepo: projectRepo}
}

// Execute ports execute(). Every failure is folded into {"success": false, "error": ...}.
func (uc *ValidateIntegrityUseCase) Execute(ctx context.Context, projectID *string) *entities.OrderedMap[any] {
	if projectID != nil && *projectID != "" {
		project, err := uc.projectRepo.FindByID(ctx, *projectID)
		if err != nil {
			return validateIntegrityError(err.Error())
		}
		if project == nil {
			return validateIntegrityError("Project " + *projectID + " not found")
		}
		validationResult := validateProjectIntegrity(project)
		result := entities.NewOrderedMap[any]()
		result.Set("success", true)
		result.Set("project_id", *projectID)
		result.Set("validation_result", validationResult)
		result.Set("message", "Integrity validation completed for project "+*projectID)
		return result
	}

	projects, err := uc.projectRepo.FindAll(ctx)
	if err != nil {
		return validateIntegrityError(err.Error())
	}
	validationResults := entities.NewOrderedMap[any]()
	overallValid := true
	for _, project := range projects {
		validationResult := validateProjectIntegrity(project)
		validationResults.Set(projectIDStr(project), validationResult)
		if v, _ := validationResult.Get("is_valid"); !v.(bool) {
			overallValid = false
		}
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("overall_valid", overallValid)
	result.Set("validation_results", validationResults)
	result.Set("total_projects", len(projects))
	result.Set("message", "Integrity validation completed for all projects")
	return result
}

func validateIntegrityError(msg string) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	result.Set("success", false)
	result.Set("error", msg)
	return result
}

// validateProjectIntegrity ports _validate_project_integrity. As in Python,
// tree.project_id is a plain string while project.id is a ProjectId value object,
// so the id comparison never holds and every branch reports "incorrect project_id".
func validateProjectIntegrity(project *entities.Project) *entities.OrderedMap[any] {
	errorsList := []string{}
	warnings := []string{}

	if project.ID == nil {
		errorsList = append(errorsList, "Project missing ID")
	}
	if project.Name == "" {
		errorsList = append(errorsList, "Project missing name")
	}

	for _, treeID := range project.GitBranchs.Keys() {
		tree, _ := project.GitBranchs.Get(treeID)
		if tree.Name == "" {
			errorsList = append(errorsList, "Task tree "+treeID+" missing name")
		}
		errorsList = append(errorsList, "Task tree "+treeID+" has incorrect project_id")
	}

	// Python names the loop variables agent_id/tree_id, but agent_assignments maps
	// git_branch_id -> agent_id; keep the swapped checks.
	for _, agentID := range project.AgentAssignments.Keys() {
		treeID, _ := project.AgentAssignments.Get(agentID)
		if !project.RegisteredAgents.Has(agentID) {
			errorsList = append(errorsList, "Agent "+agentID+" assigned but not registered")
		}
		if !project.GitBranchs.Has(treeID) {
			errorsList = append(errorsList, "Agent "+agentID+" assigned to non-existent tree "+treeID)
		}
	}

	for _, agentID := range project.RegisteredAgents.Keys() {
		agent, _ := project.RegisteredAgents.Get(agentID)
		if agent.Name == "" {
			warnings = append(warnings, "Agent "+agentID+" missing name")
		}
	}

	result := entities.NewOrderedMap[any]()
	result.Set("is_valid", len(errorsList) == 0)
	result.Set("errors", errorsList)
	result.Set("warnings", warnings)
	return result
}
