package utils

// Python task_management/interface/utils/response_formatter.py.
// ResponseStatus, the standardized response formatter and ErrorCodes.

import (
	"crypto/rand"
	"fmt"
	"os"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ResponseStatus ports the ResponseStatus enum.
type ResponseStatus string

const (
	ResponseStatusSuccess        ResponseStatus = "success"
	ResponseStatusPartialSuccess ResponseStatus = "partial_success"
	ResponseStatusFailure        ResponseStatus = "failure"
)

// ErrorCodes ports the ErrorCodes class constants.
const (
	ErrorCodesMissingField        = "MISSING_FIELD"
	ErrorCodesInvalidFormat       = "INVALID_FORMAT"
	ErrorCodesValidationError     = "VALIDATION_ERROR"
	ErrorCodesNotFound            = "NOT_FOUND"
	ErrorCodesResourceNotFound    = "RESOURCE_NOT_FOUND"
	ErrorCodesInvalidOperation    = "INVALID_OPERATION"
	ErrorCodesAlreadyExists       = "ALREADY_EXISTS"
	ErrorCodesOperationFailed     = "OPERATION_FAILED"
	ErrorCodesUnauthorized        = "UNAUTHORIZED"
	ErrorCodesInternalError       = "INTERNAL_ERROR"
	ErrorCodesDatabaseError       = "DATABASE_ERROR"
	ErrorCodesContextError        = "CONTEXT_ERROR"
	ErrorCodesInvalidState        = "INVALID_STATE"
	ErrorCodesDependencyError     = "DEPENDENCY_ERROR"
	ErrorCodesConstraintViolation = "CONSTRAINT_VIOLATION"
)

// MCPResponseFormatter ports StandardResponseFormatter. The name differs
// because package utils already declares a StandardResponseFormatter interface
// (json_parameter_mixin.go); this type satisfies that interface.
type MCPResponseFormatter struct {
	Optimizer           *services.ResponseOptimizer
	OptimizationEnabled bool
	LegacyMode          bool
}

var mcpResponseFormatterInstance *MCPResponseFormatter

// NewMCPResponseFormatter ports __init__.
func NewMCPResponseFormatter() *MCPResponseFormatter {
	f := &MCPResponseFormatter{
		Optimizer:  services.NewResponseOptimizer(),
		LegacyMode: false,
	}
	v := strings.ToLower(os.Getenv("ENABLE_RESPONSE_OPTIMIZATION"))
	if v == "" {
		v = "true"
	}
	f.OptimizationEnabled = v == "true" || v == "1" || v == "yes" || v == "on"
	return f
}

// GetInstance ports the get_instance singleton classmethod.
func (f *MCPResponseFormatter) GetInstance() *MCPResponseFormatter {
	if mcpResponseFormatterInstance == nil {
		mcpResponseFormatterInstance = NewMCPResponseFormatter()
	}
	return mcpResponseFormatterInstance
}

// CreateResponse ports create_response.
func (f *MCPResponseFormatter) CreateResponse(
	status ResponseStatus,
	operation string,
	data *entities.OrderedMap[any],
	err *string,
	errorCode *string,
	partialFailures []*entities.OrderedMap[any],
	metadata *entities.OrderedMap[any],
	workflowGuidance *entities.OrderedMap[any],
	requestContext *entities.OrderedMap[any],
	profile *services.ResponseProfile,
) *entities.OrderedMap[any] {
	operationID := newResponseOperationID()
	timestamp := value_objects.IsoFormat(time.Now().UTC())

	response := entities.NewOrderedMap[any]()
	response.Set("status", string(status))
	response.Set("success", status != ResponseStatusFailure)
	response.Set("operation", operation)
	response.Set("operation_id", operationID)
	response.Set("timestamp", timestamp)

	confirmation := entities.NewOrderedMap[any]()
	confirmation.Set("operation_completed", status != ResponseStatusFailure)
	confirmation.Set("data_present", status != ResponseStatusFailure && data != nil)
	var partial []any
	for _, pf := range partialFailures {
		partial = append(partial, pf)
	}
	if partial == nil {
		partial = []any{}
	}
	confirmation.Set("partial_failures", partial)
	operationDetails := entities.NewOrderedMap[any]()
	operationDetails.Set("operation", operation)
	operationDetails.Set("operation_id", operationID)
	operationDetails.Set("timestamp", timestamp)
	confirmation.Set("operation_details", operationDetails)
	response.Set("confirmation", confirmation)

	if data != nil {
		response.Set("data", data)
	}
	if err != nil && *err != "" {
		errorInfo := entities.NewOrderedMap[any]()
		errorInfo.Set("message", *err)
		code := "UNKNOWN_ERROR"
		if errorCode != nil {
			code = *errorCode
		}
		errorInfo.Set("code", code)
		errorInfo.Set("operation", operation)
		errorInfo.Set("timestamp", timestamp)
		response.Set("error", errorInfo)
	}
	if orderedMapTruthy(metadata) {
		response.Set("metadata", metadata)
	}
	if orderedMapTruthy(workflowGuidance) {
		response.Set("workflow_guidance", workflowGuidance)
	}

	if f.OptimizationEnabled && f.Optimizer != nil {
		if requestContext != nil {
			if headersAny, ok := requestContext.Get("headers"); ok {
				if headers, ok := headersAny.(*entities.OrderedMap[any]); ok {
					if format, ok := headers.Get("X-Response-Format"); ok && value_objects.PyStr(format) == "legacy" {
						return response
					}
				}
			}
		}
		optimized := func() (out *entities.OrderedMap[any]) {
			defer func() {
				if recover() != nil {
					out = response
				}
			}()
			return f.Optimizer.OptimizeResponse(response, profile, requestContext)
		}()
		if optimized != nil {
			return optimized
		}
		return response
	}
	return response
}

// CreateSuccessResponse ports create_success_response.
func (f *MCPResponseFormatter) CreateSuccessResponse(
	operation string,
	data *entities.OrderedMap[any],
	metadata *entities.OrderedMap[any],
	workflowGuidance *entities.OrderedMap[any],
	requestContext *entities.OrderedMap[any],
	profile *services.ResponseProfile,
) *entities.OrderedMap[any] {
	return f.CreateResponse(ResponseStatusSuccess, operation, data, nil, nil, nil, metadata, workflowGuidance, requestContext, profile)
}

// CreateErrorResponse ports create_error_response. The signature matches the
// existing utils.StandardResponseFormatter interface, so request_context is nil.
func (f *MCPResponseFormatter) CreateErrorResponse(operation, errorMessage, errorCode string, metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	return f.CreateResponse(ResponseStatusFailure, operation, nil, &errorMessage, &errorCode, nil, metadata, nil, nil, nil)
}

// CreatePartialSuccessResponse ports create_partial_success_response.
func (f *MCPResponseFormatter) CreatePartialSuccessResponse(
	operation string,
	data *entities.OrderedMap[any],
	partialFailures []*entities.OrderedMap[any],
	metadata *entities.OrderedMap[any],
	workflowGuidance *entities.OrderedMap[any],
	requestContext *entities.OrderedMap[any],
	profile *services.ResponseProfile,
) *entities.OrderedMap[any] {
	return f.CreateResponse(ResponseStatusPartialSuccess, operation, data, nil, nil, partialFailures, metadata, workflowGuidance, requestContext, profile)
}

// CreateValidationErrorResponse ports create_validation_error_response.
func (f *MCPResponseFormatter) CreateValidationErrorResponse(
	operation, field, expected string,
	actual *string,
	hint *string,
	requestContext *entities.OrderedMap[any],
) *entities.OrderedMap[any] {
	errorDetails := entities.NewOrderedMap[any]()
	errorDetails.Set("field", field)
	errorDetails.Set("expected", expected)
	h := "Please provide a valid " + field
	if hint != nil {
		h = *hint
	}
	errorDetails.Set("hint", h)
	if actual != nil && *actual != "" {
		errorDetails.Set("actual", *actual)
	}
	validationDetails := entities.NewOrderedMap[any]()
	validationDetails.Set("validation_details", errorDetails)
	msg := "Validation failed for field: " + field
	return f.CreateResponse(ResponseStatusFailure, operation, nil, &msg, ptrString(ErrorCodesValidationError), nil, validationDetails, nil, requestContext, nil)
}

// VerifyResponseSuccess ports the verify_success staticmethod.
func VerifyResponseSuccess(response *entities.OrderedMap[any]) bool {
	if response == nil {
		return false
	}
	status, _ := response.Get("status")
	if value_objects.PyStr(status) != string(ResponseStatusSuccess) {
		return false
	}
	success, _ := response.Get("success")
	if !pyIsTrue(success) {
		return false
	}
	if response.Has("error") {
		return false
	}
	confirmation := rfGetMap(response, "confirmation")
	if confirmation == nil {
		return false
	}
	oc, _ := confirmation.Get("operation_completed")
	dp, _ := confirmation.Get("data_present")
	if !pyIsTrue(oc) || !pyIsTrue(dp) {
		return false
	}
	return len(rfPartialFailures(confirmation)) == 0
}

// ExtractResponseData ports the extract_data staticmethod.
func ExtractResponseData(response *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if !VerifyResponseSuccess(response) {
		return nil
	}
	v, _ := response.Get("data")
	m, _ := v.(*entities.OrderedMap[any])
	return m
}

// GetResponseOperationID ports the get_operation_id staticmethod.
func GetResponseOperationID(response *entities.OrderedMap[any]) any {
	if response == nil {
		return nil
	}
	v, _ := response.Get("operation_id")
	return v
}

// HasResponsePartialFailures ports the has_partial_failures staticmethod.
func HasResponsePartialFailures(response *entities.OrderedMap[any]) bool {
	if response == nil {
		return false
	}
	status, _ := response.Get("status")
	if value_objects.PyStr(status) == string(ResponseStatusPartialSuccess) {
		return true
	}
	return len(rfPartialFailures(rfGetMap(response, "confirmation"))) > 0
}

// FormatSuccess ports format_success.
func (f *MCPResponseFormatter) FormatSuccess(
	data *entities.OrderedMap[any],
	operation string,
	metadata *entities.OrderedMap[any],
	requestContext *entities.OrderedMap[any],
	profile *services.ResponseProfile,
) *entities.OrderedMap[any] {
	if data != nil && data.Has("status") && data.Has("operation_id") {
		return data
	}

	success, _ := data.Get("success")
	if pyIsTrue(success) {
		mainData := entities.NewOrderedMap[any]()
		operationInfo := entities.NewOrderedMap[any]()
		operationFields := map[string]bool{
			"level": true, "context_id": true, "source_level": true, "target_level": true,
			"propagated": true, "inherited": true, "created": true, "count": true,
		}
		for _, key := range data.Keys() {
			if key == "success" || key == "error" {
				continue
			}
			value, _ := data.Get(key)
			if operationFields[key] {
				operationInfo.Set(key, value)
			} else {
				mainData.Set(key, value)
			}
		}
		if metadata == nil {
			metadata = entities.NewOrderedMap[any]()
		}
		metadata.Set("operation_details", operationInfo)
		return f.CreateSuccessResponse(operation, mainData, metadata, nil, requestContext, profile)
	} else if pyIsFalse(success) {
		errorMessage := "Unknown error occurred"
		if v, ok := data.Get("error"); ok {
			errorMessage = value_objects.PyStr(v)
		}
		return f.CreateErrorResponse(operation, errorMessage, "UNKNOWN_ERROR", metadata)
	}
	return f.CreateSuccessResponse(operation, data, metadata, nil, requestContext, profile)
}

// FormatContextResponse ports format_context_response.
func (f *MCPResponseFormatter) FormatContextResponse(
	data *entities.OrderedMap[any],
	operation string,
	standardizeFieldNames bool,
	requestContext *entities.OrderedMap[any],
	profile *services.ResponseProfile,
) *entities.OrderedMap[any] {
	if !standardizeFieldNames {
		return f.FormatSuccess(data, operation, nil, requestContext, profile)
	}

	standardizedData := entities.NewOrderedMap[any]()
	metadata := entities.NewOrderedMap[any]()

	success, _ := data.Get("success")
	if pyIsTrue(success) {
		endswith := func(suffix string) bool { return strings.HasSuffix(operation, suffix) }
		switch {
		case operation == "create" || operation == "get" || endswith(".create") || endswith(".get"):
			if ctxAny, ok := data.Get("context"); ok && orderedAnyTruthy(ctxAny) {
				if ctx, ok := ctxAny.(*entities.OrderedMap[any]); ok {
					standardizedData = ctx
				}
			}
		case operation == "update" || endswith(".update"):
			ctxAny, hasCtx := data.Get("context")
			if hasCtx && orderedAnyTruthy(ctxAny) {
				contextData, _ := ctxAny.(*entities.OrderedMap[any])
				out := entities.NewOrderedMap[any]()
				out.Set("id", rfGetWithDefault(data, "context_id", rfGetOrNil(contextData, "id")))
				out.Set("updated_data", contextData)
				lv, _ := data.Get("level")
				out.Set("level", lv)
				pv, _ := data.Get("propagated")
				out.Set("propagated", rfDefault(pv, false))
				standardizedData = out
			} else {
				out := entities.NewOrderedMap[any]()
				cid, _ := data.Get("context_id")
				out.Set("id", cid)
				out.Set("updated_data", entities.NewOrderedMap[any]())
				lv, _ := data.Get("level")
				out.Set("level", lv)
				pv, _ := data.Get("propagated")
				out.Set("propagated", rfDefault(pv, false))
				standardizedData = out
			}
		case operation == "list" || endswith(".list"):
			if v, ok := data.Get("contexts"); ok {
				standardizedData.Set("contexts", v)
			} else if v, ok := data.Get("context"); ok {
				standardizedData.Set("contexts", []any{v})
			}
		case operation == "delegate" || endswith(".delegate"):
			if v, ok := data.Get("delegation"); ok {
				standardizedData.Set("delegation_result", v)
			}
		case operation == "resolve" || endswith(".resolve"):
			if v, ok := data.Get("context"); ok {
				standardizedData.Set("resolved_context", v)
			} else if v, ok := data.Get("resolved"); ok {
				standardizedData.Set("resolved_context", v)
			}
		}

		contextOperation := entities.NewOrderedMap[any]()
		if operation == "update" || endswith(".update") {
			contextOperation.Set("source_level", rfGetOrNil(data, "source_level"))
			contextOperation.Set("target_level", rfGetOrNil(data, "target_level"))
			contextOperation.Set("inherited", rfGetDefault(data, "inherited", false))
			contextOperation.Set("created", rfGetDefault(data, "created", false))
			contextOperation.Set("count", rfGetOrNil(data, "count"))
			contextOperation.Set("operation_type", "update")
		} else {
			contextOperation.Set("level", rfGetOrNil(data, "level"))
			contextOperation.Set("context_id", rfGetOrNil(data, "context_id"))
			contextOperation.Set("source_level", rfGetOrNil(data, "source_level"))
			contextOperation.Set("target_level", rfGetOrNil(data, "target_level"))
			contextOperation.Set("inherited", rfGetDefault(data, "inherited", false))
			contextOperation.Set("propagated", rfGetDefault(data, "propagated", false))
			contextOperation.Set("created", rfGetDefault(data, "created", false))
			contextOperation.Set("count", rfGetOrNil(data, "count"))
		}
		filtered := entities.NewOrderedMap[any]()
		for _, k := range contextOperation.Keys() {
			v, _ := contextOperation.Get(k)
			if v != nil {
				filtered.Set(k, v)
			}
		}
		metadata.Set("context_operation", filtered)
		return f.CreateSuccessResponse(operation, standardizedData, metadata, nil, requestContext, profile)
	}

	return f.FormatSuccess(data, operation, nil, requestContext, profile)
}

// --- helpers ---

func ptrString(s string) *string { return &s }

func orderedMapTruthy(m *entities.OrderedMap[any]) bool { return m != nil && m.Len() > 0 }

func orderedAnyTruthy(v any) bool {
	switch t := v.(type) {
	case nil:
		return false
	case *entities.OrderedMap[any]:
		return t != nil && t.Len() > 0
	default:
		return value_objects.PyTruthy(v)
	}
}

func pyIsTrue(v any) bool  { b, ok := v.(bool); return ok && b }
func pyIsFalse(v any) bool { b, ok := v.(bool); return ok && !b }

func rfGetMap(m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	out, _ := v.(*entities.OrderedMap[any])
	return out
}

func rfGetOrNil(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, ok := m.Get(key)
	if !ok {
		return nil
	}
	return v
}

func rfGetWithDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

func rfGetDefault(m *entities.OrderedMap[any], key string, def any) any {
	if m != nil {
		if v, ok := m.Get(key); ok {
			return v
		}
	}
	return def
}

func rfDefault(v any, def any) any {
	if v == nil {
		return def
	}
	return v
}

func rfPartialFailures(confirmation *entities.OrderedMap[any]) []any {
	if confirmation == nil {
		return nil
	}
	v, _ := confirmation.Get("partial_failures")
	if v == nil {
		return nil
	}
	switch t := v.(type) {
	case []any:
		return t
	case []*entities.OrderedMap[any]:
		out := make([]any, 0, len(t))
		for _, x := range t {
			out = append(out, x)
		}
		return out
	}
	return nil
}

func newResponseOperationID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "00000000-0000-4000-8000-000000000000"
	}
	b[6] = (b[6] & 0x0f) | 0x40
	b[8] = (b[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}
