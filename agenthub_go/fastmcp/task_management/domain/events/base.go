// Package events ports task_management/domain/events.
package events

import (
	"reflect"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

var now = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// Event is implemented by every domain event.
type Event interface {
	EventType() string
	ToDict() map[string]any
}

// BaseDomainEvent holds the metadata common to all events: immutable by
// convention, timestamped, identifiable and traceable to an aggregate.
type BaseDomainEvent struct {
	EventID       string    `dict:"event_id"`
	OccurredAt    time.Time `dict:"occurred_at"`
	AggregateID   *string   `dict:"aggregate_id"`
	AggregateType *string   `dict:"aggregate_type"`
	UserID        *string   `dict:"user_id"`
}

// NewBaseDomainEvent generates a new event ID and stamps the event with the current UTC time.
func NewBaseDomainEvent() BaseDomainEvent {
	return BaseDomainEvent{EventID: value_objects.NewUUIDv4(), OccurredAt: now()}
}

// Meta exposes the embedded metadata so generic helpers can populate it.
func (b *BaseDomainEvent) Meta() *BaseDomainEvent { return b }

// CreateEventMetadata returns an empty metadata dictionary.
func CreateEventMetadata() map[string]any { return map[string]any{} }

// CreateDomainEvent builds an event of type T with the aggregate/user metadata
// populated (Python create_domain_event). T must be a struct embedding BaseDomainEvent
// constructed by the caller's New function, passed in as ev.
func CreateDomainEvent[T any, PT interface {
	*T
	Meta() *BaseDomainEvent
}](ev T, aggregateID, aggregateType, userID *string) T {
	meta := PT(&ev).Meta()
	meta.AggregateID, meta.AggregateType, meta.UserID = aggregateID, aggregateType, userID
	return ev
}

// EventToDict mirrors BaseDomainEvent.to_dict (dataclasses.asdict + fixups): every
// `dict`-tagged field (embedded structs flattened, base fields first), event_id and
// occurred_at rendered as string / ISO-8601, plus event_type. Nil slices render as
// empty lists; nil maps and pointers render as nil (None).
func EventToDict(ev any, eventType string) map[string]any {
	out := map[string]any{}
	collectFields(reflect.ValueOf(ev), out)
	if t, ok := out["occurred_at"].(time.Time); ok {
		out["occurred_at"] = value_objects.IsoFormat(t)
	}
	out["event_type"] = eventType
	return out
}

func collectFields(v reflect.Value, out map[string]any) {
	t := v.Type()
	for i := 0; i < t.NumField(); i++ {
		f := t.Field(i)
		if f.Anonymous {
			collectFields(v.Field(i), out)
			continue
		}
		name := strings.Split(f.Tag.Get("dict"), ",")[0]
		if name == "" {
			continue
		}
		fv := v.Field(i)
		switch fv.Kind() {
		case reflect.Pointer:
			if fv.IsNil() {
				out[name] = nil
			} else {
				out[name] = fv.Elem().Interface()
			}
		case reflect.Slice:
			if fv.IsNil() {
				out[name] = reflect.MakeSlice(fv.Type(), 0, 0).Interface()
			} else {
				out[name] = fv.Interface()
			}
		default:
			out[name] = fv.Interface()
		}
		out[name] = asdictValue(out[name])
	}
}

// asdictValue mirrors dataclasses.asdict for value objects: a dataclass ID such as
// TaskId becomes {"value": "<uuid>"} (only the ID types can occur in event fields).
func asdictValue(v any) any {
	if id, ok := v.(interface{ ToCanonicalFormat() string }); ok {
		return map[string]any{"value": id.ToCanonicalFormat()}
	}
	return v
}

// DomainEvent is the legacy alias of BaseDomainEvent (events/base.py).
type DomainEvent = BaseDomainEvent

func strOrNil(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// aggregateIDStr mirrors `str(self.aggregate_id) if self.aggregate_id else None`.
func (b BaseDomainEvent) aggregateIDStr() any {
	if b.AggregateID == nil || *b.AggregateID == "" {
		return nil
	}
	return *b.AggregateID
}
