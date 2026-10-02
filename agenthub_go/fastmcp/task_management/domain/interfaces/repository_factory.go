package interfaces

import "context"

// IRepository is the generic repository contract.
type IRepository interface {
	FindByID(ctx context.Context, id any) (any, error)
	FindAll(ctx context.Context) ([]any, error)
	Save(ctx context.Context, entity any) (any, error)
	Delete(ctx context.Context, entity any) (bool, error)
}

// ITaskRepository is the task repository contract.
type ITaskRepository interface{ IRepository }

// IProjectRepository is the project repository contract.
type IProjectRepository interface{ IRepository }

// IGitBranchRepository is the git branch repository contract.
type IGitBranchRepository interface{ IRepository }

// IAgentRepository is the agent repository contract.
type IAgentRepository interface{ IRepository }

// IContextRepository is the context repository contract.
type IContextRepository interface{ IRepository }

// ISubtaskRepository is the subtask repository contract.
type ISubtaskRepository interface{ IRepository }

// IRepositoryFactory creates every repository kind.
type IRepositoryFactory interface {
	CreateTaskRepository() ITaskRepository
	CreateProjectRepository() IProjectRepository
	CreateGitBranchRepository() IGitBranchRepository
	CreateAgentRepository() IAgentRepository
	CreateContextRepository() IContextRepository
	CreateSubtaskRepository() ISubtaskRepository
}

// ITaskRepositoryFactory creates task repositories.
type ITaskRepositoryFactory interface{ CreateRepository() ITaskRepository }

// IProjectRepositoryFactory creates project repositories.
type IProjectRepositoryFactory interface{ CreateRepository() IProjectRepository }

// IGitBranchRepositoryFactory creates git branch repositories.
type IGitBranchRepositoryFactory interface{ CreateRepository() IGitBranchRepository }
