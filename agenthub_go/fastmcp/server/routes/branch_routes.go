// branch_routes.go ports server/routes/branch_routes.py.
//
// The FastAPI APIRouter/Depends/Form plumbing has no Go meaning; the handler
// logic, validation branches, error text and HTTP status codes are preserved.
// BranchAPIController is not ported yet, so the minimal result and controller
// surfaces used by these routes are declared here.
package routes

import (
	"context"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
)

// BranchResult is the minimal BranchResponse/BranchesResponse/DeleteResponse/
// ApiResponse/BulkSummaryResponse surface the routes use: .success, .message,
// .error and .model_dump(by_alias=True).
type BranchResult interface {
	Success() bool
	Message() *string
	Error() *string
	ModelDump() *entities.OrderedMap[any]
}

// BranchController is the minimal BranchAPIController surface used by the routes.
type BranchController interface {
	CreateBranch(ctx context.Context, projectID, name, description, userID string) BranchResult
	ListBranches(ctx context.Context, projectID *string, userID string) BranchResult
	GetBranch(ctx context.Context, branchID, userID string) BranchResult
	UpdateBranch(ctx context.Context, branchID string, name, description, status *string, userID string) BranchResult
	DeleteBranch(ctx context.Context, branchID, userID string) BranchResult
	AssignAgent(ctx context.Context, branchID, agentID, userID string) BranchResult
	GetBranchTaskCounts(ctx context.Context, branchID, userID string) BranchResult
	GetBranchesWithTaskCounts(ctx context.Context, projectID, userID string) BranchResult
	GetBulkSummaries(ctx context.Context, projectIDs []string, userID string, includeArchived bool) BranchResult
}

// BulkSummaryRequest mirrors the BulkSummaryRequest pydantic model.
type BulkSummaryRequest struct {
	ProjectIDs      []string
	IncludeArchived bool
}

func branchMessage(result BranchResult, def string) string {
	if msg := result.Message(); msg != nil {
		return *msg
	}
	return def
}

func branchNotFound(result BranchResult) bool {
	err := result.Error()
	if err == nil {
		return false
	}
	return strings.Contains(strings.ToLower(*err), "not found")
}

// CreateBranch mirrors POST /.
func CreateBranch(ctx context.Context, projectID, gitBranchName, description, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.CreateBranch(ctx, projectID, gitBranchName, description, userID)
	if !result.Success() {
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to create branch"))
	}
	return result.ModelDump(), nil
}

// ListBranches mirrors GET /. Note the Python handler has no `except HTTPException:
// raise`, so a failed result is re-wrapped as the generic 500 message (kept quirk).
func ListBranches(ctx context.Context, projectID *string, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.ListBranches(ctx, projectID, userID)
	if !result.Success() {
		return nil, routesHTTPErr(500, "Failed to list branches")
	}
	return result.ModelDump(), nil
}

// GetBranch mirrors GET /{branch_id}.
func GetBranch(ctx context.Context, branchID, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.GetBranch(ctx, branchID, userID)
	if !result.Success() {
		return nil, routesHTTPErr(404, "Branch not found or access denied")
	}
	return result.ModelDump(), nil
}

// UpdateBranch mirrors PUT /{branch_id}.
func UpdateBranch(ctx context.Context, branchID string, name, description, status *string, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.UpdateBranch(ctx, branchID, name, description, status, userID)
	if !result.Success() {
		if branchNotFound(result) {
			return nil, routesHTTPErr(404, "Branch not found or access denied")
		}
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to update branch"))
	}
	return result.ModelDump(), nil
}

// DeleteBranch mirrors DELETE /{branch_id}.
func DeleteBranch(ctx context.Context, branchID, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.DeleteBranch(ctx, branchID, userID)
	if !result.Success() {
		if branchNotFound(result) {
			return nil, routesHTTPErr(404, "Branch not found or access denied")
		}
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to delete branch"))
	}
	return result.ModelDump(), nil
}

// AssignAgentToBranch mirrors POST /{branch_id}/assign-agent.
func AssignAgentToBranch(ctx context.Context, branchID, agentID, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.AssignAgent(ctx, branchID, agentID, userID)
	if !result.Success() {
		if branchNotFound(result) {
			return nil, routesHTTPErr(404, "Branch not found or access denied")
		}
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to assign agent"))
	}
	return result.ModelDump(), nil
}

// GetBranchTaskCounts mirrors GET /{branch_id}/task-counts.
func GetBranchTaskCounts(ctx context.Context, branchID, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.GetBranchTaskCounts(ctx, branchID, userID)
	if !result.Success() {
		if branchNotFound(result) {
			return nil, routesHTTPErr(404, "Branch not found or access denied")
		}
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to get task counts"))
	}
	return result.ModelDump(), nil
}

// GetProjectBranchesWithTaskCounts mirrors POST /project/{project_id}/summaries.
func GetProjectBranchesWithTaskCounts(ctx context.Context, projectID, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.GetBranchesWithTaskCounts(ctx, projectID, userID)
	if !result.Success() {
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to fetch branch summaries"))
	}
	return result.ModelDump(), nil
}

// GetBulkSummaries mirrors POST /summaries/bulk.
func GetBulkSummaries(ctx context.Context, request BulkSummaryRequest, userID string, controller BranchController) (*entities.OrderedMap[any], error) {
	result := controller.GetBulkSummaries(ctx, request.ProjectIDs, userID, request.IncludeArchived)
	if !result.Success() {
		return nil, routesHTTPErr(500, branchMessage(result, "Failed to fetch bulk summaries"))
	}
	return result.ModelDump(), nil
}
