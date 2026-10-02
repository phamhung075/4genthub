package services

import (
	"testing"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
	domainServices "agenthub/fastmcp/task_management/domain/services"
)

type statsInitTaskRepo struct {
	tasks []domainServices.StatusedTask
}

func (f *statsInitTaskRepo) FindByGitBranchID(branchID string) ([]domainServices.StatusedTask, error) {
	return f.tasks, nil
}

type statsInitTask struct{ status any }

func (t *statsInitTask) StatusValue() any { return t.status }

type statsInitBranch struct{ id string }

func (b *statsInitBranch) BranchID() string { return b.id }

type statsInitBranchRepo struct {
	branches []domainServices.IdentifiedBranch
	updates  map[string]map[string]any
}

func (f *statsInitBranchRepo) Get(branchID string) (any, error) { return struct{}{}, nil }

func (f *statsInitBranchRepo) Update(branchID string, updates map[string]any) (bool, error) {
	if f.updates == nil {
		f.updates = map[string]map[string]any{}
	}
	f.updates[branchID] = updates
	return true, nil
}

func (f *statsInitBranchRepo) FindByProjectID(projectID string) ([]domainServices.IdentifiedBranch, error) {
	return f.branches, nil
}

func (f *statsInitBranchRepo) GetAll() ([]domainServices.IdentifiedBranch, error) {
	return f.branches, nil
}

var _ domainServices.TaskRepositoryProtocol = (*statsInitTaskRepo)(nil)
var _ domainServices.GitBranchRepositoryProtocol = (*statsInitBranchRepo)(nil)

// statsInitBackend returns nil repositories; the initializer passes them through to an
// already-registered integration service.
type statsInitBackend struct{}

func (statsInitBackend) NewTaskRepositoryFactory() repoProviderTaskRepositoryFactory {
	return nil
}

func (statsInitBackend) NewORMTaskRepository(session any, gitBranchID *string, projectID *string, gitBranchName string, userID *string) (domainrepos.TaskRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewSubtaskRepositoryFactory() repoProviderSubtaskRepositoryFactory {
	return nil
}

func (statsInitBackend) CreateProjectRepository(userID *string) (domainrepos.ProjectRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewAgentRepositoryFactory() repoProviderAgentRepositoryFactory {
	return nil
}

func (statsInitBackend) CreateGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewGlobalContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewProjectContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewBranchContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewTaskContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (statsInitBackend) NewTokenRepository(session any) (domainrepos.ITokenRepository, error) {
	return nil, nil
}

var _ repoProviderFactoryBackend = statsInitBackend{}

func statsInitReset() {
	statsInitInitialized = false
	bsiSvcIntegrationService = nil
	repoProviderInstance = nil
	repoProviderFactoryBackendProvider = func() repoProviderFactoryBackend { return statsInitBackend{} }
}

func TestStatsInitInitializeSetsFlag(t *testing.T) {
	bsiSvcClearHandlers()
	statsInitReset()
	defer func() {
		statsInitInitialized = false
		bsiSvcIntegrationService = nil
		repoProviderInstance = nil
		repoProviderFactoryBackendProvider = nil
		bsiSvcClearHandlers()
	}()

	// Pre-register the integration service so its typed repositories need not be built.
	bsiSvcIntegrationService = NewBranchStatisticsIntegrationService(&statsInitTaskRepo{}, &statsInitBranchRepo{})

	if err := (StatisticsInitializer{}).Initialize(); err != nil {
		t.Fatalf("Initialize error: %v", err)
	}
	if !(StatisticsInitializer{}).IsInitialized() {
		t.Fatalf("IsInitialized = false, want true")
	}
	// Second call is a no-op.
	if err := (StatisticsInitializer{}).Initialize(); err != nil {
		t.Fatalf("second Initialize error: %v", err)
	}
}

func TestStatsInitRecalculateAllBranches(t *testing.T) {
	bsiSvcClearHandlers()
	statsInitReset()
	defer func() {
		statsInitInitialized = false
		bsiSvcIntegrationService = nil
		repoProviderInstance = nil
		repoProviderFactoryBackendProvider = nil
		bsiSvcClearHandlers()
	}()

	taskRepo := &statsInitTaskRepo{tasks: []domainServices.StatusedTask{&statsInitTask{status: "done"}}}
	branchRepo := &statsInitBranchRepo{branches: []domainServices.IdentifiedBranch{&statsInitBranch{id: "b1"}}}
	bsiSvcIntegrationService = NewBranchStatisticsIntegrationService(taskRepo, branchRepo)

	results, err := (StatisticsInitializer{}).RecalculateAllBranches(nil)
	if err != nil {
		t.Fatalf("RecalculateAllBranches error: %v", err)
	}
	got, ok := results["b1"]
	if !ok {
		t.Fatalf("results missing branch b1: %v", results)
	}
	if got.TaskCount != 1 || got.CompletedTaskCount != 1 || got.ProgressPercentage != 100.0 {
		t.Fatalf("branch b1 stats = %+v", got)
	}
	if updates := branchRepo.updates["b1"]["task_count"]; updates != 1 {
		t.Fatalf("branch update task_count = %v, want 1", updates)
	}
}

func TestStatsInitIsInitializedDefaultFalse(t *testing.T) {
	statsInitInitialized = false
	if (StatisticsInitializer{}).IsInitialized() {
		t.Fatalf("IsInitialized = true, want false")
	}
}
