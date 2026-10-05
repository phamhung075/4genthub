package services

// WorkflowAnalysisService ports
// task_management/application/services/workflow_analysis_service.py.
//
// Porting notes (Python quirks preserved, verified against the real Task /
// TaskContext classes):
//   - TaskStatus and Priority are frozen dataclasses, so `status == "done"`,
//     `status in [...]` and `priority in [...]` are always False against str
//     literals. Those branches never fire (see wfTaskStatusEqualsString and
//     friends).
//   - Task has no `parent_id`, `progress_breakdown` or `progress`, so the
//     parent branch is skipped, the progress-breakdown pattern never fires and
//     `getattr(task, "progress", 0)` is always 0.
//   - TaskContext has no `.data`, so any analysis that reads it raises
//     AttributeError; `progress_timeline` is a ProgressTimeline object that is
//     neither sized nor subscriptable.
//   - `_get_user_scoped_repository` has no reachable branch for the Go
//     repository interfaces (no with_user/user_id/session members).
// Repository mapping: Python `.get(id)` -> FindByID; Python `.list(labels, limit)`
// -> FindByLabels (the Go interface has no limit argument); Python
// `get_by_task_id(id)` -> GetContext.

import (
	"context"
	"errors"
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// WorkflowPattern represents a detected workflow pattern (Python dataclass).
type WorkflowPattern struct {
	PatternName     string
	PatternType     string // bottleneck, optimization, success_pattern
	Confidence      float64
	Description     string
	AffectedTasks   []value_objects.TaskId
	Recommendations []string
	Metrics         *entities.OrderedMap[any]
}

// WorkflowAnalysis is the result of a workflow analysis (Python dataclass).
type WorkflowAnalysis struct {
	TaskID                    value_objects.TaskId
	AnalysisTimestamp         time.Time
	Patterns                  []WorkflowPattern
	Bottlenecks               []*entities.OrderedMap[any]
	OptimizationOpportunities []*entities.OrderedMap[any]
	PredictedCompletionTime   *time.Duration
	RiskFactors               []string
	SuccessIndicators         []string
}

// Python exceptions that this module can raise, reproduced with their exact text.
var (
	errWfContextNoData   = errors.New("'TaskContext' object has no attribute 'data'")
	errWfTimelineNoLen   = errors.New("object of type 'ProgressTimeline' has no len()")
	errWfNoneNoLen       = errors.New("object of type 'NoneType' has no len()")
	errWfTimelineNotSub  = errors.New("'ProgressTimeline' object is not subscriptable")
	errWfDatetimeNoneSub = errors.New("unsupported operand type(s) for -: 'datetime.datetime' and 'NoneType'")
)

// zpWfAnalysisUserScoped is the optional `with_user` capability of Python
// repositories. No Go repository in this package implements it.
type zpWfAnalysisUserScoped interface {
	WithUser(userID string) any
}

// WorkflowAnalysisService analyzes workflow patterns and provides insights.
type WorkflowAnalysisService struct {
	taskRepository    repositories.TaskRepository
	contextRepository repositories.ContextRepository
	eventStore        any
	userID            *string

	// analysisCache / patternCache mirror _analysis_cache / _pattern_cache.
	analysisCache map[value_objects.TaskId]WorkflowAnalysis
	patternCache  map[string]WorkflowPattern
}

// NewWorkflowAnalysisService mirrors __init__; userID nil is Python None.
func NewWorkflowAnalysisService(taskRepository repositories.TaskRepository, contextRepository repositories.ContextRepository, eventStore any, userID *string) *WorkflowAnalysisService {
	return &WorkflowAnalysisService{
		taskRepository: taskRepository, contextRepository: contextRepository, eventStore: eventStore, userID: userID,
		analysisCache: map[value_objects.TaskId]WorkflowAnalysis{}, patternCache: map[string]WorkflowPattern{},
	}
}

// WithUser mirrors with_user(user_id): a new service sharing the repositories.
func (s *WorkflowAnalysisService) WithUser(userID string) *WorkflowAnalysisService {
	return NewWorkflowAnalysisService(s.taskRepository, s.contextRepository, s.eventStore, &userID)
}

// getUserScopedRepository mirrors _get_user_scoped_repository. Only the
// `with_user` branch is representable; the `user_id`/`session` reconstruction
// branch has no Go analog, so the repository is returned unchanged otherwise.
func (s *WorkflowAnalysisService) getUserScopedRepository(repository any) any {
	if repository == nil {
		return nil
	}
	if s.userID != nil && *s.userID != "" {
		if scoped, ok := repository.(zpWfAnalysisUserScoped); ok {
			return scoped.WithUser(*s.userID)
		}
	}
	return repository
}

// wfTaskStatusEqualsString mirrors Python `task_status == "literal"`. TaskStatus
// is a frozen dataclass (not a str subclass), so dataclass __eq__ returns
// NotImplemented for a str and the comparison is always False.
func wfTaskStatusEqualsString(_ *value_objects.TaskStatus, _ string) bool { return false }

// wfTaskStatusInStrings mirrors Python `task_status in ["a", "b"]`, always False.
func wfTaskStatusInStrings(_ *value_objects.TaskStatus, _ []string) bool { return false }

// wfPriorityInStrings mirrors Python `priority in ["urgent", "critical"]`, always False.
func wfPriorityInStrings(_ *value_objects.Priority, _ []string) bool { return false }

// wfContextNotesText reproduces `str(context.notes)` for the ContextNotes
// dataclass, used for the keyword searches in collaboration/automation checks.
func wfContextNotesText(n entities.ContextNotes) string {
	return "ContextNotes(agent_insights=" + wfContextInsightsText(n.AgentInsights) +
		", challenges_encountered=" + wfContextInsightsText(n.ChallengesEncountered) +
		", solutions_applied=" + wfContextInsightsText(n.SolutionsApplied) +
		", decisions_made=" + wfContextInsightsText(n.DecisionsMade) +
		", general_notes=" + value_objects.PyRepr(n.GeneralNotes) + ")"
}

func wfContextInsightsText(items []entities.ContextInsight) string {
	parts := make([]string, len(items))
	for i, it := range items {
		parts[i] = "ContextInsight(timestamp=" + value_objects.PyRepr(it.Timestamp) +
			", agent=" + value_objects.PyRepr(it.Agent) +
			", category=" + value_objects.PyRepr(it.Category) +
			", content=" + value_objects.PyRepr(it.Content) +
			", importance=" + value_objects.PyRepr(it.Importance) + ")"
	}
	return "[" + strings.Join(parts, ", ") + "]"
}

func wfTaskIDKey(t *entities.Task) string {
	if t == nil || t.ID == nil {
		return ""
	}
	return t.ID.String()
}

func wfOMString(om *entities.OrderedMap[any], key string) string {
	if v, ok := om.Get(key); ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return ""
}

func wfOMFloat(om *entities.OrderedMap[any], key string) float64 {
	if v, ok := om.Get(key); ok {
		if f, ok := value_objects.PyFloat(v); ok {
			return f
		}
	}
	return 0
}

func wfOMStrings(om *entities.OrderedMap[any], key string) []string {
	v, ok := om.Get(key)
	if !ok {
		return []string{}
	}
	switch l := v.(type) {
	case []string:
		return l
	case []any:
		out := []string{}
		for _, e := range l {
			if s, ok := e.(string); ok {
				out = append(out, s)
			}
		}
		return out
	}
	return []string{}
}

// AnalyzeTaskWorkflow performs the comprehensive workflow analysis.
func (s *WorkflowAnalysisService) AnalyzeTaskWorkflow(ctx context.Context, taskID value_objects.TaskId, includeRelated bool) (*WorkflowAnalysis, error) {
	// Check cache
	if cached, ok := s.analysisCache[taskID]; ok {
		if time.Now().UTC().Sub(cached.AnalysisTimestamp) < time.Hour {
			c := cached
			return &c, nil
		}
	}

	if s.taskRepository == nil {
		return nil, errors.New("'NoneType' object has no attribute 'get'")
	}
	task, err := s.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, fmt.Errorf("Task not found: %s", taskID.String())
	}

	taskContext, err := s.getTaskContext(ctx, taskID)
	if err != nil {
		return nil, err
	}

	relatedTasks := []*entities.Task{}
	if includeRelated {
		if relatedTasks, err = s.getRelatedTasks(ctx, task); err != nil {
			return nil, err
		}
	}

	patterns, err := s.detectPatterns(task, taskContext, relatedTasks)
	if err != nil {
		return nil, err
	}
	bottlenecks, err := s.identifyBottlenecks(ctx, task, taskContext)
	if err != nil {
		return nil, err
	}
	optimizations, err := s.findOptimizationOpportunities(task, taskContext, patterns)
	if err != nil {
		return nil, err
	}
	completionTime, err := s.predictCompletionTime(task, relatedTasks)
	if err != nil {
		return nil, err
	}
	riskFactors, err := s.assessRiskFactors(task, taskContext, patterns)
	if err != nil {
		return nil, err
	}
	successIndicators, err := s.identifySuccessIndicators(task, taskContext)
	if err != nil {
		return nil, err
	}

	analysis := WorkflowAnalysis{
		TaskID: taskID, AnalysisTimestamp: time.Now().UTC(), Patterns: patterns, Bottlenecks: bottlenecks,
		OptimizationOpportunities: optimizations, PredictedCompletionTime: completionTime,
		RiskFactors: riskFactors, SuccessIndicators: successIndicators,
	}
	s.analysisCache[taskID] = analysis
	return &analysis, nil
}

// getTaskContext mirrors _get_task_context: any exception becomes None, so a nil
// repository or a repository error also yields (nil, nil).
func (s *WorkflowAnalysisService) getTaskContext(ctx context.Context, taskID value_objects.TaskId) (c *entities.TaskContext, err error) {
	if s.contextRepository == nil {
		return nil, nil
	}
	defer func() {
		if recover() != nil {
			c, err = nil, nil
		}
	}()
	c, err = s.contextRepository.GetContext(ctx, taskID.String())
	if err != nil {
		return nil, nil
	}
	return c, nil
}

// GetRelatedTasks mirrors _get_related_tasks.
func (s *WorkflowAnalysisService) getRelatedTasks(ctx context.Context, task *entities.Task) ([]*entities.Task, error) {
	related := []*entities.Task{}

	// Similar labels (first two). Python passes limit=20; the Go interface has none.
	if len(task.Labels) > 0 {
		labels := task.Labels
		if len(labels) > 2 {
			labels = labels[:2]
		}
		for _, label := range labels {
			tasks, err := s.taskRepository.FindByLabels(ctx, []string{label})
			if err != nil {
				return nil, err
			}
			related = append(related, tasks...)
		}
	}

	// hasattr(task, "parent_id") is False for the Python Task entity; the Go
	// Task has no ParentID field either, so the parent branch is skipped.

	if len(task.Subtasks) > 0 {
		for _, subID := range task.Subtasks {
			subtaskID, err := value_objects.NewTaskId(subID)
			if err != nil {
				return nil, err
			}
			subtask, err := s.taskRepository.FindByID(ctx, subtaskID)
			if err != nil {
				return nil, err
			}
			if subtask != nil {
				related = append(related, subtask)
			}
		}
	}

	seen := map[string]bool{}
	unique := []*entities.Task{}
	target := wfTaskIDKey(task)
	for _, t := range related {
		k := wfTaskIDKey(t)
		if !seen[k] && k != target {
			seen[k] = true
			unique = append(unique, t)
		}
	}
	return unique, nil
}

// DetectPatterns mirrors _detect_patterns.
func (s *WorkflowAnalysisService) detectPatterns(task *entities.Task, taskContext *entities.TaskContext, relatedTasks []*entities.Task) ([]WorkflowPattern, error) {
	patterns := []WorkflowPattern{}
	patterns = append(patterns, s.detectCompletionPatterns(task, relatedTasks)...)
	patterns = append(patterns, s.detectBlockerPatterns(task, relatedTasks)...)
	collab, err := s.detectCollaborationPatterns(task, taskContext)
	if err != nil {
		return nil, err
	}
	patterns = append(patterns, collab...)
	patterns = append(patterns, s.detectProgressPatterns(task)...)
	return patterns, nil
}

// detectCompletionPatterns mirrors _detect_completion_patterns. The
// `status == "done"` filter is always False, so the branch below never fires.
func (s *WorkflowAnalysisService) detectCompletionPatterns(task *entities.Task, relatedTasks []*entities.Task) []WorkflowPattern {
	patterns := []WorkflowPattern{}
	completedSimilar := []*entities.Task{}
	for _, t := range relatedTasks {
		if wfTaskStatusEqualsString(t.Status, "done") && t.CreatedAt != nil && t.UpdatedAt != nil {
			completedSimilar = append(completedSimilar, t)
		}
	}
	if len(completedSimilar) >= 3 {
		completionTimes := []float64{}
		for _, t := range completedSimilar {
			completionTimes = append(completionTimes, value_objects.PyTotalSeconds(t.UpdatedAt.Sub(*t.CreatedAt))/3600)
		}
		avgTime := value_objects.PySum(completionTimes) / float64(len(completionTimes))
		if task.CreatedAt != nil {
			currentDuration := value_objects.PyTotalSeconds(time.Now().UTC().Sub(*task.CreatedAt)) / 3600
			if currentDuration > avgTime*1.5 {
				metrics := entities.NewOrderedMap[any]()
				metrics.Set("current_duration_hours", currentDuration)
				metrics.Set("average_duration_hours", avgTime)
				metrics.Set("sample_size", len(completedSimilar))
				affected := []value_objects.TaskId{}
				if task.ID != nil {
					affected = append(affected, *task.ID)
				}
				patterns = append(patterns, WorkflowPattern{
					PatternName: "extended_duration", PatternType: "bottleneck", Confidence: 0.8,
					Description:   fmt.Sprintf("Task is taking %.1fh vs avg %.1fh", currentDuration, avgTime),
					AffectedTasks: affected,
					Recommendations: []string{
						"Review task scope for unnecessary complexity",
						"Consider breaking down into smaller tasks",
						"Check for hidden blockers or dependencies",
					},
					Metrics: metrics,
				})
			}
		}
	}
	return patterns
}

// detectBlockerPatterns mirrors _detect_blocker_patterns. The `status ==
// "blocked"` filter is always False, so blockedCount is always 0.
func (s *WorkflowAnalysisService) detectBlockerPatterns(task *entities.Task, relatedTasks []*entities.Task) []WorkflowPattern {
	patterns := []WorkflowPattern{}
	blockedCount := 0
	for _, t := range relatedTasks {
		if wfTaskStatusEqualsString(t.Status, "blocked") {
			blockedCount++
		}
	}
	totalCount := len(relatedTasks)
	if totalCount > 5 && float64(blockedCount)/float64(totalCount) > 0.3 {
		affected := []value_objects.TaskId{}
		for _, t := range relatedTasks {
			if wfTaskStatusEqualsString(t.Status, "blocked") && t.ID != nil {
				affected = append(affected, *t.ID)
			}
		}
		metrics := entities.NewOrderedMap[any]()
		metrics.Set("blocked_count", blockedCount)
		metrics.Set("total_count", totalCount)
		metrics.Set("blocker_rate", float64(blockedCount)/float64(totalCount))
		patterns = append(patterns, WorkflowPattern{
			PatternName: "high_blocker_rate", PatternType: "bottleneck", Confidence: 0.85,
			Description:   fmt.Sprintf("%d/%d related tasks are blocked", blockedCount, totalCount),
			AffectedTasks: affected,
			Recommendations: []string{
				"Investigate common blocker themes",
				"Schedule team discussion on blockers",
				"Consider process improvements",
			},
			Metrics: metrics,
		})
	}
	return patterns
}

// detectCollaborationPatterns mirrors _detect_collaboration_patterns.
func (s *WorkflowAnalysisService) detectCollaborationPatterns(task *entities.Task, taskContext *entities.TaskContext) ([]WorkflowPattern, error) {
	patterns := []WorkflowPattern{}
	indicators := []string{}

	if task.CreatedAt == nil {
		return nil, errWfDatetimeNoneSub
	}
	age := time.Now().UTC().Sub(*task.CreatedAt)
	if age > 14*24*time.Hour && !wfTaskStatusInStrings(task.Status, []string{"done", "cancelled"}) {
		indicators = append(indicators, "long_running")
	}

	if len(task.Assignees) > 2 {
		indicators = append(indicators, "multiple_assignees")
	}

	// `context.notes` is always truthy (a dataclass), so this is `context is not None`.
	if taskContext != nil {
		collabKeywords := []string{"help", "stuck", "blocked", "review", "discuss"}
		notesText := value_objects.PyLower(wfContextNotesText(taskContext.Notes))
		for _, keyword := range collabKeywords {
			if strings.Contains(notesText, keyword) {
				indicators = append(indicators, "collaboration_keywords")
				break
			}
		}
	}

	if len(indicators) >= 2 {
		metrics := entities.NewOrderedMap[any]()
		metrics.Set("indicators", indicators)
		metrics.Set("indicator_count", len(indicators))
		affected := []value_objects.TaskId{}
		if task.ID != nil {
			affected = append(affected, *task.ID)
		}
		patterns = append(patterns, WorkflowPattern{
			PatternName: "collaboration_opportunity", PatternType: "optimization", Confidence: 0.75,
			Description:   "Multiple indicators suggest collaboration would help",
			AffectedTasks: affected,
			Recommendations: []string{
				"Schedule pair programming session",
				"Request code review",
				"Organize team discussion",
			},
			Metrics: metrics,
		})
	}
	return patterns, nil
}

// detectProgressPatterns mirrors _detect_progress_patterns. hasattr(task,
// "progress_breakdown") is False (the Task entity has no such field), so it
// always returns an empty list.
func (s *WorkflowAnalysisService) detectProgressPatterns(*entities.Task) []WorkflowPattern {
	return []WorkflowPattern{}
}

// IdentifyBottlenecks mirrors _identify_bottlenecks.
func (s *WorkflowAnalysisService) identifyBottlenecks(ctx context.Context, task *entities.Task, taskContext *entities.TaskContext) ([]*entities.OrderedMap[any], error) {
	bottlenecks := []*entities.OrderedMap[any]{}

	// `progress_timeline[-1]` raises TypeError as soon as the timeline is not
	// None, so the progress-stall bottleneck is unreachable.
	if task.ProgressTimeline != nil {
		return nil, errWfTimelineNotSub
	}

	if len(task.Dependencies) > 3 {
		blockedDeps := []value_objects.TaskId{}
		for _, depID := range task.Dependencies {
			depTask, err := s.taskRepository.FindByID(ctx, depID)
			if err != nil {
				return nil, err
			}
			// `dep_task.status in ["blocked", "cancelled"]` is always False.
			if depTask != nil && wfTaskStatusInStrings(depTask.Status, []string{"blocked", "cancelled"}) {
				blockedDeps = append(blockedDeps, depID)
			}
		}
		if len(blockedDeps) > 0 {
			om := entities.NewOrderedMap[any]()
			om.Set("type", "dependency_blocked")
			om.Set("severity", "critical")
			om.Set("description", fmt.Sprintf("%d dependencies are blocked", len(blockedDeps)))
			om.Set("impact", "Cannot proceed until resolved")
			om.Set("suggestions", []string{
				"Escalate blocked dependencies",
				"Find alternative approaches",
				"Re-evaluate dependency necessity",
			})
			bottlenecks = append(bottlenecks, om)
		}
	}
	return bottlenecks, nil
}

// FindOptimizationOpportunities mirrors _find_optimization_opportunities.
func (s *WorkflowAnalysisService) findOptimizationOpportunities(task *entities.Task, taskContext *entities.TaskContext, _ []WorkflowPattern) ([]*entities.OrderedMap[any], error) {
	opportunities := []*entities.OrderedMap[any]{}

	if len(task.Subtasks) == 0 {
		effortStr := task.EstimatedEffort
		if effortStr != "" && (strings.HasSuffix(effortStr, "d") || strings.HasSuffix(effortStr, "h")) {
			raw := effortStr[:len(effortStr)-1]
			effortValue, err := strconv.Atoi(raw)
			if err != nil {
				return nil, value_objects.ValueErrorf("invalid literal for int() with base 10: %s", value_objects.PyRepr(raw))
			}
			effortUnit := effortStr[len(effortStr)-1:]
			if (effortUnit == "d" && effortValue > 3) || (effortUnit == "h" && effortValue > 24) {
				om := entities.NewOrderedMap[any]()
				om.Set("type", "task_decomposition")
				om.Set("potential_impact", "high")
				om.Set("description", "Large task could benefit from breakdown")
				om.Set("benefits", []string{"Better progress tracking", "Easier to parallelize work", "Reduced cognitive load"})
				om.Set("implementation", []string{"Identify logical components", "Create subtasks for each component", "Define clear interfaces between subtasks"})
				opportunities = append(opportunities, om)
			}
		}
	}

	// `context.notes` is always truthy (a dataclass), so this is `context is not None`.
	if taskContext != nil {
		automationKeywords := []string{"manual", "repetitive", "every time", "copy", "paste"}
		notesText := value_objects.PyLower(wfContextNotesText(taskContext.Notes))
		for _, keyword := range automationKeywords {
			if strings.Contains(notesText, keyword) {
				om := entities.NewOrderedMap[any]()
				om.Set("type", "automation")
				om.Set("potential_impact", "medium")
				om.Set("description", "Task involves repetitive manual work")
				om.Set("benefits", []string{"Reduced time investment", "Fewer errors", "Consistent results"})
				om.Set("implementation", []string{"Identify repetitive steps", "Create scripts or tools", "Document automation process"})
				opportunities = append(opportunities, om)
				break
			}
		}
	}
	return opportunities, nil
}

// PredictCompletionTime mirrors _predict_completion_time. The `status == "done"`
// filters are always False, so it always returns None.
func (s *WorkflowAnalysisService) predictCompletionTime(task *entities.Task, relatedTasks []*entities.Task) (*time.Duration, error) {
	if task.CreatedAt == nil {
		return nil, nil
	}

	completedSimilar := []*entities.Task{}
	for _, t := range relatedTasks {
		if wfTaskStatusEqualsString(t.Status, "done") && t.CreatedAt != nil && t.UpdatedAt != nil && t.EstimatedEffort == task.EstimatedEffort {
			completedSimilar = append(completedSimilar, t)
		}
	}
	if len(completedSimilar) == 0 {
		for _, t := range relatedTasks {
			if wfTaskStatusEqualsString(t.Status, "done") && t.CreatedAt != nil && t.UpdatedAt != nil {
				completedSimilar = append(completedSimilar, t)
			}
		}
	}
	if len(completedSimilar) == 0 {
		return nil, nil
	}

	completionTimes := []float64{}
	for _, t := range completedSimilar {
		completionTimes = append(completionTimes, value_objects.PyTotalSeconds(t.UpdatedAt.Sub(*t.CreatedAt)))
	}
	avgCompletion := value_objects.PySum(completionTimes) / float64(len(completionTimes))

	// getattr(task, "progress", 0): the Task entity has no `progress` attribute.
	progress := 0.0
	currentDuration := time.Now().UTC().Sub(*task.CreatedAt)

	finalEstimate := avgCompletion
	if progress > 0 {
		estimatedTotal := value_objects.PyTotalSeconds(currentDuration) / progress
		finalEstimate = avgCompletion*0.6 + estimatedTotal*0.4
	}
	remaining := finalEstimate - value_objects.PyTotalSeconds(currentDuration)
	if remaining > 0 {
		d := time.Duration(math.Round(remaining*1e6)) * time.Microsecond
		return &d, nil
	}
	zero := time.Duration(0)
	return &zero, nil
}

// AssessRiskFactors mirrors _assess_risk_factors. A non-nil context raises the
// AttributeError on `context.data`.
func (s *WorkflowAnalysisService) assessRiskFactors(task *entities.Task, taskContext *entities.TaskContext, patterns []WorkflowPattern) ([]string, error) {
	risks := []string{}

	// `task.priority in ["urgent", "critical"]` is always False.
	if wfPriorityInStrings(task.Priority, []string{"urgent", "critical"}) && 0 < 0.3 {
		risks = append(risks, "High priority task with low progress")
	}

	bottleneckPatterns := []WorkflowPattern{}
	for _, p := range patterns {
		if p.PatternType == "bottleneck" {
			bottleneckPatterns = append(bottleneckPatterns, p)
		}
	}
	if len(bottleneckPatterns) > 0 {
		risks = append(risks, fmt.Sprintf("%d bottleneck patterns detected", len(bottleneckPatterns)))
	}

	if taskContext == nil {
		risks = append(risks, "Limited context information available")
	} else {
		return nil, errWfContextNoData
	}

	if len(task.Assignees) == 0 {
		risks = append(risks, "No assignees on task")
	}
	if len(task.Dependencies) > 5 {
		risks = append(risks, "High number of dependencies")
	}
	return risks, nil
}

// IdentifySuccessIndicators mirrors _identify_success_indicators. `hasattr(task,
// "progress_timeline")` is True, so `len(task.progress_timeline)` raises a
// TypeError before any other check: None has no len, a ProgressTimeline has no
// len. The remaining Python lines are therefore unreachable.
func (s *WorkflowAnalysisService) identifySuccessIndicators(task *entities.Task, _ *entities.TaskContext) ([]string, error) {
	if task.ProgressTimeline == nil {
		return nil, errWfNoneNoLen
	}
	return nil, errWfTimelineNoLen
}

// GetWorkflowRecommendations mirrors get_workflow_recommendations.
func (s *WorkflowAnalysisService) GetWorkflowRecommendations(ctx context.Context, taskID value_objects.TaskId) ([]*entities.OrderedMap[any], error) {
	analysis, err := s.AnalyzeTaskWorkflow(ctx, taskID, true)
	if err != nil {
		return nil, err
	}

	recommendations := []*entities.OrderedMap[any]{}

	for _, pattern := range analysis.Patterns {
		for _, rec := range pattern.Recommendations {
			om := entities.NewOrderedMap[any]()
			om.Set("source", pattern.PatternName)
			if pattern.Confidence > 0.8 {
				om.Set("priority", "high")
			} else {
				om.Set("priority", "medium")
			}
			om.Set("recommendation", rec)
			om.Set("confidence", pattern.Confidence)
			recommendations = append(recommendations, om)
		}
	}

	for _, bottleneck := range analysis.Bottlenecks {
		for _, suggestion := range wfOMStrings(bottleneck, "suggestions") {
			om := entities.NewOrderedMap[any]()
			om.Set("source", "bottleneck_"+wfOMString(bottleneck, "type"))
			om.Set("priority", wfOMString(bottleneck, "severity"))
			om.Set("recommendation", suggestion)
			om.Set("confidence", 0.9)
			recommendations = append(recommendations, om)
		}
	}

	for _, opportunity := range analysis.OptimizationOpportunities {
		impactPriority := map[string]string{"high": "high", "medium": "medium", "low": "low"}
		priority, ok := impactPriority[wfOMString(opportunity, "potential_impact")]
		if !ok {
			priority = "medium"
		}
		om := entities.NewOrderedMap[any]()
		om.Set("source", "optimization_"+wfOMString(opportunity, "type"))
		om.Set("priority", priority)
		om.Set("recommendation", wfOMString(opportunity, "description"))
		om.Set("confidence", 0.85)
		om.Set("implementation_steps", wfOMStrings(opportunity, "implementation"))
		recommendations = append(recommendations, om)
	}

	priorityOrder := map[string]int{"critical": 0, "high": 1, "medium": 2, "low": 3}
	sort.SliceStable(recommendations, func(i, j int) bool {
		pi, ok := priorityOrder[wfOMString(recommendations[i], "priority")]
		if !ok {
			pi = 2
		}
		pj, ok := priorityOrder[wfOMString(recommendations[j], "priority")]
		if !ok {
			pj = 2
		}
		if pi != pj {
			return pi < pj
		}
		return wfOMFloat(recommendations[i], "confidence") > wfOMFloat(recommendations[j], "confidence")
	})

	if len(recommendations) > 10 {
		recommendations = recommendations[:10]
	}
	return recommendations, nil
}
