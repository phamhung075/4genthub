package utils

// Python task_management/interface/utils/parameter_validation_fix.py.
// ParameterTypeCoercionError, ParameterTypeCoercer, FlexibleSchemaValidator,
// EnhancedParameterValidator and the module-level convenience functions.

import (
	"sort"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ParameterTypeCoercionError mirrors ParameterTypeCoercionError. Parameter and
// ExpectedType are `any` because the Python defaults are None.
type ParameterTypeCoercionError struct {
	Msg          string
	Parameter    any
	Value        any
	ExpectedType any
}

func (e *ParameterTypeCoercionError) Error() string { return e.Msg }

// ParameterTypeCoercerINTEGERParameters ports INTEGER_PARAMETERS.
var ParameterTypeCoercerINTEGERParameters = map[string]bool{
	"limit": true, "progress_percentage": true, "timeout": true, "port": true,
	"offset": true, "head_limit": true, "max_results": true, "page_size": true,
	"retry_count": true, "depth": true, "max_depth": true, "count": true,
	"size": true, "length": true,
}

// ParameterTypeCoercerBOOLEANParameters ports BOOLEAN_PARAMETERS.
var ParameterTypeCoercerBOOLEANParameters = map[string]bool{
	"include_context": true, "force": true, "audit_required": true,
	"include_details": true, "propagate_changes": true, "include_inherited": true,
	"force_refresh": true, "recursive": true, "enabled": true, "active": true,
	"visible": true, "public": true, "strict": true, "validate": true,
	"auto_create": true, "cascade": true,
}

// ParameterTypeCoercerTRUEValues ports TRUE_VALUES.
var ParameterTypeCoercerTRUEValues = map[string]bool{
	"true": true, "1": true, "yes": true, "on": true, "enabled": true,
	"active": true, "y": true, "t": true,
}

// ParameterTypeCoercerFALSEValues ports FALSE_VALUES.
var ParameterTypeCoercerFALSEValues = map[string]bool{
	"false": true, "0": true, "no": true, "off": true, "disabled": true,
	"inactive": true, "n": true, "f": true,
}

// ParameterTypeCoercer ports ParameterTypeCoercer.
type ParameterTypeCoercer struct{}

// CoerceToInt ports coerce_to_int. The result is `any` because Python returns an
// int unchanged, and bool is an int subclass in Python.
func (ParameterTypeCoercer) CoerceToInt(value any, parameterName string) (any, *ParameterTypeCoercionError) {
	switch v := value.(type) {
	case int:
		return v, nil
	case int64:
		return v, nil
	case bool:
		return v, nil
	}

	if s, ok := value.(string); ok {
		s = strings.TrimSpace(s)
		if s == "" {
			return nil, &ParameterTypeCoercionError{
				Msg:          "Parameter '" + parameterName + "' cannot be empty string when expecting integer",
				Parameter:    parameterName,
				Value:        s,
				ExpectedType: "integer",
			}
		}
		n, err := strconv.Atoi(s)
		if err != nil {
			return nil, &ParameterTypeCoercionError{
				Msg:          "Parameter '" + parameterName + "' value '" + s + "' cannot be converted to integer",
				Parameter:    parameterName,
				Value:        s,
				ExpectedType: "integer",
			}
		}
		return n, nil
	}

	// Direct conversion for other types (Python int(value)).
	switch v := value.(type) {
	case float64:
		return int(v), nil
	case float32:
		return int(v), nil
	}
	return nil, &ParameterTypeCoercionError{
		Msg: "Parameter '" + parameterName + "' value '" + pyString(value) +
			"' (type: " + pyTypeName(value) + ") cannot be converted to integer",
		Parameter:    parameterName,
		Value:        value,
		ExpectedType: "integer",
	}
}

// CoerceToBool ports coerce_to_bool.
func (ParameterTypeCoercer) CoerceToBool(value any, parameterName string) (bool, *ParameterTypeCoercionError) {
	if b, ok := value.(bool); ok {
		return b, nil
	}
	if s, ok := value.(string); ok {
		normalized := strings.ToLower(strings.TrimSpace(s))
		if ParameterTypeCoercerTRUEValues[normalized] {
			return true, nil
		}
		if ParameterTypeCoercerFALSEValues[normalized] {
			return false, nil
		}
		validValues := sortedUnionKeys(ParameterTypeCoercerTRUEValues, ParameterTypeCoercerFALSEValues)
		return false, &ParameterTypeCoercionError{
			Msg: "Parameter '" + parameterName + "' value '" + s + "' is not a valid boolean string. " +
				"Valid values: " + strings.Join(validValues, ", "),
			Parameter:    parameterName,
			Value:        s,
			ExpectedType: "boolean",
		}
	}
	return value_objects.PyTruthy(value), nil
}

// CoerceParameter ports coerce_parameter.
func (c ParameterTypeCoercer) CoerceParameter(key string, value any) (any, error) {
	if value == nil {
		return value, nil
	}
	if ParameterTypeCoercerINTEGERParameters[key] {
		v, err := c.CoerceToInt(value, key)
		if err != nil {
			return nil, err
		}
		return v, nil
	} else if ParameterTypeCoercerBOOLEANParameters[key] {
		v, err := c.CoerceToBool(value, key)
		if err != nil {
			return nil, err
		}
		return v, nil
	}
	return value, nil
}

// CoerceParameterTypes is the classmethod coerce_parameter_types.
func (ParameterTypeCoercer) CoerceParameterTypes(params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return ParameterTypeCoercer{}.CoerceParameters(params)
}

// CoerceParameters ports coerce_parameters.
func (c ParameterTypeCoercer) CoerceParameters(params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if params == nil || params.Len() == 0 {
		return params
	}
	coerced := entities.NewOrderedMap[any]()
	for _, key := range params.Keys() {
		value, _ := params.Get(key)
		v, err := c.CoerceParameter(key, value)
		if err != nil {
			// ParameterTypeCoercionError re-raised as-is; unexpected errors keep
			// the original value.
			if _, ok := err.(*ParameterTypeCoercionError); ok {
				return nil
			}
			coerced.Set(key, value)
			continue
		}
		coerced.Set(key, v)
	}
	return coerced
}

// FlexibleSchemaValidator ports FlexibleSchemaValidator.
type FlexibleSchemaValidator struct {
	Coercer ParameterTypeCoercer
}

// NewFlexibleSchemaValidator mirrors __init__(coercer=None).
func NewFlexibleSchemaValidator(coercer *ParameterTypeCoercer) *FlexibleSchemaValidator {
	v := FlexibleSchemaValidator{}
	if coercer != nil {
		v.Coercer = *coercer
	}
	return &v
}

// CreateFlexibleSchema ports create_flexible_schema. The Python shallow copy
// shares the nested "properties" dict, so mutating the copy also mutates the
// original schema; that quirk is preserved.
func (v *FlexibleSchemaValidator) CreateFlexibleSchema(originalSchema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	flexibleSchema := pvfixShallowCopy(originalSchema)
	propsAny, ok := flexibleSchema.Get("properties")
	if !ok {
		return flexibleSchema
	}
	props, ok := propsAny.(*entities.OrderedMap[any])
	if !ok {
		return flexibleSchema
	}
	for _, propName := range props.Keys() {
		propSchema, _ := props.Get(propName)
		ps, ok := propSchema.(*entities.OrderedMap[any])
		if !ok {
			continue
		}
		typ, _ := ps.Get("type")
		switch typ {
		case "integer":
			newProp := entities.NewOrderedMap[any]()
			newProp.Set("anyOf", []any{
				pvfixOrdered("type", "integer"),
				pvfixOrdered("type", "string", "pattern", `^-?\d+$`),
			})
			props.Set(propName, newProp)
		case "boolean":
			newProp := entities.NewOrderedMap[any]()
			enumProp := entities.NewOrderedMap[any]()
			enumProp.Set("type", "string")
			enumProp.Set("enum", sortedUnionKeys(ParameterTypeCoercerTRUEValues, ParameterTypeCoercerFALSEValues))
			newProp.Set("anyOf", []any{
				pvfixOrdered("type", "boolean"),
				enumProp,
			})
			props.Set(propName, newProp)
		}
	}
	return flexibleSchema
}

// EnhancedParameterValidator ports EnhancedParameterValidator.
type EnhancedParameterValidator struct {
	Coercer         ParameterTypeCoercer
	SchemaValidator *FlexibleSchemaValidator
}

// NewEnhancedParameterValidator ports __init__.
func NewEnhancedParameterValidator() *EnhancedParameterValidator {
	v := &EnhancedParameterValidator{}
	v.SchemaValidator = NewFlexibleSchemaValidator(&v.Coercer)
	return v
}

// ValidateParameters ports validate_parameters.
func (v *EnhancedParameterValidator) ValidateParameters(action string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	coercedParams := v.Coercer.CoerceParameters(params)
	if coercedParams == nil && params != nil && params.Len() > 0 {
		// Coercion raised ParameterTypeCoercionError; recompute it to expose the
		// structured error fields (order: success, error, error_code, parameter,
		// provided_value, expected_type, hint).
		for _, key := range params.Keys() {
			value, _ := params.Get(key)
			_, err := v.Coercer.CoerceParameter(key, value)
			if err != nil {
				if ce, ok := err.(*ParameterTypeCoercionError); ok {
					out := entities.NewOrderedMap[any]()
					out.Set("success", false)
					out.Set("error", ce.Msg)
					out.Set("error_code", "PARAMETER_COERCION_ERROR")
					out.Set("parameter", ce.Parameter)
					out.Set("provided_value", value_objects.PyStr(ce.Value))
					out.Set("expected_type", ce.ExpectedType)
					out.Set("hint", "Check parameter format. Numeric parameters can be provided as strings or integers.")
					return out
				}
			}
		}
	}

	validationResult := entities.NewOrderedMap[any]()
	validationResult.Set("success", true)
	validationResult.Set("action", action)
	validationResult.Set("original_params", params)
	validationResult.Set("coerced_params", coercedParams)
	validationResult.Set("coercion_applied", !orderedMapEqual(coercedParams, params))
	return validationResult
}

var defaultParameterCoercer = ParameterTypeCoercer{}
var defaultEnhancedValidator = NewEnhancedParameterValidator()

// CoerceParameterTypes is the public coerce_parameter_types.
func CoerceParameterTypes(params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return defaultParameterCoercer.CoerceParameters(params)
}

// ValidateParameters is the public validate_parameters.
func ValidateParameters(action string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return defaultEnhancedValidator.ValidateParameters(action, params)
}

// CreateFlexibleSchema is the public create_flexible_schema.
func CreateFlexibleSchema(originalSchema *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return defaultEnhancedValidator.SchemaValidator.CreateFlexibleSchema(originalSchema)
}

// --- helpers (uniquely named to avoid cross-file collisions) ---

func pvfixShallowCopy(src *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	dst := entities.NewOrderedMap[any]()
	if src == nil {
		return dst
	}
	for _, k := range src.Keys() {
		v, _ := src.Get(k)
		dst.Set(k, v)
	}
	return dst
}

func pvfixOrdered(kv ...string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i], kv[i+1])
	}
	return m
}

func sortedUnionKeys(a, b map[string]bool) []string {
	seen := map[string]bool{}
	var out []string
	for k := range a {
		if !seen[k] {
			seen[k] = true
			out = append(out, k)
		}
	}
	for k := range b {
		if !seen[k] {
			seen[k] = true
			out = append(out, k)
		}
	}
	sort.Strings(out)
	return out
}

func orderedMapEqual(a, b *entities.OrderedMap[any]) bool {
	if a == nil || b == nil {
		return a == b
	}
	if a.Len() != b.Len() {
		return false
	}
	for _, k := range a.Keys() {
		av, ok := a.Get(k)
		if !ok {
			return false
		}
		bv, ok := b.Get(k)
		if !ok || !pvfixDeepEqual(av, bv) {
			return false
		}
	}
	return true
}

func pvfixDeepEqual(a, b any) bool {
	am, aok := a.(*entities.OrderedMap[any])
	bm, bok := b.(*entities.OrderedMap[any])
	if aok && bok {
		return orderedMapEqual(am, bm)
	}
	return a == b
}
