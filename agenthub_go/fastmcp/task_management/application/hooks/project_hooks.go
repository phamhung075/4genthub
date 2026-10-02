package hooks

import (
	"agenthub/fastmcp/task_management/application/use_cases"
	"context"

	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProjectHooks implements the project use cases' side-effect hooks
// (create_project's context auto-creation and WebSocket broadcast).
type ProjectHooks struct {
	ContextFactory *factories.UnifiedContextFacadeFactory
	Notifier       *services.WebSocketNotificationService
}

func projectIDString(p *entities.Project) string {
	if p.ID == nil {
		return "None"
	}
	return p.ID.Value
}

// CreateProjectContext ensures the user's global context exists, then creates the
// project-level context. Every failure is swallowed (Python only logs a warning).
func (h *ProjectHooks) CreateProjectContext(ctx context.Context, p *entities.Project, userID *string) {
	if h.ContextFactory == nil {
		return
	}
	uid, err := domain.ValidateUserID(userID, "Project context creation")
	if err != nil {
		return
	}
	h.ContextFactory.AutoCreateGlobalContext(ctx, &uid)
	projectID := projectIDString(p)
	facade, err := h.ContextFactory.CreateFacade(ctx, &uid, &projectID, nil)
	if err != nil {
		return
	}
	data := entities.NewOrderedMap[any]()
	data.Set("project_id", projectID)
	data.Set("name", p.Name)
	data.Set("description", p.Description)
	data.Set("configuration", entities.NewOrderedMap[any]())
	data.Set("standards", entities.NewOrderedMap[any]())
	data.Set("team_settings", entities.NewOrderedMap[any]())
	_, _ = facade.CreateContext(ctx, "project", projectID, data, nil)
}

// NotifyProjectCreated broadcasts the "created" project event (only with a user id).
func (h *ProjectHooks) NotifyProjectCreated(ctx context.Context, p *entities.Project, userID *string) {
	if h.Notifier == nil || userID == nil || *userID == "" {
		return
	}
	if p.CreatedAt == nil || p.UpdatedAt == nil {
		return // Python: None.isoformat() raises inside the try and is only logged
	}
	data := entities.NewOrderedMap[any]()
	data.Set("id", projectIDString(p))
	data.Set("name", p.Name)
	data.Set("description", p.Description)
	data.Set("created_at", value_objects.IsoFormat(*p.CreatedAt))
	data.Set("updated_at", value_objects.IsoFormat(*p.UpdatedAt))
	h.Notifier.SyncBroadcastProjectEvent("created", projectIDString(p), userID, data)
}

var _ use_cases.CreateProjectHooks = (*ProjectHooks)(nil)

// NotifyProjectUpdated broadcasts the "updated" project event (only with a user id).
func (h *ProjectHooks) NotifyProjectUpdated(ctx context.Context, p *entities.Project, userID *string, updatedFields []string) {
	if h.Notifier == nil || userID == nil || *userID == "" || p.UpdatedAt == nil {
		return
	}
	data := entities.NewOrderedMap[any]()
	data.Set("id", projectIDString(p))
	data.Set("name", p.Name)
	data.Set("description", p.Description)
	data.Set("updated_at", value_objects.IsoFormat(*p.UpdatedAt))
	data.Set("updated_fields", updatedFields)
	h.Notifier.SyncBroadcastProjectEvent("updated", projectIDString(p), userID, data)
}

var _ use_cases.UpdateProjectHooks = (*ProjectHooks)(nil)
