package events

import (
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// hintDict builds the common hint-event dictionary header.
func hintDict(e BaseDomainEvent, eventType string) map[string]any {
	return map[string]any{
		"event_id": e.EventID, "event_type": eventType, "occurred_at": value_objects.IsoFormat(e.OccurredAt),
		"aggregate_id": e.aggregateIDStr(), "aggregate_type": strOrNil(e.AggregateType),
	}
}

func merge(d map[string]any, kv map[string]any) map[string]any {
	for k, v := range kv {
		d[k] = v
	}
	return d
}

// HintGenerated: a workflow hint was generated. IDs are UUID strings.
type HintGenerated struct {
	BaseDomainEvent
	HintID          string
	TaskID          string
	HintType        value_objects.HintType
	Priority        value_objects.HintPriority
	Message         string
	SuggestedAction string
	SourceRule      string
	Confidence      float64
	Metadata        map[string]any
}

func NewHintGenerated() HintGenerated {
	return HintGenerated{BaseDomainEvent: NewBaseDomainEvent(), HintID: value_objects.NewUUIDv4(), TaskID: value_objects.NewUUIDv4(),
		HintType: value_objects.HintTypeNextAction, Priority: value_objects.HintPriorityMedium, Metadata: map[string]any{}}
}
func (e HintGenerated) EventType() string { return "hint_generated" }
func (e HintGenerated) ToDict() map[string]any {
	return merge(hintDict(e.BaseDomainEvent, e.EventType()), map[string]any{
		"hint_id": e.HintID, "task_id": e.TaskID, "hint_type": string(e.HintType), "priority": string(e.Priority),
		"message": e.Message, "suggested_action": e.SuggestedAction, "source_rule": e.SourceRule,
		"confidence": e.Confidence, "metadata": e.Metadata})
}

// HintAccepted: a user accepted/followed a hint. (UserID here is the string field, not the base pointer.)
type HintAccepted struct {
	BaseDomainEvent
	HintID            string
	TaskID            string
	User              string // Python `user_id: str` (shadows the base field)
	ActionTaken       *string
	AcceptanceContext map[string]any
}

func NewHintAccepted() HintAccepted {
	return HintAccepted{BaseDomainEvent: NewBaseDomainEvent(), HintID: value_objects.NewUUIDv4(), TaskID: value_objects.NewUUIDv4(), AcceptanceContext: map[string]any{}}
}
func (e HintAccepted) EventType() string { return "hint_accepted" }
func (e HintAccepted) ToDict() map[string]any {
	return merge(hintDict(e.BaseDomainEvent, e.EventType()), map[string]any{
		"hint_id": e.HintID, "task_id": e.TaskID, "user_id": e.User, "action_taken": strOrNil(e.ActionTaken),
		"acceptance_context": e.AcceptanceContext})
}

// HintDismissed: a user dismissed a hint.
type HintDismissed struct {
	BaseDomainEvent
	HintID           string
	TaskID           string
	User             string // Python `user_id: str`
	Reason           *string
	DismissalContext map[string]any
}

func NewHintDismissed() HintDismissed {
	return HintDismissed{BaseDomainEvent: NewBaseDomainEvent(), HintID: value_objects.NewUUIDv4(), TaskID: value_objects.NewUUIDv4(), DismissalContext: map[string]any{}}
}
func (e HintDismissed) EventType() string { return "hint_dismissed" }
func (e HintDismissed) ToDict() map[string]any {
	return merge(hintDict(e.BaseDomainEvent, e.EventType()), map[string]any{
		"hint_id": e.HintID, "task_id": e.TaskID, "user_id": e.User, "reason": strOrNil(e.Reason),
		"dismissal_context": e.DismissalContext})
}

// HintFeedbackProvided: a user gave feedback on a hint.
type HintFeedbackProvided struct {
	BaseDomainEvent
	HintID                string
	TaskID                string
	User                  string // Python `user_id: str`
	WasHelpful            bool
	FeedbackText          *string
	EffectivenessScore    *float64
	ImprovementSuggestion *string
}

func NewHintFeedbackProvided() HintFeedbackProvided {
	return HintFeedbackProvided{BaseDomainEvent: NewBaseDomainEvent(), HintID: value_objects.NewUUIDv4(), TaskID: value_objects.NewUUIDv4()}
}
func (e HintFeedbackProvided) EventType() string { return "hint_feedback_provided" }
func (e HintFeedbackProvided) ToDict() map[string]any {
	var score any
	if e.EffectivenessScore != nil {
		score = *e.EffectivenessScore
	}
	return merge(hintDict(e.BaseDomainEvent, e.EventType()), map[string]any{
		"hint_id": e.HintID, "task_id": e.TaskID, "user_id": e.User, "was_helpful": e.WasHelpful,
		"feedback_text": strOrNil(e.FeedbackText), "effectiveness_score": score,
		"improvement_suggestions": strOrNil(e.ImprovementSuggestion)})
}

// HintPatternDetected: a new pattern was detected for hint generation.
type HintPatternDetected struct {
	BaseDomainEvent
	PatternID          string
	PatternName        string
	PatternDescription string
	Confidence         float64
	AffectedTasks      []string
	SuggestedRule      map[string]any // nil = None
}

func NewHintPatternDetected() HintPatternDetected {
	return HintPatternDetected{BaseDomainEvent: NewBaseDomainEvent(), PatternID: value_objects.NewUUIDv4(), AffectedTasks: []string{}}
}
func (e HintPatternDetected) EventType() string { return "hint_pattern_detected" }
func (e HintPatternDetected) ToDict() map[string]any {
	tasks := e.AffectedTasks
	if tasks == nil {
		tasks = []string{}
	}
	var rule any
	if e.SuggestedRule != nil {
		rule = e.SuggestedRule
	}
	return merge(hintDict(e.BaseDomainEvent, e.EventType()), map[string]any{
		"pattern_id": e.PatternID, "pattern_name": e.PatternName, "pattern_description": e.PatternDescription,
		"confidence": e.Confidence, "affected_tasks": tasks, "suggested_rule": rule})
}

// HintEffectivenessCalculated: hint effectiveness was calculated for a period.
type HintEffectivenessCalculated struct {
	BaseDomainEvent
	HintType           value_objects.HintType
	SourceRule         string
	TotalHints         int
	AcceptedCount      int
	DismissedCount     int
	EffectivenessScore float64
	PeriodStart        time.Time
	PeriodEnd          time.Time
}

func NewHintEffectivenessCalculated() HintEffectivenessCalculated {
	return HintEffectivenessCalculated{BaseDomainEvent: NewBaseDomainEvent(), HintType: value_objects.HintTypeNextAction,
		PeriodStart: now(), PeriodEnd: now()}
}
func (e HintEffectivenessCalculated) EventType() string { return "hint_effectiveness_calculated" }
func (e HintEffectivenessCalculated) ToDict() map[string]any {
	return merge(hintDict(e.BaseDomainEvent, e.EventType()), map[string]any{
		"hint_type": string(e.HintType), "source_rule": e.SourceRule, "total_hints": e.TotalHints,
		"accepted_count": e.AcceptedCount, "dismissed_count": e.DismissedCount,
		"effectiveness_score": e.EffectivenessScore, "period_start": value_objects.IsoFormat(e.PeriodStart),
		"period_end": value_objects.IsoFormat(e.PeriodEnd)})
}
