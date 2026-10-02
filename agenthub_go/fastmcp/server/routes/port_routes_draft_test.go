package routes

import (
	"context"
	"testing"

	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
)

type portFakeUser struct{ id string }

func newPortUser(id string) *authdomain.User { return &authdomain.User{ID: &id} }

type portCtxController struct {
	lastContextID  string
	lastLevel      string
	lastIncludeInh bool
	success        bool
	errText        *string
}

func (c *portCtxController) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string) (ControllerResult, error) {
	c.lastLevel, c.lastContextID = level, contextID
	return ControllerResult{Success: c.success, Error: c.errText, Body: entities.NewOrderedMap[any]()}, nil
}
func (c *portCtxController) GetContext(ctx context.Context, level, contextID string, includeInherited bool, userID string) (ControllerResult, error) {
	c.lastLevel, c.lastContextID, c.lastIncludeInh = level, contextID, includeInherited
	return ControllerResult{Success: c.success, Error: c.errText, Body: entities.NewOrderedMap[any]()}, nil
}
func (c *portCtxController) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string) (ControllerResult, error) {
	return ControllerResult{Success: c.success, Error: c.errText}, nil
}
func (c *portCtxController) DeleteContext(ctx context.Context, level, contextID string, userID string) (ControllerResult, error) {
	return ControllerResult{Success: c.success, Error: c.errText}, nil
}
func (c *portCtxController) ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool, userID string) (ControllerResult, error) {
	return ControllerResult{Success: c.success, Error: c.errText}, nil
}

func TestPortCreateContextGlobalMeUsesUserID(t *testing.T) {
	c := &portCtxController{success: true}
	u := newPortUser("user-123")
	_, err := CreateContext(context.Background(), "global", ContextCreateRequest{ContextID: "me"}, u, c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.lastContextID != "user-123" {
		t.Fatalf("context_id = %q, want user-123", c.lastContextID)
	}
}

func TestPortGetContextGlobalIgnoresParam(t *testing.T) {
	c := &portCtxController{success: true}
	u := newPortUser("user-9")
	_, err := GetContext(context.Background(), "global", "someone-else", false, true, u, c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if c.lastContextID != "user-9" {
		t.Fatalf("context_id = %q, want user-9", c.lastContextID)
	}
}

func TestPortListContextsInvalidFiltersJSON(t *testing.T) {
	c := &portCtxController{}
	bad := "{not json"
	_, err := ListContexts(context.Background(), "global", &bad, newPortUser("u"), c)
	if err == nil {
		t.Fatal("expected error")
	}
	he, ok := err.(*auth.HTTPException)
	if !ok {
		t.Fatalf("error type = %T, want *auth.HTTPException", err)
	}
	if he.StatusCode != 400 {
		t.Fatalf("status = %d, want 400", he.StatusCode)
	}
}

type portSubController struct {
	updateKeys []string
}

func (c *portSubController) CreateSubtask(ctx context.Context, taskID, title string, description *string, userID string) (ControllerResult, error) {
	return ControllerResult{Success: true}, nil
}
func (c *portSubController) GetSubtask(ctx context.Context, subtaskID, userID string) (ControllerResult, error) {
	return ControllerResult{Success: true}, nil
}
func (c *portSubController) UpdateSubtask(ctx context.Context, subtaskID string, updateData *entities.OrderedMap[any], userID string) (ControllerResult, error) {
	c.updateKeys = updateData.Keys()
	return ControllerResult{Success: true}, nil
}
func (c *portSubController) DeleteSubtask(ctx context.Context, subtaskID, userID string) (ControllerResult, error) {
	return ControllerResult{Success: true}, nil
}
func (c *portSubController) ListSubtasks(ctx context.Context, taskID, userID string) (ControllerResult, error) {
	return ControllerResult{Success: true}, nil
}
func (c *portSubController) CompleteSubtask(ctx context.Context, subtaskID string, completionSummary *string, userID string) (ControllerResult, error) {
	return ControllerResult{Success: true}, nil
}

func TestPortUpdateSubtaskKeyOrder(t *testing.T) {
	c := &portSubController{}
	title := "t"
	status := "in_progress"
	progress := 40
	_, err := UpdateSubtask(context.Background(), "s1", &title, nil, &status, &progress, newPortUser("u"), c)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	want := []string{"title", "status", "progress_percentage"}
	if len(c.updateKeys) != len(want) {
		t.Fatalf("keys = %v, want %v", c.updateKeys, want)
	}
	for i := range want {
		if c.updateKeys[i] != want[i] {
			t.Fatalf("keys = %v, want %v", c.updateKeys, want)
		}
	}
}

func TestPortPerformanceTimeseriesShape(t *testing.T) {
	out, err := GetPerformanceTimeseries(1, "15m")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	wantKeys := []string{"interval", "hours", "data_points", "note"}
	gotKeys := out.Keys()
	for i := range wantKeys {
		if gotKeys[i] != wantKeys[i] {
			t.Fatalf("keys = %v, want %v", gotKeys, wantKeys)
		}
	}
	pts, _ := out.Get("data_points")
	list := pts.([]*entities.OrderedMap[any])
	if len(list) != 4 {
		t.Fatalf("points = %d, want 4", len(list))
	}
	// i=0 -> cache_hit_rate 0.75, avg_response_time 50, active 3, score 75
	first := list[len(list)-1]
	if v, _ := first.Get("cache_hit_rate"); v != 0.75 {
		t.Fatalf("cache_hit_rate = %v, want 0.75", v)
	}
	if v, _ := first.Get("avg_response_time"); v != 50 {
		t.Fatalf("avg_response_time = %v, want 50", v)
	}
}
