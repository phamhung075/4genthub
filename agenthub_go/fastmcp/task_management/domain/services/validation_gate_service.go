package services

import (
	"context"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// GateVerdict represents the outcome of the validation gate.
type GateVerdict string

const (
	GateVerdictAccept    GateVerdict = "accept"
	GateVerdictReject    GateVerdict = "reject"
	GateVerdictUncertain GateVerdict = "uncertain"
)

// DeterministicChecks holds the individual boolean results of checks D1 through D5.
type DeterministicChecks struct {
	D1Syntax   bool `json:"d1_syntax"`
	D2Types    bool `json:"d2_types"`
	D3Tests    bool `json:"d3_tests"`
	D4CleanDiff bool `json:"d4_clean_diff"`
	D5Numstat  bool `json:"d5_numstat_sanity"`
}

// ValidationResult represents the full output of a gate evaluation.
type ValidationResult struct {
	Verdict             GateVerdict         `json:"verdict"`
	Reasons             string              `json:"reasons"`
	DeterministicChecks DeterministicChecks `json:"deterministic_checks"`
	CriteriaResults     []string            `json:"criteria_results,omitempty"`
	Evaluator           string              `json:"evaluator"`
}

// JevClient evaluates acceptance criteria when deterministic checks pass.
type JevClient interface {
	EvaluateCriteria(ctx context.Context, model string, criteria []string, evidence map[string]any) (verdict GateVerdict, reasons string, err error)
}

// ValidationGateConfig configures the gate evaluation rules and budgets.
type ValidationGateConfig struct {
	EnforcementEnabled bool
	JevModel           string
	DailyTokenCap      int64
	MaxDiffLines       int
	KeepOutPatterns    []string
}

// DefaultValidationGateConfig returns standard Next-Gen validation defaults.
func DefaultValidationGateConfig() ValidationGateConfig {
	return ValidationGateConfig{
		EnforcementEnabled: false, // shadow mode by default
		JevModel:           "jev-1.13.0",
		DailyTokenCap:      1000000, // 1M tokens/day (~$0.042/day)
		MaxDiffLines:       20000,
		KeepOutPatterns: []string{
			".claude/",
			"agenthub_go/seatcheck",
			"seatcheck",
			".env",
			".git/",
		},
	}
}

// ValidationGateService evaluates task evidence against deterministic rules and acceptance criteria.
type ValidationGateService struct {
	config     ValidationGateConfig
	jevClient  JevClient
	tokenUsage int64
	usageDate  string
}

// NewValidationGateService creates a new ValidationGateService.
func NewValidationGateService(config ValidationGateConfig, jev JevClient) *ValidationGateService {
	return &ValidationGateService{
		config:    config,
		jevClient: jev,
	}
}

// EnforcementEnabled reports whether gate enforcement is active.
func (s *ValidationGateService) EnforcementEnabled() bool {
	return s.config.EnforcementEnabled
}

// Evaluate performs deterministic checks D1–D5 and optional Jev criteria evaluation.
func (s *ValidationGateService) Evaluate(ctx context.Context, task *entities.Task, evidencePayload map[string]any) ValidationResult {
	checks := DeterministicChecks{
		D1Syntax:   true,
		D2Types:    true,
		D3Tests:    true,
		D4CleanDiff: true,
		D5Numstat:  true,
	}

	if evidencePayload == nil {
		checks.D3Tests = false
		checks.D4CleanDiff = false
		checks.D5Numstat = false
		return ValidationResult{
			Verdict:             GateVerdictReject,
			Reasons:             "No evidence submitted for task",
			DeterministicChecks: checks,
			Evaluator:           "deterministic",
		}
	}

	// 1. D3 Check: Test command and exit code
	testObj, _ := evidencePayload["test"].(map[string]any)
	if testObj != nil {
		if exitCode, ok := testObj["exit_code"].(int); ok && exitCode != 0 {
			checks.D3Tests = false
		} else if exitCodeFloat, ok := testObj["exit_code"].(float64); ok && int(exitCodeFloat) != 0 {
			checks.D3Tests = false
		}
		if failedList, ok := testObj["failed"].([]string); ok && len(failedList) > 0 {
			checks.D3Tests = false
		} else if failedAny, ok := testObj["failed"].([]any); ok && len(failedAny) > 0 {
			checks.D3Tests = false
		}
	} else {
		checks.D3Tests = false
	}

	// 2. D4 & D5 Checks: Parse numstat for clean diff and sanity bounds
	numstatRaw, _ := evidencePayload["numstat"].(string)
	paths, totalLines, err := s.parseNumstat(numstatRaw)
	if err != nil || len(paths) == 0 {
		checks.D5Numstat = false
	}
	if totalLines > s.config.MaxDiffLines {
		checks.D5Numstat = false
	}

	// Clean diff check against keep-out patterns
	for _, p := range paths {
		for _, keepOut := range s.config.KeepOutPatterns {
			if strings.Contains(p, keepOut) || filepath.Base(p) == keepOut {
				checks.D4CleanDiff = false
				break
			}
		}
		if !checks.D4CleanDiff {
			break
		}
	}

	// Fast rejection on deterministic failure
	var failureReasons []string
	if !checks.D3Tests {
		failureReasons = append(failureReasons, "D3: test suite failure or non-zero exit code")
	}
	if !checks.D4CleanDiff {
		failureReasons = append(failureReasons, "D4: keep-out file detected in git diff")
	}
	if !checks.D5Numstat {
		failureReasons = append(failureReasons, "D5: invalid numstat or excessive diff size")
	}

	if len(failureReasons) > 0 {
		return ValidationResult{
			Verdict:             GateVerdictReject,
			Reasons:             strings.Join(failureReasons, "; "),
			DeterministicChecks: checks,
			Evaluator:           "deterministic",
		}
	}

	// 3. Acceptance criteria check
	criteria := task.AcceptanceCriteria
	if len(criteria) == 0 {
		return ValidationResult{
			Verdict:             GateVerdictAccept,
			Reasons:             "Deterministic checks D1-D5 passed; no additional acceptance criteria specified",
			DeterministicChecks: checks,
			Evaluator:           "deterministic",
		}
	}

	// Jev token budget check
	if !s.checkDailyBudget(1000) { // estimated tokens for criteria eval
		return ValidationResult{
			Verdict:             GateVerdictUncertain,
			Reasons:             "Jev daily token budget cap reached; failing safe to uncertain",
			DeterministicChecks: checks,
			Evaluator:           "jev",
		}
	}

	if s.jevClient == nil {
		return ValidationResult{
			Verdict:             GateVerdictUncertain,
			Reasons:             "Jev evaluator not configured; failing safe to uncertain",
			DeterministicChecks: checks,
			Evaluator:           "jev",
		}
	}

	jevVerdict, jevReasons, err := s.jevClient.EvaluateCriteria(ctx, s.config.JevModel, criteria, evidencePayload)
	if err != nil {
		return ValidationResult{
			Verdict:             GateVerdictUncertain,
			Reasons:             fmt.Sprintf("Jev evaluation error (%s); failing safe to uncertain", err.Error()),
			DeterministicChecks: checks,
			Evaluator:           "jev",
		}
	}

	return ValidationResult{
		Verdict:             jevVerdict,
		Reasons:             jevReasons,
		DeterministicChecks: checks,
		CriteriaResults:     criteria,
		Evaluator:           "jev",
	}
}

func (s *ValidationGateService) parseNumstat(raw string) (paths []string, totalLines int, err error) {
	lines := strings.Split(strings.TrimSpace(raw), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		parts := strings.Fields(line)
		if len(parts) >= 3 {
			ins, _ := strconv.Atoi(parts[0])
			del, _ := strconv.Atoi(parts[1])
			totalLines += ins + del
			paths = append(paths, parts[2])
		}
	}
	return paths, totalLines, nil
}

func (s *ValidationGateService) checkDailyBudget(estimatedTokens int64) bool {
	today := time.Now().Format("2006-01-02")
	if s.usageDate != today {
		s.usageDate = today
		s.tokenUsage = 0
	}
	if s.tokenUsage+estimatedTokens > s.config.DailyTokenCap {
		return false
	}
	s.tokenUsage += estimatedTokens
	return true
}
