// repository_factory_adapter.go ports task_management/infrastructure/adapters/repository_factory_adapter.py.
package adapters

import (
	"context"

	"agenthub/fastmcp/task_management/domain/interfaces"
)

type baseRepoAdapter struct {
	repo any
}

func (a *baseRepoAdapter) FindByID(ctx context.Context, id any) (any, error) {
	if r, ok := a.repo.(interfaces.IRepository); ok {
		return r.FindByID(ctx, id)
	}
	return nil, nil
}

func (a *baseRepoAdapter) FindAll(ctx context.Context) ([]any, error) {
	if r, ok := a.repo.(interfaces.IRepository); ok {
		return r.FindAll(ctx)
	}
	return nil, nil
}

func (a *baseRepoAdapter) Save(ctx context.Context, entity any) (any, error) {
	if r, ok := a.repo.(interfaces.IRepository); ok {
		return r.Save(ctx, entity)
	}
	return entity, nil
}

func (a *baseRepoAdapter) Delete(ctx context.Context, entity any) (bool, error) {
	if r, ok := a.repo.(interfaces.IRepository); ok {
		return r.Delete(ctx, entity)
	}
	return true, nil
}

type TaskRepositoryAdapter struct {
	baseRepoAdapter
}

func NewTaskRepositoryAdapter(repo any) *TaskRepositoryAdapter {
	return &TaskRepositoryAdapter{baseRepoAdapter: baseRepoAdapter{repo: repo}}
}

type ProjectRepositoryAdapter struct {
	baseRepoAdapter
}

func NewProjectRepositoryAdapter(repo any) *ProjectRepositoryAdapter {
	return &ProjectRepositoryAdapter{baseRepoAdapter: baseRepoAdapter{repo: repo}}
}

type GitBranchRepositoryAdapter struct {
	baseRepoAdapter
}

func NewGitBranchRepositoryAdapter(repo any) *GitBranchRepositoryAdapter {
	return &GitBranchRepositoryAdapter{baseRepoAdapter: baseRepoAdapter{repo: repo}}
}

type AgentRepositoryAdapter struct {
	baseRepoAdapter
}

func NewAgentRepositoryAdapter(repo any) *AgentRepositoryAdapter {
	return &AgentRepositoryAdapter{baseRepoAdapter: baseRepoAdapter{repo: repo}}
}

type ContextRepositoryAdapter struct {
	baseRepoAdapter
}

func NewContextRepositoryAdapter(repo any) *ContextRepositoryAdapter {
	return &ContextRepositoryAdapter{baseRepoAdapter: baseRepoAdapter{repo: repo}}
}

type SubtaskRepositoryAdapter struct {
	baseRepoAdapter
}

func NewSubtaskRepositoryAdapter(repo any) *SubtaskRepositoryAdapter {
	return &SubtaskRepositoryAdapter{baseRepoAdapter: baseRepoAdapter{repo: repo}}
}

type RepositoryFactoryAdapter struct{}

func NewRepositoryFactoryAdapter() *RepositoryFactoryAdapter {
	return &RepositoryFactoryAdapter{}
}

func (f *RepositoryFactoryAdapter) CreateTaskRepository() interfaces.ITaskRepository {
	return NewTaskRepositoryAdapter(nil)
}

func (f *RepositoryFactoryAdapter) CreateProjectRepository() interfaces.IProjectRepository {
	return NewProjectRepositoryAdapter(nil)
}

func (f *RepositoryFactoryAdapter) CreateGitBranchRepository() interfaces.IGitBranchRepository {
	return NewGitBranchRepositoryAdapter(nil)
}

func (f *RepositoryFactoryAdapter) CreateAgentRepository() interfaces.IAgentRepository {
	return NewAgentRepositoryAdapter(nil)
}

func (f *RepositoryFactoryAdapter) CreateContextRepository() interfaces.IContextRepository {
	return NewContextRepositoryAdapter(nil)
}

func (f *RepositoryFactoryAdapter) CreateSubtaskRepository() interfaces.ISubtaskRepository {
	return NewSubtaskRepositoryAdapter(nil)
}

type TaskRepositoryFactoryAdapter struct{}

func NewTaskRepositoryFactoryAdapter() *TaskRepositoryFactoryAdapter {
	return &TaskRepositoryFactoryAdapter{}
}

func (f *TaskRepositoryFactoryAdapter) CreateRepository() interfaces.ITaskRepository {
	return NewTaskRepositoryAdapter(nil)
}

type ProjectRepositoryFactoryAdapter struct{}

func NewProjectRepositoryFactoryAdapter() *ProjectRepositoryFactoryAdapter {
	return &ProjectRepositoryFactoryAdapter{}
}

func (f *ProjectRepositoryFactoryAdapter) CreateRepository() interfaces.IProjectRepository {
	return NewProjectRepositoryAdapter(nil)
}

type GitBranchRepositoryFactoryAdapter struct{}

func NewGitBranchRepositoryFactoryAdapter() *GitBranchRepositoryFactoryAdapter {
	return &GitBranchRepositoryFactoryAdapter{}
}

func (f *GitBranchRepositoryFactoryAdapter) CreateRepository() interfaces.IGitBranchRepository {
	return NewGitBranchRepositoryAdapter(nil)
}
