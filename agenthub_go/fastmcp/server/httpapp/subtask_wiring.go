package httpapp

import (
	"context"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
	infrarepos "agenthub/fastmcp/task_management/infrastructure/repositories"
	"agenthub/fastmcp/task_management/interface/api_controllers"
	"agenthub/fastmcp/types"
)

// subtaskFacadeFactory is the services.FacadeService subtask factory over the real
// SubtaskFacadeFactory (the session argument is Python's get_db session; unused here).
type subtaskFacadeFactory struct {
	factory    *factories.SubtaskFacadeFactory
	ctxFactory *factories.UnifiedContextFacadeFactory
	sessions   *database.SessionManager
}

func (f subtaskFacadeFactory) CreateFacade(projectID, gitBranchID, userID, taskID *string) (any, error) {
	facade, err := f.factory.CreateFacade(nil, projectID, gitBranchID, userID, taskID)
	if err != nil {
		return nil, err
	}
	facade.ContextSync = subtaskCountSync{f.ctxFactory}
	facade.WithProgressStore(infrarepos.NewTaskProgressStore(f.sessions))
	return facade, nil
}

// subtaskCountSync is TaskContextSyncService(...).sync_subtask_counts.
type subtaskCountSync struct {
	ctxFactory *factories.UnifiedContextFacadeFactory
}

func (s subtaskCountSync) SyncSubtaskCounts(ctx context.Context, taskID string, subtaskRepository repositories.SubtaskRepository) error {
	facade, err := s.ctxFactory.CreateFacade(ctx, nil, nil, nil)
	if err != nil {
		return err
	}
	svc, err := services.NewTaskContextSyncService(nil, nil, nil, facade)
	if err != nil {
		return err
	}
	return svc.SyncSubtaskCounts(ctx, taskID, subtaskRepository)
}

// subtaskControllerAdapter satisfies routes.SubtaskController over SubtaskAPIController.
type subtaskControllerAdapter struct {
	c *api_controllers.SubtaskAPIController
}

func subtaskResult(success bool, errMsg, msg *string, d modelDumper) routes.ControllerResult {
	return routes.ControllerResult{Success: success, Error: errMsg, Message: msg, Body: d.ModelDump()}
}

func (a subtaskControllerAdapter) CreateSubtask(ctx context.Context, taskID, title string, description *string, userID string) (routes.ControllerResult, error) {
	r := a.c.CreateSubtask(ctx, taskID, title, description, userID)
	return subtaskResult(r.Success, r.Error, r.Message, r), nil
}

func (a subtaskControllerAdapter) GetSubtask(ctx context.Context, subtaskID, userID string) (routes.ControllerResult, error) {
	r := a.c.GetSubtask(ctx, subtaskID, userID)
	return subtaskResult(r.Success, r.Error, r.Message, r), nil
}

func (a subtaskControllerAdapter) UpdateSubtask(ctx context.Context, subtaskID string, updateData *entities.OrderedMap[any], userID string) (routes.ControllerResult, error) {
	r := a.c.UpdateSubtask(ctx, subtaskID, updateData, userID)
	return subtaskResult(r.Success, r.Error, r.Message, r), nil
}

func (a subtaskControllerAdapter) DeleteSubtask(ctx context.Context, subtaskID, userID string) (routes.ControllerResult, error) {
	r := a.c.DeleteSubtask(ctx, subtaskID, userID)
	return subtaskResult(r.Success, r.Error, r.Message, r), nil
}

func (a subtaskControllerAdapter) ListSubtasks(ctx context.Context, taskID, userID string) (routes.ControllerResult, error) {
	r := a.c.ListSubtasks(ctx, taskID, userID)
	return subtaskResult(r.Success, r.Error, r.Message, r), nil
}

func (a subtaskControllerAdapter) CompleteSubtask(ctx context.Context, subtaskID string, completionSummary *string, userID string) (routes.ControllerResult, error) {
	summary := ""
	if completionSummary != nil {
		summary = *completionSummary
	}
	r := a.c.CompleteSubtask(ctx, subtaskID, summary, userID)
	return subtaskResult(r.Success, r.Error, r.Message, r), nil
}

var (
	_ modelDumper = (*types.SubtaskResponse)(nil)
	_ modelDumper = (*types.SubtasksResponse)(nil)
)
