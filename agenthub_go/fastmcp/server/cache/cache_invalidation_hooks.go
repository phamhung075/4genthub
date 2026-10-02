// Package cache ports fastmcp/server/cache/cache_invalidation_hooks.py.
package cache

import (
	"context"
	"log"
)

// CacheInvalidationHooks provides hooks for automatic cache invalidation on data changes.
type CacheInvalidationHooks struct {
	invalidator CacheInvalidator
}

// NewCacheInvalidationHooks creates a new CacheInvalidationHooks instance.
func NewCacheInvalidationHooks() *CacheInvalidationHooks {
	return &CacheInvalidationHooks{invalidator: CacheInvalidator{}}
}

// OnTaskCreated invalidates cache when a new task is created.
func (h *CacheInvalidationHooks) OnTaskCreated(ctx context.Context, taskID, gitBranchID string) {
	log.Printf("[CACHE] Invalidating cache for new task %s (branch %s)", taskID, gitBranchID)
	_ = h.invalidator.InvalidateTaskCache(ctx, taskID)
}

// OnTaskUpdated invalidates cache when a task is updated.
func (h *CacheInvalidationHooks) OnTaskUpdated(ctx context.Context, taskID string) {
	log.Printf("[CACHE] Invalidating cache for updated task %s", taskID)
	_ = h.invalidator.InvalidateTaskCache(ctx, taskID)
}

// OnTaskDeleted invalidates cache when a task is deleted.
func (h *CacheInvalidationHooks) OnTaskDeleted(ctx context.Context, taskID string) {
	log.Printf("[CACHE] Invalidating cache for deleted task %s", taskID)
	_ = h.invalidator.InvalidateTaskCache(ctx, taskID)
}

// OnSubtaskCreated invalidates cache when a subtask is created.
func (h *CacheInvalidationHooks) OnSubtaskCreated(ctx context.Context, subtaskID, parentTaskID string) {
	log.Printf("[CACHE] Invalidating cache for created subtask %s (parent %s)", subtaskID, parentTaskID)
	_ = h.invalidator.InvalidateSubtaskCache(ctx, parentTaskID)
}

// OnSubtaskUpdated invalidates cache when a subtask is updated.
func (h *CacheInvalidationHooks) OnSubtaskUpdated(ctx context.Context, subtaskID, parentTaskID string) {
	log.Printf("[CACHE] Invalidating cache for updated subtask %s (parent %s)", subtaskID, parentTaskID)
	_ = h.invalidator.InvalidateSubtaskCache(ctx, parentTaskID)
}

// OnSubtaskDeleted invalidates cache when a subtask is deleted.
func (h *CacheInvalidationHooks) OnSubtaskDeleted(ctx context.Context, subtaskID, parentTaskID string) {
	log.Printf("[CACHE] Invalidating cache for deleted subtask %s (parent %s)", subtaskID, parentTaskID)
	_ = h.invalidator.InvalidateSubtaskCache(ctx, parentTaskID)
}

// OnContextUpdated invalidates cache when a context is updated.
func (h *CacheInvalidationHooks) OnContextUpdated(ctx context.Context, contextID string) {
	log.Printf("[CACHE] Invalidating cache for updated context %s", contextID)
	_ = h.invalidator.InvalidateContextCache(ctx, contextID)
}
