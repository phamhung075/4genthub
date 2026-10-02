package services

// Port of
// agenthub_main/src/fastmcp/task_management/application/services/project_application_service.py
//
// Application service for project management following DDD patterns.

import (
	"context"
	"sort"
	"strconv"

	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpProjectApplicationUserScoped is the minimal optional user-scoping interface
// mirroring the Python `hasattr(repository, "with_user")` branch.
type zpProjectApplicationUserScoped interface {
	WithUser(userID string) repositories.ProjectRepository
}

// ProjectApplicationService mirrors the Python class.
type ProjectApplicationService struct {
	projectRepository repositories.ProjectRepository
	userID            *string

	createProjectUseCase      *use_cases.CreateProjectUseCase
	getProjectUseCase         *use_cases.GetProjectUseCase
	listProjectsUseCase       *use_cases.ListProjectsUseCase
	updateProjectUseCase      *use_cases.UpdateProjectUseCase
	createGitBranchUseCase    *use_cases.CreateGitBranchUseCase
	projectHealthCheckUseCase *use_cases.ProjectHealthCheckUseCase
}

// NewProjectApplicationService mirrors __init__(project_repository, user_id=None).
func NewProjectApplicationService(projectRepository repositories.ProjectRepository, userID *string) *ProjectApplicationService {
	s := &ProjectApplicationService{projectRepository: projectRepository, userID: userID}
	repo := s.userScopedRepository()
	s.createProjectUseCase = use_cases.NewCreateProjectUseCase(repo)
	s.getProjectUseCase = use_cases.NewGetProjectUseCase(repo)
	s.listProjectsUseCase = use_cases.NewListProjectsUseCase(repo)
	s.updateProjectUseCase = use_cases.NewUpdateProjectUseCase(repo)
	s.createGitBranchUseCase = use_cases.NewCreateGitBranchUseCase(repo)
	s.projectHealthCheckUseCase = use_cases.NewProjectHealthCheckUseCase(repo)
	return s
}

// userScopedRepository mirrors _get_user_scoped_repository. Only the
// `with_user` branch is representable; the `user_id`/`session` reconstruction
// branch has no Go analog and returns the repository unchanged.
func (s *ProjectApplicationService) userScopedRepository() repositories.ProjectRepository {
	if s.projectRepository == nil {
		return s.projectRepository
	}
	if s.userID != nil {
		if scoped, ok := s.projectRepository.(zpProjectApplicationUserScoped); ok {
			return scoped.WithUser(*s.userID)
		}
	}
	return s.projectRepository
}

// WithUser mirrors with_user.
func (s *ProjectApplicationService) WithUser(userID string) *ProjectApplicationService {
	return NewProjectApplicationService(s.projectRepository, &userID)
}

// CreateProject mirrors create_project.
func (s *ProjectApplicationService) CreateProject(ctx context.Context, projectID, name, description string) (*entities.OrderedMap[any], error) {
	return s.createProjectUseCase.Execute(ctx, &projectID, &name, description)
}

// GetProject mirrors get_project.
func (s *ProjectApplicationService) GetProject(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	return s.getProjectUseCase.Execute(ctx, projectID)
}

// ListProjects mirrors list_projects. Python's use case defaults
// include_branches=True, and the service calls execute() with no argument.
func (s *ProjectApplicationService) ListProjects(ctx context.Context) (*entities.OrderedMap[any], error) {
	return s.listProjectsUseCase.Execute(ctx, true)
}

// UpdateProject mirrors update_project.
func (s *ProjectApplicationService) UpdateProject(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error) {
	return s.updateProjectUseCase.Execute(ctx, projectID, name, description)
}

// CreateGitBranch mirrors create_git_branch.
func (s *ProjectApplicationService) CreateGitBranch(ctx context.Context, projectID, gitBranchName, treeName, treeDescription string) (*entities.OrderedMap[any], error) {
	return s.createGitBranchUseCase.Execute(ctx, projectID, gitBranchName, treeName, treeDescription)
}

// ProjectHealthCheck mirrors project_health_check.
func (s *ProjectApplicationService) ProjectHealthCheck(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	return s.projectHealthCheckUseCase.Execute(ctx, projectID)
}

// RegisterAgent mirrors register_agent.
func (s *ProjectApplicationService) RegisterAgent(ctx context.Context, projectID, agentID, name string, capabilities []string) *entities.OrderedMap[any] {
	project, err := s.userScopedRepository().FindByID(ctx, projectID)
	if err != nil || project == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Project with ID '"+projectID+"' not found")
		return out
	}

	agentCapabilities := map[entities.AgentCapability]struct{}{}
	if capabilities != nil {
		for _, cap := range capabilities {
			if _, ok := value_objects.GetRoleBySlug(cap); ok {
				agentCapabilities[entities.AgentCapability(cap)] = struct{}{}
			}
		}
	}

	agentIDValue, idErr := value_objects.NewAgentId(agentID)
	if idErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", idErr.Error())
		return out
	}
	agent, agentErr := entities.NewAgent(entities.Agent{
		ID:           &agentIDValue,
		Name:         name,
		Capabilities: agentCapabilities,
	})
	if agentErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", agentErr.Error())
		return out
	}

	if regErr := project.RegisterAgent(agent); regErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", regErr.Error())
		return out
	}
	if updateErr := s.userScopedRepository().Update(ctx, project); updateErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", updateErr.Error())
		return out
	}

	agentDict := entities.NewOrderedMap[any]()
	agentDict.Set("id", agentID)
	agentDict.Set("name", agent.Name)
	agentDict.Set("capabilities", zpProjectApplicationCapabilityList(agent))
	createdAt := ""
	if agent.CreatedAt != nil {
		createdAt = value_objects.IsoFormat(*agent.CreatedAt)
	}
	agentDict.Set("created_at", createdAt)

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent", agentDict)
	out.Set("message", "Agent '"+agentID+"' registered successfully")
	return out
}

// AssignAgentToTree mirrors assign_agent_to_tree.
func (s *ProjectApplicationService) AssignAgentToTree(ctx context.Context, projectID, agentID, gitBranchID string) *entities.OrderedMap[any] {
	project, err := s.userScopedRepository().FindByID(ctx, projectID)
	if err != nil || project == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Project with ID '"+projectID+"' not found")
		return out
	}

	if assignErr := project.AssignAgentToTree(agentID, gitBranchID); assignErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", assignErr.Error())
		return out
	}
	if updateErr := s.userScopedRepository().Update(ctx, project); updateErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", updateErr.Error())
		return out
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("message", "Agent '"+agentID+"' assigned to tree '"+gitBranchID+"' successfully")
	return out
}

// UnregisterAgent mirrors unregister_agent.
func (s *ProjectApplicationService) UnregisterAgent(ctx context.Context, projectID, agentID string) *entities.OrderedMap[any] {
	project, err := s.userScopedRepository().FindByID(ctx, projectID)
	if err != nil || project == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Project with ID '"+projectID+"' not found")
		return out
	}

	if !project.RegisteredAgents.Has(agentID) {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Agent '"+agentID+"' not found in project '"+projectID+"'")
		return out
	}

	agent, _ := project.RegisteredAgents.Get(agentID)
	project.RegisteredAgents.Delete(agentID)

	assignmentsToRemove := []string{}
	for _, branchID := range project.AgentAssignments.Keys() {
		if assignedAgentID, _ := project.AgentAssignments.Get(branchID); assignedAgentID == agentID {
			assignmentsToRemove = append(assignmentsToRemove, branchID)
		}
	}
	for _, branchID := range assignmentsToRemove {
		project.AgentAssignments.Delete(branchID)
	}

	sessionsToRemove := []string{}
	for _, sessionID := range project.ActiveWorkSessions.Keys() {
		session, _ := project.ActiveWorkSessions.Get(sessionID)
		if session != nil && session.AgentID == agentID {
			sessionsToRemove = append(sessionsToRemove, sessionID)
		}
	}
	for _, sessionID := range sessionsToRemove {
		project.ActiveWorkSessions.Delete(sessionID)
	}

	resourcesToUnlock := []string{}
	for _, resource := range project.ResourceLocks.Keys() {
		if lockedAgentID, _ := project.ResourceLocks.Get(resource); lockedAgentID == agentID {
			resourcesToUnlock = append(resourcesToUnlock, resource)
		}
	}
	for _, resource := range resourcesToUnlock {
		project.ResourceLocks.Delete(resource)
	}

	// Python deliberately uses the unscoped repository here.
	if updateErr := s.projectRepository.Update(ctx, project); updateErr != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", updateErr.Error())
		return out
	}

	agentDict := entities.NewOrderedMap[any]()
	agentDict.Set("id", agentID)
	agentDict.Set("name", agent.Name)
	agentDict.Set("capabilities", zpProjectApplicationCapabilityList(agent))

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent", agentDict)
	out.Set("removed_sessions", len(sessionsToRemove))
	out.Set("unlocked_resources", len(resourcesToUnlock))
	out.Set("message", "Agent '"+agentID+"' unregistered successfully")
	return out
}

// CleanupObsolete mirrors cleanup_obsolete(project_id=None).
func (s *ProjectApplicationService) CleanupObsolete(ctx context.Context, projectID *string) *entities.OrderedMap[any] {
	if projectID != nil {
		project, err := s.userScopedRepository().FindByID(ctx, *projectID)
		if err != nil || project == nil {
			out := entities.NewOrderedMap[any]()
			out.Set("success", false)
			out.Set("error", "Project with ID '"+*projectID+"' not found")
			return out
		}

		cleanedItems := zpProjectApplicationCleanupProjectData(project)
		if len(cleanedItems) > 0 {
			if updateErr := s.userScopedRepository().Update(ctx, project); updateErr != nil {
				out := entities.NewOrderedMap[any]()
				out.Set("success", false)
				out.Set("error", updateErr.Error())
				return out
			}
		}

		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		out.Set("project_id", *projectID)
		out.Set("cleaned_items", cleanedItems)
		out.Set("message", "Cleanup completed for project '"+*projectID+"'")
		return out
	}

	projects, err := s.userScopedRepository().FindAll(ctx)
	if err != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", err.Error())
		return out
	}
	totalCleaned := 0
	cleanupResults := entities.NewOrderedMap[any]()

	for _, project := range projects {
		cleanedItems := zpProjectApplicationCleanupProjectData(project)
		cleanupResults.Set(zpProjectApplicationID(project), cleanedItems)
		totalCleaned += len(cleanedItems)
		if len(cleanedItems) > 0 {
			if updateErr := s.userScopedRepository().Update(ctx, project); updateErr != nil {
				out := entities.NewOrderedMap[any]()
				out.Set("success", false)
				out.Set("error", updateErr.Error())
				return out
			}
		}
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("total_cleaned", totalCleaned)
	out.Set("cleanup_results", cleanupResults)
	out.Set("message", "Cleanup completed for all projects. "+strconv.Itoa(totalCleaned)+" items cleaned")
	return out
}

// zpProjectApplicationCleanupProjectData mirrors _cleanup_project_data.
func zpProjectApplicationCleanupProjectData(project *entities.Project) []string {
	cleanedItems := []string{}

	assignmentsToRemove := []string{}
	for _, gitBranchName := range project.AgentAssignments.Keys() {
		agentID, _ := project.AgentAssignments.Get(gitBranchName)
		if !project.GitBranchs.Has(gitBranchName) {
			assignmentsToRemove = append(assignmentsToRemove, gitBranchName)
		} else if !project.RegisteredAgents.Has(agentID) {
			assignmentsToRemove = append(assignmentsToRemove, gitBranchName)
		}
	}
	for _, gitBranchName := range assignmentsToRemove {
		project.AgentAssignments.Delete(gitBranchName)
		cleanedItems = append(cleanedItems, "Removed assignment to tree '"+gitBranchName+"'")
	}

	sessionsToRemove := []string{}
	for _, sessionID := range project.ActiveWorkSessions.Keys() {
		session, _ := project.ActiveWorkSessions.Get(sessionID)
		if session != nil && !project.RegisteredAgents.Has(session.AgentID) {
			sessionsToRemove = append(sessionsToRemove, sessionID)
		}
	}
	for _, sessionID := range sessionsToRemove {
		project.ActiveWorkSessions.Delete(sessionID)
		cleanedItems = append(cleanedItems, "Removed orphaned work session '"+sessionID+"'")
	}

	resourcesToUnlock := []string{}
	for _, resource := range project.ResourceLocks.Keys() {
		agentID, _ := project.ResourceLocks.Get(resource)
		if !project.RegisteredAgents.Has(agentID) {
			resourcesToUnlock = append(resourcesToUnlock, resource)
		}
	}
	for _, resource := range resourcesToUnlock {
		project.ResourceLocks.Delete(resource)
		cleanedItems = append(cleanedItems, "Unlocked resource '"+resource+"'")
	}

	return cleanedItems
}

// zpProjectApplicationCapabilityList mirrors
// [cap.value for cap in agent.capabilities]; Python set order is unspecified,
// so we sort for determinism.
func zpProjectApplicationCapabilityList(agent *entities.Agent) []string {
	out := []string{}
	for capability := range agent.Capabilities {
		out = append(out, string(capability))
	}
	sort.Strings(out)
	return out
}

func zpProjectApplicationID(project *entities.Project) string {
	if project.ID == nil {
		return ""
	}
	return project.ID.Value
}
