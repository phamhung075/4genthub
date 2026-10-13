package use_cases

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
)

type mockGateEvaluator struct {
	result      services.ValidationResult
	enforcement bool
}

func (m *mockGateEvaluator) Evaluate(ctx context.Context, task *entities.Task, evidence map[string]any) services.ValidationResult {
	return m.result
}

func (m *mockGateEvaluator) EnforcementEnabled() bool {
	return m.enforcement
}

type mockEvidenceFetcher struct {
	evidence map[string]any
}

func (m *mockEvidenceFetcher) LatestEvidence(ctx context.Context, taskID string) (map[string]any, error) {
	return m.evidence, nil
}

func TestCompleteTaskGateShadowMode(t *testing.T) {
	task := draftNewTask(t, "test-task")
	taskID := task.ID.Value
	repo := &ledgerFakeRepo{
		task: task,
		rows: map[string]string{taskID: "in_progress"},
	}

	rec := &ledgerFakeRecorder{repo: repo}
	tx := &ledgerFakeTx{}

	gate := &mockGateEvaluator{
		result: services.ValidationResult{
			Verdict: services.GateVerdictReject,
			Reasons: "D3 test failure",
		},
		enforcement: false, // Shadow mode!
	}

	summary := "Finished"
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).
		WithLedger(StatusLedger{Tx: tx, Ledger: rec}).
		WithGate(gate, &mockEvidenceFetcher{})

	res, err := uc.Execute(context.Background(), taskID, &summary, nil, nil)
	if err != nil {
		t.Fatalf("unexpected error in shadow mode: %v", err)
	}

	// In shadow mode, completion succeeds despite reject verdict
	success, _ := res.Get("success")
	if success != true {
		t.Fatalf("expected success in shadow mode, got: %v", res)
	}
	if task.Status.String() != "done" {
		t.Fatalf("expected task status done, got: %s", task.Status.String())
	}
}

func TestCompleteTaskGateEnforcementRejection(t *testing.T) {
	task := draftNewTask(t, "test-task-reject")
	taskID := task.ID.Value
	repo := &ledgerFakeRepo{
		task: task,
		rows: map[string]string{taskID: "in_progress"},
	}

	rec := &ledgerFakeRecorder{repo: repo}
	tx := &ledgerFakeTx{}

	gate := &mockGateEvaluator{
		result: services.ValidationResult{
			Verdict: services.GateVerdictReject,
			Reasons: "D4 keep-out file present",
		},
		enforcement: true, // Enforcement enabled!
	}

	summary := "Finished"
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).
		WithLedger(StatusLedger{Tx: tx, Ledger: rec}).
		WithGate(gate, &mockEvidenceFetcher{})

	res, err := uc.Execute(context.Background(), taskID, &summary, nil, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// In enforcement mode, completion is refused
	success, _ := res.Get("success")
	if success != false {
		t.Fatalf("expected failure in enforcement mode, got: %v", res)
	}
	if task.Status.String() != "in_progress" {
		t.Fatalf("expected task status in_progress, got: %s", task.Status.String())
	}
}

func TestCompleteTaskGateEnforcementUncertainEscalates(t *testing.T) {
	task := draftNewTask(t, "test-task-uncertain")
	taskID := task.ID.Value
	repo := &ledgerFakeRepo{
		task: task,
		rows: map[string]string{taskID: "in_progress"},
	}

	rec := &ledgerFakeRecorder{repo: repo}
	tx := &ledgerFakeTx{}

	gate := &mockGateEvaluator{
		result: services.ValidationResult{
			Verdict: services.GateVerdictUncertain,
			Reasons: "Jev budget cap reached",
		},
		enforcement: true,
	}

	summary := "Finished"
	uc := NewCompleteTaskUseCase(repo, nil, nil, nil).
		WithLedger(StatusLedger{Tx: tx, Ledger: rec}).
		WithGate(gate, &mockEvidenceFetcher{})

	res, err := uc.Execute(context.Background(), taskID, &summary, nil, nil)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	success, _ := res.Get("success")
	if success != false {
		t.Fatalf("expected failure/escalation, got: %v", res)
	}
	if task.Status.String() != "review" {
		t.Fatalf("expected task status review, got: %s", task.Status.String())
	}
}
