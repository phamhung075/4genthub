package api_controllers

import (
	"context"
	"reflect"
	"sort"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	tmdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// AgentMetadataFacade is the minimal facade surface AgentAPIController calls, using the exact
// argument lists of the Python calls. The Python AgentApplicationFacade does not define
// list_all_agents/list_agents_by_category/list_agent_categories and its get_agent needs
// project_id, so every call raises AttributeError/TypeError, is swallowed, and the controller
// returns the static fallback. The Go concrete facade likewise does not satisfy this interface,
// so the provider must be nil (fallback) unless a future facade implements it.
type AgentMetadataFacade interface {
	ListAllAgents(ctx context.Context) *entities.OrderedMap[any]
	GetAgent(ctx context.Context, agentID string) *entities.OrderedMap[any]
	ListAgentsByCategory(ctx context.Context, category string) *entities.OrderedMap[any]
	ListAgentCategories(ctx context.Context) *entities.OrderedMap[any]
}

// AgentFacadeProvider yields the agent facade (Python's FacadeService.get_agent_facade).
type AgentFacadeProvider interface {
	GetAgentFacade(projectID string, userID *string) (AgentMetadataFacade, error)
}

// AgentAPIController ports AgentAPIController.
type AgentAPIController struct {
	facadeService AgentFacadeProvider
}

// NewAgentAPIController builds the controller. Python uses the global
// FacadeService.get_instance(); the Go FacadeService has no singleton, so the provider is
// injected (nil reproduces the Python always-fallback behaviour).
func NewAgentAPIController(facadeService AgentFacadeProvider) *AgentAPIController {
	return &AgentAPIController{facadeService: facadeService}
}

func (c *AgentAPIController) resolveFacade(userID string) (AgentMetadataFacade, error) {
	if c.facadeService == nil {
		return nil, &value_objects.ValueError{Msg: "AgentApplicationFacade is not available"}
	}
	return c.facadeService.GetAgentFacade("", &userID)
}

// GetAgentMetadata ports get_agent_metadata.
func (c *AgentAPIController) GetAgentMetadata(ctx context.Context, userID string, session *tmdb.SessionManager) *entities.OrderedMap[any] {
	_ = session
	facade, err := c.resolveFacade(userID)
	if err != nil {
		return c.fallbackAll(err)
	}
	result := facade.ListAllAgents(ctx)
	success, _ := result.Get("success")
	if !value_objects.PyTruthy(success) {
		staticAgents := c.staticMetadata()
		return agentControllerResponse("success", true, "agents", staticAgents, "total", len(staticAgents), "source", "static")
	}
	agents, ok := result.Get("agents")
	if !ok {
		agents = []any{}
	}
	return agentControllerResponse("success", true, "agents", agents, "total", agentControllerLen(agents), "source", "facade")
}

func (c *AgentAPIController) fallbackAll(err error) *entities.OrderedMap[any] {
	staticAgents := c.staticMetadata()
	return agentControllerResponse("success", true, "agents", staticAgents, "total", len(staticAgents), "source", "fallback", "error", err.Error())
}

// GetAgentByID ports get_agent_by_id.
func (c *AgentAPIController) GetAgentByID(ctx context.Context, agentID, userID string, session *tmdb.SessionManager) *entities.OrderedMap[any] {
	_ = session
	facade, err := c.resolveFacade(userID)
	if err != nil {
		return c.fallbackOne(agentID, err)
	}
	result := facade.GetAgent(ctx, agentID)
	success, _ := result.Get("success")
	if !value_objects.PyTruthy(success) {
		if staticAgent := c.findStaticAgent(agentID); staticAgent != nil {
			return agentControllerResponse("success", true, "agent", staticAgent, "source", "static")
		}
		return agentControllerResponse("success", false, "error", "Agent '"+agentID+"' not found", "agent", nil)
	}
	agent, _ := result.Get("agent")
	return agentControllerResponse("success", true, "agent", agent, "source", "facade")
}

func (c *AgentAPIController) fallbackOne(agentID string, err error) *entities.OrderedMap[any] {
	if staticAgent := c.findStaticAgent(agentID); staticAgent != nil {
		return agentControllerResponse("success", true, "agent", staticAgent, "source", "fallback")
	}
	return agentControllerResponse("success", false, "error", err.Error(), "agent", nil)
}

// GetAgentsByCategory ports get_agents_by_category.
func (c *AgentAPIController) GetAgentsByCategory(ctx context.Context, category, userID string, session *tmdb.SessionManager) *entities.OrderedMap[any] {
	_ = session
	facade, err := c.resolveFacade(userID)
	if err != nil {
		staticAgents := c.staticByCategory(category)
		return agentControllerResponse("success", true, "category", category, "agents", staticAgents, "total", len(staticAgents), "source", "fallback")
	}
	result := facade.ListAgentsByCategory(ctx, category)
	success, _ := result.Get("success")
	if !value_objects.PyTruthy(success) {
		staticAgents := c.staticByCategory(category)
		return agentControllerResponse("success", true, "category", category, "agents", staticAgents, "total", len(staticAgents), "source", "static")
	}
	agents, ok := result.Get("agents")
	if !ok {
		agents = []any{}
	}
	return agentControllerResponse("success", true, "category", category, "agents", agents, "total", agentControllerLen(agents), "source", "facade")
}

// ListAgentCategories ports list_agent_categories.
func (c *AgentAPIController) ListAgentCategories(ctx context.Context, userID string, session *tmdb.SessionManager) *entities.OrderedMap[any] {
	_ = session
	facade, err := c.resolveFacade(userID)
	if err != nil {
		categories := c.staticCategories()
		return agentControllerResponse("success", true, "categories", categories, "total", len(categories), "source", "fallback")
	}
	result := facade.ListAgentCategories(ctx)
	success, _ := result.Get("success")
	if !value_objects.PyTruthy(success) {
		categories := c.staticCategories()
		return agentControllerResponse("success", true, "categories", categories, "total", len(categories), "source", "static")
	}
	categories, ok := result.Get("categories")
	if !ok {
		categories = []any{}
	}
	return agentControllerResponse("success", true, "categories", categories, "total", agentControllerLen(categories), "source", "facade")
}

// staticMetadata ports _get_static_metadata.
func (c *AgentAPIController) staticMetadata() []*entities.OrderedMap[any] {
	return []*entities.OrderedMap[any]{
		agentControllerMetadata("master-orchestrator-agent", "Uber Orchestrator Agent", "master-orchestrator-agent",
			"Master Coordinator and Decision Maker",
			"The highest-level orchestrator that coordinates all other agents",
			"orchestration", "orchestrator", "critical",
			[]string{"Multi-agent coordination", "Strategic planning", "Resource allocation", "Workflow orchestration"},
			[]string{"All MCP tools"},
			"Use for high-level coordination and when multiple agents need to work together"),
		agentControllerMetadata("coding-agent", "Coding Agent", "coding-agent",
			"Software Development Specialist",
			"Specialized in writing, refactoring, and implementing code",
			"development", "specialist", "high",
			[]string{"Code implementation", "Refactoring", "API development", "Database design"},
			[]string{"Code editing tools", "File management"},
			"Use for all coding and implementation tasks"),
		agentControllerMetadata("debugger-agent", "Debugger Agent", "debugger-agent",
			"Bug Detection and Resolution Specialist",
			"Expert in identifying, analyzing, and fixing bugs and errors",
			"development", "specialist", "high",
			[]string{"Error analysis", "Stack trace interpretation", "Performance debugging"},
			[]string{"Debugging tools", "Log analysis"},
			"Use when encountering errors, test failures, or unexpected behavior"),
		agentControllerMetadata("test-orchestrator-agent", "Test Orchestrator Agent", "test-orchestrator-agent",
			"Testing Strategy and Execution Coordinator",
			"Manages comprehensive testing strategies and coordinates test execution",
			"quality", "orchestrator", "high",
			[]string{"Test strategy design", "Test suite orchestration", "Coverage analysis"},
			[]string{"Test frameworks", "Coverage tools"},
			"Use for designing and executing comprehensive test strategies"),
	}
}

func agentControllerMetadata(id, name, callName, role, description, category, typ, priority string, capabilities, tools []string, guidelines string) *entities.OrderedMap[any] {
	return agentControllerResponse(
		"id", id, "name", name, "call_name", callName, "role", role, "description", description,
		"category", category, "type", typ, "priority", priority,
		"capabilities", capabilities, "tools", tools, "guidelines", guidelines,
	)
}

// findStaticAgent ports _find_static_agent.
func (c *AgentAPIController) findStaticAgent(agentID string) *entities.OrderedMap[any] {
	for _, a := range c.staticMetadata() {
		if v, _ := a.Get("id"); v == agentID {
			return a
		}
	}
	return nil
}

// staticByCategory is the static metadata filtered by category.
func (c *AgentAPIController) staticByCategory(category string) []*entities.OrderedMap[any] {
	out := []*entities.OrderedMap[any]{}
	for _, a := range c.staticMetadata() {
		if v, _ := a.Get("category"); v == category {
			out = append(out, a)
		}
	}
	return out
}

// staticCategories ports _get_static_categories (unique categories, sorted).
func (c *AgentAPIController) staticCategories() []string {
	set := map[string]struct{}{}
	for _, a := range c.staticMetadata() {
		cat, ok := a.Get("category")
		if !ok || cat == nil {
			set["uncategorized"] = struct{}{}
			continue
		}
		if s, ok := cat.(string); ok {
			set[s] = struct{}{}
		}
	}
	out := make([]string, 0, len(set))
	for k := range set {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func agentControllerResponse(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		key, _ := pairs[i].(string)
		m.Set(key, pairs[i+1])
	}
	return m
}

// agentControllerLen mirrors Python len() for the facade's list-like values.
func agentControllerLen(v any) int {
	if v == nil {
		return 0
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Slice, reflect.Array, reflect.Map, reflect.String:
		return rv.Len()
	}
	return 0
}
