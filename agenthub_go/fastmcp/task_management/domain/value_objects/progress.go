package value_objects

import (
	"sort"
	"strconv"
	"strings"
	"time"
)

// ProgressType: Types of progress that can be tracked.
type ProgressType string

const (
	ProgressTypeAnalysis       ProgressType = "analysis"
	ProgressTypeDesign         ProgressType = "design"
	ProgressTypeImplementation ProgressType = "implementation"
	ProgressTypeTesting        ProgressType = "testing"
	ProgressTypeDocumentation  ProgressType = "documentation"
	ProgressTypeReview         ProgressType = "review"
	ProgressTypeDeployment     ProgressType = "deployment"
	ProgressTypeGeneral        ProgressType = "general"
)

// ProgressTypeValues lists all members in declaration order.
var ProgressTypeValues = []ProgressType{ProgressTypeAnalysis, ProgressTypeDesign, ProgressTypeImplementation, ProgressTypeTesting, ProgressTypeDocumentation, ProgressTypeReview, ProgressTypeDeployment, ProgressTypeGeneral}

func (e ProgressType) String() string { return string(e) }

// ProgressStatus: Status of progress.
type ProgressStatus string

const (
	ProgressStatusNotStarted ProgressStatus = "not_started"
	ProgressStatusInProgress ProgressStatus = "in_progress"
	ProgressStatusBlocked    ProgressStatus = "blocked"
	ProgressStatusCompleted  ProgressStatus = "completed"
	ProgressStatusPaused     ProgressStatus = "paused"
)

// ProgressStatusValues lists all members in declaration order.
var ProgressStatusValues = []ProgressStatus{ProgressStatusNotStarted, ProgressStatusInProgress, ProgressStatusBlocked, ProgressStatusCompleted, ProgressStatusPaused}

func (e ProgressStatus) String() string { return string(e) }

func progressTypeFrom(v string) (ProgressType, error) {
	for _, t := range ProgressTypeValues {
		if string(t) == v {
			return t, nil
		}
	}
	return "", valueErrorf("'%s' is not a valid ProgressType", v)
}

func progressStatusFrom(v string) (ProgressStatus, error) {
	for _, s := range ProgressStatusValues {
		if string(s) == v {
			return s, nil
		}
	}
	return "", valueErrorf("'%s' is not a valid ProgressStatus", v)
}

// parseISO mirrors datetime.fromisoformat for the forms IsoFormat() emits.
func parseISO(s string) (time.Time, error) {
	for _, layout := range []string{time.RFC3339Nano, "2006-01-02T15:04:05.999999999", "2006-01-02"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, valueErrorf("Invalid isoformat string: '%s'", s)
}

func dictString(d map[string]any, key string) *string {
	if s, ok := d[key].(string); ok {
		return &s
	}
	return nil
}

func dictStrings(d map[string]any, key string) []string {
	out := []string{}
	if l, ok := d[key].([]any); ok {
		for _, e := range l {
			if s, ok := e.(string); ok {
				out = append(out, s)
			}
		}
	} else if l, ok := d[key].([]string); ok {
		out = append(out, l...)
	}
	return out
}

func dictFloat(d map[string]any, key string, def float64) float64 {
	switch v := d[key].(type) {
	case float64:
		return v
	case int:
		return float64(v)
	}
	return def
}

// ProgressMetadata is additional metadata for progress tracking.
type ProgressMetadata struct {
	Blockers            []string
	Dependencies        []string
	ConfidenceLevel     float64 // 0.0 to 1.0 (default 1.0)
	Notes               *string
	EstimatedCompletion *time.Time
}

// NewProgressMetadata applies the Python default confidence of 1.0.
func NewProgressMetadata() ProgressMetadata { return ProgressMetadata{ConfidenceLevel: 1.0} }

// ToDict converts to a dictionary representation.
func (m ProgressMetadata) ToDict() map[string]any {
	var notes any
	if m.Notes != nil {
		notes = *m.Notes
	}
	return map[string]any{
		"blockers": nonNil(m.Blockers), "dependencies": nonNil(m.Dependencies), "confidence_level": m.ConfidenceLevel,
		"notes": notes, "estimated_completion": isoOrNil(m.EstimatedCompletion),
	}
}

// ProgressMetadataFromDict creates metadata from a dictionary.
func ProgressMetadataFromDict(d map[string]any) (ProgressMetadata, error) {
	m := ProgressMetadata{
		Blockers: dictStrings(d, "blockers"), Dependencies: dictStrings(d, "dependencies"),
		ConfidenceLevel: dictFloat(d, "confidence_level", 1.0), Notes: dictString(d, "notes"),
	}
	if s := dictString(d, "estimated_completion"); s != nil && *s != "" {
		t, err := parseISO(*s)
		if err != nil {
			return m, err
		}
		m.EstimatedCompletion = &t
	}
	return m, nil
}

// ProgressSnapshot is an immutable snapshot of progress at a point in time.
type ProgressSnapshot struct {
	ID           string
	TaskID       string
	Timestamp    time.Time
	ProgressType ProgressType
	Percentage   float64 // 0-100
	Status       ProgressStatus
	Description  *string
	Metadata     ProgressMetadata
	AgentID      *string
}

// NewProgressSnapshot fills Python's defaults (new UUID, now, GENERAL, NOT_STARTED,
// default metadata) for zero-valued fields and validates the percentage.
func NewProgressSnapshot(s ProgressSnapshot) (ProgressSnapshot, error) {
	if s.ID == "" {
		s.ID = NewUUIDv4()
	}
	if s.Timestamp.IsZero() {
		s.Timestamp = now()
	}
	if s.ProgressType == "" {
		s.ProgressType = ProgressTypeGeneral
	}
	if s.Status == "" {
		s.Status = ProgressStatusNotStarted
	}
	if s.Metadata.ConfidenceLevel == 0 && s.Metadata.Blockers == nil && s.Metadata.Dependencies == nil &&
		s.Metadata.Notes == nil && s.Metadata.EstimatedCompletion == nil {
		s.Metadata = NewProgressMetadata()
	}
	if !(s.Percentage >= 0 && s.Percentage <= 100) {
		return ProgressSnapshot{}, valueErrorf("Progress percentage must be between 0 and 100, got %s", pyFloat(s.Percentage))
	}
	return s, nil
}

// pyFloat formats like Python str(float): "150.0", "-1.5".
func pyFloat(f float64) string {
	s := strconv.FormatFloat(f, 'f', -1, 64)
	if !strings.ContainsAny(s, ".eEn") {
		s += ".0"
	}
	return s
}

// ToDict converts to a dictionary representation.
func (s ProgressSnapshot) ToDict() map[string]any {
	var desc, agent any
	if s.Description != nil {
		desc = *s.Description
	}
	if s.AgentID != nil {
		agent = *s.AgentID
	}
	return map[string]any{
		"id": s.ID, "task_id": s.TaskID, "timestamp": IsoFormat(s.Timestamp),
		"progress_type": string(s.ProgressType), "percentage": s.Percentage, "status": string(s.Status),
		"description": desc, "metadata": s.Metadata.ToDict(), "agent_id": agent,
	}
}

// ProgressSnapshotFromDict creates a snapshot from a dictionary.
func ProgressSnapshotFromDict(d map[string]any) (ProgressSnapshot, error) {
	s := ProgressSnapshot{Description: dictString(d, "description"), AgentID: dictString(d, "agent_id")}
	if id := dictString(d, "id"); id != nil {
		s.ID = *id
	}
	if tid := dictString(d, "task_id"); tid != nil {
		s.TaskID = *tid
	}
	if ts := dictString(d, "timestamp"); ts != nil {
		t, err := parseISO(*ts)
		if err != nil {
			return ProgressSnapshot{}, err
		}
		s.Timestamp = t
	}
	pt := "general"
	if v := dictString(d, "progress_type"); v != nil {
		pt = *v
	}
	var err error
	if s.ProgressType, err = progressTypeFrom(pt); err != nil {
		return ProgressSnapshot{}, err
	}
	st := "not_started"
	if v := dictString(d, "status"); v != nil {
		st = *v
	}
	if s.Status, err = progressStatusFrom(st); err != nil {
		return ProgressSnapshot{}, err
	}
	s.Percentage = dictFloat(d, "percentage", 0.0)
	md, _ := d["metadata"].(map[string]any)
	if s.Metadata, err = ProgressMetadataFromDict(md); err != nil {
		return ProgressSnapshot{}, err
	}
	return NewProgressSnapshot(s)
}

// ProgressTimeline aggregates the timeline of progress updates (mutable).
type ProgressTimeline struct {
	TaskID     string
	Snapshots  []ProgressSnapshot
	Milestones map[string]float64 // name -> percentage
	// MilestoneOrder keeps Python dict insertion order, which decides event order.
	MilestoneOrder []string
}

// NewProgressTimeline creates an empty timeline.
func NewProgressTimeline(taskID string) *ProgressTimeline {
	return &ProgressTimeline{TaskID: taskID, Milestones: map[string]float64{}}
}

// AddSnapshot appends a snapshot for this task and keeps the list sorted by timestamp.
func (t *ProgressTimeline) AddSnapshot(s ProgressSnapshot) error {
	if s.TaskID != t.TaskID {
		return valueErrorf("Snapshot task_id %s doesn't match timeline task_id %s", s.TaskID, t.TaskID)
	}
	t.Snapshots = append(t.Snapshots, s)
	sort.SliceStable(t.Snapshots, func(i, j int) bool { return t.Snapshots[i].Timestamp.Before(t.Snapshots[j].Timestamp) })
	return nil
}

// GetLatestSnapshot returns the most recent snapshot.
func (t *ProgressTimeline) GetLatestSnapshot() (ProgressSnapshot, bool) {
	if len(t.Snapshots) == 0 {
		return ProgressSnapshot{}, false
	}
	return t.Snapshots[len(t.Snapshots)-1], true
}

// GetSnapshotsByType returns snapshots of a type.
func (t *ProgressTimeline) GetSnapshotsByType(pt ProgressType) []ProgressSnapshot {
	out := []ProgressSnapshot{}
	for _, s := range t.Snapshots {
		if s.ProgressType == pt {
			out = append(out, s)
		}
	}
	return out
}

// GetOverallProgress averages the latest snapshot's percentage per progress type.
func (t *ProgressTimeline) GetOverallProgress() float64 {
	if len(t.Snapshots) == 0 {
		return 0.0
	}
	// Python sums dict values in first-seen type order; keep that order.
	latest := map[ProgressType]ProgressSnapshot{}
	order := []ProgressType{}
	for _, s := range t.Snapshots {
		cur, ok := latest[s.ProgressType]
		if !ok {
			order = append(order, s.ProgressType)
		}
		if !ok || s.Timestamp.After(cur.Timestamp) {
			latest[s.ProgressType] = s
		}
	}
	percentages := make([]float64, 0, len(order))
	for _, pt := range order {
		percentages = append(percentages, latest[pt].Percentage)
	}
	return PySum(percentages) / float64(len(latest))
}

// AddMilestone adds or updates a milestone.
func (t *ProgressTimeline) AddMilestone(name string, percentage float64) error {
	if !(percentage >= 0 && percentage <= 100) {
		return valueErrorf("Milestone percentage must be between 0 and 100, got %s", pyFloat(percentage))
	}
	if _, exists := t.Milestones[name]; !exists {
		t.MilestoneOrder = append(t.MilestoneOrder, name)
	}
	t.Milestones[name] = percentage
	return nil
}

// IsMilestoneReached: milestone exists and overall progress is at least its percentage.
func (t *ProgressTimeline) IsMilestoneReached(name string) bool {
	pct, ok := t.Milestones[name]
	return ok && t.GetOverallProgress() >= pct
}

// GetProgressTrend returns snapshots from the last `hours` hours.
func (t *ProgressTimeline) GetProgressTrend(hours int) []ProgressSnapshot {
	cutoff := now().Add(-time.Duration(hours) * time.Hour)
	out := []ProgressSnapshot{}
	for _, s := range t.Snapshots {
		if s.Timestamp.After(cutoff) {
			out = append(out, s)
		}
	}
	return out
}

// ToDict converts to a dictionary representation.
func (t *ProgressTimeline) ToDict() map[string]any {
	snaps := make([]map[string]any, len(t.Snapshots))
	for i, s := range t.Snapshots {
		snaps[i] = s.ToDict()
	}
	return map[string]any{"task_id": t.TaskID, "snapshots": snaps, "milestones": t.Milestones,
		"overall_progress": t.GetOverallProgress()}
}

// ProgressCalculationStrategy groups progress calculation helpers (all static in Python).
type ProgressCalculationStrategy struct{}

// KeyedProgress is one named progress value; slices of these preserve the
// Python dict insertion order so float sums are deterministic.
type KeyedProgress struct {
	Key   string
	Value float64
}

// CalculateWeightedAverage computes the weighted average, summing in the order of
// values; missing weights are filled with 1.0 and written back into weights
// (as Python mutates the dict).
func (ProgressCalculationStrategy) CalculateWeightedAverage(values []KeyedProgress, weights map[string]float64) float64 {
	if len(values) == 0 {
		return 0.0
	}
	if weights == nil {
		weights = map[string]float64{}
	}
	for _, kv := range values {
		if _, ok := weights[kv.Key]; !ok {
			weights[kv.Key] = 1.0
		}
	}
	ws, products := make([]float64, 0, len(values)), make([]float64, 0, len(values))
	for _, kv := range values {
		ws = append(ws, weights[kv.Key])
		products = append(products, float64(kv.Value*weights[kv.Key]))
	}
	totalWeight := PySum(ws)
	if totalWeight == 0 {
		return 0.0
	}
	return PySum(products) / totalWeight
}

// CalculateFromSubtasks averages "progress" across subtasks, excluding status
// "blocked" unless includeBlocked.
func (ProgressCalculationStrategy) CalculateFromSubtasks(subtasks []map[string]any, includeBlocked bool) float64 {
	var progress []float64
	for _, st := range subtasks {
		if status, _ := st["status"].(string); !includeBlocked && status == "blocked" {
			continue
		}
		progress = append(progress, dictFloat(st, "progress", 0.0))
	}
	if len(progress) == 0 {
		return 0.0
	}
	return PySum(progress) / float64(len(progress))
}

// CalculateByMilestones returns the maximum percentage among completed milestones.
func (ProgressCalculationStrategy) CalculateByMilestones(completed []string, all map[string]float64) float64 {
	best, found := 0.0, false
	for _, m := range completed {
		if v, ok := all[m]; ok && (!found || v > best) {
			best, found = v, true
		}
	}
	return best
}

// nonNil keeps empty lists serializing as [] (Python default_factory=list), not null.
func nonNil(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}

// ParseISO mirrors datetime.fromisoformat for the forms IsoFormat() emits.
func ParseISO(s string) (time.Time, error) { return parseISO(s) }
