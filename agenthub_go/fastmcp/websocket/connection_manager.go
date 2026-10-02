package websocket

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/services/protocols"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// WebSocket is the minimal FastAPI/Starlette WebSocket surface used by this package.
// There is no Go port of Starlette, so a concrete implementation must return a
// *WebSocketDisconnect (or wrap one) from SendText/ReceiveText on disconnect.
type WebSocket interface {
	Accept(ctx context.Context) error
	Close(ctx context.Context, code int, reason string) error
	SendText(ctx context.Context, data string) error
	ReceiveText(ctx context.Context) (string, error)
}

// WebSocketDisconnect mirrors fastapi.WebSocketDisconnect.
type WebSocketDisconnect struct {
	Code   int
	Reason string
}

func (e *WebSocketDisconnect) Error() string {
	return fmt.Sprintf("WebSocket disconnected (code=%d, reason=%q)", e.Code, e.Reason)
}

// IsWebSocketDisconnect reports whether err is or wraps a WebSocketDisconnect.
func IsWebSocketDisconnect(err error) bool {
	var d *WebSocketDisconnect
	return errors.As(err, &d)
}

// DBSession is one database session. Python's session_factory is an async context
// manager yielding a session that CascadeCalculator wraps.
type DBSession interface {
	Provider() protocols.CascadeDataProvider
	Close(ctx context.Context) error
}

// SessionFactory mirrors the Python session_factory callable.
type SessionFactory func() (DBSession, error)

// WSQueue is an unbounded FIFO queue, like asyncio.Queue.
type WSQueue struct {
	mu    sync.Mutex
	items []*WSMessage
}

// NewWSQueue builds an empty queue.
func NewWSQueue() *WSQueue { return &WSQueue{items: []*WSMessage{}} }

// Put appends a message.
func (q *WSQueue) Put(m *WSMessage) {
	q.mu.Lock()
	q.items = append(q.items, m)
	q.mu.Unlock()
}

// Get removes and returns the oldest message.
func (q *WSQueue) Get() (*WSMessage, bool) {
	q.mu.Lock()
	defer q.mu.Unlock()
	if len(q.items) == 0 {
		return nil, false
	}
	m := q.items[0]
	q.items = q.items[1:]
	return m, true
}

// GetTimeout waits up to d for a message (asyncio.wait_for(queue.get(), timeout=d)).
func (q *WSQueue) GetTimeout(ctx context.Context, d time.Duration) (*WSMessage, bool) {
	deadline := time.Now().Add(d)
	for {
		if m, ok := q.Get(); ok {
			return m, true
		}
		if time.Now().After(deadline) {
			return nil, false
		}
		select {
		case <-ctx.Done():
			return nil, false
		case <-time.After(2 * time.Millisecond):
		}
	}
}

// GetNowait removes and returns the oldest message without blocking.
func (q *WSQueue) GetNowait() (*WSMessage, bool) { return q.Get() }

// QSize is asyncio.Queue.qsize().
func (q *WSQueue) QSize() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}

// Empty is asyncio.Queue.empty().
func (q *WSQueue) Empty() bool { return q.QSize() == 0 }

// ConnectionManager manages WebSocket connections with dual-track processing.
type ConnectionManager struct {
	mu sync.Mutex

	Connections  *entities.OrderedMap[WebSocket]
	UserSessions *entities.OrderedMap[string]
	SessionUsers *entities.OrderedMap[string]

	AIBatchQueue   *WSQueue
	BatchProcessor *BatchProcessor

	SequenceCounter int

	SessionFactory    SessionFactory
	CascadeCalculator *services.CascadeCalculator

	ActiveUsers        entities.StringSet
	HeartbeatIntervals *entities.OrderedMap[float64]
}

// NewConnectionManager builds a manager around a database session factory.
func NewConnectionManager(sessionFactory SessionFactory) *ConnectionManager {
	return &ConnectionManager{
		Connections:        entities.NewOrderedMap[WebSocket](),
		UserSessions:       entities.NewOrderedMap[string](),
		SessionUsers:       entities.NewOrderedMap[string](),
		AIBatchQueue:       NewWSQueue(),
		SessionFactory:     sessionFactory,
		ActiveUsers:        entities.StringSet{},
		HeartbeatIntervals: entities.NewOrderedMap[float64](),
	}
}

// NewSession runs the session factory and returns the session (nil when the factory is
// nil or fails).
func (c *ConnectionManager) newSession() DBSession {
	if c.SessionFactory == nil {
		return nil
	}
	session, err := c.SessionFactory()
	if err != nil {
		return nil
	}
	return session
}

// Connect accepts a new WebSocket connection and performs the initial sync.
func (c *ConnectionManager) Connect(ctx context.Context, websocket WebSocket, userID string, sessionID *string) (string, error) {
	sid := ""
	if sessionID == nil {
		sid = value_objects.NewUUIDv4()
	} else {
		sid = *sessionID
	}

	if err := websocket.Accept(ctx); err != nil {
		return "", err
	}

	c.mu.Lock()
	c.Connections.Set(userID, websocket)
	c.UserSessions.Set(userID, sid)
	c.SessionUsers.Set(sid, userID)
	c.ActiveUsers.Add(userID)
	c.mu.Unlock()

	if session := c.newSession(); session != nil {
		c.CascadeCalculator = services.NewCascadeCalculator(session.Provider())
		c.SendInitialSync(ctx, userID, sid)
		session.Close(ctx)
	}

	return sid, nil
}

// Disconnect closes a WebSocket connection and cleans up tracking.
func (c *ConnectionManager) Disconnect(ctx context.Context, userID string) {
	c.mu.Lock()
	websocket, ok := c.Connections.Get(userID)
	if !ok {
		c.mu.Unlock()
		return
	}
	sessionID, _ := c.UserSessions.Get(userID)
	c.mu.Unlock()

	if websocket != nil {
		websocket.Close(ctx, 1000, "")
	}

	c.mu.Lock()
	c.Connections.Delete(userID)
	c.UserSessions.Delete(userID)
	if sessionID != "" {
		c.SessionUsers.Delete(sessionID)
	}
	c.ActiveUsers.Remove(userID)
	c.HeartbeatIntervals.Delete(userID)
	c.mu.Unlock()
}

// ProcessMessage processes an incoming WebSocket message with v2.0 validation.
func (c *ConnectionManager) ProcessMessage(ctx context.Context, userID, rawMessage string) {
	decoded, err := entities.DecodeJSON([]byte(rawMessage))
	if err != nil {
		c.SendError(ctx, userID, "Invalid JSON: "+err.Error(), nil)
		return
	}

	om, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		c.SendError(ctx, userID, "Internal server error", nil)
		return
	}

	validated, err := ValidateMessage(om)
	if err != nil {
		var versionErr *InvalidVersionError
		var sizeErr *MessageSizeError
		var protocolErr *ProtocolError
		switch {
		case errors.As(err, &versionErr):
			c.SendError(ctx, userID, "Protocol error: "+err.Error(), nil)
		case errors.As(err, &sizeErr):
			c.SendError(ctx, userID, "Message too large: "+err.Error(), nil)
		case errors.As(err, &protocolErr):
			c.SendError(ctx, userID, "Validation error: "+err.Error(), nil)
		default:
			c.SendError(ctx, userID, "Internal server error", nil)
		}
		return
	}

	switch validated.Metadata.Source {
	case SourceTypeUser:
		c.processUserMessage(ctx, userID, validated)
	case SourceTypeMCPAI:
		c.queueAIMessage(validated)
	}
}

func (c *ConnectionManager) processUserMessage(ctx context.Context, userID string, message *WSMessage) {
	var sessionID *string
	if sid, ok := c.UserSessions.Get(userID); ok {
		sessionID = &sid
	}

	primaryData := message.Payload.Data.Primary
	var entityID *string
	if id, ok := primaryEntityID(primaryData); ok {
		if s, ok := id.(string); ok {
			entityID = &s
		}
	}

	var calc *services.CascadeCalculator
	if session := c.newSession(); session != nil {
		calc = services.NewCascadeCalculator(session.Provider())
		defer session.Close(ctx)
	}

	userUpdate := CreateUserUpdate(ctx, message.Payload.Entity, message.Payload.Action, primaryData, calc,
		entityID, &userID, sessionID, message.Metadata.CorrelationID, c.NextSequence())

	c.BroadcastImmediate(ctx, userUpdate)
}

func (c *ConnectionManager) queueAIMessage(message *WSMessage) {
	c.AIBatchQueue.Put(message)
}

// BroadcastImmediate broadcasts a message to all connected users.
func (c *ConnectionManager) BroadcastImmediate(ctx context.Context, message *WSMessage) {
	c.mu.Lock()
	if c.Connections.Len() == 0 {
		c.mu.Unlock()
		return
	}
	type conn struct {
		user string
		ws   WebSocket
	}
	conns := make([]conn, 0, c.Connections.Len())
	for _, uid := range c.Connections.Keys() {
		ws, _ := c.Connections.Get(uid)
		conns = append(conns, conn{uid, ws})
	}
	c.mu.Unlock()

	messageJSON := message.ModelDumpJSON()
	disconnected := []string{}
	for _, cn := range conns {
		if err := cn.ws.SendText(ctx, messageJSON); err != nil {
			disconnected = append(disconnected, cn.user)
		}
	}

	for _, uid := range disconnected {
		c.Disconnect(ctx, uid)
	}
}

// BroadcastBatch broadcasts an AI batch message to all connected users.
func (c *ConnectionManager) BroadcastBatch(ctx context.Context, batchMessage *WSMessage) {
	c.BroadcastImmediate(ctx, batchMessage)
}

// SendToUser sends a message to a specific user.
func (c *ConnectionManager) SendToUser(ctx context.Context, userID string, message *WSMessage) bool {
	c.mu.Lock()
	websocket, ok := c.Connections.Get(userID)
	c.mu.Unlock()
	if !ok {
		return false
	}
	if err := websocket.SendText(ctx, message.ModelDumpJSON()); err != nil {
		if IsWebSocketDisconnect(err) {
			c.Disconnect(ctx, userID)
		}
		return false
	}
	return true
}

// SendError sends an error message to a specific user.
func (c *ConnectionManager) SendError(ctx context.Context, userID, errorMessage string, errorCode *string) {
	var sessionID *string
	if sid, ok := c.UserSessions.Get(userID); ok {
		sessionID = &sid
	}
	errorMsg := CreateError(errorMessage, errorCode, nil, sessionID, nil, c.NextSequence())
	c.SendToUser(ctx, userID, errorMsg)
}

// SendInitialSync sends initial synchronization data when a user connects.
func (c *ConnectionManager) SendInitialSync(ctx context.Context, userID, sessionID string) {
	syncData := wsDict(
		"type", "initial_sync",
		"user_id", userID,
		"timestamp", value_objects.IsoFormat(nowUTC()),
		"message", "WebSocket v2.0 connection established",
	)
	syncMessage := CreateSync(syncData, &sessionID, &userID, c.NextSequence())
	c.SendToUser(ctx, userID, syncMessage)
}

// SendHeartbeat sends a heartbeat message to a specific user.
func (c *ConnectionManager) SendHeartbeat(ctx context.Context, userID string) {
	var sessionID *string
	if sid, ok := c.UserSessions.Get(userID); ok {
		sessionID = &sid
	}
	heartbeat := CreateHeartbeat(sessionID, c.NextSequence())
	c.SendToUser(ctx, userID, heartbeat)
}

// NextSequence returns the next message sequence number.
func (c *ConnectionManager) NextSequence() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.SequenceCounter++
	return c.SequenceCounter
}

// GetConnectionStats returns connection statistics for monitoring.
func (c *ConnectionManager) GetConnectionStats() *entities.OrderedMap[any] {
	c.mu.Lock()
	defer c.mu.Unlock()

	activeUsers := make([]any, 0, c.ActiveUsers.Len())
	for _, u := range c.ActiveUsers.Items() {
		activeUsers = append(activeUsers, u)
	}

	userSessions := entities.NewOrderedMap[any]()
	for _, k := range c.UserSessions.Keys() {
		v, _ := c.UserSessions.Get(k)
		userSessions.Set(k, v)
	}
	sessionUsers := entities.NewOrderedMap[any]()
	for _, k := range c.SessionUsers.Keys() {
		v, _ := c.SessionUsers.Get(k)
		sessionUsers.Set(k, v)
	}

	return wsDict(
		"total_connections", c.Connections.Len(),
		"active_users", activeUsers,
		"queue_size", c.AIBatchQueue.QSize(),
		"sequence_counter", c.SequenceCounter,
		"sessions", wsDict("user_sessions", userSessions, "session_users", sessionUsers),
	)
}

// Cleanup disconnects all connections and clears the queue.
func (c *ConnectionManager) Cleanup(ctx context.Context) {
	c.mu.Lock()
	userIDs := c.Connections.Keys()
	c.mu.Unlock()

	for _, userID := range userIDs {
		c.Disconnect(ctx, userID)
	}

	for !c.AIBatchQueue.Empty() {
		if _, ok := c.AIBatchQueue.GetNowait(); !ok {
			break
		}
	}
}

// IsUserConnected reports whether a user is currently connected.
func (c *ConnectionManager) IsUserConnected(userID string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	_, ok := c.Connections.Get(userID)
	return ok && c.ActiveUsers.Has(userID)
}

// primaryEntityID extracts the "id" from a primary payload (dict or list of dicts).
func primaryEntityID(primary any) (any, bool) {
	if om, ok := primary.(*entities.OrderedMap[any]); ok {
		if v, ok := om.Get("id"); ok && v != nil {
			return v, true
		}
		return nil, false
	}
	if list, ok := primary.([]any); ok && len(list) > 0 {
		if om, ok := list[0].(*entities.OrderedMap[any]); ok {
			if v, ok := om.Get("id"); ok && v != nil {
				return v, true
			}
		}
	}
	return nil, false
}
