package services

import (
	"context"
	"fmt"
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// ValidationGitBranchRepository is GitBranchRepositoryProtocol.
type ValidationGitBranchRepository interface {
	Exists(ctx context.Context, branchID string) (bool, error)
}

// SimilarTask is one entry of additional_context["similar_tasks"]; Title "" = missing.
type SimilarTask struct{ Title string }

// TaskValidationService centralizes business validation rules for tasks. Repository
// and error handling follow Python: any failure inside a public validator is returned
// as a single "<Prefix> error: <message>" entry.
type TaskValidationService struct {
	gitBranchRepository ValidationGitBranchRepository
	idValidator         *utilities.IDValidator
}

// NewTaskValidationService builds the service; repository and validator may be nil.
func NewTaskValidationService(g ValidationGitBranchRepository, v *utilities.IDValidator) *TaskValidationService {
	if v == nil {
		v = utilities.NewIDValidator(true)
	}
	return &TaskValidationService{gitBranchRepository: g, idValidator: v}
}

func runeLen(s string) int { return utf8.RuneCountInString(s) }

func strOrNone(p *string) string {
	if p == nil {
		return "None"
	}
	return *p
}

// ValidateTaskCreation runs the full creation validation.
func (s *TaskValidationService) ValidateTaskCreation(ctx context.Context, task *entities.Task, similar []SimilarTask) []string {
	errs, err := s.creationErrors(ctx, task, similar)
	if err != nil {
		return []string{"Validation system error: " + err.Error()}
	}
	return errs
}

func (s *TaskValidationService) creationErrors(ctx context.Context, task *entities.Task, similar []SimilarTask) ([]string, error) {
	errs := s.validateCoreFields(task)
	rel, err := s.validateRelationships(ctx, task)
	if err != nil {
		return nil, err
	}
	errs = append(errs, rel...)
	errs = append(errs, s.ValidateBusinessConstraints(task, "create")...)
	errs = append(errs, s.ValidateContentAppropriateness(task)...)
	title := value_objects.PyStrip(value_objects.PyLower(task.Title))
	for _, st := range similar {
		if value_objects.PyStrip(value_objects.PyLower(st.Title)) == title {
			errs = append(errs, fmt.Sprintf("A task with similar title already exists: '%s'", st.Title))
			break
		}
	}
	return errs, nil
}

// ValidateTaskUpdate runs the full update validation.
func (s *TaskValidationService) ValidateTaskUpdate(current, updated *entities.Task) []string {
	errs := s.validateCoreFields(updated)
	if (current.ID == nil) != (updated.ID == nil) || (current.ID != nil && current.ID.Value != updated.ID.Value) {
		errs = append(errs, "Field 'id' cannot be modified after creation")
	}
	errs = append(errs, s.ValidateBusinessConstraints(updated, "update")...)
	errs = append(errs, s.ValidateContentAppropriateness(updated)...)
	return append(errs, validateStatusTransition(current, updated)...)
}

// ValidateTaskRelationships validates git branch and dependency rules.
func (s *TaskValidationService) ValidateTaskRelationships(ctx context.Context, task *entities.Task) (bool, []string) {
	errs := []string{}
	if task.GitBranchID != nil && *task.GitBranchID != "" {
		if s.gitBranchRepository != nil {
			ok, err := s.gitBranchRepository.Exists(ctx, *task.GitBranchID)
			if err != nil {
				return false, []string{"Relationship validation error: " + err.Error()}
			}
			if !ok {
				errs = append(errs, fmt.Sprintf("Git branch '%s' does not exist", *task.GitBranchID))
			}
		}
	} else {
		errs = append(errs, "Task must be associated with a valid git branch")
	}
	if len(task.Dependencies) > 0 {
		if len(task.Dependencies) > 10 {
			errs = append(errs, "Task cannot have more than 10 dependencies")
		}
		id := taskIDStr(task)
		for _, d := range task.Dependencies {
			if d.Value == id {
				errs = append(errs, "Task cannot depend on itself")
			}
		}
	}
	return len(errs) == 0, errs
}

// ValidateBusinessConstraints validates business-specific constraints. Python defect
// preserved: Task.due_date is a str, so any non-empty due date raises AttributeError
// ('str' object has no attribute 'tzinfo') and replaces all findings with one error.
func (s *TaskValidationService) ValidateBusinessConstraints(task *entities.Task, operationType string) []string {
	errs := []string{}
	switch {
	case value_objects.PyStrip(task.Title) == "":
		errs = append(errs, "Task title cannot be empty")
	case runeLen(task.Title) > 200:
		errs = append(errs, "Task title cannot exceed 200 characters")
	case runeLen(value_objects.PyStrip(task.Title)) < 3:
		errs = append(errs, "Task title must be at least 3 characters long")
	}
	if runeLen(task.Description) > 2000 {
		errs = append(errs, "Task description cannot exceed 2000 characters")
	}
	if len(task.Assignees) > 0 {
		if len(task.Assignees) > 5 {
			errs = append(errs, "Task cannot have more than 5 assignees")
		}
		for _, a := range task.Assignees {
			if value_objects.PyStrip(a) == "" {
				errs = append(errs, "Assignee names cannot be empty")
			} else if runeLen(a) > 50 {
				errs = append(errs, "Assignee names cannot exceed 50 characters")
			}
		}
	}
	if len(task.Labels) > 0 {
		if len(task.Labels) > 10 {
			errs = append(errs, "Task cannot have more than 10 labels")
		}
		for _, l := range task.Labels {
			if value_objects.PyStrip(l) == "" {
				errs = append(errs, "Labels cannot be empty")
			} else if runeLen(l) > 30 {
				errs = append(errs, "Labels cannot exceed 30 characters")
			}
		}
	}
	if task.DueDate != nil && *task.DueDate != "" {
		return []string{"Business constraint validation error: 'str' object has no attribute 'tzinfo'"}
	}
	if operationType == "create" || operationType == "update" {
		errs = append(errs, validatePriorityStatusCombination(task)...)
	}
	return errs
}

var titlePlaceholders = []string{"todo", "fix this", "test", "placeholder", "tbd", "to be done"}
var effortUnits = []string{"hour", "day", "week", "month", "minute", "sprint", "story point"}

// ValidateContentAppropriateness validates content quality.
func (s *TaskValidationService) ValidateContentAppropriateness(task *entities.Task) []string {
	errs := []string{}
	if task.Title != "" {
		lower := value_objects.PyStrip(value_objects.PyLower(task.Title))
		for _, p := range titlePlaceholders {
			if strings.Contains(lower, p) {
				errs = append(errs, "Task title appears to be placeholder text. Please provide a descriptive title.")
				break
			}
		}
		words := value_objects.PySplit(lower)
		if len(words) > 1 {
			counts, maxRep := map[string]int{}, 0
			for _, w := range words {
				counts[w]++
				if counts[w] > maxRep {
					maxRep = counts[w]
				}
			}
			if float64(maxRep) > float64(len(words))/2 {
				errs = append(errs, "Task title contains too much repetition")
			}
		}
	}
	if task.Description != "" {
		desc := value_objects.PyStrip(value_objects.PyLower(task.Description))
		switch value_objects.PyStrip(task.Description) {
		case "", "n/a", "na", "none":
		default:
			if runeLen(desc) < 10 {
				errs = append(errs, "Task description is too brief to be meaningful")
			}
		}
	}
	if task.EstimatedEffort != "" {
		effort := value_objects.PyLower(value_objects.PyStrip(task.EstimatedEffort))
		found := false
		for _, u := range effortUnits {
			if strings.Contains(effort, u) {
				found = true
				break
			}
		}
		if !found {
			errs = append(errs, "Estimated effort should include time units (e.g., '2 hours', '1 day', '3 weeks')")
		}
	}
	return errs
}

func (s *TaskValidationService) validateCoreFields(task *entities.Task) []string {
	errs := []string{}
	if task.ID == nil {
		errs = append(errs, "Task ID is required")
	} else if r := s.idValidator.DetectIDType(task.ID.Value, "task_id"); !r.IsValid {
		errs = append(errs, "Invalid task ID format: "+strOrNone(r.ErrorMessage))
	}
	if task.Title == "" {
		errs = append(errs, "Task title is required")
	}
	if task.Status == nil {
		errs = append(errs, "Task status is required")
	}
	if task.Priority == nil {
		errs = append(errs, "Task priority is required")
	}
	return errs
}

func (s *TaskValidationService) validateRelationships(ctx context.Context, task *entities.Task) ([]string, error) {
	errs := []string{}
	if task.GitBranchID == nil || *task.GitBranchID == "" {
		return append(errs, "Git branch ID is required"), nil
	}
	branchID := *task.GitBranchID
	if r := s.idValidator.DetectIDType(branchID, "git_branch_id"); !r.IsValid {
		errs = append(errs, "Invalid git branch ID format: "+strOrNone(r.ErrorMessage))
	}
	if s.gitBranchRepository != nil {
		ok, err := s.gitBranchRepository.Exists(ctx, branchID)
		if err != nil {
			return nil, err
		}
		if !ok {
			errs = append(errs, fmt.Sprintf("Git branch '%s' does not exist", branchID))
		}
	}
	if task.ID != nil && task.ID.Value == branchID {
		errs = append(errs, "CRITICAL: Task ID and Git Branch ID are identical. "+
			"This indicates parameter confusion that leads to data integrity issues.")
	}
	return errs, nil
}

var updateTransitions = map[string][]string{
	"todo":        {"in_progress", "blocked", "cancelled"},
	"in_progress": {"review", "testing", "done", "blocked", "todo"},
	"review":      {"in_progress", "done", "testing"},
	"testing":     {"review", "done", "in_progress"},
	"blocked":     {"todo", "in_progress"},
	"done":        {},
	"cancelled":   {},
}

func validateStatusTransition(current, updated *entities.Task) []string {
	errs := []string{}
	from, to := lowerStatus(current), lowerStatus(updated)
	if from == to {
		return errs
	}
	for _, a := range updateTransitions[from] {
		if a == to {
			return errs
		}
	}
	return append(errs, fmt.Sprintf("Invalid status transition from '%s' to '%s'", from, to))
}

func validatePriorityStatusCombination(task *entities.Task) []string {
	errs := []string{}
	priority, status := value_objects.PyLower(priorityStr(task)), lowerStatus(task)
	if priority == "critical" && status == "todo" {
		errs = append(errs, "Critical priority tasks should be started immediately")
	}
	if status == "done" && (priority == "urgent" || priority == "critical") {
		if task.CompletionSummary == nil || *task.CompletionSummary == "" {
			errs = append(errs, "High priority completed tasks must include completion summary")
		}
	}
	return errs
}

// ValidateIDParameters validates ID parameters to prevent MCP/application ID confusion.
func (s *TaskValidationService) ValidateIDParameters(taskID, gitBranchID, projectID, userID *string) []string {
	r := s.idValidator.ValidateParameterMapping(taskID, gitBranchID, projectID, userID)
	errs := []string{}
	if !r.IsValid {
		msg := "ID parameter validation failed"
		if r.ErrorMessage != nil && *r.ErrorMessage != "" {
			msg = *r.ErrorMessage
		}
		errs = append(errs, msg)
	}
	return errs
}

// ValidateTaskContextIntegrity validates task/git branch ID relationships ("" = None).
func (s *TaskValidationService) ValidateTaskContextIntegrity(taskID, expectedGitBranchID string) []string {
	r := s.idValidator.ValidateTaskContext(taskID, expectedGitBranchID)
	errs := []string{}
	if !r.IsValid {
		msg := "Task context validation failed"
		if r.ErrorMessage != nil && *r.ErrorMessage != "" {
			msg = *r.ErrorMessage
		}
		errs = append(errs, msg)
	}
	return errs
}
