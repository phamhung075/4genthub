// Redis-based EventStore for MCP session persistence (Python
// fastmcp/server/session_store.py).
//
// The RedisEventStore class is not ported: it is built on `redis.asyncio`, and the
// Go module has no Redis client (would require github.com/redis/go-redis/v9). Only
// the Redis-independent parts are ported: SessionEvent, the EventStore contract,
// MemoryEventStore, create_event_store (which returns MemoryEventStore while Redis
// is unavailable, exactly like Python when REDIS_AVAILABLE is False), and the
// global store helpers.
package server

import (
	"reflect"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// zpSessionRedisAvailable mirrors REDIS_AVAILABLE (redis.asyncio not importable in Go).
const zpSessionRedisAvailable = false

// SessionEvent mirrors the SessionEvent dataclass.
type SessionEvent struct {
	SessionID string
	StreamID  string
	EventID   string
	EventType string
	EventData *entities.OrderedMap[any]
	Timestamp float64
	TTL       *float64
}

// ToDict mirrors SessionEvent.to_dict (dataclasses.asdict field order).
func (e *SessionEvent) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("session_id", e.SessionID)
	m.Set("stream_id", e.StreamID)
	m.Set("event_id", e.EventID)
	m.Set("event_type", e.EventType)
	m.Set("event_data", e.EventData)
	m.Set("timestamp", e.Timestamp)
	if e.TTL == nil {
		m.Set("ttl", nil)
	} else {
		m.Set("ttl", *e.TTL)
	}
	return m
}

// zpSessionEventFromDict mirrors SessionEvent.from_dict.
func zpSessionEventFromDict(data *entities.OrderedMap[any]) *SessionEvent {
	e := &SessionEvent{}
	if v, ok := data.Get("session_id"); ok {
		e.SessionID, _ = v.(string)
	}
	if v, ok := data.Get("stream_id"); ok {
		e.StreamID, _ = v.(string)
	}
	if v, ok := data.Get("event_id"); ok {
		e.EventID, _ = v.(string)
	}
	if v, ok := data.Get("event_type"); ok {
		e.EventType, _ = v.(string)
	}
	if v, ok := data.Get("event_data"); ok {
		e.EventData, _ = v.(*entities.OrderedMap[any])
	}
	if v, ok := data.Get("timestamp"); ok {
		e.Timestamp = zpSessionFloat(v)
	}
	if v, ok := data.Get("ttl"); ok && v != nil {
		f := zpSessionFloat(v)
		e.TTL = &f
	}
	return e
}

func zpSessionFloat(v any) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case float32:
		return float64(n)
	case int:
		return float64(n)
	case int64:
		return float64(n)
	case *float64:
		if n != nil {
			return *n
		}
	}
	return 0
}

// IsExpired mirrors SessionEvent.is_expired.
func (e *SessionEvent) IsExpired() bool {
	if e.TTL == nil {
		return false
	}
	return zpSessionNow()-e.Timestamp > *e.TTL
}

// GetNumericID mirrors SessionEvent.get_numeric_id.
func (e *SessionEvent) GetNumericID() int {
	parts := strings.Split(e.EventID, ":")
	if len(parts) >= 2 {
		if n, ok := zpSessionAtoi(parts[1]); ok {
			return n
		}
	}
	return int(zpSessionNow() * 1000)
}

func zpSessionAtoi(s string) (int, bool) {
	if s == "" {
		return 0, false
	}
	neg := false
	i := 0
	if s[0] == '+' || s[0] == '-' {
		neg = s[0] == '-'
		i = 1
	}
	if i >= len(s) {
		return 0, false
	}
	n := 0
	for ; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return 0, false
		}
		n = n*10 + int(s[i]-'0')
	}
	if neg {
		n = -n
	}
	return n, true
}

var zpSessionNow = func() float64 { return float64(time.Now().UnixNano()) / 1e9 }

// zpSessionGenerateEventID mirrors _generate_event_id.
func zpSessionGenerateEventID(streamID string, sequence *int) string {
	*sequence++
	timestampMS := int(zpSessionNow() * 1000)
	seq := *sequence
	// f"{sequence:06d}"
	digits := ""
	if seq == 0 {
		digits = "0"
	}
	for seq > 0 {
		digits = string(rune('0'+seq%10)) + digits
		seq /= 10
	}
	for len(digits) < 6 {
		digits = "0" + digits
	}
	return streamID + ":" + zpSessionItoa(timestampMS) + ":" + digits
}

func zpSessionItoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var b []byte
	for n > 0 {
		b = append([]byte{byte('0' + n%10)}, b...)
		n /= 10
	}
	if neg {
		return "-" + string(b)
	}
	return string(b)
}

// zpSessionSerializeMessage mirrors RedisEventStore._serialize_message (the
// RedisEventStore and MemoryEventStore copies are identical). Only the Go-visible
// duck-typing branches are reproduced.
func zpSessionSerializeMessage(message any) *entities.OrderedMap[any] {
	result := entities.NewOrderedMap[any]()
	switch m := message.(type) {
	case *entities.OrderedMap[any]:
		result.Set("type", "OrderedMap")
		result.Set("message", value_objects.PyRepr(m))
		for _, k := range m.Keys() {
			v, _ := m.Get(k)
			result.Set(k, v)
		}
		return result
	case map[string]any:
		result.Set("type", "dict")
		result.Set("message", value_objects.PyRepr(m))
		for k, v := range m {
			result.Set(k, v)
		}
		return result
	default:
		result.Set("message", value_objects.PyRepr(message))
		t := reflect.TypeOf(message)
		if t == nil {
			result.Set("type", "NoneType")
		} else {
			result.Set("type", t.Name())
		}
		return result
	}
}

// JSONRPCMessage is the minimal JSON-RPC message shape used by replay.
type JSONRPCMessage struct {
	Method string
	Params *entities.OrderedMap[any]
}

// EventMessage is the minimal EventMessage (message + event_id).
type EventMessage struct {
	Message JSONRPCMessage
	EventID string
}

// EventStore mirrors the mcp EventStore contract plus the session-store additions.
type EventStore interface {
	StoreEvent(streamID string, message any) string
	GetEvents(sessionID string, streamID *string, eventType *string, limit int) []*SessionEvent
	DeleteSession(sessionID string) bool
	ReplayEventsAfter(lastEventID string, sendCallback func(EventMessage)) *string
}

// zpHealthCheckable mirrors hasattr(event_store, "health_check").
type zpHealthCheckable interface {
	HealthCheck() *entities.OrderedMap[any]
}

// zpSessionCountable mirrors hasattr(event_store, "get_session_count").
type zpSessionCountable interface {
	GetSessionCount() int
}

// MemoryEventStore mirrors MemoryEventStore.
type MemoryEventStore struct {
	DefaultTTL          int
	MaxEventsPerSession int

	mu       sync.Mutex
	store    map[string][]*SessionEvent
	sequence int
}

// NewMemoryEventStore mirrors MemoryEventStore.__init__.
func NewMemoryEventStore(defaultTTL int, maxEventsPerSession int) *MemoryEventStore {
	return &MemoryEventStore{
		DefaultTTL:          defaultTTL,
		MaxEventsPerSession: maxEventsPerSession,
		store:               map[string][]*SessionEvent{},
	}
}

// StoreEvent mirrors MemoryEventStore.store_event.
func (s *MemoryEventStore) StoreEvent(streamID string, message any) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	eventID := zpSessionGenerateEventID(streamID, &s.sequence)

	sessionID := streamID
	actualStreamID := streamID
	if idx := strings.Index(streamID, ":"); idx >= 0 {
		sessionID = streamID[:idx]
		actualStreamID = streamID[idx+1:]
	}

	eventData := entities.NewOrderedMap[any]()
	eventData.Set("message", zpSessionSerializeMessage(message))
	eventData.Set("event_id", eventID)

	ttl := float64(s.DefaultTTL)
	event := &SessionEvent{
		SessionID: sessionID,
		StreamID:  streamID,
		EventID:   eventID,
		EventType: "message",
		EventData: eventData,
		Timestamp: zpSessionNow(),
		TTL:       &ttl,
	}

	key := "mcp:session:" + sessionID + ":stream:" + actualStreamID
	events := s.store[key]
	inserted := false
	for i, existing := range events {
		if event.GetNumericID() < existing.GetNumericID() {
			events = append(events[:i], append([]*SessionEvent{event}, events[i:]...)...)
			inserted = true
			break
		}
	}
	if !inserted {
		events = append(events, event)
	}
	if len(events) > s.MaxEventsPerSession {
		events = events[len(events)-s.MaxEventsPerSession:]
	}
	s.store[key] = events
	return eventID
}

// GetEvents mirrors MemoryEventStore.get_events.
func (s *MemoryEventStore) GetEvents(sessionID string, streamID *string, eventType *string, limit int) []*SessionEvent {
	s.mu.Lock()
	defer s.mu.Unlock()
	key := "mcp:session:" + sessionID
	if streamID != nil {
		key = "mcp:session:" + sessionID + ":stream:" + *streamID
	}
	events, ok := s.store[key]
	if !ok {
		return []*SessionEvent{}
	}
	filtered := []*SessionEvent{}
	for _, event := range events {
		if !event.IsExpired() {
			if eventType == nil || event.EventType == *eventType {
				filtered = append(filtered, event)
				if len(filtered) >= limit {
					break
				}
			}
		}
	}
	return filtered
}

// DeleteSession mirrors MemoryEventStore.delete_session.
func (s *MemoryEventStore) DeleteSession(sessionID string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	prefix := "mcp:session:" + sessionID
	for key := range s.store {
		if strings.HasPrefix(key, prefix) {
			delete(s.store, key)
		}
	}
	return true
}

// ReplayEventsAfter mirrors MemoryEventStore.replay_events_after.
func (s *MemoryEventStore) ReplayEventsAfter(lastEventID string, sendCallback func(EventMessage)) *string {
	parts := strings.Split(lastEventID, ":")
	if len(parts) < 2 {
		return nil
	}
	streamID := parts[0]
	lastTimestamp, ok := zpSessionAtoi(parts[1])
	if !ok {
		return nil
	}
	sessionID := streamID
	if idx := strings.Index(streamID, ":"); idx >= 0 {
		sessionID = streamID[:idx]
	}

	sid := sessionID
	events := s.GetEvents(sid, &streamID, nil, 1000)
	replay := []*SessionEvent{}
	for _, event := range events {
		if event.GetNumericID() > lastTimestamp {
			replay = append(replay, event)
		}
	}
	for i := 1; i < len(replay); i++ {
		for j := i; j > 0 && replay[j].GetNumericID() < replay[j-1].GetNumericID(); j-- {
			replay[j], replay[j-1] = replay[j-1], replay[j]
		}
	}

	var lastSent *string
	for _, event := range replay {
		params := entities.NewOrderedMap[any]()
		params.Set("event_type", event.EventType)
		params.Set("event_data", event.EventData)
		params.Set("timestamp", event.Timestamp)
		params.Set("session_id", event.SessionID)
		params.Set("stream_id", event.StreamID)
		msg := JSONRPCMessage{Method: "session/event", Params: params}
		sendCallback(EventMessage{Message: msg, EventID: event.EventID})
		id := event.EventID
		lastSent = &id
	}
	return lastSent
}

// CreateEventStore mirrors create_event_store. With Redis unavailable it always
// returns a MemoryEventStore, matching Python when REDIS_AVAILABLE is False.
func CreateEventStore(redisURL *string, fallbackToMemory bool) EventStore {
	url := ""
	if redisURL != nil {
		url = *redisURL
	}
	if zpSessionRedisAvailable && url != "" {
		// RedisEventStore is not ported (no Redis client in go.mod).
		return NewMemoryEventStore(3600, 1000)
	}
	return NewMemoryEventStore(3600, 1000)
}

// Global event store state.
var (
	zpGlobalEventStoreMu sync.Mutex
	zpGlobalEventStore   EventStore
)

// GetGlobalEventStore mirrors get_global_event_store.
func GetGlobalEventStore() EventStore {
	zpGlobalEventStoreMu.Lock()
	defer zpGlobalEventStoreMu.Unlock()
	if zpGlobalEventStore == nil {
		zpGlobalEventStore = CreateEventStore(nil, true)
	}
	return zpGlobalEventStore
}

// CleanupGlobalEventStore mirrors cleanup_global_event_store.
func CleanupGlobalEventStore() {
	zpGlobalEventStoreMu.Lock()
	defer zpGlobalEventStoreMu.Unlock()
	zpGlobalEventStore = nil
}
