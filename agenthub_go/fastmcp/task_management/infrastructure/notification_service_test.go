package infrastructure

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func om(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func TestNotificationTitleAndMessage(t *testing.T) {
	s := NewNotificationService()

	if got := s.GenerateTitle("milestone_reached", nil); got != "Milestone Reached" {
		t.Fatalf("title = %q", got)
	}
	if got := s.GenerateTitle("weird", nil); got != "Notification: weird" {
		t.Fatalf("title = %q", got)
	}

	cases := []struct {
		typ  string
		data *entities.OrderedMap[any]
		want string
	}{
		{"milestone_reached", om("milestone", "M1", "progress", 75), "Milestone 'M1' reached at 75%"},
		{"progress_stalled", om("duration_hours", 2.5, "current_progress", 30), "No progress for 2.5 hours at 30%"},
		{"task_assigned", om("task_id", "T1", "assignee", "bob"), "Task T1 assigned to bob"},
		{"task_completed", om("task_id", "T1"), "Task T1 completed"},
		{"progress_type_completed", om("progress_type", "planning"), "Progress type planning completed"},
		{"blocker_detected", om("blockers", []any{"a", "b", "c", "d"}), "Detected 4 blocker(s): a, b, c"},
		{"agent_reassigned", om("agent_id", "A1", "from", "x", "to", "y"), "Agent A1 reassigned from x to y"},
		{"unknown_type", om("x", 1), `{"x": 1}`},
	}
	for _, c := range cases {
		got, err := s.GenerateMessage(c.typ, c.data)
		if err != nil {
			t.Fatalf("%s: unexpected error %v", c.typ, err)
		}
		if got != c.want {
			t.Fatalf("%s: got %q want %q", c.typ, got, c.want)
		}
	}
}

func TestNotificationNotifyAndParse(t *testing.T) {
	s := NewNotificationService()
	priority := "high"
	id, err := s.Notify(NotifyParams{Type: "task_assigned", Data: om("task_id", "T1", "assignee", "bob"), Priority: &priority})
	if err != nil {
		t.Fatal(err)
	}
	if id == "" {
		t.Fatal("empty id")
	}

	notes := s.GetInMemoryNotifications()
	if len(notes) != 1 {
		t.Fatalf("stored %d notifications", len(notes))
	}
	n := notes[0]
	if n.Title != "Task Assigned" || n.Message != "Task T1 assigned to bob" {
		t.Fatalf("unexpected title/message: %q / %q", n.Title, n.Message)
	}
	if n.Priority != NotificationPriorityHigh {
		t.Fatalf("priority = %q", n.Priority)
	}
	if n.MaxRetries != 3 || n.RetryCount != 0 {
		t.Fatalf("retries = %d/%d", n.RetryCount, n.MaxRetries)
	}
	if n.Metadata == nil {
		t.Fatal("metadata is nil")
	}
	if v, _ := n.Metadata.Get("source"); v != "notification_service" {
		t.Fatalf("metadata source = %v", v)
	}

	if _, err := ParseNotificationPriority("bogus"); err == nil || err.Error() != "'bogus' is not a valid NotificationPriority" {
		t.Fatalf("parse error = %v", err)
	}
	if _, err := s.Notify(NotifyParams{Type: "info", Data: om(), Priority: strPtr("bogus")}); err == nil {
		t.Fatal("expected invalid priority error")
	}
}

func strPtr(s string) *string { return &s }

func TestNotificationRetryBackoff(t *testing.T) {
	s := NewNotificationService()
	s.Channels = []NotificationChannel{} // no successful channel
	var slept []time.Duration
	s.Sleep = func(d time.Duration) { slept = append(slept, d) }

	if _, err := s.Notify(NotifyParams{Type: "info", Data: om()}); err != nil {
		t.Fatal(err)
	}
	want := []time.Duration{2 * time.Second, 4 * time.Second, 8 * time.Second}
	if len(slept) != len(want) {
		t.Fatalf("slept = %v", slept)
	}
	for i := range want {
		if slept[i] != want[i] {
			t.Fatalf("slept = %v want %v", slept, want)
		}
	}
}

func TestNotificationFileChannel(t *testing.T) {
	path := filepath.Join(t.TempDir(), "notifications.log")
	ch := &FileNotificationChannel{FilePath: path}
	ts := time.Date(2024, 1, 2, 3, 4, 5, 0, time.UTC)
	n := &Notification{
		ID: "id-1", Type: "info", Title: "T", Message: "M", Data: om("a", 1),
		Priority: NotificationPriorityLow, Timestamp: ts,
		Metadata: om("source", "notification_service"),
	}
	ok, err := ch.Send(n)
	if err != nil || !ok {
		t.Fatalf("send = %v, %v", ok, err)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	want := `{"id": "id-1", "type": "info", "title": "T", "message": "M", "data": {"a": 1}, "priority": "low", "timestamp": "2024-01-02T03:04:05+00:00", "recipients": null, "metadata": {"source": "notification_service"}}` + "\n"
	if string(data) != want {
		t.Fatalf("file = %q want %q", string(data), want)
	}
}

func TestNotificationQueueProcessing(t *testing.T) {
	s := NewNotificationService()
	s.StartProcessing()
	defer s.StopProcessing()

	s.QueueNotification(&Notification{ID: "q1", Type: "info", Title: "T", Message: "M", Priority: NotificationPriorityLow, Timestamp: time.Now().UTC()})

	deadline := time.Now().Add(2 * time.Second)
	for {
		if len(s.GetInMemoryNotifications()) == 1 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("queued notification was not processed")
		}
		time.Sleep(time.Millisecond)
	}
	if s.Repr() != "NotificationService(channels=2)" {
		t.Fatalf("repr = %q", s.Repr())
	}
}

func TestNotificationRemoveAndFilter(t *testing.T) {
	s := NewNotificationService()
	mem := NewInMemoryNotificationChannel()
	mem.Send(&Notification{ID: "1", Type: "info", Priority: NotificationPriorityLow})
	mem.Send(&Notification{ID: "2", Type: "error", Priority: NotificationPriorityHigh})
	low := NotificationPriorityLow
	got := mem.GetNotifications(nil, &low)
	if len(got) != 1 || got[0].ID != "1" {
		t.Fatalf("filter = %v", got)
	}
	typ := "error"
	if got := mem.GetNotifications(&typ, nil); len(got) != 1 || got[0].ID != "2" {
		t.Fatalf("type filter = %v", got)
	}

	if !s.RemoveChannel(s.Channels[0]) {
		t.Fatal("remove failed")
	}
	if s.RemoveChannel(NewLoggingNotificationChannel()) {
		t.Fatal("removed a channel that is not present")
	}
	if len(s.Channels) != 1 {
		t.Fatalf("channels = %d", len(s.Channels))
	}
}

func TestNotificationCallbackAndBatch(t *testing.T) {
	s := NewNotificationService()
	mem := s.Channels[0].(*InMemoryNotificationChannel)
	var seen []string
	mem.RegisterCallback(func(n *Notification) { seen = append(seen, n.ID) })

	ids, err := s.NotifyBatch([]NotifyParams{
		{Type: "info", Data: om(), Title: strPtr("a"), Message: strPtr("m")},
		{Type: "info", Data: om(), Title: strPtr("b"), Message: strPtr("m")},
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(ids) != 2 || len(seen) != 2 {
		t.Fatalf("ids=%v seen=%v", ids, seen)
	}
	if strings.Join(seen, ",") != strings.Join(ids, ",") {
		t.Fatalf("callback order mismatch: %v vs %v", seen, ids)
	}

	s.ClearInMemoryNotifications()
	if len(s.GetInMemoryNotifications()) != 0 {
		t.Fatal("clear did not clear")
	}
}
