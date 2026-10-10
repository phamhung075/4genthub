package services

import (
	"testing"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

// Embedding the domain interface satisfies it without implementing every method; the
// methods are never called in these tests.
type repoProviderFakeContextRepo struct {
	domainrepos.ContextRepository
	name string
}

type repoProviderFakeTaskFactory struct {
	projectID  string
	branchName string
	userID     *string
}

func (f *repoProviderFakeTaskFactory) CreateRepository(projectID, gitBranchName string, userID *string) (domainrepos.TaskRepository, error) {
	f.projectID, f.branchName, f.userID = projectID, gitBranchName, userID
	return nil, nil
}

type repoProviderFakeSubtaskFactory struct {
	ormUserID     *string
	projectID     string
	branchName    string
	calledORM     bool
	calledProject bool
}

func (f *repoProviderFakeSubtaskFactory) CreateORMSubtaskRepository(userID *string) (domainrepos.SubtaskRepository, error) {
	f.ormUserID = userID
	f.calledORM = true
	return nil, nil
}

func (f *repoProviderFakeSubtaskFactory) CreateSubtaskRepository(projectID, gitBranchName string, userID *string) (domainrepos.SubtaskRepository, error) {
	f.projectID, f.branchName = projectID, gitBranchName
	f.calledProject = true
	return nil, nil
}

type repoProviderFakeBackend struct {
	ormTaskSession     any
	ormTaskBranchName  string
	ormTaskUserID      *string
	taskFactory        *repoProviderFakeTaskFactory
	subtaskFactory     *repoProviderFakeSubtaskFactory
	globalContextCalls int
	globalContextRepo  *repoProviderFakeContextRepo
	gitBranchUserID    *string
	projectUserID      *string
}

func (b *repoProviderFakeBackend) NewTaskRepositoryFactory() repoProviderTaskRepositoryFactory {
	return b.taskFactory
}

func (b *repoProviderFakeBackend) NewORMTaskRepository(session any, gitBranchID *string, projectID *string, gitBranchName string, userID *string) (domainrepos.TaskRepository, error) {
	b.ormTaskSession = session
	b.ormTaskBranchName = gitBranchName
	b.ormTaskUserID = userID
	return nil, nil
}

func (b *repoProviderFakeBackend) NewSubtaskRepositoryFactory() repoProviderSubtaskRepositoryFactory {
	return b.subtaskFactory
}

func (b *repoProviderFakeBackend) CreateProjectRepository(userID *string) (domainrepos.ProjectRepository, error) {
	b.projectUserID = userID
	return nil, nil
}

func (b *repoProviderFakeBackend) CreateGitBranchRepository(userID *string) (domainrepos.GitBranchRepository, error) {
	b.gitBranchUserID = userID
	return nil, nil
}

func (b *repoProviderFakeBackend) NewGlobalContextRepository(session any) (domainrepos.ContextRepository, error) {
	b.globalContextCalls++
	return b.globalContextRepo, nil
}

func (b *repoProviderFakeBackend) NewProjectContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (b *repoProviderFakeBackend) NewBranchContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (b *repoProviderFakeBackend) NewTaskContextRepository(session any) (domainrepos.ContextRepository, error) {
	return nil, nil
}

func (b *repoProviderFakeBackend) NewTokenRepository(session any) (domainrepos.ITokenRepository, error) {
	return nil, nil
}

var _ repoProviderFactoryBackend = (*repoProviderFakeBackend)(nil)

func repoProviderInstallBackend(backend repoProviderFactoryBackend) {
	repoProviderInstance = nil
	repoProviderFactoryBackendProvider = func() repoProviderFactoryBackend { return backend }
}

func TestRepoProviderGetTaskRepositoryDefaultsBranchName(t *testing.T) {
	backend := &repoProviderFakeBackend{}
	repoProviderInstallBackend(backend)
	provider := RepositoryProviderService{}.GetInstance()
	userID := "u1"

	if _, err := provider.GetTaskRepository(nil, nil, &userID, nil); err != nil {
		t.Fatalf("GetTaskRepository error: %v", err)
	}
	if backend.ormTaskBranchName != "main" {
		t.Fatalf("ORM branch name = %q, want main", backend.ormTaskBranchName)
	}
	if backend.ormTaskUserID == nil || *backend.ormTaskUserID != "u1" {
		t.Fatalf("ORM user id = %v, want u1", backend.ormTaskUserID)
	}
}

func TestRepoProviderGetTaskRepositoryUsesFactoryWhenProjectGiven(t *testing.T) {
	factory := &repoProviderFakeTaskFactory{}
	backend := &repoProviderFakeBackend{taskFactory: factory}
	repoProviderInstallBackend(backend)
	provider := RepositoryProviderService{}.GetInstance()

	projectID := "p1"
	branchName := "dev"
	if _, err := provider.GetTaskRepository(&projectID, &branchName, nil, nil); err != nil {
		t.Fatalf("GetTaskRepository error: %v", err)
	}
	if factory.projectID != "p1" || factory.branchName != "dev" {
		t.Fatalf("factory args = (%q, %q), want (p1, dev)", factory.projectID, factory.branchName)
	}
}

func TestRepoProviderGetSubtaskRepositoryBranches(t *testing.T) {
	factory := &repoProviderFakeSubtaskFactory{}
	backend := &repoProviderFakeBackend{subtaskFactory: factory}
	repoProviderInstallBackend(backend)
	provider := RepositoryProviderService{}.GetInstance()

	if _, err := provider.GetSubtaskRepository(nil, nil, nil, nil); err != nil {
		t.Fatalf("GetSubtaskRepository error: %v", err)
	}
	if !factory.calledORM {
		t.Fatalf("expected create_orm_subtask_repository for nil project_id")
	}

	projectID := "p1"
	projectFactory := &repoProviderFakeSubtaskFactory{}
	backend.subtaskFactory = projectFactory
	if _, err := provider.GetSubtaskRepository(&projectID, nil, nil, nil); err != nil {
		t.Fatalf("GetSubtaskRepository error: %v", err)
	}
	if !projectFactory.calledProject || projectFactory.projectID != "p1" || projectFactory.branchName != "main" {
		t.Fatalf("project factory args = (%v, %q, %q), want (true, p1, main)",
			projectFactory.calledProject, projectFactory.projectID, projectFactory.branchName)
	}
}

func TestRepoProviderCachesGlobalContextRepository(t *testing.T) {
	contextRepo := &repoProviderFakeContextRepo{name: "global"}
	backend := &repoProviderFakeBackend{globalContextRepo: contextRepo}
	repoProviderInstallBackend(backend)
	provider := RepositoryProviderService{}.GetInstance()

	first, err := provider.GetGlobalContextRepository(nil)
	if err != nil {
		t.Fatalf("GetGlobalContextRepository error: %v", err)
	}
	second, err := provider.GetGlobalContextRepository(nil)
	if err != nil {
		t.Fatalf("GetGlobalContextRepository error: %v", err)
	}
	if first != second {
		t.Fatalf("global context repository was not cached")
	}
	if backend.globalContextCalls != 1 {
		t.Fatalf("global context constructor calls = %d, want 1", backend.globalContextCalls)
	}
}

func TestRepoProviderClearCacheRebuildsContextRepository(t *testing.T) {
	contextRepo := &repoProviderFakeContextRepo{name: "global"}
	backend := &repoProviderFakeBackend{globalContextRepo: contextRepo}
	repoProviderInstallBackend(backend)
	provider := RepositoryProviderService{}.GetInstance()

	if _, err := provider.GetGlobalContextRepository(nil); err != nil {
		t.Fatalf("GetGlobalContextRepository error: %v", err)
	}
	provider.ClearCache()
	if _, err := provider.GetGlobalContextRepository(nil); err != nil {
		t.Fatalf("GetGlobalContextRepository error: %v", err)
	}
	if backend.globalContextCalls != 2 {
		t.Fatalf("global context constructor calls = %d, want 2", backend.globalContextCalls)
	}
}

func TestRepoProviderGetInstanceSingleton(t *testing.T) {
	backend := &repoProviderFakeBackend{}
	repoProviderInstallBackend(backend)
	first := RepositoryProviderService{}.GetInstance()
	second := RepositoryProviderService{}.GetInstance()
	if first != second {
		t.Fatalf("GetInstance returned different instances")
	}
}
