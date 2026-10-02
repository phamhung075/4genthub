// context_notifications.go ports context_notifications.py. It reuses the WebSocket
// interface and helpers from agent_communication_hub.go (same package). The asyncio
// queue and processing loop become a mutex-guarded queue and a goroutine.
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

// EventType is context_notifications.EventType.
type EventType string

const (
	EventTypeCreated          EventType = "context.created"
	EventTypeUpdated          EventType = "context.updated"
	EventTypeDeleted          EventType = "context.deleted"
	EventTypeDelegated        EventType = "context.delegated"
	EventTypeInherited        EventType = "context.inherited"
	EventTypeBatchUpdated     EventType = "context.batch_updated"
	EventTypeCacheInvalidated EventType = "context.cache_invalidated"
)

// EventTypeValues lists the members in declaration order.
var EventTypeValues = []EventType{EventTypeCreated, EventTypeUpdated, EventTypeDeleted, EventTypeDelegated, EventTypeInherited, EventTypeBatchUpdated, EventTypeCacheInvalidated}

func (e EventType) String() string { return string(e) }

// SubscriptionScope is context_notifications.SubscriptionScope.
type SubscriptionScope string

const (
	SubscriptionScopeGlobal  SubscriptionScope = "global"
	SubscriptionScopeUser    SubscriptionScope = "user"
	SubscriptionScopeProject SubscriptionScope = "project"
	SubscriptionScopeBranch  SubscriptionScope = "branch"
	SubscriptionScopeTask    SubscriptionScope = "task"
)

// SubscriptionScopeValues lists the members in declaration order.
var SubscriptionScopeValues = []SubscriptionScope{SubscriptionScopeGlobal, SubscriptionScopeUser, SubscriptionScopeProject, SubscriptionScopeBranch, SubscriptionScopeTask}

func (e SubscriptionScope) String() string { return string(e) }

// ParseSubscriptionScope mirrors SubscriptionScope(value).
func ParseSubscriptionScope(v string) (SubscriptionScope, error) {
	for _, s := range SubscriptionScopeValues {
		if string(s) == v {
			return s, nil
		}
	}
	return "", &value_objects.ValueError{Msg: fmt.Sprintf("'%s' is not a valid SubscriptionScope", v)}
}

// ContextEvent is context_notifications.ContextEvent.
type ContextEvent struct {
	EventType EventType
	Level     string
	ContextID string
	UserID    string
	Timestamp time.Time
	Data      *entities.OrderedMap[any]
	Metadata  *entities.OrderedMap[any]
}

// NewContextEvent applies the defaults (timestamp now, metadata {}).
func NewContextEvent(eventType EventType, level, contextID, userID string, data, metadata *entities.OrderedMap[any]) *ContextEvent {
	if metadata == nil {
		metadata = entities.NewOrderedMap[any]()
	}
	return &ContextEvent{
		EventType: eventType, Level: level, ContextID: contextID, UserID: userID,
		Timestamp: time.Now().UTC(), Data: data, Metadata: metadata,
	}
}

// ToDict mirrors to_dict.
func (e *ContextEvent) ToDict() *entities.OrderedMap[any] {
	return wsObj(
		"event_type", string(e.EventType),
		"level", e.Level,
		"context_id", e.ContextID,
		"user_id", e.UserID,
		"timestamp", value_objects.IsoFormat(e.Timestamp),
		"data", e.Data,
		"metadata", e.Metadata,
	)
}

// Subscription is context_notifications.Subscription.
type Subscription struct {
	ClientID     string
	WebSocket    WebSocket
	Scope        SubscriptionScope
	Filters      *entities.OrderedMap[any]
	CreatedAt    time.Time
	LastActivity time.Time
}

// Matches mirrors matches.
func (s *Subscription) Matches(event *ContextEvent) bool {
	switch s.Scope {
	case SubscriptionScopeGlobal:
		// global scope receives all events
	case SubscriptionScopeUser:
		if !value_objects.PyEqual(event.UserID, wsGetOrNil(s.Filters, "user_id")) {
			return false
		}
	case SubscriptionScopeProject:
		if !value_objects.PyEqual(wsGetOrNil(event.Metadata, "project_id"), wsGetOrNil(s.Filters, "project_id")) {
			return false
		}
	case SubscriptionScopeBranch:
		if !value_objects.PyEqual(wsGetOrNil(event.Metadata, "git_branch_id"), wsGetOrNil(s.Filters, "git_branch_id")) {
			return false
		}
	case SubscriptionScopeTask:
		if !value_objects.PyEqual(event.ContextID, wsGetOrNil(s.Filters, "task_id")) {
			return false
		}
	}
	if wsHas(s.Filters, "event_types") {
		eventTypes, _ := s.Filters.Get("event_types")
		// event.event_type is an EventType enum in Python and never equals a plain string
		// filter item; comparing boxed values keeps that behaviour.
		if !wsContains(eventTypes, event.EventType) {
			return false
		}
	}
	if wsHas(s.Filters, "levels") {
		levels, _ := s.Filters.Get("levels")
		if !wsContains(levels, event.Level) {
			return false
		}
	}
	return true
}

func wsHas(m *entities.OrderedMap[any], key string) bool {
	if m == nil {
		return false
	}
	return m.Has(key)
}

func wsContains(container any, v any) bool {
	items := wsStringOrList(container)
	for _, item := range items {
		if value_objects.PyEqual(item, v) {
			return true
		}
	}
	return false
}

func wsStringOrList(v any) []any {
	switch x := v.(type) {
	case []any:
		return x
	case []string:
		out := make([]any, len(x))
		for i, s := range x {
			out[i] = s
		}
		return out
	case string:
		out := []any{}
		for _, r := range x {
			out = append(out, string(r))
		}
		return out
	}
	return []any{}
}

// ContextEventHandler is a registered event handler (Python Callable awaited with event).
type ContextEventHandler func(event *ContextEvent) error

// contextEventQueue is an unbounded queue with a timed get, mirroring asyncio.Queue.
type contextEventQueue struct {
	mu     sync.Mutex
	items  []*ContextEvent
	notify chan struct{}
}

func newContextEventQueue() *contextEventQueue {
	return &contextEventQueue{notify: make(chan struct{}, 1)}
}

func (q *contextEventQueue) put(e *ContextEvent) {
	q.mu.Lock()
	q.items = append(q.items, e)
	q.mu.Unlock()
	select {
	case q.notify <- struct{}{}:
	default:
	}
}

func (q *contextEventQueue) get(timeout time.Duration) (*ContextEvent, bool) {
	deadline := time.Now().Add(timeout)
	for {
		q.mu.Lock()
		if len(q.items) > 0 {
			e := q.items[0]
			q.items = q.items[1:]
			q.mu.Unlock()
			return e, true
		}
		q.mu.Unlock()
		remaining := time.Until(deadline)
		if remaining <= 0 {
			return nil, false
		}
		select {
		case <-q.notify:
		case <-time.After(remaining):
		}
	}
}

func (q *contextEventQueue) qsize() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}

// ContextNotificationService is context_notifications.ContextNotificationService.
type ContextNotificationService struct {
	Subscriptions *entities.OrderedMap[*Subscription]
	EventHandlers []ContextEventHandler
	Stats         *entities.OrderedMap[any]

	queue   *contextEventQueue
	running atomic.Bool
	stopCh  chan struct{}
	wg      sync.WaitGroup
}

// NewContextNotificationService applies the constructor defaults.
func NewContextNotificationService() *ContextNotificationService {
	s := &ContextNotificationService{
		Subscriptions: entities.NewOrderedMap[*Subscription](),
		EventHandlers: []ContextEventHandler{},
		Stats:         entities.NewOrderedMap[any](),
		queue:         newContextEventQueue(),
	}
	s.Stats.Set("events_sent", 0)
	s.Stats.Set("events_queued", 0)
	s.Stats.Set("active_connections", 0)
	s.Stats.Set("total_connections", 0)
	s.Stats.Set("errors", 0)
	return s
}

func (s *ContextNotificationService) incStat(key string, delta int) {
	n := 0
	if v, ok := s.Stats.Get(key); ok {
		if x, ok := v.(int); ok {
			n = x
		}
	}
	s.Stats.Set(key, n+delta)
}

// Start mirrors start.
func (s *ContextNotificationService) Start() {
	if s.running.Load() {
		return
	}
	s.running.Store(true)
	s.stopCh = make(chan struct{})
	s.wg.Add(1)
	go func() { defer s.wg.Done(); s.processEvents() }()
}

// Stop mirrors stop.
func (s *ContextNotificationService) Stop() {
	if !s.running.Load() {
		return
	}
	s.running.Store(false)
	close(s.stopCh)
	s.wg.Wait()
}

func (s *ContextNotificationService) processEvents() {
	for s.running.Load() {
		event, ok := s.queue.get(time.Second)
		if !ok {
			continue
		}
		if utilities.SafeCall(func() {
			s.BroadcastEvent(event)
			for _, handler := range s.EventHandlers {
				_ = handler(event)
			}
		}) != nil {
			s.incStat("errors", 1)
		}
	}
}

// BroadcastEvent mirrors _broadcast_event.
func (s *ContextNotificationService) BroadcastEvent(event *ContextEvent) {
	disconnected := []string{}
	for _, clientID := range s.Subscriptions.Keys() {
		subscription, _ := s.Subscriptions.Get(clientID)
		if !subscription.Matches(event) {
			continue
		}
		websocket := subscription.WebSocket
		if websocket == nil {
			continue
		}
		if websocket.ClientState() == WebSocketStateConnected {
			if err := websocket.SendJSON(event.ToDict()); err != nil {
				disconnected = append(disconnected, clientID)
				s.incStat("errors", 1)
				continue
			}
			subscription.LastActivity = time.Now().UTC()
			s.incStat("events_sent", 1)
		} else {
			disconnected = append(disconnected, clientID)
		}
	}
	for _, clientID := range disconnected {
		s.Unsubscribe(clientID)
	}
}

// Subscribe mirrors subscribe.
func (s *ContextNotificationService) Subscribe(websocket WebSocket, clientID string, scope SubscriptionScope, filters *entities.OrderedMap[any]) *Subscription {
	if filters == nil {
		filters = entities.NewOrderedMap[any]()
	}
	now := time.Now().UTC()
	subscription := &Subscription{
		ClientID: clientID, WebSocket: websocket, Scope: scope, Filters: filters,
		CreatedAt: now, LastActivity: now,
	}
	s.Subscriptions.Set(clientID, subscription)
	s.Stats.Set("active_connections", s.Subscriptions.Len())
	s.incStat("total_connections", 1)

	if websocket != nil {
		_ = websocket.SendJSON(wsObj(
			"type", "welcome",
			"client_id", clientID,
			"scope", string(scope),
			"timestamp", value_objects.IsoFormat(time.Now().UTC()),
		))
	}
	return subscription
}

// Unsubscribe mirrors unsubscribe.
func (s *ContextNotificationService) Unsubscribe(clientID string) {
	if s.Subscriptions.Has(clientID) {
		s.Subscriptions.Delete(clientID)
		s.Stats.Set("active_connections", s.Subscriptions.Len())
	}
}

// Notify mirrors notify.
func (s *ContextNotificationService) Notify(eventType EventType, level, contextID, userID string, data, metadata *entities.OrderedMap[any]) {
	event := NewContextEvent(eventType, level, contextID, userID, data, metadata)
	s.queue.put(event)
	s.incStat("events_queued", 1)
}

// AddEventHandler mirrors add_event_handler.
func (s *ContextNotificationService) AddEventHandler(handler ContextEventHandler) {
	s.EventHandlers = append(s.EventHandlers, handler)
}

// GetStats mirrors get_stats.
func (s *ContextNotificationService) GetStats() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	for _, k := range s.Stats.Keys() {
		v, _ := s.Stats.Get(k)
		out.Set(k, v)
	}
	out.Set("queue_size", s.queue.qsize())
	subs := []any{}
	for _, clientID := range s.Subscriptions.Keys() {
		sub, _ := s.Subscriptions.Get(clientID)
		subs = append(subs, wsObj(
			"client_id", sub.ClientID,
			"scope", string(sub.Scope),
			"created_at", value_objects.IsoFormat(sub.CreatedAt),
			"last_activity", value_objects.IsoFormat(sub.LastActivity),
		))
	}
	out.Set("subscriptions", subs)
	return out
}

// Heartbeat mirrors heartbeat.
func (s *ContextNotificationService) Heartbeat() {
	disconnected := []string{}
	for _, clientID := range s.Subscriptions.Keys() {
		subscription, _ := s.Subscriptions.Get(clientID)
		if subscription.WebSocket == nil {
			continue
		}
		if subscription.WebSocket.ClientState() == WebSocketStateConnected {
			_ = subscription.WebSocket.SendJSON(wsObj("type", "heartbeat", "timestamp", value_objects.IsoFormat(time.Now().UTC())))
		} else {
			disconnected = append(disconnected, clientID)
		}
	}
	for _, clientID := range disconnected {
		s.Unsubscribe(clientID)
	}
}

// WebSocketManager is context_notifications.WebSocketManager.
type WebSocketManager struct {
	NotificationService *ContextNotificationService
	ActiveConnections   []WebSocket
}

// NewWebSocketManager mirrors the constructor.
func NewWebSocketManager(notificationService *ContextNotificationService) *WebSocketManager {
	return &WebSocketManager{NotificationService: notificationService, ActiveConnections: []WebSocket{}}
}

func (m *WebSocketManager) addConnection(websocket WebSocket) {
	for _, c := range m.ActiveConnections {
		if c == websocket {
			return
		}
	}
	m.ActiveConnections = append(m.ActiveConnections, websocket)
}

func (m *WebSocketManager) discardConnection(websocket WebSocket) {
	for i, c := range m.ActiveConnections {
		if c == websocket {
			m.ActiveConnections = append(m.ActiveConnections[:i], m.ActiveConnections[i+1:]...)
			return
		}
	}
}

// Connect mirrors connect.
func (m *WebSocketManager) Connect(websocket WebSocket, clientID string) error {
	if err := websocket.Accept(); err != nil {
		return err
	}
	m.addConnection(websocket)
	filters := entities.NewOrderedMap[any]()
	filters.Set("user_id", clientID)
	m.NotificationService.Subscribe(websocket, clientID, SubscriptionScopeUser, filters)
	return nil
}

// Disconnect mirrors disconnect.
func (m *WebSocketManager) Disconnect(websocket WebSocket, clientID string) {
	m.discardConnection(websocket)
	m.NotificationService.Unsubscribe(clientID)
}

// HandleMessage mirrors handle_message.
func (m *WebSocketManager) HandleMessage(websocket WebSocket, clientID string, message *entities.OrderedMap[any]) error {
	msgType, _ := wsGetOrNil(message, "type").(string)
	switch msgType {
	case "subscribe":
		scopeRaw := "user"
		if v, ok := message.Get("scope"); ok && v != nil {
			scopeRaw = value_objects.PyStr(v)
		}
		scope, err := ParseSubscriptionScope(scopeRaw)
		if err != nil {
			return err
		}
		filters, _ := wsGetOrNil(message, "filters").(*entities.OrderedMap[any])
		m.NotificationService.Subscribe(websocket, clientID, scope, filters)
		return websocket.SendJSON(wsObj("type", "subscribed", "scope", string(scope), "filters", filtersOrEmpty(filters)))
	case "ping":
		return websocket.SendJSON(wsObj("type", "pong", "timestamp", value_objects.IsoFormat(time.Now().UTC())))
	case "get_stats":
		return websocket.SendJSON(wsObj("type", "stats", "data", m.NotificationService.GetStats()))
	default:
		return websocket.SendJSON(wsObj("type", "error", "message", "Unknown message type: "+value_objects.PyStr(msgType)))
	}
}

func filtersOrEmpty(filters *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	if filters == nil {
		return entities.NewOrderedMap[any]()
	}
	return filters
}

var (
	globalNotificationMu      sync.Mutex
	globalNotificationService *ContextNotificationService
	globalWebSocketManager    *WebSocketManager
)

// GetNotificationService is get_notification_service.
func GetNotificationService() *ContextNotificationService {
	globalNotificationMu.Lock()
	defer globalNotificationMu.Unlock()
	if globalNotificationService == nil {
		globalNotificationService = NewContextNotificationService()
	}
	return globalNotificationService
}

// GetWebSocketManager is get_websocket_manager.
func GetWebSocketManager() *WebSocketManager {
	globalNotificationMu.Lock()
	defer globalNotificationMu.Unlock()
	if globalWebSocketManager == nil {
		globalWebSocketManager = NewWebSocketManager(getNotificationServiceLocked())
	}
	return globalWebSocketManager
}

// getNotificationServiceLocked is the singleton lookup used while globalNotificationMu is
// already held.
func getNotificationServiceLocked() *ContextNotificationService {
	if globalNotificationService == nil {
		globalNotificationService = NewContextNotificationService()
	}
	return globalNotificationService
}

// WebsocketEndpoint mirrors websocket_endpoint.
func WebsocketEndpoint(ctx context.Context, websocket WebSocket, clientID string) {
	manager := GetWebSocketManager()
	if err := manager.Connect(websocket, clientID); err != nil {
		return
	}
	defer manager.Disconnect(websocket, clientID)

	for {
		data, err := websocket.ReceiveJSON(ctx)
		if err != nil {
			var disconnect *WebSocketDisconnect
			if errors.As(err, &disconnect) {
				break
			}
			break
		}
		message, _ := data.(*entities.OrderedMap[any])
		if message == nil {
			continue
		}
		if err := manager.HandleMessage(websocket, clientID, message); err != nil {
			break
		}
	}
}
