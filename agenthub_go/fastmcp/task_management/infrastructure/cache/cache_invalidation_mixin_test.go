package cache

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestCacheOperationValues(t *testing.T) {
	want := []string{"create", "update", "delete", "bulk_update", "bulk_delete"}
	if len(CacheOperationValues) != len(want) {
		t.Fatalf("len(CacheOperationValues) = %d", len(CacheOperationValues))
	}
	for i, op := range CacheOperationValues {
		if string(op) != want[i] {
			t.Fatalf("CacheOperationValues[%d] = %q, want %q", i, op, want[i])
		}
	}
}

func TestCacheInvalidationMixin(t *testing.T) {
	ResetContextCache()
	m := NewCacheInvalidationMixin()
	user := "u1"
	m.UserID = &user
	data := entities.NewOrderedMap[any]()
	data.Set("k", "v")

	project := "project"
	_ = m.Cache().SetContext("project", "p1", user, data, nil)
	_ = m.Cache().SetInheritanceChain("project", "p1", user, data)
	m.InvalidateCacheForEntity("context", "p1", CacheOperationUpdate, nil, &project, false)
	if got, _ := m.Cache().GetContext("project", "p1", user); got != nil {
		t.Fatal("context not invalidated")
	}
	if got, _ := m.Cache().GetInheritanceChain("project", "p1", user); got != nil {
		t.Fatal("inheritance not invalidated")
	}

	// Propagation from project touches branch and task levels for the user.
	_ = m.Cache().SetContext("branch", "b1", user, data, nil)
	_ = m.Cache().SetContext("project", "p2", user, data, nil)
	m.InvalidateCacheForEntity("context", "p2", CacheOperationUpdate, nil, &project, true)
	if got, _ := m.Cache().GetContext("branch", "b1", user); got != nil {
		t.Fatal("propagation did not invalidate branch level")
	}

	// WarmCache only handles context entities with a level.
	task := "task"
	m.WarmCache("context", "t1", data, nil, &task, nil)
	if got, _ := m.Cache().GetContext("task", "t1", user); got == nil {
		t.Fatal("WarmCache did not store the context")
	}
	m.WarmCache("task", "t9", data, nil, nil, nil)
	if got, _ := m.Cache().GetContext("task", "t9", user); got != nil {
		t.Fatal("WarmCache cached a non-context entity")
	}

	// User-scoped invalidation must not touch another user.
	other := "u2"
	_ = m.Cache().SetContext("task", "t2", other, data, nil)
	m.InvalidateAllUserCache(&user)
	if got, _ := m.Cache().GetContext("task", "t1", user); got != nil {
		t.Fatal("InvalidateAllUserCache left a user entry")
	}
	if got, _ := m.Cache().GetContext("task", "t2", other); got == nil {
		t.Fatal("InvalidateAllUserCache crossed users")
	}

	// Bulk invalidation.
	_ = m.Cache().SetContext("branch", "bb1", user, data, nil)
	_ = m.Cache().SetContext("branch", "bb2", user, data, nil)
	branch := "branch"
	m.InvalidateBulk("context", []string{"bb1", "bb2"}, CacheOperationUpdate, nil, &branch)
	if got, _ := m.Cache().GetContext("branch", "bb1", user); got != nil {
		t.Fatal("InvalidateBulk left bb1")
	}
	if got, _ := m.Cache().GetContext("branch", "bb2", user); got != nil {
		t.Fatal("InvalidateBulk left bb2")
	}
}

func TestCacheInvalidationMixinNoUser(t *testing.T) {
	ResetContextCache()
	m := NewCacheInvalidationMixin()
	level := "project"
	// No user id anywhere: the call returns without touching the cache.
	m.InvalidateCacheForEntity("context", "p1", CacheOperationDelete, nil, &level, true)
	if m.Cache() == nil {
		t.Fatal("Cache() unexpectedly nil with caching enabled")
	}

	disabled := NewCacheInvalidationMixin()
	disabled.CacheEnabled = false
	if disabled.Cache() != nil {
		t.Fatal("Cache() should be nil when disabled before first use")
	}
}
