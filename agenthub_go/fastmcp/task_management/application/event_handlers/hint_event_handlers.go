package event_handlers

import (
	"context"
	"fmt"
	"hash/fnv"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/events"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// HintRecord is the minimal shape of a hydrated hint used by _get_hint_details.
// No Go port of the hint entity/repository existed, so the fields are declared.
type HintRecord struct {
	ID         string
	SourceRule string
	HintType   string
	Priority   string
	TaskID     string
}

// HintEventRepository is the minimal hint repository dependency.
type HintEventRepository interface {
	StoreGeneratedHint(ctx context.Context, event events.HintGenerated) error
	StoreHintAcceptance(ctx context.Context, event events.HintAccepted) error
	StoreHintDismissal(ctx context.Context, event events.HintDismissed) error
	StoreHintFeedback(ctx context.Context, event events.HintFeedbackProvided) error
	StoreDetectedPattern(ctx context.Context, event events.HintPatternDetected) error
	StoreEffectivenessScore(ctx context.Context, event events.HintEffectivenessCalculated) error
	StoreImprovementSuggestion(ctx context.Context, hintID, suggestions string) error
	Get(ctx context.Context, hintID string) (*HintRecord, error)
}

// HintEventStore is the minimal event store dependency (Python EventStore).
type HintEventStore interface {
	Append(ctx context.Context, event events.Event) error
	GetEventsByAggregate(ctx context.Context, aggregateID string, eventTypes []string) ([]events.HintGenerated, error)
}

// HintEventHandlers handles hint-related domain events.
type HintEventHandlers struct {
	// mu guards the in-memory statistics maps/slices below.
	mu             sync.Mutex
	EventStore     HintEventStore
	HintRepository HintEventRepository

	HintStats         map[string]map[string]int
	PatternThresholds map[string]float64
}

// NewHintEventHandlers builds the handler with the Python defaults.
func NewHintEventHandlers(eventStore HintEventStore, hintRepository HintEventRepository) *HintEventHandlers {
	return &HintEventHandlers{
		EventStore:     eventStore,
		HintRepository: hintRepository,
		HintStats:      map[string]map[string]int{},
		PatternThresholds: map[string]float64{
			"min_hints_for_pattern": 10,
			"acceptance_threshold":  0.7,
			"dismissal_threshold":   0.5,
		},
	}
}

func (h *HintEventHandlers) stats(key string) map[string]int {
	s, ok := h.HintStats[key]
	if !ok {
		s = map[string]int{"generated": 0, "accepted": 0, "dismissed": 0, "feedback": 0}
		h.HintStats[key] = s
	}
	return s
}

func hintKey(sourceRule, hintType string) string { return sourceRule + ":" + hintType }

// HandleHintGenerated handles hint_generated.
func (h *HintEventHandlers) HandleHintGenerated(ctx context.Context, event events.HintGenerated) {
	h.mu.Lock()
	defer h.mu.Unlock()
	key := hintKey(event.SourceRule, string(event.HintType))
	h.stats(key)["generated"]++

	if h.HintRepository != nil {
		_ = h.HintRepository.StoreGeneratedHint(ctx, event)
	}
	if h.stats(key)["generated"]%50 == 0 {
		h.calculateAndPublishEffectiveness(ctx, event.SourceRule, string(event.HintType))
	}
}

// HandleHintAccepted handles hint_accepted.
func (h *HintEventHandlers) HandleHintAccepted(ctx context.Context, event events.HintAccepted) {
	h.mu.Lock()
	defer h.mu.Unlock()
	details := h.getHintDetails(ctx, event.HintID)
	if details != nil {
		key := hintKey(details.SourceRule, details.HintType)
		h.stats(key)["accepted"]++
		h.checkAcceptancePatterns(ctx, details)
	}
	if h.HintRepository != nil {
		_ = h.HintRepository.StoreHintAcceptance(ctx, event)
	}
}

// HandleHintDismissed handles hint_dismissed.
func (h *HintEventHandlers) HandleHintDismissed(ctx context.Context, event events.HintDismissed) {
	h.mu.Lock()
	defer h.mu.Unlock()
	details := h.getHintDetails(ctx, event.HintID)
	if details != nil {
		key := hintKey(details.SourceRule, details.HintType)
		h.stats(key)["dismissed"]++
		h.checkDismissalPatterns(ctx, details, event.Reason)
	}
	if h.HintRepository != nil {
		_ = h.HintRepository.StoreHintDismissal(ctx, event)
	}
}

// HandleHintFeedback handles hint_feedback_provided.
func (h *HintEventHandlers) HandleHintFeedback(ctx context.Context, event events.HintFeedbackProvided) {
	h.mu.Lock()
	defer h.mu.Unlock()
	details := h.getHintDetails(ctx, event.HintID)
	if details != nil {
		key := hintKey(details.SourceRule, details.HintType)
		h.stats(key)["feedback"]++
	}
	if h.HintRepository != nil {
		_ = h.HintRepository.StoreHintFeedback(ctx, event)
	}
	if event.ImprovementSuggestion != nil && *event.ImprovementSuggestion != "" {
		h.processImprovementSuggestions(ctx, event.HintID, *event.ImprovementSuggestion)
	}
}

// HandlePatternDetected handles hint_pattern_detected.
func (h *HintEventHandlers) HandlePatternDetected(ctx context.Context, event events.HintPatternDetected) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.handlePatternDetected(ctx, event)
}

// handlePatternDetected is HandlePatternDetected without taking the lock (called from other locked handlers).
func (h *HintEventHandlers) handlePatternDetected(ctx context.Context, event events.HintPatternDetected) {
	if h.HintRepository != nil {
		_ = h.HintRepository.StoreDetectedPattern(ctx, event)
	}
	// confidence > 0.8 and suggested_rule: only logs in Python.
	_ = event.Confidence > 0.8 && event.SuggestedRule != nil
}

// HandleEffectivenessCalculated handles hint_effectiveness_calculated.
func (h *HintEventHandlers) HandleEffectivenessCalculated(ctx context.Context, event events.HintEffectivenessCalculated) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.handleEffectivenessCalculated(ctx, event)
}

// handleEffectivenessCalculated is HandleEffectivenessCalculated without taking the lock (called from other locked handlers).
func (h *HintEventHandlers) handleEffectivenessCalculated(ctx context.Context, event events.HintEffectivenessCalculated) {
	if h.HintRepository != nil {
		_ = h.HintRepository.StoreEffectivenessScore(ctx, event)
	}
}

// systemAggregateID is Python's UUID(int=0) used as the aggregate of system events.
var systemAggregateID = "00000000-0000-0000-0000-000000000000"

// hintPatternID mirrors UUID(int=hash(key) & 0xFFFFFFFF). Python's str hash is
// randomized per process, so any stable 32-bit hash is equivalent.
func hintPatternID(key string) string {
	h := fnv.New32a()
	_, _ = h.Write([]byte(key))
	return fmt.Sprintf("00000000-0000-0000-0000-0000%08x", h.Sum32())
}

func (h *HintEventHandlers) getHintDetails(ctx context.Context, hintID string) *HintRecord {
	if h.HintRepository != nil {
		hint, err := h.HintRepository.Get(ctx, hintID)
		if err == nil && hint != nil {
			return hint
		}
	}
	if h.EventStore != nil {
		evs, err := h.EventStore.GetEventsByAggregate(ctx, hintID, []string{"hint_generated"})
		if err == nil && len(evs) > 0 {
			e := evs[0]
			return &HintRecord{ID: hintID, SourceRule: e.SourceRule, HintType: string(e.HintType), Priority: string(e.Priority), TaskID: e.TaskID}
		}
	}
	return nil
}

func (h *HintEventHandlers) calculateAndPublishEffectiveness(ctx context.Context, sourceRule, hintType string) {
	stats := h.stats(hintKey(sourceRule, hintType))
	total := stats["generated"]
	if total == 0 {
		return
	}
	accepted := stats["accepted"]
	dismissed := stats["dismissed"]
	effectiveness := float64(accepted) / float64(total)

	now := time.Now().UTC()
	event := events.NewHintEffectivenessCalculated()
	uid := "hint_event_handler"
	event.UserID = &uid
	event.AggregateID = &systemAggregateID // UUID(int=0), system event
	event.HintType = value_objects.HintType(hintType)
	event.SourceRule = sourceRule
	event.TotalHints = total
	event.AcceptedCount = accepted
	event.DismissedCount = dismissed
	event.EffectivenessScore = effectiveness
	event.PeriodStart = now.Add(-30 * 24 * time.Hour)
	event.PeriodEnd = now

	if h.EventStore != nil {
		_ = h.EventStore.Append(ctx, event)
	}
	h.handleEffectivenessCalculated(ctx, event)
}

func (h *HintEventHandlers) checkAcceptancePatterns(ctx context.Context, details *HintRecord) {
	stats := h.stats(hintKey(details.SourceRule, details.HintType))
	if float64(stats["generated"]) < h.PatternThresholds["min_hints_for_pattern"] {
		return
	}
	rate := float64(stats["accepted"]) / float64(stats["generated"])
	if rate > h.PatternThresholds["acceptance_threshold"] {
		pattern := events.NewHintPatternDetected()
		conf := rate
		if conf > 0.95 {
			conf = 0.95
		}
		pattern.AggregateID = &systemAggregateID
		pattern.PatternID = hintPatternID(hintKey(details.SourceRule, details.HintType))
		pattern.PatternName = fmt.Sprintf("high_acceptance_%s", details.SourceRule)
		pattern.PatternDescription = fmt.Sprintf("High acceptance rate for %s hints from %s", details.HintType, details.SourceRule)
		pattern.Confidence = conf
		pattern.SuggestedRule = map[string]any{"action": "increase_priority", "rule": details.SourceRule, "type": details.HintType}
		if h.EventStore != nil {
			_ = h.EventStore.Append(ctx, pattern)
		}
		h.handlePatternDetected(ctx, pattern)
	}
}

func (h *HintEventHandlers) checkDismissalPatterns(ctx context.Context, details *HintRecord, reason *string) {
	stats := h.stats(hintKey(details.SourceRule, details.HintType))
	if float64(stats["generated"]) < h.PatternThresholds["min_hints_for_pattern"] {
		return
	}
	rate := float64(stats["dismissed"]) / float64(stats["generated"])
	if rate > h.PatternThresholds["dismissal_threshold"] {
		pattern := events.NewHintPatternDetected()
		conf := rate
		if conf > 0.95 {
			conf = 0.95
		}
		pattern.AggregateID = &systemAggregateID
		pattern.PatternID = hintPatternID(hintKey(details.SourceRule, details.HintType) + "_dismissed")
		pattern.PatternName = fmt.Sprintf("high_dismissal_%s", details.SourceRule)
		pattern.PatternDescription = fmt.Sprintf("High dismissal rate for %s hints from %s", details.HintType, details.SourceRule)
		pattern.Confidence = conf
		var common any
		if reason != nil {
			common = *reason
		}
		pattern.SuggestedRule = map[string]any{"action": "decrease_priority", "rule": details.SourceRule, "type": details.HintType, "common_reason": common}
		if h.EventStore != nil {
			_ = h.EventStore.Append(ctx, pattern)
		}
		h.handlePatternDetected(ctx, pattern)
	}
}

func (h *HintEventHandlers) processImprovementSuggestions(ctx context.Context, hintID, suggestions string) {
	if h.HintRepository != nil {
		_ = h.HintRepository.StoreImprovementSuggestion(ctx, hintID, suggestions)
	}
}

// GetHintStatistics returns the current hint statistics.
func (h *HintEventHandlers) GetHintStatistics(ctx context.Context) map[string]any {
	h.mu.Lock()
	defer h.mu.Unlock()
	statsCopy := map[string]map[string]int{}
	totalGenerated, totalAccepted, totalDismissed, totalFeedback := 0, 0, 0, 0
	for k, s := range h.HintStats {
		statsCopy[k] = s
		totalGenerated += s["generated"]
		totalAccepted += s["accepted"]
		totalDismissed += s["dismissed"]
		totalFeedback += s["feedback"]
	}
	denom := totalGenerated
	if denom < 1 {
		denom = 1
	}
	return map[string]any{
		"statistics": statsCopy,
		"summary": map[string]any{
			"total_generated":         totalGenerated,
			"total_accepted":          totalAccepted,
			"total_dismissed":         totalDismissed,
			"total_feedback":          totalFeedback,
			"overall_acceptance_rate": float64(totalAccepted) / float64(denom),
		},
	}
}

// ProcessEvent routes an event to the appropriate handler.
func (h *HintEventHandlers) ProcessEvent(ctx context.Context, event events.Event) {
	switch event.EventType() {
	case "hint_generated":
		h.HandleHintGenerated(ctx, event.(events.HintGenerated))
	case "hint_accepted":
		h.HandleHintAccepted(ctx, event.(events.HintAccepted))
	case "hint_dismissed":
		h.HandleHintDismissed(ctx, event.(events.HintDismissed))
	case "hint_feedback_provided":
		h.HandleHintFeedback(ctx, event.(events.HintFeedbackProvided))
	case "hint_pattern_detected":
		h.HandlePatternDetected(ctx, event.(events.HintPatternDetected))
	case "hint_effectiveness_calculated":
		h.HandleEffectivenessCalculated(ctx, event.(events.HintEffectivenessCalculated))
	}
}
