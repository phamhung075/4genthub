package value_objects

import (
	"math"
	"time"
)

// AgentsAgentRole is agents.AgentRole: specialized roles for coordination.
// Prefixed with the module name because agent_roles.AgentRole owns the plain name.
type AgentsAgentRole string

const (
	AgentsAgentRoleArchitect  AgentsAgentRole = "architect"
	AgentsAgentRoleDeveloper  AgentsAgentRole = "developer"
	AgentsAgentRoleTester     AgentsAgentRole = "tester"
	AgentsAgentRoleReviewer   AgentsAgentRole = "reviewer"
	AgentsAgentRoleManager    AgentsAgentRole = "manager"
	AgentsAgentRoleAnalyst    AgentsAgentRole = "analyst"
	AgentsAgentRoleDesigner   AgentsAgentRole = "designer"
	AgentsAgentRoleDevops     AgentsAgentRole = "devops"
	AgentsAgentRoleSecurity   AgentsAgentRole = "security"
	AgentsAgentRoleDocumenter AgentsAgentRole = "documenter"
)

// AgentExpertise: areas of expertise for skill matching.
type AgentExpertise string

const (
	AgentExpertiseFrontend          AgentExpertise = "frontend"
	AgentExpertiseBackend           AgentExpertise = "backend"
	AgentExpertiseDatabase          AgentExpertise = "database"
	AgentExpertiseCloud             AgentExpertise = "cloud"
	AgentExpertiseMobile            AgentExpertise = "mobile"
	AgentExpertiseAiMl              AgentExpertise = "ai_ml"
	AgentExpertiseSecurity          AgentExpertise = "security"
	AgentExpertisePerformance       AgentExpertise = "performance"
	AgentExpertiseTesting           AgentExpertise = "testing"
	AgentExpertiseDocumentation     AgentExpertise = "documentation"
	AgentExpertiseArchitecture      AgentExpertise = "architecture"
	AgentExpertiseProjectManagement AgentExpertise = "project_management"
)

// AgentCapabilities represents what an agent can do.
type AgentCapabilities struct {
	PrimaryRole        AgentsAgentRole
	SecondaryRoles     map[AgentsAgentRole]struct{}
	ExpertiseAreas     map[AgentExpertise]struct{}
	SkillLevels        map[string]float64 // skill -> proficiency (0-1)
	MaxTaskComplexity  int                // 1-10 scale
	PreferredTaskTypes map[string]struct{}
}

// NewAgentCapabilities applies the Python defaults (MaxTaskComplexity 5, empty sets).
func NewAgentCapabilities(primary AgentsAgentRole) AgentCapabilities {
	return AgentCapabilities{
		PrimaryRole:        primary,
		SecondaryRoles:     map[AgentsAgentRole]struct{}{},
		ExpertiseAreas:     map[AgentExpertise]struct{}{},
		SkillLevels:        map[string]float64{},
		MaxTaskComplexity:  5,
		PreferredTaskTypes: map[string]struct{}{},
	}
}

// CanHandleRole: primary or secondary role match.
func (c AgentCapabilities) CanHandleRole(role AgentsAgentRole) bool {
	_, secondary := c.SecondaryRoles[role]
	return role == c.PrimaryRole || secondary
}

// ExpertiseMatchScore returns the fraction of required expertise covered (0-1).
func (c AgentCapabilities) ExpertiseMatchScore(required map[AgentExpertise]struct{}) float64 {
	if len(required) == 0 {
		return 1.0
	}
	matching := 0
	for e := range required {
		if _, ok := c.ExpertiseAreas[e]; ok {
			matching++
		}
	}
	return float64(matching) / float64(len(required))
}

// SkillRequirement is one required skill. Requirements are an ordered slice
// (Python dict insertion order) so the float sum is deterministic.
type SkillRequirement struct {
	Skill string
	Level float64
}

// SkillMatchScore averages per-skill proficiency ratios, capped at 1 per skill,
// summing in the order given.
func (c AgentCapabilities) SkillMatchScore(required []SkillRequirement) float64 {
	if len(required) == 0 {
		return 1.0
	}
	total := 0.0
	for _, r := range required {
		agentLevel := c.SkillLevels[r.Skill]
		level := r.Level
		if agentLevel >= level {
			total += 1.0
		} else {
			total += agentLevel / level
		}
	}
	return total / float64(len(required))
}

// TaskRequirements is the typed form of the Python task_requirements dict.
type TaskRequirements struct {
	Role      *AgentsAgentRole // "role"
	Expertise []AgentExpertise // "expertise"
	Skills    []SkillRequirement
}

// AgentProfile holds agent profile and preferences.
type AgentProfile struct {
	AgentID                  string
	DisplayName              string
	Capabilities             AgentCapabilities
	AvailabilityScore        float64 // 0-1
	PerformanceScore         float64 // 0-1
	CollaborationStyle       string  // independent, collaborative, supervisory
	CommunicationPreferences map[string]struct{}
	TimeZone                 string
	WorkingHours             map[string]string
}

// NewAgentProfile applies the Python defaults.
func NewAgentProfile(agentID, displayName string, caps AgentCapabilities) AgentProfile {
	return AgentProfile{
		AgentID: agentID, DisplayName: displayName, Capabilities: caps,
		AvailabilityScore: 1.0, PerformanceScore: 1.0, CollaborationStyle: "independent",
		CommunicationPreferences: map[string]struct{}{}, TimeZone: "UTC",
	}
}

// OverallSuitabilityScore combines role (0.4), expertise (0.3), skills (0.3), then
// scales by availability and performance and clamps to [0, 1].
func (p AgentProfile) OverallSuitabilityScore(req TaskRequirements) float64 {
	roleScore := 1.0
	if req.Role != nil && !p.Capabilities.CanHandleRole(*req.Role) {
		roleScore = 0.0
	}
	expertise := make(map[AgentExpertise]struct{}, len(req.Expertise))
	for _, e := range req.Expertise {
		expertise[e] = struct{}{}
	}
	base := roleScore*0.4 +
		p.Capabilities.ExpertiseMatchScore(expertise)*0.3 +
		p.Capabilities.SkillMatchScore(req.Skills)*0.3
	return math.Min(1.0, math.Max(0.0, base*p.AvailabilityScore*p.PerformanceScore))
}

// AgentStatus is the current agent status.
type AgentStatus struct {
	AgentID               string
	IsAvailable           bool
	CurrentWorkload       int
	MaxWorkload           int
	ActiveTasks           []string
	LastActivity          time.Time
	StatusMessage         *string
	EstimatedAvailability *time.Time
}

// WorkloadPercentage returns workload as a percentage (0 when MaxWorkload is 0).
func (s AgentStatus) WorkloadPercentage() float64 {
	if s.MaxWorkload == 0 {
		return 0.0
	}
	return float64(s.CurrentWorkload) / float64(s.MaxWorkload) * 100.0
}

// CanAcceptWork: available and below max workload.
func (s AgentStatus) CanAcceptWork() bool { return s.IsAvailable && s.CurrentWorkload < s.MaxWorkload }

// CapacityScore returns remaining capacity clamped to [0, 1].
func (s AgentStatus) CapacityScore() float64 {
	if !s.IsAvailable || s.MaxWorkload == 0 {
		return 0.0
	}
	remaining := float64(s.MaxWorkload-s.CurrentWorkload) / float64(s.MaxWorkload)
	return math.Max(0.0, math.Min(1.0, remaining))
}

// AgentPerformanceMetrics tracks agent performance; mutable (non-frozen in Python).
type AgentPerformanceMetrics struct {
	AgentID               string
	TasksCompleted        int
	TasksFailed           int
	AverageCompletionTime float64 // hours
	QualityScore          float64 // 0-1
	CollaborationScore    float64 // 0-1
	ReliabilityScore      float64 // 0-1
	FeedbackScores        []float64
}

// NewAgentPerformanceMetrics applies the Python defaults (scores 1.0).
func NewAgentPerformanceMetrics(agentID string) *AgentPerformanceMetrics {
	return &AgentPerformanceMetrics{AgentID: agentID, QualityScore: 1.0, CollaborationScore: 1.0, ReliabilityScore: 1.0}
}

// SuccessRate is completed / total, or 1.0 with no tasks.
func (m *AgentPerformanceMetrics) SuccessRate() float64 {
	total := m.TasksCompleted + m.TasksFailed
	if total == 0 {
		return 1.0
	}
	return float64(m.TasksCompleted) / float64(total)
}

// OverallPerformanceScore is the weighted blend 0.3/0.3/0.2/0.2.
func (m *AgentPerformanceMetrics) OverallPerformanceScore() float64 {
	return m.SuccessRate()*0.3 + m.QualityScore*0.3 + m.CollaborationScore*0.2 + m.ReliabilityScore*0.2
}

// UpdateWithTaskResult records an outcome; qualityRating (optional) feeds the
// quality score as the mean of the last 10 ratings.
func (m *AgentPerformanceMetrics) UpdateWithTaskResult(success bool, completionTime float64, qualityRating *float64) {
	if success {
		m.TasksCompleted++
	} else {
		m.TasksFailed++
	}
	total := float64(m.TasksCompleted + m.TasksFailed)
	m.AverageCompletionTime = (m.AverageCompletionTime*(total-1) + completionTime) / total
	if qualityRating != nil {
		m.FeedbackScores = append(m.FeedbackScores, *qualityRating)
		recent := m.FeedbackScores
		if len(recent) > 10 {
			recent = recent[len(recent)-10:]
		}
		m.QualityScore = PySum(recent) / float64(len(recent))
	}
}
