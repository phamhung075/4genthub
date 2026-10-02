package services

import (
	"context"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/task_management/domain/entities"
)

type zpTaskAuthFakeFormatter struct {
	operation string
	errMsg    string
	code      string
	calls     int
}

func (f *zpTaskAuthFakeFormatter) CreateErrorResponse(operation, errMsg, errorCode string) *entities.OrderedMap[any] {
	f.calls++
	f.operation, f.errMsg, f.code = operation, errMsg, errorCode
	m := entities.NewOrderedMap[any]()
	m.Set("error", errMsg)
	m.Set("code", errorCode)
	return m
}

type zpTaskAuthFakeUser struct{ payload map[string]any }

func (u zpTaskAuthFakeUser) TokenPayload() map[string]any { return u.payload }

func TestTaskAuthorizationService_ActionMap(t *testing.T) {
	svc := NewTaskAuthorizationService(nil)
	cases := map[string]authdomain.PermissionAction{
		"create": authdomain.ActionCreate, "get": authdomain.ActionRead,
		"list": authdomain.ActionRead, "search": authdomain.ActionRead,
		"update": authdomain.ActionUpdate, "complete": authdomain.ActionUpdate,
		"delete": authdomain.ActionDelete, "next": authdomain.ActionRead,
		"add_dependency": authdomain.ActionUpdate, "remove_dependency": authdomain.ActionUpdate,
	}
	for action, want := range cases {
		got := svc.GetPermissionForAction(action)
		if got == nil || *got != want {
			t.Fatalf("action %q: got %v want %v", action, got, want)
		}
		if !svc.IsValidAction(action) {
			t.Fatalf("action %q should be valid", action)
		}
	}
	if got := svc.GetPermissionForAction("nope"); got != nil {
		t.Fatalf("unknown action should map to nil, got %v", got)
	}
	if svc.IsValidAction("nope") {
		t.Fatal("unknown action should be invalid")
	}
}

func TestTaskAuthorizationService_UnknownActionAllows(t *testing.T) {
	svc := NewTaskAuthorizationService(nil)
	ok, resp := svc.CheckTaskPermission("nope", "u1", nil, nil)
	if !ok || resp != nil {
		t.Fatalf("unknown action should allow, got %v %v", ok, resp)
	}
}

func TestTaskAuthorizationService_NoTokenAndDenied(t *testing.T) {
	svc := NewTaskAuthorizationService(nil)
	ok, resp := svc.CheckTaskPermission("get", "u1", map[string]any{}, nil)
	if ok || resp == nil {
		t.Fatal("empty token should deny")
	}
	if v, _ := resp.Get("error"); v != "No token payload found" {
		t.Fatalf("error=%v", v)
	}
	if v, _ := resp.Get("code"); v != "AUTHENTICATION_ERROR" {
		t.Fatalf("code=%v", v)
	}

	deniedPayload := map[string]any{"scope": "projects:read"}
	ok, resp = svc.CheckTaskPermission("get", "u1", deniedPayload, nil)
	if ok || resp == nil {
		t.Fatal("missing tasks:read should deny")
	}
	if v, _ := resp.Get("error"); v != "Permission denied: requires tasks:read" {
		t.Fatalf("error=%v", v)
	}
	if v, _ := resp.Get("code"); v != "PERMISSION_DENIED" {
		t.Fatalf("code=%v", v)
	}
}

func TestTaskAuthorizationService_Allowed(t *testing.T) {
	svc := NewTaskAuthorizationService(nil)
	ok, resp := svc.CheckTaskPermission("get", "u1", map[string]any{"scope": "tasks:read"}, nil)
	if !ok || resp != nil {
		t.Fatalf("tasks:read should allow, got %v %v", ok, resp)
	}
	ok, resp = svc.CheckTaskPermission("delete", "u1", map[string]any{"realm_roles": []any{"admin"}}, nil)
	if !ok || resp != nil {
		t.Fatalf("admin should allow, got %v %v", ok, resp)
	}
}

func TestTaskAuthorizationService_Formatter(t *testing.T) {
	f := &zpTaskAuthFakeFormatter{}
	svc := NewTaskAuthorizationService(f)
	ok, resp := svc.CheckTaskPermission("get", "u1", nil, nil)
	if ok || resp == nil || f.calls != 1 {
		t.Fatalf("formatter should be used once, got %d", f.calls)
	}
	if f.operation != "get" || f.code != "AUTHENTICATION_ERROR" {
		t.Fatalf("formatter args: %q %q", f.operation, f.code)
	}
}

func TestTaskAuthorizationService_FromContext(t *testing.T) {
	svc := NewTaskAuthorizationService(nil)
	ok, resp := svc.CheckTaskPermissionFromContext(context.Background(), "get", "u1", nil)
	if !ok || resp != nil {
		t.Fatalf("no context should allow, got %v %v", ok, resp)
	}

	ctx := context.WithValue(context.Background(), authdomain.UserContextKey,
		zpTaskAuthFakeUser{payload: map[string]any{"scope": "tasks:read"}})
	ok, resp = svc.CheckTaskPermissionFromContext(ctx, "get", "u1", nil)
	if !ok || resp != nil {
		t.Fatalf("tasks:read context should allow, got %v %v", ok, resp)
	}

	ctx = context.WithValue(context.Background(), authdomain.UserContextKey,
		zpTaskAuthFakeUser{payload: map[string]any{"scope": "projects:read"}})
	ok, resp = svc.CheckTaskPermissionFromContext(ctx, "get", "u1", nil)
	if ok || resp == nil {
		t.Fatal("missing permission in context should deny")
	}
}
