package handlers

// Project Maintenance Handler (Python maintenance_handler.py).

import (
	"context"

	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/domain/entities"
)

// ProjectMaintenanceHandler ports ProjectMaintenanceHandler.
type ProjectMaintenanceHandler struct {
	responseFormatter ResponseFormatter
}

// NewProjectMaintenanceHandler ports __init__(response_formatter).
func NewProjectMaintenanceHandler(responseFormatter ResponseFormatter) *ProjectMaintenanceHandler {
	return &ProjectMaintenanceHandler{responseFormatter: responseFormatter}
}

// HandleMaintenanceAction ports handle_maintenance_action(facade, action,
// project_id, force=False, user_id=None).
func (h *ProjectMaintenanceHandler) HandleMaintenanceAction(ctx context.Context, facade *facades.ProjectApplicationFacade, action, projectID string, force *bool, userID *string) (result *entities.OrderedMap[any]) {
	f := false
	if force != nil {
		f = *force
	}
	meta := metaMap("action", action, "project_id", projectID, "force", force, "user_id", userID)

	defer func() {
		if r := recover(); r != nil {
			result = h.responseFormatter.CreateErrorResponse(action, "Failed to execute maintenance action '"+action+"': "+panicMessage(r), ErrorCodeOperationFailed, meta)
		}
	}()

	var data *entities.OrderedMap[any]
	var err error
	switch action {
	case "project_health_check":
		data, err = facade.ProjectHealthCheck(ctx, projectID, userID)
	case "cleanup_obsolete":
		data, err = facade.CleanupObsolete(ctx, projectID, f, userID)
	case "validate_integrity":
		data, err = facade.ValidateIntegrity(ctx, projectID, f, userID)
	case "rebalance_agents":
		data, err = facade.RebalanceAgents(ctx, projectID, f, userID)
	default:
		return h.responseFormatter.CreateErrorResponse(action, "Failed to execute maintenance action '"+action+"': Unknown maintenance action: "+action, ErrorCodeOperationFailed, meta)
	}
	if err != nil {
		return h.responseFormatter.CreateErrorResponse(action, "Failed to execute maintenance action '"+action+"': "+err.Error(), ErrorCodeOperationFailed, meta)
	}
	if successFalse(data) {
		return data
	}
	return h.responseFormatter.CreateSuccessResponse(action, data, meta)
}

// ProjectHealthCheck ports project_health_check(facade, project_id, user_id=None).
func (h *ProjectMaintenanceHandler) ProjectHealthCheck(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, userID *string) *entities.OrderedMap[any] {
	return h.HandleMaintenanceAction(ctx, facade, "project_health_check", projectID, nil, userID)
}

// CleanupObsolete ports cleanup_obsolete(facade, project_id, force=False, user_id=None).
func (h *ProjectMaintenanceHandler) CleanupObsolete(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, force *bool, userID *string) *entities.OrderedMap[any] {
	return h.HandleMaintenanceAction(ctx, facade, "cleanup_obsolete", projectID, force, userID)
}

// ValidateIntegrity ports validate_integrity(facade, project_id, force=False, user_id=None).
func (h *ProjectMaintenanceHandler) ValidateIntegrity(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, force *bool, userID *string) *entities.OrderedMap[any] {
	return h.HandleMaintenanceAction(ctx, facade, "validate_integrity", projectID, force, userID)
}

// RebalanceAgents ports rebalance_agents(facade, project_id, force=False, user_id=None).
func (h *ProjectMaintenanceHandler) RebalanceAgents(ctx context.Context, facade *facades.ProjectApplicationFacade, projectID string, force *bool, userID *string) *entities.OrderedMap[any] {
	return h.HandleMaintenanceAction(ctx, facade, "rebalance_agents", projectID, force, userID)
}
