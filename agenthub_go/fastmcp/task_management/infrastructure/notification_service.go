// Package infrastructure ports task_management/infrastructure modules.
//
// notification_service.go ports notification_service.py: notification channels, an
// in-memory channel, a logging channel (logging is dropped), a file channel, and the
// NotificationService with retry and an unbounded async queue.
package infrastructure

import (
	"agenthub/fastmcp/utilities"
	"fmt"
	"os"
	"strconv"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// NotificationPriority is notification_service.NotificationPriority.
type NotificationPriority string

const (
	NotificationPriorityLow    NotificationPriority = "low"
	NotificationPriorityMedium NotificationPriority = "medium"
	NotificationPriorityHigh   NotificationPriority = "high"
	NotificationPriorityUrgent NotificationPriority = "urgent"
)

// NotificationPriorityValues lists the members in declaration order.
var NotificationPriorityValues = []NotificationPriority{NotificationPriorityLow, NotificationPriorityMedium, NotificationPriorityHigh, NotificationPriorityUrgent}

func (e NotificationPriority) String() string { return string(e) }

// ParseNotificationPriority mirrors NotificationPriority(value).
func ParseNotificationPriority(v string) (NotificationPriority, error) {
	for _, p := range NotificationPriorityValues {
		if string(p) == v {
			return p, nil
		}
	}
	return "", &value_objects.ValueError{Msg: fmt.Sprintf("'%s' is not a valid NotificationPriority", v)}
}

// NotificationType is notification_service.NotificationType.
type NotificationType string

const (
	NotificationTypeInfo                  NotificationType = "info"
	NotificationTypeWarning               NotificationType = "warning"
	NotificationTypeError                 NotificationType = "error"
	NotificationTypeSuccess               NotificationType = "success"
	NotificationTypeMilestoneReached      NotificationType = "milestone_reached"
	NotificationTypeProgressStalled       NotificationType = "progress_stalled"
	NotificationTypeTaskAssigned          NotificationType = "task_assigned"
	NotificationTypeTaskCompleted         NotificationType = "task_completed"
	NotificationTypeProgressTypeCompleted NotificationType = "progress_type_completed"
	NotificationTypeBlockerDetected       NotificationType = "blocker_detected"
	NotificationTypeAgentReassigned       NotificationType = "agent_reassigned"
)

// NotificationTypeValues lists the members in declaration order.
var NotificationTypeValues = []NotificationType{
	NotificationTypeInfo, NotificationTypeWarning, NotificationTypeError, NotificationTypeSuccess,
	NotificationTypeMilestoneReached, NotificationTypeProgressStalled, NotificationTypeTaskAssigned,
	NotificationTypeTaskCompleted, NotificationTypeProgressTypeCompleted, NotificationTypeBlockerDetected,
	NotificationTypeAgentReassigned,
}

func (e NotificationType) String() string { return string(e) }

// Notification is notification_service.Notification. Data and Metadata keep Python's
// insertion order (nil pointer = None).
type Notification struct {
	ID         string
	Type       string
	Title      string
	Message    string
	Data       *entities.OrderedMap[any]
	Priority   NotificationPriority
	Timestamp  time.Time
	Recipients []string
	Metadata   *entities.OrderedMap[any]
	RetryCount int
	MaxRetries int
}

// NotificationCallback is a registered in-memory callback. Python also accepts coroutine
// functions; Go functions are always synchronous.
type NotificationCallback func(notification *Notification)

// NotificationChannel is notification_service.NotificationChannel. Python's `async send`
// becomes a synchronous Send.
type NotificationChannel interface {
	Send(notification *Notification) (bool, error)
	SupportsType(notificationType string) bool
}

// InMemoryNotificationChannel is notification_service.InMemoryNotificationChannel.
// The mutex replaces the GIL that Python relied on: Send runs on the processing goroutine
// while callers read, register callbacks and clear.
type InMemoryNotificationChannel struct {
	mu            sync.Mutex
	Notifications []*Notification
	Callbacks     []NotificationCallback
}

func NewInMemoryNotificationChannel() *InMemoryNotificationChannel {
	return &InMemoryNotificationChannel{Notifications: []*Notification{}, Callbacks: []NotificationCallback{}}
}

func (c *InMemoryNotificationChannel) Send(n *Notification) (bool, error) {
	c.mu.Lock()
	c.Notifications = append(c.Notifications, n)
	callbacks := append([]NotificationCallback(nil), c.Callbacks...)
	c.mu.Unlock()
	for _, cb := range callbacks {
		// Python wraps each callback in try/except; Go callbacks cannot fail.
		cb(n)
	}
	return true, nil
}

func (c *InMemoryNotificationChannel) SupportsType(string) bool { return true }

func (c *InMemoryNotificationChannel) RegisterCallback(cb NotificationCallback) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Callbacks = append(c.Callbacks, cb)
}

// GetNotifications filters stored notifications; nil means no filter (Python None).
func (c *InMemoryNotificationChannel) GetNotifications(notificationType *string, priority *NotificationPriority) []*Notification {
	c.mu.Lock()
	out := append([]*Notification(nil), c.Notifications...)
	c.mu.Unlock()
	if notificationType != nil && *notificationType != "" {
		filtered := []*Notification{}
		for _, n := range out {
			if n.Type == *notificationType {
				filtered = append(filtered, n)
			}
		}
		out = filtered
	}
	if priority != nil {
		filtered := []*Notification{}
		for _, n := range out {
			if n.Priority == *priority {
				filtered = append(filtered, n)
			}
		}
		out = filtered
	}
	return out
}

func (c *InMemoryNotificationChannel) Clear() {
	c.mu.Lock()
	c.Notifications = []*Notification{}
	c.mu.Unlock()
}

// LoggingNotificationChannel is notification_service.LoggingNotificationChannel; the
// logging calls are dropped.
type LoggingNotificationChannel struct {
	LogLevel int
}

func NewLoggingNotificationChannel() *LoggingNotificationChannel {
	return &LoggingNotificationChannel{LogLevel: 20} // logging.INFO
}

func (c *LoggingNotificationChannel) Send(*Notification) (bool, error) { return true, nil }
func (c *LoggingNotificationChannel) SupportsType(string) bool         { return true }

// FileNotificationChannel is notification_service.FileNotificationChannel.
type FileNotificationChannel struct {
	FilePath string
}

func (c *FileNotificationChannel) SupportsType(string) bool { return true }

func (c *FileNotificationChannel) Send(n *Notification) (bool, error) {
	d := entities.NewOrderedMap[any]()
	d.Set("id", n.ID)
	d.Set("type", n.Type)
	d.Set("title", n.Title)
	d.Set("message", n.Message)
	d.Set("data", n.Data)
	d.Set("priority", string(n.Priority))
	d.Set("timestamp", value_objects.IsoFormat(n.Timestamp))
	d.Set("recipients", notifOptList(n.Recipients))
	d.Set("metadata", n.Metadata)
	line, err := value_objects.PyJSONDumps(d, -1)
	if err != nil {
		return false, err
	}
	f, err := os.OpenFile(c.FilePath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o666)
	if err != nil {
		return false, err
	}
	defer f.Close()
	if _, err := f.WriteString(line + "\n"); err != nil {
		return false, err
	}
	return true, nil
}

func notifOptList(v []string) any {
	if v == nil {
		return nil
	}
	return v
}

// notifQueue is an unbounded FIFO mirroring asyncio.Queue (put never blocks).
type notifQueue struct {
	mu     sync.Mutex
	cond   *sync.Cond
	items  []*Notification
	closed bool
}

func newNotifQueue() *notifQueue {
	q := &notifQueue{}
	q.cond = sync.NewCond(&q.mu)
	return q
}

func (q *notifQueue) put(n *Notification) {
	q.mu.Lock()
	q.items = append(q.items, n)
	q.cond.Signal()
	q.mu.Unlock()
}

func (q *notifQueue) get() *Notification {
	q.mu.Lock()
	defer q.mu.Unlock()
	for len(q.items) == 0 && !q.closed {
		q.cond.Wait()
	}
	if len(q.items) == 0 {
		return nil
	}
	n := q.items[0]
	q.items = q.items[1:]
	return n
}

func (q *notifQueue) qsize() int {
	q.mu.Lock()
	defer q.mu.Unlock()
	return len(q.items)
}

// notifProcessing tracks the background processing task.
type notifProcessing struct {
	done chan struct{}
}

func (p *notifProcessing) finished() bool {
	select {
	case <-p.done:
		return true
	default:
		return false
	}
}

// NotifyParams are the keyword arguments of NotificationService.notify.
type NotifyParams struct {
	Type       string
	Data       *entities.OrderedMap[any]
	Title      *string
	Message    *string
	Priority   *string
	Recipients []string
}

// NotificationService is notification_service.NotificationService.
type NotificationService struct {
	Channels []NotificationChannel

	queue      *notifQueue
	processing *notifProcessing
	shutdown   bool
	shutdownMu sync.Mutex

	// Sleep is injectable so retries do not wait in tests (Python asyncio.sleep).
	Sleep func(time.Duration)
}

// NewNotificationService applies the Python constructor: default in-memory and logging
// channels.
func NewNotificationService() *NotificationService {
	s := &NotificationService{
		Channels: []NotificationChannel{},
		queue:    newNotifQueue(),
		Sleep:    time.Sleep,
	}
	s.AddChannel(NewInMemoryNotificationChannel())
	s.AddChannel(NewLoggingNotificationChannel())
	return s
}

func (s *NotificationService) sleepFor(d time.Duration) {
	if s.Sleep != nil {
		s.Sleep(d)
	} else {
		time.Sleep(d)
	}
}

// AddChannel appends a channel.
func (s *NotificationService) AddChannel(channel NotificationChannel) {
	s.Channels = append(s.Channels, channel)
}

// RemoveChannel removes a channel (by identity, like Python's list.remove).
func (s *NotificationService) RemoveChannel(channel NotificationChannel) bool {
	for i, c := range s.Channels {
		if c == channel {
			s.Channels = append(s.Channels[:i], s.Channels[i+1:]...)
			return true
		}
	}
	return false
}

// Notify sends a notification and returns its id.
func (s *NotificationService) Notify(p NotifyParams) (string, error) {
	id := value_objects.NewUUIDv4()

	title := ""
	if p.Title != nil && *p.Title != "" {
		title = *p.Title
	} else {
		title = s.GenerateTitle(p.Type, p.Data)
	}

	message := ""
	if p.Message != nil && *p.Message != "" {
		message = *p.Message
	} else {
		m, err := s.GenerateMessage(p.Type, p.Data)
		if err != nil {
			return "", err
		}
		message = m
	}

	priority := "medium"
	if p.Priority != nil {
		priority = *p.Priority
	}
	prio, err := ParseNotificationPriority(priority)
	if err != nil {
		return "", err
	}

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("source", "notification_service")

	n := &Notification{
		ID:         id,
		Type:       p.Type,
		Title:      title,
		Message:    message,
		Data:       p.Data,
		Priority:   prio,
		Timestamp:  time.Now().UTC(),
		Recipients: p.Recipients,
		Metadata:   metadata,
		MaxRetries: 3,
	}
	s.sendNotification(n)
	return id, nil
}

// sendNotification delivers to every supporting channel, retrying when none succeed.
func (s *NotificationService) sendNotification(n *Notification) {
	sentCount := 0
	for _, channel := range s.Channels {
		if channel.SupportsType(n.Type) {
			success, err := channel.Send(n)
			if err == nil && success {
				sentCount++
			}
		}
	}
	if sentCount == 0 && n.RetryCount < n.MaxRetries {
		n.RetryCount++
		s.sleepFor(time.Duration(1<<uint(n.RetryCount)) * time.Second)
		s.sendNotification(n)
	}
}

// GenerateTitle mirrors _generate_title.
func (s *NotificationService) GenerateTitle(notifType string, _ *entities.OrderedMap[any]) string {
	titles := map[string]string{
		"milestone_reached":       "Milestone Reached",
		"progress_stalled":        "Progress Stalled",
		"task_assigned":           "Task Assigned",
		"task_completed":          "Task Completed",
		"progress_type_completed": "Progress Type Completed",
		"blocker_detected":        "Blocker Detected",
		"agent_reassigned":        "Agent Reassigned",
	}
	if t, ok := titles[notifType]; ok {
		return t
	}
	return "Notification: " + notifType
}

func notifGet(data *entities.OrderedMap[any], key string, def any) any {
	if data == nil {
		return def
	}
	if v, ok := data.Get(key); ok {
		return v
	}
	return def
}

// GenerateMessage mirrors _generate_message.
func (s *NotificationService) GenerateMessage(notifType string, data *entities.OrderedMap[any]) (string, error) {
	switch notifType {
	case "milestone_reached":
		return fmt.Sprintf("Milestone '%s' reached at %s%%",
			value_objects.PyStr(notifGet(data, "milestone", "Unknown")),
			value_objects.PyStr(notifGet(data, "progress", 0))), nil
	case "progress_stalled":
		hours, ok := value_objects.PyFloat(notifGet(data, "duration_hours", 0))
		if !ok {
			return "", &value_objects.TypeError{Msg: "unsupported format string passed to non-number"}
		}
		return fmt.Sprintf("No progress for %s hours at %s%%",
			strconv.FormatFloat(hours, 'f', 1, 64),
			value_objects.PyStr(notifGet(data, "current_progress", 0))), nil
	case "task_assigned":
		return fmt.Sprintf("Task %s assigned to %s",
			value_objects.PyStr(notifGet(data, "task_id", "Unknown")),
			value_objects.PyStr(notifGet(data, "assignee", "Unknown"))), nil
	case "task_completed":
		return fmt.Sprintf("Task %s completed", value_objects.PyStr(notifGet(data, "task_id", "Unknown"))), nil
	case "progress_type_completed":
		return fmt.Sprintf("Progress type %s completed", value_objects.PyStr(notifGet(data, "progress_type", "Unknown"))), nil
	case "blocker_detected":
		blockers := notifSequence(notifGet(data, "blockers", []any{}))
		parts := make([]string, 0, 3)
		for _, b := range blockers {
			if len(parts) == 3 {
				break
			}
			parts = append(parts, value_objects.PyStr(b))
		}
		return fmt.Sprintf("Detected %d blocker(s): %s", len(blockers), joinComma(parts)), nil
	case "agent_reassigned":
		return fmt.Sprintf("Agent %s reassigned from %s to %s",
			value_objects.PyStr(notifGet(data, "agent_id", "Unknown")),
			value_objects.PyStr(notifGet(data, "from", "N/A")),
			value_objects.PyStr(notifGet(data, "to", "N/A"))), nil
	default:
		text, err := value_objects.PyJSONDumps(data, -1)
		if err != nil {
			return "", err
		}
		return notifTruncate(text, 200), nil
	}
}

// notifSequence mirrors Python slicing over a list/str sequence.
func notifSequence(v any) []any {
	switch x := v.(type) {
	case nil:
		return []any{}
	case []any:
		return x
	case []string:
		out := make([]any, len(x))
		for i, s := range x {
			out[i] = s
		}
		return out
	case string:
		out := []any{}
		for _, r := range x {
			out = append(out, string(r))
		}
		return out
	}
	return []any{}
}

func joinComma(parts []string) string {
	out := ""
	for i, p := range parts {
		if i > 0 {
			out += ", "
		}
		out += p
	}
	return out
}

// notifTruncate mirrors Python text[:n] over code points.
func notifTruncate(s string, n int) string {
	r := []rune(s)
	if len(r) > n {
		return string(r[:n])
	}
	return s
}

// NotifyBatch sends multiple notifications and returns their ids.
func (s *NotificationService) NotifyBatch(notifications []NotifyParams) ([]string, error) {
	ids := []string{}
	for _, p := range notifications {
		id, err := s.Notify(p)
		if err != nil {
			return nil, err
		}
		ids = append(ids, id)
	}
	return ids, nil
}

// StartProcessing starts consuming the queue.
func (s *NotificationService) StartProcessing() {
	if s.processing != nil && !s.processing.finished() {
		return
	}
	s.shutdownMu.Lock()
	s.shutdown = false
	s.shutdownMu.Unlock()
	p := &notifProcessing{done: make(chan struct{})}
	s.processing = p
	go func() {
		defer close(p.done)
		for !s.isShutdown() {
			n := s.queue.get()
			if n == nil {
				break
			}
			// Python's loop catches Exception per notification
			utilities.SafeCall(func() { s.sendNotification(n) })
		}
	}()
}

// StopProcessing stops consuming the queue.
func (s *NotificationService) StopProcessing() {
	s.shutdownMu.Lock()
	s.shutdown = true
	s.shutdownMu.Unlock()
	if p := s.processing; p != nil && !p.finished() {
		s.queue.put(nil)
		<-p.done
	}
}

func (s *NotificationService) isShutdown() bool {
	s.shutdownMu.Lock()
	defer s.shutdownMu.Unlock()
	return s.shutdown
}

// QueueNotification queues a notification for async processing.
func (s *NotificationService) QueueNotification(n *Notification) { s.queue.put(n) }

// GetInMemoryNotifications returns the in-memory channel's notifications, if present.
func (s *NotificationService) GetInMemoryNotifications() []*Notification {
	for _, channel := range s.Channels {
		if c, ok := channel.(*InMemoryNotificationChannel); ok {
			return c.GetNotifications(nil, nil)
		}
	}
	return []*Notification{}
}

// ClearInMemoryNotifications clears the in-memory channel, if present.
func (s *NotificationService) ClearInMemoryNotifications() {
	for _, channel := range s.Channels {
		if c, ok := channel.(*InMemoryNotificationChannel); ok {
			c.Clear()
		}
	}
}

// Repr mirrors __repr__.
func (s *NotificationService) Repr() string {
	return fmt.Sprintf("NotificationService(channels=%d)", len(s.Channels))
}

var (
	globalNotificationMu      sync.Mutex
	globalNotificationService *NotificationService
)

// GetNotificationService is get_notification_service.
func GetNotificationService() *NotificationService {
	globalNotificationMu.Lock()
	defer globalNotificationMu.Unlock()
	if globalNotificationService == nil {
		globalNotificationService = NewNotificationService()
	}
	return globalNotificationService
}

// ResetNotificationService is reset_notification_service.
func ResetNotificationService() {
	globalNotificationMu.Lock()
	defer globalNotificationMu.Unlock()
	globalNotificationService = nil
}
