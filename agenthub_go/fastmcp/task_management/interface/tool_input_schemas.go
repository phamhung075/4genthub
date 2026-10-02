package interfacelayer

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// Code derived from the Python register_tools signatures (FastMCP builds each
// inputSchema from them): per-parameter description prefix and JSON-schema type
// fragment, in signature order. The description text itself comes from the
// controllers' *_description Parameters (single source of truth).

type toolParam struct {
	Name, Prefix, Type string
}

var toolParamSpecs = map[string][]toolParam{
	"manage_task": {
		{"action", "", `{"type":"string"}`},
		{"task_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"git_branch_id", "[REQUIRED for 'create' and 'next' actions] ", `{"type":"string"}`},
		{"title", "[OPTIONAL] ", `{"type":"string"}`},
		{"description", "[OPTIONAL] ", `{"type":"string"}`},
		{"status", "[OPTIONAL] ", `{"type":"string"}`},
		{"priority", "[OPTIONAL] ", `{"type":"string"}`},
		{"details", "[OPTIONAL] ", `{"type":"string"}`},
		{"estimated_effort", "[OPTIONAL] ", `{"type":"string"}`},
		{"progress_percentage", "[OPTIONAL] ", `{"type":"integer"}`},
		{"assignees", "[OPTIONAL] ", `{"anyOf":[{"type":"string"},{"items":{"type":"string"},"type":"array"}]}`},
		{"labels", "[OPTIONAL] ", `{"anyOf":[{"type":"string"},{"items":{"type":"string"},"type":"array"}]}`},
		{"due_date", "[OPTIONAL] ", `{"type":"string"}`},
		{"dependencies", "[OPTIONAL] ", `{"anyOf":[{"type":"string"},{"items":{"type":"string"},"type":"array"}]}`},
		{"dependency_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"context_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"completion_summary", "[OPTIONAL] ", `{"type":"string"}`},
		{"testing_notes", "[OPTIONAL] ", `{"type":"string"}`},
		{"query", "[OPTIONAL] ", `{"type":"string"}`},
		{"limit", "[OPTIONAL] ", `{"type":"integer"}`},
		{"offset", "[OPTIONAL] ", `{"type":"integer"}`},
		{"sort_by", "[OPTIONAL] ", `{"type":"string"}`},
		{"sort_order", "[OPTIONAL] ", `{"type":"string"}`},
		{"include_context", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"force_full_generation", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"assignee", "[OPTIONAL] ", `{"type":"string"}`},
		{"tag", "[OPTIONAL] ", `{"type":"string"}`},
		{"user_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"requirements", "[OPTIONAL] ", `{"type":"string"}`},
		{"context", "[OPTIONAL] ", `{"type":"string"}`},
		{"auto_create_tasks", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"enable_ai_breakdown", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"enable_smart_assignment", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"enable_auto_subtasks", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"ai_requirements", "[OPTIONAL] ", `{"type":"string"}`},
		{"planning_context", "[OPTIONAL] ", `{"type":"string"}`},
		{"analyze_complexity", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"suggest_optimizations", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"identify_risks", "[OPTIONAL] ", `{"type":"boolean"}`},
		{"available_agents", "[OPTIONAL] ", `{"type":"string"}`},
	},
	"manage_subtask": {
		{"action", "[OPTIONAL] ", `{"type":"string"}`},
		{"task_id", "[REQUIRED for 'create', 'update', 'delete', 'get', 'list', 'complete' actions] ", `{"type":"string"}`},
		{"subtask_id", "[REQUIRED for 'update', 'delete', 'get', 'complete' actions] ", `{"type":"string"}`},
		{"title", "[REQUIRED for 'create' action] ", `{"type":"string"}`},
		{"description", "[OPTIONAL] ", `{"type":"string"}`},
		{"status", "[OPTIONAL] ", `{"type":"string"}`},
		{"priority", "[OPTIONAL] ", `{"type":"string"}`},
		{"assignees", "[OPTIONAL] ", `{"type":"string"}`},
		{"progress_percentage", "[OPTIONAL] ", `{"type":"integer"}`},
		{"progress_notes", "[REQUIRED for 'update' and 'complete' actions] ", `{"type":"string"}`},
		{"completion_summary", "[REQUIRED for 'complete' action] ", `{"type":"string"}`},
		{"testing_notes", "[OPTIONAL] ", `{"type":"string"}`},
		{"insights_found", "[OPTIONAL] ", `{"type":"string"}`},
		{"challenges_overcome", "[OPTIONAL] ", `{"type":"string"}`},
		{"skills_learned", "[OPTIONAL] ", `{"type":"string"}`},
		{"next_recommendations", "[OPTIONAL] ", `{"type":"string"}`},
		{"deliverables", "[OPTIONAL] ", `{"type":"string"}`},
		{"completion_quality", "[OPTIONAL] ", `{"type":"string"}`},
		{"impact_on_parent", "[OPTIONAL] ", `{"type":"string"}`},
		{"blockers", "[OPTIONAL] ", `{"type":"string"}`},
		{"user_id", "[OPTIONAL] ", `{"type":"string"}`},
	},
	"manage_context": {
		{"action", "[OPTIONAL] ", `{"type":"string"}`},
		{"level", "[REQUIRED for all actions except 'list'] ", `{"type":"string"}`},
		{"context_id", "[REQUIRED for all actions except 'list'] ", `{"type":"string"}`},
		{"data", "[OPTIONAL] ", `{"type":"string"}`},
		{"user_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"project_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"git_branch_id", "[OPTIONAL] ", `{"type":"string"}`},
		{"force_refresh", "[OPTIONAL] ", `{"type":"string"}`},
		{"include_inherited", "[OPTIONAL] ", `{"type":"string"}`},
		{"propagate_changes", "[OPTIONAL] ", `{"type":"string"}`},
		{"delegate_to", "[REQUIRED for 'delegate' action] ", `{"type":"string"}`},
		{"delegate_data", "[OPTIONAL] ", `{"type":"string"}`},
		{"delegation_reason", "[OPTIONAL] ", `{"type":"string"}`},
		{"content", "[REQUIRED for 'add_insight' and 'add_progress' actions] ", `{"type":"string"}`},
		{"category", "[OPTIONAL] ", `{"type":"string"}`},
		{"importance", "[OPTIONAL] ", `{"type":"string"}`},
		{"agent", "[OPTIONAL] ", `{"type":"string"}`},
		{"filters", "[OPTIONAL] ", `{"type":"string"}`},
	},
	"manage_project": {
		{"action", "[OPTIONAL] ", `{"type":"string"}`},
		{"project_id", "[REQUIRED for most actions except 'create' and 'list'] ", `{"type":"string"}`},
		{"name", "[REQUIRED for 'create' action] ", `{"type":"string"}`},
		{"description", "[OPTIONAL] ", `{"type":"string"}`},
		{"force", "[OPTIONAL] ", `{"type":"string"}`},
		{"user_id", "[OPTIONAL] ", `{"type":"string"}`},
	},
	"manage_git_branch": {
		{"action", "[OPTIONAL] ", `{"type":"string"}`},
		{"project_id", "[REQUIRED for all actions] ", `{"type":"string"}`},
		{"git_branch_id", "[REQUIRED for most actions except 'create' and 'list'] ", `{"type":"string"}`},
		{"git_branch_name", "[REQUIRED for 'create' action] ", `{"type":"string"}`},
		{"git_branch_description", "[OPTIONAL] ", `{"type":"string"}`},
		{"agent_id", "[REQUIRED for 'assign_agent' and 'unassign_agent' actions] ", `{"type":"string"}`},
		{"user_id", "[OPTIONAL] ", `{"type":"string"}`},
	},
	"manage_agent": {
		{"action", "[OPTIONAL] ", `{"type":"string"}`},
		{"project_id", "[REQUIRED for all actions] ", `{"anyOf":[{"type":"string"},{"type":"null"}]}`},
		{"agent_id", "[REQUIRED for most actions except 'register', 'list', and 'rebalance'] ", `{"type":"string"}`},
		{"name", "[REQUIRED for 'register' action] ", `{"type":"string"}`},
		{"call_agent", "[OPTIONAL] ", `{"type":"string"}`},
		{"git_branch_id", "[REQUIRED for 'assign' and 'unassign' actions] ", `{"type":"string"}`},
		{"user_id", "[OPTIONAL] ", `{"type":"string"}`},
	},
}

// toolInputSchema builds the MCP inputSchema FastMCP derives from the Python tool
// signature: {"type":"object","properties":{...},"required":["action"]}, each
// property carrying its type fragment, "default": null (unless required), the
// prefixed description and the Title Case name.
func toolInputSchema(tool string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	props := params
	if p, ok := params.Get("properties"); ok {
		if pm, ok := p.(*entities.OrderedMap[any]); ok {
			props = pm
		}
	}
	properties := entities.NewOrderedMap[any]()
	for _, spec := range toolParamSpecs[tool] {
		prop := entities.NewOrderedMap[any]()
		fragment, err := entities.DecodeJSON([]byte(spec.Type))
		if err != nil {
			panic(err)
		}
		fm := fragment.(*entities.OrderedMap[any])
		for _, k := range fm.Keys() {
			v, _ := fm.Get(k)
			prop.Set(k, v)
		}
		if spec.Name != "action" {
			prop.Set("default", nil)
		}
		desc := ""
		if raw, ok := props.Get(spec.Name); ok {
			if pm, ok := raw.(*entities.OrderedMap[any]); ok {
				if d, ok := pm.Get("description"); ok {
					desc, _ = d.(string)
				}
			}
		}
		prop.Set("description", spec.Prefix+desc)
		prop.Set("title", toolParamTitle(spec.Name))
		properties.Set(spec.Name, prop)
	}
	schema := entities.NewOrderedMap[any]()
	schema.Set("properties", properties)
	schema.Set("required", []any{"action"})
	schema.Set("type", "object")
	return schema
}

// toolParamTitle is pydantic's title: underscores to spaces, each word capitalised.
func toolParamTitle(name string) string {
	words := strings.Split(name, "_")
	for i, w := range words {
		if w != "" {
			words[i] = strings.ToUpper(w[:1]) + w[1:]
		}
	}
	return strings.Join(words, " ")
}
