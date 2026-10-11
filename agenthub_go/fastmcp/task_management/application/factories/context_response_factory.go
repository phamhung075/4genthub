// Package factories ports task_management/application/factories.
//
// This file ports factories/context_response_factory.py.
package factories

import (
	"math/big"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ContextResponseUnifiedFacade is the minimal UnifiedContextFacade surface used by
// ContextResponseFactory.apply_to_task_response. The Python method lazily imports
// FacadeService.get_unified_context_facade(); that service is ported in
// application/services/facade_service.go and is injected through
// ContextResponseUnifiedFacadeProvider.
type ContextResponseUnifiedFacade interface {
	GetContext(level, contextID string, includeInherited bool) *entities.OrderedMap[any]
}

// ContextResponseUnifiedFacadeProvider mirrors FacadeService.get_unified_context_facade.
var ContextResponseUnifiedFacadeProvider func() ContextResponseUnifiedFacade

// contextResponseGet is dict.get(key, default).
func contextResponseGet(m *entities.OrderedMap[any], key string, def any) any {
	if m == nil {
		return def
	}
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}

// contextResponseAsDict is isinstance(v, dict).
func contextResponseAsDict(v any) (*entities.OrderedMap[any], bool) {
	m, ok := v.(*entities.OrderedMap[any])
	if !ok || m == nil {
		return nil, false
	}
	return m, true
}

// contextResponseIsNumber is isinstance(v, (int, float)) (bool is an int in Python).
func contextResponseIsNumber(v any) bool {
	switch v.(type) {
	case bool, int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64,
		float32, float64, *big.Int:
		return true
	}
	return false
}

// contextResponsePyIn is Python's `key in container` for the containers reached here. A
// non-container panics so the caller's recover mirrors the caught TypeError.
func contextResponsePyIn(container any, key string) bool {
	switch c := container.(type) {
	case *entities.OrderedMap[any]:
		return c != nil && c.Has(key)
	case string:
		return strings.Contains(c, key)
	case []any:
		for _, x := range c {
			if s, ok := x.(string); ok && s == key {
				return true
			}
		}
		return false
	case nil:
		panic("argument of type 'NoneType' is not iterable")
	}
	panic("argument is not iterable")
}

// ContextResponseCreateUnifiedContext mirrors
// ContextResponseFactory.create_unified_context.
func ContextResponseCreateUnifiedContext(contextData *entities.OrderedMap[any]) (result *entities.OrderedMap[any]) {
	if contextData == nil || contextData.Len() == 0 {
		return nil
	}
	// Python wraps the whole body in `except Exception` and returns None.
	defer func() {
		if recover() != nil {
			result = nil
		}
	}()
	var unified any
	if contextData.Has("template_context") {
		unified = contextResponseGet(contextData, "template_context", nil)
	} else if contextData.Has("success") && contextData.Has("template_context") {
		unified = contextResponseGet(contextData, "template_context", nil)
	} else if nested, ok := contextResponseAsDict(contextResponseGet(contextData, "context", nil)); ok {
		if nested.Has("template_context") {
			unified = contextResponseGet(nested, "template_context", nil)
		} else if nested.Has("task_data") {
			unified = contextResponseConvertTaskDataToTemplate(nested)
		}
	} else if contextData.Has("metadata") && contextResponsePyIn(contextResponseGet(contextData, "metadata", nil), "task_id") {
		unified = contextData
	} else if contextData.Has("task_data") {
		unified = contextResponseConvertTaskDataToTemplate(contextData)
	} else {
		for _, key := range contextData.Keys() {
			value := contextResponseGet(contextData, key, nil)
			v, ok := contextResponseAsDict(value)
			if !ok {
				continue
			}
			if v.Has("template_context") {
				unified = contextResponseGet(v, "template_context", nil)
				break
			} else if v.Has("task_data") {
				unified = contextResponseConvertTaskDataToTemplate(v)
				break
			}
		}
	}
	if unified == nil {
		return nil
	}
	dict, ok := unified.(*entities.OrderedMap[any])
	if !ok || dict.Len() == 0 {
		return nil
	}
	return contextResponseEnsureCompleteStructure(dict)
}

// contextResponseConvertTaskDataToTemplate mirrors
// ContextResponseFactory._convert_task_data_to_template.
func contextResponseConvertTaskDataToTemplate(contextData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	taskData, ok := contextResponseAsDict(contextResponseGet(contextData, "task_data", nil))
	if !ok {
		// Python `.get` on a non-dict task_data raises; create_unified_context catches it.
		panic("task_data has no attribute 'get'")
	}

	templateContext := entities.NewOrderedMap[any]()

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("task_id", contextResponseGet(contextData, "id", ""))
	metadata.Set("status", contextResponseGet(taskData, "status", "todo"))
	metadata.Set("priority", contextResponseGet(taskData, "priority", "medium"))
	metadata.Set("assignees", contextResponseGet(taskData, "assignees", []any{}))
	metadata.Set("labels", contextResponseGet(taskData, "labels", []any{}))
	metadata.Set("created_at", contextResponseGet(taskData, "created_at", nil))
	metadata.Set("updated_at", contextResponseGet(taskData, "updated_at", nil))
	metadata.Set("version", int64(1))
	templateContext.Set("metadata", metadata)

	objective := entities.NewOrderedMap[any]()
	objective.Set("title", contextResponseGet(taskData, "title", ""))
	objective.Set("description", contextResponseGet(taskData, "description", ""))
	objective.Set("estimated_effort", contextResponseGet(taskData, "estimated_effort", ""))
	objective.Set("due_date", contextResponseGet(taskData, "due_date", nil))
	templateContext.Set("objective", objective)

	progressAny := contextResponseGet(contextData, "progress", nil)
	if progress, ok := contextResponseAsDict(progressAny); ok {
		templateContext.Set("progress", progress)
	} else if contextResponseIsNumber(progressAny) {
		progress = entities.NewOrderedMap[any]()
		progress.Set("completion_percentage", progressAny)
		templateContext.Set("progress", progress)
	} else {
		progress = entities.NewOrderedMap[any]()
		progress.Set("completion_percentage", int64(0))
		templateContext.Set("progress", progress)
	}

	if contextData.Has("insights") {
		notes := entities.NewOrderedMap[any]()
		notes.Set("agent_insights", contextResponseGet(contextData, "insights", nil))
		templateContext.Set("notes", notes)
	}
	if contextData.Has("next_steps") {
		progress, _ := contextResponseAsDict(contextResponseGet(templateContext, "progress", nil))
		progress.Set("next_steps", contextResponseGet(contextData, "next_steps", nil))
	}

	return templateContext
}

// contextResponseEnsureCompleteStructure mirrors
// ContextResponseFactory._ensure_complete_structure. It mutates and returns context. For a
// non-dict section the Python assignment raises and create_unified_context returns None.
func contextResponseEnsureCompleteStructure(context *entities.OrderedMap[any]) (result *entities.OrderedMap[any]) {
	defer func() {
		if recover() != nil {
			result = nil
		}
	}()
	defaultStructure := contextResponseDefaultStructure()
	for _, section := range defaultStructure.Keys() {
		defaultValues := contextResponseGet(defaultStructure, section, nil)
		if !context.Has(section) {
			context.Set(section, defaultValues)
			continue
		}
		defaultDict, ok := contextResponseAsDict(defaultValues)
		if !ok {
			continue
		}
		currentAny := contextResponseGet(context, section, nil)
		for _, subsection := range defaultDict.Keys() {
			// Python `subsection not in context[section]` (dict/str/list/other raises),
			// then item assignment, which only works on a dict.
			if contextResponsePyIn(currentAny, subsection) {
				continue
			}
			current, ok := contextResponseAsDict(currentAny)
			if !ok {
				panic("object does not support item assignment")
			}
			current.Set(subsection, contextResponseGet(defaultDict, subsection, nil))
		}
	}
	return context
}

// contextResponseDefaultStructure is the default_structure literal in
// _ensure_complete_structure, rebuilt fresh on each call.
func contextResponseDefaultStructure() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("metadata", entities.NewOrderedMap[any]())

	objective := entities.NewOrderedMap[any]()
	objective.Set("title", "")
	objective.Set("description", "")
	objective.Set("estimated_effort", "")
	objective.Set("due_date", nil)
	d.Set("objective", objective)

	requirements := entities.NewOrderedMap[any]()
	requirements.Set("checklist", []any{})
	requirements.Set("custom_requirements", []any{})
	requirements.Set("completion_criteria", []any{})
	d.Set("requirements", requirements)

	technical := entities.NewOrderedMap[any]()
	technical.Set("technologies", []any{})
	technical.Set("frameworks", []any{})
	technical.Set("database", "")
	technical.Set("key_files", []any{})
	technical.Set("key_directories", []any{})
	technical.Set("architecture_notes", "")
	technical.Set("patterns_used", []any{})
	d.Set("technical", technical)

	dependencies := entities.NewOrderedMap[any]()
	dependencies.Set("task_dependencies", []any{})
	dependencies.Set("external_dependencies", []any{})
	dependencies.Set("blocked_by", []any{})
	d.Set("dependencies", dependencies)

	progress := entities.NewOrderedMap[any]()
	progress.Set("completed_actions", []any{})
	progress.Set("current_session_summary", "")
	progress.Set("next_steps", []any{})
	progress.Set("completion_percentage", float64(0.0))
	progress.Set("time_spent_minutes", int64(0))
	d.Set("progress", progress)

	subtasks := entities.NewOrderedMap[any]()
	subtasks.Set("items", []any{})
	subtasks.Set("total_count", int64(0))
	subtasks.Set("completed_count", int64(0))
	subtasks.Set("progress_percentage", float64(0.0))
	d.Set("subtasks", subtasks)

	notes := entities.NewOrderedMap[any]()
	notes.Set("agent_insights", []any{})
	notes.Set("challenges_encountered", []any{})
	notes.Set("solutions_applied", []any{})
	notes.Set("decisions_made", []any{})
	notes.Set("general_notes", "")
	d.Set("notes", notes)

	d.Set("custom_sections", []any{})
	return d
}

// ContextResponseApplyToTaskResponse mirrors
// ContextResponseFactory.apply_to_task_response.
func ContextResponseApplyToTaskResponse(taskData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	taskID := contextResponseGet(taskData, "id", "")

	if !value_objects.PyTruthy(contextResponseGet(taskData, "context_data", nil)) && value_objects.PyTruthy(taskID) {
		if ContextResponseUnifiedFacadeProvider != nil {
			if facade := ContextResponseUnifiedFacadeProvider(); facade != nil {
				contextResponse := facade.GetContext("task", value_objects.PyStr(taskID), true)
				if value_objects.PyTruthy(contextResponseGet(contextResponse, "success", nil)) &&
					value_objects.PyTruthy(contextResponseGet(contextResponse, "context", nil)) {
					taskData.Set("context_data", contextResponseGet(contextResponse, "context", nil))
				}
			}
		}
	}

	if taskData.Has("context_data") && value_objects.PyTruthy(contextResponseGet(taskData, "context_data", nil)) {
		raw, _ := contextResponseAsDict(contextResponseGet(taskData, "context_data", nil))
		unified := ContextResponseCreateUnifiedContext(raw)
		taskData.Set("context_data", orderedAny(unified))
		taskData.Set("context_available", unified != nil)
	} else {
		taskData.Set("context_available", false)
	}
	return taskData
}

// orderedAny stores a nil *OrderedMap[any] as an untyped nil interface (Python None).
func orderedAny(m *entities.OrderedMap[any]) any {
	if m == nil {
		return nil
	}
	return m
}

// ContextResponseApplyToNextResponse mirrors
// ContextResponseFactory.apply_to_next_response.
func ContextResponseApplyToNextResponse(nextResponse *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if nextResponse.Has("task") {
		taskData, _ := contextResponseAsDict(contextResponseGet(nextResponse, "task", nil))
		if taskData != nil {
			var unified *entities.OrderedMap[any]
			if taskData.Has("context_info") {
				contextInfo, _ := contextResponseAsDict(contextResponseGet(taskData, "context_info", nil))
				unified = ContextResponseCreateUnifiedContext(contextInfo)

				taskData.Set("context_data", orderedAny(unified))
				taskData.Set("context_available", unified != nil)

				if unified != nil && unified.Has("metadata") &&
					contextResponsePyIn(contextResponseGet(unified, "metadata", nil), "task_id") {
					metadata, _ := contextResponseAsDict(contextResponseGet(unified, "metadata", nil))
					taskData.Set("context", contextResponseGet(metadata, "task_id", nil))
				} else if nextItem, ok := contextResponseAsDict(contextResponseGet(taskData, "next_item", nil)); ok &&
					contextResponsePyIn(nextItem, "task") {
					nestedTask, _ := contextResponseAsDict(contextResponseGet(nextItem, "task", nil))
					if nestedTask != nil && nestedTask.Has("context_id") {
						taskData.Set("context", contextResponseGet(nestedTask, "context_id", nil))
					}
				}

				taskData.Delete("context_info")
			}

			if nextItem, ok := contextResponseAsDict(contextResponseGet(taskData, "next_item", nil)); ok &&
				contextResponsePyIn(nextItem, "task") {
				nestedTask, _ := contextResponseAsDict(contextResponseGet(nextItem, "task", nil))
				if unified != nil && nestedTask != nil {
					nestedTask.Set("context_data", unified)
					nestedTask.Set("context_available", true)
				}
			}
		}
	}
	return nextResponse
}
