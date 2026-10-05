package events

import (
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// contextDict builds the common context-event dictionary: event_type, event_id,
// the event-specific fields, the timestamp field, and occurred_at = that timestamp.
func contextDict(eventType, eventID string, ts time.Time, tsKey string, fields [][2]any) map[string]any {
	d := map[string]any{"event_type": eventType, "event_id": eventID}
	for _, kv := range fields {
		d[kv[0].(string)] = kv[1]
	}
	d[tsKey] = value_objects.IsoFormat(ts)
	d["occurred_at"] = value_objects.IsoFormat(ts)
	return d
}

// ContextCreated event.
type ContextCreated struct {
	BaseDomainEvent
	ContextID string
	Level     string // global, project, branch, task
	CreatedBy string
	CreatedAt time.Time
}

func NewContextCreated() ContextCreated {
	return ContextCreated{BaseDomainEvent: NewBaseDomainEvent(), CreatedAt: now()}
}
func (e ContextCreated) EventType() string { return "ContextCreated" }
func (e ContextCreated) ToDict() map[string]any {
	return contextDict(e.EventType(), e.EventID, e.CreatedAt, "created_at", [][2]any{
		{"context_id", e.ContextID}, {"level", e.Level}, {"created_by", e.CreatedBy}})
}

// ContextUpdated event.
type ContextUpdated struct {
	BaseDomainEvent
	ContextID string
	Level     string
	UpdatedBy string
	Changes   map[string]any
	UpdatedAt time.Time
}

func NewContextUpdated() ContextUpdated {
	return ContextUpdated{BaseDomainEvent: NewBaseDomainEvent(), Changes: map[string]any{}, UpdatedAt: now()}
}
func (e ContextUpdated) EventType() string { return "ContextUpdated" }
func (e ContextUpdated) ToDict() map[string]any {
	return contextDict(e.EventType(), e.EventID, e.UpdatedAt, "updated_at", [][2]any{
		{"context_id", e.ContextID}, {"level", e.Level}, {"updated_by", e.UpdatedBy}, {"changes", e.Changes}})
}

// ContextDelegated event.
type ContextDelegated struct {
	BaseDomainEvent
	SourceContextID  string
	SourceLevel      string
	TargetLevel      string
	DelegatedData    map[string]any
	DelegationReason string
	DelegatedBy      string
	DelegatedAt      time.Time
}

func NewContextDelegated() ContextDelegated {
	return ContextDelegated{BaseDomainEvent: NewBaseDomainEvent(), DelegatedData: map[string]any{}, DelegatedAt: now()}
}
func (e ContextDelegated) EventType() string { return "ContextDelegated" }
func (e ContextDelegated) ToDict() map[string]any {
	return contextDict(e.EventType(), e.EventID, e.DelegatedAt, "delegated_at", [][2]any{
		{"source_context_id", e.SourceContextID}, {"source_level", e.SourceLevel}, {"target_level", e.TargetLevel},
		{"delegated_data", e.DelegatedData}, {"delegation_reason", e.DelegationReason}, {"delegated_by", e.DelegatedBy}})
}

// ContextInsightAdded event.
type ContextInsightAdded struct {
	BaseDomainEvent
	ContextID       string
	Level           string
	InsightContent  string
	InsightCategory string
	Importance      string
	AddedBy         string
	AddedAt         time.Time
}

func NewContextInsightAdded() ContextInsightAdded {
	return ContextInsightAdded{BaseDomainEvent: NewBaseDomainEvent(), AddedAt: now()}
}
func (e ContextInsightAdded) EventType() string { return "ContextInsightAdded" }
func (e ContextInsightAdded) ToDict() map[string]any {
	return contextDict(e.EventType(), e.EventID, e.AddedAt, "added_at", [][2]any{
		{"context_id", e.ContextID}, {"level", e.Level}, {"insight_content", e.InsightContent},
		{"insight_category", e.InsightCategory}, {"importance", e.Importance}, {"added_by", e.AddedBy}})
}

// ContextProgressAdded event.
type ContextProgressAdded struct {
	BaseDomainEvent
	ContextID       string
	Level           string
	ProgressContent string
	AddedBy         string
	AddedAt         time.Time
}

func NewContextProgressAdded() ContextProgressAdded {
	return ContextProgressAdded{BaseDomainEvent: NewBaseDomainEvent(), AddedAt: now()}
}
func (e ContextProgressAdded) EventType() string { return "ContextProgressAdded" }
func (e ContextProgressAdded) ToDict() map[string]any {
	return contextDict(e.EventType(), e.EventID, e.AddedAt, "added_at", [][2]any{
		{"context_id", e.ContextID}, {"level", e.Level}, {"progress_content", e.ProgressContent}, {"added_by", e.AddedBy}})
}

// ContextInheritanceResolved event.
type ContextInheritanceResolved struct {
	BaseDomainEvent
	ContextID        string
	Level            string
	InheritanceChain []string
	ResolvedBy       string
	ResolvedAt       time.Time
}

func NewContextInheritanceResolved() ContextInheritanceResolved {
	return ContextInheritanceResolved{BaseDomainEvent: NewBaseDomainEvent(), InheritanceChain: []string{}, ResolvedAt: now()}
}
func (e ContextInheritanceResolved) EventType() string { return "ContextInheritanceResolved" }
func (e ContextInheritanceResolved) ToDict() map[string]any {
	return contextDict(e.EventType(), e.EventID, e.ResolvedAt, "resolved_at", [][2]any{
		{"context_id", e.ContextID}, {"level", e.Level}, {"inheritance_chain", e.InheritanceChain}, {"resolved_by", e.ResolvedBy}})
}
