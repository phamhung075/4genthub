package cached

// Cached Agent Repository (Python cached/cached_agent_repository.py). The redis-py client is
// injected as a CacheClient; a nil client disables caching. The Python `__getattr__`
// delegation is not reproducible in Go: callers use BaseRepo for methods without a wrapper.
//
// Python reads `agent.project_id` when invalidating after register/update/unregister, but
// the Agent entity has no such attribute, so a cache hit path would raise AttributeError.
// Here the project id is derived from AssignedProjects (the repository's own extraction).

import (
	"context"
	"sort"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// CachedAgentBaseRepository is the underlying agent repository contract the wrapper uses.
type CachedAgentBaseRepository interface {
	GetByID(ctx context.Context, agentID string) (*entities.Agent, error)
	GetByProjectID(ctx context.Context, projectID string) ([]*entities.Agent, error)
	RegisterAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error)
	UpdateAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error)
	UnregisterAgent(ctx context.Context, agentID string) (bool, error)
	AssignAgent(ctx context.Context, agentID, gitBranchID string) (bool, error)
	UnassignAgent(ctx context.Context, agentID, gitBranchID string) (bool, error)
	RebalanceAgents(ctx context.Context, projectID string) (map[string]any, error)
}

// CachedAgentRepository wraps an agent repository with namespaced caching and invalidation.
type CachedAgentRepository struct {
	BaseRepo CachedAgentBaseRepository
	TTL      int
	Enabled  bool
	cache    cachedCache
}

// NewCachedAgentRepository builds the wrapper; cache nil disables caching.
func NewCachedAgentRepository(baseRepo CachedAgentBaseRepository, cache CacheClient, getenv func(string) string) (*CachedAgentRepository, error) {
	ttl, err := cachedTTLFromEnv(getenv)
	if err != nil {
		return nil, err
	}
	c := newCachedCache(cache, "agent", ttl)
	return &CachedAgentRepository{BaseRepo: baseRepo, TTL: ttl, Enabled: c.enabled(), cache: c}, nil
}

func (r *CachedAgentRepository) invalidateKey(key string) {
	if r.Enabled {
		r.cache.invalidateKey(key)
	}
}

func (r *CachedAgentRepository) invalidatePattern(pattern string) {
	if r.Enabled {
		r.cache.invalidatePattern(pattern)
	}
}

func (r *CachedAgentRepository) getCached(key string) any { return r.cache.get(key) }

func (r *CachedAgentRepository) setCached(key string, value any) { r.cache.set(key, value) }

// GetByID returns an agent by ID with caching.
func (r *CachedAgentRepository) GetByID(ctx context.Context, agentID string) (*entities.Agent, error) {
	cacheKey := "id:" + agentID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if agent, ok := cached.(*entities.Agent); ok {
			return agent, nil
		}
	}
	result, err := r.BaseRepo.GetByID(ctx, agentID)
	if err != nil {
		return nil, err
	}
	if result != nil {
		r.setCached(cacheKey, result)
	}
	return result, nil
}

// GetByProjectID returns all agents for a project with caching.
func (r *CachedAgentRepository) GetByProjectID(ctx context.Context, projectID string) ([]*entities.Agent, error) {
	cacheKey := "project:" + projectID
	if cached := r.getCached(cacheKey); tmvo.PyTruthy(cached) {
		if list, ok := cached.([]*entities.Agent); ok {
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

// RegisterAgent registers an agent and invalidates the agent caches.
func (r *CachedAgentRepository) RegisterAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error) {
	result, err := r.BaseRepo.RegisterAgent(ctx, agent)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		if projectID := cachedAgentProjectID(agent); projectID != "" {
			r.invalidatePattern("project:" + projectID + ":*")
		}
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// UpdateAgent updates an agent and invalidates the agent caches.
func (r *CachedAgentRepository) UpdateAgent(ctx context.Context, agent *entities.Agent) (*entities.Agent, error) {
	result, err := r.BaseRepo.UpdateAgent(ctx, agent)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + cachedAgentID(agent))
		if projectID := cachedAgentProjectID(agent); projectID != "" {
			r.invalidatePattern("project:" + projectID + ":*")
		}
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// UnregisterAgent removes an agent and invalidates the agent caches.
func (r *CachedAgentRepository) UnregisterAgent(ctx context.Context, agentID string) (bool, error) {
	agent, err := r.GetByID(ctx, agentID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.UnregisterAgent(ctx, agentID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + agentID)
		if agent != nil {
			if projectID := cachedAgentProjectID(agent); projectID != "" {
				r.invalidatePattern("project:" + projectID + ":*")
			}
		}
		r.invalidatePattern("list:*")
		r.invalidatePattern("search:*")
	}
	return result, nil
}

// AssignAgent assigns an agent to a branch and invalidates the agent caches.
func (r *CachedAgentRepository) AssignAgent(ctx context.Context, agentID, gitBranchID string) (bool, error) {
	agent, err := r.GetByID(ctx, agentID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.AssignAgent(ctx, agentID, gitBranchID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + agentID)
		if agent != nil {
			if projectID := cachedAgentProjectID(agent); projectID != "" {
				r.invalidatePattern("project:" + projectID + ":*")
			}
		}
		r.invalidatePattern("branch:" + gitBranchID + ":*")
		r.invalidatePattern("assignments:*")
	}
	return result, nil
}

// UnassignAgent unassigns an agent from a branch and invalidates the agent caches.
func (r *CachedAgentRepository) UnassignAgent(ctx context.Context, agentID, gitBranchID string) (bool, error) {
	agent, err := r.GetByID(ctx, agentID)
	if err != nil {
		return false, err
	}
	result, err := r.BaseRepo.UnassignAgent(ctx, agentID, gitBranchID)
	if err != nil {
		return false, err
	}
	if r.Enabled {
		r.invalidateKey("id:" + agentID)
		if agent != nil {
			if projectID := cachedAgentProjectID(agent); projectID != "" {
				r.invalidatePattern("project:" + projectID + ":*")
			}
		}
		r.invalidatePattern("branch:" + gitBranchID + ":*")
		r.invalidatePattern("assignments:*")
	}
	return result, nil
}

// RebalanceAgents rebalances a project's agents and invalidates the agent caches.
func (r *CachedAgentRepository) RebalanceAgents(ctx context.Context, projectID string) (map[string]any, error) {
	result, err := r.BaseRepo.RebalanceAgents(ctx, projectID)
	if err != nil {
		return nil, err
	}
	if r.Enabled {
		r.invalidatePattern("project:" + projectID + ":*")
		r.invalidatePattern("agent:*")
		r.invalidatePattern("assignments:*")
	}
	return result, nil
}

func cachedAgentID(agent *entities.Agent) string {
	if agent == nil || agent.ID == nil {
		return ""
	}
	return agent.ID.String()
}

func cachedAgentProjectID(agent *entities.Agent) string {
	if agent == nil || len(agent.AssignedProjects) == 0 {
		return ""
	}
	keys := make([]string, 0, len(agent.AssignedProjects))
	for k := range agent.AssignedProjects {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys[0]
}
