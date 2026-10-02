package cached

// Cached Project Repository (Python cached/cached_project_repository.py). The redis-py client
// is injected as a CacheClient; a nil client disables caching.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// CachedProjectBaseRepository is the underlying project repository contract.
type CachedProjectBaseRepository interface {
	GetByID(ctx context.Context, projectID string) (*entities.Project, error)
	GetAll(ctx context.Context) ([]*entities.Project, error)
	CreateProject(ctx context.Context, project *entities.Project) (*entities.Project, error)
	UpdateProject(ctx context.Context, project *entities.Project) (*entities.Project, error)
	DeleteProject(ctx context.Context, projectID string) (bool, error)
}

// CachedProjectRepository wraps a project repository with namespaced caching.
type CachedProjectRepository struct {
	BaseRepo CachedProjectBaseRepository
	TTL      int
	Enabled  bool
	cache    cachedCache
}

// NewCachedProjectRepository builds the wrapper; cache nil disables caching.
func NewCachedProjectRepository(baseRepo CachedProjectBaseRepository, cache CacheClient, getenv func(string) string) (*CachedProjectRepository, error) {
	ttl, err := cachedTTLFromEnv(getenv)
	if err != nil {
		return nil, err
	}
	c := newCachedCache(cache, "project", ttl)
	return &CachedProjectRepository{BaseRepo: baseRepo, TTL: ttl, Enabled: c.enabled(), cache: c}, nil
}

func (r *CachedProjectRepository) invalidateKey(key string) {
	if r.Enabled {
		r.cache.invalidateKey(key)
	}
}

func (r *CachedProjectRepository) invalidatePattern(pattern string) {
	if r.Enabled {
		r.cache.invalidatePattern(pattern)
	}
}

func (r *CachedProjectRepository) getCached(key string) any { return r.cache.get(key) }

func (r *CachedProjectRepository) setCached(key string, value any) { r.cache.set(key, value) }

// GetByID returns a project by ID with caching.
func (r *CachedProjectRepository) GetByID(ctx context.Context, projectID string) (*entities.Project, error) {
	cacheKey := "id:" + projectID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if project, ok := cached.(*entities.Project); ok {
			return project, nil
		}
	}
	result, err := r.BaseRepo.GetByID(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// GetAll returns all projects with caching.
func (r *CachedProjectRepository) GetAll(ctx context.Context) ([]*entities.Project, error) {
	cacheKey := "list:all"
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if list, ok := cached.([]*entities.Project); ok {
			return list, nil
		}
	}
	result, err := r.BaseRepo.GetAll(ctx)
	if err != nil {
		return nil, err
	}
	if len(result) > 0 {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// CreateProject creates a project and invalidates the project caches.
func (r *CachedProjectRepository) CreateProject(ctx context.Context, project *entities.Project) (*entities.Project, error) {
	result, err := r.BaseRepo.CreateProject(ctx, project)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// UpdateProject updates a project and invalidates the project caches.
func (r *CachedProjectRepository) UpdateProject(ctx context.Context, project *entities.Project) (*entities.Project, error) {
	result, err := r.BaseRepo.UpdateProject(ctx, project)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + cachedProjectID(project))
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// DeleteProject deletes a project and invalidates the project caches.
func (r *CachedProjectRepository) DeleteProject(ctx context.Context, projectID string) (bool, error) {
	result, err := r.BaseRepo.DeleteProject(ctx, projectID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + projectID)
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
		r.invalidatePattern("project:" + projectID + ":*")
	}
	return result, nil
}

func cachedProjectID(project *entities.Project) string {
	if project == nil || project.ID == nil {
		return ""
	}
	return project.ID.Value
}
