package websocket

import (
	"context"
	"sync"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// HTTPHandler is a Starlette HTTP endpoint. The returned value is the JSON response
// body.
type HTTPHandler func(ctx context.Context, request any) (any, error)

// WebSocketEndpoint is a Starlette WebSocket endpoint. pathParams and queryParams stand
// in for websocket.path_params and websocket.query_params.
type WebSocketEndpoint func(ctx context.Context, websocket WebSocket, pathParams, queryParams map[string]string)

// App is the minimal application-registration surface used by this package. FastAPI /
// Starlette are not ported, so an implementation is provided by the caller.
type App interface {
	AddWebSocketRoute(path string, endpoint WebSocketEndpoint)
	AddHTTPRoute(path string, methods []string, endpoint HTTPHandler)
	OnStartup(handler func(ctx context.Context) error)
	OnShutdown(handler func(ctx context.Context) error)
}

// TokenValidation mirrors the auth TokenValidation fields used by the server.
type TokenValidation struct {
	Valid  bool
	UserID *string
}

// KeycloakAuth is the minimal auth surface server.py uses. There is no Go
// KeycloakAuth in agenthub_go/fastmcp/auth, so it is injected through NewKeycloakAuth.
type KeycloakAuth interface {
	ValidateToken(ctx context.Context, token string) (*TokenValidation, error)
}

// NewKeycloakAuth constructs the auth service used to validate connection tokens. Set it
// from the concrete auth port; when nil, authentication fails closed.
var NewKeycloakAuth func() KeycloakAuth

// WebSocketServer is the WebSocket Server v2.0 with dual-track processing.
type WebSocketServer struct {
	App App

	SessionFactory    SessionFactory
	ConnectionManager *ConnectionManager
	BatchProcessor    *BatchProcessor

	IsRunning   bool
	StartupTime *string

	mu sync.Mutex
}

// NewWebSocketServer initializes the server and registers its endpoints.
func NewWebSocketServer(app App, sessionFactory SessionFactory) *WebSocketServer {
	s := &WebSocketServer{
		App:               app,
		SessionFactory:    sessionFactory,
		ConnectionManager: NewConnectionManager(sessionFactory),
		BatchProcessor:    NewBatchProcessor(nil, sessionFactory),
	}
	s.BatchProcessor.Manager = s.ConnectionManager
	s.registerEndpoints()
	return s
}

func (s *WebSocketServer) registerEndpoints() {
	websocketEndpoint := func(ctx context.Context, websocket WebSocket, pathParams, queryParams map[string]string) {
		userID := pathParams["user_id"]
		token := queryParams["token"]
		if token == "" {
			websocket.Close(ctx, 1008, "Missing token parameter")
			return
		}
		s.handleWebSocketConnection(ctx, websocket, userID, token)
	}

	websocketHealth := func(ctx context.Context, request any) (any, error) {
		return s.GetHealthStatus(ctx), nil
	}
	websocketStats := func(ctx context.Context, request any) (any, error) {
		return s.GetDetailedStats(ctx), nil
	}

	if s.App == nil {
		return
	}
	s.App.AddWebSocketRoute("/ws/{user_id}", websocketEndpoint)
	s.App.AddHTTPRoute("/ws/health", []string{"GET"}, websocketHealth)
	s.App.AddHTTPRoute("/ws/stats", []string{"GET"}, websocketStats)
}

func (s *WebSocketServer) handleWebSocketConnection(ctx context.Context, websocket WebSocket, userID, token string) {
	var sessionID *string
	defer func() {
		if sessionID != nil {
			s.ConnectionManager.Disconnect(ctx, userID)
		}
	}()

	if NewKeycloakAuth == nil {
		websocket.Close(ctx, 1008, "Invalid token")
		return
	}
	keycloakAuth := NewKeycloakAuth()
	tokenValidation, err := keycloakAuth.ValidateToken(ctx, token)
	if err != nil || tokenValidation == nil || !tokenValidation.Valid {
		websocket.Close(ctx, 1008, "Invalid token")
		return
	}
	authenticatedUserID := tokenValidation.UserID
	if authenticatedUserID == nil || *authenticatedUserID != userID {
		websocket.Close(ctx, 1008, "User ID mismatch")
		return
	}

	sid, err := s.ConnectionManager.Connect(ctx, websocket, userID, nil)
	if err != nil {
		websocket.Close(ctx, 1011, "Internal server error")
		return
	}
	sessionID = &sid

	for {
		rawMessage, err := websocket.ReceiveText(ctx)
		if err != nil {
			if IsWebSocketDisconnect(err) {
				break
			}
			s.ConnectionManager.SendError(ctx, userID, "Message processing error", nil)
			continue
		}
		s.ConnectionManager.ProcessMessage(ctx, userID, rawMessage)
	}
}

// Start starts the WebSocket server and background services.
func (s *WebSocketServer) Start(ctx context.Context) error {
	if s.IsRunning {
		return nil
	}
	s.BatchProcessor.Start(ctx)
	s.IsRunning = true
	startup := valueOfIsoNow()
	s.StartupTime = &startup
	return nil
}

// Stop stops the WebSocket server and cleans up resources.
func (s *WebSocketServer) Stop(ctx context.Context) {
	if !s.IsRunning {
		return
	}
	s.BatchProcessor.Stop(ctx)
	s.ConnectionManager.Cleanup(ctx)
	s.IsRunning = false
	s.StartupTime = nil
}

// GetHealthStatus returns the WebSocket server health status.
func (s *WebSocketServer) GetHealthStatus(ctx context.Context) *entities.OrderedMap[any] {
	connectionStats := s.ConnectionManager.GetConnectionStats()
	batchStats := s.BatchProcessor.GetStats()

	status := "stopped"
	if s.IsRunning {
		status = "healthy"
	}
	total, _ := connectionStats.Get("total_connections")
	activeUsers, _ := connectionStats.Get("active_users")
	batchRunning, _ := batchStats.Get("is_running")
	queueSize, _ := batchStats.Get("queue_size")
	batchesProcessed, _ := batchStats.Get("batches_processed")

	return wsDict(
		"status", status,
		"version", "2.0",
		"is_running", s.IsRunning,
		"startup_time", optString(s.StartupTime),
		"connections", wsDict("total", total, "active_users", lenOf(activeUsers)),
		"batch_processing", wsDict("is_running", batchRunning, "queue_size", queueSize, "batches_processed", batchesProcessed),
	)
}

// GetDetailedStats returns detailed WebSocket server statistics.
func (s *WebSocketServer) GetDetailedStats(ctx context.Context) *entities.OrderedMap[any] {
	connectionStats := s.ConnectionManager.GetConnectionStats()
	batchStats := s.BatchProcessor.GetStats()

	return wsDict(
		"server", wsDict("version", "2.0", "is_running", s.IsRunning, "startup_time", optString(s.StartupTime)),
		"connections", connectionStats,
		"batch_processing", batchStats,
		"protocol", wsDict(
			"version", "2.0",
			"supported_message_types", []any{"update", "bulk", "sync", "heartbeat", "error"},
			"supported_sources", []any{"user", "mcp-ai", "system"},
			"max_message_size_bytes", 64*1024,
		),
	)
}

// BroadcastMessage broadcasts to all connected users (API endpoint).
func (s *WebSocketServer) BroadcastMessage(ctx context.Context, messageData *entities.OrderedMap[any]) (bool, error) {
	if !s.IsRunning {
		return false, nil
	}
	connectionStats := s.ConnectionManager.GetConnectionStats()
	total, _ := connectionStats.Get("total_connections")
	return valueOfInt(total) > 0, nil
}

// GetConnectionCount returns the current number of WebSocket connections.
func (s *WebSocketServer) GetConnectionCount() int {
	stats := s.ConnectionManager.GetConnectionStats()
	total, _ := stats.Get("total_connections")
	return valueOfInt(total)
}

// IsUserConnected reports whether a specific user is connected.
func (s *WebSocketServer) IsUserConnected(userID string) bool {
	return s.ConnectionManager.IsUserConnected(userID)
}

// SendMessageToUser sends a message to a specific user (API endpoint).
func (s *WebSocketServer) SendMessageToUser(ctx context.Context, userID string, messageData *entities.OrderedMap[any]) (bool, error) {
	return s.ConnectionManager.IsUserConnected(userID), nil
}

func valueOfIsoNow() string {
	return value_objects.IsoFormat(nowUTC())
}

func lenOf(v any) int {
	switch x := v.(type) {
	case []any:
		return len(x)
	case []string:
		return len(x)
	}
	return 0
}

func valueOfInt(v any) int {
	switch x := v.(type) {
	case int:
		return x
	case int64:
		return int(x)
	}
	return 0
}

var (
	websocketServerMu sync.Mutex
	websocketServer   *WebSocketServer
)

// GetWebSocketServer returns the global WebSocket server instance.
func GetWebSocketServer() *WebSocketServer {
	websocketServerMu.Lock()
	defer websocketServerMu.Unlock()
	return websocketServer
}

// InitializeWebSocketServer initializes and configures the global WebSocket server.
func InitializeWebSocketServer(app App, sessionFactory SessionFactory) *WebSocketServer {
	websocketServerMu.Lock()
	defer websocketServerMu.Unlock()
	if websocketServer != nil {
		return websocketServer
	}
	websocketServer = NewWebSocketServer(app, sessionFactory)
	return websocketServer
}

// StartupWebSocketServer is the startup hook for the global WebSocket server.
func StartupWebSocketServer(ctx context.Context) {
	websocketServerMu.Lock()
	server := websocketServer
	websocketServerMu.Unlock()
	if server == nil {
		return
	}
	server.Start(ctx)
}

// ShutdownWebSocketServer is the shutdown hook for the global WebSocket server.
func ShutdownWebSocketServer(ctx context.Context) {
	websocketServerMu.Lock()
	server := websocketServer
	websocketServer = nil
	websocketServerMu.Unlock()
	if server != nil {
		server.Stop(ctx)
	}
}
