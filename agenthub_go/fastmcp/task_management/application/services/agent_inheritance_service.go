package services

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AgentInheritanceService handles agent assignment inheritance logic between
// tasks and subtasks (Python application/services/agent_inheritance_service.py).
type AgentInheritanceService struct {
	taskRepository    repositories.TaskRepository
	subtaskRepository repositories.SubtaskRepository
}

// NewAgentInheritanceService mirrors __init__(task_repository, subtask_repository).
func NewAgentInheritanceService(taskRepository repositories.TaskRepository, subtaskRepository repositories.SubtaskRepository) *AgentInheritanceService {
	return &AgentInheritanceService{taskRepository: taskRepository, subtaskRepository: subtaskRepository}
}

// ApplyAgentInheritance applies inheritance to a subtask with no assignees; parentTask
// nil means the parent is fetched from the repository.
func (s *AgentInheritanceService) ApplyAgentInheritance(ctx context.Context, subtask *entities.Subtask, parentTask *entities.Task) (*entities.Subtask, error) {
	if subtask.ShouldInheritAssignees() {
		if parentTask == nil {
			var parentID value_objects.TaskId
			if subtask.ParentTaskID != nil {
				parentID = *subtask.ParentTaskID
			}
			fetched, err := s.taskRepository.FindByID(ctx, parentID)
			if err != nil {
				return subtask, err
			}
			parentTask = fetched
		}

		if parentTask != nil {
			parentAssignees := parentTask.GetInheritedAssigneesForSubtasks()
			if len(parentAssignees) > 0 {
				if err := subtask.InheritAssigneesFromParent(parentAssignees); err != nil {
					return subtask, err
				}
			}
		}
	}
	return subtask, nil
}

// ApplyInheritanceToAllSubtasks applies inheritance to every subtask of a task and
// returns the subtasks that were saved (assignees changed).
func (s *AgentInheritanceService) ApplyInheritanceToAllSubtasks(ctx context.Context, taskID value_objects.TaskId) ([]*entities.Subtask, error) {
	parentTask, err := s.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if parentTask == nil {
		return []*entities.Subtask{}, nil
	}

	subtasks, err := s.subtaskRepository.FindByParentTaskID(ctx, taskID)
	if err != nil {
		return nil, err
	}

	updatedSubtasks := []*entities.Subtask{}
	for _, subtask := range subtasks {
		if subtask == nil || !subtask.ShouldInheritAssignees() {
			continue
		}
		originalAssignees := append([]string{}, subtask.Assignees...)
		if _, err := s.ApplyAgentInheritance(ctx, subtask, parentTask); err != nil {
			return nil, err
		}
		currentAssignees := subtask.Assignees
		if !zpAInheritanceStringSlicesEqual(currentAssignees, originalAssignees) {
			if _, err := s.subtaskRepository.Save(ctx, subtask); err != nil {
				return nil, err
			}
			updatedSubtasks = append(updatedSubtasks, subtask)
		}
	}

	return updatedSubtasks, nil
}

// ValidateAgentAssignments validates and normalizes assignees via entities.NormalizeAssignees, raising a *value_objects.ValueError for invalid assignees.
func (s *AgentInheritanceService) ValidateAgentAssignments(assignees []string) ([]string, error) {
	return entities.NormalizeAssignees(assignees)
}

// GetInheritanceSummary returns the inheritance summary dict for a task and its
// subtasks, or an {"error": ...} dict when the task is missing.
func (s *AgentInheritanceService) GetInheritanceSummary(ctx context.Context, taskID value_objects.TaskId) (*entities.OrderedMap[any], error) {
	parentTask, err := s.taskRepository.FindByID(ctx, taskID)
	if err != nil {
		return nil, err
	}
	if parentTask == nil {
		summary := entities.NewOrderedMap[any]()
		summary.Set("error", "Task "+taskID.String()+" not found")
		return summary, nil
	}

	subtasks, err := s.subtaskRepository.FindByParentTaskID(ctx, taskID)
	if err != nil {
		return nil, err
	}

	summary := entities.NewOrderedMap[any]()
	summary.Set("task_id", taskID.String())
	summary.Set("parent_assignees", parentTask.Assignees)
	summary.Set("parent_assignee_count", len(parentTask.Assignees))
	summary.Set("total_subtasks", len(subtasks))
	summary.Set("subtasks_with_assignees", 0)
	summary.Set("subtasks_inheriting", 0)
	subtaskDetails := []*entities.OrderedMap[any]{}

	for _, subtask := range subtasks {
		if subtask == nil {
			continue
		}
		currentAssignees := subtask.Assignees
		subtaskInfo := entities.NewOrderedMap[any]()
		subtaskInfo.Set("id", zpAInheritanceTaskIDString(subtask.ID))
		subtaskInfo.Set("title", subtask.Title)
		subtaskInfo.Set("has_assignees", subtask.HasAssignees())
		subtaskInfo.Set("should_inherit", subtask.ShouldInheritAssignees())
		subtaskInfo.Set("current_assignees", currentAssignees)
		subtaskInfo.Set("assignee_count", len(currentAssignees))

		if subtask.HasAssignees() {
			count, _ := summary.Get("subtasks_with_assignees")
			summary.Set("subtasks_with_assignees", count.(int)+1)
		}
		if subtask.ShouldInheritAssignees() {
			count, _ := summary.Get("subtasks_inheriting")
			summary.Set("subtasks_inheriting", count.(int)+1)
		}

		subtaskDetails = append(subtaskDetails, subtaskInfo)
	}

	summary.Set("subtask_details", subtaskDetails)
	return summary, nil
}

// zpAInheritanceTaskIDString mirrors str(task_id) for an optional TaskId (None -> "None").
func zpAInheritanceTaskIDString(id *value_objects.TaskId) string {
	if id == nil {
		return "None"
	}
	return id.String()
}

// zpAInheritanceStringSlicesEqual mirrors Python list equality for assignee lists;
// nil and an empty slice compare equal (len-based, like ==).
func zpAInheritanceStringSlicesEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
