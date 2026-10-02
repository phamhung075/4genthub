package database

import (
	"sync/atomic"
	"time"
)

// Timestamped is an entity with timestamp management (BaseTimestampEntity: created_at,
// updated_at and touch). nil timestamps are Python None.
type Timestamped interface {
	GetCreatedAt() *time.Time
	SetCreatedAt(*time.Time)
	GetUpdatedAt() *time.Time
	SetUpdatedAt(*time.Time)
	Touch()
}

// TimestampNow is the clock used by the handlers.
var TimestampNow = func() time.Time { return time.Now().UTC() }

var timestampEventsRegistered atomic.Bool

// SetupTimestampEvents registers the timestamp handlers. SQLAlchemy fires them from mapper
// events; Go repositories call BeforeInsertTimestamps / BeforeUpdateTimestamps explicitly
// when the registration is active.
func SetupTimestampEvents() { timestampEventsRegistered.Store(true) }

// CleanupTimestampEvents removes the handlers (testing / re-initialisation).
func CleanupTimestampEvents() { timestampEventsRegistered.Store(false) }

// TimestampEventsActive reports whether the handlers are registered.
func TimestampEventsActive() bool { return timestampEventsRegistered.Load() }

// asTimestamped is _is_timestamp_entity: only entities with timestamp management qualify.
func asTimestamped(target any) (Timestamped, bool) {
	t, ok := target.(Timestamped)
	return t, ok
}

// BeforeInsertTimestamps sets missing created_at / updated_at on a new entity and
// normalises both to UTC. Other targets are ignored.
func BeforeInsertTimestamps(target any) {
	t, ok := asTimestamped(target)
	if !ok {
		return
	}
	now := TimestampNow()
	if t.GetCreatedAt() == nil {
		t.SetCreatedAt(&now)
	}
	if t.GetUpdatedAt() == nil {
		n := now
		t.SetUpdatedAt(&n)
	}
	ensureUTC(t)
}

// BeforeUpdateTimestamps refreshes updated_at on an existing entity and keeps both
// timestamps in UTC (created_at is otherwise preserved).
func BeforeUpdateTimestamps(target any) {
	t, ok := asTimestamped(target)
	if !ok {
		return
	}
	now := TimestampNow()
	t.SetUpdatedAt(&now)
	ensureUTC(t)
}

// ensureUTC converts aware timestamps to UTC. Python also attaches UTC to naive
// datetimes; time.Time has no naive form, so the layer that scans naive database values
// interprets them as UTC.
func ensureUTC(t Timestamped) {
	if c := t.GetCreatedAt(); c != nil {
		u := c.UTC()
		t.SetCreatedAt(&u)
	}
	if u := t.GetUpdatedAt(); u != nil {
		v := u.UTC()
		t.SetUpdatedAt(&v)
	}
}
