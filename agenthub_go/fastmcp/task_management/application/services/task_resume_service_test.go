package services

import (
	"context"
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// The fakes below are the whole world of these tests: no database, no session, no clock. They are
// seams for the five reads the service declares, and they answer by task id alone.
type resumeFakeTaskRead struct {
	task *entities.Task
	err  error
}

func (f *resumeFakeTaskRead) FindByID(context.Context, value_objects.TaskId) (*entities.Task, error) {
	return f.task, f.err
}

type resumeFakeSubtaskRead struct {
	subtasks []*entities.Subtask
	err      error
}

func (f *resumeFakeSubtaskRead) FindByParentTaskID(context.Context, value_objects.TaskId) ([]*entities.Subtask, error) {
	return f.subtasks, f.err
}

type resumeFakeDependencyRead struct {
	statuses map[string]string
	err      error
}

func (f *resumeFakeDependencyRead) StatusesOf(context.Context, []string) (map[string]string, error) {
	return f.statuses, f.err
}

type resumeFakeContextRead struct {
	doc *entities.TaskContextUnified
	err error
}

func (f *resumeFakeContextRead) Get(context.Context, string) (*entities.TaskContextUnified, error) {
	return f.doc, f.err
}

type resumeFakeEventRead struct {
	events []*entities.TaskEvent
	err    error
}

func (f *resumeFakeEventRead) Events(context.Context, string) ([]*entities.TaskEvent, error) {
	return f.events, f.err
}

// resumeTestService wires the fakes the case supplies, defaulting the reads a case does not care
// about to empty answers.
func resumeTestService(task *entities.Task, subtasks []*entities.Subtask, statuses map[string]string,
	doc *entities.TaskContextUnified, events []*entities.TaskEvent) *TaskResumeService {
	if statuses == nil {
		statuses = map[string]string{}
	}
	return NewTaskResumeService(
		&resumeFakeTaskRead{task: task},
		&resumeFakeSubtaskRead{subtasks: subtasks},
		&resumeFakeDependencyRead{statuses: statuses},
		&resumeFakeContextRead{doc: doc},
		&resumeFakeEventRead{events: events},
	)
}

const resumeTestTaskID = "11111111-1111-1111-1111-111111111111"

func resumeTestID(t *testing.T, raw string) value_objects.TaskId {
	t.Helper()
	id, err := value_objects.NewTaskId(raw)
	if err != nil {
		t.Fatalf("NewTaskId(%q): %v", raw, err)
	}
	return id
}

func resumeTestStatus(t *testing.T, raw string) *value_objects.TaskStatus {
	t.Helper()
	status, err := value_objects.NewTaskStatus(raw)
	if err != nil {
		t.Fatalf("NewTaskStatus(%q): %v", raw, err)
	}
	return &status
}

// resumeTestTask is a plain in-progress task with the two criteria every case can lean on.
func resumeTestTask(t *testing.T, dependencies ...string) *entities.Task {
	t.Helper()
	id := resumeTestID(t, resumeTestTaskID)
	deps := []value_objects.TaskId{}
	for _, dep := range dependencies {
		deps = append(deps, resumeTestID(t, dep))
	}
	return &entities.Task{
		ID:                 &id,
		Title:              "Resume me",
		Status:             resumeTestStatus(t, "in_progress"),
		AcceptanceCriteria: []string{"criterion one", "criterion two"},
		Dependencies:       deps,
	}
}

func resumeTestSubtask(t *testing.T, raw, statusRaw string, progress int) *entities.Subtask {
	t.Helper()
	id := resumeTestID(t, raw)
	return &entities.Subtask{
		ID:                 &id,
		Title:              "subtask " + raw,
		Status:             resumeTestStatus(t, statusRaw),
		ProgressPercentage: progress,
	}
}

func resumeTestVerdict(seq int, verdict string, reasons []string) *entities.TaskEvent {
	return &entities.TaskEvent{
		Seq:  seq,
		Kind: entities.TaskEventKindGateVerdict,
		Payload: map[string]any{
			"verdict": verdict,
			"reasons": reasons,
		},
	}
}

func resumeTestEvidence(seq int, failed []string, exitCode int, numstat string) *entities.TaskEvent {
	return &entities.TaskEvent{
		Seq:  seq,
		Kind: entities.TaskEventKindEvidenceSubmitted,
		Payload: map[string]any{
			"base_sha": "base-sha",
			"head_sha": "head-sha",
			"numstat":  numstat,
			"test": map[string]any{
				"command":   "go test ./...",
				"exit_code": exitCode,
				"failed":    failed,
			},
		},
	}
}

func resumeMustGet(t *testing.T, m *entities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("brief is missing section %q; keys = %v", key, m.Keys())
	}
	return v
}

func resumeMustString(t *testing.T, m *entities.OrderedMap[any], key string) string {
	t.Helper()
	v, ok := resumeMustGet(t, m, key).(string)
	if !ok {
		t.Fatalf("section %q = %#v, want a string", key, resumeMustGet(t, m, key))
	}
	return v
}

func resumeMustSection(t *testing.T, m *entities.OrderedMap[any], key string) *entities.OrderedMap[any] {
	t.Helper()
	v, ok := resumeMustGet(t, m, key).(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("section %q = %#v, want an ordered map", key, resumeMustGet(t, m, key))
	}
	return v
}

func resumeJSON(t *testing.T, m *entities.OrderedMap[any]) string {
	t.Helper()
	s, err := value_objects.PyJSONDumps(m, -1)
	if err != nil {
		t.Fatalf("PyJSONDumps: %v", err)
	}
	return s
}

// TestResumeRejectVerdictDrivesNextAction is the O4 acceptance check: a task with a REJECT verdict
// resumes with that verdict's reasons as the next action, and the verdict section carries them.
func TestResumeRejectVerdictDrivesNextAction(t *testing.T) {
	svc := resumeTestService(resumeTestTask(t), nil, nil, nil, []*entities.TaskEvent{
		resumeTestVerdict(1, "reject", []string{"D3 failed, TestX still fails"}),
	})

	brief, err := svc.Resume(context.Background(), resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume: %v", err)
	}

	if got := resumeMustString(t, brief, "next_action"); got != "fix: D3 failed, TestX still fails" {
		t.Fatalf("next_action = %q, want the verdict's reasons", got)
	}
	verdict := resumeMustSection(t, brief, "last_verdict")
	if got := resumeMustString(t, verdict, "verdict"); got != "reject" {
		t.Fatalf("last_verdict.verdict = %q, want reject", got)
	}
	reasons, _ := verdict.Get("reasons")
	if got, ok := reasons.([]string); !ok || len(got) != 1 || got[0] != "D3 failed, TestX still fails" {
		t.Fatalf("last_verdict.reasons = %#v, want the reject's reasons", reasons)
	}
}

// TestResumeFailingEvidenceWithoutVerdictDrivesNextAction is the ladder's second arm: no verdict, but
// the last evidence's test run failed, so the next action names the failing tests.
func TestResumeFailingEvidenceWithoutVerdictDrivesNextAction(t *testing.T) {
	svc := resumeTestService(resumeTestTask(t), nil, nil, nil, []*entities.TaskEvent{
		resumeTestEvidence(1, []string{"TestX", "TestY"}, 1, "1\t1\tmain.go\n"),
	})

	brief, err := svc.Resume(context.Background(), resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume: %v", err)
	}

	if got := resumeMustString(t, brief, "next_action"); got != "fix: TestX; TestY" {
		t.Fatalf("next_action = %q, want the failing test names", got)
	}
	if resumeMustGet(t, brief, "last_verdict") != nil {
		t.Fatalf("last_verdict = %#v, want nil when the ledger holds no verdict", resumeMustGet(t, brief, "last_verdict"))
	}
	evidence := resumeMustSection(t, brief, "last_evidence")
	if got := resumeMustString(t, evidence, "head_sha"); got != "head-sha" {
		t.Fatalf("last_evidence.head_sha = %q, want head-sha", got)
	}
	failed, _ := evidence.Get("failing_tests")
	if got, ok := failed.([]string); !ok || len(got) != 2 || got[0] != "TestX" || got[1] != "TestY" {
		t.Fatalf("last_evidence.failing_tests = %#v, want [TestX TestY]", failed)
	}
}

// TestResumeOpenSubtasksAndBlockersAppear proves the two work-shape sections carry exactly the open
// subtasks and the dependencies that are not done, in the task's own order.
func TestResumeOpenSubtasksAndBlockersAppear(t *testing.T) {
	done := "22222222-2222-2222-2222-222222222222"
	open := "33333333-3333-3333-3333-333333333333"
	task := resumeTestTask(t, done, open)

	subtasks := []*entities.Subtask{
		resumeTestSubtask(t, "44444444-4444-4444-4444-444444444444", "done", 100),
		resumeTestSubtask(t, "55555555-5555-5555-5555-555555555555", "in_progress", 20),
	}
	statuses := map[string]string{done: "done", open: "in_progress"}

	svc := resumeTestService(task, subtasks, statuses, nil, nil)
	brief, err := svc.Resume(context.Background(), resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume: %v", err)
	}

	openSubtasks, _ := brief.Get("open_subtasks")
	list, ok := openSubtasks.([]any)
	if !ok || len(list) != 1 {
		t.Fatalf("open_subtasks = %#v, want exactly the one incomplete subtask", openSubtasks)
	}
	entry, ok := list[0].(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("open_subtasks[0] = %#v, want an ordered map", list[0])
	}
	if got := resumeMustString(t, entry, "id"); got != "55555555-5555-5555-5555-555555555555" {
		t.Fatalf("open_subtasks[0].id = %q, want the open subtask", got)
	}

	blockers, _ := brief.Get("blockers")
	ids, ok := blockers.([]string)
	if !ok || len(ids) != 1 || ids[0] != open {
		t.Fatalf("blockers = %#v, want the not-done dependency %s", blockers, open)
	}
}

// TestResumeLadderDefaultArm proves the ladder's default: nothing blocks, evidence passes, so the
// next action is the bare `continue`.
func TestResumeLadderDefaultArm(t *testing.T) {
	svc := resumeTestService(resumeTestTask(t), nil, nil, nil, []*entities.TaskEvent{
		resumeTestEvidence(1, nil, 0, "1\t1\tmain.go\n"),
	})

	brief, err := svc.Resume(context.Background(), resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume: %v", err)
	}
	if got := resumeMustString(t, brief, "next_action"); got != "continue" {
		t.Fatalf("next_action = %q, want continue", got)
	}
}

// TestResumeNoEvidenceStartsWithASubmission proves the ladder's no-evidence arm, distinct from both
// `continue` and `fix:`.
func TestResumeNoEvidenceStartsWithASubmission(t *testing.T) {
	svc := resumeTestService(resumeTestTask(t), nil, nil, nil, nil)

	brief, err := svc.Resume(context.Background(), resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume: %v", err)
	}
	if got := resumeMustString(t, brief, "next_action"); got != "start: submit evidence with 4genteam evidence" {
		t.Fatalf("next_action = %q, want the start arm", got)
	}
	if resumeMustGet(t, brief, "last_evidence") != nil {
		t.Fatalf("last_evidence = %#v, want nil with no evidence", resumeMustGet(t, brief, "last_evidence"))
	}
}

// TestResumeOverBudgetReportsOverageAndKeepsSections is the box's third check: an over-limit brief is
// returned WHOLE. The over-limit and under-limit briefs are the SAME task with a different context
// document size, so comparing their section keys and their non-budget facts proves nothing was
// dropped, and the context section still carries the full oversized document.
const resumeBigNote = 20000

func resumeBudgetBrief(t *testing.T, doc *entities.TaskContextUnified) *entities.OrderedMap[any] {
	t.Helper()
	task := resumeTestTask(t)
	contextID := "ctx-1"
	task.ContextID = &contextID
	svc := resumeTestService(task, nil, nil, doc, []*entities.TaskEvent{
		resumeTestEvidence(1, nil, 0, "1\t1\tmain.go\n"),
	})
	brief, err := svc.Resume(context.Background(), resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume: %v", err)
	}
	return brief
}

func TestResumeOverBudgetReportsOverageAndKeepsSections(t *testing.T) {
	small := entities.NewTaskContextUnified("ctx-small", "")
	small.TaskData = map[string]any{"notes": "small"}
	big := entities.NewTaskContextUnified("ctx-big", "")
	big.TaskData = map[string]any{"notes": strings.Repeat("x", resumeBigNote)}

	under := resumeBudgetBrief(t, small)
	over := resumeBudgetBrief(t, big)

	underBudget := resumeMustSection(t, under, "budget")
	overBudget := resumeMustSection(t, over, "budget")

	overTokens, _ := overBudget.Get("tokens")
	overLimit, _ := overBudget.Get("limit")
	overOverage, _ := overBudget.Get("overage")
	if overOverage.(int) <= 0 {
		t.Fatalf("budget = %v, want a POSITIVE overage reported rather than a truncation", overBudget)
	}
	if overLimit.(int) != resumeBriefTokenBudget {
		t.Fatalf("budget.limit = %v, want the named constant %d", overLimit, resumeBriefTokenBudget)
	}
	if overTokens.(int) <= resumeBriefTokenBudget {
		t.Fatalf("budget.tokens = %v, want it over the limit %d", overTokens, resumeBriefTokenBudget)
	}
	if underOverage, _ := underBudget.Get("overage"); underOverage.(int) != 0 {
		t.Fatalf("under-limit budget.overage = %v, want 0", underOverage)
	}

	// The section KEYS are identical: the over-limit brief kept every section.
	if got, want := over.Keys(), under.Keys(); strings.Join(got, ",") != strings.Join(want, ",") {
		t.Fatalf("sections differ: over = %v, under = %v", got, want)
	}
	// Every non-context FACT is identical: only the context document's size differed, so an
	// equal-value comparison here is the proof that nothing else was dropped or reshaped.
	for _, key := range under.Keys() {
		if key == "budget" || key == "context" {
			continue
		}
		underValue, _ := under.Get(key)
		overValue, _ := over.Get(key)
		if !reflect.DeepEqual(underValue, overValue) {
			t.Fatalf("section %q differs between the under- and over-limit briefs:\nunder = %#v\nover  = %#v",
				key, underValue, overValue)
		}
	}
	// The oversized context still travels WHOLE - that is what "reported, not cut" means.
	contextSection := resumeMustSection(t, over, "context")
	taskData, _ := contextSection.Get("task_data")
	notes, _ := taskData.(map[string]any)["notes"].(string)
	if len(notes) != resumeBigNote {
		t.Fatalf("over-limit context notes = %d bytes, want the full %d: the brief was truncated", len(notes), resumeBigNote)
	}
}

// TestResumeBriefIsFunctionOfInputsOnly is the second binding check: two calls whose seam data is
// identical but whose CONTEXT carries a different caller produce byte-identical briefs - no caller
// identity, seat, session or clock reaches the output.
func TestResumeBriefIsFunctionOfInputsOnly(t *testing.T) {
	svc := resumeTestService(resumeTestTask(t), nil, nil, nil, []*entities.TaskEvent{
		resumeTestVerdict(1, "reject", []string{"criterion two unmet"}),
		resumeTestEvidence(2, nil, 0, "2\t1\tmain.go\nlib.go\n"),
	})

	ctxA := WithActor(context.Background(), SeatActor("room-a/seat-one"))
	ctxB := WithActor(context.Background(), SeatActor("room-b/seat-two"))

	first, err := svc.Resume(ctxA, resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume (first caller): %v", err)
	}
	second, err := svc.Resume(ctxB, resumeTestTaskID)
	if err != nil {
		t.Fatalf("Resume (second caller): %v", err)
	}

	firstJSON := resumeJSON(t, first)
	secondJSON := resumeJSON(t, second)
	if firstJSON != secondJSON {
		t.Fatalf("briefs differ across callers:\nfirst  = %s\nsecond = %s", firstJSON, secondJSON)
	}
	if strings.Contains(firstJSON, "room-a") || strings.Contains(firstJSON, "seat-one") ||
		strings.Contains(firstJSON, "room-b") || strings.Contains(firstJSON, "seat-two") {
		t.Fatalf("the brief carries caller identity: %s", firstJSON)
	}
}
