package value_objects

import (
	"math"
	"time"
)

// VisionHierarchyLevel: Hierarchical levels for vision objectives.
type VisionHierarchyLevel string

const (
	VisionHierarchyLevelOrganization VisionHierarchyLevel = "organization"
	VisionHierarchyLevelDepartment   VisionHierarchyLevel = "department"
	VisionHierarchyLevelTeam         VisionHierarchyLevel = "team"
	VisionHierarchyLevelProject      VisionHierarchyLevel = "project"
	VisionHierarchyLevelMilestone    VisionHierarchyLevel = "milestone"
)

// VisionHierarchyLevelValues lists all members in declaration order.
var VisionHierarchyLevelValues = []VisionHierarchyLevel{VisionHierarchyLevelOrganization, VisionHierarchyLevelDepartment, VisionHierarchyLevelTeam, VisionHierarchyLevelProject, VisionHierarchyLevelMilestone}

func (e VisionHierarchyLevel) String() string { return string(e) }

// ContributionType: Types of contributions a task can make to a vision objective.
type ContributionType string

const (
	ContributionTypeDirect      ContributionType = "direct"
	ContributionTypeSupporting  ContributionType = "supporting"
	ContributionTypeEnabling    ContributionType = "enabling"
	ContributionTypeExploratory ContributionType = "exploratory"
	ContributionTypeMaintenance ContributionType = "maintenance"
)

// ContributionTypeValues lists all members in declaration order.
var ContributionTypeValues = []ContributionType{ContributionTypeDirect, ContributionTypeSupporting, ContributionTypeEnabling, ContributionTypeExploratory, ContributionTypeMaintenance}

func (e ContributionType) String() string { return string(e) }

// MetricType: Types of metrics that can be tracked.
type MetricType string

const (
	MetricTypePercentage MetricType = "percentage"
	MetricTypeCount      MetricType = "count"
	MetricTypeCurrency   MetricType = "currency"
	MetricTypeTime       MetricType = "time"
	MetricTypeRating     MetricType = "rating"
	MetricTypeCustom     MetricType = "custom"
)

// MetricTypeValues lists all members in declaration order.
var MetricTypeValues = []MetricType{MetricTypePercentage, MetricTypeCount, MetricTypeCurrency, MetricTypeTime, MetricTypeRating, MetricTypeCustom}

func (e MetricType) String() string { return string(e) }

// pyDays mirrors timedelta.days: floor of the duration in days (negative durations round down).
func pyDays(d time.Duration) int {
	day := 24 * time.Hour
	q := d / day
	if d%day < 0 {
		q--
	}
	return int(q)
}

// VisionMetric is a measurable metric for a vision objective.
type VisionMetric struct {
	Name          string
	CurrentValue  float64
	TargetValue   float64
	Unit          string
	MetricType    MetricType // default MetricTypeCustom
	BaselineValue float64
	LastUpdated   time.Time // default now
}

// NewVisionMetric applies Python defaults (CUSTOM type, baseline 0, updated now).
func NewVisionMetric(name string, current, target float64, unit string) VisionMetric {
	return VisionMetric{Name: name, CurrentValue: current, TargetValue: target, Unit: unit,
		MetricType: MetricTypeCustom, LastUpdated: now()}
}

// ProgressPercentage is progress toward target, clamped to [0, 100].
func (m VisionMetric) ProgressPercentage() float64 {
	if m.TargetValue == m.BaselineValue {
		if m.CurrentValue >= m.TargetValue {
			return 100.0
		}
		return 0.0
	}
	progress := (m.CurrentValue - m.BaselineValue) / (m.TargetValue - m.BaselineValue)
	return math.Min(math.Max(progress*100, 0.0), 100.0)
}

// IsAchieved: current value reached the target.
func (m VisionMetric) IsAchieved() bool { return m.CurrentValue >= m.TargetValue }

// ToDict converts to a dictionary representation.
func (m VisionMetric) ToDict() map[string]any {
	return map[string]any{
		"name": m.Name, "current_value": m.CurrentValue, "target_value": m.TargetValue, "unit": m.Unit,
		"metric_type": string(m.MetricType), "baseline_value": m.BaselineValue,
		"progress_percentage": m.ProgressPercentage(), "is_achieved": m.IsAchieved(),
		"last_updated": IsoFormat(m.LastUpdated),
	}
}

// VisionObjective is a vision objective in the organizational hierarchy.
type VisionObjective struct {
	ID          string
	Title       string
	Description string
	Level       VisionHierarchyLevel
	ParentID    *string
	Owner       string
	Priority    int    // 1-5, 5 highest
	Status      string // active, completed, paused, cancelled
	CreatedAt   time.Time
	DueDate     *time.Time
	Metrics     []VisionMetric
	Tags        []string
	Metadata    map[string]any
}

// NewVisionObjective applies Python defaults (new UUID, PROJECT level, priority 1, "active", now).
func NewVisionObjective() VisionObjective {
	return VisionObjective{ID: NewUUIDv4(), Level: VisionHierarchyLevelProject, Priority: 1, Status: "active",
		CreatedAt: now(), Metrics: []VisionMetric{}, Tags: []string{}, Metadata: map[string]any{}}
}

// OverallProgress averages metric progress.
func (o VisionObjective) OverallProgress() float64 {
	if len(o.Metrics) == 0 {
		return 0.0
	}
	percentages := make([]float64, 0, len(o.Metrics))
	for _, m := range o.Metrics {
		percentages = append(percentages, m.ProgressPercentage())
	}
	return PySum(percentages) / float64(len(o.Metrics))
}

// IsCompleted: there are metrics and all are achieved.
func (o VisionObjective) IsCompleted() bool {
	if len(o.Metrics) == 0 {
		return false
	}
	for _, m := range o.Metrics {
		if !m.IsAchieved() {
			return false
		}
	}
	return true
}

// DaysRemaining returns whole days until due date (floored, min 0), or false with no due date.
func (o VisionObjective) DaysRemaining() (int, bool) {
	if o.DueDate == nil {
		return 0, false
	}
	d := pyDays(o.DueDate.Sub(now()))
	if d < 0 {
		d = 0
	}
	return d, true
}

// ToDict converts to a dictionary representation (due_date is the raw datetime, as in Python).
func (o VisionObjective) ToDict() map[string]any {
	metrics := make([]map[string]any, len(o.Metrics))
	for i, m := range o.Metrics {
		metrics[i] = m.ToDict()
	}
	var parent, due, days any
	if o.ParentID != nil && *o.ParentID != "" {
		parent = *o.ParentID
	}
	if o.DueDate != nil {
		due = *o.DueDate
	}
	if d, ok := o.DaysRemaining(); ok {
		days = d
	}
	return map[string]any{
		"id": o.ID, "title": o.Title, "description": o.Description, "level": string(o.Level),
		"parent_id": parent, "owner": o.Owner, "priority": o.Priority, "status": o.Status,
		"created_at": IsoFormat(o.CreatedAt), "due_date": due, "metrics": metrics, "tags": o.Tags,
		"overall_progress": o.OverallProgress(), "is_completed": o.IsCompleted(), "days_remaining": days,
		"metadata": o.Metadata,
	}
}

// VisionAlignment is the alignment between a task and a vision objective.
type VisionAlignment struct {
	TaskID           string
	ObjectiveID      string
	AlignmentScore   float64 // 0.0 to 1.0
	ContributionType ContributionType
	Confidence       float64 // default 0.8
	Rationale        string
	CalculatedAt     time.Time
	Factors          map[string]float64
}

// NewVisionAlignment applies Python defaults (confidence 0.8, calculated now).
func NewVisionAlignment(taskID, objectiveID string, score float64, contribution ContributionType) VisionAlignment {
	return VisionAlignment{TaskID: taskID, ObjectiveID: objectiveID, AlignmentScore: score,
		ContributionType: contribution, Confidence: 0.8, CalculatedAt: now(), Factors: map[string]float64{}}
}

func (a VisionAlignment) IsStrongAlignment() bool { return a.AlignmentScore >= 0.7 }
func (a VisionAlignment) IsWeakAlignment() bool   { return a.AlignmentScore < 0.3 }

// ToDict converts to a dictionary representation.
func (a VisionAlignment) ToDict() map[string]any {
	return map[string]any{
		"task_id": a.TaskID, "objective_id": a.ObjectiveID, "alignment_score": a.AlignmentScore,
		"contribution_type": string(a.ContributionType), "confidence": a.Confidence, "rationale": a.Rationale,
		"calculated_at": IsoFormat(a.CalculatedAt), "is_strong_alignment": a.IsStrongAlignment(),
		"is_weak_alignment": a.IsWeakAlignment(), "factors": a.Factors,
	}
}

// VisionInsight is an insight or recommendation based on vision analysis.
type VisionInsight struct {
	ID                 string
	Type               string // recommendation, warning, opportunity
	Title              string
	Description        string
	Impact             string // low, medium, high, critical
	AffectedObjectives []string
	AffectedTasks      []string
	SuggestedActions   []string
	CreatedAt          time.Time
	ExpiresAt          *time.Time
	Metadata           map[string]any
}

// NewVisionInsight applies Python defaults (new UUID, "recommendation", "medium", now).
func NewVisionInsight() VisionInsight {
	return VisionInsight{ID: NewUUIDv4(), Type: "recommendation", Impact: "medium", CreatedAt: now(),
		AffectedObjectives: []string{}, AffectedTasks: []string{}, SuggestedActions: []string{}, Metadata: map[string]any{}}
}

// IsExpired: expiry set and passed.
func (i VisionInsight) IsExpired() bool { return i.ExpiresAt != nil && now().After(*i.ExpiresAt) }

// UrgencyScore scales impact by 1.5 (<=1 day to expiry) or 1.2 (<=7 days), capped at 1.0.
func (i VisionInsight) UrgencyScore() float64 {
	base, ok := map[string]float64{"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}[i.Impact]
	if !ok {
		base = 0.5
	}
	if i.ExpiresAt != nil {
		days := pyDays(i.ExpiresAt.Sub(now()))
		if days <= 1 {
			return math.Min(base*1.5, 1.0)
		} else if days <= 7 {
			return math.Min(base*1.2, 1.0)
		}
	}
	return base
}

// ToDict converts to a dictionary representation.
func (i VisionInsight) ToDict() map[string]any {
	return map[string]any{
		"id": i.ID, "type": i.Type, "title": i.Title, "description": i.Description, "impact": i.Impact,
		"affected_objectives": i.AffectedObjectives, "affected_tasks": i.AffectedTasks,
		"suggested_actions": i.SuggestedActions, "created_at": IsoFormat(i.CreatedAt),
		"expires_at": isoOrNil(i.ExpiresAt), "is_expired": i.IsExpired(), "urgency_score": i.UrgencyScore(),
		"metadata": i.Metadata,
	}
}

// VisionDashboard is aggregated vision metrics and insights for an executive view.
type VisionDashboard struct {
	Timestamp               time.Time
	TotalObjectives         int
	ActiveObjectives        int
	CompletedObjectives     int
	OverallProgress         float64
	ObjectivesByLevel       map[string]int
	ObjectivesByStatus      map[string]int
	TopPerformingObjectives []map[string]any
	AtRiskObjectives        []map[string]any
	RecentCompletions       []map[string]any
	ActiveInsights          []VisionInsight
	AlignmentSummary        map[string]any
}

// NewVisionDashboard applies Python defaults (timestamp now, zero counts, empty collections).
func NewVisionDashboard() VisionDashboard {
	return VisionDashboard{Timestamp: now(), ObjectivesByLevel: map[string]int{}, ObjectivesByStatus: map[string]int{},
		TopPerformingObjectives: []map[string]any{}, AtRiskObjectives: []map[string]any{},
		RecentCompletions: []map[string]any{}, ActiveInsights: []VisionInsight{}, AlignmentSummary: map[string]any{}}
}

// ToDict converts to a dictionary representation.
func (d VisionDashboard) ToDict() map[string]any {
	insights := make([]map[string]any, len(d.ActiveInsights))
	for i, in := range d.ActiveInsights {
		insights[i] = in.ToDict()
	}
	return map[string]any{
		"timestamp": IsoFormat(d.Timestamp),
		"summary": map[string]any{
			"total_objectives": d.TotalObjectives, "active_objectives": d.ActiveObjectives,
			"completed_objectives": d.CompletedObjectives, "overall_progress": d.OverallProgress,
		},
		"breakdowns": map[string]any{"by_level": d.ObjectivesByLevel, "by_status": d.ObjectivesByStatus},
		"highlights": map[string]any{
			"top_performing": d.TopPerformingObjectives, "at_risk": d.AtRiskObjectives,
			"recent_completions": d.RecentCompletions,
		},
		"insights":  insights,
		"alignment": d.AlignmentSummary,
	}
}
