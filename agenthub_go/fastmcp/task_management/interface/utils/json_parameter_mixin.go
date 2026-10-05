package utils

// JSON Parameter Mixin for MCP Controllers (Python interface/utils/json_parameter_mixin.py).

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// StandardResponseFormatter is the minimal surface the mixin needs from
// interface/utils/response_formatter.py (no Go port yet).
type StandardResponseFormatter interface {
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
}

// JSONParameterMixin adds JSON parameter parsing to MCP controllers.
type JSONParameterMixin struct {
	Formatter StandardResponseFormatter
}

// ParseJSONParameters mirrors parse_json_parameters.
func (m JSONParameterMixin) ParseJSONParameters(parameters *entities.OrderedMap[any], toolName *string, customDictParams []string) (*entities.OrderedMap[any], error) {
	var dictParamNames []string
	if len(customDictParams) > 0 {
		dictParamNames = customDictParams
	} else if toolName != nil {
		dictParamNames = GetDictParametersForTool(*toolName)
	} else {
		dictParamNames = []string{"data", "metadata", "config", "filters"}
	}

	return (JSONParameterParser{}).ParseMultipleDictParameters(parameters, dictParamNames)
}

// CreateJSONErrorResponse mirrors create_json_error_response.
func (m JSONParameterMixin) CreateJSONErrorResponse(err error, operation, toolName string) *entities.OrderedMap[any] {
	errorStr := err.Error()

	paramName := "parameter"
	if strings.Contains(errorStr, "'") {
		parts := strings.Split(errorStr, "'")
		if len(parts) >= 2 {
			paramName = parts[1]
		}
	}

	errorMetadata := (JSONParameterParser{}).CreateErrorResponse(paramName, errorStr, toolName)
	return m.Formatter.CreateErrorResponse(operation, errorStr, "INVALID_PARAMETER_FORMAT", errorMetadata)
}

// SafeParseDictParameter mirrors safe_parse_dict_parameter.
func (m JSONParameterMixin) SafeParseDictParameter(paramValue any, paramName string, defaultValue *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if paramValue == nil {
		return defaultValue
	}
	parsed, err := (JSONParameterParser{}).ParseDictParameter(paramValue, paramName)
	if err != nil {
		return defaultValue
	}
	return parsed
}
