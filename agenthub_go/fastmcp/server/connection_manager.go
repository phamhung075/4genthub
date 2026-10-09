// Package server ports fastmcp/server. Every module that carries behaviour with a
// Go meaning is ported, each in its own file: context.py in context.go,
// dependencies.py in dependencies.go and error_middleware.py in error_middleware.go.
// What has no Go meaning is the FastMCP/MCP-SDK/Starlette/FastAPI framework itself.
package server

import (
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// srvGet reads a key from a Python-dict-like value (an *entities.OrderedMap[any]
// or a plain map[string]any), returning def when the key is absent. A present
// key with a nil value still yields that nil value, matching dict.get semantics.
func srvGet(om any, key string, def any) any {
	switch m := om.(type) {
	case *entities.OrderedMap[any]:
		if m == nil {
			return def
		}
		if v, ok := m.Get(key); ok {
			return v
		}
	case map[string]any:
		if v, ok := m[key]; ok {
			return v
		}
	}
	return def
}

// srvInt mirrors int(value) for the numeric results of the ported code.
func srvInt(v any) int {
	if f, ok := value_objects.PyFloat(v); ok {
		return int(f)
	}
	return 0
}

// ConnectionInfo mirrors the Python dataclass of the same name.
type ConnectionInfo struct {
	SessionID          string
	ClientInfo         *entities.OrderedMap[any]
	ConnectedAt        time.Time
	LastActivity       time.Time
	HealthCheckCount   int
	IsHealthy          bool
	ClientCapabilities *entities.OrderedMap[any]
}

// UpdateActivity mirrors ConnectionInfo.update_activity.
func (c *ConnectionInfo) UpdateActivity() { c.LastActivity = time.Now() }

// IsStale mirrors ConnectionInfo.is_stale(timeout_minutes).
func (c *ConnectionInfo) IsStale(timeoutMinutes int) bool {
	return time.Since(c.LastActivity) > time.Duration(timeoutMinutes)*time.Minute
}

// ConnectionManager mirrors the Python class of the same name. Python's asyncio
// task is a goroutine guarded by a stop channel.
type ConnectionManager struct {
	mu sync.Mutex

	Connections         *entities.OrderedMap[*ConnectionInfo]
	ServerStartTime     time.Time
	ServerRestartCount  int
	HealthCheckInterval int // seconds
	ConnectionTimeout   int // minutes

	running bool
	stopCh  chan struct{}
	wg      sync.WaitGroup
}

// NewConnectionManager builds a manager with the Python defaults.
func NewConnectionManager() *ConnectionManager {
	return &ConnectionManager{
		Connections:         entities.NewOrderedMap[*ConnectionInfo](),
		ServerStartTime:     time.Now(),
		HealthCheckInterval: 30,
		ConnectionTimeout:   30,
	}
}

// StartMonitoring mirrors ConnectionManager.start_monitoring.
func (m *ConnectionManager) StartMonitoring() {
	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return
	}
	m.running = true
	ch := make(chan struct{})
	m.stopCh = ch
	m.wg.Add(1)
	m.mu.Unlock()

	go m.healthMonitorLoop(ch)
}

// StopMonitoring mirrors ConnectionManager.stop_monitoring (task cancel + await).
func (m *ConnectionManager) StopMonitoring() {
	m.mu.Lock()
	if !m.running {
		m.mu.Unlock()
		return
	}
	m.running = false
	close(m.stopCh)
	m.mu.Unlock()

	m.wg.Wait()
}

// RegisterConnection mirrors ConnectionManager.register_connection. A nil
// clientCapabilities is the dataclass default None; an empty/zero value becomes {}.
func (m *ConnectionManager) RegisterConnection(sessionID string, clientInfo *entities.OrderedMap[any], clientCapabilities *entities.OrderedMap[any]) *ConnectionInfo {
	now := time.Now()
	if clientCapabilities == nil {
		clientCapabilities = entities.NewOrderedMap[any]()
	}
	conn := &ConnectionInfo{
		SessionID:          sessionID,
		ClientInfo:         clientInfo,
		ConnectedAt:        now,
		LastActivity:       now,
		IsHealthy:          true,
		ClientCapabilities: clientCapabilities,
	}

	m.mu.Lock()
	m.Connections.Set(sessionID, conn)
	m.mu.Unlock()
	return conn
}

// UpdateConnectionActivity mirrors ConnectionManager.update_connection_activity.
func (m *ConnectionManager) UpdateConnectionActivity(sessionID string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if c, ok := m.Connections.Get(sessionID); ok {
		c.UpdateActivity()
	}
}

// UnregisterConnection mirrors ConnectionManager.unregister_connection (nil when absent).
func (m *ConnectionManager) UnregisterConnection(sessionID string) *ConnectionInfo {
	m.mu.Lock()
	defer m.mu.Unlock()
	c, ok := m.Connections.Get(sessionID)
	if !ok {
		return nil
	}
	m.Connections.Delete(sessionID)
	return c
}

// GetConnection mirrors ConnectionManager.get_connection.
func (m *ConnectionManager) GetConnection(sessionID string) *ConnectionInfo {
	m.mu.Lock()
	defer m.mu.Unlock()
	c, _ := m.Connections.Get(sessionID)
	return c
}

// GetActiveConnections mirrors ConnectionManager.get_active_connections.
func (m *ConnectionManager) GetActiveConnections() *entities.OrderedMap[*ConnectionInfo] {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.activeConnectionsLocked()
}

func (m *ConnectionManager) activeConnectionsLocked() *entities.OrderedMap[*ConnectionInfo] {
	active := entities.NewOrderedMap[*ConnectionInfo]()
	for _, sid := range m.Connections.Keys() {
		c, _ := m.Connections.Get(sid)
		if !c.IsStale(m.ConnectionTimeout) {
			active.Set(sid, c)
		}
	}
	return active
}

// CleanupStaleConnections mirrors ConnectionManager.cleanup_stale_connections.
func (m *ConnectionManager) CleanupStaleConnections() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	var stale []string
	for _, sid := range m.Connections.Keys() {
		c, _ := m.Connections.Get(sid)
		if c.IsStale(m.ConnectionTimeout) {
			stale = append(stale, sid)
		}
	}
	for _, sid := range stale {
		m.Connections.Delete(sid)
	}
	return len(stale)
}

// GetConnectionStats mirrors ConnectionManager.get_connection_stats. The returned
// OrderedMap preserves the Python dict key order.
func (m *ConnectionManager) GetConnectionStats() *entities.OrderedMap[any] {
	m.mu.Lock()
	defer m.mu.Unlock()

	activeConnections := m.activeConnectionsLocked()
	now := time.Now()

	serverInfo := entities.NewOrderedMap[any]()
	serverInfo.Set("start_time", value_objects.IsoFormatNaive(m.ServerStartTime))
	serverInfo.Set("uptime_seconds", now.Sub(m.ServerStartTime).Seconds())
	serverInfo.Set("restart_count", m.ServerRestartCount)

	connections := entities.NewOrderedMap[any]()
	connections.Set("total_registered", m.Connections.Len())
	connections.Set("active_connections", activeConnections.Len())
	connections.Set("stale_connections", m.Connections.Len()-activeConnections.Len())

	activeClients := make([]any, 0, activeConnections.Len())
	for _, sid := range activeConnections.Keys() {
		conn, _ := activeConnections.Get(sid)
		caps := []any{}
		if conn.ClientCapabilities != nil && conn.ClientCapabilities.Len() > 0 {
			for _, k := range conn.ClientCapabilities.Keys() {
				caps = append(caps, k)
			}
		}
		clientStats := entities.NewOrderedMap[any]()
		clientStats.Set("session_id", sid)
		clientStats.Set("client_name", srvGet(conn.ClientInfo, "name", "unknown"))
		clientStats.Set("client_version", srvGet(conn.ClientInfo, "version", "unknown"))
		clientStats.Set("connected_at", value_objects.IsoFormatNaive(conn.ConnectedAt))
		clientStats.Set("last_activity", value_objects.IsoFormatNaive(conn.LastActivity))
		clientStats.Set("connection_age_seconds", now.Sub(conn.ConnectedAt).Seconds())
		clientStats.Set("health_checks", conn.HealthCheckCount)
		clientStats.Set("is_healthy", conn.IsHealthy)
		clientStats.Set("capabilities", caps)
		activeClients = append(activeClients, clientStats)
	}

	stats := entities.NewOrderedMap[any]()
	stats.Set("server_info", serverInfo)
	stats.Set("connections", connections)
	stats.Set("active_clients", activeClients)
	return stats
}

// healthMonitorLoop mirrors ConnectionManager._health_monitor_loop. The Python
// `except Exception` is a per-iteration recover; CancelledError is the stop channel.
func (m *ConnectionManager) healthMonitorLoop(ch chan struct{}) {
	defer m.wg.Done()
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
			m.CleanupStaleConnections()
			active := m.GetActiveConnections()
			m.mu.Lock()
			for _, conn := range active.Values() {
				conn.HealthCheckCount++
			}
			m.mu.Unlock()
		}()

		select {
		case <-ch:
			return
		case <-time.After(time.Duration(m.HealthCheckInterval) * time.Second):
		}
	}
}

// HandleServerRestart mirrors ConnectionManager.handle_server_restart.
func (m *ConnectionManager) HandleServerRestart() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.ServerRestartCount++
	m.ServerStartTime = time.Now()
	for _, sid := range m.Connections.Keys() {
		c, _ := m.Connections.Get(sid)
		c.IsHealthy = false
	}
}

// GetReconnectionInfo mirrors ConnectionManager.get_reconnection_info.
func (m *ConnectionManager) GetReconnectionInfo() *entities.OrderedMap[any] {
	m.mu.Lock()
	defer m.mu.Unlock()
	action := "continue"
	if m.ServerRestartCount > 0 {
		action = "reconnect"
	}
	info := entities.NewOrderedMap[any]()
	info.Set("server_restart_count", m.ServerRestartCount)
	info.Set("server_start_time", value_objects.IsoFormatNaive(m.ServerStartTime))
	info.Set("recommended_action", action)
	info.Set("health_endpoint", "/health")
	info.Set("mcp_endpoint", "/mcp/")
	info.Set("connection_timeout_minutes", m.ConnectionTimeout)
	return info
}

// Global connection manager instance (Python module-level _connection_manager).
var (
	connectionManagerMu sync.Mutex
	connectionManager   *ConnectionManager
)

// GetConnectionManager mirrors get_connection_manager(): create on first use and
// start monitoring.
func GetConnectionManager() *ConnectionManager {
	connectionManagerMu.Lock()
	defer connectionManagerMu.Unlock()
	if connectionManager == nil {
		connectionManager = NewConnectionManager()
		connectionManager.StartMonitoring()
	}
	return connectionManager
}

// CleanupConnectionManager mirrors cleanup_connection_manager().
func CleanupConnectionManager() {
	connectionManagerMu.Lock()
	defer connectionManagerMu.Unlock()
	if connectionManager != nil {
		connectionManager.StopMonitoring()
		connectionManager = nil
	}
}
