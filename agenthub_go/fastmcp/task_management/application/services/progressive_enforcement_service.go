package services

// Port of
// agenthub_main/src/fastmcp/task_management/application/services/progressive_enforcement_service.py
//
// Progressive Enforcement Service for Manual Context System. It implements
// gradual enforcement based on agent behavior: new agents get more warnings
// before strict enforcement kicks in.

import (
	"fmt"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// AgentProfile mirrors the Python dataclass tracking an agent's learning
// progress. Optional datetime -> *time.Time.
type AgentProfile struct {
	AgentID                 string
	FirstSeen               time.Time
	EnforcementLevel        EnforcementLevel
	OperationsCount         int
	LearningPhaseOperations int
	WarningsReceived        int
	ConsecutiveCompliant    int
	ConsecutiveFailures     int
	LastEscalation          *time.Time
	ComplianceHistory       []bool
	ManuallySetLevel        bool
}

// NewAgentProfile mirrors AgentProfile(agent_id, first_seen, enforcement_level,
// learning_phase_operations=...). We only expose the fields the Python service
// passes at construction time.
func NewAgentProfile(agentID string, firstSeen time.Time, level EnforcementLevel, learningPhaseOperations int) *AgentProfile {
	return &AgentProfile{
		AgentID:                 agentID,
		FirstSeen:               firstSeen,
		EnforcementLevel:        level,
		LearningPhaseOperations: learningPhaseOperations,
		ComplianceHistory:       []bool{},
	}
}

// ShouldEscalate mirrors AgentProfile.should_escalate.
func (p *AgentProfile) ShouldEscalate() bool {
	if p.EnforcementLevel == zpEnfEnforcementLevelStrict {
		return false
	}
	if p.ConsecutiveFailures >= 5 {
		return true
	}
	if p.OperationsCount >= 20 {
		recent := p.ComplianceHistory
		if len(p.ComplianceHistory) >= 10 {
			recent = p.ComplianceHistory[len(p.ComplianceHistory)-10:]
		}
		rate := 0.0
		if len(recent) > 0 {
			rate = float64(zpProgCountTrue(recent)) / float64(len(recent))
		}
		if rate < 0.6 {
			return true
		}
	}
	if p.EnforcementLevel == zpEnfEnforcementLevelWarning && p.WarningsReceived >= 10 {
		return true
	}
	return false
}

// ShouldDeescalate mirrors AgentProfile.should_deescalate.
func (p *AgentProfile) ShouldDeescalate() bool {
	if p.EnforcementLevel == zpEnfEnforcementLevelSoft {
		return false
	}
	if p.ConsecutiveCompliant >= 20 {
		recent := p.ComplianceHistory
		if len(p.ComplianceHistory) >= 20 {
			recent = p.ComplianceHistory[len(p.ComplianceHistory)-20:]
		}
		rate := 0.0
		if len(recent) > 0 {
			rate = float64(zpProgCountTrue(recent)) / float64(len(recent))
		}
		if rate >= 0.95 {
			return true
		}
	}
	return false
}

// UpdateCompliance mirrors AgentProfile.update_compliance.
func (p *AgentProfile) UpdateCompliance(isCompliant bool, wasWarned bool) {
	p.OperationsCount++
	p.ComplianceHistory = append(p.ComplianceHistory, isCompliant)
	if len(p.ComplianceHistory) > 100 {
		p.ComplianceHistory = p.ComplianceHistory[len(p.ComplianceHistory)-100:]
	}
	if isCompliant {
		p.ConsecutiveCompliant++
		p.ConsecutiveFailures = 0
	} else {
		p.ConsecutiveFailures++
		p.ConsecutiveCompliant = 0
		if wasWarned {
			p.WarningsReceived++
		}
	}
}

// EscalateLevel mirrors AgentProfile.escalate_level.
func (p *AgentProfile) EscalateLevel() {
	if p.EnforcementLevel == zpEnfEnforcementLevelSoft {
		p.EnforcementLevel = zpEnfEnforcementLevelWarning
	} else if p.EnforcementLevel == zpEnfEnforcementLevelWarning {
		p.EnforcementLevel = zpEnfEnforcementLevelStrict
	}
	now := time.Now().UTC()
	p.LastEscalation = &now
	p.ConsecutiveFailures = 0
	p.ManuallySetLevel = false
}

// DeescalateLevel mirrors AgentProfile.deescalate_level.
func (p *AgentProfile) DeescalateLevel() {
	if p.EnforcementLevel == zpEnfEnforcementLevelStrict {
		p.EnforcementLevel = zpEnfEnforcementLevelWarning
	} else if p.EnforcementLevel == zpEnfEnforcementLevelWarning {
		p.EnforcementLevel = zpEnfEnforcementLevelSoft
	}
	p.ConsecutiveCompliant = 0
	p.ManuallySetLevel = false
}

// ProgressiveEnforcementService mirrors the Python class.
type ProgressiveEnforcementService struct {
	EnforcementService *ParameterEnforcementService
	DefaultLevel       EnforcementLevel
	AgentProfiles      map[string]*AgentProfile
	// mu guards the per-agent maps: one service serves concurrent MCP calls.
	mu sync.Mutex
}

// Configuration for progressive enforcement (Python class attributes).
const (
	ProgressiveDefaultStartingLevel         = zpEnfEnforcementLevelWarning
	ProgressiveLearningPhaseOperations      = 10
	ProgressiveEscalationThresholdFailures  = 5
	ProgressiveDeescalationThresholdSuccess = 20
	ProgressiveComplianceRateThreshold      = 0.6
)

// NewProgressiveEnforcementService mirrors __init__: enforcement_service or a
// fresh ParameterEnforcementService(default_level).
func NewProgressiveEnforcementService(enforcementService *ParameterEnforcementService, defaultLevel EnforcementLevel) *ProgressiveEnforcementService {
	if enforcementService == nil {
		enforcementService = NewParameterEnforcementService(defaultLevel, nil)
	}
	return &ProgressiveEnforcementService{
		EnforcementService: enforcementService,
		DefaultLevel:       defaultLevel,
		AgentProfiles:      map[string]*AgentProfile{},
	}
}

// EnforceWithProgression mirrors enforce_with_progression.
func (s *ProgressiveEnforcementService) EnforceWithProgression(action string, providedParams *entities.OrderedMap[any], agentID string) EnforcementResult {
	s.mu.Lock()
	defer s.mu.Unlock()
	profile := s.getOrCreateProfile(agentID)

	currentEnforcementLevel := profile.EnforcementLevel

	if profile.OperationsCount < ProgressiveLearningPhaseOperations {
		if currentEnforcementLevel == zpEnfEnforcementLevelStrict {
			currentEnforcementLevel = zpEnfEnforcementLevelWarning
		}
	}

	result := s.EnforcementService.Enforce(action, providedParams, &agentID, &currentEnforcementLevel)

	isCompliant := len(result.MissingRequired) == 0
	wasWarned := result.Level == zpEnfEnforcementLevelWarning && !isCompliant
	profile.UpdateCompliance(isCompliant, wasWarned)

	if profile.ShouldEscalate() {
		oldLevel := profile.EnforcementLevel
		profile.EscalateLevel()
		result.Hints = append(result.Hints,
			fmt.Sprintf("⚠️ Enforcement level increased from %s to %s due to repeated non-compliance",
				oldLevel.String(), profile.EnforcementLevel.String()))
	} else if profile.ShouldDeescalate() {
		oldLevel := profile.EnforcementLevel
		profile.DeescalateLevel()
		result.Hints = append(result.Hints,
			fmt.Sprintf("✅ Enforcement level decreased from %s to %s due to consistent compliance",
				oldLevel.String(), profile.EnforcementLevel.String()))
	}

	if profile.OperationsCount < ProgressiveLearningPhaseOperations {
		remaining := ProgressiveLearningPhaseOperations - profile.OperationsCount
		result.Hints = append(result.Hints,
			fmt.Sprintf("📚 Learning phase: %d operations remaining before standard enforcement", remaining))
	}

	if profile.OperationsCount >= 10 {
		recentCompliance := profile.ComplianceHistory
		if len(profile.ComplianceHistory) > 10 {
			recentCompliance = profile.ComplianceHistory[len(profile.ComplianceHistory)-10:]
		}
		rate := 0.0
		if len(recentCompliance) > 0 {
			rate = float64(zpProgCountTrue(recentCompliance)) / float64(len(recentCompliance))
		}
		result.Hints = append(result.Hints,
			fmt.Sprintf("📊 Recent compliance: %.0f%% (%d/10 operations)", rate*100, zpProgCountTrue(recentCompliance)))
	}

	return result
}

// getOrCreateProfile mirrors _get_or_create_profile.
func (s *ProgressiveEnforcementService) getOrCreateProfile(agentID string) *AgentProfile {
	if _, ok := s.AgentProfiles[agentID]; !ok {
		s.AgentProfiles[agentID] = NewAgentProfile(agentID, time.Now().UTC(), s.DefaultLevel, ProgressiveLearningPhaseOperations)
	}
	return s.AgentProfiles[agentID]
}

// GetAgentProfile mirrors get_agent_profile (nil when absent).
func (s *ProgressiveEnforcementService) GetAgentProfile(agentID string) *AgentProfile {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.AgentProfiles[agentID]
}

// GetAllProfiles mirrors get_all_profiles: a shallow copy of the map.
func (s *ProgressiveEnforcementService) GetAllProfiles() map[string]*AgentProfile {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make(map[string]*AgentProfile, len(s.AgentProfiles))
	for k, v := range s.AgentProfiles {
		out[k] = v
	}
	return out
}

// ResetAgentProfile mirrors reset_agent_profile.
func (s *ProgressiveEnforcementService) ResetAgentProfile(agentID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.AgentProfiles[agentID]; ok {
		s.AgentProfiles[agentID] = NewAgentProfile(agentID, time.Now().UTC(), s.DefaultLevel, ProgressiveLearningPhaseOperations)
	}
}

// SetAgentLevel mirrors set_agent_level.
func (s *ProgressiveEnforcementService) SetAgentLevel(agentID string, level EnforcementLevel) {
	s.mu.Lock()
	defer s.mu.Unlock()
	profile := s.getOrCreateProfile(agentID)
	profile.EnforcementLevel = level
	profile.ManuallySetLevel = true
}

// GetEnforcementStats mirrors get_enforcement_stats. The returned OrderedMap
// preserves Python dict insertion order; by_level is a nested OrderedMap.
func (s *ProgressiveEnforcementService) GetEnforcementStats() *entities.OrderedMap[any] {
	s.mu.Lock()
	defer s.mu.Unlock()
	byLevel := entities.NewOrderedMap[any]()
	byLevel.Set("soft", 0)
	byLevel.Set("warning", 0)
	byLevel.Set("strict", 0)

	problemAgents := []any{}

	stats := entities.NewOrderedMap[any]()
	stats.Set("total_agents", len(s.AgentProfiles))
	stats.Set("by_level", byLevel)
	stats.Set("learning_phase", 0)
	stats.Set("average_compliance", 0.0)
	stats.Set("problem_agents", problemAgents)

	totalCompliance := 0.0
	agentsWithHistory := 0

	for _, profile := range s.AgentProfiles {
		switch profile.EnforcementLevel {
		case zpEnfEnforcementLevelSoft:
			soft, _ := byLevel.Get("soft")
			byLevel.Set("soft", soft.(int)+1)
		case zpEnfEnforcementLevelWarning:
			warning, _ := byLevel.Get("warning")
			byLevel.Set("warning", warning.(int)+1)
		case zpEnfEnforcementLevelStrict:
			strict, _ := byLevel.Get("strict")
			byLevel.Set("strict", strict.(int)+1)
		}

		if profile.OperationsCount < ProgressiveLearningPhaseOperations {
			lp, _ := stats.Get("learning_phase")
			stats.Set("learning_phase", lp.(int)+1)
		}

		if len(profile.ComplianceHistory) > 0 {
			rate := float64(zpProgCountTrue(profile.ComplianceHistory)) / float64(len(profile.ComplianceHistory))
			totalCompliance += rate
			agentsWithHistory++

			if rate < 0.5 && profile.OperationsCount >= 20 {
				entry := entities.NewOrderedMap[any]()
				entry.Set("agent_id", profile.AgentID)
				entry.Set("compliance_rate", rate)
				entry.Set("operations", profile.OperationsCount)
				entry.Set("level", profile.EnforcementLevel.String())
				problemAgents = append(problemAgents, entry)
			}
		}
	}

	if agentsWithHistory > 0 {
		stats.Set("average_compliance", totalCompliance/float64(agentsWithHistory))
	}
	stats.Set("problem_agents", problemAgents)

	return stats
}

// zpProgCountTrue mirrors Python sum(list_of_bool).
func zpProgCountTrue(xs []bool) int {
	n := 0
	for _, x := range xs {
		if x {
			n++
		}
	}
	return n
}
