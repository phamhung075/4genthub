package server

import (
	"strings"
	"testing"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
)

func secStrptr(s string) *string { return &s }

func keysOf(om *entities.OrderedMap[any]) []string { return om.Keys() }

func TestSecurityContextFromRequest(t *testing.T) {
	t.Setenv("ENVIRONMENT", "staging")

	uid := secStrptr("user-1")
	cases := []struct {
		name        string
		userID      *string
		isAdmin     bool
		isInternal  bool
		environment *string
		wantLevel   AccessLevel
		wantEnv     string
	}{
		{"anonymous", nil, false, false, nil, AccessLevelClient, "staging"},
		{"user only", uid, false, false, nil, AccessLevelClient, "staging"},
		{"admin no user", nil, true, true, nil, AccessLevelAdmin, "staging"},
		{"admin with user", uid, true, false, nil, AccessLevelAuthenticated, "staging"},
		{"internal with user", uid, false, true, nil, AccessLevelAuthenticated, "staging"},
		{"admin internal with user", uid, true, true, nil, AccessLevelAdmin, "staging"},
		{"explicit env", uid, true, true, secStrptr("development"), AccessLevelAdmin, "development"},
		{"empty env falls back", uid, true, true, secStrptr(""), AccessLevelAdmin, "staging"},
	}

	for _, tc := range cases {
		got := NewSecurityContextFromRequest(tc.userID, tc.isAdmin, tc.isInternal, tc.environment)
		if got.AccessLevel != tc.wantLevel {
			t.Errorf("%s: access level = %q, want %q", tc.name, got.AccessLevel, tc.wantLevel)
		}
		if got.Environment != tc.wantEnv {
			t.Errorf("%s: environment = %q, want %q", tc.name, got.Environment, tc.wantEnv)
		}
		if got.IsInternal != tc.isInternal {
			t.Errorf("%s: is_internal = %v, want %v", tc.name, got.IsInternal, tc.isInternal)
		}
	}
}

func TestClientResponseShape(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("PRODUCTION", "false")

	out := ClientHealthCheck()
	wantKeys := []string{"success", "status", "timestamp"}
	if got := strings.Join(keysOf(out), ","); got != strings.Join(wantKeys, ",") {
		t.Fatalf("keys = %v, want %v", keysOf(out), wantKeys)
	}
	if v, _ := out.Get("success"); v != true {
		t.Errorf("success = %v, want true", v)
	}
	if v, _ := out.Get("status"); v != "healthy" {
		t.Errorf("status = %v, want healthy", v)
	}
	if v, _ := out.Get("timestamp"); srvFloat(v) <= 0 {
		t.Errorf("timestamp = %v, want > 0", v)
	}
}

func TestAdminResponseShape(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("PRODUCTION", "false")
	t.Setenv("PYTHONPATH", "/opt/app")
	t.Setenv("TASKS_JSON_PATH", "not set")
	t.Setenv("SUPABASE_URL", "")
	t.Setenv("ENVIRONMENT", "production")

	out := SecureHealthCheck(secStrptr("admin-1"), true, true, nil)
	wantKeys := []string{
		"success", "status", "server_name", "version", "authentication",
		"task_management", "environment", "connections", "security_context", "timestamp",
	}
	if got := strings.Join(keysOf(out), ","); got != strings.Join(wantKeys, ",") {
		t.Fatalf("keys = %v, want %v", keysOf(out), wantKeys)
	}
	if v, _ := out.Get("server_name"); v != config.ServerName {
		t.Errorf("server_name = %v", v)
	}
	if v, _ := out.Get("version"); v != config.ReleaseVersion {
		t.Errorf("version = %v", v)
	}

	auth := srvGet(out, "authentication", nil)
	if v := srvGet(auth, "enabled", nil); v != true {
		t.Errorf("authentication.enabled = %v, want true", v)
	}
	if v := srvGet(auth, "mvp_mode", nil); v != false {
		t.Errorf("authentication.mvp_mode = %v, want false", v)
	}

	env := srvGet(out, "environment", nil)
	if v := srvGet(env, "pythonpath", nil); v != "/opt/app" {
		t.Errorf("environment.pythonpath = %v", v)
	}
	// auth_enabled / mvp_mode are raw env strings in _get_environment_info.
	if v := srvGet(env, "auth_enabled", nil); v != "true" {
		t.Errorf("environment.auth_enabled = %v, want string true", v)
	}
	if v := srvGet(env, "mvp_mode", nil); v != "false" {
		t.Errorf("environment.mvp_mode = %v, want string false", v)
	}
	if v := srvGet(env, "supabase_configured", nil); v != false {
		t.Errorf("environment.supabase_configured = %v, want false", v)
	}

	tm := srvGet(out, "task_management", nil)
	if v := srvGet(tm, "task_management_enabled", nil); v != true {
		t.Errorf("task_management_enabled = %v", v)
	}
	if v, ok := srvGet(tm, "enabled_tools", nil).([]any); !ok || len(v) != 0 {
		t.Errorf("enabled_tools = %v, want []", srvGet(tm, "enabled_tools", nil))
	}

	sec := srvGet(out, "security_context", nil)
	if v := srvGet(sec, "access_level", nil); v != "admin" {
		t.Errorf("security_context.access_level = %v", v)
	}
	if v, ok := srvGet(sec, "user_id", nil).(*string); !ok || v == nil || *v != "admin-1" {
		t.Errorf("security_context.user_id = %v", srvGet(sec, "user_id", nil))
	}
	if v := srvGet(sec, "environment", nil); v != "production" {
		t.Errorf("security_context.environment = %v", v)
	}
}

func TestConnectionsInfoRecommendedAction(t *testing.T) {
	c := NewSecureHealthChecker()

	zero := entities.NewOrderedMap[any]()
	zero.Set("active_connections", 0)
	if v, _ := c.getConnectionsInfo(zero).Get("recommended_action"); v != "check_client_connection" {
		t.Errorf("recommended_action = %v, want check_client_connection", v)
	}

	two := entities.NewOrderedMap[any]()
	two.Set("active_connections", 2)
	if v, _ := c.getConnectionsInfo(two).Get("recommended_action"); v != "no_action_needed" {
		t.Errorf("recommended_action = %v, want no_action_needed", v)
	}
}

func TestErrorResponseFiltering(t *testing.T) {
	c := NewSecureHealthChecker()

	client := c.getErrorResponse("boom", SecurityContext{AccessLevel: AccessLevelClient, Environment: "production"})
	if got := strings.Join(keysOf(client), ","); got != "success,status,timestamp" {
		t.Fatalf("client error keys = %v", keysOf(client))
	}

	auth := c.getErrorResponse("boom", SecurityContext{AccessLevel: AccessLevelAuthenticated})
	if v, _ := auth.Get("error"); v != "Service temporarily unavailable" {
		t.Errorf("authenticated error = %v", v)
	}

	admin := c.getErrorResponse("boom", SecurityContext{AccessLevel: AccessLevelAdmin})
	if v, _ := admin.Get("error"); v != "boom" {
		t.Errorf("admin error = %v, want boom", v)
	}
}
