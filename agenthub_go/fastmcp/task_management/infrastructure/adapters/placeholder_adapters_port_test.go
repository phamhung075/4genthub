package adapters

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/interfaces"
)

func TestPlaceholderValidationServiceDefaults(t *testing.T) {
	svc := NewPlaceholderValidationService()
	if got := svc.Validate("thing", 1); !got.IsValid() || len(got.Errors()) != 0 {
		t.Fatalf("default validate = %+v, want valid with no errors", got)
	}
	if svc.UnregisterValidator("missing") {
		t.Fatal("unregister missing = true, want false")
	}
	if got := svc.ListValidators(); len(got) != 0 {
		t.Fatalf("validators = %v, want empty", got)
	}
	if got := svc.ValidateAll(map[string]any{"a": 1, "b": 2}); len(got) != 2 {
		t.Fatalf("validate_all size = %d, want 2", len(got))
	}
}

func TestPlaceholderValidationResultDetails(t *testing.T) {
	r := NewPlaceholderValidationResult(false, []string{"e1", "e2"}, nil)
	details := r.Details()
	if details["valid"] != false || details["error_count"] != 2 || details["warning_count"] != 0 {
		t.Fatalf("details = %v", details)
	}
}

func TestPlaceholderNotificationService(t *testing.T) {
	svc := &PlaceholderNotificationService{}
	n := svc.CreateNotification("email", "bob", "hi", nil)
	if n.NotificationType() != "email" || n.Recipient() != "bob" || n.Message() != "hi" {
		t.Fatalf("notification = %+v", n)
	}
	ok, err := svc.SendNotification(context.Background(), n)
	if !ok || err != nil {
		t.Fatalf("send = %v,%v want true,nil", ok, err)
	}
	results, _ := svc.SendBulkNotifications(context.Background(), []interfaces.INotification{n, n})
	if len(results) != 2 || !results[0] || !results[1] {
		t.Fatalf("bulk = %v", results)
	}
}

func TestPlaceholderMonitoringAndResolver(t *testing.T) {
	mon := &PlaceholderMonitoringService{}
	health := mon.GetHealthStatus()
	if health["status"] != "healthy" {
		t.Fatalf("status = %v", health["status"])
	}
	if got := mon.GetMetrics(nil); len(got) != 0 {
		t.Fatalf("metrics = %v", got)
	}
	res := &PlaceholderPathResolver{}
	if got := res.JoinPaths("a", "b", "c"); got != "a/b/c" {
		t.Fatalf("join = %q", got)
	}
	if got := res.GetParentDirectory("/a/b/c"); got != "/a/b" {
		t.Fatalf("parent = %q", got)
	}
}

func TestPlaceholderEventBus(t *testing.T) {
	bus := NewPlaceholderEventBus()
	if bus.IsRunning() {
		t.Fatal("bus should not be running")
	}
	_ = bus.Start(context.Background())
	if !bus.IsRunning() {
		t.Fatal("bus should be running")
	}
	_ = bus.Stop(context.Background())
	if bus.IsRunning() {
		t.Fatal("bus should be stopped")
	}
	if handlers := bus.GetHandlers("x"); len(handlers) != 0 {
		t.Fatalf("handlers = %v", handlers)
	}
}
