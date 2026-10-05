package infrastructure

import (
	"fmt"
	"reflect"
	"sort"
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// StoredEvent represents a stored event with metadata (event_store.StoredEvent).
type StoredEvent struct {
	EventID       string
	EventType     string
	EventData     map[string]any
	AggregateID   *string
	AggregateType *string
	Timestamp     time.Time
	Version       int
	Metadata      map[string]any
}

// EventStore persists domain events (event_store.EventStore). The Python SQLite backend
// is not ported (Go's stdlib has no SQLite driver); this is an in-memory store with the
// same observable methods. StoragePath is retained for shape.
type EventStore struct {
	StoragePath   string
	EventHandlers []any

	mu     sync.Mutex
	events []StoredEvent
	byID   map[string]int
}

// NewEventStore mirrors EventStore.__init__; a nil path becomes ":memory:".
func NewEventStore(storagePath *string) *EventStore {
	path := ":memory:"
	if storagePath != nil {
		path = *storagePath
	}
	return &EventStore{StoragePath: path, EventHandlers: []any{}, events: []StoredEvent{}, byID: map[string]int{}}
}

// Append mirrors EventStore.append and returns the generated event ID.
func (s *EventStore) Append(event any) string {
	eventID := value_objects.NewUUIDv4()
	aggregateID := extractAggregateID(event)
	aggregateType := extractAggregateType(event)
	stored := StoredEvent{
		EventID:       eventID,
		EventType:     eventTypeName(event),
		EventData:     serializeEvent(event),
		AggregateID:   aggregateID,
		AggregateType: aggregateType,
		Timestamp:     time.Now().UTC().Truncate(time.Microsecond),
		Version:       1,
		Metadata:      map[string]any{"source": "event_store", "environment": "production"},
	}
	s.storeEvent(stored)
	return eventID
}

func (s *EventStore) storeEvent(event StoredEvent) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.byID[event.EventID] = len(s.events)
	s.events = append(s.events, event)
}

// GetEvents mirrors EventStore.get_events (timestamp descending, then limit).
func (s *EventStore) GetEvents(aggregateID, eventType *string, fromTimestamp, toTimestamp *time.Time, limit int) []StoredEvent {
	s.mu.Lock()
	matched := make([]StoredEvent, 0, len(s.events))
	for _, e := range s.events {
		if aggregateID != nil && *aggregateID != "" && (e.AggregateID == nil || *e.AggregateID != *aggregateID) {
			continue
		}
		if eventType != nil && *eventType != "" && e.EventType != *eventType {
			continue
		}
		if fromTimestamp != nil && e.Timestamp.Before(*fromTimestamp) {
			continue
		}
		if toTimestamp != nil && e.Timestamp.After(*toTimestamp) {
			continue
		}
		matched = append(matched, e)
	}
	s.mu.Unlock()

	sort.SliceStable(matched, func(i, j int) bool { return matched[i].Timestamp.After(matched[j].Timestamp) })
	if limit >= 0 && len(matched) > limit {
		matched = matched[:limit]
	}
	return matched
}

// GetAggregateEvents mirrors EventStore.get_aggregate_events (timestamp ascending).
func (s *EventStore) GetAggregateEvents(aggregateID string, fromVersion *int) []StoredEvent {
	s.mu.Lock()
	matched := make([]StoredEvent, 0, len(s.events))
	for _, e := range s.events {
		if e.AggregateID == nil || *e.AggregateID != aggregateID {
			continue
		}
		if fromVersion != nil && *fromVersion != 0 && !(e.Version > *fromVersion) {
			continue
		}
		matched = append(matched, e)
	}
	s.mu.Unlock()

	sort.SliceStable(matched, func(i, j int) bool { return matched[i].Timestamp.Before(matched[j].Timestamp) })
	return matched
}

// GetEventByID mirrors EventStore.get_event_by_id.
func (s *EventStore) GetEventByID(eventID string) *StoredEvent {
	s.mu.Lock()
	defer s.mu.Unlock()
	idx, ok := s.byID[eventID]
	if !ok {
		return nil
	}
	event := s.events[idx]
	return &event
}

// GetEventCount mirrors EventStore.get_event_count.
func (s *EventStore) GetEventCount(aggregateID, eventType *string) int {
	s.mu.Lock()
	defer s.mu.Unlock()
	count := 0
	for _, e := range s.events {
		if aggregateID != nil && *aggregateID != "" && (e.AggregateID == nil || *e.AggregateID != *aggregateID) {
			continue
		}
		if eventType != nil && *eventType != "" && e.EventType != *eventType {
			continue
		}
		count++
	}
	return count
}

// CreateSnapshot mirrors EventStore.create_snapshot.
func (s *EventStore) CreateSnapshot(aggregateID, aggregateType string, snapshotData map[string]any, version int) string {
	eventID := value_objects.NewUUIDv4()
	s.storeEvent(StoredEvent{
		EventID:       eventID,
		EventType:     aggregateType + "Snapshot",
		EventData:     snapshotData,
		AggregateID:   &aggregateID,
		AggregateType: &aggregateType,
		Timestamp:     time.Now().UTC().Truncate(time.Microsecond),
		Version:       version,
		Metadata:      map[string]any{"is_snapshot": true},
	})
	return eventID
}

// GetLatestSnapshot mirrors EventStore.get_latest_snapshot.
func (s *EventStore) GetLatestSnapshot(aggregateID string) *StoredEvent {
	s.mu.Lock()
	var matched []StoredEvent
	for _, e := range s.events {
		if (e.AggregateID != nil && *e.AggregateID == aggregateID) && strings.HasSuffix(e.EventType, "Snapshot") {
			matched = append(matched, e)
		}
	}
	s.mu.Unlock()
	if len(matched) == 0 {
		return nil
	}
	sort.SliceStable(matched, func(i, j int) bool { return matched[i].Timestamp.After(matched[j].Timestamp) })
	event := matched[0]
	return &event
}

// Clear mirrors EventStore.clear.
func (s *EventStore) Clear() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.events = []StoredEvent{}
	s.byID = map[string]int{}
}

// String is EventStore.__repr__.
func (s *EventStore) String() string { return "EventStore(storage_path='" + s.StoragePath + "')" }

// eventTypeName is event.__class__.__name__.
func eventTypeName(event any) string {
	t := reflect.TypeOf(event)
	for t != nil && t.Kind() == reflect.Pointer {
		t = t.Elem()
	}
	if t == nil {
		return ""
	}
	return t.Name()
}

// extractAggregateID mirrors the aggregate_id/task_id/project_id lookup in append. A
// present-but-None aggregate_id becomes the string "None" (Python str(None)), a quirk
// that is preserved.
func extractAggregateID(event any) *string {
	for _, name := range []string{"AggregateID", "TaskID", "ProjectID"} {
		if fv, ok := fieldByName(event, name); ok {
			s := reflectString(fv)
			return &s
		}
	}
	return nil
}

// extractAggregateType mirrors the aggregate_type lookup and class-name inference.
func extractAggregateType(event any) *string {
	if fv, ok := fieldByName(event, "AggregateType"); ok {
		if isNilValue(fv) {
			return nil
		}
		s := reflectString(fv)
		return &s
	}
	name := eventTypeName(event)
	switch {
	case strings.Contains(name, "Task"):
		t := "Task"
		return &t
	case strings.Contains(name, "Project"):
		t := "Project"
		return &t
	case strings.Contains(name, "Agent"):
		t := "Agent"
		return &t
	}
	return nil
}

// serializeEvent mirrors EventStore._serialize_event.
func serializeEvent(event any) map[string]any {
	if td, ok := event.(interface{ ToDict() map[string]any }); ok {
		return td.ToDict()
	}
	v := reflect.ValueOf(event)
	for v.IsValid() && (v.Kind() == reflect.Pointer || v.Kind() == reflect.Interface) {
		if v.IsNil() {
			return map[string]any{"data": "None"}
		}
		v = v.Elem()
	}
	if !v.IsValid() || v.Kind() != reflect.Struct {
		return map[string]any{"data": value_objects.PyStr(event)}
	}
	data := map[string]any{}
	collectSerializedFields(v, data)
	return data
}

func collectSerializedFields(v reflect.Value, data map[string]any) {
	t := v.Type()
	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)
		if f.PkgPath != "" { // unexported: never in Python's __dict__
			continue
		}
		fv := v.Field(i)
		if f.Anonymous {
			inner := fv
			for inner.IsValid() && (inner.Kind() == reflect.Pointer || inner.Kind() == reflect.Interface) {
				if inner.IsNil() {
					break
				}
				inner = inner.Elem()
			}
			if inner.IsValid() && inner.Kind() == reflect.Struct {
				collectSerializedFields(inner, data)
				continue
			}
		}
		name := f.Name
		if tag := f.Tag.Get("dict"); tag != "" {
			name = strings.Split(tag, ",")[0]
		}
		if strings.HasPrefix(name, "_") || !fv.CanInterface() {
			continue
		}
		data[name] = serializeFieldValue(fv)
	}
}

// serializeFieldValue mirrors the datetime/__dict__ special cases of _serialize_event.
func serializeFieldValue(fv reflect.Value) any {
	for fv.IsValid() && fv.Kind() == reflect.Interface {
		if fv.IsNil() {
			return nil
		}
		fv = fv.Elem()
	}
	if !fv.IsValid() {
		return nil
	}
	if fv.Type() == reflect.TypeOf(time.Time{}) {
		return value_objects.IsoFormat(fv.Interface().(time.Time))
	}
	switch fv.Kind() {
	case reflect.Pointer:
		if fv.IsNil() {
			return nil
		}
		return reflectString(fv)
	case reflect.Struct:
		return reflectString(fv)
	}
	if fv.CanInterface() {
		return fv.Interface()
	}
	return nil
}

// reflectString is Python str(value) for a reflected field.
func reflectString(v reflect.Value) string {
	if isNilValue(v) {
		return "None"
	}
	for v.Kind() == reflect.Pointer || v.Kind() == reflect.Interface {
		v = v.Elem()
	}
	if v.CanInterface() {
		if s, ok := v.Interface().(fmt.Stringer); ok {
			return s.String()
		}
	}
	if v.CanInterface() {
		return value_objects.PyStr(v.Interface())
	}
	return "None"
}

func isNilValue(v reflect.Value) bool {
	switch v.Kind() {
	case reflect.Pointer, reflect.Interface, reflect.Map, reflect.Slice, reflect.Func:
		return v.IsNil()
	}
	return false
}

// fieldByName finds an exported field by its Go name, preferring outer fields and then
// recursing into anonymous embedded structs (Go promotion).
func fieldByName(event any, name string) (reflect.Value, bool) {
	v := reflect.ValueOf(event)
	for v.IsValid() && (v.Kind() == reflect.Pointer || v.Kind() == reflect.Interface) {
		if v.IsNil() {
			return reflect.Value{}, false
		}
		v = v.Elem()
	}
	if !v.IsValid() || v.Kind() != reflect.Struct {
		return reflect.Value{}, false
	}
	return structFieldByName(v, name)
}

func structFieldByName(v reflect.Value, name string) (reflect.Value, bool) {
	t := v.Type()
	for i := 0; i < t.NumField(); i++ {
		if t.Field(i).Name == name {
			return v.Field(i), true
		}
	}
	for i := 0; i < t.NumField(); i++ {
		if !t.Field(i).Anonymous {
			continue
		}
		inner := v.Field(i)
		for inner.IsValid() && (inner.Kind() == reflect.Pointer || inner.Kind() == reflect.Interface) {
			if inner.IsNil() {
				break
			}
			inner = inner.Elem()
		}
		if inner.IsValid() && inner.Kind() == reflect.Struct {
			if fv, ok := structFieldByName(inner, name); ok {
				return fv, true
			}
		}
	}
	return reflect.Value{}, false
}

var (
	globalEventStoreMu sync.Mutex
	globalEventStore   *EventStore
)

// GetEventStore returns the global event store, creating it on first use.
func GetEventStore(storagePath *string) *EventStore {
	globalEventStoreMu.Lock()
	defer globalEventStoreMu.Unlock()
	if globalEventStore == nil {
		globalEventStore = NewEventStore(storagePath)
	}
	return globalEventStore
}

// ResetEventStore mirrors reset_event_store.
func ResetEventStore() {
	globalEventStoreMu.Lock()
	defer globalEventStoreMu.Unlock()
	if globalEventStore != nil {
		globalEventStore.Clear()
	}
	globalEventStore = nil
}
