package common

import "agenthub/fastmcp/task_management/domain/entities"

// TaskProgressInfo is enhanced progress tracking for tasks.
type TaskProgressInfo struct {
	CurrentPhaseIndex    int
	TotalPhases          int
	CompletionPercentage float64
	EstimatedCompletion  *string
}

// ToDict mirrors asdict(self) (field declaration order).
func (p TaskProgressInfo) ToDict() *entities.OrderedMap[any] {
	var estimated any
	if p.EstimatedCompletion != nil {
		estimated = *p.EstimatedCompletion
	}
	m := entities.NewOrderedMap[any]()
	m.Set("current_phase_index", p.CurrentPhaseIndex)
	m.Set("total_phases", p.TotalPhases)
	m.Set("completion_percentage", p.CompletionPercentage)
	m.Set("estimated_completion", estimated)
	return m
}
