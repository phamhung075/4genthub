package services

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpProjCreateProjectUseCase is the consumer-side port of
// CreateProjectUseCase.execute(project_id, name, description).
type zpProjCreateProjectUseCase interface {
	Execute(ctx context.Context, projectID *string, name *string, description string) (*entities.OrderedMap[any], error)
}

// zpProjGetProjectUseCase is the consumer-side port of GetProjectUseCase.execute(project_id).
type zpProjGetProjectUseCase interface {
	Execute(ctx context.Context, projectID string) (*entities.OrderedMap[any], error)
}

// zpProjListProjectsUseCase is the consumer-side port of
// ListProjectsUseCase.execute(include_branches=True).
type zpProjListProjectsUseCase interface {
	Execute(ctx context.Context, includeBranches bool) (*entities.OrderedMap[any], error)
}

// zpProjUpdateProjectUseCase is the consumer-side port of
// UpdateProjectUseCase.execute(project_id, name, description).
type zpProjUpdateProjectUseCase interface {
	Execute(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error)
}

// zpProjCleanupObsoleteUseCase is the consumer-side port of
// CleanupObsoleteUseCase.execute(project_id=None).
type zpProjCleanupObsoleteUseCase interface {
	Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
}

// zpProjProjectHealthCheckUseCase is the consumer-side port of
// ProjectHealthCheckUseCase.execute(project_id=None).
type zpProjProjectHealthCheckUseCase interface {
	Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
}

// zpProjValidateIntegrityUseCase is the consumer-side port of
// ValidateIntegrityUseCase.execute(project_id=None).
type zpProjValidateIntegrityUseCase interface {
	Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
}

// zpProjRebalanceAgentsUseCase is the consumer-side port of
// RebalanceAgentsUseCase.execute(project_id=None).
type zpProjRebalanceAgentsUseCase interface {
	Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error)
}

// zpProjWebSocketNotifier is the consumer-side port of
// WebSocketNotificationService.sync_broadcast_project_event. Python passes
// keyword arguments and the helper swallows its own errors, so no error is returned.
type zpProjWebSocketNotifier interface {
	SyncBroadcastProjectEvent(eventType string, projectID any, userID *string, projectData *entities.OrderedMap[any])
}

// zpProjGitBranchRepository is the consumer-side port of the repository that
// Python's delete_project obtains from RepositoryFactory.get_git_branch_repository.
// The domain interface is embedded; find_all_by_project and delete_branch are added.
type zpProjGitBranchRepository interface {
	repositories.GitBranchRepository

	FindAllByProject(ctx context.Context, projectID string) ([]*entities.GitBranch, error)
	DeleteBranch(ctx context.Context, branchID string) (bool, error)
}

// zpProjTaskCounter abstracts the direct get_session()/Task-model count in delete_project
// (the application layer must not import the database package).
type zpProjTaskCounter interface {
	CountTasksByBranch(ctx context.Context, branchID string) (int, error)
}

// zpProjDeps bundles the use cases. Python builds each use case from the
// user-scoped repository inside the corresponding method, so the caller supplies
// ready-built (user-scoped) instances here.
type zpProjDeps struct {
	CreateProject      zpProjCreateProjectUseCase
	GetProject         zpProjGetProjectUseCase
	ListProjects       zpProjListProjectsUseCase
	UpdateProject      zpProjUpdateProjectUseCase
	CleanupObsolete    zpProjCleanupObsoleteUseCase
	ProjectHealthCheck zpProjProjectHealthCheckUseCase
	ValidateIntegrity  zpProjValidateIntegrityUseCase
	RebalanceAgents    zpProjRebalanceAgentsUseCase
}

// ProjectManagementService mirrors project_management_service.ProjectManagementService.
type ProjectManagementService struct {
	projectRepo   repositories.ProjectRepository
	userID        *string
	deps          zpProjDeps
	notifier      zpProjWebSocketNotifier
	gitBranchRepo zpProjGitBranchRepository
	taskCounter   zpProjTaskCounter
}

// zpProjNewService mirrors ProjectManagementService.__init__. Python falls back to
// GlobalRepositoryManager.get_default() when project_repo is None; the Go port has no
// such factory, so the caller supplies the already-appropriate (user-scoped) repository.
// The use cases, the WebSocket notifier and the delete_project collaborators (git branch
// repository, task counter) are also caller-supplied and may be nil.
func zpProjNewService(projectRepo repositories.ProjectRepository, userID *string, deps zpProjDeps, notifier zpProjWebSocketNotifier, gitBranchRepo zpProjGitBranchRepository, taskCounter zpProjTaskCounter) *ProjectManagementService {
	return &ProjectManagementService{
		projectRepo:   projectRepo,
		userID:        userID,
		deps:          deps,
		notifier:      notifier,
		gitBranchRepo: gitBranchRepo,
		taskCounter:   taskCounter,
	}
}

// zpProjGet is Python dict.get(key) (None when missing).
func zpProjGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// zpProjGetDefault is Python dict.get(key, default).
func zpProjGetDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}

// zpProjFailure builds {"success": False, "error": msg}.
func zpProjFailure(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// zpProjHasUser is bool(self._user_id).
func (s *ProjectManagementService) zpProjHasUser() bool {
	return s.userID != nil && *s.userID != ""
}

// zpProjUserScopedRepository mirrors _get_user_scoped_repository.
func (s *ProjectManagementService) zpProjUserScopedRepository() repositories.ProjectRepository {
	if r, ok := serviceUserScopedRepository(s.projectRepo, s.userID).(repositories.ProjectRepository); ok {
		return r
	}
	return s.projectRepo
}

// zpProjProjectCreatePayload mirrors ProjectCreatePayload(...).model_dump(). ok is false
// when Pydantic validation would raise (id or name missing/not a string); the caller then
// falls back to the raw project dict.
func zpProjProjectCreatePayload(raw *entities.OrderedMap[any]) (*entities.OrderedMap[any], bool) {
	if raw == nil {
		return nil, false
	}
	id, idOK := raw.Get("id")
	if !idOK {
		return nil, false
	}
	name, nameOK := raw.Get("name")
	if !nameOK {
		return nil, false
	}
	idStr, idIsStr := id.(string)
	nameStr, nameIsStr := name.(string)
	if !idIsStr || !nameIsStr {
		return nil, false
	}
	m := entities.NewOrderedMap[any]()
	m.Set("id", idStr)
	m.Set("name", nameStr)
	m.Set("description", zpProjGet(raw, "description"))
	m.Set("created_at", zpProjGet(raw, "created_at"))
	m.Set("updated_at", zpProjGet(raw, "updated_at"))
	return m, true
}

// zpProjProjectUpdatePayload mirrors ProjectUpdatePayload(...).model_dump() with
// id=raw.get("id") or project_id.
func zpProjProjectUpdatePayload(raw *entities.OrderedMap[any], projectID string) (*entities.OrderedMap[any], bool) {
	if raw == nil {
		return nil, false
	}
	id := zpProjGet(raw, "id")
	idStr, idIsStr := id.(string)
	if !idIsStr || idStr == "" {
		idStr = projectID
	}
	name := zpProjGet(raw, "name")
	nameStr, nameIsStr := name.(string)
	if !nameIsStr {
		return nil, false
	}
	m := entities.NewOrderedMap[any]()
	m.Set("id", idStr)
	m.Set("name", nameStr)
	m.Set("description", zpProjGet(raw, "description"))
	m.Set("updated_at", zpProjGet(raw, "updated_at"))
	return m, true
}

// zpProjRawProjectMap is result.get("project", {}) coerced to an OrderedMap (nil when the
// value is missing/None/not a dict).
func zpProjRawProjectMap(result *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	raw := zpProjGetDefault(result, "project", entities.NewOrderedMap[any]())
	rawMap, _ := raw.(*entities.OrderedMap[any])
	return rawMap
}

// CreateProject mirrors create_project.
func (s *ProjectManagementService) CreateProject(ctx context.Context, name, description string) (*entities.OrderedMap[any], error) {
	if s.deps.CreateProject == nil {
		return zpProjFailure("CreateProjectUseCase is not configured"), nil
	}
	result, err := s.deps.CreateProject.Execute(ctx, nil, &name, description)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	if value_objects.PyTruthy(zpProjGet(result, "success")) && s.zpProjHasUser() {
		rawProjectData := zpProjRawProjectMap(result)
		projectData, ok := zpProjProjectCreatePayload(rawProjectData)
		if !ok {
			projectData = rawProjectData
		}
		if projectData != nil && s.notifier != nil {
			s.notifier.SyncBroadcastProjectEvent("created", zpProjGet(projectData, "id"), s.userID, projectData)
		}
	}
	return result, nil
}

// GetProject mirrors get_project.
func (s *ProjectManagementService) GetProject(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	if s.deps.GetProject == nil {
		return zpProjFailure("GetProjectUseCase is not configured"), nil
	}
	result, err := s.deps.GetProject.Execute(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// GetProjectByName mirrors get_project_by_name.
func (s *ProjectManagementService) GetProjectByName(ctx context.Context, name string) (*entities.OrderedMap[any], error) {
	userScopedRepo := s.zpProjUserScopedRepository()
	project, err := userScopedRepo.FindByName(ctx, name)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	if project == nil {
		return zpProjFailure(fmt.Sprintf("Project with name '%s' not found", name)), nil
	}
	if s.deps.GetProject == nil {
		return zpProjFailure("GetProjectUseCase is not configured"), nil
	}
	result, err := s.deps.GetProject.Execute(ctx, project.GetEntityID())
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// ListProjects mirrors list_projects.
func (s *ProjectManagementService) ListProjects(ctx context.Context, includeBranches bool) (*entities.OrderedMap[any], error) {
	if s.deps.ListProjects == nil {
		return zpProjFailure("ListProjectsUseCase is not configured"), nil
	}
	result, err := s.deps.ListProjects.Execute(ctx, includeBranches)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// UpdateProject mirrors update_project.
func (s *ProjectManagementService) UpdateProject(ctx context.Context, projectID string, name, description *string) (*entities.OrderedMap[any], error) {
	if s.deps.UpdateProject == nil {
		return zpProjFailure("UpdateProjectUseCase is not configured"), nil
	}
	result, err := s.deps.UpdateProject.Execute(ctx, projectID, name, description)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	if value_objects.PyTruthy(zpProjGet(result, "success")) && s.zpProjHasUser() {
		rawProjectData := zpProjRawProjectMap(result)
		projectData, ok := zpProjProjectUpdatePayload(rawProjectData, projectID)
		if !ok {
			projectData = rawProjectData
		}
		// Python calls the notifier with project_data even when it is None.
		if s.notifier != nil {
			s.notifier.SyncBroadcastProjectEvent("updated", projectID, s.userID, projectData)
		}
	}
	return result, nil
}

// ProjectHealthCheck mirrors project_health_check.
func (s *ProjectManagementService) ProjectHealthCheck(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if s.deps.ProjectHealthCheck == nil {
		return zpProjFailure("ProjectHealthCheckUseCase is not configured"), nil
	}
	result, err := s.deps.ProjectHealthCheck.Execute(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// CleanupObsolete mirrors cleanup_obsolete.
func (s *ProjectManagementService) CleanupObsolete(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if s.deps.CleanupObsolete == nil {
		return zpProjFailure("CleanupObsoleteUseCase is not configured"), nil
	}
	result, err := s.deps.CleanupObsolete.Execute(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// ValidateIntegrity mirrors validate_integrity.
func (s *ProjectManagementService) ValidateIntegrity(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if s.deps.ValidateIntegrity == nil {
		return zpProjFailure("ValidateIntegrityUseCase is not configured"), nil
	}
	result, err := s.deps.ValidateIntegrity.Execute(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// RebalanceAgents mirrors rebalance_agents.
func (s *ProjectManagementService) RebalanceAgents(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	if s.deps.RebalanceAgents == nil {
		return zpProjFailure("RebalanceAgentsUseCase is not configured"), nil
	}
	result, err := s.deps.RebalanceAgents.Execute(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	return result, nil
}

// DeleteProject mirrors delete_project.
func (s *ProjectManagementService) DeleteProject(ctx context.Context, projectID string, force bool) (*entities.OrderedMap[any], error) {
	userScopedRepo := s.zpProjUserScopedRepository()
	project, err := userScopedRepo.FindByID(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	if project == nil {
		return zpProjFailure(fmt.Sprintf("Project %s not found", projectID)), nil
	}

	if !force {
		branches, err := s.zpProjFindAllByProject(ctx, projectID)
		if err != nil {
			return zpProjFailure(err.Error()), nil
		}
		if len(branches) > 0 {
			if len(branches) > 1 {
				branchNames := make([]string, 0, len(branches))
				for _, branch := range branches {
					branchNames = append(branchNames, branch.Name)
				}
				return zpProjFailure(fmt.Sprintf("Cannot delete project with multiple branches (%d branches: %s). Delete other branches first, or use force=True", len(branches), strings.Join(branchNames, ", "))), nil
			}
			mainBranch := branches[0]
			branchName := mainBranch.Name
			if branchName != "main" {
				return zpProjFailure(fmt.Sprintf("Cannot delete project with non-main branch '%s'. Project must have only 'main' branch, or use force=True", branchName)), nil
			}
			branchID := mainBranch.GetEntityID()
			taskCount := 0
			if s.taskCounter != nil {
				taskCount, err = s.taskCounter.CountTasksByBranch(ctx, branchID)
				if err != nil {
					return zpProjFailure(err.Error()), nil
				}
			}
			if taskCount > 0 {
				return zpProjFailure(fmt.Sprintf("Cannot delete project with %d tasks in main branch. Delete all tasks first, or use force=True", taskCount)), nil
			}
		}
	}

	branches, err := s.zpProjFindAllByProject(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	for _, branch := range branches {
		branchID := branch.GetEntityID()
		if branchID != "" {
			if _, err := s.gitBranchRepo.DeleteBranch(ctx, branchID); err != nil {
				return zpProjFailure(err.Error()), nil
			}
		}
	}

	deleted, err := userScopedRepo.Delete(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}
	verifyProject, err := userScopedRepo.FindByID(ctx, projectID)
	if err != nil {
		return zpProjFailure(err.Error()), nil
	}

	if deleted && verifyProject == nil {
		if s.notifier != nil {
			projectData := entities.NewOrderedMap[any]()
			projectData.Set("id", projectID)
			projectData.Set("name", project.Name)
			s.notifier.SyncBroadcastProjectEvent("deleted", projectID, s.userID, projectData)
		}
		result := entities.NewOrderedMap[any]()
		result.Set("success", true)
		result.Set("message", fmt.Sprintf("Project '%s' deleted successfully", project.Name))
		result.Set("project_id", projectID)
		return result, nil
	}
	if deleted && verifyProject != nil {
		return zpProjFailure(fmt.Sprintf("Failed to delete project %s - project still exists after deletion", projectID)), nil
	}
	return zpProjFailure(fmt.Sprintf("Failed to delete project %s - repository returned False", projectID)), nil
}

// zpProjFindAllByProject wraps the injected git branch repository; nil means no branches.
func (s *ProjectManagementService) zpProjFindAllByProject(ctx context.Context, projectID string) ([]*entities.GitBranch, error) {
	if s.gitBranchRepo == nil {
		return nil, nil
	}
	return s.gitBranchRepo.FindAllByProject(ctx, projectID)
}

// ProjectUseCaseHooks are the side-effect hooks of the create/update project use cases
// (context auto-creation and the WebSocket broadcast); see application/hooks.
type ProjectUseCaseHooks interface {
	use_cases.CreateProjectHooks
	use_cases.UpdateProjectHooks
}

// NewProjectManagementService builds the service over an already user-scoped project
// repository, constructing the use cases Python builds inside each method. notifier,
// gitBranchRepo, taskCounter and hooks may be nil.
func NewProjectManagementService(projectRepo repositories.ProjectRepository, userID *string,
	notifier zpProjWebSocketNotifier, gitBranchRepo zpProjGitBranchRepository,
	taskCounter zpProjTaskCounter, hooks ProjectUseCaseHooks) *ProjectManagementService {
	create := use_cases.NewCreateProjectUseCase(projectRepo)
	update := use_cases.NewUpdateProjectUseCase(projectRepo)
	if hooks != nil {
		create.WithHooks(hooks)
		update.WithHooks(hooks)
	}
	deps := zpProjDeps{
		CreateProject:      create,
		GetProject:         use_cases.NewGetProjectUseCase(projectRepo),
		ListProjects:       use_cases.NewListProjectsUseCase(projectRepo),
		UpdateProject:      update,
		CleanupObsolete:    use_cases.NewCleanupObsoleteUseCase(projectRepo),
		ProjectHealthCheck: use_cases.NewProjectHealthCheckUseCase(projectRepo),
		ValidateIntegrity:  zpProjValidateIntegrityAdapter{use_cases.NewValidateIntegrityUseCase(projectRepo)},
	}
	return zpProjNewService(projectRepo, userID, deps, notifier, gitBranchRepo, taskCounter)
}

// zpProjValidateIntegrityAdapter adapts the error-free ValidateIntegrityUseCase.Execute.
type zpProjValidateIntegrityAdapter struct {
	uc *use_cases.ValidateIntegrityUseCase
}

func (a zpProjValidateIntegrityAdapter) Execute(ctx context.Context, projectID *string) (*entities.OrderedMap[any], error) {
	return a.uc.Execute(ctx, projectID), nil
}

// Exported names for the ports NewProjectManagementService takes, for the composition root.
type (
	ProjectGitBranchRepositoryPort = zpProjGitBranchRepository
	ProjectTaskCounterPort         = zpProjTaskCounter
)
