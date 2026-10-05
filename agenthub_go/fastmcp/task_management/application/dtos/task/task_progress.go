package task

import "agenthub/fastmcp/task_management/domain/entities"

// TaskProgress tracks the current task and subtask progress.
type TaskProgress struct {
	CurrentTaskID     *int
	CurrentSubtaskID  *string
	TaskStartTime     *string
	SubtaskStartTime  *string
	CompletedTasks    []int
	CompletedSubtasks []string
	LastUpdated       string
}

// ToDict mirrors asdict(self).
func (p TaskProgress) ToDict() *entities.OrderedMap[any] {
	var currentTask, currentSubtask, taskStart, subtaskStart any
	if p.CurrentTaskID != nil {
		currentTask = *p.CurrentTaskID
	}
	if p.CurrentSubtaskID != nil {
		currentSubtask = *p.CurrentSubtaskID
	}
	if p.TaskStartTime != nil {
		taskStart = *p.TaskStartTime
	}
	if p.SubtaskStartTime != nil {
		subtaskStart = *p.SubtaskStartTime
	}
	m := entities.NewOrderedMap[any]()
	m.Set("current_task_id", currentTask)
	m.Set("current_subtask_id", currentSubtask)
	m.Set("task_start_time", taskStart)
	m.Set("subtask_start_time", subtaskStart)
	m.Set("completed_tasks", append([]int{}, p.CompletedTasks...))
	m.Set("completed_subtasks", append([]string{}, p.CompletedSubtasks...))
	m.Set("last_updated", p.LastUpdated)
	return m
}
