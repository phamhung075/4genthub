package use_cases

import (
	"context"
	"fmt"

	dtostask "agenthub/fastmcp/task_management/application/dtos/task"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/repositories"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// GetTaskContextService is the sync UnifiedContextFacade surface used by
// GetTaskUseCase when include_context is requested. The Python old-style async
// service branch is legacy and is not ported.
type GetTaskContextService interface {
	GetContext(ctx context.Context, level, contextID string, includeInherited bool) (*entities.OrderedMap[any], error)
}

// TaskProgressEventLister is the ledger as a response needs it for O1c's progress union: the events
// a task already has, oldest first. *repositories.TaskEventRepository satisfies it through Events,
// and the wiring passes the same repository the events route reads and the recorder writes.
type TaskProgressEventLister interface {
	Events(ctx context.Context, taskID string) ([]*entities.TaskEvent, error)
}

// GetTaskUseCase ports get_task.GetTaskUseCase.
type GetTaskUseCase struct {
	taskRepository      repositories.TaskRepository
	contextService      GetTaskContextService    // may be nil
	gitBranchRepository dtostask.GitBranchGetter // may be nil
	progressEvents      TaskProgressEventLister  // may be nil
}

// NewGetTaskUseCase builds the use case. progressEvents may be nil, and then the response's details
// is the column alone - the same contract the two dependencies above keep.
func NewGetTaskUseCase(taskRepository repositories.TaskRepository,
	contextService GetTaskContextService,
	gitBranchRepository dtostask.GitBranchGetter,
	progressEvents TaskProgressEventLister) *GetTaskUseCase {
	return &GetTaskUseCase{
		taskRepository:      taskRepository,
		contextService:      contextService,
		gitBranchRepository: gitBranchRepository,
		progressEvents:      progressEvents,
	}
}

// Execute retrieves a task and optionally context data.
func (uc *GetTaskUseCase) Execute(ctx context.Context, taskID string,
	forceFullGeneration bool, includeContext bool) (*dtostask.TaskResponse, error) {

	domainTaskID, err := value_objects.NewTaskId(taskID)
	if err != nil {
		return nil, err
	}
	task, err := uc.taskRepository.FindByID(ctx, domainTaskID)
	if err != nil {
		return nil, err
	}
	if task == nil {
		return nil, exceptions.NewTaskNotFoundError(fmt.Sprintf("Task with ID %s not found", taskID))
	}

	var contextData *entities.OrderedMap[any]
	if includeContext {
		contextData = uc.fetchContextData(ctx, taskID)
	}

	// O1c's union reads the ledger side of a task's progress here, once, and hands it to the response
	// builder: the notes written since the write switch, which details merges with the notes still in
	// the column. A nil lister leaves details exactly as the column renders it.
	var progressEvents []*entities.TaskEvent
	if uc.progressEvents != nil {
		events, err := uc.progressEvents.Events(ctx, taskID)
		if err != nil {
			return nil, err
		}
		progressEvents = events
	}

	return dtostask.TaskResponseFromDomain(ctx, task, uc.gitBranchRepository, progressEvents, contextData, nil, nil, nil)
}

// fetchContextData mirrors the dict-returning UnifiedContextFacade branch; every
// failure is swallowed and leaves the context absent.
func (uc *GetTaskUseCase) fetchContextData(ctx context.Context, taskID string) *entities.OrderedMap[any] {
	if uc.contextService == nil {
		return nil
	}
	response, err := uc.contextService.GetContext(ctx, "task", taskID, true)
	if err != nil || response == nil {
		return nil
	}
	success, _ := response.Get("success")
	if value_objects.PyTruthy(success) {
		if contextValue, ok := response.Get("context"); ok && value_objects.PyTruthy(contextValue) {
			return getTaskToOrderedMap(contextValue)
		}
		if dataValue, ok := response.Get("data"); ok && value_objects.PyTruthy(dataValue) {
			if dataMap := getTaskToOrderedMap(dataValue); dataMap != nil {
				if inner, ok := dataMap.Get("context_data"); ok {
					return getTaskToOrderedMap(inner)
				}
			}
			return getTaskToOrderedMap(dataValue)
		}
	}
	return nil
}

func getTaskToOrderedMap(v any) *entities.OrderedMap[any] {
	switch value := v.(type) {
	case nil:
		return nil
	case *entities.OrderedMap[any]:
		return value
	case *entities.TaskContext:
		return useCaseOrderedFromMap(value.ToDict(false), nil)
	case map[string]any:
		return useCaseOrderedFromMap(value, nil)
	}
	return nil
}
