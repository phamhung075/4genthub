package services

// Parameter Enforcement Service for Manual Context System
//
// This service enforces context parameter requirements based on action and configuration.
// It provides progressive enforcement levels from logging-only to strict blocking.
//
// Part of Phase 2: Core Enforcement Implementation
// (Python application/services/parameter_enforcement_service.py)

import (
	"strings"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// EnforcementLevel is the severity of parameter validation.
type EnforcementLevel string

const (
	zpEnfEnforcementLevelDisabled EnforcementLevel = "disabled" // No enforcement
	zpEnfEnforcementLevelSoft     EnforcementLevel = "soft"     // Log only, no blocking
	zpEnfEnforcementLevelWarning  EnforcementLevel = "warning"  // Warn but allow operation
	zpEnfEnforcementLevelStrict   EnforcementLevel = "strict"   // Block operation if parameters missing
)

func (e EnforcementLevel) String() string { return string(e) }

// EnforcementResult is the result of a parameter enforcement check.
type EnforcementResult struct {
	Allowed            bool
	Level              EnforcementLevel
	MissingRequired    []string
	MissingRecommended []string
	Message            string
	Hints              []string
	Examples           *entities.OrderedMap[any]
	ComplianceTracked  bool
	AgentID            *string
}

// AgentCompliance tracks agent compliance statistics.
type AgentCompliance struct {
	AgentID             string
	TotalOperations     int
	CompliantOperations int
	WarningsIssued      int
	OperationsBlocked   int
	ConsecutiveFailures int
	LastOperation       *time.Time
	ComplianceRate      float64
}

// UpdateCompliance mirrors update_compliance.
func (c *AgentCompliance) UpdateCompliance(isCompliant bool, wasBlocked bool) {
	c.TotalOperations++
	if isCompliant {
		c.CompliantOperations++
		c.ConsecutiveFailures = 0
	} else {
		c.ConsecutiveFailures++
		if wasBlocked {
			c.OperationsBlocked++
		} else {
			c.WarningsIssued++
		}
	}
	if c.TotalOperations > 0 {
		c.ComplianceRate = float64(c.CompliantOperations) / float64(c.TotalOperations)
	} else {
		c.ComplianceRate = 0.0
	}
	now := time.Now().UTC()
	c.LastOperation = &now
}

// zpEnfRequiredParams is the Python REQUIRED_PARAMS class attribute (key order is not
// observed; lookups only).
var zpEnfRequiredParams = map[string]map[string][]string{
	"update": {
		"strict":      {"work_notes", "progress_made"},
		"recommended": {"files_modified", "blockers_encountered", "decisions_made"},
	},
	"complete": {
		"strict":      {"completion_summary"},
		"recommended": {"testing_notes", "deployment_notes", "files_created", "files_modified"},
	},
	"create": {
		"strict":      {},
		"recommended": {"estimated_effort", "initial_thoughts", "approach"},
	},
	"subtask_update": {
		"strict":      {"progress_notes"},
		"recommended": {"blockers", "insights_found"},
	},
	"subtask_complete": {
		"strict":      {"completion_summary"},
		"recommended": {"impact_on_parent", "insights_found", "testing_notes"},
	},
}

// zpEnfParameterTemplates is the Python PARAMETER_TEMPLATES class attribute.
var zpEnfParameterTemplates = map[string]any{
	"work_notes":           "Brief description of work being done (e.g., 'Refactoring authentication module')",
	"progress_made":        "What was accomplished (e.g., 'Completed JWT implementation')",
	"completion_summary":   "Detailed summary of what was completed (e.g., 'Implemented JWT auth with refresh tokens, added rate limiting, created comprehensive tests')",
	"testing_notes":        "Testing performed (e.g., 'Unit tests added with 95% coverage, integration tests passing')",
	"files_modified":       []string{"auth/jwt.py", "auth/middleware.py", "tests/test_auth.py"},
	"blockers_encountered": []string{"Redis connection timeout", "Missing API documentation"},
	"decisions_made":       []string{"Use Redis for token storage", "Implement refresh token rotation"},
	"insights_found":       []string{"Found existing utility for token generation", "Database index needed for performance"},
}

// zpEnfRequirements mirrors requirements.get(kind, []).
func zpEnfRequirements(action, kind string) []string {
	requirements, ok := zpEnfRequiredParams[action]
	if !ok {
		return []string{}
	}
	values, ok := requirements[kind]
	if !ok {
		return []string{}
	}
	return values
}

// zpEnfMissing mirrors `p not in provided_params or not provided_params[p]`.
func zpEnfMissing(providedParams *entities.OrderedMap[any], key string) bool {
	if providedParams == nil {
		return true
	}
	v, ok := providedParams.Get(key)
	if !ok {
		return true
	}
	return !value_objects.PyTruthy(v)
}

// zpEnfExamples builds an empty Python dict for a result.
func zpEnfExamples() *entities.OrderedMap[any] { return entities.NewOrderedMap[any]() }

// ParameterEnforcementService enforces context parameter requirements.
type ParameterEnforcementService struct {
	userID           *string
	EnforcementLevel EnforcementLevel
	AgentCompliance  *entities.OrderedMap[*AgentCompliance]
	// mu guards the per-agent maps: one service serves concurrent MCP calls.
	mu sync.Mutex
}

// NewParameterEnforcementService mirrors
// __init__(enforcement_level=EnforcementLevel.WARNING, user_id=None).
func NewParameterEnforcementService(enforcementLevel EnforcementLevel, userID *string) *ParameterEnforcementService {
	return &ParameterEnforcementService{
		userID:           userID,
		EnforcementLevel: enforcementLevel,
		AgentCompliance:  entities.NewOrderedMap[*AgentCompliance](),
	}
}

// WithUser creates a new service instance scoped to a specific user.
func (s *ParameterEnforcementService) WithUser(userID string) *ParameterEnforcementService {
	return NewParameterEnforcementService(s.EnforcementLevel, &userID)
}

// Enforce enforces parameter requirements for an action.
func (s *ParameterEnforcementService) Enforce(action string, providedParams *entities.OrderedMap[any], agentID *string, enforcementLevel *EnforcementLevel) EnforcementResult {
	s.mu.Lock()
	defer s.mu.Unlock()
	level := s.EnforcementLevel
	if enforcementLevel != nil {
		level = *enforcementLevel
	}

	if level == zpEnfEnforcementLevelDisabled {
		return EnforcementResult{
			Allowed:            true,
			Level:              level,
			MissingRequired:    []string{},
			MissingRecommended: []string{},
			Message:            "Parameter enforcement disabled",
			Hints:              []string{},
			Examples:           zpEnfExamples(),
		}
	}

	strictParams := zpEnfRequirements(action, "strict")
	recommendedParams := zpEnfRequirements(action, "recommended")

	missingRequired := make([]string, 0)
	for _, p := range strictParams {
		if zpEnfMissing(providedParams, p) {
			missingRequired = append(missingRequired, p)
		}
	}
	missingRecommended := make([]string, 0)
	for _, p := range recommendedParams {
		if zpEnfMissing(providedParams, p) {
			missingRecommended = append(missingRecommended, p)
		}
	}

	isCompliant := len(missingRequired) == 0
	if agentID != nil && *agentID != "" {
		s.trackEnforcement(*agentID, isCompliant, level == zpEnfEnforcementLevelStrict && !isCompliant)
	}

	switch level {
	case zpEnfEnforcementLevelSoft:
		return s.createSoftResult(missingRequired, missingRecommended, agentID)
	case zpEnfEnforcementLevelWarning:
		return s.createWarningResult(action, missingRequired, missingRecommended, agentID)
	case zpEnfEnforcementLevelStrict:
		if len(missingRequired) > 0 {
			return s.createStrictResult(action, missingRequired, missingRecommended, agentID)
		}
		hints := []string{}
		if len(missingRecommended) > 0 {
			hints = append(hints, "✅ All required parameters provided for "+action)
		}
		return EnforcementResult{
			Allowed:            true,
			Level:              zpEnfEnforcementLevelStrict,
			MissingRequired:    missingRequired,
			MissingRecommended: missingRecommended,
			Hints:              hints,
			Examples:           zpEnfExamples(),
			ComplianceTracked:  true,
			AgentID:            agentID,
		}
	}

	return EnforcementResult{
		Allowed:            true,
		Level:              level,
		MissingRequired:    []string{},
		MissingRecommended: []string{},
		Message:            "All required parameters provided",
		Hints:              []string{},
		Examples:           zpEnfExamples(),
	}
}

// createSoftResult creates the result for SOFT enforcement (log only).
func (s *ParameterEnforcementService) createSoftResult(missingRequired, missingRecommended []string, agentID *string) EnforcementResult {
	return EnforcementResult{
		Allowed:            true,
		Level:              zpEnfEnforcementLevelSoft,
		MissingRequired:    missingRequired,
		MissingRecommended: missingRecommended,
		Message:            "Operation allowed (soft enforcement - logging only)",
		ComplianceTracked:  agentID != nil,
		AgentID:            agentID,
		Hints:              []string{},
		Examples:           zpEnfExamples(),
	}
}

// createWarningResult creates the result for WARNING enforcement.
func (s *ParameterEnforcementService) createWarningResult(action string, missingRequired, missingRecommended []string, agentID *string) EnforcementResult {
	hints := []string{}
	examples := zpEnfExamples()

	if len(missingRequired) > 0 {
		hints = append(hints, "⚠️ Missing required parameters: "+strings.Join(missingRequired, ", "))
		hints = append(hints, "These parameters will be required in strict mode")

		for _, param := range missingRequired {
			if template, ok := zpEnfParameterTemplates[param]; ok {
				examples.Set(param, template)
			}
		}
	}

	if len(missingRecommended) > 0 {
		hints = append(hints, "💡 Consider adding: "+strings.Join(missingRecommended, ", "))
	}

	message := "Operation allowed"
	if len(missingRequired) > 0 {
		message = "Operation allowed with warnings"
	}

	return EnforcementResult{
		Allowed:            true,
		Level:              zpEnfEnforcementLevelWarning,
		MissingRequired:    missingRequired,
		MissingRecommended: missingRecommended,
		Message:            message,
		Hints:              hints,
		Examples:           examples,
		ComplianceTracked:  agentID != nil,
		AgentID:            agentID,
	}
}

// createStrictResult creates the result for STRICT enforcement (blocking).
func (s *ParameterEnforcementService) createStrictResult(action string, missingRequired, missingRecommended []string, agentID *string) EnforcementResult {
	hints := []string{
		"❌ Operation blocked: Missing required parameters for " + action,
		"Required: " + strings.Join(missingRequired, ", "),
		"Please provide these parameters to proceed",
	}
	if len(missingRecommended) > 0 {
		hints = append(hints, "Also recommended: "+strings.Join(missingRecommended, ", "))
	}

	examples := zpEnfExamples()
	for _, param := range missingRequired {
		if template, ok := zpEnfParameterTemplates[param]; ok {
			examples.Set(param, template)
		}
	}

	if action == "complete" {
		exampleCommand := entities.NewOrderedMap[any]()
		exampleCommand.Set("action", "complete")
		exampleCommand.Set("task_id", "<task_id>")
		exampleCommand.Set("completion_summary", "Implemented feature X with Y approach, achieving Z results")
		exampleCommand.Set("testing_notes", "Added unit tests with 90% coverage, all integration tests passing")
		examples.Set("example_command", exampleCommand)
	} else if action == "update" {
		exampleCommand := entities.NewOrderedMap[any]()
		exampleCommand.Set("action", "update")
		exampleCommand.Set("task_id", "<task_id>")
		exampleCommand.Set("work_notes", "Working on authentication module refactoring")
		exampleCommand.Set("progress_made", "Completed JWT token generation logic")
		exampleCommand.Set("files_modified", []string{"auth/jwt.py", "auth/utils.py"})
		examples.Set("example_command", exampleCommand)
	}

	return EnforcementResult{
		Allowed:            false,
		Level:              zpEnfEnforcementLevelStrict,
		MissingRequired:    missingRequired,
		MissingRecommended: missingRecommended,
		Message:            "Operation blocked: Missing required parameters (" + strings.Join(missingRequired, ", ") + ")",
		Hints:              hints,
		Examples:           examples,
		ComplianceTracked:  agentID != nil,
		AgentID:            agentID,
	}
}

// trackEnforcement tracks agent compliance statistics.
func (s *ParameterEnforcementService) trackEnforcement(agentID string, isCompliant bool, wasBlocked bool) {
	if s.AgentCompliance == nil {
		s.AgentCompliance = entities.NewOrderedMap[*AgentCompliance]()
	}
	compliance, ok := s.AgentCompliance.Get(agentID)
	if !ok {
		compliance = &AgentCompliance{AgentID: agentID}
		s.AgentCompliance.Set(agentID, compliance)
	}
	compliance.UpdateCompliance(isCompliant, wasBlocked)
}

// GetAgentCompliance returns the compliance statistics for an agent, or nil.
func (s *ParameterEnforcementService) GetAgentCompliance(agentID string) *AgentCompliance {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.AgentCompliance == nil {
		return nil
	}
	compliance, _ := s.AgentCompliance.Get(agentID)
	return compliance
}

// GetAllComplianceStats returns a shallow copy of the compliance map.
func (s *ParameterEnforcementService) GetAllComplianceStats() *entities.OrderedMap[*AgentCompliance] {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.AgentCompliance == nil {
		return entities.NewOrderedMap[*AgentCompliance]()
	}
	return s.AgentCompliance.Copy()
}

// SetEnforcementLevel updates the default enforcement level.
func (s *ParameterEnforcementService) SetEnforcementLevel(level EnforcementLevel) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.EnforcementLevel = level
}

// GetParameterHints returns helpful hints for parameters required by an action.
func (s *ParameterEnforcementService) GetParameterHints(action string) *entities.OrderedMap[any] {
	strictParams := zpEnfRequirements(action, "strict")
	recommendedParams := zpEnfRequirements(action, "recommended")

	templates := entities.NewOrderedMap[any]()
	allParams := append(append([]string{}, strictParams...), recommendedParams...)
	for _, param := range allParams {
		if template, ok := zpEnfParameterTemplates[param]; ok {
			templates.Set(param, template)
		}
	}

	hints := entities.NewOrderedMap[any]()
	hints.Set("action", action)
	hints.Set("required", strictParams)
	hints.Set("recommended", recommendedParams)
	hints.Set("templates", templates)
	return hints
}
