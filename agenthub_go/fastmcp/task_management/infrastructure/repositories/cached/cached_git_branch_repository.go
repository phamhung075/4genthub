package cached

// Cached Git Branch Repository (Python cached/cached_git_branch_repository.py). The redis-py
// client is injected as a CacheClient; a nil client disables caching. Python's async methods
// are plain synchronous Go methods.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// CachedGitBranchBaseRepository is the underlying git branch repository contract.
type CachedGitBranchBaseRepository interface {
	GetByID(ctx context.Context, branchID string) (*entities.GitBranch, error)
	GetByProjectID(ctx context.Context, projectID string) ([]*entities.GitBranch, error)
	FindByName(ctx context.Context, projectID, branchName string) (*entities.GitBranch, error)
	CreateBranch(ctx context.Context, projectID, branchName, description string) (any, error)
	CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (map[string]any, error)
	UpdateBranch(ctx context.Context, branch *entities.GitBranch) (*entities.GitBranch, error)
	DeleteBranch(ctx context.Context, branchID string) (bool, error)
	ArchiveBranch(ctx context.Context, branchID string) (bool, error)
	RestoreBranch(ctx context.Context, branchID string) (bool, error)
}

// cachedUserIDHolder lets UserID proxy the base repository's user id when it exposes one.
type cachedUserIDHolder interface{ GetUserID() *string }

// CachedGitBranchRepository wraps a git branch repository with namespaced caching.
type CachedGitBranchRepository struct {
	BaseRepo CachedGitBranchBaseRepository
	TTL      int
	Enabled  bool
	cache    cachedCache
}

// NewCachedGitBranchRepository builds the wrapper; cache nil disables caching.
func NewCachedGitBranchRepository(baseRepo CachedGitBranchBaseRepository, cache CacheClient, getenv func(string) string) (*CachedGitBranchRepository, error) {
	ttl, err := cachedTTLFromEnv(getenv)
	if err != nil {
		return nil, err
	}
	c := newCachedCache(cache, "gitbranch", ttl)
	return &CachedGitBranchRepository{BaseRepo: baseRepo, TTL: ttl, Enabled: c.enabled(), cache: c}, nil
}

// UserID proxies the base repository user id for authentication checks.
func (r *CachedGitBranchRepository) UserID() *string {
	if holder, ok := r.BaseRepo.(cachedUserIDHolder); ok {
		return holder.GetUserID()
	}
	return nil
}

func (r *CachedGitBranchRepository) invalidateKey(key string) {
	if r.Enabled {
		r.cache.invalidateKey(key)
	}
}

func (r *CachedGitBranchRepository) invalidatePattern(pattern string) {
	if r.Enabled {
		r.cache.invalidatePattern(pattern)
	}
}

func (r *CachedGitBranchRepository) getCached(key string) any { return r.cache.get(key) }

func (r *CachedGitBranchRepository) setCached(key string, value any) { r.cache.set(key, value) }

// GetByID returns a git branch by ID with caching.
func (r *CachedGitBranchRepository) GetByID(ctx context.Context, branchID string) (*entities.GitBranch, error) {
	cacheKey := "id:" + branchID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if branch, ok := cached.(*entities.GitBranch); ok {
			return branch, nil
		}
	}
	result, err := r.BaseRepo.GetByID(ctx, branchID)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// GetByProjectID returns all branches for a project with caching.
func (r *CachedGitBranchRepository) GetByProjectID(ctx context.Context, projectID string) ([]*entities.GitBranch, error) {
	cacheKey := "project:" + projectID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if list, ok := cached.([]*entities.GitBranch); ok {
			return list, nil
		}
	}
	result, err := r.BaseRepo.GetByProjectID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if len(result) > 0 {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// FindByName finds a branch by name within a project with caching.
func (r *CachedGitBranchRepository) FindByName(ctx context.Context, projectID, branchName string) (*entities.GitBranch, error) {
	cacheKey := "project:" + projectID + ":name:" + branchName
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if branch, ok := cached.(*entities.GitBranch); ok {
			return branch, nil
		}
	}
	result, err := r.BaseRepo.FindByName(ctx, projectID, branchName)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// CreateBranch creates a branch and invalidates the branch caches.
func (r *CachedGitBranchRepository) CreateBranch(ctx context.Context, projectID, branchName, description string) (any, error) {
	result, err := r.BaseRepo.CreateBranch(ctx, projectID, branchName, description)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidatePattern("project:" + projectID + ":*")
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// CreateGitBranch creates a branch and invalidates the branch caches.
func (r *CachedGitBranchRepository) CreateGitBranch(ctx context.Context, projectID, gitBranchName, gitBranchDescription string) (map[string]any, error) {
	result, err := r.BaseRepo.CreateGitBranch(ctx, projectID, gitBranchName, gitBranchDescription)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidatePattern("project:" + projectID + ":*")
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// UpdateBranch updates a branch and invalidates the branch caches.
func (r *CachedGitBranchRepository) UpdateBranch(ctx context.Context, branch *entities.GitBranch) (*entities.GitBranch, error) {
	result, err := r.BaseRepo.UpdateBranch(ctx, branch)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + cachedGitBranchID(branch))
		if branch != nil {
			r.invalidatePattern("project:" + branch.ProjectID + ":*")
		}
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// DeleteBranch deletes a branch and invalidates the branch caches.
func (r *CachedGitBranchRepository) DeleteBranch(ctx context.Context, branchID string) (bool, error) {
	branch, err := r.GetByID(ctx, branchID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.DeleteBranch(ctx, branchID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + branchID)
		if branch != nil {
			r.invalidatePattern("project:" + branch.ProjectID + ":*")
		}
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// ArchiveBranch archives a branch and invalidates the branch caches.
func (r *CachedGitBranchRepository) ArchiveBranch(ctx context.Context, branchID string) (bool, error) {
	branch, err := r.GetByID(ctx, branchID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.ArchiveBranch(ctx, branchID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + branchID)
		if branch != nil {
			r.invalidatePattern("project:" + branch.ProjectID + ":*")
		}
		r.invalidatePattern("list:*")
	}
	return result, nil
}

// RestoreBranch restores a branch and invalidates the branch caches.
func (r *CachedGitBranchRepository) RestoreBranch(ctx context.Context, branchID string) (bool, error) {
	branch, err := r.GetByID(ctx, branchID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.RestoreBranch(ctx, branchID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + branchID)
		if branch != nil {
			r.invalidatePattern("project:" + branch.ProjectID + ":*")
		}
		r.invalidatePattern("list:*")
	}
	return result, nil
}

func cachedGitBranchID(branch *entities.GitBranch) string {
	if branch == nil || branch.ID == nil {
		return ""
	}
	return branch.ID.String()
}
