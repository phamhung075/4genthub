package services

import (
	"context"
	"fmt"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpGitBranchContextService is the consumer-side port of the UnifiedContextService
// methods GitBranchService calls. Python falls back to
// FacadeService.get_unified_context_facade; the Go caller supplies the
// facade. Only create_context and delete_context are used, and both are synchronous in
// Python (storage-touching, so ctx comes first here). The return value is the Python
// dict; key order is only read through get(), so it is an OrderedMap.
type zpGitBranchContextService interface {
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], projectID *string) (*entities.OrderedMap[any], error)
	DeleteContext(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error)
}

// zpGitBranchWebSocketNotifier is the consumer-side port of
// WebSocketNotificationService.sync_broadcast_branch_event, which Python imports inside
// delete_git_branch. The Python helper swallows its own errors, so no error is returned.
type zpGitBranchWebSocketNotifier interface {
	SyncBroadcastBranchEvent(eventType, branchID, projectID string, userID *string, branchData *entities.OrderedMap[any])
}

// zpGitBranchRepository is the duck-typed git-branch repository the Python service uses.
// The ABC (domain GitBranchRepository) declares find_by_id/create_git_branch/
// get_git_branch_by_name/delete_git_branch/... while the concrete ORM repository exposes
// find_by_name/create_branch/delete_branch/find_all/update/assign_agent/unassign_agent;
// Python duck-types both. The domain interface is embedded here and the concrete methods
// are added so the service compiles; note that the ported ORMGitBranchRepository does not
// implement Update(*GitBranch) (it has UpdateDomain) or the extra *bool* shapes of the
// Python ABC (its archive/restore methods return maps) -- see the package report.
type zpGitBranchRepository interface {
	repositories.GitBranchRepository

	FindByName(ctx context.Context, projectID, branchName string) (*entities.GitBranch, error)
	CreateBranch(ctx context.Context, projectID, branchName, description string) (*entities.GitBranch, error)
	DeleteBranch(ctx context.Context, branchID string) (bool, error)
	FindAll(ctx context.Context) ([]*entities.GitBranch, error)
	Update(ctx context.Context, branch *entities.GitBranch) (bool, error)
	AssignAgent(ctx context.Context, projectID, branchID, agentID string) (bool, error)
	UnassignAgent(ctx context.Context, projectID, branchID string) (bool, error)
}

// GitBranchService mirrors git_branch_service.GitBranchService.
type GitBranchService struct {
	projectRepo    repositories.ProjectRepository
	gitBranchRepo  zpGitBranchRepository
	contextService zpGitBranchContextService
	userID         *string
	notifier       zpGitBranchWebSocketNotifier
}

// zpGitBranchNewService mirrors GitBranchService.__init__. Python raises ValueError when
// project_repo or git_branch_repo is missing and otherwise builds the context service from
// FacadeService; here both repositories are required and the context service plus the
// WebSocket notifier (both unported) are injected and may be nil.
func zpGitBranchNewService(projectRepo repositories.ProjectRepository, gitBranchRepo zpGitBranchRepository, contextService zpGitBranchContextService, userID *string, notifier zpGitBranchWebSocketNotifier) (*GitBranchService, error) {
	if projectRepo == nil {
		return nil, &value_objects.ValueError{Msg: "Project repository is required"}
	}
	if gitBranchRepo == nil {
		return nil, &value_objects.ValueError{Msg: "Git branch repository is required"}
	}
	return &GitBranchService{
		projectRepo:    projectRepo,
		gitBranchRepo:  gitBranchRepo,
		contextService: contextService,
		userID:         userID,
		notifier:       notifier,
	}, nil
}

// WithUser mirrors GitBranchService.with_user; the repositories are non-nil by
// construction, so the constructor error cannot occur.
func (s *GitBranchService) WithUser(userID string) *GitBranchService {
	svc, _ := zpGitBranchNewService(s.projectRepo, s.gitBranchRepo, s.contextService, &userID, s.notifier)
	return svc
}

// zpGitBranchUserScopedProjectRepo mirrors _get_user_scoped_repository.
func (s *GitBranchService) zpGitBranchUserScopedProjectRepo() repositories.ProjectRepository {
	if r, ok := serviceUserScopedRepository(s.projectRepo, s.userID).(repositories.ProjectRepository); ok {
		return r
	}
	return s.projectRepo
}

// zpGitBranchUserScopedGitBranchRepo mirrors _get_user_scoped_repository.
func (s *GitBranchService) zpGitBranchUserScopedGitBranchRepo() zpGitBranchRepository {
	if r, ok := serviceUserScopedRepository(s.gitBranchRepo, s.userID).(zpGitBranchRepository); ok {
		return r
	}
	return s.gitBranchRepo
}

// zpGitBranchGet is Python dict.get(key) (None when missing).
func zpGitBranchGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// zpGitBranchFailure builds {"success": False, "error": msg}.
func zpGitBranchFailure(msg string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", msg)
	return m
}

// zpGitBranchFailureCode builds {"success": False, "error": msg, "error_code": code}.
func zpGitBranchFailureCode(code, msg string) *entities.OrderedMap[any] {
	m := zpGitBranchFailure(msg)
	m.Set("error_code", code)
	return m
}

// zpGitBranchBranchDict is GitBranch.to_dict with Python's key order. The entity's
// ToDict() returns an unordered map, so the ordered form is rebuilt here.
func zpGitBranchBranchDict(b *entities.GitBranch) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", b.GetEntityID())
	m.Set("name", b.Name)
	var gitBranchName any
	if b.GitBranchName != nil {
		gitBranchName = *b.GitBranchName
	}
	m.Set("git_branch_name", gitBranchName)
	m.Set("description", b.Description)
	m.Set("project_id", b.ProjectID)
	m.Set("created_at", value_objects.IsoFormat(*b.CreatedAt))
	m.Set("updated_at", value_objects.IsoFormat(*b.UpdatedAt))
	var assignedAgentID any
	if b.AssignedAgentID != nil {
		assignedAgentID = *b.AssignedAgentID
	}
	m.Set("assigned_agent_id", assignedAgentID)
	m.Set("assigned_agents", append([]string{}, b.AssignedAgents...))
	m.Set("priority", b.Priority.Value)
	m.Set("status", b.Status.Value)
	m.Set("archived", b.Archived)
	return m
}

// zpGitBranchContextData builds the branch context data dict used by create_git_branch
// and create_missing_branch_context.
func zpGitBranchContextData(projectID, branchName, description, createdBy string) *entities.OrderedMap[any] {
	data := entities.NewOrderedMap[any]()
	data.Set("project_id", projectID)
	data.Set("git_branch_name", branchName)
	settings := entities.NewOrderedMap[any]()
	for _, key := range []string{"feature_flags", "branch_workflow", "testing_strategy", "deployment_config", "collaboration_settings", "agent_assignments"} {
		settings.Set(key, entities.NewOrderedMap[any]())
	}
	data.Set("branch_settings", settings)
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("branch_description", description)
	metadata.Set("auto_created", true)
	metadata.Set("created_by", createdBy)
	data.Set("metadata", metadata)
	return data
}

// CreateGitBranch mirrors create_git_branch.
func (s *GitBranchService) CreateGitBranch(ctx context.Context, projectID, branchName, description string) (*entities.OrderedMap[any], error) {
	projectRepo := s.zpGitBranchUserScopedProjectRepo()
	project, err := projectRepo.FindByID(ctx, projectID)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if project == nil {
		return zpGitBranchFailure(fmt.Sprintf("Project %s not found", projectID)), nil
	}

	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	existing, err := gitBranchRepo.FindByName(ctx, projectID, branchName)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if existing != nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch '%s' already exists in project %s", branchName, projectID)), nil
	}

	gitBranch, err := gitBranchRepo.CreateBranch(ctx, projectID, branchName, description)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}

	// Branch-context creation is best effort: Python logs and continues on failure.
	if s.contextService != nil {
		data := zpGitBranchContextData(projectID, branchName, description, "git_branch_service")
		_, _ = s.contextService.CreateContext(ctx, "branch", gitBranch.GetEntityID(), data, nil)
	}

	if err := project.AddGitBranch(gitBranch); err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if err := projectRepo.Update(ctx, project); err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}

	branchData := entities.NewOrderedMap[any]()
	branchData.Set("id", gitBranch.GetEntityID())
	branchData.Set("name", gitBranch.Name)
	branchData.Set("git_branch_name", gitBranch.Name)
	branchData.Set("description", gitBranch.Description)
	branchData.Set("project_id", gitBranch.ProjectID)

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("git_branch", branchData)
	result.Set("message", fmt.Sprintf("Git branch '%s' created successfully", branchName))
	return result, nil
}

// GetGitBranch mirrors get_git_branch. Python does not wrap this method in try/except, so
// repository errors surface as the Go error return.
func (s *GitBranchService) GetGitBranch(ctx context.Context, projectID, branchName string) (*entities.OrderedMap[any], error) {
	projectRepo := s.zpGitBranchUserScopedProjectRepo()
	project, err := projectRepo.FindByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if project == nil {
		return zpGitBranchFailure(fmt.Sprintf("Project %s not found", projectID)), nil
	}
	gitBranch := project.GetGitBranch(branchName)
	if gitBranch == nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch '%s' not found in project %s", branchName, projectID)), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("git_branch", zpGitBranchBranchDict(gitBranch))
	return result, nil
}

// ListGitBranchs mirrors list_git_branchs (Python spelling preserved).
func (s *GitBranchService) ListGitBranchs(ctx context.Context, projectID string) (*entities.OrderedMap[any], error) {
	projectRepo := s.zpGitBranchUserScopedProjectRepo()
	project, err := projectRepo.FindByID(ctx, projectID)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if project == nil {
		return zpGitBranchFailure(fmt.Sprintf("Project %s not found", projectID)), nil
	}
	branches := []any{}
	for _, branch := range project.GitBranchs.Values() {
		branches = append(branches, zpGitBranchBranchDict(branch))
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("project_id", projectID)
	result.Set("count", len(branches))
	result.Set("git_branchs", branches)
	return result, nil
}

// DeleteGitBranch mirrors delete_git_branch.
func (s *GitBranchService) DeleteGitBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()

	gitBranch, err := gitBranchRepo.FindByID(ctx, gitBranchID, nil)
	if err != nil {
		return zpGitBranchFailureCode("DELETE_FAILED", err.Error()), nil
	}
	if gitBranch == nil {
		return zpGitBranchFailureCode("DELETE_FAILED", fmt.Sprintf("Git branch with ID %s not found", gitBranchID)), nil
	}
	branchName := gitBranch.Name
	branchProjectID := gitBranch.ProjectID

	success, err := gitBranchRepo.DeleteBranch(ctx, gitBranchID)
	if err != nil {
		return zpGitBranchFailureCode("DELETE_FAILED", err.Error()), nil
	}
	if !success {
		return zpGitBranchFailureCode("DELETE_FAILED", fmt.Sprintf("Failed to delete git branch %s", gitBranchID)), nil
	}

	// Context deletion is best effort.
	if s.contextService != nil {
		_, _ = s.contextService.DeleteContext(ctx, "branch", gitBranchID)
	}

	projectRepo := s.zpGitBranchUserScopedProjectRepo()
	project, err := projectRepo.FindByID(ctx, projectID)
	if err != nil {
		return zpGitBranchFailureCode("DELETE_FAILED", err.Error()), nil
	}
	if project != nil && project.GitBranchs.Has(gitBranchID) {
		project.GitBranchs.Delete(gitBranchID)
		if err := projectRepo.Update(ctx, project); err != nil {
			return zpGitBranchFailureCode("DELETE_FAILED", err.Error()), nil
		}
	}

	// BranchDeletePayload validation and the dict fallback produce the same three keys in
	// the same order, so the validation branch is unobservable and omitted.
	if s.notifier != nil {
		branchData := entities.NewOrderedMap[any]()
		branchData.Set("id", gitBranchID)
		branchData.Set("name", branchName)
		branchData.Set("project_id", branchProjectID)
		s.notifier.SyncBroadcastBranchEvent("deleted", gitBranchID, branchProjectID, s.userID, branchData)
	}

	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", fmt.Sprintf("Git branch %s deleted successfully", gitBranchID))
	return result, nil
}

// CreateMissingBranchContext mirrors create_missing_branch_context.
func (s *GitBranchService) CreateMissingBranchContext(ctx context.Context, branchID string, projectID *string, branchName, description string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	gitBranch, err := gitBranchRepo.FindByID(ctx, branchID, nil)
	if err != nil {
		return zpGitBranchFailure(fmt.Sprintf("Failed to create branch context: %s", err.Error())), nil
	}
	if gitBranch == nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch %s not found", branchID)), nil
	}

	actualProjectID := gitBranch.ProjectID
	if projectID != nil && *projectID != "" {
		actualProjectID = *projectID
	}
	if branchName == "" {
		branchName = gitBranch.Name
	}
	if description == "" {
		if gitBranch.Description != "" {
			description = gitBranch.Description
		} else {
			description = fmt.Sprintf("Branch context for %s", gitBranch.Name)
		}
	}

	data := zpGitBranchContextData(actualProjectID, branchName, description, "git_branch_service_missing_context_fix")
	if s.contextService == nil {
		return zpGitBranchFailure("Failed to create branch context: Unknown error"), nil
	}
	result, err := s.contextService.CreateContext(ctx, "branch", branchID, data, &actualProjectID)
	if err != nil {
		return zpGitBranchFailure(fmt.Sprintf("Failed to create branch context: %s", err.Error())), nil
	}
	if result != nil && value_objects.PyTruthy(zpGitBranchGet(result, "success")) {
		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		out.Set("branch_context", zpGitBranchGet(result, "context"))
		out.Set("message", fmt.Sprintf("Branch context created for branch %s", branchID))
		return out, nil
	}
	errValue := any("Unknown error")
	if result != nil {
		if v, ok := result.Get("error"); ok {
			errValue = v
		}
	}
	return zpGitBranchFailure(fmt.Sprintf("Failed to create branch context: %s", value_objects.PyStr(errValue))), nil
}

// GetGitBranchByID mirrors get_git_branch_by_id.
func (s *GitBranchService) GetGitBranchByID(ctx context.Context, gitBranchID string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	branches, err := gitBranchRepo.FindAll(ctx)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	var gitBranch *entities.GitBranch
	for _, branch := range branches {
		if branch.GetEntityID() == gitBranchID {
			gitBranch = branch
			break
		}
	}
	if gitBranch == nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch %s not found", gitBranchID)), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("project_id", gitBranch.ProjectID)
	result.Set("branch_name", gitBranch.Name)
	result.Set("git_branch", zpGitBranchBranchDict(gitBranch))
	return result, nil
}

// UpdateGitBranch mirrors update_git_branch.
func (s *GitBranchService) UpdateGitBranch(ctx context.Context, gitBranchID string, branchName, description *string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	branches, err := gitBranchRepo.FindAll(ctx)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	var gitBranch *entities.GitBranch
	for _, branch := range branches {
		if branch.GetEntityID() == gitBranchID {
			gitBranch = branch
			break
		}
	}
	if gitBranch == nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch with ID %s not found", gitBranchID)), nil
	}
	if branchName == nil && description == nil {
		return zpGitBranchFailure("No fields to update. Provide branch_name and/or description."), nil
	}
	updatedFields := []string{}
	if branchName != nil {
		gitBranch.Name = *branchName
		updatedFields = append(updatedFields, "name")
	}
	if description != nil {
		gitBranch.Description = *description
		updatedFields = append(updatedFields, "description")
	}
	success, err := gitBranchRepo.Update(ctx, gitBranch)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if !success {
		return zpGitBranchFailure("Failed to update git branch"), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("git_branch", zpGitBranchBranchDict(gitBranch))
	result.Set("updated_fields", updatedFields)
	return result, nil
}

// AssignAgentToBranch mirrors assign_agent_to_branch.
func (s *GitBranchService) AssignAgentToBranch(ctx context.Context, projectID, agentID, branchName string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	gitBranch, err := gitBranchRepo.FindByName(ctx, projectID, branchName)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if gitBranch == nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch %s not found in project %s", branchName, projectID)), nil
	}
	if gitBranch.AssignedAgents == nil {
		gitBranch.AssignedAgents = []string{}
	}
	alreadyAssigned := false
	for _, assigned := range gitBranch.AssignedAgents {
		if assigned == agentID {
			alreadyAssigned = true
			break
		}
	}
	if !alreadyAssigned {
		gitBranch.AssignedAgents = append(gitBranch.AssignedAgents, agentID)
	}
	// Python falls back to repository.update when the repository has no assign_agent;
	// zpGitBranchRepository always exposes AssignAgent, so that branch is unreachable.
	success, err := gitBranchRepo.AssignAgent(ctx, projectID, gitBranch.GetEntityID(), agentID)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if !success {
		return zpGitBranchFailure(fmt.Sprintf("Failed to assign agent %s to git branch %s", agentID, branchName)), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", fmt.Sprintf("Agent %s assigned to git branch %s", agentID, branchName))
	return result, nil
}

// UnassignAgentFromBranch mirrors unassign_agent_from_branch.
func (s *GitBranchService) UnassignAgentFromBranch(ctx context.Context, projectID, agentID, branchName string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	gitBranch, err := gitBranchRepo.FindByName(ctx, projectID, branchName)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if gitBranch == nil {
		return zpGitBranchFailure(fmt.Sprintf("Git branch %s not found in project %s", branchName, projectID)), nil
	}
	for i, assigned := range gitBranch.AssignedAgents {
		if assigned == agentID {
			gitBranch.AssignedAgents = append(gitBranch.AssignedAgents[:i], gitBranch.AssignedAgents[i+1:]...)
			break
		}
	}
	success, err := gitBranchRepo.UnassignAgent(ctx, projectID, gitBranch.GetEntityID())
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if !success {
		return zpGitBranchFailure(fmt.Sprintf("Failed to unassign agent %s from git branch %s", agentID, branchName)), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", fmt.Sprintf("Agent %s unassigned from git branch %s", agentID, branchName))
	return result, nil
}

// GetBranchStatistics mirrors get_branch_statistics.
func (s *GitBranchService) GetBranchStatistics(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	statistics, err := gitBranchRepo.GetBranchStatistics(ctx, projectID, gitBranchID)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if statistics != nil {
		if errValue, ok := statistics["error"]; ok {
			return zpGitBranchFailure(value_objects.PyStr(errValue)), nil
		}
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("statistics", statistics)
	return result, nil
}

// ArchiveBranch mirrors archive_branch. Python treats the repository result as a bool, so
// the ported map-returning ArchiveBranch is truthiness-tested (a non-empty map -- including
// one whose "success" is false -- always passes, faithfully preserving the Python bug).
func (s *GitBranchService) ArchiveBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	success, err := gitBranchRepo.ArchiveBranch(ctx, projectID, gitBranchID)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if !value_objects.PyTruthy(success) {
		return zpGitBranchFailure(fmt.Sprintf("Failed to archive git branch %s", gitBranchID)), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", fmt.Sprintf("Git branch %s archived successfully", gitBranchID))
	return result, nil
}

// RestoreBranch mirrors restore_branch (same truthiness quirk as ArchiveBranch).
func (s *GitBranchService) RestoreBranch(ctx context.Context, projectID, gitBranchID string) (*entities.OrderedMap[any], error) {
	gitBranchRepo := s.zpGitBranchUserScopedGitBranchRepo()
	success, err := gitBranchRepo.RestoreBranch(ctx, projectID, gitBranchID)
	if err != nil {
		return zpGitBranchFailure(err.Error()), nil
	}
	if !value_objects.PyTruthy(success) {
		return zpGitBranchFailure(fmt.Sprintf("Failed to restore git branch %s", gitBranchID)), nil
	}
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("message", fmt.Sprintf("Git branch %s restored successfully", gitBranchID))
	return result, nil
}

// GitBranchRepositoryPort is the repository surface GitBranchService needs.
type GitBranchRepositoryPort = zpGitBranchRepository

// NewGitBranchService builds the service for the composition root. contextService and
// notifier may be nil.
func NewGitBranchService(projectRepo repositories.ProjectRepository, gitBranchRepo GitBranchRepositoryPort, contextService zpGitBranchContextService, userID *string, notifier zpGitBranchWebSocketNotifier) (*GitBranchService, error) {
	return zpGitBranchNewService(projectRepo, gitBranchRepo, contextService, userID, notifier)
}
