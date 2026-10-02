package services

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RuleContext is the context information for rule evaluation.
type RuleContext struct {
	Task               *entities.Task
	Context            *entities.TaskContext
	RelatedTasks       []*entities.Task
	HistoricalPatterns map[string]any
}

// NewRuleContext applies the Python defaults (empty related tasks / patterns).
func NewRuleContext(task *entities.Task, ctx *entities.TaskContext) RuleContext {
	return RuleContext{Task: task, Context: ctx, RelatedTasks: []*entities.Task{}, HistoricalPatterns: map[string]any{}}
}

// HintRule generates a hint when applicable; Evaluate returns (nil, nil) when it does not.
type HintRule interface {
	Evaluate(rc RuleContext) (*value_objects.WorkflowHint, error)
	RuleName() string
}

// Python quirks preserved (verified against the real Task / TaskContext classes):
//   - Task has no `progress` / `progress_breakdown`, so the two rules that need them never fire.
//   - TaskContext.notes is a ContextNotes dataclass without `.get` (and TaskContext has no
//     `.data`), so any rule that reads the context raises AttributeError.
//   - Task.progress_timeline is a ProgressTimeline object that is not subscriptable.
var (
	errNotesGet         = errors.New("'ContextNotes' object has no attribute 'get'")
	errTimelineNotSubsc = errors.New("'ProgressTimeline' object is not subscriptable")
)

func newHint(task *entities.Task, ht value_objects.HintType, p value_objects.HintPriority, message, action string,
	source string, confidence float64, reasoning string, patterns []string, contextData map[string]any) *value_objects.WorkflowHint {
	md, _ := value_objects.NewHintMetadata(source, confidence, reasoning, []string{}, patterns, nil)
	h := value_objects.CreateWorkflowHint(taskIDStr(task), ht, p, message, action, md, contextData, nil)
	return &h
}

// StalledProgressRule generates hints for stalled tasks.
type StalledProgressRule struct{ StallHours int }

func NewStalledProgressRule() StalledProgressRule { return StalledProgressRule{StallHours: 24} }

func (StalledProgressRule) RuleName() string { return "stalled_progress" }

// Evaluate: with no timeline there is no progress entry; with a ProgressTimeline object
// Python raises TypeError on `task.progress_timeline[-1]`.
func (StalledProgressRule) Evaluate(rc RuleContext) (*value_objects.WorkflowHint, error) {
	if rc.Task.ProgressTimeline == nil {
		return nil, nil
	}
	return nil, errTimelineNotSubsc
}

// stalledHint builds the hints the rule would emit for a stall of the given duration.
func (r StalledProgressRule) stalledHint(task *entities.Task, stall time.Duration) *value_objects.WorkflowHint {
	hours := int(value_objects.PyTotalSeconds(stall) / 3600)
	if lowerStatus(task) == "blocked" {
		p := value_objects.HintPriorityHigh
		if hours > 48 {
			p = value_objects.HintPriorityCritical
		}
		return newHint(task, value_objects.HintTypeBlockerResolution, p,
			fmt.Sprintf("Task has been blocked for %d hours", hours),
			"Review blockers and consider: 1) Escalating to team lead, 2) Finding alternative approaches, 3) Breaking down the blocker into smaller issues",
			r.RuleName(), 0.9, fmt.Sprintf("Task has been blocked for %d hours", hours), []string{"extended_blocker"},
			map[string]any{"hours_stalled": hours})
	}
	return newHint(task, value_objects.HintTypeNextAction, value_objects.HintPriorityHigh,
		fmt.Sprintf("No progress recorded for %d hours", hours),
		"Consider: 1) Updating task progress, 2) Marking as blocked if stuck, 3) Breaking down into smaller subtasks",
		r.RuleName(), 0.8, fmt.Sprintf("No progress recorded for %d hours", hours), []string{"progress_stall"},
		map[string]any{"hours_stalled": hours})
}

// ImplementationReadyForTestingRule never fires: Task has no progress_breakdown.
type ImplementationReadyForTestingRule struct{ ImplementationThreshold float64 }

func NewImplementationReadyForTestingRule() ImplementationReadyForTestingRule {
	return ImplementationReadyForTestingRule{ImplementationThreshold: 0.75}
}

func (ImplementationReadyForTestingRule) RuleName() string { return "implementation_ready_for_testing" }

func (ImplementationReadyForTestingRule) Evaluate(RuleContext) (*value_objects.WorkflowHint, error) {
	return nil, nil
}

// MissingContextRule generates hints for tasks with missing or incomplete context.
type MissingContextRule struct{}

func (MissingContextRule) RuleName() string { return "missing_context" }

func (r MissingContextRule) Evaluate(rc RuleContext) (*value_objects.WorkflowHint, error) {
	if rc.Context == nil {
		return newHint(rc.Task, value_objects.HintTypeNextAction, value_objects.HintPriorityHigh,
			"Task is missing context information",
			"Add context with task objectives, requirements, and initial notes",
			r.RuleName(), 0.95, "Task has no context information", []string{"missing_context"}, nil), nil
	}
	return nil, errNotesGet
}

// ComplexDependencyRule suggests breakdown for tasks with complex dependencies.
type ComplexDependencyRule struct{ ComplexityThreshold int }

func NewComplexDependencyRule() ComplexDependencyRule {
	return ComplexDependencyRule{ComplexityThreshold: 3}
}

func (ComplexDependencyRule) RuleName() string { return "complex_dependencies" }

func (r ComplexDependencyRule) Evaluate(rc RuleContext) (*value_objects.WorkflowHint, error) {
	n := len(rc.Task.Dependencies)
	if n < r.ComplexityThreshold || len(rc.Task.Subtasks) > 0 {
		return nil, nil
	}
	return newHint(rc.Task, value_objects.HintTypeOptimization, value_objects.HintPriorityMedium,
		fmt.Sprintf("Task has %d dependencies - consider decomposition", n),
		"Break down the task into smaller subtasks to manage dependencies more effectively",
		r.RuleName(), 0.8, fmt.Sprintf("Task has %d dependencies", n), []string{"high_complexity"},
		map[string]any{"dependency_count": n}), nil
}

// NearCompletionRule never fires: Task has no `progress` attribute.
type NearCompletionRule struct{ CompletionThreshold float64 }

func NewNearCompletionRule() NearCompletionRule { return NearCompletionRule{CompletionThreshold: 0.9} }

func (NearCompletionRule) RuleName() string { return "near_completion" }

func (NearCompletionRule) Evaluate(RuleContext) (*value_objects.WorkflowHint, error) { return nil, nil }

// CollaborationNeededRule suggests collaboration for tasks that would benefit from it.
// Python defects preserved: a present context raises (ContextNotes has no `.get`);
// Priority has no `label`, so str(priority) is used; Task has no `progress` (getattr
// default 0), so urgent/critical tasks always count as slow.
type CollaborationNeededRule struct{}

func (CollaborationNeededRule) RuleName() string { return "collaboration_needed" }

func (r CollaborationNeededRule) Evaluate(rc RuleContext) (*value_objects.WorkflowHint, error) {
	task := rc.Task
	indicators := []string{}
	if task.CreatedAt == nil {
		return nil, errors.New("unsupported operand type(s) for -: 'datetime.datetime' and 'NoneType'")
	}
	if status := statusStr(task); time.Since(*task.CreatedAt) > 7*24*time.Hour && status != "done" && status != "cancelled" {
		indicators = append(indicators, "long_running")
	}
	if rc.Context != nil {
		return nil, errNotesGet
	}
	if p := priorityStr(task); p == "urgent" || p == "critical" {
		indicators = append(indicators, "high_priority_slow_progress")
	}
	if len(indicators) == 0 {
		return nil, nil
	}
	return newHint(task, value_objects.HintTypeCollaboration, value_objects.HintPriorityMedium,
		"This task might benefit from collaboration",
		"Consider: 1) Pair programming session, 2) Design review with team, 3) Asking for help on specific blockers",
		r.RuleName(), 0.75, "Collaboration indicators: "+strings.Join(indicators, ", "), indicators,
		map[string]any{"indicators": indicators}), nil
}
