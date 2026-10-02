// Package base ports task_management/domain/entities/base.
package base

import (
	"time"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

var now = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// TimestampUpdatedEvent is fired when an entity timestamp is updated.
type TimestampUpdatedEvent struct {
	events.BaseDomainEvent
	EntityID     string
	OldTimestamp *time.Time
	NewTimestamp time.Time
	Metadata     map[string]any
}

func NewTimestampUpdatedEvent() TimestampUpdatedEvent {
	return TimestampUpdatedEvent{BaseDomainEvent: events.NewBaseDomainEvent(), NewTimestamp: now(), Metadata: events.CreateEventMetadata()}
}
func (e TimestampUpdatedEvent) EventType() string { return "timestamp_updated" }
func (e TimestampUpdatedEvent) ToDict() map[string]any {
	var old any
	if e.OldTimestamp != nil {
		old = value_objects.IsoFormat(*e.OldTimestamp)
	}
	return map[string]any{
		"event_type": e.EventType(), "entity_id": e.EntityID, "old_timestamp": old,
		"new_timestamp": value_objects.IsoFormat(e.NewTimestamp), "metadata": e.Metadata,
	}
}

// TimestampCreatedEvent is fired when an entity is first created.
type TimestampCreatedEvent struct {
	events.BaseDomainEvent
	EntityID         string
	CreatedTimestamp time.Time
	Metadata         map[string]any
}

func NewTimestampCreatedEvent() TimestampCreatedEvent {
	return TimestampCreatedEvent{BaseDomainEvent: events.NewBaseDomainEvent(), CreatedTimestamp: now(), Metadata: events.CreateEventMetadata()}
}
func (e TimestampCreatedEvent) EventType() string { return "timestamp_created" }
func (e TimestampCreatedEvent) ToDict() map[string]any {
	return map[string]any{
		"event_type": e.EventType(), "entity_id": e.EntityID,
		"created_timestamp": value_objects.IsoFormat(e.CreatedTimestamp), "metadata": e.Metadata,
	}
}

// EntityHooks are the abstract methods concrete entities implement
// (`_get_entity_id`, `_validate_entity`); Python calls them from __post_init__ and touch().
type EntityHooks interface {
	GetEntityID() string
	ValidateEntity() error
}

// BaseTimestampEntity is the single source of truth for timestamp management:
// automatic created_at/updated_at, UTC enforcement and timestamp domain events.
// Concrete entities embed it and call Init(self) from their constructor.
type BaseTimestampEntity struct {
	CreatedAt    *time.Time
	UpdatedAt    *time.Time
	domainEvents []events.Event
	hooks        EntityHooks
}

// Init is Python's __post_init__: it binds the hooks, ensures clean timestamps,
// then validates the entity.
func (b *BaseTimestampEntity) Init(h EntityHooks) error {
	b.hooks = h
	if err := b.ensureCleanTimestamps(); err != nil {
		return err
	}
	return h.ValidateEntity()
}

func (b *BaseTimestampEntity) entityID() string { return b.hooks.GetEntityID() }

func (b *BaseTimestampEntity) ensureCleanTimestamps() error {
	n := now()
	isNew := b.CreatedAt == nil && b.UpdatedAt == nil
	if b.CreatedAt == nil {
		b.CreatedAt = &n
	} else {
		t := b.CreatedAt.UTC()
		b.CreatedAt = &t
	}
	if b.UpdatedAt == nil {
		b.UpdatedAt = &n
	} else {
		t := b.UpdatedAt.UTC()
		b.UpdatedAt = &t
	}
	if b.UpdatedAt.Before(*b.CreatedAt) {
		return value_objects.ValueErrorf("Entity %s has updated_at earlier than created_at", b.entityID())
	}
	if isNew {
		ev := NewTimestampCreatedEvent()
		ev.EntityID, ev.CreatedTimestamp = b.entityID(), *b.CreatedAt
		b.AddDomainEvent(ev)
	}
	return nil
}

// Touch updates updated_at, fires a TimestampUpdatedEvent and re-validates the entity.
func (b *BaseTimestampEntity) Touch(reason string) error {
	old := b.UpdatedAt
	n := now()
	b.UpdatedAt = &n
	ev := NewTimestampUpdatedEvent()
	ev.EntityID, ev.OldTimestamp, ev.NewTimestamp = b.entityID(), old, n
	b.AddDomainEvent(ev)
	return b.hooks.ValidateEntity()
}

// IsNewerThan compares updated_at timestamps with null handling.
func (b *BaseTimestampEntity) IsNewerThan(other *BaseTimestampEntity) bool {
	if b.UpdatedAt == nil {
		return false
	}
	if other.UpdatedAt == nil {
		return true
	}
	return b.UpdatedAt.After(*other.UpdatedAt)
}

// GetAgeSeconds is the age since creation, or false if created_at is unset.
func (b *BaseTimestampEntity) GetAgeSeconds() (float64, bool) {
	if b.CreatedAt == nil {
		return 0, false
	}
	return value_objects.PyTotalSeconds(now().Sub(*b.CreatedAt)), true
}

// GetStalenessSeconds is the time since the last update, or false if updated_at is unset.
func (b *BaseTimestampEntity) GetStalenessSeconds() (float64, bool) {
	if b.UpdatedAt == nil {
		return 0, false
	}
	return value_objects.PyTotalSeconds(now().Sub(*b.UpdatedAt)), true
}

// AddDomainEvent appends a domain event.
func (b *BaseTimestampEntity) AddDomainEvent(e events.Event) {
	b.domainEvents = append(b.domainEvents, e)
}

// GetDomainEvents returns a copy of the domain events.
func (b *BaseTimestampEntity) GetDomainEvents() []events.Event {
	return append([]events.Event{}, b.domainEvents...)
}

// ClearDomainEvents drops processed events.
func (b *BaseTimestampEntity) ClearDomainEvents() { b.domainEvents = nil }

// ToTimestampDict exports timestamp information.
func (b *BaseTimestampEntity) ToTimestampDict() map[string]any {
	var created, updated, age, stale any
	if b.CreatedAt != nil {
		created = value_objects.IsoFormat(*b.CreatedAt)
	}
	if b.UpdatedAt != nil {
		updated = value_objects.IsoFormat(*b.UpdatedAt)
	}
	if a, ok := b.GetAgeSeconds(); ok {
		age = a
	}
	if s, ok := b.GetStalenessSeconds(); ok {
		stale = s
	}
	return map[string]any{
		"entity_id": b.entityID(), "created_at": created, "updated_at": updated,
		"age_seconds": age, "staleness_seconds": stale, "domain_events_count": len(b.domainEvents),
	}
}

// RawDict mirrors the event's Python `__dict__` with datetimes rendered as ISO
// strings; TaskContext.to_dict leaks these under metadata["_domain_events"].
func (e TimestampUpdatedEvent) RawDict() map[string]any {
	var old any
	if e.OldTimestamp != nil {
		old = value_objects.IsoFormat(*e.OldTimestamp)
	}
	return map[string]any{
		"event_id": e.EventID, "occurred_at": value_objects.IsoFormat(e.OccurredAt),
		"aggregate_id": strPtrAny(e.AggregateID), "aggregate_type": strPtrAny(e.AggregateType), "user_id": strPtrAny(e.UserID),
		"entity_id": e.EntityID, "old_timestamp": old, "new_timestamp": value_objects.IsoFormat(e.NewTimestamp),
		"metadata": e.Metadata,
	}
}

// RawDict: see TimestampUpdatedEvent.RawDict.
func (e TimestampCreatedEvent) RawDict() map[string]any {
	return map[string]any{
		"event_id": e.EventID, "occurred_at": value_objects.IsoFormat(e.OccurredAt),
		"aggregate_id": strPtrAny(e.AggregateID), "aggregate_type": strPtrAny(e.AggregateType), "user_id": strPtrAny(e.UserID),
		"entity_id": e.EntityID, "created_timestamp": value_objects.IsoFormat(e.CreatedTimestamp),
		"metadata": e.Metadata,
	}
}

func strPtrAny(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}
