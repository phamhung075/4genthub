package utils

// Python task_management/interface/utils/mcp_parameter_validator.py.
// MCPParameterValidator and the two quick integration functions.
// create_parameter_validation_decorator and example_mcp_controller_integration
// are Python decorator/print helpers with no Go meaning and are not ported.

import (
	"agenthub/fastmcp/task_management/domain/entities"
)

// MCPParameterValidator ports MCPParameterValidator.
type MCPParameterValidator struct{}

// ValidateAndCoerceMCPParameters ports validate_and_coerce_mcp_parameters. A
// Python exception return value cannot be produced by Go coercion (which
// reports *ParameterTypeCoercionError through the result dict), so the
// except-branch shape is kept for completeness of the contract.
func (MCPParameterValidator) ValidateAndCoerceMCPParameters(action string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	coercedParams := CoerceParameterTypes(params)
	validationResult := ValidateParameters(action, coercedParams)

	successAny, _ := validationResult.Get("success")
	if b, ok := successAny.(bool); ok && b {
		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		cp, _ := validationResult.Get("coerced_params")
		out.Set("coerced_params", cp)
		out.Set("action", action)
		out.Set("validation_notes", "Parameters validated and coerced successfully")
		return out
	}
	return validationResult
}

// ValidateMCPParameters ports validate_mcp_parameters.
func ValidateMCPParameters(action string, params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return MCPParameterValidator{}.ValidateAndCoerceMCPParameters(action, params)
}

// CoerceMCPParameters ports coerce_mcp_parameters.
func CoerceMCPParameters(params *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return CoerceParameterTypes(params)
}
