package services

import (
	"context"
	"errors"
	"fmt"
	"math"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DelegationRequest mirrors the Python dataclass
// context_delegation_service.DelegationRequest. The dataclass defaults for the
// optional fields are trigger_type="manual" and confidence_score=None; use
// zpCtxDelNewDelegationRequest to build one with those defaults.
type DelegationRequest struct {
	SourceLevel     string
	SourceID        string
	TargetLevel     string
	TargetID        string
	DelegatedData   *entities.OrderedMap[any]
	Reason          string
	TriggerType     string
	ConfidenceScore *float64
}

// DelegationResult mirrors the Python dataclass DelegationResult. The Python
// module defines it but never uses it; it is kept for shape parity. Zero values
// match the dataclass defaults: processed=False, approved=None,
// error_message=None, impact_assessment=None.
type DelegationResult struct {
	Success          bool
	DelegationID     string
	Processed        bool
	Approved         *bool
	ErrorMessage     *string
	ImpactAssessment *entities.OrderedMap[any]
}

// zpCtxDelRepository is the minimal repository surface the Python service uses
// through `self.repository`. Python's methods are async and the arguments are:
//
//	get_delegations(filters: dict) -> list[dict]
//	get_delegation(delegation_id: str) -> dict | None
//	update_delegation(delegation_id: str, data: dict) -> bool
//	get_global_context(context_id) / get_project_context(context_id) /
//	get_task_context(context_id) -> dict | None
//	update_global_context(context_id, context_data) /
//	update_project_context(context_id, context_data) /
//	update_task_context(context_id, context_data) -> bool
//	store_delegation(delegation_data: dict) -> str  (the delegation id)
//
// A missing delegation is (nil, nil). Dict arguments/returns are insertion
// ordered because the Python dict order is observable (e.g. update payloads).
type zpCtxDelRepository interface {
	GetDelegations(ctx context.Context, filters *entities.OrderedMap[any]) ([]*entities.OrderedMap[any], error)
	GetDelegation(ctx context.Context, delegationID string) (*entities.OrderedMap[any], error)
	UpdateDelegation(ctx context.Context, delegationID string, updates *entities.OrderedMap[any]) (bool, error)
	GetGlobalContext(ctx context.Context, contextID string) (*entities.OrderedMap[any], error)
	GetProjectContext(ctx context.Context, contextID string) (*entities.OrderedMap[any], error)
	GetTaskContext(ctx context.Context, contextID string) (*entities.OrderedMap[any], error)
	UpdateGlobalContext(ctx context.Context, contextID string, contextData *entities.OrderedMap[any]) (bool, error)
	UpdateProjectContext(ctx context.Context, contextID string, contextData *entities.OrderedMap[any]) (bool, error)
	UpdateTaskContext(ctx context.Context, contextID string, contextData *entities.OrderedMap[any]) (bool, error)
	StoreDelegation(ctx context.Context, delegationData *entities.OrderedMap[any]) (string, error)
}

// ContextDelegationService ports
// task_management/application/services/context_delegation_service.py.
//
// Unportable branches: delegate_context consults the asyncio event loop and
// returns a mock pending response when it is already running. Go has no event
// loop, so DelegateContext always runs ProcessDelegation (the Python
// not-running branch). The `_queue_for_review` and `get_queue_status` except
// branches are likewise unreachable in Go because their only error source is
// already caught by the callee. The shallow-copy + list.append quirk of
// `_merge_*_context` (Python mutates the caller's delegated_insights list in
// place) cannot be reproduced with Go slices.
type ContextDelegationService struct {
	repository zpCtxDelRepository
	userID     *string
}

// zpCtxDelNewContextDelegationService mirrors __init__(repository=None, user_id=None).
func zpCtxDelNewContextDelegationService(repository zpCtxDelRepository, userID *string) *ContextDelegationService {
	return &ContextDelegationService{repository: repository, userID: userID}
}

// WithUser mirrors with_user(user_id): a new instance sharing the repository.
func (s *ContextDelegationService) WithUser(userID string) *ContextDelegationService {
	return zpCtxDelNewContextDelegationService(s.repository, &userID)
}

// getUserScopedRepository mirrors _get_user_scoped_repository. The Python
// `hasattr(repository, "with_user")` branch delegates to the shared
// serviceUserScopedRepository helper; the `elif hasattr(repository, "user_id")`
// reconstruction branch has no Go equivalent (zpCtxDelRepository exposes no
// session/user_id) and is omitted, so the repository is returned unchanged.
func (s *ContextDelegationService) getUserScopedRepository(repository zpCtxDelRepository) zpCtxDelRepository {
	if scoped, ok := serviceUserScopedRepository(repository, s.userID).(zpCtxDelRepository); ok {
		return scoped
	}
	return repository
}

// zpCtxDelNewDelegationRequest applies the Python dataclass defaults for the
// optional fields (trigger_type="manual", confidence_score=None).
func zpCtxDelNewDelegationRequest(sourceLevel, sourceID, targetLevel, targetID string, delegatedData *entities.OrderedMap[any], reason string) *DelegationRequest {
	return &DelegationRequest{
		SourceLevel:     sourceLevel,
		SourceID:        sourceID,
		TargetLevel:     targetLevel,
		TargetID:        targetID,
		DelegatedData:   delegatedData,
		Reason:          reason,
		TriggerType:     "manual",
		ConfidenceScore: nil,
	}
}

// ===============================================
// MAIN DELEGATION PROCESSING
// ===============================================

// DelegateContext mirrors the synchronous delegate_context wrapper. The Python
// running-event-loop mock response branch is unportable; this always runs
// ProcessDelegation with trigger_type="manual" and confidence_score=None.
func (s *ContextDelegationService) DelegateContext(ctx context.Context, request *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if request == nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "'NoneType' object has no attribute 'get'")
		out.Set("status", "failed")
		return out
	}

	sourceLevel := zpCtxDelString(zpCtxDelMapGet(request, "source_level"))
	sourceID := zpCtxDelString(zpCtxDelMapGet(request, "source_id"))
	targetLevel := zpCtxDelString(zpCtxDelMapGet(request, "target_level"))

	var data *entities.OrderedMap[any]
	if raw, ok := request.Get("data"); ok {
		data, _ = zpCtxDelAsDict(raw)
	} else {
		data = entities.NewOrderedMap[any]()
	}

	reason := "Manual delegation"
	if raw, ok := request.Get("reason"); ok {
		reason = zpCtxDelString(raw)
	}

	targetID := sourceID
	if targetLevel == "global" {
		targetID = "global_singleton"
	}

	return s.ProcessDelegation(ctx, sourceLevel, sourceID, targetLevel, targetID, data, reason, "manual", nil)
}

// ProcessDelegation mirrors the async process_delegation.
func (s *ContextDelegationService) ProcessDelegation(ctx context.Context, sourceLevel, sourceID, targetLevel, targetID string, delegatedData *entities.OrderedMap[any], reason, triggerType string, confidenceScore *float64) *entities.OrderedMap[any] {
	validationResult := s.validateDelegationRequest(sourceLevel, sourceID, targetLevel, targetID, delegatedData)

	valid, _ := validationResult.Get("valid")
	if !value_objects.PyTruthy(valid) {
		validationErrors, _ := validationResult.Get("errors")
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Invalid delegation request: "+value_objects.PyRepr(validationErrors))
		out.Set("delegation_id", nil)
		return out
	}

	delegationRequest := zpCtxDelNewDelegationRequest(sourceLevel, sourceID, targetLevel, targetID, delegatedData, reason)
	delegationRequest.TriggerType = triggerType
	delegationRequest.ConfidenceScore = confidenceScore

	delegationID, err := s.storeDelegationRequest(ctx, delegationRequest)
	if err != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", err.Error())
		out.Set("delegation_id", nil)
		return out
	}

	impactAssessment := s.assessDelegationImpact(ctx, delegationRequest)
	autoApprove := s.shouldAutoApprove(ctx, delegationRequest, impactAssessment)

	var result *entities.OrderedMap[any]
	if autoApprove {
		result = s.executeDelegation(ctx, delegationID, delegationRequest, impactAssessment)
	} else {
		result = s.queueForReview(ctx, delegationID, delegationRequest, impactAssessment)
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("delegation_id", delegationID)
	out.Set("auto_approved", autoApprove)
	out.Set("impact_assessment", impactAssessment)
	out.Set("result", result)
	return out
}

// ===============================================
// AUTOMATIC DELEGATION DETECTION
// ===============================================

// EvaluateAutoDelegationTriggers mirrors the async
// evaluate_auto_delegation_triggers. Any error in Python is swallowed and [] is
// returned, so this returns an empty slice instead of an error.
func (s *ContextDelegationService) EvaluateAutoDelegationTriggers(ctx context.Context, contextLevel, contextID string, contextData, changes *entities.OrderedMap[any]) []*DelegationRequest {
	delegationRequests := []*DelegationRequest{}

	switch contextLevel {
	case "task":
		if contextData == nil {
			return delegationRequests
		}
		delegationTriggers := entities.NewOrderedMap[any]()
		if raw, ok := contextData.Get("delegation_triggers"); ok {
			triggers, ok := zpCtxDelAsDict(raw)
			if !ok {
				return delegationRequests
			}
			delegationTriggers = triggers
		}

		patterns := entities.NewOrderedMap[any]()
		if raw, ok := delegationTriggers.Get("patterns"); ok {
			p, ok := zpCtxDelAsDict(raw)
			if !ok {
				return delegationRequests
			}
			patterns = p
		}
		patternRequests, err := s.evaluatePatternTriggers(ctx, contextID, changes, patterns)
		if err != nil {
			return delegationRequests
		}
		delegationRequests = append(delegationRequests, patternRequests...)

		thresholds := entities.NewOrderedMap[any]()
		if raw, ok := delegationTriggers.Get("thresholds"); ok {
			t, ok := zpCtxDelAsDict(raw)
			if !ok {
				return delegationRequests
			}
			thresholds = t
		}
		thresholdRequests, err := s.evaluateThresholdTriggers(ctx, contextID, contextData, changes, thresholds)
		if err != nil {
			return delegationRequests
		}
		delegationRequests = append(delegationRequests, thresholdRequests...)

		delegationRequests = append(delegationRequests, s.evaluateAITriggers(ctx, contextID, contextData, changes)...)

	case "project":
		delegationRequests = append(delegationRequests, s.evaluateProjectToGlobalTriggers(ctx, contextID, contextData, changes)...)
	}

	return delegationRequests
}

func (s *ContextDelegationService) evaluatePatternTriggers(ctx context.Context, contextID string, changes, patterns *entities.OrderedMap[any]) ([]*DelegationRequest, error) {
	requests := []*DelegationRequest{}
	if patterns == nil {
		return nil, errors.New("'NoneType' object has no attribute 'items'")
	}

	for _, pattern := range patterns.Keys() {
		matched, err := s.matchesPattern(changes, pattern)
		if err != nil {
			return nil, err
		}
		if !matched {
			continue
		}
		targetVal, _ := patterns.Get(pattern)
		targetLevel := zpCtxDelString(targetVal)
		targetID := s.resolveTargetID(ctx, contextID, "task", targetLevel)

		request := zpCtxDelNewDelegationRequest("task", contextID, targetLevel, targetID, s.extractPatternData(changes, pattern), "Auto-delegation: "+pattern+" pattern detected")
		request.TriggerType = "auto_pattern"
		request.ConfidenceScore = zpCtxDelFloatPtr(0.8)
		requests = append(requests, request)
	}
	return requests, nil
}

func (s *ContextDelegationService) evaluateThresholdTriggers(ctx context.Context, contextID string, contextData, changes, thresholds *entities.OrderedMap[any]) ([]*DelegationRequest, error) {
	requests := []*DelegationRequest{}
	if thresholds == nil {
		return nil, errors.New("'NoneType' object has no attribute 'items'")
	}

	for _, thresholdName := range thresholds.Keys() {
		configVal, _ := thresholds.Get(thresholdName)
		thresholdConfig, _ := zpCtxDelAsDict(configVal)

		if !s.exceedsThreshold(contextData, changes, thresholdName, thresholdConfig) {
			continue
		}

		targetLevel := "project"
		if thresholdConfig != nil {
			if raw, ok := thresholdConfig.Get("delegate_to"); ok {
				targetLevel = zpCtxDelString(raw)
			}
		}
		targetID := s.resolveTargetID(ctx, contextID, "task", targetLevel)
		thresholdData, err := s.extractThresholdData(contextData, thresholdName)
		if err != nil {
			return nil, err
		}

		request := zpCtxDelNewDelegationRequest("task", contextID, targetLevel, targetID, thresholdData, "Auto-delegation: "+thresholdName+" threshold exceeded")
		request.TriggerType = "auto_threshold"
		request.ConfidenceScore = zpCtxDelFloatPtr(0.9)
		requests = append(requests, request)
	}
	return requests, nil
}

func (s *ContextDelegationService) evaluateAITriggers(ctx context.Context, contextID string, contextData, changes *entities.OrderedMap[any]) []*DelegationRequest {
	requests := []*DelegationRequest{}
	_ = contextData

	aiPatterns := []struct {
		pattern       string
		targetLevel   string
		minConfidence float64
	}{
		{"reusable_component", "project", 0.85},
		{"security_insight", "global", 0.95},
		{"performance_optimization", "project", 0.80},
		{"architectural_decision", "global", 0.90},
	}

	for _, aiPattern := range aiPatterns {
		confidence := s.calculateAIDelegationConfidence(changes, aiPattern.pattern)
		if confidence < aiPattern.minConfidence {
			continue
		}
		targetID := s.resolveTargetID(ctx, contextID, "task", aiPattern.targetLevel)
		reason := fmt.Sprintf("AI-initiated delegation: %s (confidence: %.2f)", aiPattern.pattern, confidence)

		request := zpCtxDelNewDelegationRequest("task", contextID, aiPattern.targetLevel, targetID, s.extractAIPatternData(changes, aiPattern.pattern), reason)
		request.TriggerType = "ai_initiated"
		request.ConfidenceScore = zpCtxDelFloatPtr(confidence)
		requests = append(requests, request)
	}
	return requests
}

// ===============================================
// DELEGATION EXECUTION
// ===============================================

func (s *ContextDelegationService) executeDelegation(ctx context.Context, delegationID string, request *DelegationRequest, impactAssessment *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	_ = impactAssessment

	targetContext := s.getContext(ctx, request.TargetLevel, request.TargetID)
	updatedContext, err := s.mergeDelegatedData(ctx, targetContext, request.DelegatedData, request)
	if err != nil {
		s.markDelegationFailed(ctx, delegationID, err.Error())
		return zpCtxDelExecutionFailure(delegationID, err.Error())
	}

	// Python ignores the return value of _update_context (the bool is discarded).
	_ = s.updateContext(ctx, request.TargetLevel, request.TargetID, updatedContext)

	if request.DelegatedData == nil {
		err := errors.New("'NoneType' object has no attribute 'keys'")
		s.markDelegationFailed(ctx, delegationID, err.Error())
		return zpCtxDelExecutionFailure(delegationID, err.Error())
	}

	mergedFields := []any{}
	for _, field := range request.DelegatedData.Keys() {
		mergedFields = append(mergedFields, field)
	}
	implementationDetails := entities.NewOrderedMap[any]()
	implementationDetails.Set("merged_fields", mergedFields)
	implementationDetails.Set("target_context_updated", true)

	implementationData := entities.NewOrderedMap[any]()
	implementationData.Set("implemented_at", value_objects.IsoFormat(time.Now().UTC()))
	implementationData.Set("implementation_details", implementationDetails)
	// Python ignores this return value too; only exceptions matter, and
	// markDelegationImplemented catches its own.
	_ = s.markDelegationImplemented(ctx, delegationID, implementationData)

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("delegation_id", delegationID)
	out.Set("implemented", true)
	out.Set("target_updated", true)
	return out
}

// zpCtxDelExecutionFailure is the Python
// {"success": False, "delegation_id": ..., "error": ...} shape.
func zpCtxDelExecutionFailure(delegationID, message string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("delegation_id", delegationID)
	out.Set("error", message)
	return out
}

func (s *ContextDelegationService) mergeDelegatedData(ctx context.Context, targetContext, delegatedData *entities.OrderedMap[any], request *DelegationRequest) (*entities.OrderedMap[any], error) {
	if targetContext == nil {
		return nil, errors.New("'NoneType' object has no attribute 'copy'")
	}
	updatedContext := targetContext.Copy()

	switch request.TargetLevel {
	case "global":
		return s.mergeToGlobalContext(updatedContext, delegatedData, request)
	case "project":
		return s.mergeToProjectContext(updatedContext, delegatedData, request)
	}
	return updatedContext, nil
}

func (s *ContextDelegationService) mergeToGlobalContext(globalContext, delegatedData *entities.OrderedMap[any], request *DelegationRequest) (*entities.OrderedMap[any], error) {
	updated := globalContext.Copy()
	reason := value_objects.PyLower(request.Reason)

	switch {
	case strings.Contains(reason, "security"):
		base, extra, err := zpCtxDelNestedPair(updated, "security_policies", delegatedData, "security_insights")
		if err != nil {
			return nil, err
		}
		merged, err := zpCtxDelDictUpdate(base, extra)
		if err != nil {
			return nil, err
		}
		updated.Set("security_policies", merged)
	case strings.Contains(reason, "coding") || strings.Contains(reason, "standard"):
		base, extra, err := zpCtxDelNestedPair(updated, "coding_standards", delegatedData, "coding_patterns")
		if err != nil {
			return nil, err
		}
		merged, err := zpCtxDelDictUpdate(base, extra)
		if err != nil {
			return nil, err
		}
		updated.Set("coding_standards", merged)
	case strings.Contains(reason, "workflow"):
		base, extra, err := zpCtxDelNestedPair(updated, "workflow_templates", delegatedData, "workflow_patterns")
		if err != nil {
			return nil, err
		}
		merged, err := zpCtxDelDictUpdate(base, extra)
		if err != nil {
			return nil, err
		}
		updated.Set("workflow_templates", merged)
	}

	if err := zpCtxDelAppendInsight(updated, request, delegatedData); err != nil {
		return nil, err
	}
	return updated, nil
}

func (s *ContextDelegationService) mergeToProjectContext(projectContext, delegatedData *entities.OrderedMap[any], request *DelegationRequest) (*entities.OrderedMap[any], error) {
	updated := projectContext.Copy()
	reason := value_objects.PyLower(request.Reason)

	switch {
	case strings.Contains(reason, "team"):
		base, extra, err := zpCtxDelNestedPair(updated, "team_preferences", delegatedData, "team_insights")
		if err != nil {
			return nil, err
		}
		merged, err := zpCtxDelDictUpdate(base, extra)
		if err != nil {
			return nil, err
		}
		updated.Set("team_preferences", merged)
	case strings.Contains(reason, "technology"):
		base, extra, err := zpCtxDelNestedPair(updated, "technology_stack", delegatedData, "tech_insights")
		if err != nil {
			return nil, err
		}
		merged, err := zpCtxDelDictUpdate(base, extra)
		if err != nil {
			return nil, err
		}
		updated.Set("technology_stack", merged)
	case strings.Contains(reason, "workflow"):
		base, extra, err := zpCtxDelNestedPair(updated, "project_workflow", delegatedData, "workflow_insights")
		if err != nil {
			return nil, err
		}
		merged, err := zpCtxDelDictUpdate(base, extra)
		if err != nil {
			return nil, err
		}
		updated.Set("project_workflow", merged)
	}

	if err := zpCtxDelAppendInsight(updated, request, delegatedData); err != nil {
		return nil, err
	}
	return updated, nil
}

// zpCtxDelAppendInsight implements the shared tail of _merge_to_*_context: it
// appends one delegation-metadata dict to `delegated_insights` (defaulting to an
// empty list) and stores it back. Python mutates the existing list in place
// (the shallow copy aliases it); Go appends into a new slice.
func zpCtxDelAppendInsight(updated *entities.OrderedMap[any], request *DelegationRequest, delegatedData *entities.OrderedMap[any]) error {
	var list []any
	if existing, ok := updated.Get("delegated_insights"); ok {
		l, ok := existing.([]any)
		if !ok {
			return errors.New("'NoneType' object has no attribute 'append'")
		}
		list = l
	} else {
		list = []any{}
	}

	item := entities.NewOrderedMap[any]()
	item.Set("delegation_id", request.SourceID)
	item.Set("source", request.SourceLevel+":"+request.SourceID)
	item.Set("data", delegatedData)
	item.Set("reason", request.Reason)
	item.Set("delegated_at", value_objects.IsoFormat(time.Now().UTC()))

	list = append(list, item)
	updated.Set("delegated_insights", list)
	return nil
}

// ===============================================
// DELEGATION QUEUE MANAGEMENT
// ===============================================

// GetPendingDelegations mirrors get_pending_delegations. Python swallows any
// exception and returns [], so this returns an empty slice on error.
func (s *ContextDelegationService) GetPendingDelegations(ctx context.Context, targetLevel, targetID *string) []*entities.OrderedMap[any] {
	filters := entities.NewOrderedMap[any]()
	filters.Set("processed", false)
	if targetLevel != nil && *targetLevel != "" {
		filters.Set("target_level", *targetLevel)
	}
	if targetID != nil && *targetID != "" {
		filters.Set("target_id", *targetID)
	}

	if s.repository == nil {
		return []*entities.OrderedMap[any]{}
	}
	delegations, err := s.repository.GetDelegations(ctx, filters)
	if err != nil {
		return []*entities.OrderedMap[any]{}
	}
	return delegations
}

// ApproveDelegation mirrors approve_delegation.
func (s *ContextDelegationService) ApproveDelegation(ctx context.Context, delegationID, approver string) *entities.OrderedMap[any] {
	if s.repository == nil {
		return zpCtxDelErrorResult("'NoneType' object has no attribute 'get_delegation'")
	}

	delegation, err := s.repository.GetDelegation(ctx, delegationID)
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}
	if delegation == nil {
		return zpCtxDelErrorResult("Delegation not found")
	}
	if processed, ok := delegation.Get("processed"); ok && value_objects.PyTruthy(processed) {
		return zpCtxDelErrorResult("Delegation already processed")
	}

	sourceLevel, err := zpCtxDelRequiredString(delegation, "source_level")
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}
	sourceID, err := zpCtxDelRequiredString(delegation, "source_id")
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}
	targetLevel, err := zpCtxDelRequiredString(delegation, "target_level")
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}
	targetID, err := zpCtxDelRequiredString(delegation, "target_id")
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}

	var delegatedData *entities.OrderedMap[any]
	if raw, err := zpCtxDelRequired(delegation, "delegated_data"); err != nil {
		return zpCtxDelErrorResult(err.Error())
	} else {
		delegatedData, _ = zpCtxDelAsDict(raw)
	}

	reason, err := zpCtxDelRequiredString(delegation, "delegation_reason")
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}
	triggerType, err := zpCtxDelRequiredString(delegation, "trigger_type")
	if err != nil {
		return zpCtxDelErrorResult(err.Error())
	}

	var confidenceScore *float64
	if raw, ok := delegation.Get("confidence_score"); ok {
		if f, ok := value_objects.PyFloat(raw); ok {
			confidenceScore = &f
		}
	}

	request := zpCtxDelNewDelegationRequest(sourceLevel, sourceID, targetLevel, targetID, delegatedData, reason)
	request.TriggerType = triggerType
	request.ConfidenceScore = confidenceScore

	impactAssessment := s.assessDelegationImpact(ctx, request)
	result := s.executeDelegation(ctx, delegationID, request, impactAssessment)

	update := entities.NewOrderedMap[any]()
	update.Set("approved", true)
	update.Set("processed", true)
	update.Set("processed_at", value_objects.IsoFormat(time.Now().UTC()))
	update.Set("processed_by", approver)
	if _, err := s.repository.UpdateDelegation(ctx, delegationID, update); err != nil {
		return zpCtxDelErrorResult(err.Error())
	}

	return result
}

// RejectDelegation mirrors reject_delegation.
func (s *ContextDelegationService) RejectDelegation(ctx context.Context, delegationID, reason, rejector string) *entities.OrderedMap[any] {
	if s.repository == nil {
		return zpCtxDelErrorResult("'NoneType' object has no attribute 'update_delegation'")
	}

	update := entities.NewOrderedMap[any]()
	update.Set("approved", false)
	update.Set("processed", true)
	update.Set("processed_at", value_objects.IsoFormat(time.Now().UTC()))
	update.Set("processed_by", rejector)
	update.Set("rejected_reason", reason)
	if _, err := s.repository.UpdateDelegation(ctx, delegationID, update); err != nil {
		return zpCtxDelErrorResult(err.Error())
	}

	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("delegation_id", delegationID)
	out.Set("rejected", true)
	return out
}

// ===============================================
// UTILITY METHODS
// ===============================================

func (s *ContextDelegationService) validateDelegationRequest(sourceLevel, sourceID, targetLevel, targetID string, delegatedData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	_ = sourceID
	_ = targetID

	validationErrors := []any{}
	validLevels := []string{"task", "project", "global"}
	if !zpCtxDelContains(validLevels, sourceLevel) {
		validationErrors = append(validationErrors, "Invalid source level: "+sourceLevel)
	}
	if !zpCtxDelContains(validLevels, targetLevel) {
		validationErrors = append(validationErrors, "Invalid target level: "+targetLevel)
	}

	levelHierarchy := map[string]int{"task": 0, "project": 1, "global": 2}
	sourceRank, sourceOK := levelHierarchy[sourceLevel]
	targetRank, targetOK := levelHierarchy[targetLevel]
	if sourceOK && targetOK && sourceRank >= targetRank {
		validationErrors = append(validationErrors, fmt.Sprintf("Cannot delegate from %s to %s - must delegate upward", sourceLevel, targetLevel))
	}

	if delegatedData == nil || delegatedData.Len() == 0 {
		validationErrors = append(validationErrors, "No data provided for delegation")
	}

	out := entities.NewOrderedMap[any]()
	out.Set("valid", len(validationErrors) == 0)
	out.Set("errors", validationErrors)
	return out
}

// matchesPattern mirrors _matches_pattern. The second return value is the
// Python exception that would escape the lambda (only a None `changes`).
func (s *ContextDelegationService) matchesPattern(changes *entities.OrderedMap[any], pattern string) (bool, error) {
	if changes == nil {
		return false, errors.New("'NoneType' object has no attribute 'values'")
	}
	values := changes.Values()

	anyValueContains := func(needles ...string) bool {
		for _, v := range values {
			text := zpCtxDelLower(v)
			for _, needle := range needles {
				if strings.Contains(text, needle) {
					return true
				}
			}
		}
		return false
	}

	switch pattern {
	case "security_discovery":
		return anyValueContains("security", "vulnerability"), nil
	case "team_improvement":
		return anyValueContains("team", "process", "workflow"), nil
	case "reusable_utility":
		return anyValueContains("reusable", "utility", "helper"), nil
	case "performance_optimization":
		return anyValueContains("performance", "optimization", "speed"), nil
	case "architectural_insight":
		return anyValueContains("architecture", "design", "pattern"), nil
	}
	return false, nil
}

func (s *ContextDelegationService) extractPatternData(changes *entities.OrderedMap[any], pattern string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("pattern", pattern)
	out.Set("extracted_data", changes)
	out.Set("extraction_method", "pattern_matching")
	out.Set("extraction_timestamp", value_objects.IsoFormat(time.Now().UTC()))
	return out
}

// GetQueueStatus mirrors get_queue_status.
func (s *ContextDelegationService) GetQueueStatus(ctx context.Context) *entities.OrderedMap[any] {
	pendingCount := len(s.GetPendingDelegations(ctx, nil, nil))

	out := entities.NewOrderedMap[any]()
	out.Set("status", "healthy")
	out.Set("pending_delegations", pendingCount)
	out.Set("queue_healthy", pendingCount < 100)
	return out
}

// ===============================================
// MISSING UTILITY METHODS IMPLEMENTATION
// ===============================================

// resolveTargetID mirrors _resolve_target_id. _get_context swallows its own
// errors, so no exception path remains.
func (s *ContextDelegationService) resolveTargetID(ctx context.Context, sourceID, sourceLevel, targetLevel string) string {
	if targetLevel == "global" {
		return "global_singleton"
	} else if targetLevel == "project" {
		if sourceLevel == "task" {
			taskContext := s.getContext(ctx, "task", sourceID)
			if taskContext != nil {
				if raw, ok := taskContext.Get("parent_project_id"); ok {
					return zpCtxDelString(raw)
				}
			}
			return "agenthub"
		}
		return sourceID
	}
	return sourceID
}

// getContext mirrors _get_context: any repository error becomes nil.
func (s *ContextDelegationService) getContext(ctx context.Context, level, contextID string) *entities.OrderedMap[any] {
	if s.repository == nil {
		return nil
	}
	switch level {
	case "global":
		v, err := s.repository.GetGlobalContext(ctx, contextID)
		if err != nil {
			return nil
		}
		return v
	case "project":
		v, err := s.repository.GetProjectContext(ctx, contextID)
		if err != nil {
			return nil
		}
		return v
	case "task":
		v, err := s.repository.GetTaskContext(ctx, contextID)
		if err != nil {
			return nil
		}
		return v
	}
	return nil
}

// updateContext mirrors _update_context: any repository error becomes false.
func (s *ContextDelegationService) updateContext(ctx context.Context, level, contextID string, contextData *entities.OrderedMap[any]) bool {
	if s.repository == nil {
		return false
	}
	switch level {
	case "global":
		ok, err := s.repository.UpdateGlobalContext(ctx, contextID, contextData)
		if err != nil {
			return false
		}
		return ok
	case "project":
		ok, err := s.repository.UpdateProjectContext(ctx, contextID, contextData)
		if err != nil {
			return false
		}
		return ok
	case "task":
		ok, err := s.repository.UpdateTaskContext(ctx, contextID, contextData)
		if err != nil {
			return false
		}
		return ok
	}
	return false
}

// storeDelegationRequest mirrors _store_delegation_request; the Python method
// re-raises, so the error is returned to ProcessDelegation.
func (s *ContextDelegationService) storeDelegationRequest(ctx context.Context, request *DelegationRequest) (string, error) {
	delegationData := entities.NewOrderedMap[any]()
	delegationData.Set("source_level", request.SourceLevel)
	delegationData.Set("source_id", request.SourceID)
	delegationData.Set("target_level", request.TargetLevel)
	delegationData.Set("target_id", request.TargetID)
	delegationData.Set("delegated_data", request.DelegatedData)
	delegationData.Set("reason", request.Reason)
	delegationData.Set("trigger_type", request.TriggerType)
	delegationData.Set("auto_delegated", strings.HasPrefix(request.TriggerType, "auto"))
	if request.ConfidenceScore != nil {
		delegationData.Set("confidence_score", *request.ConfidenceScore)
	} else {
		delegationData.Set("confidence_score", nil)
	}

	if s.repository == nil {
		return "", errors.New("'NoneType' object has no attribute 'store_delegation'")
	}
	return s.repository.StoreDelegation(ctx, delegationData)
}

// assessDelegationImpact mirrors _assess_delegation_impact.
func (s *ContextDelegationService) assessDelegationImpact(ctx context.Context, request *DelegationRequest) *entities.OrderedMap[any] {
	_ = ctx

	impactScore := 0
	riskFactors := []any{}
	benefits := []any{}

	if request.TriggerType == "manual" {
		impactScore += 30
		benefits = append(benefits, "Manual review by human or AI")
	} else if strings.HasPrefix(request.TriggerType, "auto") {
		impactScore += 20
		benefits = append(benefits, "Automated pattern detection")
	}

	if request.TargetLevel == "global" {
		impactScore += 50
		benefits = append(benefits, "Organization-wide knowledge sharing")
		riskFactors = append(riskFactors, "High impact on all projects")
	} else if request.TargetLevel == "project" {
		impactScore += 30
		benefits = append(benefits, "Project-level knowledge sharing")
		riskFactors = append(riskFactors, "Medium impact on project team")
	}

	if request.ConfidenceScore != nil && *request.ConfidenceScore != 0 {
		switch {
		case *request.ConfidenceScore >= 0.8:
			impactScore += 20
			benefits = append(benefits, "High confidence in delegation value")
		case *request.ConfidenceScore < 0.5:
			impactScore -= 20
			riskFactors = append(riskFactors, "Low confidence in delegation value")
		}
	}

	recommendation := "manual_review"
	if impactScore >= 70 {
		recommendation = "auto_approve"
	}

	out := entities.NewOrderedMap[any]()
	out.Set("impact_score", impactScore)
	out.Set("risk_factors", riskFactors)
	out.Set("benefits", benefits)
	out.Set("recommendation", recommendation)
	return out
}

// shouldAutoApprove mirrors _should_auto_approve. The Python try/except returns
// false on error; the only error source would be a non-numeric confidence,
// which the *float64 field cannot carry.
func (s *ContextDelegationService) shouldAutoApprove(ctx context.Context, request *DelegationRequest, impactAssessment *entities.OrderedMap[any]) bool {
	_ = ctx

	if request.ConfidenceScore != nil && *request.ConfidenceScore != 0 && *request.ConfidenceScore < 0.7 {
		return false
	}

	recommendation := "manual_review"
	if impactAssessment != nil {
		if raw, ok := impactAssessment.Get("recommendation"); ok {
			recommendation = zpCtxDelString(raw)
		}
	}
	if recommendation == "auto_approve" {
		return true
	}

	autoApprovePatterns := []string{"security_discovery", "compliance_violation", "performance_optimization"}
	dataText := zpCtxDelLower(request.DelegatedData)
	for _, pattern := range autoApprovePatterns {
		if strings.Contains(dataText, pattern) {
			return true
		}
	}
	return false
}

// queueForReview mirrors _queue_for_review. The Python except branch builds a
// dict only when the logger itself raises; unreachable in Go.
func (s *ContextDelegationService) queueForReview(ctx context.Context, delegationID string, request *DelegationRequest, impactAssessment *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	_ = ctx
	_ = request

	out := entities.NewOrderedMap[any]()
	out.Set("queued", true)
	out.Set("delegation_id", delegationID)
	out.Set("review_required", true)
	out.Set("impact_assessment", impactAssessment)
	out.Set("estimated_review_time", "24 hours")
	return out
}

// markDelegationImplemented mirrors _mark_delegation_implemented.
func (s *ContextDelegationService) markDelegationImplemented(ctx context.Context, delegationID string, implementationData *entities.OrderedMap[any]) bool {
	if s.repository == nil || implementationData == nil {
		return false
	}
	implementedAt, ok := implementationData.Get("implemented_at")
	if !ok {
		return false
	}
	implementationDetails, ok := implementationData.Get("implementation_details")
	if !ok {
		return false
	}
	detailsJSON, err := value_objects.PyJSONDumps(implementationDetails, -1)
	if err != nil {
		return false
	}

	update := entities.NewOrderedMap[any]()
	update.Set("processed", true)
	update.Set("approved", true)
	update.Set("processed_at", zpCtxDelString(implementedAt))
	update.Set("implementation_details", detailsJSON)

	ok2, err := s.repository.UpdateDelegation(ctx, delegationID, update)
	if err != nil {
		return false
	}
	return ok2
}

// markDelegationFailed mirrors _mark_delegation_failed.
func (s *ContextDelegationService) markDelegationFailed(ctx context.Context, delegationID, errorMessage string) bool {
	if s.repository == nil {
		return false
	}

	update := entities.NewOrderedMap[any]()
	update.Set("processed", true)
	update.Set("approved", false)
	update.Set("processed_at", value_objects.IsoFormat(time.Now().UTC()))
	update.Set("failure_reason", errorMessage)

	ok, err := s.repository.UpdateDelegation(ctx, delegationID, update)
	if err != nil {
		return false
	}
	return ok
}

// exceedsThreshold mirrors _exceeds_threshold; any Python exception is caught
// and becomes false.
func (s *ContextDelegationService) exceedsThreshold(contextData, changes *entities.OrderedMap[any], thresholdName string, thresholdConfig *entities.OrderedMap[any]) bool {
	if thresholdConfig == nil {
		return false
	}

	thresholdType := "count"
	if raw, ok := thresholdConfig.Get("type"); ok {
		thresholdType = zpCtxDelString(raw)
	}
	thresholdValue := any(int64(1))
	if raw, ok := thresholdConfig.Get("value"); ok {
		thresholdValue = raw
	}

	switch thresholdType {
	case "count":
		pattern := ""
		if raw, ok := thresholdConfig.Get("pattern"); ok {
			s, ok := raw.(string)
			if !ok {
				return false
			}
			pattern = s
		}
		count := strings.Count(zpCtxDelLower(changes), value_objects.PyLower(pattern))
		value, ok := value_objects.PyFloat(thresholdValue)
		if !ok {
			return false
		}
		return float64(count) >= value

	case "percentage":
		if contextData == nil {
			return false
		}
		currentValue := any(int64(0))
		if raw, ok := contextData.Get(thresholdName); ok {
			currentValue = raw
		}
		current, ok := value_objects.PyFloat(currentValue)
		if !ok {
			return false
		}
		value, ok := value_objects.PyFloat(thresholdValue)
		if !ok {
			return false
		}
		return current >= value
	}
	return false
}

// extractThresholdData mirrors _extract_threshold_data; a None context_data
// raises in Python, so an error is returned.
func (s *ContextDelegationService) extractThresholdData(contextData *entities.OrderedMap[any], thresholdName string) (*entities.OrderedMap[any], error) {
	if contextData == nil {
		return nil, errors.New("'NoneType' object has no attribute 'get'")
	}

	thresholdData := any(entities.NewOrderedMap[any]())
	if raw, ok := contextData.Get(thresholdName); ok {
		thresholdData = raw
	}

	out := entities.NewOrderedMap[any]()
	out.Set("threshold_name", thresholdName)
	out.Set("threshold_data", thresholdData)
	out.Set("extraction_method", "threshold_trigger")
	out.Set("extraction_timestamp", value_objects.IsoFormat(time.Now().UTC()))
	return out, nil
}

// calculateAIDelegationConfidence mirrors
// _calculate_ai_delegation_confidence. Python's sum() over floats is
// Neumaier-compensated from 3.12, hence PySum.
func (s *ContextDelegationService) calculateAIDelegationConfidence(changes *entities.OrderedMap[any], pattern string) float64 {
	patternWeights := map[string]float64{
		"reusable_component":       0.8,
		"security_insight":         0.95,
		"performance_optimization": 0.75,
		"architectural_decision":   0.9,
	}
	baseConfidence, ok := patternWeights[pattern]
	if !ok {
		baseConfidence = 0.5
	}

	changeText := zpCtxDelLower(changes)

	qualityIndicators := []struct {
		indicator string
		boost     float64
	}{
		{"documented", 0.1},
		{"tested", 0.1},
		{"validated", 0.1},
		{"reusable", 0.1},
		{"pattern", 0.05},
		{"best practice", 0.1},
	}

	boosts := []float64{}
	for _, quality := range qualityIndicators {
		if strings.Contains(changeText, quality.indicator) {
			boosts = append(boosts, quality.boost)
		}
	}
	qualityBoost := value_objects.PySum(boosts)

	return math.Min(baseConfidence+qualityBoost, 1.0)
}

func (s *ContextDelegationService) extractAIPatternData(changes *entities.OrderedMap[any], pattern string) *entities.OrderedMap[any] {
	confidenceFactors := entities.NewOrderedMap[any]()
	confidenceFactors.Set("pattern_strength", "high")
	confidenceFactors.Set("reusability_score", "medium")
	confidenceFactors.Set("organizational_impact", "high")

	out := entities.NewOrderedMap[any]()
	out.Set("ai_pattern", pattern)
	out.Set("detected_data", changes)
	out.Set("extraction_method", "ai_pattern_recognition")
	out.Set("extraction_timestamp", value_objects.IsoFormat(time.Now().UTC()))
	out.Set("confidence_factors", confidenceFactors)
	return out
}

func (s *ContextDelegationService) evaluateProjectToGlobalTriggers(ctx context.Context, contextID string, contextData, changes *entities.OrderedMap[any]) []*DelegationRequest {
	_ = ctx
	_ = contextData

	requests := []*DelegationRequest{}
	globalPatterns := []struct {
		pattern  string
		category string
	}{
		{"security_policy", "security"},
		{"coding_standard", "coding"},
		{"workflow_template", "workflow"},
		{"compliance_pattern", "compliance"},
	}

	changesText := zpCtxDelLower(changes)
	for _, globalPattern := range globalPatterns {
		if !strings.Contains(changesText, globalPattern.pattern) && !strings.Contains(changesText, globalPattern.category) {
			continue
		}

		delegatedData := entities.NewOrderedMap[any]()
		delegatedData.Set(globalPattern.category+"_insights", changes)
		delegatedData.Set("source_project", contextID)
		delegatedData.Set("category", globalPattern.category)

		request := zpCtxDelNewDelegationRequest("project", contextID, "global", "global_singleton", delegatedData,
			fmt.Sprintf("Project-level %s pattern detected for global adoption", globalPattern.category))
		request.TriggerType = "auto_pattern"
		request.ConfidenceScore = zpCtxDelFloatPtr(0.85)
		requests = append(requests, request)
	}
	return requests
}

// ===============================================
// SHARED HELPERS
// ===============================================

// zpCtxDelErrorResult is the Python {"success": False, "error": ...} shape.
func zpCtxDelErrorResult(message string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	out.Set("success", false)
	out.Set("error", message)
	return out
}

// zpCtxDelMapGet is dict.get(key) with no default; a missing key is None (nil).
func zpCtxDelMapGet(d *entities.OrderedMap[any], key string) any {
	if d == nil {
		return nil
	}
	v, _ := d.Get(key)
	return v
}

// zpCtxDelString mirrors str(v): a string is itself, nil is "None", everything
// else goes through PyStr. Typed-nil ordered maps are rendered as None instead
// of panicking.
func zpCtxDelString(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	if m, ok := v.(*entities.OrderedMap[any]); ok && m == nil {
		return "None"
	}
	return value_objects.PyStr(v)
}

// zpCtxDelLower mirrors str(v).lower().
func zpCtxDelLower(v any) string { return value_objects.PyLower(zpCtxDelString(v)) }

// zpCtxDelAsDict returns an ordered map for a dict-like value; ok is false for
// nil or any non-dict value.
func zpCtxDelAsDict(v any) (*entities.OrderedMap[any], bool) {
	if v == nil {
		return nil, false
	}
	m, ok := v.(*entities.OrderedMap[any])
	if !ok || m == nil {
		return nil, false
	}
	return m, true
}

// zpCtxDelFloatPtr is &f for building Optional[float] fields.
func zpCtxDelFloatPtr(f float64) *float64 { return &f }

// zpCtxDelContains mirrors `x in list`.
func zpCtxDelContains(values []string, needle string) bool {
	for _, value := range values {
		if value == needle {
			return true
		}
	}
	return false
}

// zpCtxDelRequired mirrors d[key]: a missing key is a KeyError carrying the
// quoted key, matching str(KeyError).
func zpCtxDelRequired(d *entities.OrderedMap[any], key string) (any, error) {
	if d == nil {
		return nil, errors.New("'NoneType' object is not subscriptable")
	}
	v, ok := d.Get(key)
	if !ok {
		return nil, errors.New("'" + key + "'")
	}
	return v, nil
}

func zpCtxDelRequiredString(d *entities.OrderedMap[any], key string) (string, error) {
	v, err := zpCtxDelRequired(d, key)
	if err != nil {
		return "", err
	}
	return zpCtxDelString(v), nil
}

// zpCtxDelDictGet is delegated_data.get(key) with no default; a None mapping is
// an AttributeError in Python, so it is returned as an error.
func zpCtxDelDictGet(d *entities.OrderedMap[any], key string) (any, bool, error) {
	if d == nil {
		return nil, false, errors.New("'NoneType' object has no attribute 'get'")
	}
	v, ok := d.Get(key)
	return v, ok, nil
}

// zpCtxDelNestedPair resolves `updated.get(baseKey, {})` and
// `delegatedData.get(extraKey, {})`, applying the Python empty-dict defaults.
func zpCtxDelNestedPair(updated *entities.OrderedMap[any], baseKey string, delegatedData *entities.OrderedMap[any], extraKey string) (any, any, error) {
	base, ok := updated.Get(baseKey)
	if !ok {
		base = entities.NewOrderedMap[any]()
	}
	extra, ok, err := zpCtxDelDictGet(delegatedData, extraKey)
	if err != nil {
		return nil, nil, err
	}
	if !ok {
		extra = entities.NewOrderedMap[any]()
	}
	return base, extra, nil
}

// zpCtxDelDictUpdate is dict.update(extra): it mutates and returns base, so the
// shallow-copy aliasing of the Python nested dicts is preserved.
func zpCtxDelDictUpdate(base, extra any) (any, error) {
	baseMap, ok := base.(*entities.OrderedMap[any])
	if !ok || baseMap == nil {
		return nil, errors.New("'NoneType' object has no attribute 'update'")
	}
	extraMap, ok := extra.(*entities.OrderedMap[any])
	if !ok || extraMap == nil {
		return nil, errors.New("'NoneType' object is not iterable")
	}
	for _, key := range extraMap.Keys() {
		value, _ := extraMap.Get(key)
		baseMap.Set(key, value)
	}
	return baseMap, nil
}
