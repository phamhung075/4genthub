package services

import (
	"agenthub/fastmcp/task_management/domain/events"
	domainServices "agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// BranchStatisticsIntegrationService is the application service that integrates branch
// statistics with domain events (Python
// application/services/branch_statistics_integration_service.py). Logging is dropped.
type BranchStatisticsIntegrationService struct {
	bsiSvcBranchStatisticsService *domainServices.BranchStatisticsService
	bsiSvcEventDispatcher         *domainServices.EventDispatcher
	bsiSvcHandlersRegistered      bool
}

// NewBranchStatisticsIntegrationService mirrors __init__(task_repository,
// git_branch_repository). Python accepts any duck-typed repositories; the Go port
// asserts the BranchStatisticsService protocols when the service is built.
func NewBranchStatisticsIntegrationService(taskRepository, gitBranchRepository any) *BranchStatisticsIntegrationService {
	taskRepo, ok := taskRepository.(domainServices.TaskRepositoryProtocol)
	if !ok {
		panic(&value_objects.TypeError{Msg: "task_repository does not implement TaskRepositoryProtocol"})
	}
	gitBranchRepo, ok := gitBranchRepository.(domainServices.GitBranchRepositoryProtocol)
	if !ok {
		panic(&value_objects.TypeError{Msg: "git_branch_repository does not implement GitBranchRepositoryProtocol"})
	}
	return &BranchStatisticsIntegrationService{
		bsiSvcBranchStatisticsService: domainServices.NewBranchStatisticsService(taskRepo, gitBranchRepo),
		bsiSvcEventDispatcher:         domainServices.GetEventDispatcher(),
		bsiSvcHandlersRegistered:      false,
	}
}

// RegisterEventHandlers registers all event handlers for branch statistics updates.
func (s *BranchStatisticsIntegrationService) RegisterEventHandlers() {
	if s.bsiSvcHandlersRegistered {
		return
	}
	dispatcher := s.bsiSvcEventDispatcher

	dispatcher.RegisterHandler("task_created", domainServices.EventHandler{
		Name: "bsiSvc_handle_task_created",
		Fn:   func(eventData any) { s.bsiSvcHandleTaskCreated(eventData) },
	})
	dispatcher.RegisterHandler("task_updated", domainServices.EventHandler{
		Name: "bsiSvc_handle_task_updated",
		Fn:   func(eventData any) { s.bsiSvcHandleTaskUpdated(eventData) },
	})
	dispatcher.RegisterHandler("task_deleted", domainServices.EventHandler{
		Name: "bsiSvc_handle_task_deleted",
		Fn:   func(eventData any) { s.bsiSvcHandleTaskDeleted(eventData) },
	})
	dispatcher.RegisterHandler("task_status_changed", domainServices.EventHandler{
		Name: "bsiSvc_handle_task_status_changed",
		Fn:   func(eventData any) { s.bsiSvcHandleTaskStatusChanged(eventData) },
	})
	dispatcher.RegisterHandler("task_moved_to_branch", domainServices.EventHandler{
		Name: "bsiSvc_handle_task_moved_to_branch",
		Fn:   func(eventData any) { s.bsiSvcHandleTaskMovedToBranch(eventData) },
	})

	s.bsiSvcHandlersRegistered = true
}

// bsiSvcHandleTaskCreated handles task creation events. The Python handler catches
// Exception and logs; the dispatcher already swallows panics.
func (s *BranchStatisticsIntegrationService) bsiSvcHandleTaskCreated(eventData any) {
	event, ok := bsiSvcTaskCreatedEvent(eventData)
	if !ok {
		return
	}
	s.bsiSvcBranchStatisticsService.OnTaskCreated(bsiSvcIDString(event.TaskID), event.BranchID, event.Status)
}

func (s *BranchStatisticsIntegrationService) bsiSvcHandleTaskUpdated(eventData any) {
	event, ok := bsiSvcTaskUpdatedEvent(eventData)
	if !ok {
		return
	}
	var newBranchID *string
	if event.NewBranchID != nil && *event.NewBranchID != "" {
		newBranchID = event.NewBranchID
	} else {
		branchID := event.BranchID
		newBranchID = &branchID
	}
	s.bsiSvcBranchStatisticsService.OnTaskUpdated(
		bsiSvcIDString(event.TaskID),
		event.OldBranchID,
		newBranchID,
		bsiSvcStringOrEmpty(event.OldStatus),
		bsiSvcStringOrEmpty(event.NewStatus),
	)
}

func (s *BranchStatisticsIntegrationService) bsiSvcHandleTaskDeleted(eventData any) {
	event, ok := bsiSvcTaskDeletedEvent(eventData)
	if !ok {
		return
	}
	s.bsiSvcBranchStatisticsService.OnTaskDeleted(event.TaskID, event.BranchID, event.Status)
}

func (s *BranchStatisticsIntegrationService) bsiSvcHandleTaskStatusChanged(eventData any) {
	event, ok := bsiSvcTaskStatusChangedEvent(eventData)
	if !ok {
		return
	}
	branchID := event.BranchID
	s.bsiSvcBranchStatisticsService.OnTaskUpdated(
		event.TaskID,
		&branchID,
		&branchID,
		event.OldStatus,
		event.NewStatus,
	)
}

func (s *BranchStatisticsIntegrationService) bsiSvcHandleTaskMovedToBranch(eventData any) {
	event, ok := bsiSvcTaskMovedToBranchEvent(eventData)
	if !ok {
		return
	}
	oldBranchID := event.OldBranchID
	newBranchID := event.NewBranchID
	s.bsiSvcBranchStatisticsService.OnTaskUpdated(
		event.TaskID,
		&oldBranchID,
		&newBranchID,
		"",
		"",
	)
}

// RecalculateAllBranches recalculates statistics for all branches (project_id None
// means every branch).
func (s *BranchStatisticsIntegrationService) RecalculateAllBranches(projectID *string) (map[string]domainServices.BranchStatistics, error) {
	id := ""
	if projectID != nil {
		id = *projectID
	}
	return s.bsiSvcBranchStatisticsService.RecalculateAllBranches(id)
}

// bsiSvcIntegrationService is the singleton instance (Python _integration_service).
var bsiSvcIntegrationService *BranchStatisticsIntegrationService

// GetBranchStatisticsIntegrationService returns the singleton instance of the
// integration service, creating and initializing it on first use.
func GetBranchStatisticsIntegrationService(taskRepository, gitBranchRepository any) *BranchStatisticsIntegrationService {
	if bsiSvcIntegrationService == nil {
		bsiSvcIntegrationService = NewBranchStatisticsIntegrationService(taskRepository, gitBranchRepository)
		bsiSvcIntegrationService.RegisterEventHandlers()
	}
	return bsiSvcIntegrationService
}

// ---- event accessors ------------------------------------------------------------

func bsiSvcTaskCreatedEvent(eventData any) (events.TaskCreatedEvent, bool) {
	switch e := eventData.(type) {
	case events.TaskCreatedEvent:
		return e, true
	case *events.TaskCreatedEvent:
		if e != nil {
			return *e, true
		}
	}
	return events.TaskCreatedEvent{}, false
}

func bsiSvcTaskUpdatedEvent(eventData any) (events.TaskUpdatedEvent, bool) {
	switch e := eventData.(type) {
	case events.TaskUpdatedEvent:
		return e, true
	case *events.TaskUpdatedEvent:
		if e != nil {
			return *e, true
		}
	}
	return events.TaskUpdatedEvent{}, false
}

func bsiSvcTaskDeletedEvent(eventData any) (events.TaskDeletedEvent, bool) {
	switch e := eventData.(type) {
	case events.TaskDeletedEvent:
		return e, true
	case *events.TaskDeletedEvent:
		if e != nil {
			return *e, true
		}
	}
	return events.TaskDeletedEvent{}, false
}

func bsiSvcTaskStatusChangedEvent(eventData any) (events.TaskStatusChangedEvent, bool) {
	switch e := eventData.(type) {
	case events.TaskStatusChangedEvent:
		return e, true
	case *events.TaskStatusChangedEvent:
		if e != nil {
			return *e, true
		}
	}
	return events.TaskStatusChangedEvent{}, false
}

func bsiSvcTaskMovedToBranchEvent(eventData any) (events.TaskMovedToBranchEvent, bool) {
	switch e := eventData.(type) {
	case events.TaskMovedToBranchEvent:
		return e, true
	case *events.TaskMovedToBranchEvent:
		if e != nil {
			return *e, true
		}
	}
	return events.TaskMovedToBranchEvent{}, false
}

// bsiSvcIDString is str(task_id) for the event's id (a string or a value-object ID).
func bsiSvcIDString(v any) string {
	switch id := v.(type) {
	case string:
		return id
	case interface{ ToCanonicalFormat() string }:
		return id.ToCanonicalFormat()
	case interface{ String() string }:
		return id.String()
	}
	return value_objects.PyStr(v)
}

// bsiSvcStringOrEmpty dereferences an optional status string (None -> "").
func bsiSvcStringOrEmpty(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}
