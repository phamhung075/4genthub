package httpapp

import (
	"context"

	"agenthub/fastmcp/auth/middleware"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/hooks"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"

	"agenthub/fastmcp/server/routes"
)

// branchGetter is the GitBranchGetter the use cases read branches through.
type branchGetter struct{ repo gitBranchRepo }

func (g branchGetter) GetByID(ctx context.Context, branchID string) (*entities.GitBranch, error) {
	return g.repo.FindByID(ctx, branchID, nil)
}

// contextReader adapts the unified context facade to use_cases.GetTaskContextService.
type contextReader struct {
	facade *facades.UnifiedContextFacade
	userID *string
}

func (c contextReader) GetContext(ctx context.Context, level, contextID string, includeInherited bool) (*entities.OrderedMap[any], error) {
	return c.facade.GetContext(ctx, level, contextID, includeInherited, false, c.userID)
}

// branchRepoWithProject adds FirstProjectID to the branch repository.
type branchRepoWithProject struct {
	gitBranchRepo
	sessions *database.SessionManager
}

func (b branchRepoWithProject) FirstProjectID(ctx context.Context) (string, bool, error) {
	var id string
	found := false
	err := b.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		err := s.QueryRowContext(ctx, `SELECT id FROM projects LIMIT 1`).Scan(&id)
		if err != nil {
			return nil // no project (sql.ErrNoRows) is the "no project" case
		}
		found = true
		return nil
	})
	return id, found, err
}

// routesBroadcaster adapts the routes package's package-level broadcast to the port the application
// layer declares. Go interfaces are implicit but ordinary functions are not, so the port needs exactly
// one adapter and this is it.
type routesBroadcaster struct{}

func (routesBroadcaster) BroadcastDataChange(
	ctx context.Context, eventType, entityType, entityID, userID string, data any,
	metadata *entities.OrderedMap[any],
) error {
	return routes.BroadcastDataChange(ctx, eventType, entityType, entityID, userID, data, metadata)
}

// newTaskNotifier is the notifier the task and subtask facades publish through, and it exists because
// the ZERO-VALUED service it replaces looked wired and was not: `&services.WebSocketNotificationService{}`
// has a non-nil Notifier field, so the hook's `if h.Notifier == nil` check passed, while Broker was nil,
// so SyncBroadcastTask returned at `if s.Broker == nil` for EVERY task and subtask event. The app looked
// half-alive because of it - on the same socket, in the same capture, seat frames arrived (they go
// through routes.BroadcastDataChange directly) and task frames never did - and NO TEST COULD SEE IT,
// because every test constructs the service WITH a fake broker.
//
// The Provider reads the context the notification metadata is enriched from (titles, parent branch);
// absent, the service falls back to the Python's fallback contexts, but a production app has the real
// one available and there is no reason to run degraded.
func newTaskNotifier(sessions *database.SessionManager) *services.WebSocketNotificationService {
	return &services.WebSocketNotificationService{
		Provider: &services.DBWebSocketContextProvider{Sessions: sessions},
		Broker:   routesBroadcaster{},
	}
}

// taskFacadeProvider is FacadeService.get_task_facade: it builds the task facade, use cases
// and hooks for one user, project and branch.
type taskFacadeProvider struct {
	sessions   *database.SessionManager
	ctxFactory *factories.UnifiedContextFacadeFactory
	notifier   *services.WebSocketNotificationService
}

func (p taskFacadeProvider) TaskFacade(ctx context.Context, userID, projectID, gitBranchID *string) (*facades.TaskApplicationFacade, error) {
	taskRepo, err := infrarepos.NewORMTaskRepository(p.sessions, gitBranchID, projectID, nil, userID, false)
	if err != nil {
		return nil, err
	}
	subtaskRepo, err := infrarepos.NewORMSubtaskRepository(p.sessions, userID)
	if err != nil {
		return nil, err
	}
	branchRepo, err := newGitBranchRepo(p.sessions, userID)
	if err != nil {
		return nil, err
	}
	projectRepo, err := newProjectRepo(p.sessions, userID)
	if err != nil {
		return nil, err
	}
	taskContextRepo, err := infrarepos.NewTaskContextRepository(p.sessions, userID)
	if err != nil {
		return nil, err
	}
	unified, err := p.ctxFactory.CreateFacade(ctx, userID, projectID, gitBranchID)
	if err != nil {
		return nil, err
	}

	taskHooks := &hooks.TaskHooks{ContextFactory: p.ctxFactory, Notifier: p.notifier, TaskRepository: taskRepo}
	getter := branchGetter{branchRepo}
	branchWithProject := branchRepoWithProject{branchRepo, p.sessions}

	deps := facades.TaskFacadeDeps{
		GitBranchRepository: branchWithProject,
		ContextService:      unified,
		Notifier:            p.notifier,
		CreateTask:          use_cases.NewCreateTaskUseCase(taskRepo, getter).WithHooks(taskHooks),
		UpdateTask:          use_cases.NewUpdateTaskUseCase(taskRepo, getter).WithHooks(taskHooks),
		GetTask:             use_cases.NewGetTaskUseCase(taskRepo, contextReader{unified, userID}, getter),
		DeleteTask:          use_cases.NewDeleteTaskUseCase(taskRepo, subtaskRepo, cascadeBranchRepo{branchRepo}, projectRepo, nil),
		CompleteTask:        use_cases.NewCompleteTaskUseCase(taskRepo, subtaskRepo, legacyTaskContextRepo{taskContextRepo}, completeContextFactory{p.ctxFactory, userID}).WithHooks(taskHooks),
		SearchTasks:         use_cases.NewSearchTasksUseCase(taskRepo),
		NextTask:            use_cases.NewNextTaskUseCase(taskRepo, nil),
		DependencyResolver:  services.NewDependencyResolverService(taskRepo, userID),
		ApplyContextFormat:  factories.ContextResponseApplyToTaskResponse,
		CurrentUserID:       middleware.GetCurrentUserID,
		ProjectBranchLookup: func(ctx context.Context, id string) (*entities.OrderedMap[any], error) {
			return nil, &AttributeError{"'ProjectManagementService' object has no attribute 'get_git_branch_by_id'"}
		},
		LoadSubtasks: func(ctx context.Context, user *string, parent value_objects.TaskId) ([]*entities.Subtask, error) {
			repo, err := infrarepos.NewORMSubtaskRepository(p.sessions, user)
			if err != nil {
				return nil, err
			}
			return repo.FindByParentTaskID(ctx, parent)
		},
		NewMinimalLister: func(branch, user *string) (facades.TaskMinimalLister, error) {
			return infrarepos.NewORMTaskRepository(p.sessions, branch, nil, nil, user, true)
		},
	}
	syncSvc, err := services.NewTaskContextSyncService(taskRepo, nil, userID, unified)
	if err != nil {
		return nil, err
	}
	deps.ContextSync = syncSvc
	return facades.NewTaskApplicationFacade(taskRepo, subtaskRepo, deps), nil
}

// cascadeBranchRepo adapts the branch repository to services.CascadeBranchRepository.
type cascadeBranchRepo struct{ gitBranchRepo }

func (c cascadeBranchRepo) FindByID(ctx context.Context, id string) (*entities.GitBranch, error) {
	return c.gitBranchRepo.FindByID(ctx, id, nil)
}

func (c cascadeBranchRepo) FindByProjectID(ctx context.Context, projectID string) ([]*entities.GitBranch, error) {
	return c.FindAllByProject(ctx, projectID)
}

func (c cascadeBranchRepo) Delete(ctx context.Context, id string) (bool, error) {
	return c.DeleteBranch(ctx, id)
}

// legacyTaskContextRepo is the legacy TaskContextRepository.get existence check.
type legacyTaskContextRepo struct {
	repo *infrarepos.TaskContextRepository
}

func (l legacyTaskContextRepo) Get(contextID string) (map[string]any, error) {
	e, err := l.repo.Get(context.Background(), contextID)
	if err != nil || e == nil {
		return nil, err
	}
	return map[string]any{"id": contextID}, nil
}

func orderedToMap(m *entities.OrderedMap[any]) map[string]any {
	if m == nil {
		return map[string]any{}
	}
	out := make(map[string]any, m.Len())
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out[k] = v
	}
	return out
}

// completeContextFactory builds the unified context facade the completion flow uses.
type completeContextFactory struct {
	factory *factories.UnifiedContextFacadeFactory
	userID  *string
}

type completeContextFacade struct{ f *facades.UnifiedContextFacade }

func (c completeContextFacade) CreateContext(level, contextID string, data *entities.OrderedMap[any]) map[string]any {
	r, err := c.f.CreateContext(context.Background(), level, contextID, data, nil)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error()}
	}
	return orderedToMap(r)
}

func (c completeContextFacade) GetContext(level, contextID string) map[string]any {
	r, err := c.f.GetContext(context.Background(), level, contextID, false, false, nil)
	if err != nil {
		return map[string]any{"success": false, "error": err.Error()}
	}
	return orderedToMap(r)
}

func (c completeContextFacade) UpdateContext(level, contextID string, data *entities.OrderedMap[any], propagateChanges bool) {
	_, _ = c.f.UpdateContext(context.Background(), level, contextID, data, propagateChanges)
}

func (f completeContextFactory) CreateFacade(gitBranchID *string, projectID *string) use_cases.CompleteTaskContextFacade {
	facade, err := f.factory.CreateFacade(context.Background(), f.userID, projectID, gitBranchID)
	if err != nil {
		return nil
	}
	return completeContextFacade{facade}
}

var _ use_cases.CompleteTaskContextFacadeFactory = completeContextFactory{}

// AttributeError is Python's AttributeError: ProjectManagementService has no
// get_git_branch_by_id, so the facade's "project manager" fallback always raises it.
type AttributeError struct{ msg string }

func (e *AttributeError) Error() string { return e.msg }
