package factories

// Focused behaviour tests for the task factories, expectations read from the
// Python response_factory.py / validation_factory.py sources.

import (
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type draftFakeFormatter struct {
	lastOperation string
	lastError     string
	lastCode      string
	lastMetadata  *entities.OrderedMap[any]
	lastData      any
	lastGuidance  *entities.OrderedMap[any]
	lastSuccess   bool
}

func (f *draftFakeFormatter) CreateSuccessResponse(operation string, data any,
	workflowGuidance *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastSuccess = true
	f.lastOperation = operation
	f.lastData = data
	f.lastGuidance = workflowGuidance
	out := entities.NewOrderedMap[any]()
	out.Set("status", "success")
	return out
}

func (f *draftFakeFormatter) CreateErrorResponse(operation, errorMessage, errorCode string,
	metadata *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	f.lastSuccess = false
	f.lastOperation = operation
	f.lastError = errorMessage
	f.lastCode = errorCode
	f.lastMetadata = metadata
	out := entities.NewOrderedMap[any]()
	out.Set("status", "failure")
	return out
}

func (f *draftFakeFormatter) GetTimestamp() string { return "2024-01-01T00:00:00+00:00" }

func draftKeys(m *entities.OrderedMap[any]) []string {
	if m == nil {
		return nil
	}
	return m.Keys()
}

func TestDraftCreateValidationErrorResponse(t *testing.T) {
	ff := &draftFakeFormatter{}
	rf := NewResponseFactory(ff)
	rf.CreateValidationErrorResponse("title", "A non-empty title string",
		"Include 'title' in your request", nil)

	if ff.lastOperation != "validation" {
		t.Fatalf("operation = %q", ff.lastOperation)
	}
	if ff.lastError != "Invalid field: title. Expected: A non-empty title string" {
		t.Fatalf("error = %q", ff.lastError)
	}
	if ff.lastCode != "VALIDATION_ERROR" {
		t.Fatalf("code = %q", ff.lastCode)
	}
	if got := strings.Join(draftKeys(ff.lastMetadata), ","); got != "field,hint" {
		t.Fatalf("metadata keys = %q", got)
	}
	if v, _ := ff.lastMetadata.Get("field"); v != "title" {
		t.Fatalf("field = %v", v)
	}
}

func TestDraftCreateBusinessRuleErrorResponse(t *testing.T) {
	ff := &draftFakeFormatter{}
	rf := NewResponseFactory(ff)
	rf.CreateBusinessRuleErrorResponse("title_length", "Task title must be at least 3 characters long",
		"Provide a more descriptive title for the task", nil)

	if ff.lastOperation != "business_validation" {
		t.Fatalf("operation = %q", ff.lastOperation)
	}
	if ff.lastError != "Business rule violation (title_length): Task title must be at least 3 characters long" {
		t.Fatalf("error = %q", ff.lastError)
	}
	if ff.lastCode != "BUSINESS_RULE_VIOLATION" {
		t.Fatalf("code = %q", ff.lastCode)
	}
	if got := strings.Join(draftKeys(ff.lastMetadata), ","); got != "rule,hint" {
		t.Fatalf("metadata keys = %q", got)
	}
}

func TestDraftCreateMissingFieldError(t *testing.T) {
	rf := NewResponseFactory(&draftFakeFormatter{})
	got := rf.CreateMissingFieldError("title", "create_task")

	if v, _ := got.Get("status"); v != "failure" {
		t.Fatalf("status = %v", v)
	}
	errObj, _ := got.Get("error")
	if errObj.(*entities.OrderedMap[any]).Keys()[0] != "message" {
		t.Fatalf("error keys = %v", errObj.(*entities.OrderedMap[any]).Keys())
	}
	if v, _ := errObj.(*entities.OrderedMap[any]).Get("message"); v != "Validation failed for field: title" {
		t.Fatalf("error message = %v", v)
	}
	if v, _ := got.Get("operation"); v != "create_task" {
		t.Fatalf("operation = %v", v)
	}
	md, _ := got.Get("metadata")
	vd, _ := md.(*entities.OrderedMap[any]).Get("validation_details")
	details := vd.(*entities.OrderedMap[any])
	if got := strings.Join(details.Keys(), ","); got != "field,expected,hint" {
		t.Fatalf("validation_details keys = %q", got)
	}
	if v, _ := details.Get("expected"); v != "A valid title value" {
		t.Fatalf("expected = %v", v)
	}
	if v, _ := details.Get("hint"); v != "Include 'title' in your request for action 'create_task'" {
		t.Fatalf("hint = %v", v)
	}
}

func TestDraftCreateInvalidActionErrorDefaultActions(t *testing.T) {
	rf := NewResponseFactory(&draftFakeFormatter{})
	got := rf.CreateInvalidActionError("bogus", nil)
	md, _ := got.Get("metadata")
	vd, _ := md.(*entities.OrderedMap[any]).Get("validation_details")
	details := vd.(*entities.OrderedMap[any])
	expected, _ := details.Get("expected")
	want := "One of: create, update, get, delete, complete, list, search, next, add_dependency, remove_dependency, ai_plan, ai_create, ai_enhance, ai_analyze, ai_suggest_agents"
	if expected != want {
		t.Fatalf("expected = %q", expected)
	}
	hint, _ := details.Get("hint")
	if hint != "Invalid action: bogus. Use one of the supported actions." {
		t.Fatalf("hint = %q", hint)
	}
}

func TestDraftStandardizeFacadeResponseSuccess(t *testing.T) {
	ff := &draftFakeFormatter{}
	rf := NewResponseFactory(ff)

	facade := entities.NewOrderedMap[any]()
	facade.Set("success", true)
	facade.Set("action", "create")
	facade.Set("task", "T")
	wg := entities.NewOrderedMap[any]()
	wg.Set("next", "review")
	facade.Set("workflow_guidance", wg)

	rf.StandardizeFacadeResponse(facade, "create")

	if !ff.lastSuccess {
		t.Fatal("expected success response")
	}
	data := ff.lastData.(*entities.OrderedMap[any])
	if got := strings.Join(data.Keys(), ","); got != "task" {
		t.Fatalf("data keys = %q", got)
	}
	if ff.lastGuidance != wg {
		t.Fatal("workflow_guidance not extracted")
	}
}

func TestDraftStandardizeFacadeResponseError(t *testing.T) {
	ff := &draftFakeFormatter{}
	rf := NewResponseFactory(ff)

	facade := entities.NewOrderedMap[any]()
	facade.Set("success", false)
	facade.Set("error", "boom")
	facade.Set("error_code", "CONFLICT")
	facade.Set("retry", true)

	rf.StandardizeFacadeResponse(facade, "create")

	if ff.lastError != "boom" || ff.lastCode != "CONFLICT" {
		t.Fatalf("error=%q code=%q", ff.lastError, ff.lastCode)
	}
	if got := strings.Join(draftKeys(ff.lastMetadata), ","); got != "retry" {
		t.Fatalf("metadata keys = %q", got)
	}
}

// --- validation factory ---

type draftFakeParamValidator struct {
	createCalled bool
	updateCalled bool
	searchCalled bool
	valid        bool
	lastFilters  map[string]any
	lastBranch   *string
}

func (v *draftFakeParamValidator) ValidateCreateTaskParams(title, gitBranchID, description, status, priority, dueDate *string,
	assignees, labels, dependencies []string) (bool, *entities.OrderedMap[any]) {
	v.createCalled = true
	if title != nil {
		b := *title
		v.lastBranch = &b
	}
	return v.valid, draftErr("param")
}

func (v *draftFakeParamValidator) ValidateUpdateTaskParams(taskID *string, filters map[string]any) (bool, *entities.OrderedMap[any]) {
	v.updateCalled = true
	v.lastFilters = filters
	return v.valid, draftErr("param")
}

func (v *draftFakeParamValidator) ValidateSearchParams(query *string, filters map[string]any) (bool, *entities.OrderedMap[any]) {
	v.searchCalled = true
	return v.valid, draftErr("param")
}

type draftFakeContextValidator struct {
	reqCalled  bool
	dataCalled bool
	valid      bool
	lastOp     string
}

func (v *draftFakeContextValidator) ValidateContextRequirements(operation string, taskID, gitBranchID *string,
	includeContext *bool) (bool, *entities.OrderedMap[any]) {
	v.reqCalled = true
	v.lastOp = operation
	return v.valid, draftErr("context")
}

func (v *draftFakeContextValidator) ValidateContextData(contextData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {
	v.dataCalled = true
	return v.valid, draftErr("context")
}

type draftFakeBusinessValidator struct {
	createCalled bool
	updateCalled bool
	valid        bool
}

func (v *draftFakeBusinessValidator) ValidateTaskCreationRules(title, gitBranchID string, priority, dueDate *string,
	dependencies []string) (bool, *entities.OrderedMap[any]) {
	v.createCalled = true
	return v.valid, draftErr("business")
}

func (v *draftFakeBusinessValidator) ValidateTaskUpdateRules(taskID string, currentTaskData *entities.OrderedMap[any],
	status, priority, dueDate *string, dependencies []string, completionSummary *string) (bool, *entities.OrderedMap[any]) {
	v.updateCalled = true
	return v.valid, draftErr("business")
}

func (v *draftFakeBusinessValidator) ValidateCompletionRequirements(taskData *entities.OrderedMap[any],
	completionSummary, testingNotes *string) (bool, *entities.OrderedMap[any]) {
	return v.valid, draftErr("business")
}

func (v *draftFakeBusinessValidator) ValidateTaskDeletionRules(taskID string,
	currentTaskData *entities.OrderedMap[any]) (bool, *entities.OrderedMap[any]) {
	return v.valid, draftErr("business")
}

func draftErr(prefix string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("error", prefix)
	return m
}

func draftSetupValidationFactory(p, c, b bool) (*ValidationFactory, *draftFakeParamValidator, *draftFakeContextValidator, *draftFakeBusinessValidator) {
	param := &draftFakeParamValidator{valid: p}
	ctx := &draftFakeContextValidator{valid: c}
	biz := &draftFakeBusinessValidator{valid: b}
	oldP, oldC, oldB := NewParameterValidator, NewContextValidator, NewBusinessValidator
	NewParameterValidator = func(ResponseFormatter) ParameterValidator { return param }
	NewContextValidator = func(ResponseFormatter) ContextValidator { return ctx }
	NewBusinessValidator = func(ResponseFormatter) BusinessValidator { return biz }
	vf := NewValidationFactory(&draftFakeFormatter{})
	NewParameterValidator, NewContextValidator, NewBusinessValidator = oldP, oldC, oldB
	return vf, param, ctx, biz
}

func TestDraftValidationCreateStopsAtParameter(t *testing.T) {
	vf, param, ctx, biz := draftSetupValidationFactory(false, true, true)
	title := "ab"
	branch := "11111111-1111-1111-1111-111111111111"
	ok, errResp := vf.ValidateCreateRequest(&title, &branch, nil, nil, nil, nil, nil, nil, nil, nil)
	if ok || errResp == nil {
		t.Fatal("expected parameter failure")
	}
	if !param.createCalled || ctx.reqCalled || biz.createCalled {
		t.Fatalf("call order wrong: param=%v ctx=%v biz=%v", param.createCalled, ctx.reqCalled, biz.createCalled)
	}
}

func TestDraftValidationCreateSkipsEmptyContextData(t *testing.T) {
	vf, _, ctx, biz := draftSetupValidationFactory(true, true, true)
	title := "abc"
	branch := "11111111-1111-1111-1111-111111111111"
	empty := entities.NewOrderedMap[any]()
	ok, _ := vf.ValidateCreateRequest(&title, &branch, nil, nil, nil, nil, nil, nil, nil, empty)
	if !ok {
		t.Fatal("expected valid")
	}
	if ctx.dataCalled {
		t.Fatal("empty context_data must not be validated")
	}
	if !biz.createCalled {
		t.Fatal("business rules must run")
	}
}

func TestDraftValidationUpdateFiltersTaskID(t *testing.T) {
	vf, param, _, _ := draftSetupValidationFactory(true, true, true)
	taskID := "22222222-2222-2222-2222-222222222222"
	params := map[string]any{"task_id": taskID, "status": "done"}
	ok, _ := vf.ValidateUpdateRequest(&taskID, nil, params)
	if !ok {
		t.Fatal("expected valid")
	}
	if _, has := param.lastFilters["task_id"]; has {
		t.Fatal("task_id must be removed from update params")
	}
}
