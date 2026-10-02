package middleware

import (
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// om builds a Python-dict-like OrderedMap from alternating key/value pairs.
func om(pairs ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func validTask() *entities.OrderedMap[any] {
	return om(
		"id", "t1",
		"title", "Task",
		"status", "pending",
		"priority", "medium",
		"assignees", []any{},
		"labels", []any{},
		"subtask_count", int64(2),
		"completed_subtasks", int64(1),
		"progress_percentage", int64(50),
		"progress_count", int64(2),
		"created_at", "2024-01-01T00:00:00+00:00",
		"updated_at", "2024-01-02T00:00:00+00:00",
	)
}

func validSubtask() *entities.OrderedMap[any] {
	return om(
		"id", "s1",
		"title", "Subtask",
		"status", "pending",
		"priority", "medium",
		"assignees", []any{},
		"progress_percentage", int64(0),
		"created_at", "2024-01-01T00:00:00+00:00",
		"updated_at", "2024-01-02T00:00:00+00:00",
		"parent_task_id", "t1",
	)
}

func TestValidateFieldMissing(t *testing.T) {
	issue := (ResponseValidator{}).ValidateField("task.title", nil, FieldSchema{Type: pyKindStr, Required: true})
	if issue == nil {
		t.Fatal("expected an issue")
	}
	if issue.Severity != "error" || issue.IssueType != "missing" {
		t.Fatalf("severity/type = %q/%q", issue.Severity, issue.IssueType)
	}
	if issue.Expected != "str" {
		t.Fatalf("expected = %#v", issue.Expected)
	}
	if issue.Actual != nil {
		t.Fatalf("actual = %#v", issue.Actual)
	}
	if issue.Message != "Required field 'task.title' is missing or null" {
		t.Fatalf("message = %q", issue.Message)
	}
	if issue.Timestamp == "" {
		t.Fatal("timestamp empty")
	}
}

func TestValidateFieldMissingWithoutType(t *testing.T) {
	issue := (ResponseValidator{}).ValidateField("field", nil, FieldSchema{Required: true})
	if issue == nil || issue.Expected != "any" {
		t.Fatalf("expected = %#v", issue)
	}
}

func TestValidateFieldNullWithDefault(t *testing.T) {
	def := FieldSchema{Type: pyKindList, Required: true, Default: []any{}}
	issue := (ResponseValidator{}).ValidateField("assignees", nil, def)
	if issue == nil {
		t.Fatal("expected an issue")
	}
	if issue.Severity != "warning" || issue.IssueType != "null" {
		t.Fatalf("severity/type = %q/%q", issue.Severity, issue.IssueType)
	}
	if !reflect.DeepEqual(issue.Expected, []any{}) {
		t.Fatalf("expected = %#v", issue.Expected)
	}
	if issue.Message != "Field 'assignees' is null but should default to []" {
		t.Fatalf("message = %q", issue.Message)
	}
}

func TestValidateFieldOptionalNullIsClean(t *testing.T) {
	if issue := (ResponseValidator{}).ValidateField("description", nil, FieldSchema{Type: pyKindStr, Required: false}); issue != nil {
		t.Fatalf("unexpected issue: %#v", issue)
	}
}

func TestValidateFieldWrongType(t *testing.T) {
	issue := (ResponseValidator{}).ValidateField("task.title", 123, FieldSchema{Type: pyKindStr, Required: true})
	if issue == nil {
		t.Fatal("expected an issue")
	}
	if issue.Severity != "error" || issue.IssueType != "wrong_type" {
		t.Fatalf("severity/type = %q/%q", issue.Severity, issue.IssueType)
	}
	if issue.Expected != "str" || issue.Actual != "int" {
		t.Fatalf("expected/actual = %#v/%#v", issue.Expected, issue.Actual)
	}
	if issue.Message != "Field 'task.title' has wrong type: expected str, got int" {
		t.Fatalf("message = %q", issue.Message)
	}
}

func TestValidateFieldBoolIsIntQuirk(t *testing.T) {
	// Python bool is a subclass of int: isinstance(True, int) is True.
	if issue := (ResponseValidator{}).ValidateField("count", true, FieldSchema{Type: pyKindInt, Required: true}); issue != nil {
		t.Fatalf("bool should satisfy int: %#v", issue)
	}
	if issue := (ResponseValidator{}).ValidateField("count", false, FieldSchema{Type: pyKindInt, Required: true}); issue != nil {
		t.Fatalf("bool should satisfy int: %#v", issue)
	}
	// ... but bool is reported as "bool", not "int".
	if got := pyTypeName(true); got != "bool" {
		t.Fatalf("pyTypeName(true) = %q", got)
	}
	if issue := (ResponseValidator{}).ValidateField("flag", int64(1), FieldSchema{Type: pyKindBool, Required: true}); issue == nil || issue.Actual != "int" {
		t.Fatalf("int should not satisfy bool: %#v", issue)
	}
	// float must not satisfy int.
	if issue := (ResponseValidator{}).ValidateField("count", 1.5, FieldSchema{Type: pyKindInt, Required: true}); issue == nil {
		t.Fatal("float should not satisfy int")
	}
}

func TestValidateObjectUnexpectedFields(t *testing.T) {
	schema := newSchema(schemaEntry{"id", FieldSchema{Type: pyKindStr, Required: true}})
	obj := om("id", "1", "extra", "x", "n", int64(5))

	issues := (ResponseValidator{}).ValidateObject(obj, schema, "")
	if len(issues) != 2 {
		t.Fatalf("len(issues) = %d: %#v", len(issues), issues)
	}
	if issues[0].FieldPath != "extra" || issues[0].IssueType != "unexpected" || issues[0].Severity != "info" {
		t.Fatalf("issues[0] = %#v", issues[0])
	}
	if issues[0].Expected != "not in schema" || issues[0].Actual != "str" {
		t.Fatalf("issues[0] expected/actual = %#v/%#v", issues[0].Expected, issues[0].Actual)
	}
	if issues[0].Message != "Unexpected field 'extra' not in schema (possible schema drift)" {
		t.Fatalf("message = %q", issues[0].Message)
	}
	if issues[1].FieldPath != "n" || issues[1].Actual != "int" {
		t.Fatalf("issues[1] = %#v", issues[1])
	}
}

func TestValidateObjectUnexpectedWithParentPath(t *testing.T) {
	schema := newSchema(schemaEntry{"id", FieldSchema{Type: pyKindStr, Required: true}})
	obj := om("id", "1", "extra", "x")
	issues := (ResponseValidator{}).ValidateObject(obj, schema, "task")
	if len(issues) != 1 || issues[0].FieldPath != "task.extra" {
		t.Fatalf("issues = %#v", issues)
	}
}

func TestValidateTaskResponseValid(t *testing.T) {
	if issues := (ResponseValidator{}).ValidateTaskResponse(validTask()); len(issues) != 0 {
		t.Fatalf("expected no issues, got %#v", issues)
	}
}

func TestValidateTaskResponseMissingField(t *testing.T) {
	task := validTask()
	task.Delete("title")
	issues := (ResponseValidator{}).ValidateTaskResponse(task)
	if len(issues) != 1 {
		t.Fatalf("len(issues) = %d: %#v", len(issues), issues)
	}
	if issues[0].FieldPath != "task.title" || issues[0].IssueType != "missing" || issues[0].Severity != "error" {
		t.Fatalf("issue = %#v", issues[0])
	}
	if issues[0].Message != "Required field 'task.title' is missing or null" {
		t.Fatalf("message = %q", issues[0].Message)
	}
}

func TestValidateTaskResponseWrongType(t *testing.T) {
	task := validTask()
	task.Set("subtask_count", "2")
	issues := (ResponseValidator{}).ValidateTaskResponse(task)
	if len(issues) != 1 {
		t.Fatalf("len(issues) = %d: %#v", len(issues), issues)
	}
	if issues[0].FieldPath != "task.subtask_count" || issues[0].Expected != "int" || issues[0].Actual != "str" {
		t.Fatalf("issue = %#v", issues[0])
	}
}

func TestValidateTaskResponseBoolAcceptedAsInt(t *testing.T) {
	task := validTask()
	task.Set("subtask_count", true)
	if issues := (ResponseValidator{}).ValidateTaskResponse(task); len(issues) != 0 {
		t.Fatalf("bool should satisfy int: %#v", issues)
	}
}

func TestValidateSubtaskResponse(t *testing.T) {
	if issues := (ResponseValidator{}).ValidateSubtaskResponse(validSubtask()); len(issues) != 0 {
		t.Fatalf("expected no issues, got %#v", issues)
	}

	subtask := validSubtask()
	subtask.Delete("parent_task_id")
	issues := (ResponseValidator{}).ValidateSubtaskResponse(subtask)
	if len(issues) != 1 || issues[0].FieldPath != "subtask.parent_task_id" || issues[0].IssueType != "missing" {
		t.Fatalf("issue = %#v", issues)
	}
}

func TestValidateListResponse(t *testing.T) {
	second := validTask()
	second.Delete("status")
	items := []any{validTask(), second}
	issues := (ResponseValidator{}).ValidateListResponse(items, TaskSchema, "task")
	if len(issues) != 1 {
		t.Fatalf("len(issues) = %d: %#v", len(issues), issues)
	}
	if issues[0].FieldPath != "task[1].status" || issues[0].IssueType != "missing" {
		t.Fatalf("issue = %#v", issues[0])
	}
}

func TestValidateTaskEndpointFallsThroughWhenTasksNotList(t *testing.T) {
	// Python: elif "tasks" in data and isinstance(data["tasks"], list) -> when
	// "tasks" is present but not a list the condition is false, so the chain
	// falls through to the "data" branch.
	root := om("tasks", "notalist", "data", om("task", om("id", "t1")))
	issues := NewResponseValidatorMiddleware().validateTaskEndpoint(root)
	found := false
	for _, i := range issues {
		if i.FieldPath == "task.title" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected data.task validation, got %#v", issues)
	}
}

func TestShouldValidatePath(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	yes := []string{"/mcp/tools", "/api/tasks/1", "/api/subtasks", "/api/projects/x", "/api/branches", "/api/context", "/api/tasks-extra"}
	for _, p := range yes {
		if !m.shouldValidatePath(p) {
			t.Errorf("expected %q to validate", p)
		}
	}
	no := []string{"/health", "/api/other", "/subtasks", "/api", ""}
	for _, p := range no {
		if m.shouldValidatePath(p) {
			t.Errorf("expected %q not to validate", p)
		}
	}
}

func TestGetStatsFormatting(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	m.addStat("total_requests", 3)
	m.addStat("validated_requests", 1)
	m.addStat("issues_found", 2)
	m.addStat("errors", 1)
	m.addStat("warnings", 1)

	stats := m.GetStats()
	if got := stats.Keys(); !reflect.DeepEqual(got, []string{"total_requests", "validated_requests", "issues_found", "errors", "warnings", "validation_rate"}) {
		t.Fatalf("keys = %#v", got)
	}
	if v, _ := stats.Get("validation_rate"); v != "33.3%" {
		t.Fatalf("validation_rate = %#v", v)
	}

	empty := NewResponseValidatorMiddleware()
	if v, _ := empty.GetStats().Get("validation_rate"); v != "0.0%" {
		t.Fatalf("empty validation_rate = %#v", v)
	}

	two := NewResponseValidatorMiddleware()
	two.addStat("total_requests", 3)
	two.addStat("validated_requests", 2)
	if v, _ := two.GetStats().Get("validation_rate"); v != "66.7%" {
		t.Fatalf("validation_rate = %#v", v)
	}
}

const validTaskJSON = `{"task":{"id":"t1","title":"Task","status":"pending","priority":"medium","assignees":[],"labels":[],"subtask_count":2,"completed_subtasks":1,"progress_percentage":50,"progress_count":2,"created_at":"2024-01-01T00:00:00+00:00","updated_at":"2024-01-02T00:00:00+00:00"}}`

const invalidTaskJSON = `{"task":{"id":"t1","status":"pending","priority":"medium","assignees":[],"labels":[],"subtask_count":2,"completed_subtasks":1,"progress_percentage":50,"progress_count":2,"created_at":"2024-01-01T00:00:00+00:00","updated_at":"2024-01-02T00:00:00+00:00"}}`

func serve(m *ResponseValidatorMiddleware, method, path, contentType, body string) *httptest.ResponseRecorder {
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if contentType != "" {
			w.Header().Set("Content-Type", contentType)
		}
		_, _ = w.Write([]byte(body))
	})
	rec := httptest.NewRecorder()
	m.Middleware(next).ServeHTTP(rec, httptest.NewRequest(method, path, nil))
	return rec
}

func TestMiddlewareValidJSONPassesThroughAndValidates(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	rec := serve(m, http.MethodGet, "/api/tasks/t1", "application/json; charset=utf-8", validTaskJSON)
	if rec.Body.String() != validTaskJSON {
		t.Fatalf("body not passed through: %q", rec.Body.String())
	}
	stats := m.GetStats()
	if v, _ := stats.Get("total_requests"); v != 1 {
		t.Fatalf("total_requests = %#v", v)
	}
	if v, _ := stats.Get("validated_requests"); v != 1 {
		t.Fatalf("validated_requests = %#v", v)
	}
	if v, _ := stats.Get("issues_found"); v != 0 {
		t.Fatalf("issues_found = %#v", v)
	}
}

func TestMiddlewareInvalidJSONCountsIssues(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	serve(m, http.MethodGet, "/api/tasks/t1", "application/json", invalidTaskJSON)
	stats := m.GetStats()
	if v, _ := stats.Get("validated_requests"); v != 1 {
		t.Fatalf("validated_requests = %#v", v)
	}
	if v, _ := stats.Get("issues_found"); v != 1 {
		t.Fatalf("issues_found = %#v", v)
	}
	if v, _ := stats.Get("errors"); v != 1 {
		t.Fatalf("errors = %#v", v)
	}
}

func TestMiddlewareSkipsNonJSONContentType(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	serve(m, http.MethodGet, "/api/tasks/t1", "text/plain", invalidTaskJSON)
	stats := m.GetStats()
	if v, _ := stats.Get("validated_requests"); v != 0 {
		t.Fatalf("validated_requests = %#v", v)
	}
}

func TestMiddlewareSkipsUnvalidatedPath(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	serve(m, http.MethodGet, "/health", "application/json", invalidTaskJSON)
	stats := m.GetStats()
	if v, _ := stats.Get("validated_requests"); v != 0 {
		t.Fatalf("validated_requests = %#v", v)
	}
}

func TestMiddlewareDisabledSkipsValidation(t *testing.T) {
	old := ValidateResponses
	ValidateResponses = false
	defer func() { ValidateResponses = old }()

	m := NewResponseValidatorMiddleware()
	serve(m, http.MethodGet, "/api/tasks/t1", "application/json", invalidTaskJSON)
	stats := m.GetStats()
	if v, _ := stats.Get("total_requests"); v != 1 {
		t.Fatalf("total_requests = %#v", v)
	}
	if v, _ := stats.Get("validated_requests"); v != 0 {
		t.Fatalf("validated_requests = %#v", v)
	}
}

func TestMiddlewareSampleRateZeroSkipsValidation(t *testing.T) {
	old := ValidationSampleRate
	ValidationSampleRate = 0
	defer func() { ValidationSampleRate = old }()

	m := NewResponseValidatorMiddleware()
	serve(m, http.MethodGet, "/api/tasks/t1", "application/json", invalidTaskJSON)
	if v, _ := m.GetStats().Get("validated_requests"); v != 0 {
		t.Fatalf("validated_requests = %#v", v)
	}
}

func TestMiddlewareStreamingResponseCannotBeValidated(t *testing.T) {
	m := NewResponseValidatorMiddleware()
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(invalidTaskJSON))
		if f, ok := w.(http.Flusher); ok {
			f.Flush()
		}
	})
	rec := httptest.NewRecorder()
	m.Middleware(next).ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/api/tasks/t1", nil))
	stats := m.GetStats()
	if v, _ := stats.Get("validated_requests"); v != 1 {
		t.Fatalf("validated_requests = %#v", v)
	}
	if v, _ := stats.Get("issues_found"); v != 0 {
		t.Fatalf("streaming issues_found = %#v", v)
	}
	if !strings.Contains(rec.Body.String(), `"id":"t1"`) {
		t.Fatalf("streamed body not delivered: %q", rec.Body.String())
	}
}
