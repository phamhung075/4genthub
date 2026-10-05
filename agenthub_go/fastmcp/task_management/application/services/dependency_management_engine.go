package services

import (
	"context"
	"math"
	"regexp"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SuggestionType ports dependency_management_engine.SuggestionType.
type SuggestionType string

const (
	SuggestionTypeContent  SuggestionType = "content"
	SuggestionTypePattern  SuggestionType = "pattern"
	SuggestionTypeSemantic SuggestionType = "semantic"
	SuggestionTypeResource SuggestionType = "resource"
	SuggestionTypeTemporal SuggestionType = "temporal"
)

// SuggestionStatus ports dependency_management_engine.SuggestionStatus.
type SuggestionStatus string

const (
	SuggestionStatusPending     SuggestionStatus = "pending"
	SuggestionStatusAccepted    SuggestionStatus = "accepted"
	SuggestionStatusRejected    SuggestionStatus = "rejected"
	SuggestionStatusAutoApplied SuggestionStatus = "auto_applied"
)

// DependencyHint ports dependency_management_engine.DependencyHint.
type DependencyHint struct {
	TaskID                string
	SuggestedDependencyID string
	ConfidenceScore       float64
	SuggestionReason      string
	SuggestionType        SuggestionType
	Evidence              *entities.OrderedMap[any]
}

// NewDependencyHint mirrors __post_init__ validation (confidence in [0,1]).
func NewDependencyHint(h DependencyHint) (*DependencyHint, error) {
	if h.ConfidenceScore < 0.0 || h.ConfidenceScore > 1.0 {
		return nil, value_objects.ValueErrorf("Confidence score must be between 0 and 1, got %s", value_objects.PyStr(h.ConfidenceScore))
	}
	if h.Evidence == nil {
		h.Evidence = entities.NewOrderedMap[any]()
	}
	return &h, nil
}

// DependencySuggestion ports dependency_management_engine.DependencySuggestion.
type DependencySuggestion struct {
	Hint           *DependencyHint
	TargetTaskInfo *task.DependencyInfo
	Status         SuggestionStatus
	CreatedAt      time.Time
	UpdatedAt      time.Time
}

// NewDependencySuggestion builds a suggestion with the Python default status and timestamps.
func NewDependencySuggestion(hint *DependencyHint) *DependencySuggestion {
	now := time.Now().UTC()
	return &DependencySuggestion{Hint: hint, Status: SuggestionStatusPending, CreatedAt: now, UpdatedAt: now}
}

// EnhancedDependencyRelationships ports dependency_management_engine.EnhancedDependencyRelationships.
type EnhancedDependencyRelationships struct {
	BasicRelationships *task.DependencyRelationships
	AISuggestions      []*DependencySuggestion
	SuggestionSummary  string
	OptimizationScore  float64
	PerformanceMetrics *entities.OrderedMap[any]
}

// depKeywordScore holds the ordered DEPENDENCY_KEYWORDS entries.
type depKeywordScore struct {
	Keyword string
	Score   float64
}

// ContentAnalyzer ports dependency_management_engine.ContentAnalyzer.
type ContentAnalyzer struct {
	taskRepository     repositories.TaskRepository
	dependencyKeywords []depKeywordScore
}

// NewContentAnalyzer builds the analyzer with the ordered keyword table.
func NewContentAnalyzer(taskRepository repositories.TaskRepository) *ContentAnalyzer {
	return &ContentAnalyzer{
		taskRepository: taskRepository,
		dependencyKeywords: []depKeywordScore{
			{"before", 1.0},
			{"after", 1.0},
			{"requires", 0.9},
			{"depends on", 0.9},
			{"needs", 0.8},
			{"blocks", 1.0},
			{"blocked by", 1.0},
			{"prerequisite", 0.9},
			{"follows", 0.8},
			{"precedes", 0.8},
			{"implements", 0.7},
			{"uses", 0.6},
			{"extends", 0.7},
			{"inherits from", 0.8},
			{"based on", 0.6},
		},
	}
}

// AnalyzeTaskContent ports analyze_task_content. The Python Task entity has no
// `details` attribute, so _extract_text_content raises AttributeError; that is
// caught here and no hint is ever produced (bug preserved).
func (a *ContentAnalyzer) AnalyzeTaskContent(ctx context.Context, t *entities.Task) []*DependencyHint {
	hints := []*DependencyHint{}

	contentText, err := a.extractTextContent(t)
	if err != nil {
		return hints
	}

	allTasks := a.getAllTasksForAnalysis(ctx, t)
	hints = append(hints, a.analyzeDependencyKeywords(t, contentText, allTasks)...)
	hints = append(hints, a.analyzeFileDependencies(t, contentText, allTasks)...)
	hints = append(hints, a.analyzeAgentDependencies(t, allTasks)...)
	return hints
}

// extractTextContent ports _extract_text_content. Python accesses task.details,
// which raises AttributeError on the Task entity.
func (a *ContentAnalyzer) extractTextContent(t *entities.Task) (string, error) {
	_ = t
	return "", valueErrorNoDetails
}

var valueErrorNoDetails = value_objects.ValueErrorf("'Task' object has no attribute 'details'")

// getAllTasksForAnalysis ports _get_all_tasks_for_analysis.
func (a *ContentAnalyzer) getAllTasksForAnalysis(ctx context.Context, currentTask *entities.Task) []*entities.Task {
	allTasks, err := a.taskRepository.FindAll(ctx)
	if err != nil {
		return []*entities.Task{}
	}
	filtered := []*entities.Task{}
	currentID := ""
	if currentTask.ID != nil {
		currentID = currentTask.ID.Value
	}
	for _, t := range allTasks {
		if t.ID != nil && t.ID.Value != currentID {
			filtered = append(filtered, t)
		}
	}
	return filtered
}

// analyzeDependencyKeywords ports _analyze_dependency_keywords.
func (a *ContentAnalyzer) analyzeDependencyKeywords(t *entities.Task, contentText string, allTasks []*entities.Task) []*DependencyHint {
	hints := []*DependencyHint{}

	for _, kw := range a.dependencyKeywords {
		if !strings.Contains(contentText, kw.Keyword) {
			continue
		}
		for _, otherTask := range allTasks {
			otherTitleLower := strings.ToLower(otherTask.Title)
			if !strings.Contains(contentText, otherTitleLower) {
				continue
			}
			keywordPos := strings.Index(contentText, kw.Keyword)
			titlePos := strings.Index(contentText, otherTitleLower)
			diff := keywordPos - titlePos
			if diff < 0 {
				diff = -diff
			}
			if diff >= 100 {
				continue
			}
			proximityScore := math.Max(0.5, 1.0-float64(diff)/100)
			confidence := kw.Score * proximityScore
			evidence := entities.NewOrderedMap[any]()
			evidence.Set("keyword", kw.Keyword)
			evidence.Set("proximity", diff)
			evidence.Set("base_score", kw.Score)
			evidence.Set("proximity_score", proximityScore)
			hint, _ := NewDependencyHint(DependencyHint{
				TaskID:                t.ID.Value,
				SuggestedDependencyID: otherTask.ID.Value,
				ConfidenceScore:       math.Min(confidence, 0.95),
				SuggestionReason:      "Found '" + kw.Keyword + "' near task '" + otherTask.Title + "' in content",
				SuggestionType:        SuggestionTypeContent,
				Evidence:              evidence,
			})
			hints = append(hints, hint)
		}
	}
	return hints
}

var depFilePatterns = []*regexp.Regexp{
	regexp.MustCompile(`[/\w\-\.]+\.(py|js|ts|tsx|jsx|java|cpp|h|sql|yaml|yml|json|xml|html|css)`),
	regexp.MustCompile(`src/[/\w\-\.]+`),
	regexp.MustCompile(`tests?/[/\w\-\.]+`),
	regexp.MustCompile(`docs?/[/\w\-\.]+`),
	regexp.MustCompile(`config/[/\w\-\.]+`),
}

// analyzeFileDependencies ports _analyze_file_dependencies.
func (a *ContentAnalyzer) analyzeFileDependencies(t *entities.Task, contentText string, allTasks []*entities.Task) []*DependencyHint {
	hints := []*DependencyHint{}

	foundFiles := &entities.StringSet{}
	for i, pattern := range depFilePatterns {
		if i == 0 {
			// Python re.findall returns the capturing group for this pattern.
			for _, m := range pattern.FindAllStringSubmatch(contentText, -1) {
				if len(m) > 1 {
					foundFiles.Add(m[1])
				}
			}
			continue
		}
		for _, m := range pattern.FindAllString(contentText, -1) {
			foundFiles.Add(m)
		}
	}

	if foundFiles.Len() == 0 {
		return hints
	}

	for _, otherTask := range allTasks {
		otherContent, err := a.extractTextContent(otherTask)
		if err != nil {
			return hints
		}
		commonFiles := []string{}
		for _, filePath := range foundFiles.Items() {
			if strings.Contains(otherContent, strings.ToLower(filePath)) {
				commonFiles = append(commonFiles, filePath)
			}
		}
		if len(commonFiles) == 0 {
			continue
		}
		confidence := math.Min(0.8, float64(len(commonFiles))*0.2)
		firstFiles := commonFiles
		if len(firstFiles) > 3 {
			firstFiles = firstFiles[:3]
		}
		evidence := entities.NewOrderedMap[any]()
		evidence.Set("shared_files", commonFiles)
		evidence.Set("file_count", len(commonFiles))
		hint, _ := NewDependencyHint(DependencyHint{
			TaskID:                t.ID.Value,
			SuggestedDependencyID: otherTask.ID.Value,
			ConfidenceScore:       confidence,
			SuggestionReason:      "Tasks share " + itoa(len(commonFiles)) + " file references: " + strings.Join(firstFiles, ", "),
			SuggestionType:        SuggestionTypeContent,
			Evidence:              evidence,
		})
		hints = append(hints, hint)
	}
	return hints
}

// analyzeAgentDependencies ports _analyze_agent_dependencies.
func (a *ContentAnalyzer) analyzeAgentDependencies(t *entities.Task, allTasks []*entities.Task) []*DependencyHint {
	hints := []*DependencyHint{}

	if len(t.Assignees) == 0 {
		return hints
	}

	taskAgents := &entities.StringSet{}
	for _, ag := range t.Assignees {
		taskAgents.Add(ag)
	}

	for _, otherTask := range allTasks {
		if len(otherTask.Assignees) == 0 {
			continue
		}
		otherAgents := &entities.StringSet{}
		for _, ag := range otherTask.Assignees {
			otherAgents.Add(ag)
		}
		sharedAgents := &entities.StringSet{}
		for _, ag := range taskAgents.Items() {
			if otherAgents.Has(ag) {
				sharedAgents.Add(ag)
			}
		}
		if sharedAgents.Len() == 0 {
			continue
		}

		confidence := math.Min(0.7, float64(sharedAgents.Len())*0.3)

		if otherTask.CreatedAt != nil && t.CreatedAt != nil && otherTask.CreatedAt.Before(*t.CreatedAt) {
			confidence += 0.1
		}

		union := &entities.StringSet{}
		for _, ag := range taskAgents.Items() {
			union.Add(ag)
		}
		for _, ag := range otherAgents.Items() {
			union.Add(ag)
		}
		sharedList := sharedAgents.Items()
		firstAgents := sharedList
		if len(firstAgents) > 2 {
			firstAgents = firstAgents[:2]
		}
		evidence := entities.NewOrderedMap[any]()
		evidence.Set("shared_agents", sharedList)
		evidence.Set("agent_overlap", float64(sharedAgents.Len())/float64(union.Len()))
		hint, _ := NewDependencyHint(DependencyHint{
			TaskID:                t.ID.Value,
			SuggestedDependencyID: otherTask.ID.Value,
			ConfidenceScore:       math.Min(confidence, 0.8),
			SuggestionReason:      "Tasks share " + itoa(sharedAgents.Len()) + " agent(s): " + strings.Join(firstAgents, ", "),
			SuggestionType:        SuggestionTypeResource,
			Evidence:              evidence,
		})
		hints = append(hints, hint)
	}
	return hints
}

// DependencyManagementEngine ports dependency_management_engine.DependencyManagementEngine.
type DependencyManagementEngine struct {
	DependencyResolver *DependencyResolverService
	TaskRepository     repositories.TaskRepository
	UserID             *string
	ContentAnalyzer    *ContentAnalyzer
	PerformanceMetrics *entities.OrderedMap[any]
}

// NewDependencyManagementEngine builds the engine with default performance metrics.
func NewDependencyManagementEngine(dependencyResolver *DependencyResolverService, taskRepository repositories.TaskRepository, userID *string) *DependencyManagementEngine {
	return &DependencyManagementEngine{
		DependencyResolver: dependencyResolver,
		TaskRepository:     taskRepository,
		UserID:             userID,
		ContentAnalyzer:    NewContentAnalyzer(taskRepository),
		PerformanceMetrics: newDependencyPerformanceMetrics(),
	}
}

func newDependencyPerformanceMetrics() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("analysis_time", 0.0)
	m.Set("suggestions_generated", 0)
	m.Set("suggestions_accepted", 0)
	m.Set("cache_hits", 0)
	m.Set("cache_misses", 0)
	return m
}

// WithUser mirrors with_user(user_id).
func (e *DependencyManagementEngine) WithUser(userID string) *DependencyManagementEngine {
	return NewDependencyManagementEngine(e.DependencyResolver.WithUser(userID), e.TaskRepository, &userID)
}

// ResolveDependenciesWithAI ports resolve_dependencies_with_ai.
func (e *DependencyManagementEngine) ResolveDependenciesWithAI(ctx context.Context, taskID string) (*EnhancedDependencyRelationships, error) {
	startTime := time.Now()

	basicRelationships, err := e.DependencyResolver.ResolveDependencies(ctx, taskID)
	if err == nil {
		aiSuggestions := e.generateAISuggestions(ctx, taskID)
		optimizationScore := e.calculateOptimizationScore(basicRelationships, aiSuggestions)
		suggestionSummary := e.generateSuggestionSummary(aiSuggestions)

		analysisTime := time.Since(startTime).Seconds()
		e.PerformanceMetrics.Set("analysis_time", analysisTime)
		e.PerformanceMetrics.Set("suggestions_generated", len(aiSuggestions))

		return &EnhancedDependencyRelationships{
			BasicRelationships: basicRelationships,
			AISuggestions:      aiSuggestions,
			SuggestionSummary:  suggestionSummary,
			OptimizationScore:  optimizationScore,
			PerformanceMetrics: e.PerformanceMetrics.Copy(),
		}, nil
	}

	// Fallback to basic resolution (Python re-calls the resolver, so a
	// TaskNotFoundError propagates from here).
	basicRelationships, err2 := e.DependencyResolver.ResolveDependencies(ctx, taskID)
	if err2 != nil {
		return nil, err2
	}
	metrics := entities.NewOrderedMap[any]()
	metrics.Set("error", err.Error())
	return &EnhancedDependencyRelationships{
		BasicRelationships: basicRelationships,
		AISuggestions:      []*DependencySuggestion{},
		SuggestionSummary:  "AI analysis failed, showing basic dependencies only",
		OptimizationScore:  0.0,
		PerformanceMetrics: metrics,
	}, nil
}

// SuggestDependencies ports suggest_dependencies. Python catches every exception
// (including TaskNotFoundError) and returns an empty list.
func (e *DependencyManagementEngine) SuggestDependencies(ctx context.Context, taskID string) []*DependencySuggestion {
	suggestions := []*DependencySuggestion{}

	taskIDObj, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return suggestions
	}
	t, err := e.TaskRepository.FindByID(ctx, taskIDObj)
	if err != nil || t == nil {
		return suggestions
	}

	contentHints := e.ContentAnalyzer.AnalyzeTaskContent(ctx, t)

	for _, hint := range contentHints {
		depID, err := value_objects.NewTaskId(hint.SuggestedDependencyID)
		if err != nil {
			continue
		}
		depTask, err := e.TaskRepository.FindByID(ctx, depID)
		if err != nil || depTask == nil {
			continue
		}
		effort := depTask.EstimatedEffort
		assignees := []string{}
		if len(depTask.Assignees) > 0 {
			assignees = append([]string{}, depTask.Assignees...)
		}
		depInfo := task.NewDependencyInfo(task.DependencyInfo{
			TaskID:               hint.SuggestedDependencyID,
			Title:                depTask.Title,
			Status:               depTask.Status.Value,
			Priority:             depTask.Priority.Value,
			CompletionPercentage: depTask.OverallProgress,
			IsBlocking:           false,
			IsBlocked:            false,
			EstimatedEffort:      &effort,
			Assignees:            assignees,
			UpdatedAt:            depTask.UpdatedAt,
		})
		suggestion := NewDependencySuggestion(hint)
		suggestion.TargetTaskInfo = depInfo
		suggestions = append(suggestions, suggestion)
	}

	sort.SliceStable(suggestions, func(i, j int) bool {
		return suggestions[i].Hint.ConfidenceScore > suggestions[j].Hint.ConfidenceScore
	})

	if len(suggestions) > 10 {
		suggestions = suggestions[:10]
	}
	return suggestions
}

// generateAISuggestions ports _generate_ai_suggestions.
func (e *DependencyManagementEngine) generateAISuggestions(ctx context.Context, taskID string) []*DependencySuggestion {
	return e.SuggestDependencies(ctx, taskID)
}

// calculateOptimizationScore ports _calculate_optimization_score.
func (e *DependencyManagementEngine) calculateOptimizationScore(basicRelationships *task.DependencyRelationships, aiSuggestions []*DependencySuggestion) float64 {
	if len(aiSuggestions) == 0 {
		return 0.0
	}

	highConfidenceSuggestions := []*DependencySuggestion{}
	for _, s := range aiSuggestions {
		if s.Hint.ConfidenceScore > 0.7 {
			highConfidenceSuggestions = append(highConfidenceSuggestions, s)
		}
	}
	existingDeps := len(basicRelationships.DependsOn)

	suggestionScore := 0.0
	for _, s := range highConfidenceSuggestions {
		suggestionScore += s.Hint.ConfidenceScore
	}
	suggestionScore /= float64(len(aiSuggestions))

	coverageScore := math.Min(1.0, float64(len(highConfidenceSuggestions))/float64(depMaxInt(1, existingDeps)))
	return (suggestionScore + coverageScore) / 2
}

// generateSuggestionSummary ports _generate_suggestion_summary.
func (e *DependencyManagementEngine) generateSuggestionSummary(suggestions []*DependencySuggestion) string {
	if len(suggestions) == 0 {
		return "No AI suggestions available"
	}

	highConf := 0
	mediumConf := 0
	for _, s := range suggestions {
		if s.Hint.ConfidenceScore > 0.7 {
			highConf++
		}
		if s.Hint.ConfidenceScore > 0.4 && s.Hint.ConfidenceScore <= 0.7 {
			mediumConf++
		}
	}

	parts := []string{}
	if highConf > 0 {
		parts = append(parts, itoa(highConf)+" high-confidence suggestion(s)")
	}
	if mediumConf > 0 {
		parts = append(parts, itoa(mediumConf)+" medium-confidence suggestion(s)")
	}

	total := len(suggestions)
	if len(parts) > 0 {
		return "Found " + itoa(total) + " AI suggestions: " + strings.Join(parts, ", ")
	}
	return "Found " + itoa(total) + " low-confidence AI suggestions"
}

// GetPerformanceMetrics ports get_performance_metrics.
func (e *DependencyManagementEngine) GetPerformanceMetrics() *entities.OrderedMap[any] {
	return e.PerformanceMetrics.Copy()
}

// ResetPerformanceMetrics ports reset_performance_metrics.
func (e *DependencyManagementEngine) ResetPerformanceMetrics() {
	e.PerformanceMetrics = newDependencyPerformanceMetrics()
}

func depMaxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func itoa(n int) string { return value_objects.PyStr(n) }
