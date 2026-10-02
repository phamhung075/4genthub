package value_objects

import (
	"sort"
	"time"
)

// HintType: Types of workflow hints available in the system.
type HintType string

const (
	HintTypeNextAction        HintType = "next_action"
	HintTypeBlockerResolution HintType = "blocker_resolution"
	HintTypeOptimization      HintType = "optimization"
	HintTypeCompletion        HintType = "completion"
	HintTypeCollaboration     HintType = "collaboration"
)

// HintTypeValues lists all members in declaration order.
var HintTypeValues = []HintType{HintTypeNextAction, HintTypeBlockerResolution, HintTypeOptimization, HintTypeCompletion, HintTypeCollaboration}

func (e HintType) String() string { return string(e) }

// HintPriority: Priority levels for workflow hints.
type HintPriority string

const (
	HintPriorityLow      HintPriority = "low"
	HintPriorityMedium   HintPriority = "medium"
	HintPriorityHigh     HintPriority = "high"
	HintPriorityCritical HintPriority = "critical"
)

// HintPriorityValues lists all members in declaration order.
var HintPriorityValues = []HintPriority{HintPriorityLow, HintPriorityMedium, HintPriorityHigh, HintPriorityCritical}

func (e HintPriority) String() string { return string(e) }

// HintMetadata is metadata associated with a workflow hint.
type HintMetadata struct {
	Source             string
	Confidence         float64 // 0.0 to 1.0
	Reasoning          string
	RelatedTasks       []string // task UUIDs
	PatternsDetected   []string
	EffectivenessScore *float64
}

// NewHintMetadata validates confidence and effectiveness ranges.
func NewHintMetadata(source string, confidence float64, reasoning string, relatedTasks, patterns []string, effectiveness *float64) (HintMetadata, error) {
	if !(confidence >= 0.0 && confidence <= 1.0) {
		return HintMetadata{}, valueErrorf("Confidence must be between 0.0 and 1.0")
	}
	if effectiveness != nil && !(*effectiveness >= 0.0 && *effectiveness <= 1.0) {
		return HintMetadata{}, valueErrorf("Effectiveness score must be between 0.0 and 1.0")
	}
	return HintMetadata{source, confidence, reasoning, relatedTasks, patterns, effectiveness}, nil
}

// WorkflowHint is a single workflow hint providing intelligent guidance.
type WorkflowHint struct {
	ID              string
	Type            HintType
	Priority        HintPriority
	Message         string
	SuggestedAction string
	Metadata        HintMetadata
	CreatedAt       time.Time
	TaskID          string
	ContextData     map[string]any
	ExpiresAt       *time.Time
}

// CreateWorkflowHint is the factory: new UUID, created now (UTC), empty context by default.
func CreateWorkflowHint(taskID string, hintType HintType, priority HintPriority, message, suggestedAction string,
	metadata HintMetadata, contextData map[string]any, expiresAt *time.Time) WorkflowHint {
	if len(contextData) == 0 {
		contextData = map[string]any{}
	}
	return WorkflowHint{ID: NewUUIDv4(), Type: hintType, Priority: priority, Message: message,
		SuggestedAction: suggestedAction, Metadata: metadata, CreatedAt: now(), TaskID: taskID,
		ContextData: contextData, ExpiresAt: expiresAt}
}

// IsExpired: expiry set and passed.
func (h WorkflowHint) IsExpired() bool { return h.ExpiresAt != nil && now().After(*h.ExpiresAt) }

// ToDict converts the hint to its dictionary representation.
func (h WorkflowHint) ToDict() map[string]any {
	return map[string]any{
		"id": h.ID, "type": string(h.Type), "priority": string(h.Priority), "message": h.Message,
		"suggested_action": h.SuggestedAction, "reasoning": h.Metadata.Reasoning,
		"confidence": h.Metadata.Confidence, "created_at": IsoFormat(h.CreatedAt), "task_id": h.TaskID,
		"context_data": h.ContextData, "expires_at": isoOrNil(h.ExpiresAt),
	}
}

// HintCollection manages multiple hints for a task (mutable).
type HintCollection struct {
	TaskID string
	Hints  []WorkflowHint
}

// AddHint appends a hint whose task matches the collection.
func (c *HintCollection) AddHint(h WorkflowHint) error {
	if h.TaskID != c.TaskID {
		return valueErrorf("Hint task_id must match collection task_id")
	}
	c.Hints = append(c.Hints, h)
	return nil
}

// GetActiveHints returns all non-expired hints.
func (c *HintCollection) GetActiveHints() []WorkflowHint {
	out := []WorkflowHint{}
	for _, h := range c.Hints {
		if !h.IsExpired() {
			out = append(out, h)
		}
	}
	return out
}

// GetHintsByType returns active hints of a type.
func (c *HintCollection) GetHintsByType(t HintType) []WorkflowHint {
	out := []WorkflowHint{}
	for _, h := range c.GetActiveHints() {
		if h.Type == t {
			out = append(out, h)
		}
	}
	return out
}

// GetHintsByPriority returns active hints of a priority.
func (c *HintCollection) GetHintsByPriority(p HintPriority) []WorkflowHint {
	out := []WorkflowHint{}
	for _, h := range c.GetActiveHints() {
		if h.Priority == p {
			out = append(out, h)
		}
	}
	return out
}

var hintPriorityOrder = map[HintPriority]int{
	HintPriorityCritical: 0, HintPriorityHigh: 1, HintPriorityMedium: 2, HintPriorityLow: 3,
}

// GetTopHints returns up to limit active hints sorted by priority then confidence (desc).
func (c *HintCollection) GetTopHints(limit int) []WorkflowHint {
	sorted := c.GetActiveHints()
	sort.SliceStable(sorted, func(i, j int) bool {
		pi, pj := hintPriorityOrder[sorted[i].Priority], hintPriorityOrder[sorted[j].Priority]
		if pi != pj {
			return pi < pj
		}
		return sorted[i].Metadata.Confidence > sorted[j].Metadata.Confidence
	})
	return sorted[:pySliceEnd(len(sorted), limit)]
}

// RemoveExpiredHints drops expired hints and returns the count removed.
func (c *HintCollection) RemoveExpiredHints() int {
	original := len(c.Hints)
	c.Hints = c.GetActiveHints()
	return original - len(c.Hints)
}

// ClearHintsByType drops hints of a type and returns the count removed.
func (c *HintCollection) ClearHintsByType(t HintType) int {
	original := len(c.Hints)
	kept := []WorkflowHint{}
	for _, h := range c.Hints {
		if h.Type != t {
			kept = append(kept, h)
		}
	}
	c.Hints = kept
	return original - len(kept)
}

// pySliceEnd resolves the end index of Python's seq[:limit]: negative limits count
// from the end, and the result is clamped to [0, n].
func pySliceEnd(n, limit int) int {
	if limit < 0 {
		limit += n
	}
	if limit < 0 {
		return 0
	}
	if limit > n {
		return n
	}
	return limit
}
