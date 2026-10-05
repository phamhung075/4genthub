package use_cases

import (
	"time"

	"agenthub/fastmcp/connection_management/application/dtos"
	"agenthub/fastmcp/connection_management/domain/services"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

var connLastBroadcastKeys = []string{
	"last_broadcast_time", "last_broadcast_type", "broadcast_count", "error",
}

// RegisterStatusUpdatesUseCase is the use case for registering clients for status updates.
type RegisterStatusUpdatesUseCase struct {
	broadcastingService services.StatusBroadcastingService
}

// NewRegisterStatusUpdatesUseCase builds the use case.
func NewRegisterStatusUpdatesUseCase(broadcastingService services.StatusBroadcastingService) *RegisterStatusUpdatesUseCase {
	return &RegisterStatusUpdatesUseCase{broadcastingService: broadcastingService}
}

// Execute runs the register status updates use case.
func (u *RegisterStatusUpdatesUseCase) Execute(request *dtos.RegisterUpdatesRequest) (resp *dtos.RegisterUpdatesResponse) {
	defer func() {
		if r := recover(); r != nil {
			e := connErrString(r)
			resp = &dtos.RegisterUpdatesResponse{
				Success:    false,
				SessionID:  request.SessionID,
				Registered: false,
				UpdateInfo: tmentities.NewOrderedMap[any](),
				Error:      &e,
			}
		}
	}()

	// client_info = request.client_info or {}; then update in place (Python dict.update).
	clientInfo := request.ClientInfo
	if clientInfo == nil {
		clientInfo = tmentities.NewOrderedMap[any]()
	}
	clientInfo.Set("session_id", request.SessionID)
	clientInfo.Set("registered_at", tmvo.IsoFormatNaive(time.Now().Truncate(time.Microsecond)))

	statusUpdate, err := u.broadcastingService.RegisterClientForUpdates(request.SessionID, connMapFromOrdered(clientInfo))
	if err != nil {
		panic(err)
	}

	clientsCount := u.broadcastingService.GetRegisteredClientsCount()
	lastBroadcast := u.broadcastingService.GetLastBroadcastInfo()

	updateInfo := tmentities.NewOrderedMap[any]()
	updateInfo.Set("registered_clients", clientsCount)
	updateInfo.Set("last_broadcast", connOrderedFromMap(lastBroadcast, connLastBroadcastKeys))
	updateInfo.Set("registration_time", tmvo.IsoFormatNaive(statusUpdate.Timestamp))
	updateInfo.Set("event_type", statusUpdate.EventType)

	return &dtos.RegisterUpdatesResponse{
		Success:    true,
		SessionID:  request.SessionID,
		Registered: true,
		UpdateInfo: updateInfo,
	}
}

// connMapFromOrdered flattens an OrderedMap into a plain map for the boundary to the
// domain service (which stores map[string]any).
func connMapFromOrdered(m *tmentities.OrderedMap[any]) map[string]any {
	if m == nil {
		return map[string]any{}
	}
	out := make(map[string]any, m.Len())
	for _, k := range m.Keys() {
		v, _ := m.Get(k)
		out[k] = v
	}
	return out
}
