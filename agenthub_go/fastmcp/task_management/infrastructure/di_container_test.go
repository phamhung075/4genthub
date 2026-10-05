package infrastructure

import "testing"

type diTestService struct{ Name string }

func TestDIContainerSingletonAndFactory(t *testing.T) {
	c := NewDIContainer()
	if c.Get("missing") != nil {
		t.Fatal("expected nil")
	}
	s := &diTestService{Name: "a"}
	c.RegisterSingleton("svc", s)
	if got := c.Get("svc"); got != s {
		t.Fatalf("got %v", got)
	}
	if !c.Has("svc") {
		t.Fatal("Has should be true")
	}

	calls := 0
	c.RegisterFactory("made", func() any { calls++; return &diTestService{Name: "made"} })
	first := c.Get("made")
	second := c.Get("made")
	if calls != 1 || first != second {
		t.Fatalf("factory calls=%d same=%v", calls, first == second)
	}
	c.RegisterFactory("made", func() any { return &diTestService{Name: "new"} })
	if got := c.Get("made").(*diTestService); got.Name != "new" {
		t.Fatalf("factory precedence: %v", got.Name)
	}
	if len(c.GetAllServices()) != 2 {
		t.Fatalf("services = %d", len(c.GetAllServices()))
	}
	c.Remove("svc")
	if c.Has("svc") {
		t.Fatal("Remove failed")
	}
}

func TestDIContainerInfrastructureInit(t *testing.T) {
	ResetEventBus()
	ResetNotificationService()
	c := NewDIContainer()
	path := "/tmp/events.db"
	c.InitializeInfrastructure(&path, nil)
	if c.GetEventBus() == nil || c.GetNotificationService() == nil || c.GetEventStore() == nil {
		t.Fatal("infrastructure not registered")
	}
}
