// Package websocket ports task_management/infrastructure/websocket.
//
// agent_communication_hub.go ports agent_communication_hub.py. FastAPI/Starlette's
// WebSocket is represented by the WebSocket interface (only the methods this module
// uses); the asyncio background loops become goroutines with a stop channel. Logging is
// dropped.
package websocket

import (
	"agenthub/fastmcp/utilities"
	"context"
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// WebSocketState mirrors starlette.websockets.WebSocketState values used here.
const (
	WebSocketStateConnected    = "CONNECTED"
	WebSocketStateDisconnected = "DISCONNECTED"
)

// WebSocketDisconnect mirrors starlette.websockets.WebSocketDisconnect.
type WebSocketDisconnect struct{}

func (e *WebSocketDisconnect) Error() string { return "WebSocket disconnect" }

// WebSocket is the subset of FastAPI/Starlette's WebSocket used by this package. Python's
// asyncio.wait_for timeout becomes a context deadline on the receive calls.
type WebSocket interface {
	Accept() error
	SendText(text string) error
	SendJSON(data any) error
	ReceiveText(ctx context.Context) (string, error)
	ReceiveJSON(ctx context.Context) (any, error)
	Close() error
	ClientState() string
}

// MessageType is agent_communication_hub.MessageType.
type MessageType string

const (
	MessageTypeConnect              MessageType = "connect"
	MessageTypeDisconnect           MessageType = "disconnect"
	MessageTypeHeartbeat            MessageType = "heartbeat"
	MessageTypeAck                  MessageType = "acknowledge"
	MessageTypeStatusUpdate         MessageType = "status_update"
	MessageTypeResourceUpdate       MessageType = "resource_update"
	MessageTypeTaskUpdate           MessageType = "task_update"
	MessageTypeCoordinationRequest  MessageType = "coordination_request"
	MessageTypeCoordinationResponse MessageType = "coordination_response"
	MessageTypeWorkHandoff          MessageType = "work_handoff"
	MessageTypeDirectMessage        MessageType = "direct_message"
	MessageTypeBroadcastMessage     MessageType = "broadcast_message"
	MessageTypeGroupMessage         MessageType = "group_message"
	MessageTypeNotification         MessageType = "notification"
	MessageTypeAlert                MessageType = "alert"
	MessageTypeError                MessageType = "error"
)

// MessageTypeValues lists the members in declaration order.
var MessageTypeValues = []MessageType{
	MessageTypeConnect, MessageTypeDisconnect, MessageTypeHeartbeat, MessageTypeAck,
	MessageTypeStatusUpdate, MessageTypeResourceUpdate, MessageTypeTaskUpdate,
	MessageTypeCoordinationRequest, MessageTypeCoordinationResponse, MessageTypeWorkHandoff,
	MessageTypeDirectMessage, MessageTypeBroadcastMessage, MessageTypeGroupMessage,
	MessageTypeNotification, MessageTypeAlert, MessageTypeError,
}

func (e MessageType) String() string { return string(e) }

// ParseMessageType mirrors MessageType(value).
func ParseMessageType(v string) (MessageType, error) {
	for _, m := range MessageTypeValues {
		if string(m) == v {
			return m, nil
		}
	}
	return "", &value_objects.ValueError{Msg: fmt.Sprintf("'%s' is not a valid MessageType", v)}
}

// WebSocketMessage is agent_communication_hub.WebSocketMessage.
type WebSocketMessage struct {
	ID            string
	Type          MessageType
	FromAgent     string
	ToAgents      []string
	Timestamp     time.Time
	Payload       *entities.OrderedMap[any]
	RequiresAck   bool
	CorrelationID *string
}

// ToJSON mirrors to_json: dataclasses.asdict order with type and timestamp overridden,
// serialized by json.dumps (default separators).
func (m *WebSocketMessage) ToJSON() (string, error) {
	d := entities.NewOrderedMap[any]()
	d.Set("id", m.ID)
	d.Set("type", string(m.Type))
	d.Set("from_agent", m.FromAgent)
	d.Set("to_agents", m.ToAgents)
	d.Set("timestamp", value_objects.IsoFormat(m.Timestamp))
	d.Set("payload", m.Payload)
	d.Set("requires_ack", m.RequiresAck)
	d.Set("correlation_id", wsOptString(m.CorrelationID))
	return value_objects.PyJSONDumps(d, -1)
}

func wsOptString(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// wsStringList converts a decoded JSON array to []string via str().
func wsStringList(v any) []string {
	switch x := v.(type) {
	case []string:
		return x
	case []any:
		out := make([]string, 0, len(x))
		for _, e := range x {
			out = append(out, value_objects.PyStr(e))
		}
		return out
	case nil:
		return []string{}
	case string:
		out := []string{}
		for _, r := range x {
			out = append(out, string(r))
		}
		return out
	}
	return []string{}
}

// FromJSON mirrors from_json.
func FromJSON(jsonStr string) (*WebSocketMessage, error) {
	raw, err := entities.DecodeJSON([]byte(jsonStr))
	if err != nil {
		return nil, err
	}
	d, ok := raw.(*entities.OrderedMap[any])
	if !ok {
		return nil, &value_objects.TypeError{Msg: "message must be a JSON object"}
	}
	mustKeys := []string{"id", "type", "from_agent", "to_agents", "timestamp", "payload"}
	for _, k := range mustKeys {
		if !d.Has(k) {
			return nil, &value_objects.TypeError{Msg: "missing required field: " + k}
		}
	}
	typRaw, _ := d.Get("type")
	typ, err := ParseMessageType(value_objects.PyStr(typRaw))
	if err != nil {
		return nil, err
	}
	tsRaw, _ := d.Get("timestamp")
	ts, err := value_objects.ParseISO(value_objects.PyStr(tsRaw))
	if err != nil {
		return nil, err
	}
	id, _ := d.Get("id")
	fromAgent, _ := d.Get("from_agent")
	toAgents, _ := d.Get("to_agents")
	payload, _ := d.Get("payload")
	payloadMap, _ := payload.(*entities.OrderedMap[any])
	requiresAck := false
	if v, ok := d.Get("requires_ack"); ok {
		requiresAck = value_objects.PyTruthy(v)
	}
	var correlationID *string
	if v, ok := d.Get("correlation_id"); ok && v != nil {
		s := value_objects.PyStr(v)
		correlationID = &s
	}
	return &WebSocketMessage{
		ID:            value_objects.PyStr(id),
		Type:          typ,
		FromAgent:     value_objects.PyStr(fromAgent),
		ToAgents:      wsStringList(toAgents),
		Timestamp:     ts,
		Payload:       payloadMap,
		RequiresAck:   requiresAck,
		CorrelationID: correlationID,
	}, nil
}

// AgentConnection is agent_communication_hub.AgentConnection.
type AgentConnection struct {
	AgentID       string
	SessionID     string
	WebSocket     WebSocket
	ConnectedAt   time.Time
	LastHeartbeat time.Time
	Subscriptions *entities.StringSet
}

// NewAgentConnection mirrors __post_init__ (subscriptions default to an empty set).
func NewAgentConnection(agentID, sessionID string, websocket WebSocket, connectedAt, lastHeartbeat time.Time) *AgentConnection {
	return &AgentConnection{
		AgentID: agentID, SessionID: sessionID, WebSocket: websocket,
		ConnectedAt: connectedAt, LastHeartbeat: lastHeartbeat, Subscriptions: &entities.StringSet{},
	}
}

// SendMessage mirrors send_message.
func (c *AgentConnection) SendMessage(message *WebSocketMessage) bool {
	if c.WebSocket != nil && c.WebSocket.ClientState() == WebSocketStateConnected {
		text, err := message.ToJSON()
		if err == nil && c.WebSocket.SendText(text) == nil {
			return true
		}
	}
	return false
}

// IsAlive mirrors is_alive.
func (c *AgentConnection) IsAlive(timeoutSeconds int) bool {
	elapsed := value_objects.PyTotalSeconds(time.Now().UTC().Sub(c.LastHeartbeat))
	return elapsed < float64(timeoutSeconds)
}

// MessageHandler is a registered handler (Python Callable awaited with the message).
type MessageHandler func(message *WebSocketMessage) error

// StatusTracker is the part of RealTimeStatusTracker the hub uses. Python passes the raw
// payload values; the interface keeps the dynamic pass-through.
type StatusTracker interface {
	UpdateAgentStatus(ctx context.Context, agentID string, status, currentTaskID, currentActivity, metadata any) error
}

// AgentCommunicationHub is agent_communication_hub.AgentCommunicationHub.
type AgentCommunicationHub struct {
	StatusTracker     StatusTracker
	HeartbeatInterval int
	MessageTimeout    int

	Connections *entities.OrderedMap[*AgentConnection]
	Sessions    map[string]*entities.AgentSession

	PendingAcks     map[string]*WebSocketMessage
	MessageHandlers map[MessageType][]MessageHandler

	Channels *entities.OrderedMap[*entities.StringSet]
	Metrics  *entities.OrderedMap[any]

	runMu   sync.Mutex
	running atomic.Bool
	stopCh  chan struct{}
	wg      sync.WaitGroup
}

// NewAgentCommunicationHub applies the constructor defaults.
func NewAgentCommunicationHub(statusTracker StatusTracker, heartbeatInterval, messageTimeout int) *AgentCommunicationHub {
	h := &AgentCommunicationHub{
		StatusTracker:     statusTracker,
		HeartbeatInterval: heartbeatInterval,
		MessageTimeout:    messageTimeout,
		Connections:       entities.NewOrderedMap[*AgentConnection](),
		Sessions:          map[string]*entities.AgentSession{},
		PendingAcks:       map[string]*WebSocketMessage{},
		MessageHandlers:   map[MessageType][]MessageHandler{},
		Channels:          entities.NewOrderedMap[*entities.StringSet](),
		Metrics:           entities.NewOrderedMap[any](),
	}
	h.Metrics.Set("total_connections", 0)
	h.Metrics.Set("messages_sent", 0)
	h.Metrics.Set("messages_received", 0)
	h.Metrics.Set("messages_failed", 0)
	h.Metrics.Set("avg_latency_ms", 0)
	h.Channels.Set("global", &entities.StringSet{})
	h.Channels.Set("status", &entities.StringSet{})
	h.Channels.Set("coordination", &entities.StringSet{})
	return h
}

func (h *AgentCommunicationHub) incMetric(key string, delta int) {
	n := 0
	if v, ok := h.Metrics.Get(key); ok {
		if x, ok := v.(int); ok {
			n = x
		}
	}
	h.Metrics.Set(key, n+delta)
}

// Start mirrors start.
func (h *AgentCommunicationHub) Start() {
	if h.running.Load() {
		return
	}
	h.runMu.Lock()
	defer h.runMu.Unlock()
	if h.running.Load() {
		return
	}
	h.running.Store(true)
	h.stopCh = make(chan struct{})
	h.wg.Add(2)
	go func() { defer h.wg.Done(); h.heartbeatLoop() }()
	go func() { defer h.wg.Done(); h.cleanupLoop() }()
}

// Stop mirrors stop: stops the background loops and disconnects every agent.
func (h *AgentCommunicationHub) Stop() {
	h.runMu.Lock()
	if !h.running.Load() {
		h.runMu.Unlock()
		return
	}
	h.running.Store(false)
	close(h.stopCh)
	h.runMu.Unlock()
	h.wg.Wait()
	for _, id := range h.Connections.Keys() {
		h.DisconnectAgent(id)
	}
}

func (h *AgentCommunicationHub) heartbeatLoop() {
	for h.running.Load() {
		rec := utilities.SafeCall(func() {
			for _, id := range h.Connections.Keys() {
				h.SendHeartbeat(id)
			}
		})
		wait := time.Duration(h.HeartbeatInterval) * time.Second
		if rec != nil {
			wait = 5 * time.Second
		}
		select {
		case <-h.stopCh:
			return
		case <-time.After(wait):
		}
	}
}

func (h *AgentCommunicationHub) cleanupLoop() {
	for h.running.Load() {
		rec := utilities.SafeCall(func() {
			dead := []string{}
			for _, id := range h.Connections.Keys() {
				c, _ := h.Connections.Get(id)
				if !c.IsAlive(60) {
					dead = append(dead, id)
				}
			}
			for _, id := range dead {
				h.DisconnectAgent(id)
			}
		})
		wait := 60 * time.Second
		if rec != nil {
			wait = 30 * time.Second
		}
		select {
		case <-h.stopCh:
			return
		case <-time.After(wait):
		}
	}
}

// ConnectAgent mirrors connect_agent.
func (h *AgentCommunicationHub) ConnectAgent(agentID, sessionID string, websocket WebSocket) error {
	if err := websocket.Accept(); err != nil {
		return err
	}
	now := time.Now().UTC()
	connection := NewAgentConnection(agentID, sessionID, websocket, now, now)
	h.Connections.Set(agentID, connection)
	h.incMetric("total_connections", 1)
	global, _ := h.Channels.Get("global")
	global.Add(agentID)

	welcome := &WebSocketMessage{
		ID: value_objects.NewUUIDv4(), Type: MessageTypeConnect, FromAgent: "hub",
		ToAgents: []string{agentID}, Timestamp: time.Now().UTC(),
		Payload: wsObj(
			"status", "connected",
			"session_id", sessionID,
			"hub_version", "1.0.0",
			"available_channels", h.Channels.Keys(),
		),
	}
	connection.SendMessage(welcome)

	h.BroadcastToChannel("global", MessageTypeNotification, wsObj(
		"event", "agent_connected",
		"agent_id", agentID,
		"timestamp", value_objects.IsoFormat(time.Now().UTC()),
	), []string{agentID})
	return nil
}

// DisconnectAgent mirrors disconnect_agent.
func (h *AgentCommunicationHub) DisconnectAgent(agentID string) {
	connection, ok := h.Connections.Get(agentID)
	if !ok {
		return
	}
	if connection.WebSocket != nil && connection.WebSocket.ClientState() == WebSocketStateConnected {
		_ = connection.WebSocket.Close()
	}
	for _, channel := range h.Channels.Keys() {
		set, _ := h.Channels.Get(channel)
		set.Remove(agentID)
	}
	h.Connections.Delete(agentID)
	h.BroadcastToChannel("global", MessageTypeNotification, wsObj(
		"event", "agent_disconnected",
		"agent_id", agentID,
		"timestamp", value_objects.IsoFormat(time.Now().UTC()),
	), nil)
}

// HandleAgentConnection mirrors handle_agent_connection.
func (h *AgentCommunicationHub) HandleAgentConnection(ctx context.Context, websocket WebSocket, agentID, sessionID string) {
	if err := h.ConnectAgent(agentID, sessionID, websocket); err != nil {
		return
	}
	defer h.DisconnectAgent(agentID)

	for h.running.Load() {
		recvCtx, cancel := context.WithTimeout(ctx, time.Duration(h.HeartbeatInterval*2)*time.Second)
		text, err := websocket.ReceiveText(recvCtx)
		cancel()
		if err != nil {
			var disconnect *WebSocketDisconnect
			if errors.As(err, &disconnect) {
				break
			}
			if errors.Is(err, context.DeadlineExceeded) {
				if _, ok := h.Connections.Get(agentID); ok {
					h.SendHeartbeat(agentID)
				}
				continue
			}
			break
		}
		h.ProcessMessage(agentID, text)
	}
}

// ProcessMessage mirrors process_message.
func (h *AgentCommunicationHub) ProcessMessage(fromAgent, messageText string) {
	message, err := FromJSON(messageText)
	if err != nil {
		h.SendError(fromAgent, err.Error())
		return
	}
	h.incMetric("messages_received", 1)

	if connection, ok := h.Connections.Get(fromAgent); ok {
		connection.LastHeartbeat = time.Now().UTC()
	}

	if message.Type == MessageTypeAck {
		h.HandleAcknowledgment(message)
		return
	}

	switch message.Type {
	case MessageTypeHeartbeat:
		// heartbeat already updated above
	case MessageTypeStatusUpdate:
		h.HandleStatusUpdate(fromAgent, message)
	case MessageTypeDirectMessage:
		h.RouteDirectMessage(message)
	case MessageTypeBroadcastMessage:
		h.RouteBroadcastMessage(message)
	case MessageTypeGroupMessage:
		h.RouteGroupMessage(message)
	case MessageTypeCoordinationRequest:
		h.HandleCoordinationRequest(message)
	default:
		h.CallMessageHandlers(message.Type, message)
	}

	if message.RequiresAck {
		h.SendAcknowledgment(fromAgent, message.ID)
	}
}

// SendMessage mirrors send_message.
func (h *AgentCommunicationHub) SendMessage(toAgent string, messageType MessageType, payload *entities.OrderedMap[any], requiresAck bool, correlationID *string) bool {
	connection, ok := h.Connections.Get(toAgent)
	if !ok {
		return false
	}
	message := &WebSocketMessage{
		ID: value_objects.NewUUIDv4(), Type: messageType, FromAgent: "hub",
		ToAgents: []string{toAgent}, Timestamp: time.Now().UTC(), Payload: payload,
		RequiresAck: requiresAck, CorrelationID: correlationID,
	}
	success := connection.SendMessage(message)
	if success {
		h.incMetric("messages_sent", 1)
		if requiresAck {
			h.PendingAcks[message.ID] = message
		}
	} else {
		h.incMetric("messages_failed", 1)
	}
	return success
}

// BroadcastMessage mirrors broadcast_message.
func (h *AgentCommunicationHub) BroadcastMessage(messageType MessageType, payload *entities.OrderedMap[any], exclude []string) int {
	message := &WebSocketMessage{
		ID: value_objects.NewUUIDv4(), Type: messageType, FromAgent: "hub",
		ToAgents: []string{}, Timestamp: time.Now().UTC(), Payload: payload,
	}
	sentCount := 0
	for _, agentID := range h.Connections.Keys() {
		if stringIn(exclude, agentID) {
			continue
		}
		connection, _ := h.Connections.Get(agentID)
		if connection.SendMessage(message) {
			sentCount++
		}
	}
	h.incMetric("messages_sent", sentCount)
	return sentCount
}

// BroadcastToChannel mirrors broadcast_to_channel.
func (h *AgentCommunicationHub) BroadcastToChannel(channel string, messageType MessageType, payload *entities.OrderedMap[any], exclude []string) int {
	set, ok := h.Channels.Get(channel)
	if !ok {
		return 0
	}
	sentCount := 0
	for _, agentID := range set.Items() {
		if stringIn(exclude, agentID) {
			continue
		}
		if _, ok := h.Connections.Get(agentID); !ok {
			continue
		}
		if h.SendMessage(agentID, messageType, payload, false, nil) {
			sentCount++
		}
	}
	return sentCount
}

// SubscribeToChannel mirrors subscribe_to_channel.
func (h *AgentCommunicationHub) SubscribeToChannel(agentID, channel string) bool {
	connection, ok := h.Connections.Get(agentID)
	if !ok {
		return false
	}
	set, ok := h.Channels.Get(channel)
	if !ok {
		set = &entities.StringSet{}
		h.Channels.Set(channel, set)
	}
	set.Add(agentID)
	connection.Subscriptions.Add(channel)
	h.SendMessage(agentID, MessageTypeNotification, wsObj("event", "channel_subscribed", "channel", channel), false, nil)
	return true
}

// UnsubscribeFromChannel mirrors unsubscribe_from_channel.
func (h *AgentCommunicationHub) UnsubscribeFromChannel(agentID, channel string) bool {
	if set, ok := h.Channels.Get(channel); ok {
		set.Remove(agentID)
	}
	if connection, ok := h.Connections.Get(agentID); ok {
		connection.Subscriptions.Remove(channel)
	}
	return true
}

// RegisterMessageHandler mirrors register_message_handler.
func (h *AgentCommunicationHub) RegisterMessageHandler(messageType MessageType, handler MessageHandler) {
	h.MessageHandlers[messageType] = append(h.MessageHandlers[messageType], handler)
}

// CallMessageHandlers mirrors call_message_handlers.
func (h *AgentCommunicationHub) CallMessageHandlers(messageType MessageType, message *WebSocketMessage) {
	for _, handler := range h.MessageHandlers[messageType] {
		_ = handler(message)
	}
}

// HandleStatusUpdate mirrors handle_status_update.
func (h *AgentCommunicationHub) HandleStatusUpdate(fromAgent string, message *WebSocketMessage) {
	if h.StatusTracker != nil {
		h.StatusTracker.UpdateAgentStatus(context.Background(), fromAgent,
			wsGetOrNil(message.Payload, "status"),
			wsGetOrNil(message.Payload, "current_task_id"),
			wsGetOrNil(message.Payload, "current_activity"),
			wsGetOrNil(message.Payload, "metadata"))
	}
	payload := wsObj("agent_id", fromAgent)
	for _, k := range message.Payload.Keys() {
		v, _ := message.Payload.Get(k)
		payload.Set(k, v)
	}
	h.BroadcastToChannel("status", MessageTypeStatusUpdate, payload, []string{fromAgent})
}

// HandleCoordinationRequest mirrors handle_coordination_request.
func (h *AgentCommunicationHub) HandleCoordinationRequest(message *WebSocketMessage) {
	payload := message.Payload
	targetRaw := wsGetOrNil(payload, "target_agent")
	target, _ := targetRaw.(string)
	if target != "" {
		if _, ok := h.Connections.Get(target); ok {
			h.SendMessage(target, MessageTypeCoordinationRequest, payload, true, &message.ID)
		}
	}
	h.BroadcastToChannel("coordination", MessageTypeNotification, wsObj(
		"event", "coordination_request",
		"from_agent", message.FromAgent,
		"to_agent", targetRaw,
		"type", wsGetOrNil(payload, "coordination_type"),
	), nil)
}

// RouteDirectMessage mirrors route_direct_message.
func (h *AgentCommunicationHub) RouteDirectMessage(message *WebSocketMessage) {
	for _, target := range message.ToAgents {
		if connection, ok := h.Connections.Get(target); ok {
			connection.SendMessage(message)
		}
	}
}

// RouteBroadcastMessage mirrors route_broadcast_message.
func (h *AgentCommunicationHub) RouteBroadcastMessage(message *WebSocketMessage) {
	h.BroadcastMessage(MessageTypeBroadcastMessage, message.Payload, []string{message.FromAgent})
}

// RouteGroupMessage mirrors route_group_message.
func (h *AgentCommunicationHub) RouteGroupMessage(message *WebSocketMessage) {
	channel, _ := wsGetOrNil(message.Payload, "channel").(string)
	if channel != "" {
		h.BroadcastToChannel(channel, MessageTypeGroupMessage, message.Payload, []string{message.FromAgent})
	}
}

// SendHeartbeat mirrors send_heartbeat.
func (h *AgentCommunicationHub) SendHeartbeat(agentID string) {
	h.SendMessage(agentID, MessageTypeHeartbeat, wsObj("timestamp", value_objects.IsoFormat(time.Now().UTC())), true, nil)
}

// SendAcknowledgment mirrors send_acknowledgment.
func (h *AgentCommunicationHub) SendAcknowledgment(toAgent, messageID string) {
	h.SendMessage(toAgent, MessageTypeAck, wsObj("ack_message_id", messageID), false, nil)
}

// HandleAcknowledgment mirrors handle_acknowledgment.
func (h *AgentCommunicationHub) HandleAcknowledgment(message *WebSocketMessage) {
	ackID := wsGetOrNil(message.Payload, "ack_message_id")
	if ackID == nil {
		return
	}
	delete(h.PendingAcks, value_objects.PyStr(ackID))
}

// SendError mirrors send_error.
func (h *AgentCommunicationHub) SendError(toAgent, errorMessage string) {
	h.SendMessage(toAgent, MessageTypeError, wsObj("error", errorMessage), false, nil)
}

// GetConnectionStatus mirrors get_connection_status.
func (h *AgentCommunicationHub) GetConnectionStatus() *entities.OrderedMap[any] {
	channels := entities.NewOrderedMap[any]()
	for _, channel := range h.Channels.Keys() {
		set, _ := h.Channels.Get(channel)
		channels.Set(channel, set.Len())
	}
	return wsObj(
		"active_connections", h.Connections.Len(),
		"agents", h.Connections.Keys(),
		"channels", channels,
		"pending_acks", len(h.PendingAcks),
		"metrics", h.Metrics,
	)
}

// GetAgentInfo mirrors get_agent_info.
func (h *AgentCommunicationHub) GetAgentInfo(agentID string) *entities.OrderedMap[any] {
	connection, ok := h.Connections.Get(agentID)
	if !ok {
		return nil
	}
	return wsObj(
		"agent_id", agentID,
		"session_id", connection.SessionID,
		"connected_at", value_objects.IsoFormat(connection.ConnectedAt),
		"last_heartbeat", value_objects.IsoFormat(connection.LastHeartbeat),
		"subscriptions", connection.Subscriptions.Items(),
		"is_alive", connection.IsAlive(60),
	)
}

func wsObj(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func wsGetOrNil(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func stringIn(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}
