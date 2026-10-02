// Package services ports ai_task_planning/application/services.
package services

import (
	"math"
	"strings"

	"agenthub/fastmcp/ai_task_planning/domain/entities"
	domainservices "agenthub/fastmcp/ai_task_planning/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AITaskFacade is the TaskApplicationFacade surface AITaskPlanningService accepts.
// The Python class TaskApplicationFacade has no Go port; the service only checks
// whether a facade was supplied (execute_plan_with_mcp), never calling a method,
// so this interface declares no methods.
type AITaskFacade interface{}

// AIAgentCapabilities is one entry of the agent capability mapping.
type AIAgentCapabilities struct {
	Patterns           []string
	Phases             []entities.ExecutionPhase
	MaxConcurrentTasks int
	Specializations    []string
}

// AITaskPlanningService mirrors ai_planning_service.AITaskPlanningService.
type AITaskPlanningService struct {
	RequirementAnalyzer *domainservices.RequirementAnalyzer
	TaskFacade          AITaskFacade
	AgentCapabilities   *tmentities.OrderedMap[*AIAgentCapabilities]
}

// NewAITaskPlanningService mirrors AITaskPlanningService.__init__. Python's
// task_facade defaults to None; callers pass nil for that.
func NewAITaskPlanningService(taskFacade AITaskFacade) *AITaskPlanningService {
	return &AITaskPlanningService{
		RequirementAnalyzer: domainservices.NewRequirementAnalyzer(),
		TaskFacade:          taskFacade,
		AgentCapabilities:   aiPlanningAgentCapabilities(),
	}
}

func aiPlanningAgentCapabilities() *tmentities.OrderedMap[*AIAgentCapabilities] {
	caps := tmentities.NewOrderedMap[*AIAgentCapabilities]()
	caps.Set("coding-agent", &AIAgentCapabilities{
		Patterns:           []string{"crud_operations", "api_integration", "database_schema"},
		Phases:             []entities.ExecutionPhase{entities.PhaseImplementation},
		MaxConcurrentTasks: 3,
		Specializations:    []string{"backend", "api", "database"},
	})
	caps.Set("shadcn-ui-expert-agent", &AIAgentCapabilities{
		Patterns:           []string{"ui_component"},
		Phases:             []entities.ExecutionPhase{entities.PhaseImplementation, entities.PhaseArchitecture},
		MaxConcurrentTasks: 2,
		Specializations:    []string{"frontend", "ui", "components"},
	})
	caps.Set("system-architect-agent", &AIAgentCapabilities{
		Patterns:           []string{"database_schema", "api_integration", "security_requirement"},
		Phases:             []entities.ExecutionPhase{entities.PhaseArchitecture, entities.PhasePlanning},
		MaxConcurrentTasks: 2,
		Specializations:    []string{"architecture", "design", "systems"},
	})
	caps.Set("test-orchestrator-agent", &AIAgentCapabilities{
		Patterns:           []string{"testing_requirement"},
		Phases:             []entities.ExecutionPhase{entities.PhaseTesting},
		MaxConcurrentTasks: 4,
		Specializations:    []string{"testing", "qa", "automation"},
	})
	caps.Set("security-auditor-agent", &AIAgentCapabilities{
		Patterns:           []string{"security_requirement", "user_authentication"},
		Phases:             []entities.ExecutionPhase{entities.PhaseReview, entities.PhaseArchitecture},
		MaxConcurrentTasks: 2,
		Specializations:    []string{"security", "audit", "compliance"},
	})
	caps.Set("debugger-agent", &AIAgentCapabilities{
		Patterns:           []string{"bug_fix"},
		Phases:             []entities.ExecutionPhase{entities.PhaseImplementation},
		MaxConcurrentTasks: 2,
		Specializations:    []string{"debugging", "troubleshooting", "fixes"},
	})
	caps.Set("documentation-agent", &AIAgentCapabilities{
		Patterns:           []string{"documentation_requirement"},
		Phases:             []entities.ExecutionPhase{entities.PhasePlanning, entities.PhaseReview},
		MaxConcurrentTasks: 3,
		Specializations:    []string{"documentation", "guides", "specs"},
	})
	caps.Set("devops-agent", &AIAgentCapabilities{
		Patterns:           []string{"deployment", "monitoring"},
		Phases:             []entities.ExecutionPhase{entities.PhaseDeployment, entities.PhaseMonitoring},
		MaxConcurrentTasks: 2,
		Specializations:    []string{"deployment", "infrastructure", "cicd"},
	})
	return caps
}

// CreateIntelligentPlan generates an AI task plan from a planning request.
func (s *AITaskPlanningService) CreateIntelligentPlan(planningRequest *entities.PlanningRequest) (*entities.TaskPlan, error) {
	analyzedRequirements := s.RequirementAnalyzer.AnalyzeRequirementsBatch(planningRequest.Requirements)
	insights := s.RequirementAnalyzer.GeneratePlanningInsights(analyzedRequirements)

	plan := entities.NewTaskPlan(
		tmvo.NewUUIDv4(),
		planningRequest.ID,
		"AI Plan: "+planningRequest.Title,
		"Intelligent breakdown of "+planningRequest.Title+" into executable tasks",
	)

	s.aiPlanningGenerateTasksFromRequirements(plan, analyzedRequirements, planningRequest)
	s.aiPlanningOptimizeAgentAssignments(plan)
	s.aiPlanningGenerateIntelligentDependencies(plan, analyzedRequirements)

	if _, err := plan.CalculateCriticalPath(); err != nil {
		return nil, err
	}
	plan.FindParallelExecutionGroups()

	isValid, validationErrors := plan.ValidatePlan()
	if !isValid {
		s.aiPlanningFixPlanIssues(plan, validationErrors)
	}

	plan.ConfidenceScore = s.aiPlanningCalculateConfidenceScore(plan, analyzedRequirements, insights)

	phaseOrder := []entities.ExecutionPhase{
		entities.PhasePlanning,
		entities.PhaseArchitecture,
		entities.PhaseImplementation,
		entities.PhaseTesting,
		entities.PhaseReview,
		entities.PhaseDeployment,
		entities.PhaseMonitoring,
	}
	filtered := []entities.ExecutionPhase{}
	for _, phase := range phaseOrder {
		if aiPlanningPhaseIn(plan.ExecutionPhases, phase) {
			filtered = append(filtered, phase)
		}
	}
	plan.ExecutionPhases = filtered

	return plan, nil
}

func (s *AITaskPlanningService) aiPlanningGenerateTasksFromRequirements(plan *entities.TaskPlan,
	analyzedRequirements []*domainservices.AnalyzedRequirement, planningRequest *entities.PlanningRequest) {

	for _, analysis := range analyzedRequirements {
		taskType := s.aiPlanningDetermineTaskType(analysis)
		phase := s.aiPlanningDetermineExecutionPhase(analysis)

		mainTask := entities.NewPlannedTask(
			tmvo.NewUUIDv4(),
			"Implement: "+aiPlanningTruncate(analysis.OriginalRequirement.Description, 60)+"...",
			analysis.OriginalRequirement.Description,
			taskType,
			phase,
		)
		mainTask.EstimatedHours = analysis.EstimatedEffortHours
		mainTask.EstimatedComplexity = s.aiPlanningMapComplexityLevel(analysis)
		mainTask.AcceptanceCriteria = analysis.OriginalRequirement.AcceptanceCriteria
		mainTask.TechnicalRequirements = analysis.TechnicalConsiderations
		mainTask.Priority = analysis.OriginalRequirement.Priority
		mainTask.Risks = analysis.RiskFactors
		mainTask.FileReferences = analysis.OriginalRequirement.RelatedFiles

		plan.AddTask(mainTask)

		s.aiPlanningGenerateSubtasksForPatterns(plan, mainTask, analysis)
	}
}

// aiPlanningSubtaskTemplate is one tuple of the subtask templates table.
type aiPlanningSubtaskTemplate struct {
	title string
	phase entities.ExecutionPhase
	agent string
	hours float64
}

func aiPlanningSubtaskTemplates() map[string][]aiPlanningSubtaskTemplate {
	return map[string][]aiPlanningSubtaskTemplate{
		"crud_operations": {
			{"Design Data Models", entities.PhaseArchitecture, "system-architect-agent", 2.0},
			{"Implement CRUD Operations", entities.PhaseImplementation, "coding-agent", 4.0},
			{"Add Input Validation", entities.PhaseImplementation, "coding-agent", 2.0},
			{"Create API Tests", entities.PhaseTesting, "test-orchestrator-agent", 3.0},
		},
		"user_authentication": {
			{"Design Security Architecture", entities.PhaseArchitecture, "security-auditor-agent", 3.0},
			{"Implement Authentication Logic", entities.PhaseImplementation, "coding-agent", 4.0},
			{"Add Password Security", entities.PhaseImplementation, "security-auditor-agent", 2.0},
			{"Security Audit", entities.PhaseReview, "security-auditor-agent", 2.0},
			{"Authentication Testing", entities.PhaseTesting, "test-orchestrator-agent", 3.0},
		},
		"ui_component": {
			{"Design Component Structure", entities.PhaseArchitecture, "shadcn-ui-expert-agent", 2.0},
			{"Implement UI Component", entities.PhaseImplementation, "shadcn-ui-expert-agent", 3.0},
			{"Add Component Tests", entities.PhaseTesting, "test-orchestrator-agent", 2.0},
			{"Component Documentation", entities.PhaseReview, "documentation-agent", 1.0},
		},
		"api_integration": {
			{"API Research and Documentation", entities.PhasePlanning, "system-architect-agent", 2.0},
			{"Implement API Integration", entities.PhaseImplementation, "coding-agent", 4.0},
			{"Error Handling", entities.PhaseImplementation, "coding-agent", 2.0},
			{"Integration Testing", entities.PhaseTesting, "test-orchestrator-agent", 3.0},
		},
	}
}

func (s *AITaskPlanningService) aiPlanningGenerateSubtasksForPatterns(plan *entities.TaskPlan,
	mainTask *entities.PlannedTask, analysis *domainservices.AnalyzedRequirement) {

	templates := aiPlanningSubtaskTemplates()
	for _, pattern := range analysis.DetectedPatterns {
		patternKey := string(pattern)
		entries, ok := templates[patternKey]
		if !ok {
			continue
		}
		for _, entry := range entries {
			subtask := entities.NewPlannedTask(
				tmvo.NewUUIDv4(),
				mainTask.Title+" - "+entry.title,
				entry.title+" for "+analysis.OriginalRequirement.Description,
				entities.TaskTypeSubtask,
				entry.phase,
			)
			subtask.EstimatedHours = entry.hours
			subtask.EstimatedComplexity = "medium"
			subtask.AgentAssignment = entities.NewAgentAssignment(entry.agent, nil, nil)
			subtask.AcceptanceCriteria = []string{"Complete " + tmvo.PyLower(entry.title)}
			subtask.Priority = mainTask.Priority
			parentID := mainTask.ID
			subtask.ParentTaskID = &parentID

			plan.AddTask(subtask)
			mainTask.AddSubtask(subtask)
		}
	}
}

func (s *AITaskPlanningService) aiPlanningOptimizeAgentAssignments(plan *entities.TaskPlan) {
	unassignedTasks := []*entities.PlannedTask{}
	for _, task := range plan.Tasks {
		if task.AgentAssignment == nil {
			unassignedTasks = append(unassignedTasks, task)
		}
	}

	for _, task := range unassignedTasks {
		bestAgent := s.aiPlanningFindOptimalAgent(task, plan)
		if bestAgent == "" {
			continue
		}
		task.AgentAssignment = entities.NewAgentAssignment(bestAgent, nil, nil)
		currentWorkload, _ := plan.AgentWorkload.Get(bestAgent)
		plan.AgentWorkload.Set(bestAgent, currentWorkload+task.EstimatedHours)
		plan.RequiredAgents.Add(bestAgent)
	}
}

func (s *AITaskPlanningService) aiPlanningFindOptimalAgent(task *entities.PlannedTask, plan *entities.TaskPlan) string {
	type aiPlanningAgentScore struct {
		agent string
		score float64
	}

	agentScores := []aiPlanningAgentScore{}
	for _, agent := range s.AgentCapabilities.Keys() {
		capabilities, _ := s.AgentCapabilities.Get(agent)
		score := 0.0

		if aiPlanningPhaseIn(capabilities.Phases, task.Phase) {
			score += 3
		}

		currentWorkload, _ := plan.AgentWorkload.Get(agent)
		maxWorkload := 40.0
		workloadFactor := math.Max(0, (maxWorkload-currentWorkload)/maxWorkload)
		score += workloadFactor * 2

		if task.TaskType == entities.TaskTypeTesting && aiPlanningContains(capabilities.Specializations, "testing") {
			score += 4
		} else if (task.TaskType == entities.TaskTypeFeature || task.TaskType == entities.TaskTypeTask) &&
			aiPlanningContains(capabilities.Specializations, "backend") {
			score += 2
		} else if task.Phase == entities.PhaseArchitecture &&
			aiPlanningContains(capabilities.Specializations, "architecture") {
			score += 4
		}

		agentScores = append(agentScores, aiPlanningAgentScore{agent, score})
	}

	if len(agentScores) > 0 {
		best := agentScores[0]
		for _, candidate := range agentScores[1:] {
			if candidate.score > best.score {
				best = candidate
			}
		}
		return best.agent
	}

	return "coding-agent"
}

func (s *AITaskPlanningService) aiPlanningGenerateIntelligentDependencies(plan *entities.TaskPlan,
	analyzedRequirements []*domainservices.AnalyzedRequirement) {

	phaseOrder := []entities.ExecutionPhase{
		entities.PhasePlanning,
		entities.PhaseArchitecture,
		entities.PhaseImplementation,
		entities.PhaseTesting,
		entities.PhaseReview,
		entities.PhaseDeployment,
		entities.PhaseMonitoring,
	}

	tasksByPhase := map[entities.ExecutionPhase][]*entities.PlannedTask{}
	for _, task := range plan.Tasks {
		tasksByPhase[task.Phase] = append(tasksByPhase[task.Phase], task)
	}

	for i := 0; i < len(phaseOrder)-1; i++ {
		currentTasks := tasksByPhase[phaseOrder[i]]
		nextTasks := tasksByPhase[phaseOrder[i+1]]
		for _, currentTask := range currentTasks {
			for _, nextTask := range nextTasks {
				if s.aiPlanningTasksAreRelated(currentTask, nextTask) {
					plan.AddDependency(nextTask.ID, currentTask.ID, "finish_to_start", 0)
				}
			}
		}
	}

	parentChildMap := tmentities.NewOrderedMap[[]string]()
	for _, task := range plan.Tasks {
		if task.ParentTaskID == nil {
			continue
		}
		parent := plan.GetTaskByID(*task.ParentTaskID)
		if parent == nil {
			continue
		}
		children, _ := parentChildMap.Get(parent.ID)
		parentChildMap.Set(parent.ID, append(children, task.ID))
	}

	for _, parentID := range parentChildMap.Keys() {
		childIDs, _ := parentChildMap.Get(parentID)
		for _, childID := range childIDs {
			existingDep := false
			for _, dep := range plan.Dependencies {
				if (dep.DependentTaskID == parentID && dep.PrerequisiteTaskID == childID) ||
					(dep.DependentTaskID == childID && dep.PrerequisiteTaskID == parentID) {
					existingDep = true
					break
				}
			}
			if !existingDep {
				plan.AddDependency(parentID, childID, "finish_to_finish", 0)
			}
		}
	}
}

func (s *AITaskPlanningService) aiPlanningTasksAreRelated(task1, task2 *entities.PlannedTask) bool {
	if task1.ID == aiPlanningOptString(task2.ParentTaskID) ||
		task2.ID == aiPlanningOptString(task1.ParentTaskID) {
		return false
	}

	if task1.ParentTaskID != nil && task2.ParentTaskID != nil &&
		*task1.ParentTaskID == *task2.ParentTaskID {
		return true
	}

	if aiPlanningShareString(task1.FileReferences, task2.FileReferences) {
		return true
	}

	if aiPlanningCommonWordCount(tmvo.PyLower(task1.Title), tmvo.PyLower(task2.Title)) > 3 {
		return true
	}

	return false
}

func (s *AITaskPlanningService) aiPlanningFixPlanIssues(plan *entities.TaskPlan, validationErrors []string) {
	for _, validationError := range validationErrors {
		if strings.Contains(validationError, "Circular dependency") {
			if len(plan.Dependencies) > 0 {
				plan.Dependencies = plan.Dependencies[:len(plan.Dependencies)-1]
			}
		} else if strings.Contains(tmvo.PyLower(validationError), "unassigned") {
			for _, task := range plan.Tasks {
				if task.AgentAssignment == nil {
					task.AgentAssignment = entities.NewAgentAssignment("coding-agent", nil, nil)
				}
			}
		}
	}
}

func (s *AITaskPlanningService) aiPlanningCalculateConfidenceScore(plan *entities.TaskPlan,
	analyzedRequirements []*domainservices.AnalyzedRequirement, insights *tmentities.OrderedMap[any]) float64 {

	confidenceFactors := []float64{}

	patternDistribution, _ := insights.Get("pattern_distribution")
	totalPatterns := aiPlanningMappingLen(patternDistribution)
	if totalPatterns > 0 {
		confidenceFactors = append(confidenceFactors, math.Min(1.0, float64(totalPatterns)/5))
	}

	assignedTasks := 0
	for _, task := range plan.Tasks {
		if task.AgentAssignment != nil {
			assignedTasks++
		}
	}
	assignmentRatio := 0.0
	if len(plan.Tasks) > 0 {
		assignmentRatio = float64(assignedTasks) / float64(len(plan.Tasks))
	}
	confidenceFactors = append(confidenceFactors, assignmentRatio)

	if len(analyzedRequirements) > 0 {
		efforts := make([]float64, len(analyzedRequirements))
		for i, analysis := range analyzedRequirements {
			efforts[i] = analysis.EstimatedEffortHours
		}
		avgEffort := tmvo.PySum(efforts) / float64(len(analyzedRequirements))
		if avgEffort >= 1 && avgEffort <= 8 {
			confidenceFactors = append(confidenceFactors, 0.8)
		} else {
			confidenceFactors = append(confidenceFactors, 0.6)
		}
	} else {
		confidenceFactors = append(confidenceFactors, 0.3)
	}

	depRatio := 0.0
	if len(plan.Tasks) > 0 {
		depRatio = float64(len(plan.Dependencies)) / float64(len(plan.Tasks))
	}
	if depRatio >= 0.1 && depRatio <= 0.5 {
		confidenceFactors = append(confidenceFactors, 0.8)
	} else {
		confidenceFactors = append(confidenceFactors, 0.6)
	}

	medium, high := 0.0, 0.0
	if complexityDistAny, ok := insights.Get("complexity_distribution"); ok {
		if complexityDist, isMap := complexityDistAny.(*tmentities.OrderedMap[any]); isMap {
			if v, ok := complexityDist.Get("medium"); ok {
				medium, _ = tmvo.PyFloat(v)
			}
			if v, ok := complexityDist.Get("high"); ok {
				high, _ = tmvo.PyFloat(v)
			}
		}
	}
	if medium > high {
		confidenceFactors = append(confidenceFactors, 0.8)
	} else {
		confidenceFactors = append(confidenceFactors, 0.6)
	}

	if len(confidenceFactors) > 0 {
		return tmvo.PySum(confidenceFactors) / float64(len(confidenceFactors))
	}
	return 0.5
}

func (s *AITaskPlanningService) aiPlanningDetermineTaskType(analysis *domainservices.AnalyzedRequirement) entities.TaskType {
	if analysis.EstimatedEffortHours > 40 {
		return entities.TaskTypeEpic
	} else if analysis.EstimatedEffortHours > 16 {
		return entities.TaskTypeFeature
	} else if aiPlanningHasPatternValue(analysis.DetectedPatterns, "testing_requirement") {
		return entities.TaskTypeTesting
	} else if aiPlanningHasPatternValue(analysis.DetectedPatterns, "bug_fix") {
		return entities.TaskTypeBug
	} else if aiPlanningHasPatternValue(analysis.DetectedPatterns, "documentation") {
		return entities.TaskTypeDocumentation
	}
	return entities.TaskTypeTask
}

func (s *AITaskPlanningService) aiPlanningDetermineExecutionPhase(analysis *domainservices.AnalyzedRequirement) entities.ExecutionPhase {
	patterns := []string{}
	for _, pattern := range analysis.DetectedPatterns {
		patterns = append(patterns, string(pattern))
	}

	if aiPlanningContains(patterns, "documentation_requirement") {
		return entities.PhasePlanning
	} else if aiPlanningContains(patterns, "database_schema") || aiPlanningContains(patterns, "security_requirement") {
		return entities.PhaseArchitecture
	} else if aiPlanningContains(patterns, "testing_requirement") {
		return entities.PhaseTesting
	} else if aiPlanningContains(patterns, "deployment") || aiPlanningContains(patterns, "monitoring") {
		return entities.PhaseDeployment
	}
	return entities.PhaseImplementation
}

func (s *AITaskPlanningService) aiPlanningMapComplexityLevel(analysis *domainservices.AnalyzedRequirement) string {
	keywordComplexity := "medium"
	if v, ok := analysis.ComplexityIndicators.Get("keyword_complexity"); ok {
		if s, isStr := v.(string); isStr {
			keywordComplexity = s
		}
	}
	patternComplexity := 2.0
	if v, ok := analysis.ComplexityIndicators.Get("pattern_complexity"); ok {
		if f, isNum := tmvo.PyFloat(v); isNum {
			patternComplexity = f
		}
	}

	if keywordComplexity == "high" || patternComplexity > 4 {
		return "complex"
	} else if keywordComplexity == "low" && patternComplexity < 2 {
		return "simple"
	}
	return "medium"
}

// ExecutePlanWithMCP executes the task plan by creating MCP tasks.
func (s *AITaskPlanningService) ExecutePlanWithMCP(plan *entities.TaskPlan, gitBranchID string) *tmentities.OrderedMap[any] {
	if s.TaskFacade == nil {
		out := tmentities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error", "Task facade not available for MCP integration")
		return out
	}

	createdTasks := []any{}
	failedTasks := []any{}

	rootTasks := plan.GetRootTasks()
	for _, rootTask := range rootTasks {
		mcpRequest := rootTask.ToMCPTaskRequest()
		mcpRequest.Set("git_branch_id", gitBranchID)

		mcpTaskID := tmvo.NewUUIDv4()
		rootTask.MCPTaskID = &mcpTaskID
		rootTask.Status = "created"

		created := tmentities.NewOrderedMap[any]()
		created.Set("planned_task_id", rootTask.ID)
		created.Set("mcp_task_id", mcpTaskID)
		created.Set("title", rootTask.Title)
		createdTasks = append(createdTasks, created)

		subtasks := plan.GetSubtasks(rootTask.ID)
		for _, subtask := range subtasks {
			subtaskRequest := subtask.ToMCPTaskRequest()
			subtaskRequest.Set("git_branch_id", gitBranchID)

			subtaskMCPID := tmvo.NewUUIDv4()
			subtask.MCPTaskID = &subtaskMCPID
			subtask.Status = "created"

			subtaskCreated := tmentities.NewOrderedMap[any]()
			subtaskCreated.Set("planned_task_id", subtask.ID)
			subtaskCreated.Set("mcp_task_id", subtaskMCPID)
			subtaskCreated.Set("title", subtask.Title)
			subtaskCreated.Set("parent_task_id", mcpTaskID)
			createdTasks = append(createdTasks, subtaskCreated)
		}
	}

	planSummary := tmentities.NewOrderedMap[any]()
	planSummary.Set("total_tasks", len(plan.Tasks))
	planSummary.Set("created_count", len(createdTasks))
	planSummary.Set("failed_count", len(failedTasks))
	planSummary.Set("estimated_hours", plan.TotalEstimatedHours)
	planSummary.Set("required_agents", plan.RequiredAgents.Items())

	out := tmentities.NewOrderedMap[any]()
	out.Set("success", len(failedTasks) == 0)
	out.Set("created_tasks", createdTasks)
	out.Set("failed_tasks", failedTasks)
	out.Set("plan_summary", planSummary)
	return out
}

// --- helpers -------------------------------------------------------------

func aiPlanningTruncate(s string, n int) string {
	runes := []rune(s)
	if len(runes) > n {
		runes = runes[:n]
	}
	return string(runes)
}

func aiPlanningPhaseIn(phases []entities.ExecutionPhase, phase entities.ExecutionPhase) bool {
	for _, p := range phases {
		if p == phase {
			return true
		}
	}
	return false
}

func aiPlanningContains(items []string, item string) bool {
	for _, x := range items {
		if x == item {
			return true
		}
	}
	return false
}

func aiPlanningHasPatternValue(patterns []domainservices.RequirementPattern, value string) bool {
	for _, pattern := range patterns {
		if string(pattern) == value {
			return true
		}
	}
	return false
}

func aiPlanningOptString(s *string) string {
	if s == nil {
		return ""
	}
	return *s
}

func aiPlanningShareString(a, b []string) bool {
	if len(a) == 0 || len(b) == 0 {
		return false
	}
	set := map[string]struct{}{}
	for _, x := range a {
		set[x] = struct{}{}
	}
	for _, x := range b {
		if _, ok := set[x]; ok {
			return true
		}
	}
	return false
}

func aiPlanningCommonWordCount(a, b string) int {
	setA := map[string]struct{}{}
	for _, word := range tmvo.PySplit(a) {
		setA[word] = struct{}{}
	}
	setB := map[string]struct{}{}
	for _, word := range tmvo.PySplit(b) {
		setB[word] = struct{}{}
	}
	count := 0
	for word := range setA {
		if _, ok := setB[word]; ok {
			count++
		}
	}
	return count
}

func aiPlanningMappingLen(v any) int {
	switch m := v.(type) {
	case *tmentities.OrderedMap[any]:
		return m.Len()
	case map[string]any:
		return len(m)
	}
	return 0
}
