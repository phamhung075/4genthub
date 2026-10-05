package workflow_guidance

// Base workflow guidance interface
// (Python workflow_guidance/base.py).

import (
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// WorkflowGuidanceInterface ports WorkflowGuidanceInterface(ABC). The Python
// abstract methods are declared as an interface; nothing in the ported set
// implements it (each guidance type exposes GenerateGuidance directly).
type WorkflowGuidanceInterface interface {
	EnhanceResponse(response *entities.OrderedMap[any], action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any]
	AnalyzeState(response *entities.OrderedMap[any], context *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetRules(action string, response *entities.OrderedMap[any]) []string
	SuggestNextActions(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []any
	GenerateHints(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []string
	CheckWarnings(action string, response *entities.OrderedMap[any], context *entities.OrderedMap[any]) []string
	GetExamples(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetParameterGuidance(action string) *entities.OrderedMap[any]
}

// BaseWorkflowGuidance ports BaseWorkflowGuidance. Its methods are the
// overridable defaults subclasses replace.
type BaseWorkflowGuidance struct{}

// ContextGet mirrors `context.get(key) if context else None`.
func ContextGet(context *entities.OrderedMap[any], key string) any {
	if context == nil || !bool(pyTruthyMap(context)) {
		return nil
	}
	v, _ := context.Get(key)
	return v
}

// ContextGetDefault mirrors `context.get(key, default) if context else default`.
func ContextGetDefault(context *entities.OrderedMap[any], key string, def any) any {
	if context == nil {
		return def
	}
	if v, ok := context.Get(key); ok {
		return v
	}
	return def
}

// ContextGetStringDefault mirrors `context.get(key, default) if context else default`
// for the string-valued cases used by the guidance builders.
func ContextGetStringDefault(context *entities.OrderedMap[any], key string, def string) string {
	if context == nil {
		return def
	}
	if v, ok := context.Get(key); ok {
		return toString(v)
	}
	return def
}

func pyTruthyMap(o *entities.OrderedMap[any]) bool { return o.Len() > 0 }

func toString(v any) string {
	return value_objects.PyStr(v)
}

// OrValue mirrors Python's `value or default`: returns value when truthy, else
// the string default.
func OrValue(v any, def string) any {
	if value_objects.PyTruthy(v) {
		return v
	}
	return def
}

// OrString mirrors Python's `value or default` for a value interpolated into a
// string (f-string / code example).
func OrString(v any, def string) string {
	if value_objects.PyTruthy(v) {
		return value_objects.PyStr(v)
	}
	return def
}

// GenerateGuidance ports BaseWorkflowGuidance.generate_guidance.
func (BaseWorkflowGuidance) GenerateGuidance(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if context == nil {
		context = entities.NewOrderedMap[any]()
	}
	out := entities.NewOrderedMap[any]()
	out.Set("current_state", BaseDetermineState(action, context))
	out.Set("rules", []any{})
	out.Set("next_actions", []any{})
	out.Set("hints", []any{})
	out.Set("warnings", []any{})
	out.Set("examples", entities.NewOrderedMap[any]())
	out.Set("parameter_guidance", BaseParameterGuidance(action))
	return out
}

// BaseDetermineState ports BaseWorkflowGuidance._determine_state.
func BaseDetermineState(action string, context *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("phase", "operation")
	out.Set("action", action)
	return out
}

// BaseParameterGuidance ports BaseWorkflowGuidance._get_parameter_guidance.
func BaseParameterGuidance(action string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("applicable_parameters", []any{})
	out.Set("parameter_tips", entities.NewOrderedMap[any]())
	return out
}
