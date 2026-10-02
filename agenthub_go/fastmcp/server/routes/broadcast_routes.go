// broadcast_routes.go ports server/routes/broadcast_routes.py.
//
// The FastAPI APIRouter/pydantic plumbing has no Go meaning; the request model
// and handler logic are preserved. broadcast_data_change is imported from
// websocket_routes.py, which is not ported yet, so the minimal function type is
// declared here (to be replaced by the real websocket_routes port).
package routes

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
)

// BroadcastRequest mirrors the BroadcastRequest pydantic model.
type BroadcastRequest struct {
	EventType  string
	EntityType string
	EntityID   string
	UserID     string
	Data       *entities.OrderedMap[any]
	Metadata   *entities.OrderedMap[any]
}

// BroadcastFunc mirrors websocket_routes.broadcast_data_change.
type BroadcastFunc func(ctx context.Context, eventType, entityType, entityID, userID string, data, metadata *entities.OrderedMap[any]) error

// TriggerBroadcast mirrors POST /notify.
func TriggerBroadcast(ctx context.Context, request BroadcastRequest, broadcast BroadcastFunc) (*entities.OrderedMap[any], error) {
	if err := broadcast(ctx, request.EventType, request.EntityType, request.EntityID, request.UserID, request.Data, request.Metadata); err != nil {
		return nil, routesHTTPErr(500, err.Error())
	}
	out := entities.NewOrderedMap[any]()
	out.Set("status", "broadcast_sent")
	out.Set("entity_type", request.EntityType)
	out.Set("event_type", request.EventType)
	return out, nil
}
