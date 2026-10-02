package workflow_guidance

// Subtask Workflow Guidance Module
// (Python workflow_guidance/subtask.py).

import (
	"sort"
	"strconv"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SubtaskWorkflowGuidance provides workflow guidance for subtask operations.
type SubtaskWorkflowGuidance struct{}

// GenerateGuidance ports generate_guidance.
func (SubtaskWorkflowGuidance) GenerateGuidance(action string, context *entities.OrderedMap[any]) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			// Python `except Exception`: return minimal guidance.
			out = entities.NewOrderedMap[any]()
			out.Set("hints", []any{"Continue with your workflow"})
			out.Set("next_actions", []any{})
			out.Set("rules", []any{})
			out.Set("recommendations", []any{})
		}
	}()

	hints := []any{}
	nextActions := []any{}
	rules := []any{}
	recommendations := []any{}

	switch action {
	case "create":
		hints = append(hints, "Subtask created successfully. Remember to update progress regularly.")
		nextActions = append(nextActions, wgsAction("update", "Update progress as you work"))
		rules = append(rules, "Always provide completion_summary when completing subtasks")
	case "update":
		response := wgsOM(wgsGet(context, "response"))
		if wgsNum(wgsGet(wgsOM(wgsGet(response, "subtask")), "progress_percentage")) >= 75 {
			hints = append(hints, "Subtask is nearing completion. Prepare completion summary.")
		}
		nextActions = append(nextActions, wgsAction("complete", "Complete when finished"))
	case "complete":
		hints = append(hints, "Subtask completed! Parent task progress has been updated.")
		nextActions = append(nextActions, wgsAction("list", "Check overall progress"))
		recommendations = append(recommendations, "Review parent task to see if it's ready for completion")
	case "list":
		response := wgsOM(wgsGet(context, "response"))
		subtasks := wgsList(wgsGet(response, "subtasks"))
		completed := 0
		for _, s := range subtasks {
			if wgsStr(wgsGet(wgsOM(s), "status")) == "done" {
				completed++
			}
		}
		total := len(subtasks)
		if completed == total && total > 0 {
			hints = append(hints, "All "+strconv.Itoa(total)+" subtasks complete! Parent task ready for completion.")
			recommendations = append(recommendations, "Consider completing the parent task")
		} else if completed > 0 {
			hints = append(hints, "Progress: "+strconv.Itoa(completed)+"/"+strconv.Itoa(total)+" subtasks completed")
		}
	case "delete":
		hints = append(hints, "Subtask deleted. Parent task progress recalculated.")
		nextActions = append(nextActions, wgsAction("list", "View remaining subtasks"))
	}

	guidance := entities.NewOrderedMap[any]()
	guidance.Set("hints", hints)
	guidance.Set("next_actions", nextActions)
	guidance.Set("rules", rules)
	guidance.Set("recommendations", recommendations)
	return guidance
}

// SubtaskWorkflowFactory is the factory for SubtaskWorkflowGuidance instances.
type SubtaskWorkflowFactory struct{}

// Create ports the static create().
func (SubtaskWorkflowFactory) Create() *SubtaskWorkflowGuidance {
	return &SubtaskWorkflowGuidance{}
}

func wgsAction(action, description string) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("action", action)
	om.Set("description", description)
	return om
}

func wgsGet(om *entities.OrderedMap[any], k string) any {
	if om == nil {
		return nil
	}
	v, _ := om.Get(k)
	return v
}

func wgsOM(v any) *entities.OrderedMap[any] {
	switch t := v.(type) {
	case *entities.OrderedMap[any]:
		return t
	case map[string]any:
		om := entities.NewOrderedMap[any]()
		keys := make([]string, 0, len(t))
		for k := range t {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			om.Set(k, t[k])
		}
		return om
	}
	return nil
}

func wgsList(v any) []any {
	switch t := v.(type) {
	case []any:
		return t
	case []string:
		out := make([]any, len(t))
		for i, s := range t {
			out[i] = s
		}
		return out
	}
	return nil
}

func wgsNum(v any) float64 {
	switch t := v.(type) {
	case float64:
		return t
	case float32:
		return float64(t)
	case int:
		return float64(t)
	case int64:
		return float64(t)
	case int32:
		return float64(t)
	}
	return 0
}

func wgsStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return value_objects.PyStr(v)
}
