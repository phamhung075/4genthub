package services

import (
	"math"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ParameterTransformationService transforms and validates MCP controller parameters
// (Python application/services/parameter_transformation_service.py). The Python
// methods are @staticmethod; the value-receiver methods mirror their names.
type ParameterTransformationService struct{}

// TransformStringToList transforms a string parameter to a list: None -> nil, a Go
// []any -> as-is, a string is stripped ("", nil; comma-separated split dropping empty
// items; otherwise a single-element list), any other type -> nil.
func (ParameterTransformationService) TransformStringToList(value any, fieldName string) []any {
	if value == nil {
		return nil
	}

	if list, ok := value.([]any); ok {
		return list
	}

	if text, ok := value.(string); ok {
		text = value_objects.PyStrip(text)
		if text == "" {
			return nil
		}
		if strings.Contains(text, ",") {
			result := []any{}
			for _, item := range strings.Split(text, ",") {
				item = value_objects.PyStrip(item)
				if item != "" {
					result = append(result, item)
				}
			}
			return result
		}
		return []any{text}
	}

	return nil
}

// TransformToInteger mirrors int(value) with a fallback to default: None -> default,
// bool (an int subclass) -> 1/0, ints -> themselves, floats truncated toward zero,
// strings parsed with Python int() semantics, anything else -> default.
func (ParameterTransformationService) TransformToInteger(value any, defaultValue int, fieldName string) int {
	if value == nil {
		return defaultValue
	}

	switch v := value.(type) {
	case bool:
		if v {
			return 1
		}
		return 0
	case int:
		return v
	case int8:
		return int(v)
	case int16:
		return int(v)
	case int32:
		return int(v)
	case int64:
		return int(v)
	case uint:
		return int(v)
	case uint8:
		return int(v)
	case uint16:
		return int(v)
	case uint32:
		return int(v)
	case uint64:
		return int(v)
	case float32:
		return zpAParameterFloatToInt(float64(v), defaultValue)
	case float64:
		return zpAParameterFloatToInt(v, defaultValue)
	case string:
		parsed, ok := value_objects.PyParseInt(v)
		if !ok {
			return defaultValue
		}
		return int(parsed.Int64())
	}

	return defaultValue
}

// ValidateProgressPercentage delegates to the domain ProgressPercentage value object.
// None -> (nil, nil); valid -> (int, nil); invalid -> (nil, error message).
func (ParameterTransformationService) ValidateProgressPercentage(value any) (*int, *string) {
	if value == nil {
		return nil, nil
	}

	progress, err := value_objects.ProgressPercentageFromAny(value)
	if err != nil {
		errorMsg := "progress_percentage must be an integer between 0 and 100: " + err.Error()
		return nil, &errorMsg
	}

	result := progress.ToInt()
	return &result, nil
}

// TransformBooleanDefault returns default for None, otherwise the boolean value.
func (ParameterTransformationService) TransformBooleanDefault(value *bool, defaultValue bool) bool {
	if value == nil {
		return defaultValue
	}
	return *value
}

// TransformMultipleFields transforms the present fields of kwargs according to
// field_configs (type list/integer/percentage/boolean) and returns a copy.
func (s ParameterTransformationService) TransformMultipleFields(kwargs *entities.OrderedMap[any], fieldConfigs *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	var result *entities.OrderedMap[any]
	if kwargs == nil {
		result = entities.NewOrderedMap[any]()
	} else {
		result = kwargs.Copy()
	}
	if fieldConfigs == nil {
		return result
	}

	for _, fieldName := range fieldConfigs.Keys() {
		if !result.Has(fieldName) {
			continue
		}
		config, _ := fieldConfigs.Get(fieldName)
		fieldType, _ := zpAParameterMapString(config, "type")
		fieldValue, _ := result.Get(fieldName)

		switch fieldType {
		case "list":
			list := s.TransformStringToList(fieldValue, fieldName)
			if list == nil {
				result.Set(fieldName, nil)
			} else {
				result.Set(fieldName, list)
			}
		case "integer":
			defaultValue := zpAParameterMapIntDefault(config, "default", 0)
			result.Set(fieldName, s.TransformToInteger(fieldValue, defaultValue, fieldName))
		case "percentage":
			transformed, errorMsg := s.ValidateProgressPercentage(fieldValue)
			if errorMsg != nil {
				result.Set(fieldName, nil)
				result.Set(fieldName+"_error", *errorMsg)
			} else if transformed == nil {
				result.Set(fieldName, nil)
			} else {
				result.Set(fieldName, *transformed)
			}
		case "boolean":
			defaultValue := zpAParameterMapBoolDefault(config, "default", false)
			result.Set(fieldName, s.TransformBooleanDefault(zpAParameterBoolPtr(fieldValue), defaultValue))
		}
	}

	return result
}

// zpAParameterFloatToInt truncates a float like int() and falls back to default for
// NaN/Inf, which raise ValueError in Python.
func zpAParameterFloatToInt(value float64, fallback int) int {
	if math.IsNaN(value) || math.IsInf(value, 0) {
		return fallback
	}
	return int(math.Trunc(value))
}

// zpAParameterMapGet looks a key up in a Python-dict-like value.
func zpAParameterMapGet(m any, key string) (any, bool) {
	switch d := m.(type) {
	case *entities.OrderedMap[any]:
		if d == nil {
			return nil, false
		}
		return d.Get(key)
	case map[string]any:
		v, ok := d[key]
		return v, ok
	}
	return nil, false
}

// zpAParameterMapString reads a string config value.
func zpAParameterMapString(m any, key string) (string, bool) {
	value, ok := zpAParameterMapGet(m, key)
	if !ok {
		return "", false
	}
	text, ok := value.(string)
	return text, ok
}

// zpAParameterMapIntDefault reads an integer config default (config.get("default", 0)).
func zpAParameterMapIntDefault(m any, key string, fallback int) int {
	value, ok := zpAParameterMapGet(m, key)
	if !ok || value == nil {
		return fallback
	}
	switch v := value.(type) {
	case bool:
		if v {
			return 1
		}
		return 0
	case int:
		return v
	case int8:
		return int(v)
	case int16:
		return int(v)
	case int32:
		return int(v)
	case int64:
		return int(v)
	case uint:
		return int(v)
	case uint8:
		return int(v)
	case uint16:
		return int(v)
	case uint32:
		return int(v)
	case uint64:
		return int(v)
	case float32:
		return zpAParameterFloatToInt(float64(v), fallback)
	case float64:
		return zpAParameterFloatToInt(v, fallback)
	}
	return fallback
}

// zpAParameterMapBoolDefault reads a boolean config default (config.get("default", False)).
func zpAParameterMapBoolDefault(m any, key string, fallback bool) bool {
	value, ok := zpAParameterMapGet(m, key)
	if !ok || value == nil {
		return fallback
	}
	if b, ok := value.(bool); ok {
		return b
	}
	return fallback
}

// zpAParameterBoolPtr converts an optional Python bool to a *bool (nil = None).
func zpAParameterBoolPtr(value any) *bool {
	if value == nil {
		return nil
	}
	if b, ok := value.(bool); ok {
		return &b
	}
	return nil
}
