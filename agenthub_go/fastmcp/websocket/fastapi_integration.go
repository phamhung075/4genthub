package websocket

import (
	"context"
	"errors"

	"agenthub/fastmcp/task_management/domain/entities"
)

// This file ports only the framework-independent parts of fastapi_integration.py.
// Dropped (they bind to FastAPI / FastMCP / task_management database configuration, none
// of which is ported here):
//   - get_database_session_factory (calls task_management get_db_config)
//   - add_websocket_routes_to_existing_app (calls get_db_config.get_async_session)
//   - integrate_websocket_with_fastmcp (reads fastmcp_server.app / ._app)
// SetupWebSocketIntegration takes the App registration interface and the
// SessionFactory explicitly instead.

// GetWebSocketEndpointsInfo returns information about WebSocket endpoints.
func GetWebSocketEndpointsInfo() *entities.OrderedMap[any] {
	return wsDict(
		"websocket_endpoint", "/ws/{user_id}",
		"health_endpoint", "/ws/health",
		"stats_endpoint", "/ws/stats",
		"protocol_version", "2.0",
		"authentication", "JWT token required (query parameter)",
		"supported_message_types", []any{"update", "bulk", "sync", "heartbeat", "error"},
		"features", []any{
			"Real-time user updates (immediate processing)",
			"AI message batching (500ms intervals)",
			"Cascade data integration",
			"JWT authentication",
			"Connection management",
			"Health monitoring",
		},
	)
}

// SetupWebSocketIntegration sets up the WebSocket v2.0 integration with an application.
func SetupWebSocketIntegration(ctx context.Context, app App, sessionFactory SessionFactory) (*WebSocketServer, error) {
	if sessionFactory == nil {
		return nil, errors.New("WebSocket database setup failed: database session factory not available")
	}

	websocketServer := InitializeWebSocketServer(app, sessionFactory)

	if app != nil {
		app.OnStartup(func(ctx context.Context) error {
			websocketServer.Start(ctx)
			return nil
		})
		app.OnShutdown(func(ctx context.Context) error {
			websocketServer.Stop(ctx)
			return nil
		})
	}
	return websocketServer, nil
}

// AddWebSocketHealthToMainHealth adds WebSocket health information to a main health
// response. Python runs get_health_status through asyncio.run because the function is
// sync; Go has no event loop, so it takes a context and calls the method directly.
func AddWebSocketHealthToMainHealth(ctx context.Context, mainHealthResponse *entities.OrderedMap[any], websocketServer *WebSocketServer) *entities.OrderedMap[any] {
	if websocketServer == nil {
		mainHealthResponse.Set("websocket", wsDict("status", "not_configured"))
		return mainHealthResponse
	}

	wsHealth := websocketServer.GetHealthStatus(ctx)
	status, _ := wsHealth.Get("status")
	version, _ := wsHealth.Get("version")
	connections, _ := wsHealth.Get("connections")
	batchProcessing, _ := wsHealth.Get("batch_processing")

	conns, _ := connections.(*entities.OrderedMap[any])
	var total, activeUsers any
	if conns != nil {
		total, _ = conns.Get("total")
		activeUsers, _ = conns.Get("active_users")
	}
	batch, _ := batchProcessing.(*entities.OrderedMap[any])
	var batchRunning any
	if batch != nil {
		batchRunning, _ = batch.Get("is_running")
	}

	mainHealthResponse.Set("websocket", wsDict(
		"status", status,
		"version", version,
		"connections", total,
		"active_users", activeUsers,
		"batch_processing", batchRunning,
	))
	return mainHealthResponse
}
