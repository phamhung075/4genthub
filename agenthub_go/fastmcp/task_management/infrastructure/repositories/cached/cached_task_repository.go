package cached

// Cached Task Repository (Python cached/cached_task_repository.py). The redis-py client is
// injected as a CacheClient; a nil client disables caching. Python's async methods are plain
// synchronous Go methods. The simplified _serialize_task/_deserialize_task are reproduced.
//
// Python's `task` here has no project_id attribute (the hasattr guard skips it), so the
// project cache invalidation is a no-op; Go keeps the same guard.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// CachedTaskBaseRepository is the underlying task repository contract.
type CachedTaskBaseRepository interface {
	Create(ctx context.Context, task *entities.Task) (*entities.Task, error)
	Update(ctx context.Context, task *entities.Task) (*entities.Task, error)
	Delete(ctx context.Context, taskID tmvo.TaskId) (bool, error)
	FindByID(ctx context.Context, taskID tmvo.TaskId) (*entities.Task, error)
	FindAll(ctx context.Context) ([]*entities.Task, error)
}

// CachedTaskRepository wraps a task repository with namespaced caching.
type CachedTaskRepository struct {
	BaseRepo CachedTaskBaseRepository
	TTL      int
	Enabled  bool
	cache    cachedCache
}

// NewCachedTaskRepository builds the wrapper; cache nil disables caching.
func NewCachedTaskRepository(baseRepo CachedTaskBaseRepository, cache CacheClient, getenv func(string) string) (*CachedTaskRepository, error) {
	ttl, err := cachedTTLFromEnv(getenv)
	if err != nil {
		return nil, err
	}
	c := newCachedCache(cache, "task", ttl)
	return &CachedTaskRepository{BaseRepo: baseRepo, TTL: ttl, Enabled: c.enabled(), cache: c}, nil
}

func (r *CachedTaskRepository) invalidateKey(key string) {
	if r.Enabled {
		r.cache.invalidateKey(key)
	}
}

func (r *CachedTaskRepository) invalidatePattern(pattern string) {
	if r.Enabled {
		r.cache.invalidatePattern(pattern)
	}
}

func (r *CachedTaskRepository) getCached(key string) any { return r.cache.get(key) }

func (r *CachedTaskRepository) setCached(key string, value any) { r.cache.set(key, value) }

// Create creates a task and invalidates the task caches.
func (r *CachedTaskRepository) Create(ctx context.Context, task *entities.Task) (*entities.Task, error) {
	result, err := r.BaseRepo.Create(ctx, task)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidatePattern("list:*")
		if task != nil && task.GitBranchID != nil {
			r.invalidatePattern("branch:" + *task.GitBranchID + ":*")
		}
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// Update updates a task and invalidates the task caches.
func (r *CachedTaskRepository) Update(ctx context.Context, task *entities.Task) (*entities.Task, error) {
	result, err := r.BaseRepo.Update(ctx, task)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		if task != nil && task.ID != nil {
			r.invalidateKey(task.ID.Value)
		}
		r.invalidatePattern("list:*")
		if task != nil && task.GitBranchID != nil {
			r.invalidatePattern("branch:" + *task.GitBranchID + ":*")
		}
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// Delete deletes a task and invalidates every task cache.
func (r *CachedTaskRepository) Delete(ctx context.Context, taskID tmvo.TaskId) (bool, error) {
	// Python looks the task up first and ignores any error.
	_, _ = r.BaseRepo.FindByID(ctx, taskID)
	result, err := r.BaseRepo.Delete(ctx, taskID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey(taskID.Value)
		r.invalidatePattern("*")
	}
	return result, nil
}

// FindByID finds a task by ID with caching.
func (r *CachedTaskRepository) FindByID(ctx context.Context, taskID tmvo.TaskId) (*entities.Task, error) {
	cacheKey := taskID.Value
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if decoded, ok := cached.(*entities.OrderedMap[any]); ok {
			return r.deserializeTask(decoded), nil
		}
	}
	result, err := r.BaseRepo.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, r.serializeTask(result))
	}
	return result, nil
}

// FindAll finds all tasks with caching.
func (r *CachedTaskRepository) FindAll(ctx context.Context) ([]*entities.Task, error) {
	cacheKey := "list:all"
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if list, ok := cached.([]*entities.OrderedMap[any]); ok {
			out := make([]*entities.Task, 0, len(list))
			for _, item := range list {
				out = append(out, r.deserializeTask(item))
			}
			return out, nil
		}
	}
	result, err := r.BaseRepo.FindAll(ctx)
	if err != nil {
		return nil, err
	}
	serialized := make([]*entities.OrderedMap[any], 0, len(result))
	for _, task := range result {
		serialized = append(serialized, r.serializeTask(task))
	}
	r.setCached(cacheKey, serialized)
	return result, nil
}

// serializeTask is _serialize_task.
func (r *CachedTaskRepository) serializeTask(task *entities.Task) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	if task != nil && task.ID != nil {
		out.Set("id", task.ID.Value)
	} else {
		out.Set("id", nil)
	}
	if task != nil {
		out.Set("title", task.Title)
		out.Set("description", task.Description)
		if task.Status != nil {
			out.Set("status", task.Status.Value)
		} else {
			out.Set("status", nil)
		}
		if task.Priority != nil {
			out.Set("priority", task.Priority.Value)
		} else {
			out.Set("priority", nil)
		}
		if task.GitBranchID != nil {
			out.Set("git_branch_id", *task.GitBranchID)
		} else {
			out.Set("git_branch_id", nil)
		}
	} else {
		out.Set("title", nil)
		out.Set("description", nil)
		out.Set("status", nil)
		out.Set("priority", nil)
		out.Set("git_branch_id", nil)
	}
	// Python's Task has no project_id attribute, so this entry is always None.
	out.Set("project_id", nil)
	return out
}

// deserializeTask is _deserialize_task: set every attribute that exists on the entity.
func (r *CachedTaskRepository) deserializeTask(data *entities.OrderedMap[any]) *entities.Task {
	task := &entities.Task{}
	if data == nil {
		return task
	}
	if v, ok := data.Get("id"); ok {
		if s, ok := v.(string); ok {
			if id, err := tmvo.NewTaskId(s); err == nil {
				task.ID = &id
			}
		}
	}
	if v, ok := data.Get("title"); ok {
		if s, ok := v.(string); ok {
			task.Title = s
		}
	}
	if v, ok := data.Get("description"); ok {
		if s, ok := v.(string); ok {
			task.Description = s
		}
	}
	if v, ok := data.Get("status"); ok {
		if s, ok := v.(string); ok {
			if status, err := tmvo.TaskStatusFromString(s); err == nil {
				task.Status = &status
			}
		}
	}
	if v, ok := data.Get("priority"); ok {
		if s, ok := v.(string); ok {
			if priority, err := tmvo.PriorityFromString(s); err == nil {
				task.Priority = &priority
			}
		}
	}
	if v, ok := data.Get("git_branch_id"); ok {
		if s, ok := v.(string); ok {
			task.GitBranchID = &s
		}
	}
	return task
}
