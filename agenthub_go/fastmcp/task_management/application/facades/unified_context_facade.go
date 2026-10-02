// Package facades ports task_management/application/facades.
//
// This file ports facades/unified_context_facade.py.
package facades

import (
	"context"
	"errors"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UnifiedContextService is the consumer-side port of
// application/services/unified_context_service.py (not ported yet). The Python service is
// synchronous and raises the domain exceptions caught by the facade; the Go methods are
// ctx-first because they touch storage and return the Python exception as an error.
// Response dicts whose key order is observable are OrderedMaps.
type UnifiedContextService interface {
	CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any],
		userID, projectID *string, autoCreateParents bool) (*entities.OrderedMap[any], error)
	GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error)
	UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool, userID *string) (*entities.OrderedMap[any], error)
	DeleteContext(ctx context.Context, level, contextID string, userID *string) (*entities.OrderedMap[any], error)
	ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error)
	DelegateContext(ctx context.Context, level, contextID, delegateTo string, data *entities.OrderedMap[any], delegationReason *string) (*entities.OrderedMap[any], error)
	AddInsight(ctx context.Context, level, contextID, content string, category, importance, agent *string) (*entities.OrderedMap[any], error)
	AddProgress(ctx context.Context, level, contextID, content string, agent *string) (*entities.OrderedMap[any], error)
	ListContexts(ctx context.Context, level string, filters *entities.OrderedMap[any]) (*entities.OrderedMap[any], error)
	BootstrapContextHierarchy(ctx context.Context, userID, projectID, branchID *string) (*entities.OrderedMap[any], error)
}

// UnifiedContextFacade mirrors unified_context_facade.UnifiedContextFacade.
type UnifiedContextFacade struct {
	service     UnifiedContextService
	userID      *string
	projectID   *string
	gitBranchID *string
}

// NewUnifiedContextFacade mirrors __init__.
func NewUnifiedContextFacade(service UnifiedContextService, userID, projectID, gitBranchID *string) *UnifiedContextFacade {
	return &UnifiedContextFacade{service: service, userID: userID, projectID: projectID, gitBranchID: gitBranchID}
}

// zpUCFAddScopeToData mirrors _add_scope_to_data: data.copy(), then user_id / project_id /
// git_branch_id are appended (in that order) when the scope is set and the key is missing.
func (f *UnifiedContextFacade) zpUCFAddScopeToData(data *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	if data != nil {
		for _, k := range data.Keys() {
			v, _ := data.Get(k)
			result.Set(k, v)
		}
	}
	if f.userID != nil && *f.userID != "" && !result.Has("user_id") {
		result.Set("user_id", *f.userID)
	}
	if f.projectID != nil && *f.projectID != "" && !result.Has("project_id") {
		result.Set("project_id", *f.projectID)
	}
	if f.gitBranchID != nil && *f.gitBranchID != "" && !result.Has("git_branch_id") {
		result.Set("git_branch_id", *f.gitBranchID)
	}
	return result
}

// zpUCFErrorResponse builds {"success": false, "error": <str>, "error_type": <t>}.
func zpUCFErrorResponse(err error, errorType string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("error", err.Error())
	m.Set("error_type", errorType)
	return m
}

// zpUCFServiceError maps a service error the way the Python except branches do. The order
// matches the Python except clause order.
func zpUCFServiceError(err error) *entities.OrderedMap[any] {
	var validation *exceptions.ValidationException
	var notFound *exceptions.ResourceNotFoundException
	var dbErr *exceptions.DatabaseException
	var repoErr *exceptions.RepositoryError
	switch {
	case errors.As(err, &validation):
		return zpUCFErrorResponse(err, "validation")
	case errors.As(err, &notFound):
		return zpUCFErrorResponse(err, "not_found")
	case errors.As(err, &dbErr), errors.As(err, &repoErr):
		return zpUCFErrorResponse(err, "database")
	default:
		return zpUCFErrorResponse(err, "unexpected")
	}
}

// zpUCFListError is list_contexts' except chain: it has no ResourceNotFoundException branch,
// so a not-found error is "unexpected".
func zpUCFListError(err error) *entities.OrderedMap[any] {
	var notFound *exceptions.ResourceNotFoundException
	var validation *exceptions.ValidationException
	var dbErr *exceptions.DatabaseException
	var repoErr *exceptions.RepositoryError
	if errors.As(err, &notFound) && !errors.As(err, &validation) && !errors.As(err, &dbErr) && !errors.As(err, &repoErr) {
		return zpUCFErrorResponse(err, "unexpected")
	}
	return zpUCFServiceError(err)
}

// zpUCFGet is dict.get(key) returning None when absent.
func zpUCFGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

// CreateContext mirrors UnifiedContextFacade.create_context.
func (f *UnifiedContextFacade) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID *string) (*entities.OrderedMap[any], error) {
	effectiveUserID := userID // Python: user_id or self._user_id (empty string falls back too)
	if effectiveUserID == nil || *effectiveUserID == "" {
		effectiveUserID = f.userID
	}
	res, err := f.service.CreateContext(ctx, level, contextID, f.zpUCFAddScopeToData(data), effectiveUserID, f.projectID, true)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// GetContext mirrors UnifiedContextFacade.get_context.
func (f *UnifiedContextFacade) GetContext(ctx context.Context, level, contextID string, includeInherited, forceRefresh bool, userID *string) (*entities.OrderedMap[any], error) {
	res, err := f.service.GetContext(ctx, level, contextID, includeInherited, forceRefresh, userID)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// GetContextSummary mirrors UnifiedContextFacade.get_context_summary.
func (f *UnifiedContextFacade) GetContextSummary(ctx context.Context, contextID string) (*entities.OrderedMap[any], error) {
	response, err := f.service.GetContext(ctx, "task", contextID, false, false, nil)
	if err != nil {
		var validation *exceptions.ValidationException
		var notFound *exceptions.ResourceNotFoundException
		var dbErr *exceptions.DatabaseException
		var repoErr *exceptions.RepositoryError
		switch {
		case errors.As(err, &validation):
			out := entities.NewOrderedMap[any]()
			out.Set("success", false)
			out.Set("has_context", false)
			out.Set("error", err.Error())
			out.Set("error_type", "validation")
			return out, nil
		case errors.As(err, &notFound):
			out := entities.NewOrderedMap[any]()
			out.Set("success", true)
			out.Set("has_context", false)
			out.Set("context_size", 0)
			out.Set("last_updated", nil)
			return out, nil
		case errors.As(err, &dbErr), errors.As(err, &repoErr):
			out := entities.NewOrderedMap[any]()
			out.Set("success", false)
			out.Set("has_context", false)
			out.Set("error", err.Error())
			out.Set("error_type", "database")
			return out, nil
		default:
			out := entities.NewOrderedMap[any]()
			out.Set("success", false)
			out.Set("has_context", false)
			out.Set("error", "An unexpected error occurred")
			out.Set("error_type", "unexpected")
			return out, nil
		}
	}
	if value_objects.PyTruthy(zpUCFGet(response, "success")) && value_objects.PyTruthy(zpUCFGet(response, "context")) {
		contextData, _ := zpUCFGet(response, "context").(*entities.OrderedMap[any])
		dumped, _ := value_objects.PyJSONDumps(contextData, -1)
		lastUpdated := zpUCFGet(contextData, "updated_at")
		if !value_objects.PyTruthy(lastUpdated) {
			lastUpdated = zpUCFGet(contextData, "created_at")
		}
		out := entities.NewOrderedMap[any]()
		out.Set("success", true)
		out.Set("has_context", true)
		out.Set("context_size", len(dumped))
		out.Set("last_updated", lastUpdated)
		return out, nil
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("has_context", false)
	out.Set("context_size", 0)
	out.Set("last_updated", nil)
	return out, nil
}

// UpdateContext mirrors UnifiedContextFacade.update_context.
func (f *UnifiedContextFacade) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], propagateChanges bool) (*entities.OrderedMap[any], error) {
	res, err := f.service.UpdateContext(ctx, level, contextID, f.zpUCFAddScopeToData(data), propagateChanges, nil)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// DeleteContext mirrors UnifiedContextFacade.delete_context.
func (f *UnifiedContextFacade) DeleteContext(ctx context.Context, level, contextID string) (*entities.OrderedMap[any], error) {
	res, err := f.service.DeleteContext(ctx, level, contextID, nil)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// ResolveContext mirrors UnifiedContextFacade.resolve_context.
func (f *UnifiedContextFacade) ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool) (*entities.OrderedMap[any], error) {
	res, err := f.service.ResolveContext(ctx, level, contextID, forceRefresh, nil)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// DelegateContext mirrors UnifiedContextFacade.delegate_context.
func (f *UnifiedContextFacade) DelegateContext(ctx context.Context, level, contextID, delegateTo string, data *entities.OrderedMap[any], delegationReason *string) (*entities.OrderedMap[any], error) {
	res, err := f.service.DelegateContext(ctx, level, contextID, delegateTo, data, delegationReason)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// AddInsight mirrors UnifiedContextFacade.add_insight.
func (f *UnifiedContextFacade) AddInsight(ctx context.Context, level, contextID, content string, category, importance, agent *string) (*entities.OrderedMap[any], error) {
	res, err := f.service.AddInsight(ctx, level, contextID, content, category, importance, agent)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// AddProgress mirrors UnifiedContextFacade.add_progress.
func (f *UnifiedContextFacade) AddProgress(ctx context.Context, level, contextID, content string, agent *string) (*entities.OrderedMap[any], error) {
	res, err := f.service.AddProgress(ctx, level, contextID, content, agent)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}

// ListContexts mirrors UnifiedContextFacade.list_contexts. The Python filter dict is
// mutated in place; the Go port mutates the supplied map.
func (f *UnifiedContextFacade) ListContexts(ctx context.Context, level string, filters *entities.OrderedMap[any]) (*entities.OrderedMap[any], error) {
	if filters == nil {
		filters = entities.NewOrderedMap[any]()
	}
	if f.userID != nil && *f.userID != "" {
		filters.Set("user_id", *f.userID)
	}
	if level != "project" && f.projectID != nil && *f.projectID != "" {
		filters.Set("project_id", *f.projectID)
	}
	if level != "project" && level != "branch" && f.gitBranchID != nil && *f.gitBranchID != "" {
		filters.Set("git_branch_id", *f.gitBranchID)
	}
	res, err := f.service.ListContexts(ctx, level, filters)
	if err != nil {
		return zpUCFListError(err), nil
	}
	return res, nil
}

// BootstrapContextHierarchy mirrors UnifiedContextFacade.bootstrap_context_hierarchy.
func (f *UnifiedContextFacade) BootstrapContextHierarchy(ctx context.Context, projectID, branchID *string) (*entities.OrderedMap[any], error) {
	effectiveProjectID := projectID
	if effectiveProjectID == nil {
		effectiveProjectID = f.projectID
	}
	effectiveBranchID := branchID
	if effectiveBranchID == nil {
		effectiveBranchID = f.gitBranchID
	}
	res, err := f.service.BootstrapContextHierarchy(ctx, f.userID, effectiveProjectID, effectiveBranchID)
	if err != nil {
		var validation *exceptions.ValidationException
		var notFound *exceptions.ResourceNotFoundException
		var dbErr *exceptions.DatabaseException
		var repoErr *exceptions.RepositoryError
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		switch {
		case errors.As(err, &validation):
			out.Set("error", err.Error())
			out.Set("error_type", "validation")
		case errors.As(err, &notFound):
			out.Set("error", err.Error())
			out.Set("error_type", "not_found")
		case errors.As(err, &dbErr), errors.As(err, &repoErr):
			out.Set("error", err.Error())
			out.Set("error_type", "database")
		default:
			out.Set("error", "An unexpected error occurred")
			out.Set("error_type", "unexpected")
		}
		out.Set("bootstrap_completed", false)
		return out, nil
	}
	return res, nil
}

// CreateContextFlexible mirrors UnifiedContextFacade.create_context_flexible.
func (f *UnifiedContextFacade) CreateContextFlexible(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], autoCreateParents bool) (*entities.OrderedMap[any], error) {
	scoped := f.zpUCFAddScopeToData(data)
	if !autoCreateParents {
		scoped.Set("allow_orphaned_creation", true)
	}
	res, err := f.service.CreateContext(ctx, level, contextID, scoped, f.userID, f.projectID, autoCreateParents)
	if err != nil {
		return zpUCFServiceError(err), nil
	}
	return res, nil
}
