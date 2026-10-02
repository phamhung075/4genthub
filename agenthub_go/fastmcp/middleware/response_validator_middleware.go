// Package middleware ports agenthub_main/src/fastmcp/middleware.
package middleware

import (
	"fmt"
	"math/big"
	"math/rand"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	vo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ---------------------------------------------------------------------------
// Environment configuration (read at package init, like the Python module).
// ---------------------------------------------------------------------------

// getenvDefault is os.getenv(key, default): the default is used only when the
// variable is absent, not when it is set to the empty string.
func getenvDefault(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}

// pyEnvFlag mirrors os.getenv(key, def).lower() in ("true", "1", "yes").
func pyEnvFlag(key, def string) bool {
	switch vo.PyLower(getenvDefault(key, def)) {
	case "true", "1", "yes":
		return true
	}
	return false
}

// pyEnvLower mirrors os.getenv(key, def).lower().
func pyEnvLower(key, def string) string { return vo.PyLower(getenvDefault(key, def)) }

// pyEnvInt mirrors int(os.getenv(key, def)); an invalid value panics with a
// ValueError, matching the import-time failure in Python.
func pyEnvInt(key, def string) int {
	s := getenvDefault(key, def)
	n, err := strconv.Atoi(s)
	if err != nil {
		panic(&vo.ValueError{Msg: fmt.Sprintf("invalid literal for int() with base 10: '%s'", s)})
	}
	return n
}

var (
	// ValidateResponses is VALIDATE_RESPONSES (default "true").
	ValidateResponses = pyEnvFlag("VALIDATE_RESPONSES", "true")
	// ValidationLogLevel is VALIDATION_LOG_LEVEL (default "warning", lowercased).
	ValidationLogLevel = pyEnvLower("VALIDATION_LOG_LEVEL", "warning")
	// ValidationSampleRate is VALIDATION_SAMPLE_RATE (default 100).
	ValidationSampleRate = pyEnvInt("VALIDATION_SAMPLE_RATE", "100")
)

// ---------------------------------------------------------------------------
// Shared Python type plumbing (json.loads values).
// ---------------------------------------------------------------------------

// py type-kind tokens are the exact type(...).__name__ strings Python reports.
const (
	pyKindStr   = "str"
	pyKindList  = "list"
	pyKindDict  = "dict"
	pyKindInt   = "int"
	pyKindBool  = "bool"
	pyKindFloat = "float"
)

// FieldSchema is one {type, required, default} entry of a schema dict.
type FieldSchema struct {
	Type     string
	Required bool
	Default  any
}

type schemaEntry struct {
	name string
	def  FieldSchema
}

func newSchema(entries ...schemaEntry) *entities.OrderedMap[FieldSchema] {
	m := entities.NewOrderedMap[FieldSchema]()
	for _, e := range entries {
		m.Set(e.name, e.def)
	}
	return m
}

// isPyDict is isinstance(v, dict) for the dict representations used here.
func isPyDict(v any) bool {
	switch v.(type) {
	case *entities.OrderedMap[any], map[string]any:
		return true
	}
	return false
}

// asOrderedDict normalizes a Python dict-like value to an OrderedMap.
func asOrderedDict(v any) (*entities.OrderedMap[any], bool) {
	switch m := v.(type) {
	case *entities.OrderedMap[any]:
		return m, true
	case map[string]any:
		om := entities.NewOrderedMap[any]()
		for k, val := range m {
			om.Set(k, val)
		}
		return om, true
	}
	return nil, false
}

// pyIsInstance is isinstance(value, kind) for JSON-like values and the
// str/list/int/dict/bool/float schema tokens. Python bool is a subclass of int.
func pyIsInstance(value any, kind string) bool {
	switch kind {
	case pyKindStr:
		_, ok := value.(string)
		return ok
	case pyKindBool:
		_, ok := value.(bool)
		return ok
	case pyKindDict:
		return isPyDict(value)
	case pyKindList:
		rv := reflect.ValueOf(value)
		if !rv.IsValid() {
			return false
		}
		k := rv.Kind()
		return k == reflect.Slice || k == reflect.Array
	case pyKindInt:
		if _, ok := value.(bool); ok {
			return true // bool subclasses int
		}
		if _, ok := value.(*big.Int); ok {
			return true
		}
		rv := reflect.ValueOf(value)
		switch rv.Kind() {
		case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
			reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
			return true
		}
		return false
	case pyKindFloat:
		rv := reflect.ValueOf(value)
		switch rv.Kind() {
		case reflect.Float32, reflect.Float64:
			return true
		}
		return false
	}
	return false
}

// pyTypeName is type(value).__name__ for a JSON-like value.
func pyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case bool:
		return pyKindBool
	case string:
		return pyKindStr
	case *big.Int:
		return pyKindInt
	case *entities.OrderedMap[any]:
		return pyKindDict
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return pyKindInt
	case reflect.Float32, reflect.Float64:
		return pyKindFloat
	case reflect.Slice, reflect.Array:
		return pyKindList
	case reflect.Map:
		return pyKindDict
	case reflect.Pointer:
		if rv.IsNil() {
			return "NoneType"
		}
		return pyTypeName(rv.Elem().Interface())
	}
	return "object"
}

// ---------------------------------------------------------------------------
// ValidationIssue / ResponseValidator
// ---------------------------------------------------------------------------

// ValidationIssue represents a validation issue found in a response.
type ValidationIssue struct {
	Severity  string // error, warning, info
	FieldPath string
	IssueType string // missing, null, wrong_type, unexpected
	Expected  any
	Actual    any
	Message   string
	Timestamp string
}

func newIssue(severity, fieldPath, issueType string, expected, actual any, message string) *ValidationIssue {
	return &ValidationIssue{
		Severity:  severity,
		FieldPath: fieldPath,
		IssueType: issueType,
		Expected:  expected,
		Actual:    actual,
		Message:   message,
		Timestamp: vo.IsoFormat(time.Now().UTC()),
	}
}

// ResponseValidator validates response payloads against expected schemas.
type ResponseValidator struct{}

// TaskSchema is ResponseValidator.TASK_SCHEMA (field order preserved).
var TaskSchema = newSchema(
	schemaEntry{"id", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"title", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"status", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"priority", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"assignees", FieldSchema{Type: pyKindList, Required: true, Default: []any{}}},
	schemaEntry{"labels", FieldSchema{Type: pyKindList, Required: true, Default: []any{}}},
	schemaEntry{"subtask_count", FieldSchema{Type: pyKindInt, Required: true, Default: 0}},
	schemaEntry{"completed_subtasks", FieldSchema{Type: pyKindInt, Required: true, Default: 0}},
	schemaEntry{"progress_percentage", FieldSchema{Type: pyKindInt, Required: true, Default: 0}},
	schemaEntry{"progress_count", FieldSchema{Type: pyKindInt, Required: true, Default: 0}},
	schemaEntry{"created_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"updated_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"git_branch_id", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"project_id", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"description", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"details", FieldSchema{Type: pyKindStr, Required: false}},
	schemaEntry{"context_data", FieldSchema{Type: pyKindDict, Required: false}},
	schemaEntry{"has_dependencies", FieldSchema{Type: pyKindBool, Required: false}},
	schemaEntry{"has_context", FieldSchema{Type: pyKindBool, Required: false}},
)

// SubtaskSchema is ResponseValidator.SUBTASK_SCHEMA.
var SubtaskSchema = newSchema(
	schemaEntry{"id", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"title", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"status", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"priority", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"assignees", FieldSchema{Type: pyKindList, Required: true, Default: []any{}}},
	schemaEntry{"progress_percentage", FieldSchema{Type: pyKindInt, Required: true, Default: 0}},
	schemaEntry{"created_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"updated_at", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"parent_task_id", FieldSchema{Type: pyKindStr, Required: true}},
)

// WebSocketMessageSchema is ResponseValidator.WEBSOCKET_MESSAGE_SCHEMA.
var WebSocketMessageSchema = newSchema(
	schemaEntry{"event", FieldSchema{Type: pyKindStr, Required: true}},
	schemaEntry{"data", FieldSchema{Type: pyKindDict, Required: true}},
	schemaEntry{"timestamp", FieldSchema{Type: pyKindStr, Required: false}},
)

// ValidateField validates a single field against its schema definition. It
// returns the (at most one) issue the Python method would append, or nil.
func (ResponseValidator) ValidateField(fieldPath string, value any, schemaDef FieldSchema) *ValidationIssue {
	expectedType := schemaDef.Type
	isRequired := schemaDef.Required
	defaultValue := schemaDef.Default

	if value == nil {
		if isRequired && defaultValue == nil {
			expected := "any"
			if expectedType != "" {
				expected = expectedType
			}
			return newIssue("error", fieldPath, "missing", expected, nil,
				fmt.Sprintf("Required field '%s' is missing or null", fieldPath))
		} else if isRequired && defaultValue != nil {
			return newIssue("warning", fieldPath, "null", defaultValue, nil,
				fmt.Sprintf("Field '%s' is null but should default to %s", fieldPath, vo.PyStr(defaultValue)))
		}
		return nil
	}

	if expectedType != "" && !pyIsInstance(value, expectedType) {
		return newIssue("error", fieldPath, "wrong_type", expectedType, pyTypeName(value),
			fmt.Sprintf("Field '%s' has wrong type: expected %s, got %s", fieldPath, expectedType, pyTypeName(value)))
	}
	return nil
}

// ValidateObject validates an object against a schema.
func (r ResponseValidator) ValidateObject(obj *entities.OrderedMap[any], schema *entities.OrderedMap[FieldSchema], parentPath string) []ValidationIssue {
	issues := []ValidationIssue{}

	for _, fieldName := range schema.Keys() {
		fieldSchema, _ := schema.Get(fieldName)
		fieldPath := fieldName
		if parentPath != "" {
			fieldPath = parentPath + "." + fieldName
		}
		var value any
		if obj != nil {
			value, _ = obj.Get(fieldName)
		}
		if issue := r.ValidateField(fieldPath, value, fieldSchema); issue != nil {
			issues = append(issues, *issue)
		}
	}

	// Unexpected fields (Python iterates a set; insertion order is used here).
	if obj != nil {
		schemaFields := map[string]bool{}
		for _, k := range schema.Keys() {
			schemaFields[k] = true
		}
		for _, unexpectedField := range obj.Keys() {
			if schemaFields[unexpectedField] {
				continue
			}
			fieldPath := unexpectedField
			if parentPath != "" {
				fieldPath = parentPath + "." + unexpectedField
			}
			v, _ := obj.Get(unexpectedField)
			issues = append(issues, *newIssue("info", fieldPath, "unexpected", "not in schema", pyTypeName(v),
				fmt.Sprintf("Unexpected field '%s' not in schema (possible schema drift)", unexpectedField)))
		}
	}

	return issues
}

// ValidateTaskResponse validates a task response.
func (r ResponseValidator) ValidateTaskResponse(taskData *entities.OrderedMap[any]) []ValidationIssue {
	return r.ValidateObject(taskData, TaskSchema, "task")
}

// ValidateSubtaskResponse validates a subtask response.
func (r ResponseValidator) ValidateSubtaskResponse(subtaskData *entities.OrderedMap[any]) []ValidationIssue {
	return r.ValidateObject(subtaskData, SubtaskSchema, "subtask")
}

// ValidateListResponse validates a list of items.
func (r ResponseValidator) ValidateListResponse(items []any, itemSchema *entities.OrderedMap[FieldSchema], itemType string) []ValidationIssue {
	allIssues := []ValidationIssue{}
	for idx, item := range items {
		obj, _ := item.(*entities.OrderedMap[any])
		issues := r.ValidateObject(obj, itemSchema, fmt.Sprintf("%s[%d]", itemType, idx))
		allIssues = append(allIssues, issues...)
	}
	return allIssues
}

// ---------------------------------------------------------------------------
// ResponseValidatorMiddleware
// ---------------------------------------------------------------------------

// ResponseValidatorMiddleware validates all HTTP responses. The Python
// BaseHTTPMiddleware maps to Middleware, a stdlib func(http.Handler) http.Handler.
type ResponseValidatorMiddleware struct {
	ValidationStats *entities.OrderedMap[int]
}

// NewResponseValidatorMiddleware builds the middleware with zeroed stats in
// the Python insertion order.
func NewResponseValidatorMiddleware() *ResponseValidatorMiddleware {
	stats := entities.NewOrderedMap[int]()
	stats.Set("total_requests", 0)
	stats.Set("validated_requests", 0)
	stats.Set("issues_found", 0)
	stats.Set("errors", 0)
	stats.Set("warnings", 0)
	return &ResponseValidatorMiddleware{ValidationStats: stats}
}

func (m *ResponseValidatorMiddleware) addStat(key string, delta int) {
	v, _ := m.ValidationStats.Get(key)
	m.ValidationStats.Set(key, v+delta)
}

// Middleware wraps next with the Python dispatch logic.
func (m *ResponseValidatorMiddleware) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		m.addStat("total_requests", 1)

		// Skip validation if disabled or not sampled.
		if !ValidateResponses || rand.Intn(100)+1 > ValidationSampleRate {
			next.ServeHTTP(w, r)
			return
		}

		// Skip validation for non-API endpoints.
		if !m.shouldValidatePath(r.URL.Path) {
			next.ServeHTTP(w, r)
			return
		}

		rec := httptest.NewRecorder()
		next.ServeHTTP(rec, r)

		contentType := rec.Header().Get("Content-Type")
		if !strings.Contains(contentType, "application/json") {
			writeRecorded(w, rec)
			return
		}

		m.validateResponse(r, rec)
		m.addStat("validated_requests", 1)
		writeRecorded(w, rec)
	})
}

func (m *ResponseValidatorMiddleware) shouldValidatePath(path string) bool {
	validatePrefixes := []string{
		"/mcp/",
		"/api/tasks",
		"/api/subtasks",
		"/api/projects",
		"/api/branches",
		"/api/context",
	}
	for _, prefix := range validatePrefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

// validateResponse validates the recorded response body. Errors are swallowed
// like the Python method's internal try/except (logging dropped).
func (m *ResponseValidatorMiddleware) validateResponse(request *http.Request, rec *httptest.ResponseRecorder) {
	// Streaming responses can't be validated.
	if rec.Flushed {
		return
	}

	body := rec.Body.Bytes()
	if len(body) == 0 {
		return
	}

	data, err := entities.DecodeJSON(body)
	if err != nil {
		return // "Could not parse response JSON" (logging dropped)
	}

	path := request.URL.Path
	var issues []ValidationIssue

	if strings.Contains(path, "/tasks") || strings.Contains(path, "/mcp/") {
		issues = m.validateTaskEndpoint(data)
	} else if strings.Contains(path, "/subtasks") {
		issues = m.validateSubtaskEndpoint(data)
	}

	if len(issues) > 0 {
		m.addStat("issues_found", len(issues))
		for _, issue := range issues {
			switch issue.Severity {
			case "error":
				m.addStat("errors", 1)
			case "warning":
				m.addStat("warnings", 1)
			}
		}
	}
}

func (m *ResponseValidatorMiddleware) validateTaskEndpoint(data any) []ValidationIssue {
	issues := []ValidationIssue{}
	r := ResponseValidator{}

	root, ok := data.(*entities.OrderedMap[any])
	if !ok {
		return issues
	}

	if v, ok := root.Get("task"); ok {
		if task, ok := v.(*entities.OrderedMap[any]); ok {
			issues = append(issues, r.ValidateTaskResponse(task)...)
		}
	} else if v, ok := root.Get("tasks"); ok && pyIsInstance(v, pyKindList) {
		if list, ok := v.([]any); ok {
			issues = append(issues, r.ValidateListResponse(list, TaskSchema, "task")...)
		}
	} else if v, ok := root.Get("data"); ok {
		if d, ok := v.(*entities.OrderedMap[any]); ok {
			if tv, ok := d.Get("task"); ok {
				if task, ok := tv.(*entities.OrderedMap[any]); ok {
					issues = append(issues, r.ValidateTaskResponse(task)...)
				}
			} else if tv, ok := d.Get("tasks"); ok {
				if list, ok := tv.([]any); ok {
					issues = append(issues, r.ValidateListResponse(list, TaskSchema, "task")...)
				}
			}
		}
	}

	return issues
}

func (m *ResponseValidatorMiddleware) validateSubtaskEndpoint(data any) []ValidationIssue {
	issues := []ValidationIssue{}
	r := ResponseValidator{}

	root, ok := data.(*entities.OrderedMap[any])
	if !ok {
		return issues
	}

	if v, ok := root.Get("subtask"); ok {
		if subtask, ok := v.(*entities.OrderedMap[any]); ok {
			issues = append(issues, r.ValidateSubtaskResponse(subtask)...)
		}
	} else if v, ok := root.Get("subtasks"); ok && pyIsInstance(v, pyKindList) {
		if list, ok := v.([]any); ok {
			issues = append(issues, r.ValidateListResponse(list, SubtaskSchema, "subtask")...)
		}
	}

	return issues
}

// GetStats returns validation statistics (key order preserved).
func (m *ResponseValidatorMiddleware) GetStats() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for _, k := range m.ValidationStats.Keys() {
		v, _ := m.ValidationStats.Get(k)
		out.Set(k, v)
	}
	total, _ := m.ValidationStats.Get("total_requests")
	validated, _ := m.ValidationStats.Get("validated_requests")
	rate := float64(validated) / float64(max(total, 1)) * 100
	out.Set("validation_rate", fmt.Sprintf("%.1f%%", rate))
	return out
}

// writeRecorded copies a buffered response onto the real writer.
func writeRecorded(w http.ResponseWriter, rec *httptest.ResponseRecorder) {
	for k, vals := range rec.Header() {
		for _, v := range vals {
			w.Header().Add(k, v)
		}
	}
	code := rec.Code
	if code == 0 {
		code = http.StatusOK
	}
	w.WriteHeader(code)
	_, _ = w.Write(rec.Body.Bytes())
}
