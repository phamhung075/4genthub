package cache

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CacheOperation enumerates the cache operations (cache_invalidation_mixin.CacheOperation).
type CacheOperation string

const (
	CacheOperationCreate     CacheOperation = "create"
	CacheOperationUpdate     CacheOperation = "update"
	CacheOperationDelete     CacheOperation = "delete"
	CacheOperationBulkUpdate CacheOperation = "bulk_update"
	CacheOperationBulkDelete CacheOperation = "bulk_delete"
)

// CacheOperationValues lists all members in declaration order.
var CacheOperationValues = []CacheOperation{CacheOperationCreate, CacheOperationUpdate, CacheOperationDelete, CacheOperationBulkUpdate, CacheOperationBulkDelete}

func (o CacheOperation) String() string { return string(o) }

// CacheInvalidationMixin adds cache invalidation to repositories
// (cache_invalidation_mixin.CacheInvalidationMixin). UserID replaces the repository's
// user_id attribute that the Python mixin reads with getattr.
type CacheInvalidationMixin struct {
	CacheEnabled bool
	UserID       *string

	cache *ContextCache
}

// NewCacheInvalidationMixin mirrors CacheInvalidationMixin.__init__.
func NewCacheInvalidationMixin() *CacheInvalidationMixin {
	return &CacheInvalidationMixin{CacheEnabled: true}
}

// Cache lazily loads the context cache (the Python `cache` property). It returns nil
// when caching is disabled.
func (m *CacheInvalidationMixin) Cache() *ContextCache {
	if m.cache == nil && m.CacheEnabled {
		m.cache = GetContextCache()
	}
	return m.cache
}

func (m *CacheInvalidationMixin) resolveUser(userID *string) *string {
	user := userID
	if user == nil || *user == "" {
		user = m.UserID
	}
	if user == nil || *user == "" {
		return nil
	}
	return user
}

// InvalidateCacheForEntity mirrors CacheInvalidationMixin.invalidate_cache_for_entity.
func (m *CacheInvalidationMixin) InvalidateCacheForEntity(entityType, entityID string, operation CacheOperation, userID *string, level *string, propagate bool) {
	if m.Cache() == nil {
		return
	}
	user := m.resolveUser(userID)
	if user == nil {
		return
	}
	// cache errors never break the main operation (Python logs and swallows them)
	switch entityType {
	case "context":
		_ = m.invalidateContextCache(entityID, level, *user, operation, propagate)
	case "task":
		_ = m.invalidateTaskCache(entityID, *user, operation, propagate)
	case "project":
		_ = m.invalidateProjectCache(entityID, *user, operation, propagate)
	case "branch":
		_ = m.invalidateBranchCache(entityID, *user, operation, propagate)
	}
}

func (m *CacheInvalidationMixin) invalidateContextCache(contextID string, level *string, userID string, operation CacheOperation, propagate bool) error {
	if level == nil || *level == "" {
		return nil
	}
	if err := m.Cache().InvalidateContext(userID, level, &contextID); err != nil {
		return err
	}
	if err := m.Cache().InvalidateInheritance(userID, level, &contextID); err != nil {
		return err
	}
	if propagate && operation != CacheOperationDelete {
		return m.propagateContextInvalidation(*level, contextID, userID)
	}
	return nil
}

func (m *CacheInvalidationMixin) invalidateTaskCache(taskID, userID string, operation CacheOperation, propagate bool) error {
	task := "task"
	if err := m.Cache().InvalidateContext(userID, &task, &taskID); err != nil {
		return err
	}
	// A deleted task would also invalidate its branch context, but that needs task
	// metadata the mixin does not hold (Python's `pass`).
	_ = operation
	_ = propagate
	return nil
}

func (m *CacheInvalidationMixin) invalidateProjectCache(projectID, userID string, operation CacheOperation, propagate bool) error {
	project := "project"
	if err := m.Cache().InvalidateContext(userID, &project, &projectID); err != nil {
		return err
	}
	if propagate {
		if err := m.invalidateChildContexts("project", projectID, userID); err != nil {
			return err
		}
	}
	_ = operation
	return nil
}

func (m *CacheInvalidationMixin) invalidateBranchCache(branchID, userID string, operation CacheOperation, propagate bool) error {
	branch := "branch"
	if err := m.Cache().InvalidateContext(userID, &branch, &branchID); err != nil {
		return err
	}
	if propagate {
		if err := m.invalidateChildContexts("branch", branchID, userID); err != nil {
			return err
		}
	}
	_ = operation
	return nil
}

var contextPropagationRules = map[string][]string{
	"global":  {"project", "branch", "task"},
	"project": {"branch", "task"},
	"branch":  {"task"},
	"task":    {},
}

func (m *CacheInvalidationMixin) propagateContextInvalidation(level, contextID, userID string) error {
	for _, affected := range contextPropagationRules[level] {
		affectedLevel := affected
		if err := m.Cache().InvalidateContext(userID, &affectedLevel, nil); err != nil {
			return err
		}
		if err := m.Cache().InvalidateInheritance(userID, &affectedLevel, nil); err != nil {
			return err
		}
	}
	_ = contextID
	return nil
}

func (m *CacheInvalidationMixin) invalidateChildContexts(parentLevel, parentID, userID string) error {
	switch parentLevel {
	case "global":
		if err := m.Cache().InvalidateContext(userID, nil, nil); err != nil {
			return err
		}
		if err := m.Cache().InvalidateInheritance(userID, nil, nil); err != nil {
			return err
		}
	case "project":
		for _, level := range []string{"branch", "task"} {
			l := level
			if err := m.Cache().InvalidateContext(userID, &l, nil); err != nil {
				return err
			}
			if err := m.Cache().InvalidateInheritance(userID, &l, nil); err != nil {
				return err
			}
		}
	case "branch":
		task := "task"
		if err := m.Cache().InvalidateContext(userID, &task, nil); err != nil {
			return err
		}
		if err := m.Cache().InvalidateInheritance(userID, &task, nil); err != nil {
			return err
		}
	}
	_ = parentID
	return nil
}

// InvalidateBulk mirrors CacheInvalidationMixin.invalidate_bulk.
// The final propagation is not guarded in Python, so its error is returned.
func (m *CacheInvalidationMixin) InvalidateBulk(entityType string, entityIDs []string, operation CacheOperation, userID *string, level *string) error {
	for _, entityID := range entityIDs {
		m.InvalidateCacheForEntity(entityType, entityID, operation, userID, level, false)
	}
	if len(entityIDs) > 0 && level != nil && *level != "" {
		if user := m.resolveUser(userID); user != nil {
			if m.Cache() == nil {
				return &value_objects.TypeError{Msg: "'NoneType' object has no attribute 'invalidate_context'"}
			}
			return m.propagateContextInvalidation(*level, entityIDs[0], *user)
		}
	}
	return nil
}

// InvalidateAllUserCache mirrors CacheInvalidationMixin.invalidate_all_user_cache.
func (m *CacheInvalidationMixin) InvalidateAllUserCache(userID *string) {
	if m.Cache() == nil {
		return
	}
	user := m.resolveUser(userID)
	if user == nil {
		return
	}
	// errors are logged and swallowed (Python try/except)
	if err := m.Cache().InvalidateContext(*user, nil, nil); err != nil {
		return
	}
	_ = m.Cache().InvalidateInheritance(*user, nil, nil)
}

// WarmCache mirrors CacheInvalidationMixin.warm_cache.
func (m *CacheInvalidationMixin) WarmCache(entityType, entityID string, data *entities.OrderedMap[any], userID *string, level *string, ttl *int) {
	if m.Cache() == nil {
		return
	}
	user := m.resolveUser(userID)
	if user == nil {
		return
	}
	if entityType == "context" && level != nil && *level != "" {
		_ = m.Cache().SetContext(*level, entityID, *user, data, ttl)
	}
}
