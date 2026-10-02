// Agent Facade Factory (Python
// task_management/application/factories/agent_facade_factory.py).
//
// The Python factory requires user authentication (no default_id fallback) and falls back
// to a mock AgentApplicationFacade when the real facade cannot be created. The Go
// AgentApplicationFacade has no port yet, so its construction goes through
// AgentApplicationFacadeConstructor; when that hook is unset the factory behaves like the
// Python except branch and caches the mock.
package factories

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"sync"
)

// AgentApplicationFacade is the consumer-side marker for the unported
// AgentApplicationFacade; no method is called by the factory.
type AgentApplicationFacade interface{}

// AgentRepositoryFactoryBackend is the static AgentRepositoryFactory.create(user_id) used
// by the factory. The infrastructure factory has no matching static method yet.
type AgentRepositoryFactoryBackend func(userID string) (repositories.AgentRepository, error)

// AgentRepositoryFactoryDefault is the fallback backend when none was injected.
var AgentRepositoryFactoryDefault AgentRepositoryFactoryBackend

// AgentApplicationFacadeConstructor builds the unported AgentApplicationFacade.
var AgentApplicationFacadeConstructor func(repo repositories.AgentRepository) AgentApplicationFacade

// AgentFacadeFactory mirrors agent_facade_factory.AgentFacadeFactory.
type AgentFacadeFactory struct {
	agentRepositoryFactory AgentRepositoryFactoryBackend
	cacheMu                sync.Mutex
	facadesCache           map[string]AgentApplicationFacade
}

// NewAgentFacadeFactory mirrors __init__.
func NewAgentFacadeFactory(agentRepositoryFactory AgentRepositoryFactoryBackend) *AgentFacadeFactory {
	return &AgentFacadeFactory{
		agentRepositoryFactory: agentRepositoryFactory,
		facadesCache:           map[string]AgentApplicationFacade{},
	}
}

// CreateAgentFacade mirrors create_agent_facade.
func (f *AgentFacadeFactory) CreateAgentFacade(projectID string, userID *string) (AgentApplicationFacade, error) {
	cacheKey := projectID
	f.cacheMu.Lock()
	cached, ok := f.facadesCache[cacheKey]
	f.cacheMu.Unlock()
	if ok {
		return cached, nil
	}
	if userID == nil || *userID == "" {
		return nil, &value_objects.ValueError{Msg: "user_id is required for agent facade creation (no fallback allowed for DDD compliance)"}
	}

	backend := f.agentRepositoryFactory
	if backend == nil {
		backend = AgentRepositoryFactoryDefault
	}
	if backend != nil {
		repository, err := backend(*userID)
		if err == nil && AgentApplicationFacadeConstructor != nil {
			facade := AgentApplicationFacadeConstructor(repository)
			f.cacheMu.Lock()
			f.facadesCache[cacheKey] = facade
			f.cacheMu.Unlock()
			return facade, nil
		}
	}

	mock := &MockAgentApplicationFacade{}
	f.cacheMu.Lock()
	f.facadesCache[cacheKey] = mock
	f.cacheMu.Unlock()
	return mock, nil
}

// ClearCache mirrors clear_cache.
func (f *AgentFacadeFactory) ClearCache() {
	f.cacheMu.Lock()
	defer f.cacheMu.Unlock()
	f.facadesCache = map[string]AgentApplicationFacade{}
}

// GetCachedFacade mirrors get_cached_facade.
func (f *AgentFacadeFactory) GetCachedFacade(projectID string) AgentApplicationFacade {
	f.cacheMu.Lock()
	defer f.cacheMu.Unlock()
	facade, _ := f.facadesCache[projectID]
	return facade
}

// CreateFacade mirrors create_facade.
func (f *AgentFacadeFactory) CreateFacade(projectID string) (AgentApplicationFacade, error) {
	if projectID == "" {
		return nil, &value_objects.ValueError{Msg: "Project ID is required. No fallback to default project allowed per DDD principles."}
	}
	return f.CreateAgentFacade(projectID, nil)
}

// Create mirrors the `create` staticmethod: it always raises.
func (f *AgentFacadeFactory) Create() (AgentApplicationFacade, error) {
	return nil, &value_objects.ValueError{Msg: "Cannot create agent facade: Project ID is required. No fallback to default project allowed per DDD principles."}
}

// MockAgentApplicationFacade mirrors the Python mock facade.
type MockAgentApplicationFacade struct{}

func (m *MockAgentApplicationFacade) RegisterAgent(projectID, agentID, name string, callAgent *string) *entities.OrderedMap[any] {
	agent := entities.NewOrderedMap[any]()
	agent.Set("id", agentID)
	agent.Set("name", name)
	agent.Set("project_id", projectID)
	agent.Set("call_agent", callAgent)
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent", agent)
	out.Set("message", "Mock: Agent "+name+" registered successfully")
	return out
}

func (m *MockAgentApplicationFacade) AssignAgent(projectID, agentID, gitBranchID string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent_id", agentID)
	out.Set("git_branch_id", gitBranchID)
	out.Set("message", "Mock: Agent "+agentID+" assigned to "+gitBranchID)
	return out
}

func (m *MockAgentApplicationFacade) UnassignAgent(projectID, agentID, gitBranchID string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent_id", agentID)
	out.Set("git_branch_id", gitBranchID)
	out.Set("message", "Mock: Agent "+agentID+" unassigned from "+gitBranchID)
	return out
}

func (m *MockAgentApplicationFacade) GetAgent(projectID, agentID string) *entities.OrderedMap[any] {
	agent := entities.NewOrderedMap[any]()
	agent.Set("id", agentID)
	agent.Set("name", "Mock Agent "+agentID)
	agent.Set("project_id", projectID)
	agent.Set("call_agent", nil)
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent", agent)
	out.Set("message", "Mock: Agent "+agentID+" retrieved successfully")
	return out
}

func (m *MockAgentApplicationFacade) ListAgents(projectID string) *entities.OrderedMap[any] {
	agents := []any{}
	for _, spec := range []struct{ id, name string }{{"mock-agent-1", "Mock Agent 1"}, {"mock-agent-2", "Mock Agent 2"}} {
		agent := entities.NewOrderedMap[any]()
		agent.Set("id", spec.id)
		agent.Set("name", spec.name)
		agent.Set("project_id", projectID)
		agent.Set("call_agent", nil)
		agents = append(agents, agent)
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agents", agents)
	out.Set("message", "Mock: Listed agents for project "+projectID)
	return out
}

func (m *MockAgentApplicationFacade) UpdateAgent(projectID, agentID string, name, callAgent *string) *entities.OrderedMap[any] {
	effectiveName := "Mock Agent " + agentID
	if name != nil && *name != "" {
		effectiveName = *name
	}
	agent := entities.NewOrderedMap[any]()
	agent.Set("id", agentID)
	agent.Set("name", effectiveName)
	agent.Set("project_id", projectID)
	agent.Set("call_agent", callAgent)
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent", agent)
	out.Set("message", "Mock: Agent "+agentID+" updated successfully")
	return out
}

func (m *MockAgentApplicationFacade) UnregisterAgent(projectID, agentID string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("agent_id", agentID)
	out.Set("message", "Mock: Agent "+agentID+" unregistered successfully")
	return out
}

func (m *MockAgentApplicationFacade) RebalanceAgents(projectID string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("project_id", projectID)
	out.Set("message", "Mock: Agents rebalanced for project "+projectID)
	return out
}
