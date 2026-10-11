// Token cost configuration for MCP operations, ported from
// agenthub_main/src/fastmcp/auth/config/token_costs.py.
package config

import "agenthub/fastmcp/task_management/domain/entities"

// tokenCostPairs is TOKEN_COSTS in Python insertion order.
var tokenCostPairs = []struct {
	op   string
	cost int
}{
	// Project operations
	{"create_project", 10},
	{"update_project", 5},
	{"delete_project", 5},
	{"list_projects", 1},
	{"get_project", 1},
	{"project_health_check", 3},
	{"cleanup_obsolete", 5},
	{"validate_integrity", 3},
	{"rebalance_agents", 5},
	// Git Branch operations
	{"create_branch", 5},
	{"update_branch", 3},
	{"delete_branch", 3},
	{"list_branches", 1},
	{"get_branch", 1},
	{"get_branch_statistics", 2},
	{"archive_branch", 3},
	{"restore_branch", 3},
	// Task operations
	{"create_task", 5},
	{"update_task", 3},
	{"complete_task", 3},
	{"delete_task", 3},
	{"list_tasks", 1},
	{"get_task", 1},
	{"search_tasks", 2},
	{"next_task", 2},
	{"add_dependency", 2},
	{"remove_dependency", 2},
	{"ai_plan", 15},
	{"ai_create", 10},
	{"ai_enhance", 8},
	{"ai_analyze", 7},
	{"ai_suggest_agents", 5},
	// Subtask operations
	{"create_subtask", 3},
	{"update_subtask", 2},
	{"complete_subtask", 2},
	{"delete_subtask", 2},
	{"list_subtasks", 1},
	{"get_subtask", 1},
	// Agent operations
	{"assign_agent", 3},
	{"unassign_agent", 2},
	// Context operations
	{"create_context", 5},
	{"update_context", 3},
	{"delete_context", 3},
	{"get_context", 1},
	{"resolve_context", 2},
	{"delegate_context", 4},
	{"add_insight", 2},
	{"add_progress", 2},
	{"list_contexts", 1},
	// Authentication operations (free - should not consume tokens)
	{"login", 0},
	{"register", 0},
	{"logout", 0},
	{"refresh_token", 0},
	{"verify_email", 0},
	{"forgot_password", 0},
	{"reset_password", 0},
	// Token balance operations (free - managing tokens shouldn't cost tokens)
	{"get_balance", 0},
	{"get_usage_stats", 0},
	{"add_tokens", 0},
	{"update_quota", 0},
}

// TokenCosts is TOKEN_COSTS as an insertion-ordered dict.
var TokenCosts = func() *entities.OrderedMap[int] {
	m := entities.NewOrderedMap[int]()
	for _, p := range tokenCostPairs {
		m.Set(p.op, p.cost)
	}
	return m
}()

// GetOperationCost is get_operation_cost: TOKEN_COSTS.get(operation, default).
func GetOperationCost(operation string, def int) int {
	if v, ok := TokenCosts.Get(operation); ok {
		return v
	}
	return def
}

// GetAllCosts is get_all_costs: a copy of TOKEN_COSTS.
func GetAllCosts() *entities.OrderedMap[int] { return TokenCosts.Copy() }

// GetFreeOperations is get_free_operations: operations with cost 0 in insertion order.
func GetFreeOperations() []string {
	var out []string
	for _, k := range TokenCosts.Keys() {
		if v, _ := TokenCosts.Get(k); v == 0 {
			out = append(out, k)
		}
	}
	return out
}

// GetExpensiveOperations is get_expensive_operations: cost >= threshold, in insertion order.
func GetExpensiveOperations(threshold int) *entities.OrderedMap[int] {
	m := entities.NewOrderedMap[int]()
	for _, k := range TokenCosts.Keys() {
		if v, _ := TokenCosts.Get(k); v >= threshold {
			m.Set(k, v)
		}
	}
	return m
}
