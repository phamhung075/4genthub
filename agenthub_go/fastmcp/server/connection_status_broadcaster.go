package server

import (
	"os"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// StatusUpdate mirrors the Python dataclass StatusUpdate.
type StatusUpdate struct {
	EventType          string
	Timestamp          float64
	ServerStatus       string
	ConnectionCount    int
	ServerRestartCount int
	UptimeSeconds      float64
	RecommendedAction  string
	ToolsAvailable     bool
	AuthEnabled        bool
	AdditionalInfo     *entities.OrderedMap[any]
}

// ToDict mirrors dataclasses.asdict(StatusUpdate): field declaration order.
func (s *StatusUpdate) ToDict() *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("event_type", s.EventType)
	om.Set("timestamp", s.Timestamp)
	om.Set("server_status", s.ServerStatus)
	om.Set("connection_count", s.ConnectionCount)
	om.Set("server_restart_count", s.ServerRestartCount)
	om.Set("uptime_seconds", s.UptimeSeconds)
	om.Set("recommended_action", s.RecommendedAction)
	om.Set("tools_available", s.ToolsAvailable)
	om.Set("auth_enabled", s.AuthEnabled)
	if s.AdditionalInfo == nil {
		om.Set("additional_info", any(nil))
	} else {
		om.Set("additional_info", s.AdditionalInfo)
	}
	return om
}

// ConnectionStatusBroadcaster mirrors the Python class of the same name.
type ConnectionStatusBroadcaster struct {
	ConnectionManager        *ConnectionManager
	ConnectedClients         *entities.StringSet
	LastStatus               *StatusUpdate
	BroadcastInterval        int // seconds
	ImmediateBroadcastEvents *entities.StringSet

	mu      sync.Mutex
	running bool
	stopCh  chan struct{}
	wg      sync.WaitGroup
}

// NewConnectionStatusBroadcaster mirrors __init__(connection_manager=None).
func NewConnectionStatusBroadcaster(connectionManager *ConnectionManager) *ConnectionStatusBroadcaster {
	events := &entities.StringSet{}
	events.Add("server_restart")
	events.Add("connection_lost")
	return &ConnectionStatusBroadcaster{
		ConnectionManager:        connectionManager,
		ConnectedClients:         &entities.StringSet{},
		BroadcastInterval:        30,
		ImmediateBroadcastEvents: events,
	}
}

// StartBroadcasting mirrors ConnectionStatusBroadcaster.start_broadcasting.
func (b *ConnectionStatusBroadcaster) StartBroadcasting() {
	b.muLock()
	if b.running {
		b.muUnlock()
		return
	}
	b.running = true
	ch := make(chan struct{})
	b.stopCh = ch
	b.wg.Add(1)
	b.muUnlock()

	go b.broadcastLoop(ch)
}

// StopBroadcasting mirrors ConnectionStatusBroadcaster.stop_broadcasting.
func (b *ConnectionStatusBroadcaster) StopBroadcasting() {
	b.muLock()
	if !b.running {
		b.muUnlock()
		return
	}
	b.running = false
	close(b.stopCh)
	b.muUnlock()
	b.wg.Wait()
}

// The broadcaster below is driven by a single asyncio task in Python; a mutex
// guards the client set for concurrent Go callers.
func (b *ConnectionStatusBroadcaster) muLock()   { b.mu.Lock() }
func (b *ConnectionStatusBroadcaster) muUnlock() { b.mu.Unlock() }

// RegisterClient mirrors ConnectionStatusBroadcaster.register_client.
func (b *ConnectionStatusBroadcaster) RegisterClient(sessionID string) {
	b.muLock()
	b.ConnectedClients.Add(sessionID)
	b.muUnlock()
	b.sendImmediateStatusUpdate(sessionID)
}

// UnregisterClient mirrors ConnectionStatusBroadcaster.unregister_client.
func (b *ConnectionStatusBroadcaster) UnregisterClient(sessionID string) {
	b.muLock()
	b.ConnectedClients.Remove(sessionID)
	b.muUnlock()
}

// BroadcastServerRestart mirrors ConnectionStatusBroadcaster.broadcast_server_restart.
func (b *ConnectionStatusBroadcaster) BroadcastServerRestart() {
	statusUpdate := b.createStatusUpdate("server_restart")
	statusUpdate.RecommendedAction = "reconnect"
	statusUpdate.ServerStatus = "restarted"
	b.broadcastToAllClients(statusUpdate, true)
}

// BroadcastConnectionHealth mirrors ConnectionStatusBroadcaster.broadcast_connection_health.
func (b *ConnectionStatusBroadcaster) BroadcastConnectionHealth() {
	statusUpdate := b.createStatusUpdate("connection_health")
	b.broadcastToAllClients(statusUpdate, false)
}

// BroadcastToolsStatus mirrors ConnectionStatusBroadcaster.broadcast_tools_status.
func (b *ConnectionStatusBroadcaster) BroadcastToolsStatus(toolsAvailable bool) {
	statusUpdate := b.createStatusUpdate("tools_available")
	statusUpdate.ToolsAvailable = toolsAvailable
	if !toolsAvailable {
		statusUpdate.RecommendedAction = "reconnect"
		statusUpdate.ServerStatus = "degraded"
	}
	b.broadcastToAllClients(statusUpdate, true)
}

// createStatusUpdate mirrors ConnectionStatusBroadcaster._create_status_update.
func (b *ConnectionStatusBroadcaster) createStatusUpdate(eventType string) *StatusUpdate {
	now := float64(time.Now().UnixNano()) / 1e9

	connectionCount := 0
	serverRestartCount := 0
	uptimeSeconds := 0.0
	serverStatus := "healthy"
	recommendedAction := "continue"

	// Python computes auth_enabled from AUTH_ENABLED (default "false", tuple
	// membership) and then unconditionally overwrites it below with
	// os.environ.get("AUTH_ENABLED", "true").lower() == "true". The first
	// computation is dead; only the second is observable.

	if b.ConnectionManager != nil {
		func() {
			defer func() {
				if r := recover(); r != nil {
					serverStatus = "degraded"
				}
			}()
			stats := b.ConnectionManager.GetConnectionStats()
			reconnectionInfo := b.ConnectionManager.GetReconnectionInfo()

			connectionCount = srvInt(srvGet(srvGet(stats, "connections", nil), "active_connections", 0))
			serverRestartCount = srvInt(srvGet(srvGet(stats, "server_info", nil), "restart_count", 0))
			if f, ok := value_objects.PyFloat(srvGet(srvGet(stats, "server_info", nil), "uptime_seconds", 0)); ok {
				uptimeSeconds = f
			}
			recommendedAction = value_objects.PyStr(srvGet(reconnectionInfo, "recommended_action", "continue"))

			if serverRestartCount > 0 && uptimeSeconds < 60 {
				serverStatus = "restarted"
			} else if connectionCount == 0 && uptimeSeconds > 60 {
				serverStatus = "degraded"
			} else {
				serverStatus = "healthy"
			}
		}()
	}

	authEnabled := strings.ToLower(envOr("AUTH_ENABLED", "true")) == "true"

	additionalInfo := entities.NewOrderedMap[any]()
	additionalInfo.Set("broadcast_time", value_objects.IsoFormatNaive(time.Now()))
	additionalInfo.Set("client_count", b.clientCountLocked())

	return &StatusUpdate{
		EventType:          eventType,
		Timestamp:          now,
		ServerStatus:       serverStatus,
		ConnectionCount:    connectionCount,
		ServerRestartCount: serverRestartCount,
		UptimeSeconds:      uptimeSeconds,
		RecommendedAction:  recommendedAction,
		ToolsAvailable:     true,
		AuthEnabled:        authEnabled,
		AdditionalInfo:     additionalInfo,
	}
}

// envOr mirrors os.environ.get(name, default).
func envOr(name, def string) string {
	if v, ok := os.LookupEnv(name); ok {
		return v
	}
	return def
}

// broadcastToAllClients mirrors ConnectionStatusBroadcaster._broadcast_to_all_clients.
func (b *ConnectionStatusBroadcaster) broadcastToAllClients(statusUpdate *StatusUpdate, immediate bool) {
	b.muLock()
	clientCount := b.ConnectedClients.Len()
	clients := b.ConnectedClients.Items()
	if clientCount == 0 {
		b.muUnlock()
		return
	}
	// Python builds {"type": "status_update", "data": asdict(status_update)} and
	// discards it (no transport); there is no observable effect to port.
	b.LastStatus = statusUpdate
	b.muUnlock()

	for _, clientID := range clients {
		func() {
			defer func() {
				if r := recover(); r != nil {
					b.muLock()
					b.ConnectedClients.Remove(clientID)
					b.muUnlock()
				}
			}()
		}()
	}
}

// sendImmediateStatusUpdate mirrors ConnectionStatusBroadcaster._send_immediate_status_update.
func (b *ConnectionStatusBroadcaster) sendImmediateStatusUpdate(sessionID string) {
	func() {
		defer func() { _ = recover() }()
		b.createStatusUpdate("connection_health")
	}()
}

// broadcastLoop mirrors ConnectionStatusBroadcaster._broadcast_loop.
func (b *ConnectionStatusBroadcaster) broadcastLoop(ch chan struct{}) {
	defer b.wg.Done()
	for {
		func() {
			defer func() {
				if r := recover(); r != nil {
					select {
					case <-time.After(5 * time.Second):
					case <-ch:
					}
				}
			}()
			b.muLock()
			hasClients := b.ConnectedClients.Len() > 0
			b.muUnlock()
			if hasClients {
				b.BroadcastConnectionHealth()
			}
		}()

		select {
		case <-ch:
			return
		case <-time.After(time.Duration(b.BroadcastInterval) * time.Second):
		}
	}
}

// GetLastStatus mirrors ConnectionStatusBroadcaster.get_last_status (nil = None).
func (b *ConnectionStatusBroadcaster) GetLastStatus() *entities.OrderedMap[any] {
	b.muLock()
	defer b.muUnlock()
	if b.LastStatus != nil {
		return b.LastStatus.ToDict()
	}
	return nil
}

// GetClientCount mirrors ConnectionStatusBroadcaster.get_client_count.
func (b *ConnectionStatusBroadcaster) GetClientCount() int {
	b.muLock()
	defer b.muUnlock()
	return b.ConnectedClients.Len()
}

func (b *ConnectionStatusBroadcaster) clientCountLocked() int {
	b.muLock()
	defer b.muUnlock()
	return b.ConnectedClients.Len()
}

// Global status broadcaster instance (Python module-level _status_broadcaster).
var (
	statusBroadcasterMu sync.Mutex
	statusBroadcaster   *ConnectionStatusBroadcaster
)

// GetStatusBroadcaster mirrors get_status_broadcaster().
func GetStatusBroadcaster(connectionManager *ConnectionManager) *ConnectionStatusBroadcaster {
	statusBroadcasterMu.Lock()
	defer statusBroadcasterMu.Unlock()
	if statusBroadcaster == nil {
		statusBroadcaster = NewConnectionStatusBroadcaster(connectionManager)
		statusBroadcaster.StartBroadcasting()
	}
	return statusBroadcaster
}

// CleanupStatusBroadcaster mirrors cleanup_status_broadcaster().
func CleanupStatusBroadcaster() {
	statusBroadcasterMu.Lock()
	defer statusBroadcasterMu.Unlock()
	if statusBroadcaster != nil {
		statusBroadcaster.StopBroadcasting()
		statusBroadcaster = nil
	}
}
