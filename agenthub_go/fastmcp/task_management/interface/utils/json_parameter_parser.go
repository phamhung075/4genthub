package utils

// JSON Parameter Parser Utility (Python interface/utils/json_parameter_parser.py).

import (
	"reflect"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// JSONParameterParser parses JSON strings to ordered dicts for MCP parameters.
type JSONParameterParser struct{}

// ParseDictParameter mirrors JSONParameterParser.parse_dict_parameter.
// paramValue is nil for None, a string, an *entities.OrderedMap[any], or a map.
func (JSONParameterParser) ParseDictParameter(paramValue any, paramName string) (*entities.OrderedMap[any], error) {
	if paramValue == nil {
		return nil, nil
	}

	switch v := paramValue.(type) {
	case *entities.OrderedMap[any]:
		return v, nil
	case map[string]any:
		om := entities.NewOrderedMap[any]()
		for k, val := range v {
			om.Set(k, val)
		}
		return om, nil
	case string:
		parsed, err := entities.DecodeJSON([]byte(v))
		if err != nil {
			return nil, &value_objects.ValueError{Msg: "Invalid JSON string in '" + paramName + "' parameter: " + err.Error() +
				". Valid formats: " + paramName + "={'key': 'value'} or " +
				paramName + "='{\"key\": \"value\"}'"}
		}
		om, ok := parsed.(*entities.OrderedMap[any])
		if !ok {
			return nil, &value_objects.ValueError{Msg: "Parameter '" + paramName + "' JSON must be an object, not " + pyTypeName(parsed)}
		}
		return om, nil
	default:
		return nil, &value_objects.ValueError{Msg: "Parameter '" + paramName + "' must be a dictionary object or JSON string, not " + pyTypeName(paramValue)}
	}
}

// ParseMultipleDictParameters mirrors parse_multiple_dict_parameters.
func (JSONParameterParser) ParseMultipleDictParameters(parameters *entities.OrderedMap[any], dictParamNames []string) (*entities.OrderedMap[any], error) {
	parsedParams := entities.NewOrderedMap[any]()
	for _, k := range parameters.KeysAny() {
		parsedParams.Set(k, parameters.GetAny(k))
	}

	for _, paramName := range dictParamNames {
		if parsedParams.Has(paramName) && parsedParams.GetAny(paramName) != nil {
			parsed, err := (JSONParameterParser{}).ParseDictParameter(parsedParams.GetAny(paramName), paramName)
			if err != nil {
				return nil, err
			}
			parsedParams.Set(paramName, parsed)
		}
	}

	return parsedParams, nil
}

// CreateErrorResponse mirrors create_error_response.
func (JSONParameterParser) CreateErrorResponse(paramName, errorMessage, toolName string) *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("error", errorMessage)
	d.Set("error_code", "INVALID_PARAMETER_FORMAT")
	d.Set("parameter", paramName)
	d.Set("suggestions", []any{
		"Use a dictionary object: " + paramName + "={'key': 'value', 'nested': {'item': 123}}",
		"Or use a JSON string: " + paramName + "='{\"key\": \"value\", \"nested\": {\"item\": 123}}'",
		"Ensure JSON is valid using a JSON validator",
	})
	examples := entities.NewOrderedMap[any]()
	examples.Set("dictionary_format", toolName+"(action='create', "+paramName+"={'title': 'My Title', 'data': {'key': 'value'}})")
	examples.Set("json_string_format", toolName+"(action='create', "+paramName+"='{\"title\": \"My Title\", \"data\": {\"key\": \"value\"}}')")
	d.Set("examples", examples)
	return d
}

// CommonDictParameters is COMMON_DICT_PARAMETERS.
var CommonDictParameters = []string{
	"data",
	"delegate_data",
	"filters",
	"data_metadata",
	"client_info",
	"dependency_data",
	"agent_config",
	"agent_metadata",
	"rule_data",
	"rule_config",
	"metadata",
	"config",
	"settings",
	"options",
	"params",
	"context",
	"payload",
}

// GetDictParametersForTool mirrors get_dict_parameters_for_tool.
func GetDictParametersForTool(toolName string) []string {
	toolSpecific := map[string][]string{
		"manage_context":    {"data", "delegate_data", "filters", "data_metadata"},
		"manage_connection": {"client_info"},
		"manage_dependency": {"dependency_data"},
		"manage_agent":      {"agent_config", "agent_metadata"},
		"manage_rule":       {"rule_data", "rule_config"},
	}
	if v, ok := toolSpecific[toolName]; ok {
		return v
	}
	return []string{"data", "metadata", "config"}
}

// pyTypeName mirrors type(v).__name__ for the JSON values DecodeJSON yields.
func pyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case string:
		return "str"
	case bool:
		return "bool"
	case int:
		return "int"
	case int64:
		return "int"
	case float64:
		return "float"
	case []any:
		return "list"
	case *entities.OrderedMap[any]:
		return "dict"
	default:
		t := reflect.TypeOf(v)
		if t == nil {
			return "NoneType"
		}
		return t.String()
	}
}
