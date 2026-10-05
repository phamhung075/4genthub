package services

import (
	"context"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services/protocols"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// EntityType is re-exported from protocols (see the note there).
type EntityType = protocols.EntityType

const (
	EntityTypeTask    = protocols.EntityTypeTask
	EntityTypeSubtask = protocols.EntityTypeSubtask
	EntityTypeBranch  = protocols.EntityTypeBranch
	EntityTypeProject = protocols.EntityTypeProject
	EntityTypeContext = protocols.EntityTypeContext
)

// CascadeResult holds every entity affected by a change.
type CascadeResult struct {
	EntityID          string
	EntityType        EntityType
	AffectedTasks     entities.StringSet
	AffectedSubtasks  entities.StringSet
	AffectedBranches  entities.StringSet
	AffectedProjects  entities.StringSet
	AffectedContexts  entities.StringSet
	CalculationTimeMs float64
	CacheHit          bool
}

// GetAllAffectedIDs is the union of all affected sets (order: tasks, subtasks,
// branches, projects, contexts; Python's set order is arbitrary).
func (r *CascadeResult) GetAllAffectedIDs() entities.StringSet {
	var out entities.StringSet
	for _, s := range []*entities.StringSet{&r.AffectedTasks, &r.AffectedSubtasks, &r.AffectedBranches, &r.AffectedProjects, &r.AffectedContexts} {
		for _, id := range s.Items() {
			out.Add(id)
		}
	}
	return out
}

// GetAffectedCount is the number of distinct affected IDs.
func (r *CascadeResult) GetAffectedCount() int {
	s := r.GetAllAffectedIDs()
	return s.Len()
}

// CascadeCalculator computes the entities affected by a change, with a 5-minute cache.
type CascadeCalculator struct {
	dataProvider protocols.CascadeDataProvider

	mu              sync.Mutex
	cache           *entities.OrderedMap[*CascadeResult]
	cacheTimestamps map[string]float64
	cacheTTLSeconds int
}

// NewCascadeCalculator builds a calculator around a data provider.
func NewCascadeCalculator(p protocols.CascadeDataProvider) *CascadeCalculator {
	return &CascadeCalculator{dataProvider: p, cache: entities.NewOrderedMap[*CascadeResult](),
		cacheTimestamps: map[string]float64{}, cacheTTLSeconds: 300}
}

func unixNow() float64 { return float64(time.Now().UnixMicro()) / 1e6 }

func addAll(s *entities.StringSet, ids []string) {
	for _, id := range ids {
		s.Add(id)
	}
}

// CalculateCascade determines the entity type (auto-detected when nil) and delegates.
func (c *CascadeCalculator) CalculateCascade(ctx context.Context, entityID string, entityType *EntityType, useCache bool) (*CascadeResult, error) {
	start := unixNow()
	kind := "auto"
	if entityType != nil {
		kind = string(*entityType)
	}
	cacheKey := entityID + ":" + kind
	if useCache {
		c.mu.Lock()
		if c.isCacheValid(cacheKey) {
			r, _ := c.cache.Get(cacheKey)
			r.CacheHit = true
			c.mu.Unlock()
			return r, nil
		}
		c.mu.Unlock()
	}
	if entityType == nil {
		t, err := c.dataProvider.DetectEntityType(ctx, entityID)
		if err != nil {
			return nil, err
		}
		if t == nil {
			return nil, value_objects.ValueErrorf("Could not detect entity type for ID: %s", entityID)
		}
		entityType = t
	}
	var result *CascadeResult
	var err error
	switch *entityType {
	case EntityTypeTask:
		result, err = c.CalculateTaskCascade(ctx, entityID)
	case EntityTypeSubtask:
		result, err = c.CalculateSubtaskCascade(ctx, entityID)
	case EntityTypeBranch:
		result, err = c.CalculateBranchCascade(ctx, entityID)
	case EntityTypeProject:
		result, err = c.CalculateProjectCascade(ctx, entityID)
	default:
		result, err = c.CalculateContextCascade(ctx, entityID)
	}
	if err != nil {
		return nil, err
	}
	result.CalculationTimeMs = (unixNow() - start) * 1000
	if useCache {
		c.mu.Lock()
		c.cache.Set(cacheKey, result)
		c.cacheTimestamps[cacheKey] = unixNow()
		c.mu.Unlock()
	}
	return result, nil
}

func newResult(id string, t EntityType) *CascadeResult {
	return &CascadeResult{EntityID: id, EntityType: t}
}

// CalculateTaskCascade: the task, its parents and subtasks, branch, project and contexts.
func (c *CascadeCalculator) CalculateTaskCascade(ctx context.Context, taskID string) (*CascadeResult, error) {
	r := newResult(taskID, EntityTypeTask)
	r.AffectedTasks.Add(taskID)
	d, err := c.dataProvider.GetTaskCascadeData(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if d == nil {
		return r, nil
	}
	r.AffectedBranches.Add(d.GitBranchID)
	r.AffectedProjects.Add(d.ProjectID)
	if d.ContextID != nil && *d.ContextID != "" {
		r.AffectedContexts.Add(*d.ContextID)
	}
	sub, err := c.dataProvider.GetTaskSubtaskIDs(ctx, taskID)
	if err != nil {
		return nil, err
	}
	addAll(&r.AffectedSubtasks, sub)
	parents, err := c.dataProvider.GetTaskParentTaskIDs(ctx, taskID)
	if err != nil {
		return nil, err
	}
	addAll(&r.AffectedTasks, parents)
	rel, err := c.dataProvider.GetRelatedContextIDs(ctx, d.GitBranchID, d.ProjectID)
	if err != nil {
		return nil, err
	}
	addAll(&r.AffectedContexts, rel)
	return r, nil
}

// CalculateSubtaskCascade: the subtask, its parent task, branch, project and contexts.
func (c *CascadeCalculator) CalculateSubtaskCascade(ctx context.Context, subtaskID string) (*CascadeResult, error) {
	r := newResult(subtaskID, EntityTypeSubtask)
	r.AffectedSubtasks.Add(subtaskID)
	d, err := c.dataProvider.GetSubtaskCascadeData(ctx, subtaskID)
	if err != nil {
		return nil, err
	}
	if d == nil {
		return r, nil
	}
	r.AffectedTasks.Add(d.TaskID)
	r.AffectedBranches.Add(d.GitBranchID)
	r.AffectedProjects.Add(d.ProjectID)
	if d.ContextID != nil && *d.ContextID != "" {
		r.AffectedContexts.Add(*d.ContextID)
	}
	rel, err := c.dataProvider.GetRelatedContextIDs(ctx, d.GitBranchID, d.ProjectID)
	if err != nil {
		return nil, err
	}
	addAll(&r.AffectedContexts, rel)
	return r, nil
}

// CalculateBranchCascade: the branch, its project, tasks, subtasks and contexts.
func (c *CascadeCalculator) CalculateBranchCascade(ctx context.Context, branchID string) (*CascadeResult, error) {
	r := newResult(branchID, EntityTypeBranch)
	r.AffectedBranches.Add(branchID)
	d, err := c.dataProvider.GetBranchCascadeData(ctx, branchID)
	if err != nil {
		return nil, err
	}
	if d == nil {
		return r, nil
	}
	r.AffectedProjects.Add(d.ProjectID)
	addAll(&r.AffectedTasks, d.TaskIDs.Items())
	addAll(&r.AffectedSubtasks, d.SubtaskIDs.Items())
	rel, err := c.dataProvider.GetRelatedContextIDs(ctx, branchID, d.ProjectID)
	if err != nil {
		return nil, err
	}
	addAll(&r.AffectedContexts, rel)
	return r, nil
}

// CalculateProjectCascade: the project, its branches, tasks, subtasks and contexts.
func (c *CascadeCalculator) CalculateProjectCascade(ctx context.Context, projectID string) (*CascadeResult, error) {
	r := newResult(projectID, EntityTypeProject)
	r.AffectedProjects.Add(projectID)
	d, err := c.dataProvider.GetProjectCascadeData(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if d == nil {
		return r, nil
	}
	addAll(&r.AffectedBranches, d.BranchIDs.Items())
	addAll(&r.AffectedTasks, d.TaskIDs.Items())
	addAll(&r.AffectedSubtasks, d.SubtaskIDs.Items())
	for _, b := range r.AffectedBranches.Items() {
		rel, err := c.dataProvider.GetRelatedContextIDs(ctx, b, projectID)
		if err != nil {
			return nil, err
		}
		addAll(&r.AffectedContexts, rel)
	}
	return r, nil
}

// CalculateContextCascade: the context and everything that references it.
func (c *CascadeCalculator) CalculateContextCascade(ctx context.Context, contextID string) (*CascadeResult, error) {
	r := newResult(contextID, EntityTypeContext)
	r.AffectedContexts.Add(contextID)
	d, err := c.dataProvider.GetContextCascadeData(ctx, contextID)
	if err != nil {
		return nil, err
	}
	if d == nil {
		return r, nil
	}
	addAll(&r.AffectedTasks, d.TaskIDs.Items())
	addAll(&r.AffectedBranches, d.BranchIDs.Items())
	addAll(&r.AffectedProjects, d.ProjectIDs.Items())
	addAll(&r.AffectedSubtasks, d.SubtaskIDs.Items())
	return r, nil
}

// isCacheValid requires c.mu held.
func (c *CascadeCalculator) isCacheValid(key string) bool {
	if !c.cache.Has(key) {
		return false
	}
	return unixNow()-c.cacheTimestamps[key] < float64(c.cacheTTLSeconds)
}

// ClearCache drops all cached results.
func (c *CascadeCalculator) ClearCache() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.cache = entities.NewOrderedMap[*CascadeResult]()
	c.cacheTimestamps = map[string]float64{}
}

// GetCacheStats returns cache_size, cache_entries and cache_ttl_seconds.
func (c *CascadeCalculator) GetCacheStats() map[string]any {
	c.mu.Lock()
	defer c.mu.Unlock()
	return map[string]any{"cache_size": c.cache.Len(), "cache_entries": c.cache.Keys(), "cache_ttl_seconds": c.cacheTTLSeconds}
}
