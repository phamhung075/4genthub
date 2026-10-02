// Package agent ports task_management/application/dtos/agent.
package agent

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentResponse is the response DTO for agent data.
type AgentResponse struct {
	ID          string
	Name        string
	CallAgent   string
	Assignments []string
}

// AgentResponseFromDict mirrors AgentResponse.from_dict: missing keys fall back
// to "" / [].
func AgentResponseFromDict(data *entities.OrderedMap[any]) AgentResponse {
	return AgentResponse{
		ID:          orderedString(data, "id", ""),
		Name:        orderedString(data, "name", ""),
		CallAgent:   orderedString(data, "call_agent", ""),
		Assignments: orderedStringList(data, "assignments"),
	}
}

func orderedValue(data *entities.OrderedMap[any], key string) (any, bool) {
	if data == nil {
		return nil, false
	}
	return data.Get(key)
}

func orderedString(data *entities.OrderedMap[any], key, def string) string {
	v, ok := orderedValue(data, key)
	if !ok || v == nil {
		return def
	}
	if s, ok := v.(string); ok {
		return s
	}
	return value_objects.PyStr(v)
}

func orderedStringList(data *entities.OrderedMap[any], key string) []string {
	v, ok := orderedValue(data, key)
	if !ok || v == nil {
		return []string{}
	}
	switch xs := v.(type) {
	case []string:
		return append([]string{}, xs...)
	case []any:
		out := make([]string, 0, len(xs))
		for _, x := range xs {
			if x == nil {
				out = append(out, "None")
				continue
			}
			out = append(out, value_objects.PyStr(x))
		}
		return out
	}
	return []string{}
}
