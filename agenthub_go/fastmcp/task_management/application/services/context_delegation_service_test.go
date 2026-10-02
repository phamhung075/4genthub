package services

import (
	"context"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// zpCtxDelFakeRepository is the in-memory zpCtxDelRepository used by the tests.
// It records the last arguments it saw so call shapes can be checked.
type zpCtxDelFakeRepository struct {
	delegations    []*entities.OrderedMap[any]
	delegationsErr error
	lastFilters    *entities.OrderedMap[any]

	delegation       *entities.OrderedMap[any]
	getDelegationErr error

	lastUpdate  *entities.OrderedMap[any]
	updateCalls int
	updateErr   error

	globalContext    *entities.OrderedMap[any]
	projectContext   *entities.OrderedMap[any]
	taskContext      *entities.OrderedMap[any]
	contextErr       error
	lastUpdatedCtx   *entities.OrderedMap[any]
	lastUpdatedLevel string

	storedData *entities.OrderedMap[any]
	storeID    string
	storeErr   error
}

func (f *zpCtxDelFakeRepository) GetDelegations(ctx context.Context, filters *entities.OrderedMap[any]) ([]*entities.OrderedMap[any], error) {
	f.lastFilters = filters
	return f.delegations, f.delegationsErr
}

func (f *zpCtxDelFakeRepository) GetDelegation(ctx context.Context, delegationID string) (*entities.OrderedMap[any], error) {
	return f.delegation, f.getDelegationErr
}

func (f *zpCtxDelFakeRepository) UpdateDelegation(ctx context.Context, delegationID string, updates *entities.OrderedMap[any]) (bool, error) {
	f.lastUpdate = updates
	f.updateCalls++
	return f.updateErr == nil, f.updateErr
}

func (f *zpCtxDelFakeRepository) GetGlobalContext(ctx context.Context, contextID string) (*entities.OrderedMap[any], error) {
	return f.globalContext, f.contextErr
}

func (f *zpCtxDelFakeRepository) GetProjectContext(ctx context.Context, contextID string) (*entities.OrderedMap[any], error) {
	return f.projectContext, f.contextErr
}

func (f *zpCtxDelFakeRepository) GetTaskContext(ctx context.Context, contextID string) (*entities.OrderedMap[any], error) {
	return f.taskContext, f.contextErr
}

func (f *zpCtxDelFakeRepository) UpdateGlobalContext(ctx context.Context, contextID string, contextData *entities.OrderedMap[any]) (bool, error) {
	f.lastUpdatedCtx = contextData
	f.lastUpdatedLevel = "global"
	return f.contextErr == nil, f.contextErr
}

func (f *zpCtxDelFakeRepository) UpdateProjectContext(ctx context.Context, contextID string, contextData *entities.OrderedMap[any]) (bool, error) {
	f.lastUpdatedCtx = contextData
	f.lastUpdatedLevel = "project"
	return f.contextErr == nil, f.contextErr
}

func (f *zpCtxDelFakeRepository) UpdateTaskContext(ctx context.Context, contextID string, contextData *entities.OrderedMap[any]) (bool, error) {
	f.lastUpdatedCtx = contextData
	f.lastUpdatedLevel = "task"
	return f.contextErr == nil, f.contextErr
}

func (f *zpCtxDelFakeRepository) StoreDelegation(ctx context.Context, delegationData *entities.OrderedMap[any]) (string, error) {
	f.storedData = delegationData
	return f.storeID, f.storeErr
}

// zpCtxDelOM builds an ordered map from alternating key (string) / value pairs.
func zpCtxDelOM(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func zpCtxDelStrPtr(s string) *string  { return &s }
func zpCtxDelFloat(f float64) *float64 { return &f }

func TestContextDelegationService_ValidateDelegationRequest(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)
	data := zpCtxDelOM("data", "test")

	cases := []struct {
		name        string
		sourceLevel string
		targetLevel string
		delegated   *entities.OrderedMap[any]
		wantValid   bool
		wantErrors  []any
	}{
		{"valid", "task", "project", data, true, []any{}},
		{"invalid source", "invalid_level", "project", data, false, []any{"Invalid source level: invalid_level"}},
		{"invalid target", "task", "invalid_level", data, false, []any{"Invalid target level: invalid_level"}},
		{"downward", "project", "task", data, false, []any{"Cannot delegate from project to task - must delegate upward"}},
		{"same level", "project", "project", data, false, []any{"Cannot delegate from project to project - must delegate upward"}},
		{"no data", "task", "project", entities.NewOrderedMap[any](), false, []any{"No data provided for delegation"}},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			result := svc.validateDelegationRequest(tc.sourceLevel, "src", tc.targetLevel, "tgt", tc.delegated)
			valid, _ := result.Get("valid")
			if valid != tc.wantValid {
				t.Fatalf("valid = %v, want %v", valid, tc.wantValid)
			}
			errs, _ := result.Get("errors")
			if !reflect.DeepEqual(errs, tc.wantErrors) {
				t.Fatalf("errors = %#v, want %#v", errs, tc.wantErrors)
			}
			if !reflect.DeepEqual(result.Keys(), []string{"valid", "errors"}) {
				t.Fatalf("keys = %v", result.Keys())
			}
		})
	}
}

func TestContextDelegationService_ProcessDelegationValidationFailure(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	result := svc.ProcessDelegation(context.Background(), "task", "task_1", "project", "proj_1",
		entities.NewOrderedMap[any](), "Test reason", "manual", nil)

	if success, _ := result.Get("success"); success != false {
		t.Fatalf("success = %v, want false", success)
	}
	errText, _ := result.Get("error")
	want := "Invalid delegation request: ['No data provided for delegation']"
	if errText != want {
		t.Fatalf("error = %q, want %q", errText, want)
	}
	if id, _ := result.Get("delegation_id"); id != nil {
		t.Fatalf("delegation_id = %v, want nil", id)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "error", "delegation_id"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
}

func TestContextDelegationService_ProcessDelegationAutoApproved(t *testing.T) {
	repo := &zpCtxDelFakeRepository{
		storeID:        "del_1",
		projectContext: zpCtxDelOM("existing", "value"),
	}
	svc := zpCtxDelNewContextDelegationService(repo, nil)

	data := zpCtxDelOM("security_discovery", "vulnerability found")
	result := svc.ProcessDelegation(context.Background(), "task", "task_1", "project", "proj_1",
		data, "Security fix", "manual", zpCtxDelFloat(0.9))

	if success, _ := result.Get("success"); success != true {
		t.Fatalf("success = %v, want true", success)
	}
	if id, _ := result.Get("delegation_id"); id != "del_1" {
		t.Fatalf("delegation_id = %v", id)
	}
	if auto, _ := result.Get("auto_approved"); auto != true {
		t.Fatalf("auto_approved = %v, want true", auto)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"success", "delegation_id", "auto_approved", "impact_assessment", "result"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	execResult, _ := result.Get("result")
	execMap, ok := execResult.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("result is %T", execResult)
	}
	if impl, _ := execMap.Get("implemented"); impl != true {
		t.Fatalf("implemented = %v, want true", impl)
	}

	// _store_delegation_request payload shape and order.
	wantStoreKeys := []string{"source_level", "source_id", "target_level", "target_id", "delegated_data", "reason", "trigger_type", "auto_delegated", "confidence_score"}
	if !reflect.DeepEqual(repo.storedData.Keys(), wantStoreKeys) {
		t.Fatalf("store keys = %v", repo.storedData.Keys())
	}
	if auto, _ := repo.storedData.Get("auto_delegated"); auto != false {
		t.Fatalf("auto_delegated = %v", auto)
	}
	if conf, _ := repo.storedData.Get("confidence_score"); conf != 0.9 {
		t.Fatalf("confidence_score = %v", conf)
	}
}

func TestContextDelegationService_AssessDelegationImpact(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	high := zpCtxDelNewDelegationRequest("task", "task_1", "global", "global_singleton", zpCtxDelOM("data", "test"), "Security improvement")
	high.ConfidenceScore = zpCtxDelFloat(0.9)
	result := svc.assessDelegationImpact(context.Background(), high)

	if score, _ := result.Get("impact_score"); score != 100 {
		t.Fatalf("impact_score = %v, want 100", score)
	}
	if rec, _ := result.Get("recommendation"); rec != "auto_approve" {
		t.Fatalf("recommendation = %v", rec)
	}
	risks, _ := result.Get("risk_factors")
	if !reflect.DeepEqual(risks, []any{"High impact on all projects"}) {
		t.Fatalf("risk_factors = %#v", risks)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"impact_score", "risk_factors", "benefits", "recommendation"}) {
		t.Fatalf("keys = %v", result.Keys())
	}

	low := zpCtxDelNewDelegationRequest("task", "task_1", "task", "task_2", zpCtxDelOM("test", "data"), "Test")
	low.TriggerType = "unknown"
	low.ConfidenceScore = zpCtxDelFloat(0.3)
	lowResult := svc.assessDelegationImpact(context.Background(), low)
	if score, _ := lowResult.Get("impact_score"); score != -20 {
		t.Fatalf("low impact_score = %v, want -20", score)
	}
	if rec, _ := lowResult.Get("recommendation"); rec != "manual_review" {
		t.Fatalf("low recommendation = %v", rec)
	}
}

func TestContextDelegationService_ShouldAutoApprove(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	high := zpCtxDelNewDelegationRequest("task", "task_1", "project", "proj_1", zpCtxDelOM("data", "test"), "Test")
	high.ConfidenceScore = zpCtxDelFloat(0.9)
	if !svc.shouldAutoApprove(context.Background(), high, zpCtxDelOM("recommendation", "auto_approve")) {
		t.Fatal("high confidence with auto_approve recommendation should auto-approve")
	}

	low := zpCtxDelNewDelegationRequest("task", "task_1", "project", "proj_1", zpCtxDelOM("data", "test"), "Test")
	low.ConfidenceScore = zpCtxDelFloat(0.5)
	if svc.shouldAutoApprove(context.Background(), low, zpCtxDelOM("recommendation", "auto_approve")) {
		t.Fatal("confidence 0.5 must not auto-approve")
	}

	pattern := zpCtxDelNewDelegationRequest("task", "task_1", "global", "global_singleton", zpCtxDelOM("security_discovery", "vulnerability found"), "Security")
	pattern.ConfidenceScore = zpCtxDelFloat(0.8)
	if !svc.shouldAutoApprove(context.Background(), pattern, zpCtxDelOM("recommendation", "manual_review")) {
		t.Fatal("security_discovery data should auto-approve")
	}

	nilData := zpCtxDelNewDelegationRequest("task", "task_1", "project", "proj_1", nil, "Test")
	if svc.shouldAutoApprove(context.Background(), nilData, entities.NewOrderedMap[any]()) {
		t.Fatal("nil delegated_data must not auto-approve")
	}
}

func TestContextDelegationService_MatchesPattern(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	cases := []struct {
		pattern string
		changes *entities.OrderedMap[any]
		want    bool
	}{
		{"security_discovery", zpCtxDelOM("findings", "Found security vulnerability in authentication"), true},
		{"team_improvement", zpCtxDelOM("process_improvement", "Updated team workflow"), true},
		{"reusable_utility", zpCtxDelOM("component", "Created reusable authentication utility"), true},
		{"security_discovery", zpCtxDelOM("routine_update", "Updated documentation formatting"), false},
		{"unknown_pattern", zpCtxDelOM("test", "data"), false},
	}
	for _, tc := range cases {
		got, err := svc.matchesPattern(tc.changes, tc.pattern)
		if err != nil {
			t.Fatalf("matchesPattern(%q) error: %v", tc.pattern, err)
		}
		if got != tc.want {
			t.Fatalf("matchesPattern(%q) = %v, want %v", tc.pattern, got, tc.want)
		}
	}
}

func TestContextDelegationService_ExceedsThreshold(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	countTrue := svc.exceedsThreshold(zpCtxDelOM("key", "value"),
		zpCtxDelOM("description", "security issue found in security module"),
		"security_count", zpCtxDelOM("type", "count", "value", 2, "pattern", "security"))
	if !countTrue {
		t.Fatal("count threshold should be exceeded")
	}

	percentageTrue := svc.exceedsThreshold(zpCtxDelOM("completion_rate", 85),
		zpCtxDelOM("update", "progress updated"), "completion_rate",
		zpCtxDelOM("type", "percentage", "value", 80))
	if !percentageTrue {
		t.Fatal("percentage threshold should be exceeded")
	}

	percentageFalse := svc.exceedsThreshold(zpCtxDelOM("error_count", 3),
		zpCtxDelOM("update", "minor fix"), "error_count",
		zpCtxDelOM("type", "percentage", "value", 10))
	if percentageFalse {
		t.Fatal("3 < 10 should not exceed")
	}

	invalidType := svc.exceedsThreshold(entities.NewOrderedMap[any](), entities.NewOrderedMap[any](), "test",
		zpCtxDelOM("type", "invalid_type"))
	if invalidType {
		t.Fatal("unknown threshold type must be false")
	}

	// Python quirk: str(changes).lower().count("") is len+1, so an empty pattern
	// exceeds any threshold up to the repr length + 1.
	emptyTrue := svc.exceedsThreshold(entities.NewOrderedMap[any](), zpCtxDelOM("a", "b"), "test",
		zpCtxDelOM("type", "count", "value", 11, "pattern", ""))
	if !emptyTrue {
		t.Fatal("empty pattern count 11 should exceed 11")
	}
	emptyFalse := svc.exceedsThreshold(entities.NewOrderedMap[any](), zpCtxDelOM("a", "b"), "test",
		zpCtxDelOM("type", "count", "value", 12, "pattern", ""))
	if emptyFalse {
		t.Fatal("empty pattern count 11 should not exceed 12")
	}
}

func TestContextDelegationService_MergeToGlobalContext(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	delegated := zpCtxDelOM("security_insights", zpCtxDelOM("new_policy", "value"))
	request := zpCtxDelNewDelegationRequest("task", "task_1", "global", "global_singleton", delegated, "Security best practices")
	result, err := svc.mergeToGlobalContext(entities.NewOrderedMap[any](), delegated, request)
	if err != nil {
		t.Fatalf("mergeToGlobalContext error: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"security_policies", "delegated_insights"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	policies, _ := result.Get("security_policies")
	policyMap := policies.(*entities.OrderedMap[any])
	if v, _ := policyMap.Get("new_policy"); v != "value" {
		t.Fatalf("new_policy = %v", v)
	}
	insights, _ := result.Get("delegated_insights")
	insightList := insights.([]any)
	if len(insightList) != 1 {
		t.Fatalf("delegated_insights len = %d", len(insightList))
	}
	item := insightList[0].(*entities.OrderedMap[any])
	if item.Keys()[0] != "delegation_id" || item.Keys()[4] != "delegated_at" {
		t.Fatalf("insight keys = %v", item.Keys())
	}
	if source, _ := item.Get("source"); source != "task:task_1" {
		t.Fatalf("source = %v", source)
	}

	// Coding branch uses "standard" in the reason, not "coding".
	codingData := zpCtxDelOM("coding_patterns", zpCtxDelOM("pattern", "factory_pattern"))
	codingRequest := zpCtxDelNewDelegationRequest("task", "task_1", "global", "global_singleton", codingData, "Coding standard improvement")
	codingResult, err := svc.mergeToGlobalContext(entities.NewOrderedMap[any](), codingData, codingRequest)
	if err != nil {
		t.Fatalf("coding merge error: %v", err)
	}
	if !reflect.DeepEqual(codingResult.Keys(), []string{"coding_standards", "delegated_insights"}) {
		t.Fatalf("coding keys = %v", codingResult.Keys())
	}
}

func TestContextDelegationService_MergeToProjectContext(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	delegated := zpCtxDelOM("team_insights", zpCtxDelOM("collaboration", "improved"))
	request := zpCtxDelNewDelegationRequest("task", "task_1", "project", "proj_1", delegated, "Team efficiency improvement")
	result, err := svc.mergeToProjectContext(entities.NewOrderedMap[any](), delegated, request)
	if err != nil {
		t.Fatalf("mergeToProjectContext error: %v", err)
	}
	if !reflect.DeepEqual(result.Keys(), []string{"team_preferences", "delegated_insights"}) {
		t.Fatalf("keys = %v", result.Keys())
	}
	prefs, _ := result.Get("team_preferences")
	prefMap := prefs.(*entities.OrderedMap[any])
	if v, _ := prefMap.Get("collaboration"); v != "improved" {
		t.Fatalf("collaboration = %v", v)
	}

	techData := zpCtxDelOM("tech_insights", zpCtxDelOM("library", "new_framework"))
	techRequest := zpCtxDelNewDelegationRequest("task", "task_1", "project", "proj_1", techData, "Technology stack update")
	techResult, err := svc.mergeToProjectContext(entities.NewOrderedMap[any](), techData, techRequest)
	if err != nil {
		t.Fatalf("technology merge error: %v", err)
	}
	if !reflect.DeepEqual(techResult.Keys(), []string{"technology_stack", "delegated_insights"}) {
		t.Fatalf("technology keys = %v", techResult.Keys())
	}
}

func TestContextDelegationService_GetPendingDelegationsFilters(t *testing.T) {
	repo := &zpCtxDelFakeRepository{
		delegations: []*entities.OrderedMap[any]{
			zpCtxDelOM("delegation_id", "del_1"),
			zpCtxDelOM("delegation_id", "del_2"),
		},
	}
	svc := zpCtxDelNewContextDelegationService(repo, nil)

	delegations := svc.GetPendingDelegations(context.Background(), zpCtxDelStrPtr("project"), zpCtxDelStrPtr("proj_123"))
	if len(delegations) != 2 {
		t.Fatalf("len = %d", len(delegations))
	}
	if !reflect.DeepEqual(repo.lastFilters.Keys(), []string{"processed", "target_level", "target_id"}) {
		t.Fatalf("filters = %v", repo.lastFilters.Keys())
	}
	if v, _ := repo.lastFilters.Get("processed"); v != false {
		t.Fatalf("processed = %v", v)
	}
	if v, _ := repo.lastFilters.Get("target_level"); v != "project" {
		t.Fatalf("target_level = %v", v)
	}
	if v, _ := repo.lastFilters.Get("target_id"); v != "proj_123" {
		t.Fatalf("target_id = %v", v)
	}
}

func TestContextDelegationService_GetQueueStatusShape(t *testing.T) {
	repo := &zpCtxDelFakeRepository{}
	svc := zpCtxDelNewContextDelegationService(repo, nil)

	repo.delegations = []*entities.OrderedMap[any]{zpCtxDelOM("id", "1"), zpCtxDelOM("id", "2")}
	healthy := svc.GetQueueStatus(context.Background())
	if !reflect.DeepEqual(healthy.Keys(), []string{"status", "pending_delegations", "queue_healthy"}) {
		t.Fatalf("healthy keys = %v", healthy.Keys())
	}
	if v, _ := healthy.Get("status"); v != "healthy" {
		t.Fatalf("status = %v", v)
	}
	if v, _ := healthy.Get("pending_delegations"); v != 2 {
		t.Fatalf("pending = %v", v)
	}
	if v, _ := healthy.Get("queue_healthy"); v != true {
		t.Fatalf("queue_healthy = %v", v)
	}

	unhealthy := make([]*entities.OrderedMap[any], 150)
	for i := range unhealthy {
		unhealthy[i] = zpCtxDelOM("id", i)
	}
	repo.delegations = unhealthy
	got := svc.GetQueueStatus(context.Background())
	if v, _ := got.Get("pending_delegations"); v != 150 {
		t.Fatalf("pending = %v, want 150", v)
	}
	if v, _ := got.Get("queue_healthy"); v != false {
		t.Fatalf("queue_healthy = %v, want false", v)
	}
}

func TestContextDelegationService_ApproveDelegation(t *testing.T) {
	repo := &zpCtxDelFakeRepository{}
	svc := zpCtxDelNewContextDelegationService(repo, nil)

	notFound := svc.ApproveDelegation(context.Background(), "nonexistent", "admin")
	if success, _ := notFound.Get("success"); success != false {
		t.Fatalf("success = %v", success)
	}
	if errText, _ := notFound.Get("error"); errText != "Delegation not found" {
		t.Fatalf("error = %v", errText)
	}

	repo.delegation = zpCtxDelOM("processed", true)
	already := svc.ApproveDelegation(context.Background(), "del_1", "admin")
	if errText, _ := already.Get("error"); errText != "Delegation already processed" {
		t.Fatalf("error = %v", errText)
	}
}

func TestContextDelegationService_MarkDelegationImplemented(t *testing.T) {
	repo := &zpCtxDelFakeRepository{}
	svc := zpCtxDelNewContextDelegationService(repo, nil)

	implementationData := zpCtxDelOM(
		"implemented_at", "2020-01-01T00:00:00+00:00",
		"implementation_details", zpCtxDelOM(
			"merged_fields", []any{"field1", "field2"},
			"target_context_updated", true,
		),
	)
	if !svc.markDelegationImplemented(context.Background(), "del_123", implementationData) {
		t.Fatal("markDelegationImplemented returned false")
	}
	if !reflect.DeepEqual(repo.lastUpdate.Keys(), []string{"processed", "approved", "processed_at", "implementation_details"}) {
		t.Fatalf("update keys = %v", repo.lastUpdate.Keys())
	}
	details, _ := repo.lastUpdate.Get("implementation_details")
	want := `{"merged_fields": ["field1", "field2"], "target_context_updated": true}`
	if details != want {
		t.Fatalf("implementation_details = %q, want %q", details, want)
	}
}

func TestContextDelegationService_DelegateContextQueuesForReview(t *testing.T) {
	repo := &zpCtxDelFakeRepository{
		storeID:        "del_9",
		projectContext: zpCtxDelOM("existing", "value"),
	}
	svc := zpCtxDelNewContextDelegationService(repo, nil)

	request := zpCtxDelOM(
		"source_level", "task",
		"source_id", "task_123",
		"target_level", "project",
		"data", zpCtxDelOM("pattern", "test"),
		"reason", "Test delegation",
	)
	result := svc.DelegateContext(context.Background(), request)

	if success, _ := result.Get("success"); success != true {
		t.Fatalf("success = %v", success)
	}
	if id, _ := result.Get("delegation_id"); id != "del_9" {
		t.Fatalf("delegation_id = %v", id)
	}
	if auto, _ := result.Get("auto_approved"); auto != false {
		t.Fatalf("auto_approved = %v", auto)
	}
	queued, _ := result.Get("result")
	queuedMap := queued.(*entities.OrderedMap[any])
	if v, _ := queuedMap.Get("queued"); v != true {
		t.Fatalf("queued = %v", v)
	}
	if v, _ := queuedMap.Get("estimated_review_time"); v != "24 hours" {
		t.Fatalf("estimated_review_time = %v", v)
	}
}

func TestContextDelegationService_EvaluatePatternTriggers(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	changes := zpCtxDelOM("security", "vulnerability discovered")
	patterns := zpCtxDelOM("security_discovery", "global")
	requests, err := svc.evaluatePatternTriggers(context.Background(), "task_123", changes, patterns)
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if len(requests) != 1 {
		t.Fatalf("len = %d", len(requests))
	}
	got := requests[0]
	if got.SourceLevel != "task" || got.TargetLevel != "global" || got.TargetID != "global_singleton" {
		t.Fatalf("request = %+v", got)
	}
	if got.TriggerType != "auto_pattern" || got.ConfidenceScore == nil || *got.ConfidenceScore != 0.8 {
		t.Fatalf("trigger/confidence = %q / %v", got.TriggerType, got.ConfidenceScore)
	}
}

func TestContextDelegationService_EvaluateProjectToGlobalTriggers(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	changes := zpCtxDelOM("security_policy", "new authentication policy", "coding_standard", "updated")
	requests := svc.evaluateProjectToGlobalTriggers(context.Background(), "proj_123", entities.NewOrderedMap[any](), changes)
	if len(requests) != 2 {
		t.Fatalf("len = %d, want 2", len(requests))
	}
	for _, request := range requests {
		if request.SourceLevel != "project" || request.TargetLevel != "global" || request.TriggerType != "auto_pattern" {
			t.Fatalf("request = %+v", request)
		}
		if request.ConfidenceScore == nil || *request.ConfidenceScore != 0.85 {
			t.Fatalf("confidence = %v", request.ConfidenceScore)
		}
	}
}

func TestContextDelegationService_CalculateAIDelegationConfidence(t *testing.T) {
	svc := zpCtxDelNewContextDelegationService(nil, nil)

	changes := zpCtxDelOM(
		"security", "documented vulnerability with tested fix",
		"validation", "pattern validated with best practice implementation",
	)
	if got := svc.calculateAIDelegationConfidence(changes, "security_insight"); got != 1.0 {
		t.Fatalf("confidence = %v, want 1.0", got)
	}
	if got := svc.calculateAIDelegationConfidence(zpCtxDelOM("routine", "simple update"), "unknown_pattern"); got != 0.5 {
		t.Fatalf("unknown pattern confidence = %v, want 0.5", got)
	}
}
