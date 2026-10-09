package facades

import (
	"context"
	"strings"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	domainservices "agenthub/fastmcp/task_management/domain/services"
)

// projectManagedService is the consumer-side port of the
// ProjectManagementService methods ProjectApplicationFacade calls. The signatures match
// application/services.ProjectManagementService.
type projectManagedService interface {
	CreateProject(ctx context.Context, name, description string) (*entities.OrderedMap[any], error)
	GetProject(ctx context.Context, projectID string) (*entities.OrderedMap[any], error)
	GetProjectByName(ctx context.Context, name string) (*entities.OrderedMap[any], error)
	ListProjects(ctx context.Context, includeBranches bool) (*entities.OrderedMap[any], error)
	UpdateProject(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error)
	ProjectHealthCheck(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
	CleanupObsolete(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
	ValidateIntegrity(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
	RebalanceAgents(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
	DeleteProject(ctx context.Context, projectID string, force bool) (*entities.OrderedMap[any], error)
}

// projectServiceWithUser adds ProjectManagementService.with_user, which the current Go
// service does not expose (it stores its user id privately). A caller-supplied adapter
// must implement it; see the package report.
type projectServiceWithUser interface {
	projectManagedService
	WithUser(userID string) projectServiceWithUser
}

// projectRepositoryManager is the consumer-side port of
// GlobalRepositoryManager.get_for_user, used for name validation.
type projectRepositoryManager interface {
	GetForUser(userID string) repositories.ProjectRepository
}

// ProjectApplicationFacade mirrors project_application_facade.ProjectApplicationFacade.
type ProjectApplicationFacade struct {
	projectService projectServiceWithUser
	userID         *string
	manager        projectRepositoryManager
}

// NewProjectApplicationFacade mirrors __init__(project_service=None, user_id=None).
// Python builds ProjectManagementService from GlobalRepositoryManager when no service is
// given; the Go equivalent is ProjectFacadeBuilder in
// application/factories/project_facade_factory.go, so this constructor requires a ready
// user-scoped service.
func NewProjectApplicationFacade(projectService projectServiceWithUser, manager projectRepositoryManager, userID *string) *ProjectApplicationFacade {
	return &ProjectApplicationFacade{projectService: projectService, userID: userID, manager: manager}
}

// WithUser mirrors with_user(user_id).
func (f *ProjectApplicationFacade) WithUser(userID string) *ProjectApplicationFacade {
	return NewProjectApplicationFacade(f.projectService.WithUser(userID), f.manager, &userID)
}

func paTruthy(s *string) bool { return s != nil && *s != "" }

func paStr(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func paEffectiveUser(userID, instance *string) *string {
	if paTruthy(userID) {
		return userID
	}
	return instance
}

func paError(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// paDuplicateError mirrors the enhanced error response for duplicate project names.
func paDuplicateError(errorMsg, name string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", errorMsg)
	if strings.Contains(strings.ToLower(errorMsg), "already exists") {
		m.Set("error_code", "DUPLICATE_PROJECT_NAME")
		m.Set("hint", "Use manage_project(action='list') to see all existing projects")
		actions := []any{}
		listAction := entities.NewOrderedMap[any]()
		listAction.Set("action", "list")
		listAction.Set("description", "View all existing projects")
		actions = append(actions, listAction)
		getAction := entities.NewOrderedMap[any]()
		getAction.Set("action", "get")
		getAction.Set("name", name)
		getAction.Set("description", "Get details of existing project '"+name+"'")
		actions = append(actions, getAction)
		m.Set("suggested_actions", actions)
	}
	return m
}

// ManageProject mirrors manage_project(action, project_id=None, name=None,
// description=None, user_id=None, force=False).
func (f *ProjectApplicationFacade) ManageProject(ctx context.Context, action string, projectID, name, description, userID *string, force bool) (*entities.OrderedMap[any], error) {
	switch action {
	case "create":
		if !paTruthy(name) {
			return paError("Missing required field: name"), nil
		}
		effectiveUserID := paEffectiveUser(userID, f.userID)
		if !paTruthy(effectiveUserID) {
			return paError("User authentication required"), nil
		}
		repo := f.manager.GetForUser(*effectiveUserID)
		validator := domainservices.NewProjectNameValidator(repo)
		if err := validator.ValidateProjectName(ctx, *name, *effectiveUserID, nil); err != nil {
			return paDuplicateError(err.Error(), *name), nil
		}
		var service projectManagedService = f.projectService
		if paTruthy(effectiveUserID) {
			service = f.projectService.WithUser(*effectiveUserID)
		}
		return service.CreateProject(ctx, *name, paStr(description))
	case "get":
		if paTruthy(projectID) {
			return f.projectService.GetProject(ctx, *projectID)
		} else if paTruthy(name) {
			return f.projectService.GetProjectByName(ctx, *name)
		}
		return paError("Missing required field: project_id or name"), nil
	case "list":
		effectiveUserID := paEffectiveUser(userID, f.userID)
		var service projectManagedService = f.projectService
		if paTruthy(effectiveUserID) {
			service = f.projectService.WithUser(*effectiveUserID)
		}
		return service.ListProjects(ctx, true)
	case "update":
		if !paTruthy(projectID) {
			return paError("Missing required field: project_id"), nil
		}
		if name != nil {
			effectiveUserID := paEffectiveUser(userID, f.userID)
			if !paTruthy(effectiveUserID) {
				return paError("User authentication required"), nil
			}
			repo := f.manager.GetForUser(*effectiveUserID)
			validator := domainservices.NewProjectNameValidator(repo)
			if err := validator.ValidateProjectName(ctx, *name, *effectiveUserID, projectID); err != nil {
				return paDuplicateError(err.Error(), *name), nil
			}
		}
		return f.projectService.UpdateProject(ctx, *projectID, name, description)
	case "project_health_check":
		return f.projectService.ProjectHealthCheck(ctx, projectID)
	case "cleanup_obsolete":
		return f.projectService.CleanupObsolete(ctx, projectID)
	case "validate_integrity":
		return f.projectService.ValidateIntegrity(ctx, projectID)
	case "rebalance_agents":
		return f.projectService.RebalanceAgents(ctx, projectID)
	case "delete":
		if !paTruthy(projectID) {
			return paError("Missing required field: project_id"), nil
		}
		effectiveUserID := paEffectiveUser(userID, f.userID)
		var service projectManagedService = f.projectService
		if paTruthy(effectiveUserID) {
			service = f.projectService.WithUser(*effectiveUserID)
		}
		return service.DeleteProject(ctx, *projectID, force)
	}
	return paError("Invalid action: " + action), nil
}

// CreateProject mirrors create_project(name, description="").
func (f *ProjectApplicationFacade) CreateProject(ctx context.Context, name, description string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "create", nil, &name, &description, nil, false)
}

// GetProject mirrors get_project(project_id).
func (f *ProjectApplicationFacade) GetProject(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "get", &projectID, nil, nil, nil, false)
}

// GetProjectByName mirrors get_project_by_name(name).
func (f *ProjectApplicationFacade) GetProjectByName(ctx context.Context, name string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "get", nil, &name, nil, nil, false)
}

// ListProjects mirrors list_projects.
func (f *ProjectApplicationFacade) ListProjects(ctx context.Context) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "list", nil, nil, nil, nil, false)
}

// UpdateProject mirrors update_project(project_id, name=None, description=None).
func (f *ProjectApplicationFacade) UpdateProject(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "update", &projectID, name, description, nil, false)
}

// DeleteProject mirrors delete_project(project_id, force=False).
func (f *ProjectApplicationFacade) DeleteProject(ctx context.Context, projectID string, force bool) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "delete", &projectID, nil, nil, nil, force)
}

// ProjectHealthCheck mirrors project_health_check(project_id, user_id=None).
func (f *ProjectApplicationFacade) ProjectHealthCheck(ctx context.Context, projectID string, userID *string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "project_health_check", &projectID, nil, nil, userID, false)
}

// CleanupObsolete mirrors cleanup_obsolete(project_id, force=False, user_id=None).
func (f *ProjectApplicationFacade) CleanupObsolete(ctx context.Context, projectID string, force bool, userID *string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "cleanup_obsolete", &projectID, nil, nil, userID, force)
}

// ValidateIntegrity mirrors validate_integrity(project_id, force=False, user_id=None).
func (f *ProjectApplicationFacade) ValidateIntegrity(ctx context.Context, projectID string, force bool, userID *string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "validate_integrity", &projectID, nil, nil, userID, force)
}

// RebalanceAgents mirrors rebalance_agents(project_id, force=False, user_id=None).
func (f *ProjectApplicationFacade) RebalanceAgents(ctx context.Context, projectID string, force bool, userID *string) (*entities.OrderedMap[any], error) {
	return f.ManageProject(ctx, "rebalance_agents", &projectID, nil, nil, userID, force)
}

// projectServiceAdapter gives *services.ProjectManagementService the with_user method
// ProjectApplicationFacade needs; build constructs the service for another user.
type projectServiceAdapter struct {
	*services.ProjectManagementService
	build func(userID string) *services.ProjectManagementService
}

// WithUser mirrors ProjectManagementService.with_user.
func (a projectServiceAdapter) WithUser(userID string) projectServiceWithUser {
	return projectServiceAdapter{ProjectManagementService: a.build(userID), build: a.build}
}

// ProjectRepositoryManagerFunc is GlobalRepositoryManager.get_for_user as a function.
type ProjectRepositoryManagerFunc func(userID string) repositories.ProjectRepository

// GetForUser implements projectRepositoryManager.
func (f ProjectRepositoryManagerFunc) GetForUser(userID string) repositories.ProjectRepository {
	return f(userID)
}

// NewProjectApplicationFacadeFromBuilder builds the facade around a per-user service builder
// (the Go form of ProjectManagementService(project_repo, user_id) / with_user).
func NewProjectApplicationFacadeFromBuilder(build func(userID string) *services.ProjectManagementService,
	manager ProjectRepositoryManagerFunc, userID *string) *ProjectApplicationFacade {
	var svc *services.ProjectManagementService
	if userID != nil {
		svc = build(*userID)
	} else {
		svc = build("")
	}
	return NewProjectApplicationFacade(projectServiceAdapter{ProjectManagementService: svc, build: build}, manager, userID)
}
