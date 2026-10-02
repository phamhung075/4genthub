// Package adapters ports task_management/interface/adapters.
package adapters

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/utilities"
)

// AttributeError is Python's AttributeError.
type AttributeError struct{ Msg string }

func (e *AttributeError) Error() string { return e.Msg }

// SimpleMultiAgentProjectService is the project service the adapter delegates to. Python
// types it as ProjectManagementService, but the adapter calls create_project(project_id=...),
// register_agent, assign_agent_to_tree and reads _projects_file/_brain_dir/_agent_converter/
// _orchestrator/_projects, none of which the real ProjectManagementService has: only an
// injected double (as in the tests) satisfies it.
type SimpleMultiAgentProjectService interface {
	CreateProject(projectID, name, description string) *entities.OrderedMap[any]
	RegisterAgent(projectID, agentID, name, callAgent string) *entities.OrderedMap[any]
	GetProject(projectID string) *entities.OrderedMap[any]
	AssignAgentToTree(projectID, agentID, gitBranchName string) *entities.OrderedMap[any]
	ListProjects() *entities.OrderedMap[any]
	ProjectsFile() any
	BrainDir() any
	AgentConverter() any
	Orchestrator() any
	Projects() any
}

// SimpleMultiAgentAdapter is the simplified multi-agent adapter kept for backward compatibility.
type SimpleMultiAgentAdapter struct {
	pathResolver   *utilities.PathResolver
	projectService SimpleMultiAgentProjectService

	// Attributes the Python constructor copies from the project service for tests.
	ProjectsFile   any
	BrainDir       any
	AgentConverter any
	Orchestrator   any
}

// NewSimpleMultiAgentAdapter mirrors __init__(projects_file_path, path_resolver, project_service).
// Without an injected project service Python builds ProjectManagementService(path_resolver,
// projects_file_path), which lacks _projects_file, so the constructor raises AttributeError.
func NewSimpleMultiAgentAdapter(pathResolver *utilities.PathResolver, projectService SimpleMultiAgentProjectService) (*SimpleMultiAgentAdapter, error) {
	if pathResolver == nil {
		resolver, err := utilities.NewPathResolver()
		if err != nil {
			return nil, err
		}
		pathResolver = resolver
	}
	if projectService == nil {
		return nil, &AttributeError{Msg: "'ProjectManagementService' object has no attribute '_projects_file'"}
	}
	return &SimpleMultiAgentAdapter{
		pathResolver:   pathResolver,
		projectService: projectService,
		ProjectsFile:   projectService.ProjectsFile(),
		BrainDir:       projectService.BrainDir(),
		AgentConverter: projectService.AgentConverter(),
		Orchestrator:   projectService.Orchestrator(),
	}, nil
}

// CreateProject is create_project (description defaults to "Project: <name>").
func (a *SimpleMultiAgentAdapter) CreateProject(projectID, name, description string) *entities.OrderedMap[any] {
	if description == "" {
		description = "Project: " + name
	}
	return a.projectService.CreateProject(projectID, name, description)
}

// RegisterAgent is register_agent (call_agent defaults to "@<agent_id with _ -> ->-agent").
func (a *SimpleMultiAgentAdapter) RegisterAgent(projectID, agentID, name, callAgent string) *entities.OrderedMap[any] {
	if callAgent == "" {
		callAgent = "@" + strings.ReplaceAll(agentID, "_", "-") + "-agent"
	}
	return a.projectService.RegisterAgent(projectID, agentID, name, callAgent)
}

// GetProject is get_project.
func (a *SimpleMultiAgentAdapter) GetProject(projectID string) *entities.OrderedMap[any] {
	return a.projectService.GetProject(projectID)
}

// AssignAgentToTree is assign_agent_to_tree.
func (a *SimpleMultiAgentAdapter) AssignAgentToTree(projectID, agentID, gitBranchName string) *entities.OrderedMap[any] {
	return a.projectService.AssignAgentToTree(projectID, agentID, gitBranchName)
}

// ListProjects is list_projects.
func (a *SimpleMultiAgentAdapter) ListProjects() *entities.OrderedMap[any] {
	return a.projectService.ListProjects()
}

// Projects is the _projects property (internal projects data for tests).
func (a *SimpleMultiAgentAdapter) Projects() any { return a.projectService.Projects() }
