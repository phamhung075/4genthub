package events

import (
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ProgressEvent is the (non-BaseDomainEvent) base of progress events.
type ProgressEvent struct {
	EventID   string
	TaskID    string // Python `str | TaskId`; a TaskId is stored via its string form
	Timestamp time.Time
	AgentID   *string
}

// NewProgressEvent generates an ID and stamps now (UTC).
func NewProgressEvent() ProgressEvent {
	return ProgressEvent{EventID: value_objects.NewUUIDv4(), Timestamp: now()}
}

func (p ProgressEvent) toDict(eventType string) map[string]any {
	return map[string]any{
		"event_id": p.EventID, "event_type": eventType, "task_id": p.TaskID,
		"timestamp": value_objects.IsoFormat(p.Timestamp), "agent_id": strOrNil(p.AgentID),
	}
}

// ProgressUpdated event.
type ProgressUpdated struct {
	ProgressEvent
	ProgressType  value_objects.ProgressType
	OldPercentage float64
	NewPercentage float64
	Status        value_objects.ProgressStatus
	Description   *string
	Metadata      map[string]any // nil = None
}

func NewProgressUpdated() ProgressUpdated {
	return ProgressUpdated{ProgressEvent: NewProgressEvent(), ProgressType: value_objects.ProgressTypeGeneral, Status: value_objects.ProgressStatusInProgress}
}
func (e ProgressUpdated) EventType() string { return "ProgressUpdated" }
func (e ProgressUpdated) ToDict() map[string]any {
	var md any
	if e.Metadata != nil {
		md = e.Metadata
	}
	return merge(e.toDict(e.EventType()), map[string]any{
		"progress_type": string(e.ProgressType), "old_percentage": e.OldPercentage, "new_percentage": e.NewPercentage,
		"status": string(e.Status), "description": strOrNil(e.Description), "metadata": md})
}

// ProgressDelta is new minus old percentage.
func (e ProgressUpdated) ProgressDelta() float64 { return e.NewPercentage - e.OldPercentage }

// ProgressMilestoneReached event.
type ProgressMilestoneReached struct {
	ProgressEvent
	MilestoneName       string
	MilestonePercentage float64
	CurrentProgress     float64
}

func NewProgressMilestoneReached() ProgressMilestoneReached {
	return ProgressMilestoneReached{ProgressEvent: NewProgressEvent()}
}
func (e ProgressMilestoneReached) EventType() string { return "ProgressMilestoneReached" }
func (e ProgressMilestoneReached) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"milestone_name": e.MilestoneName, "milestone_percentage": e.MilestonePercentage, "current_progress": e.CurrentProgress})
}

// ProgressStalled event.
type ProgressStalled struct {
	ProgressEvent
	LastUpdateTimestamp time.Time
	StallDurationHours  float64
	CurrentPercentage   float64
	Blockers            []string
}

func NewProgressStalled() ProgressStalled {
	return ProgressStalled{ProgressEvent: NewProgressEvent(), LastUpdateTimestamp: now(), Blockers: []string{}}
}
func (e ProgressStalled) EventType() string { return "ProgressStalled" }
func (e ProgressStalled) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"last_update_timestamp": value_objects.IsoFormat(e.LastUpdateTimestamp), "stall_duration_hours": e.StallDurationHours,
		"current_percentage": e.CurrentPercentage, "blockers": nonNilStrings(e.Blockers)})
}

func nonNilStrings(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

// SubtaskProgressAggregated event.
type SubtaskProgressAggregated struct {
	ProgressEvent
	ParentTaskID           string
	SubtaskCount           int
	OldParentProgress      float64
	NewParentProgress      float64
	AggregationMethod      string
	SubtaskProgressDetails []map[string]any
}

func NewSubtaskProgressAggregated() SubtaskProgressAggregated {
	return SubtaskProgressAggregated{ProgressEvent: NewProgressEvent(), AggregationMethod: "weighted_average", SubtaskProgressDetails: []map[string]any{}}
}
func (e SubtaskProgressAggregated) EventType() string { return "SubtaskProgressAggregated" }
func (e SubtaskProgressAggregated) ToDict() map[string]any {
	details := e.SubtaskProgressDetails
	if details == nil {
		details = []map[string]any{}
	}
	return merge(e.toDict(e.EventType()), map[string]any{
		"parent_task_id": e.ParentTaskID, "subtask_count": e.SubtaskCount, "old_parent_progress": e.OldParentProgress,
		"new_parent_progress": e.NewParentProgress, "aggregation_method": e.AggregationMethod,
		"subtask_progress_details": details})
}

// ProgressSnapshotCreated event.
type ProgressSnapshotCreated struct {
	ProgressEvent
	Snapshot value_objects.ProgressSnapshot
}

func NewProgressSnapshotCreated() ProgressSnapshotCreated {
	snap, _ := value_objects.NewProgressSnapshot(value_objects.ProgressSnapshot{})
	return ProgressSnapshotCreated{ProgressEvent: NewProgressEvent(), Snapshot: snap}
}
func (e ProgressSnapshotCreated) EventType() string { return "ProgressSnapshotCreated" }
func (e ProgressSnapshotCreated) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{"snapshot": e.Snapshot.ToDict()})
}

// ProgressTypeCompleted event.
type ProgressTypeCompleted struct {
	ProgressEvent
	ProgressType        value_objects.ProgressType
	CompletionTimestamp time.Time
}

func NewProgressTypeCompleted() ProgressTypeCompleted {
	return ProgressTypeCompleted{ProgressEvent: NewProgressEvent(), ProgressType: value_objects.ProgressTypeGeneral, CompletionTimestamp: now()}
}
func (e ProgressTypeCompleted) EventType() string { return "ProgressTypeCompleted" }
func (e ProgressTypeCompleted) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"progress_type": string(e.ProgressType), "completion_timestamp": value_objects.IsoFormat(e.CompletionTimestamp)})
}

// ProgressBlocked event.
type ProgressBlocked struct {
	ProgressEvent
	ProgressType         value_objects.ProgressType
	CurrentPercentage    float64
	Blockers             []string
	Dependencies         []string
	EstimatedUnblockTime *time.Time
}

func NewProgressBlocked() ProgressBlocked {
	return ProgressBlocked{ProgressEvent: NewProgressEvent(), ProgressType: value_objects.ProgressTypeGeneral, Blockers: []string{}, Dependencies: []string{}}
}
func (e ProgressBlocked) EventType() string { return "ProgressBlocked" }
func (e ProgressBlocked) ToDict() map[string]any {
	var unblock any
	if e.EstimatedUnblockTime != nil {
		unblock = value_objects.IsoFormat(*e.EstimatedUnblockTime)
	}
	return merge(e.toDict(e.EventType()), map[string]any{
		"progress_type": string(e.ProgressType), "current_percentage": e.CurrentPercentage,
		"blockers": nonNilStrings(e.Blockers), "dependencies": nonNilStrings(e.Dependencies), "estimated_unblock_time": unblock})
}

// ProgressUnblocked event.
type ProgressUnblocked struct {
	ProgressEvent
	ProgressType         value_objects.ProgressType
	BlockedDurationHours float64
	Resolution           *string
}

func NewProgressUnblocked() ProgressUnblocked {
	return ProgressUnblocked{ProgressEvent: NewProgressEvent(), ProgressType: value_objects.ProgressTypeGeneral}
}
func (e ProgressUnblocked) EventType() string { return "ProgressUnblocked" }
func (e ProgressUnblocked) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"progress_type": string(e.ProgressType), "blocked_duration_hours": e.BlockedDurationHours, "resolution": strOrNil(e.Resolution)})
}

// ProgressRolledBack event.
type ProgressRolledBack struct {
	ProgressEvent
	ProgressType   value_objects.ProgressType
	FromPercentage float64
	ToPercentage   float64
	Reason         string
}

func NewProgressRolledBack() ProgressRolledBack {
	return ProgressRolledBack{ProgressEvent: NewProgressEvent(), ProgressType: value_objects.ProgressTypeGeneral}
}
func (e ProgressRolledBack) EventType() string { return "ProgressRolledBack" }
func (e ProgressRolledBack) ToDict() map[string]any {
	return merge(e.toDict(e.EventType()), map[string]any{
		"progress_type": string(e.ProgressType), "from_percentage": e.FromPercentage, "to_percentage": e.ToPercentage, "reason": e.Reason})
}

// EventType is the class name, as the Python base uses `self.__class__.__name__`.
func (p ProgressEvent) EventType() string { return "ProgressEvent" }

// ToDict is the base-class to_dict (Python exposes it on ProgressEvent itself).
func (p ProgressEvent) ToDict() map[string]any { return p.toDict(p.EventType()) }
