package cached

// Cached Subtask Repository (Python cached/cached_subtask_repository.py). The redis-py client
// is injected as a CacheClient; a nil client disables caching.
//
// Python reads `subtask.task_id`, but the Subtask entity's field is parent_task_id, so that
// direct access would raise AttributeError; Go uses ParentTaskID.Value instead.

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// CachedSubtaskBaseRepository is the underlying subtask repository contract.
type CachedSubtaskBaseRepository interface {
	GetByID(ctx context.Context, subtaskID string) (*entities.Subtask, error)
	GetByTaskID(ctx context.Context, taskID string) ([]*entities.Subtask, error)
	FindByParentTaskID(ctx context.Context, parentTaskID tmvo.TaskId) ([]*entities.Subtask, error)
	Create(ctx context.Context, subtask *entities.Subtask) (*entities.Subtask, error)
	Update(ctx context.Context, subtask *entities.Subtask) (*entities.Subtask, error)
	Delete(ctx context.Context, subtaskID string) (bool, error)
	DeleteByParentTaskID(ctx context.Context, taskID string) (int, error)
	RemoveSubtask(ctx context.Context, subtaskID string) (bool, error)
	UpdateProgress(ctx context.Context, subtaskID string, progressPercentage int, progressNotes *string) (*entities.Subtask, error)
}

// CachedSubtaskRepository wraps a subtask repository with namespaced caching.
type CachedSubtaskRepository struct {
	BaseRepo CachedSubtaskBaseRepository
	TTL      int
	Enabled  bool
	cache    cachedCache
}

// NewCachedSubtaskRepository builds the wrapper; cache nil disables caching.
func NewCachedSubtaskRepository(baseRepo CachedSubtaskBaseRepository, cache CacheClient, getenv func(string) string) (*CachedSubtaskRepository, error) {
	ttl, err := cachedTTLFromEnv(getenv)
	if err != nil {
		return nil, err
	}
	c := newCachedCache(cache, "subtask", ttl)
	return &CachedSubtaskRepository{BaseRepo: baseRepo, TTL: ttl, Enabled: c.enabled(), cache: c}, nil
}

// UserID proxies the base repository user id for authentication checks.
func (r *CachedSubtaskRepository) UserID() *string {
	if holder, ok := r.BaseRepo.(cachedUserIDHolder); ok {
		return holder.GetUserID()
	}
	return nil
}

func (r *CachedSubtaskRepository) invalidateKey(key string) {
	if r.Enabled {
		r.cache.invalidateKey(key)
	}
}

func (r *CachedSubtaskRepository) invalidatePattern(pattern string) {
	if r.Enabled {
		r.cache.invalidatePattern(pattern)
	}
}

func (r *CachedSubtaskRepository) getCached(key string) any { return r.cache.get(key) }

func (r *CachedSubtaskRepository) setCached(key string, value any) { r.cache.set(key, value) }

// GetByID returns a subtask by ID with caching.
func (r *CachedSubtaskRepository) GetByID(ctx context.Context, subtaskID string) (*entities.Subtask, error) {
	cacheKey := "id:" + subtaskID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if subtask, ok := cached.(*entities.Subtask); ok {
			return subtask, nil
		}
	}
	result, err := r.BaseRepo.GetByID(ctx, subtaskID)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// GetByTaskID returns all subtasks for a task with caching.
func (r *CachedSubtaskRepository) GetByTaskID(ctx context.Context, taskID string) ([]*entities.Subtask, error) {
	cacheKey := "task:" + taskID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if list, ok := cached.([]*entities.Subtask); ok {
			return list, nil
		}
	}
	result, err := r.BaseRepo.GetByTaskID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if len(result) > 0 {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// FindByParentTaskID returns all subtasks for a parent task with caching.
func (r *CachedSubtaskRepository) FindByParentTaskID(ctx context.Context, parentTaskID tmvo.TaskId) ([]*entities.Subtask, error) {
	taskIDStr := parentTaskID.Value
	cacheKey := "parent_task:" + taskIDStr
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if list, ok := cached.([]*entities.Subtask); ok {
			return list, nil
		}
	}
	result, err := r.BaseRepo.FindByParentTaskID(ctx, parentTaskID)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// Create creates a subtask and invalidates the subtask caches.
func (r *CachedSubtaskRepository) Create(ctx context.Context, subtask *entities.Subtask) (*entities.Subtask, error) {
	result, err := r.BaseRepo.Create(ctx, subtask)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		taskID := cachedSubtaskTaskID(subtask)
		r.invalidatePattern("task:" + taskID + ":*")
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
		r.invalidatePattern("task:id:" + taskID)
	}
	return result, nil
}

// Update updates a subtask and invalidates the subtask caches.
func (r *CachedSubtaskRepository) Update(ctx context.Context, subtask *entities.Subtask) (*entities.Subtask, error) {
	result, err := r.BaseRepo.Update(ctx, subtask)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		taskID := cachedSubtaskTaskID(subtask)
		r.invalidateKey("id:" + cachedSubtaskID(subtask))
		r.invalidatePattern("task:" + taskID + ":*")
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
		r.invalidatePattern("task:id:" + taskID)
	}
	return result, nil
}

// Delete deletes a subtask and invalidates the subtask caches.
func (r *CachedSubtaskRepository) Delete(ctx context.Context, subtaskID string) (bool, error) {
	subtask, err := r.GetByID(ctx, subtaskID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.Delete(ctx, subtaskID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + subtaskID)
		if subtask != nil {
			taskID := cachedSubtaskTaskID(subtask)
			r.invalidatePattern("task:" + taskID + ":*")
			r.invalidatePattern("task:id:" + taskID)
		}
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// DeleteByParentTaskID deletes all subtasks for a task and invalidates the subtask caches.
func (r *CachedSubtaskRepository) DeleteByParentTaskID(ctx context.Context, taskID string) (int, error) {
	result, err := r.BaseRepo.DeleteByParentTaskID(ctx, taskID)
	if err != nil {
		return 0, err
	}
	if r.Enabled {
		r.invalidatePattern("task:" + taskID + ":*")
		r.invalidatePattern("subtask:*")
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
		r.invalidatePattern("task:id:" + taskID)
	}
	return result, nil
}

// RemoveSubtask removes a subtask and invalidates the subtask caches.
func (r *CachedSubtaskRepository) RemoveSubtask(ctx context.Context, subtaskID string) (bool, error) {
	subtask, err := r.GetByID(ctx, subtaskID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.RemoveSubtask(ctx, subtaskID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + subtaskID)
		if subtask != nil {
			taskID := cachedSubtaskTaskID(subtask)
			r.invalidatePattern("task:" + taskID + ":*")
			r.invalidatePattern("task:id:" + taskID)
		}
		r.invalidatePattern("list:*")
	}
	return result, nil
}

// UpdateProgress updates a subtask's progress and invalidates the subtask caches.
func (r *CachedSubtaskRepository) UpdateProgress(ctx context.Context, subtaskID string, progressPercentage int, progressNotes *string) (*entities.Subtask, error) {
	subtask, err := r.GetByID(ctx, subtaskID)
	if err != nil {
		return nil, err
	}
	result, err := r.BaseRepo.UpdateProgress(ctx, subtaskID, progressPercentage, progressNotes)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + subtaskID)
		if subtask != nil {
			taskID := cachedSubtaskTaskID(subtask)
			r.invalidatePattern("task:" + taskID + ":*")
			r.invalidatePattern("task:id:" + taskID)
		}
	}
	return result, nil
}

func cachedSubtaskID(subtask *entities.Subtask) string {
	if subtask == nil || subtask.ID == nil {
		return ""
	}
	return subtask.ID.Value
}

func cachedSubtaskTaskID(subtask *entities.Subtask) string {
	if subtask == nil || subtask.ParentTaskID == nil {
		return ""
	}
	return subtask.ParentTaskID.Value
}
