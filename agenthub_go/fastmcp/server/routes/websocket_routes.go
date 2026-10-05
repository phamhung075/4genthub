// websocket_routes.go ports server/routes/websocket_routes.py.
//
// The FastAPI APIRouter / Starlette WebSocket plumbing and the two endpoint
// receive loops have no Go meaning; the module-level state, retry/cleanup
// workers, persistence helpers, authorization checks and broadcast construction
// are ported with their key order and branches preserved.
//
// Missing Python dependencies are declared here as minimal interfaces (no Go
// port exists yet): MissedNotificationStore and OwnershipChecker.
package routes

import (
	"context"
	"errors"
	"math/rand"
	"os"
	"strings"
	"sync"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/server/metrics"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	wslib "agenthub/fastmcp/websocket"
)

// Retry / cleanup configuration constants.
const (
	RetryBaseDelaySeconds       = 5
	RetryBackoffMultiplier      = 2
	RetryMaxAttempts            = 3
	RetryQueueCheckIntervalSecs = 5
	NotificationCleanupInterval = 3600
	NotificationRetentionHours  = 24
)

// QueuedMessage mirrors the Python QueuedMessage dataclass.
type QueuedMessage struct {
	MessageID     string
	Message       *entities.OrderedMap[any]
	UserID        string
	Timestamp     time.Time
	RetryCount    int
	MaxRetries    int
	NextRetryTime time.Time
}

// WebSocketConnection mirrors the Python WebSocketConnection dataclass.
type WebSocketConnection struct {
	Websocket    wslib.WebSocket
	User         *authdomain.User
	ClientID     string
	Subscription *entities.OrderedMap[any]
	ConnectedAt  time.Time
	LastActivity time.Time
}

// UpdateActivity sets last_activity to now (UTC).
func (c *WebSocketConnection) UpdateActivity() { c.LastActivity = time.Now().UTC() }

// Global connection registry and per-user retry queues.
var (
	connectionsMu     sync.Mutex
	connections       = map[wslib.WebSocket]*WebSocketConnection{}
	messageQueueMu    sync.Mutex
	userMessageQueues = map[string][]*QueuedMessage{}
)

// RegisterConnection adds an accepted realtime socket to the broadcast registry. Without this the
// fan-out snapshot is always empty and every broadcast goes nowhere: the registry was previously
// written only by tests. The key is the socket itself, which is exactly what
// IsUserAuthorizedForMessage and the broadcast loop look up.
func RegisterConnection(ws wslib.WebSocket, user *authdomain.User, clientID string) {
	if ws == nil || user == nil {
		return
	}
	now := time.Now().UTC()
	connectionsMu.Lock()
	connections[ws] = &WebSocketConnection{
		Websocket:    ws,
		User:         user,
		ClientID:     clientID,
		Subscription: entities.NewOrderedMap[any](),
		ConnectedAt:  now,
		LastActivity: now,
	}
	connectionsMu.Unlock()
}

// UnregisterConnection removes a socket on every exit path. Deleting an unknown key is a no-op, so
// this cannot conflict with the broadcast's own cleanup of disconnected clients.
func UnregisterConnection(ws wslib.WebSocket) {
	if ws == nil {
		return
	}
	connectionsMu.Lock()
	delete(connections, ws)
	connectionsMu.Unlock()
}

// MissedNotification is the persisted replay record shape used by the helpers.
type MissedNotification struct {
	ID               string
	Message          *entities.OrderedMap[any]
	CreatedAt        time.Time
	DeliveryAttempts int
}

// MissedNotificationStore is the persistence port for the missed_notifications helpers.
// Python calls get_session()/MissedNotification directly; the Go repository lives in
// task_management/infrastructure/repositories/orm (`MissedNotificationRepository`) and httpapp
// assigns it to MissedStore at startup (`wireMissedNotificationStore`). The global stays a seam
// so tests can inject a fake; nil keeps Python's exception path.
type MissedNotificationStore interface {
	Store(ctx context.Context, userID string, message *entities.OrderedMap[any]) (string, error)
	Fetch(ctx context.Context, userID string, delivered bool, limit int) ([]*MissedNotification, error)
	MarkDelivered(ctx context.Context, notificationID string) (bool, error)
	IncrementDeliveryAttempts(ctx context.Context, notificationID string) (bool, error)
	CleanupExpired(ctx context.Context, olderThanHours int) (int, error)
}

// MissedStore is the injected missed-notification store; nil keeps Python's
// exception path (returns None / empty / false / 0).
var MissedStore MissedNotificationStore

// OwnershipChecker is the minimal DB port for resource ownership queries.
type OwnershipChecker interface {
	TaskOwnedBy(ctx context.Context, taskID, userID string) (bool, error)
	SubtaskParentOwnedBy(ctx context.Context, subtaskID, userID string) (bool, error)
	BranchOwnedBy(ctx context.Context, branchID, userID string) (bool, error)
	ProjectOwnedBy(ctx context.Context, projectID, userID string) (bool, error)
}

// Ownership is the injected ownership checker; nil behaves as not-found.
var Ownership OwnershipChecker

// wrGet reads an OrderedMap key, nil-safe.
func wrGet(m *entities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func wrStr(v any) string {
	s, _ := v.(string)
	return s
}

func wrRandInt(min, max int) int { return min + rand.Intn(max-min+1) }

// userID returns user.ID as a string ("" when absent).
func wrUserID(u *authdomain.User) string {
	if u == nil || u.ID == nil {
		return ""
	}
	return *u.ID
}

func wsClientHost(ws wslib.WebSocket) string {
	type clientInfo interface{ ClientHost() string }
	if c, ok := ws.(clientInfo); ok {
		return c.ClientHost()
	}
	return "unknown"
}

func wsClientPort(ws wslib.WebSocket) int {
	type clientPort interface{ ClientPort() int }
	if c, ok := ws.(clientPort); ok {
		return c.ClientPort()
	}
	return 0
}

// sendJSON mirrors websocket.send_json; errors are swallowed like the Python
// try/except around the error-notification sends.
func wrSendJSON(ctx context.Context, ws wslib.WebSocket, message *entities.OrderedMap[any]) error {
	data, err := value_objects.PyJSONDumpsCompact(message)
	if err != nil {
		return err
	}
	return ws.SendText(ctx, data)
}

// StoreMissedNotification mirrors store_missed_notification.
func StoreMissedNotification(ctx context.Context, userID string, message *entities.OrderedMap[any]) *string {
	if MissedStore == nil {
		return nil
	}
	id, err := MissedStore.Store(ctx, userID, message)
	if err != nil {
		return nil
	}
	return &id
}

// FetchMissedNotifications mirrors fetch_missed_notifications and its key order.
func FetchMissedNotifications(ctx context.Context, userID string, delivered bool, limit int) []*entities.OrderedMap[any] {
	result := []*entities.OrderedMap[any]{}
	if MissedStore == nil {
		return result
	}
	notifs, err := MissedStore.Fetch(ctx, userID, delivered, limit)
	if err != nil {
		return result
	}
	for _, n := range notifs {
		row := entities.NewOrderedMap[any]()
		row.Set("id", n.ID)
		row.Set("message", n.Message)
		row.Set("created_at", n.CreatedAt)
		row.Set("delivery_attempts", n.DeliveryAttempts)
		result = append(result, row)
	}
	return result
}

// MarkNotificationDelivered mirrors mark_notification_delivered.
func MarkNotificationDelivered(ctx context.Context, notificationID string) bool {
	if MissedStore == nil {
		return false
	}
	ok, err := MissedStore.MarkDelivered(ctx, notificationID)
	return err == nil && ok
}

// IncrementDeliveryAttempts mirrors increment_delivery_attempts.
func IncrementDeliveryAttempts(ctx context.Context, notificationID string) bool {
	if MissedStore == nil {
		return false
	}
	ok, err := MissedStore.IncrementDeliveryAttempts(ctx, notificationID)
	return err == nil && ok
}

// CleanupExpiredNotifications mirrors cleanup_expired_notifications.
func CleanupExpiredNotifications(ctx context.Context, olderThanHours int) int {
	if MissedStore == nil {
		return 0
	}
	n, err := MissedStore.CleanupExpired(ctx, olderThanHours)
	if err != nil {
		return 0
	}
	return n
}

// LogAuthorizationFailure builds the structured audit entry. Logging is dropped.
func LogAuthorizationFailure(websocket wslib.WebSocket, userID, entityType, entityID string, err error, failureReason string) {
	audit := entities.NewOrderedMap[any]()
	audit.Set("event", "authorization_failure")
	audit.Set("timestamp", time.Now().UTC().Format("2006-01-02T15:04:05.000000+00:00"))
	audit.Set("user_id", userID)
	audit.Set("entity_type", entityType)
	audit.Set("entity_id", entityID)
	audit.Set("failure_reason", failureReason)
	if err != nil {
		audit.Set("error_type", "Exception")
		audit.Set("error_message", err.Error())
	} else {
		audit.Set("error_type", "NoneType")
		audit.Set("error_message", "None")
	}
	conn := entities.NewOrderedMap[any]()
	conn.Set("client_host", wsClientHost(websocket))
	conn.Set("client_port", wsClientPort(websocket))
	audit.Set("connection_info", conn)
}

// CheckResourceOwnership mirrors _check_resource_ownership.
func CheckResourceOwnership(ctx context.Context, connectionUserID, entityType, entityID string, metadata *entities.OrderedMap[any]) bool {
	if Ownership != nil {
		var (
			owned bool
			err   error
		)
		switch entityType {
		case "task":
			owned, err = Ownership.TaskOwnedBy(ctx, entityID, connectionUserID)
		case "subtask":
			parentTaskID := wrStr(wrGet(metadata, "parent_task_id"))
			if parentTaskID != "" {
				owned, err = Ownership.TaskOwnedBy(ctx, parentTaskID, connectionUserID)
			} else {
				owned, err = Ownership.SubtaskParentOwnedBy(ctx, entityID, connectionUserID)
			}
		case "branch":
			owned, err = Ownership.BranchOwnedBy(ctx, entityID, connectionUserID)
		case "project":
			owned, err = Ownership.ProjectOwnedBy(ctx, entityID, connectionUserID)
		default:
			return false
		}
		if err == nil {
			return owned
		}
	}

	// Failure mode: development fails open, production fails closed.
	environment := strings.ToLower(wrEnv("ENVIRONMENT", "production"))
	return environment == "development"
}

// IsUserAuthorizedForMessage mirrors is_user_authorized_for_message.
func IsUserAuthorizedForMessage(ctx context.Context, websocket wslib.WebSocket, entityType, entityID, triggeringUserID string, metadata *entities.OrderedMap[any]) bool {
	connectionsMu.Lock()
	conn, ok := connections[websocket]
	connectionsMu.Unlock()
	if !ok {
		msg := entities.NewOrderedMap[any]()
		msg.Set("id", "auth-error-"+wrItoa(wrRandInt(100000, 999999)))
		msg.Set("version", "2.0")
		msg.Set("type", "error")
		msg.Set("timestamp", time.Now().UTC().Format("2006-01-02T15:04:05.000000+00:00"))
		msg.Set("sequence", wrRandInt(1000, 9999))
		payload := entities.NewOrderedMap[any]()
		payload.Set("entity", "system")
		payload.Set("action", "authorization_denied")
		data := entities.NewOrderedMap[any]()
		primary := entities.NewOrderedMap[any]()
		primary.Set("code", "NO_USER_CONTEXT")
		primary.Set("message", "WebSocket connection has no authenticated user")
		primary.Set("entity_type", entityType)
		primary.Set("entity_id", entityID)
		primary.Set("reason", "Connection not properly authenticated")
		data.Set("primary", primary)
		payload.Set("data", data)
		msg.Set("payload", payload)
		meta := entities.NewOrderedMap[any]()
		meta.Set("source", "system")
		meta.Set("severity", "error")
		msg.Set("metadata", meta)
		_ = wrSendJSON(ctx, websocket, msg)
		return false
	}

	connectionUserID := wrUserID(conn.User)

	// Rule 1: users always receive messages about their own actions.
	if connectionUserID == triggeringUserID {
		return true
	}

	// Rule 2: system messages check the real resource owner.
	if triggeringUserID == "system" {
		return CheckResourceOwnership(ctx, connectionUserID, entityType, entityID, metadata)
	}

	// Rule 3: entity-specific ownership.
	if Ownership != nil {
		var (
			owned bool
			err   error
		)
		switch entityType {
		case "task":
			owned, err = Ownership.TaskOwnedBy(ctx, entityID, connectionUserID)
		case "subtask":
			parentTaskID := wrStr(wrGet(metadata, "parent_task_id"))
			if parentTaskID != "" {
				owned, err = Ownership.TaskOwnedBy(ctx, parentTaskID, connectionUserID)
			}
		case "branch":
			owned, err = Ownership.BranchOwnedBy(ctx, entityID, connectionUserID)
		case "project":
			owned, err = Ownership.ProjectOwnedBy(ctx, entityID, connectionUserID)
		}
		if err == nil && owned {
			return true
		}
	}

	// Default: deny and notify the frontend.
	msg := entities.NewOrderedMap[any]()
	msg.Set("id", "auth-error-"+wrItoa(wrRandInt(100000, 999999)))
	msg.Set("version", "2.0")
	msg.Set("type", "error")
	msg.Set("timestamp", time.Now().UTC().Format("2006-01-02T15:04:05.000000+00:00"))
	msg.Set("sequence", wrRandInt(1000, 9999))
	payload := entities.NewOrderedMap[any]()
	payload.Set("entity", "system")
	payload.Set("action", "authorization_denied")
	data := entities.NewOrderedMap[any]()
	primary := entities.NewOrderedMap[any]()
	primary.Set("code", "NOT_AUTHORIZED")
	primary.Set("message", "You don't have access to this "+entityType)
	primary.Set("entity_type", entityType)
	primary.Set("entity_id", entityID)
	primary.Set("reason", "No authorization rules matched for this resource")
	data.Set("primary", primary)
	payload.Set("data", data)
	msg.Set("payload", payload)
	meta := entities.NewOrderedMap[any]()
	meta.Set("source", "system")
	meta.Set("userId", connectionUserID)
	meta.Set("severity", "warning")
	msg.Set("metadata", meta)
	_ = wrSendJSON(ctx, websocket, msg)
	return false
}

// BroadcastDataChange mirrors the Python broadcast_data_change. It satisfies the
// websocket_notification_service Broker interface.
func BroadcastDataChange(ctx context.Context, eventType, entityType, entityID, userID string, data any, metadata *entities.OrderedMap[any]) error {
	userTriggered := map[string]bool{
		"created": true, "updated": true, "deleted": true,
		"completed": true, "assigned": true, "unassigned": true,
	}
	source := "system"
	if userTriggered[eventType] {
		source = "user"
	}

	message := entities.NewOrderedMap[any]()
	message.Set("id", "broadcast-"+entityType+"-"+wrItoa(wrRandInt(100000, 999999)))
	message.Set("version", "2.0")
	message.Set("type", "update")
	message.Set("timestamp", time.Now().UTC().Format("2006-01-02T15:04:05.000000+00:00"))
	message.Set("sequence", wrRandInt(1000, 9999))
	payload := entities.NewOrderedMap[any]()
	payload.Set("entity", entityType)
	payload.Set("action", eventType)
	pdata := entities.NewOrderedMap[any]()
	if data != nil {
		pdata.Set("primary", data)
	} else {
		pdata.Set("primary", nil)
	}
	payload.Set("data", pdata)
	message.Set("payload", payload)

	meta := entities.NewOrderedMap[any]()
	meta.Set("source", source)
	meta.Set("userId", userID)
	meta.Set("entity_type", entityType)
	meta.Set("entity_id", entityID)
	meta.Set("event_type", eventType)
	if metadata != nil {
		for _, k := range metadata.Keys() {
			v, _ := metadata.Get(k)
			meta.Set(k, v)
		}
	}
	message.Set("metadata", meta)

	// Move cascade data from metadata to payload.data.
	if metadata != nil {
		if cascade, ok := metadata.Get("cascade"); ok {
			pdata.Set("cascade", cascade)
			meta.Delete("cascade")
		}
	}

	disconnected := []wslib.WebSocket{}
	authorizedClients := 0
	totalConnections := 0

	done := metrics.TrackBroadcastDuration(eventType, entityType)
	defer done()

	connectionsMu.Lock()
	snapshot := make([]*WebSocketConnection, 0, len(connections))
	for _, c := range connections {
		snapshot = append(snapshot, c)
	}
	totalConnections = len(snapshot)
	connectionsMu.Unlock()

	for _, connection := range snapshot {
		ws := connection.Websocket
		connectionUser := connection.User
		connectionUserID := wrUserID(connectionUser)

		authorized := IsUserAuthorizedForMessage(ctx, ws, entityType, entityID, userID, metadata)
		if authorized {
			messageID, _ := message.Get("id")
			fullID := wrStr(messageID) + "-" + connectionUserID
			queued := &QueuedMessage{
				MessageID:     fullID,
				Message:       message.Copy(),
				UserID:        connectionUserID,
				Timestamp:     time.Now().UTC(),
				RetryCount:    0,
				MaxRetries:    RetryMaxAttempts,
				NextRetryTime: time.Now().UTC(),
			}
			messageQueueMu.Lock()
			userMessageQueues[connectionUserID] = append(userMessageQueues[connectionUserID], queued)
			messageQueueMu.Unlock()

			err := wrSendJSON(ctx, ws, message)
			if err == nil {
				authorizedClients++
				messageQueueMu.Lock()
				kept := userMessageQueues[connectionUserID][:0]
				for _, m := range userMessageQueues[connectionUserID] {
					if m.MessageID != fullID {
						kept = append(kept, m)
					}
				}
				userMessageQueues[connectionUserID] = kept
				messageQueueMu.Unlock()
				continue
			}
			if wslib.IsWebSocketDisconnect(err) {
				disconnected = append(disconnected, ws)
				continue
			}
			// Failed: bump retry info with exponential backoff.
			messageQueueMu.Lock()
			for _, m := range userMessageQueues[connectionUserID] {
				if m.MessageID == fullID {
					m.RetryCount++
					delay := float64(RetryBaseDelaySeconds) * wrPow(RetryBackoffMultiplier, m.RetryCount-1)
					m.NextRetryTime = time.Now().UTC().Add(time.Duration(delay * float64(time.Second)))
				}
			}
			messageQueueMu.Unlock()
			disconnected = append(disconnected, ws)
		} else {
			blocked := entities.NewOrderedMap[any]()
			blocked.Set("id", "auth-blocked-"+wrItoa(wrRandInt(100000, 999999)))
			blocked.Set("version", "2.0")
			blocked.Set("type", "error")
			blocked.Set("timestamp", time.Now().UTC().Format("2006-01-02T15:04:05.000000+00:00"))
			blocked.Set("sequence", wrRandInt(1000, 9999))
			bp := entities.NewOrderedMap[any]()
			bp.Set("entity", "system")
			bp.Set("action", "notification_blocked")
			bd := entities.NewOrderedMap[any]()
			bprim := entities.NewOrderedMap[any]()
			bprim.Set("code", "NOT_AUTHORIZED")
			bprim.Set("message", "Notification blocked: You don't have access to this "+entityType)
			bprim.Set("entity_type", entityType)
			bprim.Set("entity_id", entityID)
			bprim.Set("event_type", eventType)
			bprim.Set("reason", "Authorization check failed")
			bd.Set("primary", bprim)
			bp.Set("data", bd)
			blocked.Set("payload", bp)
			bm := entities.NewOrderedMap[any]()
			bm.Set("source", "system")
			bm.Set("userId", connectionUserID)
			bm.Set("severity", "info")
			blocked.Set("metadata", bm)
			_ = wrSendJSON(ctx, ws, blocked)
		}
	}

	// Store missed notifications for offline target users.
	targetUserIDs := map[string]bool{}
	if userID != "" {
		targetUserIDs[userID] = true
	}
	if metadata != nil {
		if v, ok := metadata.Get("user_ids"); ok {
			if list, ok := v.([]any); ok {
				for _, id := range list {
					if s, ok := id.(string); ok {
						targetUserIDs[s] = true
					}
				}
			} else if list, ok := v.([]string); ok {
				for _, id := range list {
					targetUserIDs[id] = true
				}
			}
		} else if v, ok := metadata.Get("user_id"); ok {
			if s, ok := v.(string); ok {
				targetUserIDs[s] = true
			}
		}
	}

	connectionsMu.Lock()
	connectedUserIDs := map[string]bool{}
	for _, c := range connections {
		connectedUserIDs[wrUserID(c.User)] = true
	}
	connectionsMu.Unlock()

	for offlineUserID := range targetUserIDs {
		if connectedUserIDs[offlineUserID] {
			continue
		}
		StoreMissedNotification(ctx, offlineUserID, message)
	}

	// Clean up disconnected clients.
	connectionsMu.Lock()
	for _, ws := range disconnected {
		delete(connections, ws)
	}
	connectionsMu.Unlock()

	_ = totalConnections
	_ = authorizedClients
	return nil
}

// ProcessMessageRetryQueue mirrors process_message_retry_queue.
func ProcessMessageRetryQueue(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-time.After(time.Duration(RetryQueueCheckIntervalSecs) * time.Second):
		}
		currentTime := time.Now().UTC()

		messageQueueMu.Lock()
		for userID, queue := range userMessageQueues {
			metrics.UpdateQueueSize(userID, len(queue))
			toRemove := []*QueuedMessage{}
			for _, queuedMsg := range queue {
				if queuedMsg.RetryCount >= queuedMsg.MaxRetries {
					metrics.RecordRetryAttempt(false, queuedMsg.RetryCount)
					metrics.RecordDeliveryTime("failed", currentTime.Sub(queuedMsg.Timestamp).Seconds())
					toRemove = append(toRemove, queuedMsg)
					continue
				}
				if !currentTime.After(queuedMsg.NextRetryTime) && !currentTime.Equal(queuedMsg.NextRetryTime) {
					continue
				}
				connectionsMu.Lock()
				targets := []wslib.WebSocket{}
				for _, connection := range connections {
					if wrUserID(connection.User) == userID {
						targets = append(targets, connection.Websocket)
					}
				}
				connectionsMu.Unlock()
				if len(targets) == 0 {
					queuedMsg.RetryCount++
					delay := float64(RetryBaseDelaySeconds) * wrPow(RetryBackoffMultiplier, queuedMsg.RetryCount-1)
					queuedMsg.NextRetryTime = currentTime.Add(time.Duration(delay * float64(time.Second)))
					continue
				}
				delivered := false
				for _, ws := range targets {
					if err := wrSendJSON(ctx, ws, queuedMsg.Message); err == nil {
						delivered = true
						break
					}
				}
				if delivered {
					metrics.RecordRetryAttempt(true, queuedMsg.RetryCount+1)
					metrics.RecordDeliveryTime("retry", currentTime.Sub(queuedMsg.Timestamp).Seconds())
					toRemove = append(toRemove, queuedMsg)
				} else {
					queuedMsg.RetryCount++
					delay := float64(RetryBaseDelaySeconds) * wrPow(RetryBackoffMultiplier, queuedMsg.RetryCount-1)
					queuedMsg.NextRetryTime = currentTime.Add(time.Duration(delay * float64(time.Second)))
				}
			}
			for _, msg := range toRemove {
				for i, m := range queue {
					if m == msg {
						queue = append(queue[:i], queue[i+1:]...)
						break
					}
				}
			}
			if len(queue) == 0 {
				delete(userMessageQueues, userID)
				metrics.ClearQueueMetrics(userID)
			} else {
				userMessageQueues[userID] = queue
			}
		}
		messageQueueMu.Unlock()
	}
}

var (
	retryQueueCancel context.CancelFunc
	retryQueueMu     sync.Mutex
)

// StartRetryQueueProcessor mirrors start_retry_queue_processor.
func StartRetryQueueProcessor(ctx context.Context) {
	retryQueueMu.Lock()
	defer retryQueueMu.Unlock()
	if retryQueueCancel != nil {
		return
	}
	workerCtx, cancel := context.WithCancel(ctx)
	retryQueueCancel = cancel
	go ProcessMessageRetryQueue(workerCtx)
}

// StopRetryQueueProcessor mirrors stop_retry_queue_processor.
func StopRetryQueueProcessor() {
	retryQueueMu.Lock()
	defer retryQueueMu.Unlock()
	if retryQueueCancel != nil {
		retryQueueCancel()
		retryQueueCancel = nil
	}
}

// ProcessNotificationCleanup mirrors process_notification_cleanup.
func ProcessNotificationCleanup(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-time.After(time.Duration(NotificationCleanupInterval) * time.Second):
		}
		CleanupExpiredNotifications(ctx, NotificationRetentionHours)
	}
}

var (
	cleanupCancel context.CancelFunc
	cleanupMu     sync.Mutex
)

// StartNotificationCleanupTask mirrors start_notification_cleanup_task.
func StartNotificationCleanupTask(ctx context.Context) {
	cleanupMu.Lock()
	defer cleanupMu.Unlock()
	if cleanupCancel != nil {
		return
	}
	workerCtx, cancel := context.WithCancel(ctx)
	cleanupCancel = cancel
	go ProcessNotificationCleanup(workerCtx)
}

// StopNotificationCleanupTask mirrors stop_notification_cleanup_task.
func StopNotificationCleanupTask() {
	cleanupMu.Lock()
	defer cleanupMu.Unlock()
	if cleanupCancel != nil {
		cleanupCancel()
		cleanupCancel = nil
	}
}

func wrItoa(n int) string {
	return value_objects.PyStr(n)
}

func wrPow(base, exp int) float64 {
	if exp <= 0 {
		return 1
	}
	result := 1.0
	for i := 0; i < exp; i++ {
		result *= float64(base)
	}
	return result
}

func wrEnv(name, def string) string {
	if v, ok := os.LookupEnv(name); ok {
		return v
	}
	return def
}

// Ensure the injected interfaces are referenced even when nil.
var _ = errors.New
