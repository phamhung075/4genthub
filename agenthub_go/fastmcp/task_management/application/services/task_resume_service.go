package services

import (
	"context"
	"fmt"
	"strings"

	"agenthub/fastmcp/seat_management/domain/contextpacks"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// resumeBriefTokenBudget is the size budget of ONE resume brief, in tokens, measured with
// contextpacks.EstimateTokensOf over the brief's own JSON.
//
// IT IS A PRODUCT DEFAULT, NOT A LAW. The owner can change the number and NOTHING else moves: the
// budget block reports `tokens`, `limit` (this constant) and `overage`, and the brief's shape and
// section order are untouched by the value. The brief is NEVER truncated to fit - the overage is
// REPORTED, because a brief that silently drops the criteria or the last rejection's reasons is the
// silent-degradation failure this ledger exists to make impossible.
const resumeBriefTokenBudget = 4000

// TaskResumeTaskRead reads the task a brief is about. It is FindByID alone because every fact the
// brief needs of the task - status, acceptance criteria, dependency ids, the context document id -
// is carried by the Task entity itself.
type TaskResumeTaskRead interface {
	FindByID(ctx context.Context, taskID value_objects.TaskId) (*entities.Task, error)
}

// TaskResumeSubtaskRead lists the task's subtasks. WHICH of them count as open is the service's
// rule, not the reader's, so the reader is a plain list.
type TaskResumeSubtaskRead interface {
	FindByParentTaskID(ctx context.Context, parentTaskID value_objects.TaskId) ([]*entities.Subtask, error)
}

// TaskResumeDependencyRead answers the statuses of the tasks this task depends on, keyed by task id.
// It is deliberately a status read rather than a "blocking" read: the rule that a dependency blocks
// while it is not done lives in this service where it is reviewable, and a dependency the reader
// cannot resolve (no entry in the returned map) is reported as blocking rather than quietly dropped.
type TaskResumeDependencyRead interface {
	StatusesOf(ctx context.Context, taskIDs []string) (map[string]string, error)
}

// TaskResumeContextRead reads the TASK-LEVEL context document by its id. Inheritance across levels
// is manage_context action=resolve's job; this reader is the one document the level holds, and the
// brief names it as the task level rather than implying an inherited view.
type TaskResumeContextRead interface {
	Get(ctx context.Context, contextID string) (*entities.TaskContextUnified, error)
}

// TaskResumeEventRead reads the task's ledger. It takes no caller: the ledger is read for a task,
// and the identity that scopes the read belongs to whatever repository instance the composition
// hands in - it is never an input to the brief.
type TaskResumeEventRead interface {
	Events(ctx context.Context, taskID string) ([]*entities.TaskEvent, error)
}

// TaskResumeService builds the resume brief: ONE ordered map composed from the task, its subtasks,
// its dependencies, its task-level context document and its ledger.
//
// The brief is a FUNCTION OF ITS INPUTS ONLY. Every seam above is addressed by task id, never by
// caller, seat, session or clock, and the sections carry facts about the task rather than who asked,
// so two different callers resume the same work with BYTE-IDENTICAL briefs. Nothing is truncated;
// the budget block reports the size and the overage instead.
type TaskResumeService struct {
	tasks        TaskResumeTaskRead
	subtasks     TaskResumeSubtaskRead
	dependencies TaskResumeDependencyRead
	contexts     TaskResumeContextRead
	ledger       TaskResumeEventRead
}

// NewTaskResumeService builds the service over the five reads it needs.
func NewTaskResumeService(tasks TaskResumeTaskRead, subtasks TaskResumeSubtaskRead,
	dependencies TaskResumeDependencyRead, contexts TaskResumeContextRead, ledger TaskResumeEventRead) *TaskResumeService {
	return &TaskResumeService{tasks: tasks, subtasks: subtasks, dependencies: dependencies, contexts: contexts, ledger: ledger}
}

// Resume builds the brief for one task. The keys are emitted in the SECTION PRIORITY order decided
// by the lead - (1) task and acceptance_criteria, (2) last_verdict, (3) next_action, (4)
// open_subtasks and blockers, (5) last_evidence, (6) context and last_handover, then budget - so a
// consumer that reads only its first three sections still has the criteria, the last rejection's
// reasons and the next action. A future budget policy would cut against that order; nothing cuts now.
func (s *TaskResumeService) Resume(ctx context.Context, taskID string) (*entities.OrderedMap[any], error) {
	id, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil, err
	}

	task, err := s.tasks.FindByID(ctx, id)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task %s not found", taskID))
	}

	subtasks, err := s.subtasks.FindByParentTaskID(ctx, id)
	if err != nil {
		return nil, err
	}

	dependencyIDs := task.GetDependencyIDs()
	statuses := map[string]string{}
	if len(dependencyIDs) > 0 {
		statuses, err = s.dependencies.StatusesOf(ctx, dependencyIDs)
		if err != nil {
			return nil, err
		}
	}

	events, err := s.ledger.Events(ctx, taskID)
	if err != nil {
		return nil, err
	}

	var contextDoc *entities.TaskContextUnified
	if task.ContextID != nil && *task.ContextID != "" {
		contextDoc, err = s.contexts.Get(ctx, *task.ContextID)
		if err != nil {
			return nil, err
		}
	}

	verdict := resumeLastEvent(events, entities.TaskEventKindGateVerdict)
	evidence := resumeLastEvent(events, entities.TaskEventKindEvidenceSubmitted)
	handover := resumeLastEvent(events, entities.TaskEventKindHandover)

	openSubtasks := []any{}
	for _, subtask := range subtasks {
		if subtask == nil || resumeSubtaskCompleted(subtask) {
			continue
		}
		openSubtasks = append(openSubtasks, resumeSubtaskFacts(subtask))
	}

	blockers := []string{}
	for _, dependencyID := range dependencyIDs {
		if status, found := statuses[dependencyID]; !found || status != string(value_objects.TaskStatusDone) {
			blockers = append(blockers, dependencyID)
		}
	}

	brief := entities.NewOrderedMap[any]()
	brief.Set("task", resumeTaskFacts(task))
	brief.Set("acceptance_criteria", resumeStrings(task.AcceptanceCriteria))
	brief.Set("last_verdict", resumeVerdictSection(verdict))
	brief.Set("next_action", resumeNextAction(verdict, evidence, len(openSubtasks), blockers))
	brief.Set("open_subtasks", openSubtasks)
	brief.Set("blockers", blockers)
	brief.Set("last_evidence", resumeEvidenceSection(evidence, taskID))
	brief.Set("context", resumeContextSection(contextDoc))
	brief.Set("last_handover", resumeHandoverSection(handover))

	serialized, err := value_objects.PyJSONDumps(brief, -1)
	if err != nil {
		return nil, err
	}
	tokens := contextpacks.EstimateTokensOf(serialized)
	overage := tokens - resumeBriefTokenBudget
	if overage < 0 {
		overage = 0
	}
	budget := entities.NewOrderedMap[any]()
	budget.Set("tokens", tokens)
	budget.Set("limit", resumeBriefTokenBudget)
	budget.Set("overage", overage)
	brief.Set("budget", budget)

	return brief, nil
}

// resumeLastEvent is the most recent ledger entry of a kind, by the sequence the ledger assigned. A
// nil result means the task has no entry of that kind.
func resumeLastEvent(events []*entities.TaskEvent, kind entities.TaskEventKind) *entities.TaskEvent {
	var last *entities.TaskEvent
	for _, event := range events {
		if event == nil || event.Kind != kind {
			continue
		}
		if last == nil || event.Seq >= last.Seq {
			last = event
		}
	}
	return last
}

// resumeTaskFacts is the task as the brief names it: identity, title and stored status.
func resumeTaskFacts(task *entities.Task) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", task.GetEntityID())
	m.Set("title", task.Title)
	status := ""
	if task.Status != nil {
		status = task.Status.String()
	}
	m.Set("status", status)
	return m
}

// resumeVerdictSection emits the last gate verdict's verdict and reasons, or nil when the ledger
// holds none. Nothing else of the event travels: its actor is not part of the brief.
func resumeVerdictSection(event *entities.TaskEvent) any {
	if event == nil {
		return nil
	}
	m := entities.NewOrderedMap[any]()
	m.Set("verdict", resumeString(event.Payload["verdict"]))
	m.Set("reasons", resumeStrings(event.Payload["reasons"]))
	return m
}

// resumeEvidenceSection emits the last evidence as FACTS - the two shas, the failing test names and
// the touched-file count - and a LINK to the raw numstat rather than the numstat itself, which is
// the one unbounded part of a submission. Returns nil when the ledger holds no evidence.
func resumeEvidenceSection(event *entities.TaskEvent, taskID string) any {
	if event == nil {
		return nil
	}
	test := resumeTestBlock(event)
	m := entities.NewOrderedMap[any]()
	m.Set("base_sha", resumeString(event.Payload["base_sha"]))
	m.Set("head_sha", resumeString(event.Payload["head_sha"]))
	m.Set("failing_tests", resumeStrings(test["failed"]))
	m.Set("files_touched", resumeNumstatFiles(resumeString(event.Payload["numstat"])))
	m.Set("link", fmt.Sprintf("/api/v2/tasks/%s/events?after_seq=%d", taskID, event.Seq-1))
	return m
}

// resumeContextSection emits the TASK-LEVEL context document and says so: `level` is "task", because
// inheritance across levels is manage_context action=resolve's job and is not re-implemented here.
// Returns nil when the task names no context or the context read returned none.
func resumeContextSection(doc *entities.TaskContextUnified) any {
	if doc == nil {
		return nil
	}
	m := entities.NewOrderedMap[any]()
	m.Set("level", "task")
	m.Set("id", doc.ID)
	m.Set("branch_id", doc.BranchID)
	m.Set("task_data", doc.TaskData)
	m.Set("execution_context", doc.ExecutionContext)
	m.Set("discovered_patterns", doc.DiscoveredPatterns)
	m.Set("implementation_notes", doc.ImplementationNotes)
	m.Set("test_results", doc.TestResults)
	m.Set("blockers", doc.Blockers)
	m.Set("progress", doc.Progress)
	m.Set("insights", doc.Insights)
	m.Set("next_steps", doc.NextSteps)
	m.Set("metadata", doc.Metadata)
	return m
}

// resumeHandoverSection emits the last handover entry's payload verbatim: the note's own carrier,
// with no key invented and nothing dropped. Returns nil when the ledger holds no handover.
func resumeHandoverSection(event *entities.TaskEvent) any {
	if event == nil {
		return nil
	}
	return event.Payload
}

// resumeNextAction is the DETERMINISTIC ladder over the facts, most recent blocking fact first: a
// REJECT verdict, then a failing evidence run, then open subtasks, then blocking dependencies, then
// no evidence at all, then continue. It reads nothing but its arguments.
func resumeNextAction(verdict, evidence *entities.TaskEvent, openSubtasks int, blockers []string) string {
	if verdict != nil && strings.ToLower(resumeString(verdict.Payload["verdict"])) == "reject" {
		return "fix: " + resumeOrFallback(resumeStrings(verdict.Payload["reasons"]), "rejected")
	}
	if evidence != nil && resumeEvidenceFailed(evidence) {
		return "fix: " + resumeOrFallback(resumeStrings(resumeTestBlock(evidence)["failed"]), "the test run failed")
	}
	if openSubtasks > 0 {
		return fmt.Sprintf("continue: %d open subtask(s)", openSubtasks)
	}
	if len(blockers) > 0 {
		return "blocked: " + strings.Join(blockers, ", ")
	}
	if evidence == nil {
		return "start: submit evidence with 4genteam evidence"
	}
	return "continue"
}

// resumeEvidenceFailed reports whether an evidence entry's test run failed: a non-zero exit code, a
// non-empty failed list, or both.
func resumeEvidenceFailed(event *entities.TaskEvent) bool {
	test := resumeTestBlock(event)
	if len(resumeStrings(test["failed"])) > 0 {
		return true
	}
	return resumeIntDefault(test["exit_code"], 0) != 0
}

// resumeTestBlock is the evidence entry's nested `test` object, or an empty map when absent.
func resumeTestBlock(event *entities.TaskEvent) map[string]any {
	if test, ok := event.Payload["test"].(map[string]any); ok {
		return test
	}
	return map[string]any{}
}

// resumeSubtaskCompleted mirrors Subtask.IsCompleted (done OR progress at 100) with a nil-status
// guard, so a subtask whose status was never set cannot take the process down.
func resumeSubtaskCompleted(subtask *entities.Subtask) bool {
	return subtask.ProgressPercentage >= 100 || (subtask.Status != nil && subtask.Status.IsCompleted())
}

// resumeSubtaskFacts is one open subtask as the brief names it: identity, title and stored status.
func resumeSubtaskFacts(subtask *entities.Subtask) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("id", resumeTaskIDString(subtask.ID))
	m.Set("title", subtask.Title)
	status := ""
	if subtask.Status != nil {
		status = subtask.Status.String()
	}
	m.Set("status", status)
	return m
}

// resumeNumstatFiles counts the touched files in a raw `git diff --numstat` text: its non-blank
// lines, one per changed file.
func resumeNumstatFiles(numstat string) int {
	count := 0
	for _, line := range strings.Split(numstat, "\n") {
		if strings.TrimSpace(line) != "" {
			count++
		}
	}
	return count
}

// resumeOrFallback joins items with "; ", or returns fallback when the list is empty.
func resumeOrFallback(items []string, fallback string) string {
	if len(items) == 0 {
		return fallback
	}
	return strings.Join(items, "; ")
}

// resumeTaskIDString is a possibly-nil task id as a string.
func resumeTaskIDString(id *value_objects.TaskId) string {
	if id == nil {
		return ""
	}
	return id.String()
}

// resumeString is a JSON-like value as a string; nil is empty.
func resumeString(v any) string {
	switch x := v.(type) {
	case nil:
		return ""
	case string:
		return x
	}
	return value_objects.PyStr(v)
}

// resumeStrings is a JSON-like value as a string list: a list ([]string or []any), a single string,
// or nil (empty list). It never returns nil, so a section serializes as [] rather than null.
func resumeStrings(v any) []string {
	switch x := v.(type) {
	case nil:
		return []string{}
	case []string:
		return append([]string{}, x...)
	case []any:
		out := make([]string, 0, len(x))
		for _, item := range x {
			out = append(out, resumeString(item))
		}
		return out
	case string:
		return []string{x}
	}
	return []string{resumeString(v)}
}

// resumeIntDefault is a JSON-like number as an int, or fallback when it is absent or not a number.
func resumeIntDefault(v any, fallback int) int {
	switch x := v.(type) {
	case int:
		return x
	case int8:
		return int(x)
	case int16:
		return int(x)
	case int32:
		return int(x)
	case int64:
		return int(x)
	case float32:
		return int(x)
	case float64:
		return int(x)
	}
	return fallback
}
