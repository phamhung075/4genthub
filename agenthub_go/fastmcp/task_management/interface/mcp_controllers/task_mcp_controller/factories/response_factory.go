package factories

// Response Factory for Task MCP Controller (Python response_factory.py).

import (
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// pyJoin mirrors ", ".join(list).
func pyJoin(items []string, sep string) string { return strings.Join(items, sep) }

// ErrorCodes constants from interface/utils/response_formatter.py ErrorCodes.
const (
	ErrorCodeValidation            = "VALIDATION_ERROR"
	ErrorCodeOperationFailed       = "OPERATION_FAILED"
	ErrorCodeBusinessRuleViolation = "BUSINESS_RULE_VIOLATION"
	ErrorCodeInternalError         = "INTERNAL_ERROR"
	ErrorCodeUnknownError          = "UNKNOWN_ERROR"
)

// ResponseFormatter is the minimal view of the interface-layer
// StandardResponseFormatter (task_management/interface/utils/response_formatter.py)
// used by the task factories and handlers. That module has no Go port yet; the
// interface is declared here and reported as a dependency.
type ResponseFormatter interface {
	CreateSuccessResponse(operation string, data any, workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any]
	CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetTimestamp() string
}

// ResponseFactory ports ResponseFactory.
type ResponseFactory struct {
	responseFormatter ResponseFormatter
}

// NewResponseFactory ports __init__(response_formatter).
func NewResponseFactory(responseFormatter ResponseFormatter) *ResponseFactory {
	return &ResponseFactory{responseFormatter: responseFormatter}
}

// CreateSuccessResponse ports create_success_response.
func (f *ResponseFactory) CreateSuccessResponse(operation string, data any,
	workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return f.responseFormatter.CreateSuccessResponse(operation, data, workflowGuidance)
}

// CreateErrorResponse ports create_error_response. errorCode defaults to
// ErrorCodes.OPERATION_FAILED.
func (f *ResponseFactory) CreateErrorResponse(operation, errorMessage string,
	errorCode *string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	code := ErrorCodeOperationFailed
	if errorCode != nil {
		code = *errorCode
	}
	return f.responseFormatter.CreateErrorResponse(operation, errorMessage, code, metadata)
}

// StandardizeFacadeResponse ports standardize_facade_response.
func (f *ResponseFactory) StandardizeFacadeResponse(facadeResponse *entities.OrderedMap[any],
	operation string) *entities.OrderedMap[any] {
	successVal, _ := facadeResponse.Get("success")
	if value_objects.PyTruthy(successVal) {
		data := entities.NewOrderedMap[any]()
		for _, key := range facadeResponse.Keys() {
			if key == "success" || key == "action" || key == "error" || key == "error_code" {
				continue
			}
			v, _ := facadeResponse.Get(key)
			data.Set(key, v)
		}

		var workflowGuidance *entities.OrderedMap[any]
		if v, ok := data.Get("workflow_guidance"); ok {
			if m, isMap := v.(*entities.OrderedMap[any]); isMap {
				workflowGuidance = m
			} else if v != nil {
				workflowGuidance = entities.NewOrderedMap[any]()
			}
			data.Delete("workflow_guidance")
		}

		return f.CreateSuccessResponse(operation, data, workflowGuidance)
	}

	// A facade answers with the reason as a flat string; the handler layer answers
	// through the interface formatter, which writes it into an error map
	// ({message, code, ...}). Reading only the string form dropped every reason the
	// formatter produced - the five AI refusals among them - and answered
	// "Unknown error occurred" instead.
	errorMessage := "Unknown error occurred"
	errorCode := ErrorCodeOperationFailed
	if v, ok := facadeResponse.Get("error"); ok && v != nil {
		switch typed := v.(type) {
		case string:
			errorMessage = typed
		case *entities.OrderedMap[any]:
			if m, ok := typed.Get("message"); ok && m != nil {
				errorMessage = value_objects.PyStr(m)
			}
			if c, ok := typed.Get("code"); ok && c != nil {
				if s, isStr := c.(string); isStr {
					errorCode = s
				}
			}
		}
	}
	if v, ok := facadeResponse.Get("error_code"); ok && v != nil {
		if s, isStr := v.(string); isStr {
			errorCode = s
		}
	}

	metadata := entities.NewOrderedMap[any]()
	for _, key := range facadeResponse.Keys() {
		if key == "success" || key == "action" || key == "error" || key == "error_code" {
			continue
		}
		v, _ := facadeResponse.Get(key)
		metadata.Set(key, v)
	}
	var metadataPtr *entities.OrderedMap[any]
	if metadata.Len() > 0 {
		metadataPtr = metadata
	}
	code := errorCode
	return f.CreateErrorResponse(operation, errorMessage, &code, metadataPtr)
}

// EnrichResponseWithMetadata ports enrich_response_with_metadata.
func (f *ResponseFactory) EnrichResponseWithMetadata(response *entities.OrderedMap[any],
	metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	enriched := response.Copy()
	if existing, ok := enriched.Get("metadata"); ok {
		if m, isMap := existing.(*entities.OrderedMap[any]); isMap {
			for _, k := range metadata.Keys() {
				v, _ := metadata.Get(k)
				m.Set(k, v)
			}
			return enriched
		}
	}
	enriched.Set("metadata", metadata)
	return enriched
}

// AddPaginationMetadata ports add_pagination_metadata.
func (f *ResponseFactory) AddPaginationMetadata(response *entities.OrderedMap[any],
	total, limit, offset int) *entities.OrderedMap[any] {
	pagination := entities.NewOrderedMap[any]()
	pagination.Set("total", total)
	pagination.Set("limit", limit)
	pagination.Set("offset", offset)
	pagination.Set("has_more", total > offset+limit)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("pagination", pagination)
	return f.EnrichResponseWithMetadata(response, metadata)
}

// AddOperationMetadata ports add_operation_metadata.
func (f *ResponseFactory) AddOperationMetadata(response *entities.OrderedMap[any],
	operation string, timestamp *string) *entities.OrderedMap[any] {
	ts := f.responseFormatter.GetTimestamp()
	if timestamp != nil {
		ts = *timestamp
	}
	operationInfo := entities.NewOrderedMap[any]()
	operationInfo.Set("operation", operation)
	operationInfo.Set("timestamp", ts)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("operation_info", operationInfo)
	return f.EnrichResponseWithMetadata(response, metadata)
}

// CreateValidationErrorResponse ports create_validation_error_response.
func (f *ResponseFactory) CreateValidationErrorResponse(field, expected, hint string,
	operation *string) *entities.OrderedMap[any] {
	op := "validation"
	if operation != nil {
		op = *operation
	}
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("field", field)
	metadata.Set("hint", hint)
	code := ErrorCodeValidation
	return f.CreateErrorResponse(op, "Invalid field: "+field+". Expected: "+expected, &code, metadata)
}

// CreateBusinessRuleErrorResponse ports create_business_rule_error_response.
func (f *ResponseFactory) CreateBusinessRuleErrorResponse(ruleName, message, hint string,
	operation *string) *entities.OrderedMap[any] {
	op := "business_validation"
	if operation != nil {
		op = *operation
	}
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("rule", ruleName)
	metadata.Set("hint", hint)
	code := ErrorCodeBusinessRuleViolation
	return f.CreateErrorResponse(op, "Business rule violation ("+ruleName+"): "+message, &code, metadata)
}

// CreateMissingFieldError ports create_missing_field_error(field, action).
func (f *ResponseFactory) CreateMissingFieldError(field, action string) *entities.OrderedMap[any] {
	response := entities.NewOrderedMap[any]()
	response.Set("status", "failure")

	errObj := entities.NewOrderedMap[any]()
	errObj.Set("message", "Validation failed for field: "+field)
	errObj.Set("code", "VALIDATION_ERROR")
	response.Set("error", errObj)

	response.Set("operation", action)

	validationDetails := entities.NewOrderedMap[any]()
	validationDetails.Set("field", field)
	validationDetails.Set("expected", "A valid "+field+" value")
	validationDetails.Set("hint", "Include '"+field+"' in your request for action '"+action+"'")
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("validation_details", validationDetails)
	response.Set("metadata", metadata)
	return response
}

// CreateInvalidActionError ports create_invalid_action_error.
func (f *ResponseFactory) CreateInvalidActionError(invalidAction string,
	validActions []string) *entities.OrderedMap[any] {
	if validActions == nil {
		validActions = []string{
			"create",
			"update",
			"get",
			"delete",
			"complete",
			"list",
			"search",
			"next",
			"add_dependency",
			"remove_dependency",
			"ai_plan",
			"ai_create",
			"ai_enhance",
			"ai_analyze",
			"ai_suggest_agents",
		}
	}

	response := entities.NewOrderedMap[any]()
	response.Set("status", "failure")

	errObj := entities.NewOrderedMap[any]()
	errObj.Set("message", "Validation failed for field: action")
	errObj.Set("code", "VALIDATION_ERROR")
	response.Set("error", errObj)

	response.Set("operation", "unknown_action")

	validationDetails := entities.NewOrderedMap[any]()
	validationDetails.Set("field", "action")
	validationDetails.Set("expected", "One of: "+pyJoin(validActions, ", "))
	validationDetails.Set("hint", "Invalid action: "+invalidAction+". Use one of the supported actions.")
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("validation_details", validationDetails)
	response.Set("metadata", metadata)
	return response
}
