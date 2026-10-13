package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

type mockJevClient struct {
	verdict GateVerdict
	reasons string
	err     error
}

func (m *mockJevClient) EvaluateCriteria(ctx context.Context, model string, criteria []string, evidence map[string]any) (GateVerdict, string, error) {
	if m.err != nil {
		return GateVerdictUncertain, "", m.err
	}
	return m.verdict, m.reasons, nil
}

func TestValidationGateDeterministicFailures(t *testing.T) {
	config := DefaultValidationGateConfig()
	service := NewValidationGateService(config, nil)

	task := &entities.Task{}

	// Case 1: No evidence
	res := service.Evaluate(context.Background(), task, nil)
	if res.Verdict != GateVerdictReject {
		t.Fatalf("Expected reject on nil evidence, got %s", res.Verdict)
	}

	// Case 2: Test failed exit code
	evidenceFailTest := map[string]any{
		"numstat": "10\t2\tmain.go",
		"test": map[string]any{
			"command":   "go test ./...",
			"exit_code": 1,
			"failed":    []string{"TestFoo"},
		},
	}
	res = service.Evaluate(context.Background(), task, evidenceFailTest)
	if res.Verdict != GateVerdictReject {
		t.Fatalf("Expected reject on test exit code 1, got %s", res.Verdict)
	}
	if res.DeterministicChecks.D3Tests {
		t.Errorf("D3Tests should be false")
	}

	// Case 3: Keep-out file present in diff
	evidenceKeepOut := map[string]any{
		"numstat": "5\t0\t.claude/config.json\n10\t2\tmain.go",
		"test": map[string]any{
			"command":   "go test ./...",
			"exit_code": 0,
			"failed":    []string{},
		},
	}
	res = service.Evaluate(context.Background(), task, evidenceKeepOut)
	if res.Verdict != GateVerdictReject {
		t.Fatalf("Expected reject on keep-out file, got %s", res.Verdict)
	}
	if res.DeterministicChecks.D4CleanDiff {
		t.Errorf("D4CleanDiff should be false")
	}
}

func TestValidationGateDeterministicPassNoCriteria(t *testing.T) {
	config := DefaultValidationGateConfig()
	service := NewValidationGateService(config, nil)

	task := &entities.Task{}
	cleanEvidence := map[string]any{
		"numstat": "10\t2\tpkg/math.go",
		"test": map[string]any{
			"command":   "go test ./...",
			"exit_code": 0,
			"failed":    []string{},
		},
	}

	res := service.Evaluate(context.Background(), task, cleanEvidence)
	if res.Verdict != GateVerdictAccept {
		t.Fatalf("Expected accept, got %s (reasons: %s)", res.Verdict, res.Reasons)
	}
	if !res.DeterministicChecks.D1Syntax || !res.DeterministicChecks.D2Types ||
		!res.DeterministicChecks.D3Tests || !res.DeterministicChecks.D4CleanDiff ||
		!res.DeterministicChecks.D5Numstat {
		t.Errorf("All deterministic checks should be true: %+v", res.DeterministicChecks)
	}
}

func TestValidationGateJevBudgetExceededFailsSafe(t *testing.T) {
	config := DefaultValidationGateConfig()
	config.DailyTokenCap = 500 // smaller than 1000 estimation
	service := NewValidationGateService(config, &mockJevClient{verdict: GateVerdictAccept})

	task := &entities.Task{
		AcceptanceCriteria: []string{"Must compute factorials correctly"},
	}
	cleanEvidence := map[string]any{
		"numstat": "10\t2\tpkg/math.go",
		"test": map[string]any{
			"command":   "go test ./...",
			"exit_code": 0,
			"failed":    []string{},
		},
	}

	res := service.Evaluate(context.Background(), task, cleanEvidence)
	if res.Verdict != GateVerdictUncertain {
		t.Fatalf("Expected fail-safe uncertain on budget cap, got %s", res.Verdict)
	}
}

func TestValidationGateJevClientErrorFailsSafe(t *testing.T) {
	config := DefaultValidationGateConfig()
	service := NewValidationGateService(config, &mockJevClient{err: errors.New("timeout")})

	task := &entities.Task{
		AcceptanceCriteria: []string{"Must compute factorials correctly"},
	}
	cleanEvidence := map[string]any{
		"numstat": "10\t2\tpkg/math.go",
		"test": map[string]any{
			"command":   "go test ./...",
			"exit_code": 0,
			"failed":    []string{},
		},
	}

	res := service.Evaluate(context.Background(), task, cleanEvidence)
	if res.Verdict != GateVerdictUncertain {
		t.Fatalf("Expected fail-safe uncertain on Jev error, got %s", res.Verdict)
	}
}

func TestValidationGateJevAccepts(t *testing.T) {
	config := DefaultValidationGateConfig()
	service := NewValidationGateService(config, &mockJevClient{
		verdict: GateVerdictAccept,
		reasons: "Criteria 1 validated by test cases",
	})

	task := &entities.Task{
		AcceptanceCriteria: []string{"Must compute factorials correctly"},
	}
	cleanEvidence := map[string]any{
		"numstat": "10\t2\tpkg/math.go",
		"test": map[string]any{
			"command":   "go test ./...",
			"exit_code": 0,
			"failed":    []string{},
		},
	}

	res := service.Evaluate(context.Background(), task, cleanEvidence)
	if res.Verdict != GateVerdictAccept {
		t.Fatalf("Expected accept from Jev, got %s", res.Verdict)
	}
}
