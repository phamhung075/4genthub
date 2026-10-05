package server

import (
	"strings"
	"testing"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeSecureCtx struct {
	userID *string
}

func (f fakeSecureCtx) UserID() *string { return f.userID }

func TestSecureConnectionCheckInvalidLevel(t *testing.T) {
	out := SecureConnectionCheck(nil, "superuser")

	if got := strings.Join(keysOf(out), ","); got != "success,error,valid_levels,timestamp" {
		t.Fatalf("keys = %v", keysOf(out))
	}
	if v, _ := out.Get("error"); v != "Invalid access level: superuser" {
		t.Errorf("error = %v", v)
	}
	levels, _ := out.Get("valid_levels")
	if got := levels.([]any)[0].(string); got != "client" {
		t.Errorf("first valid level = %v", got)
	}
	if v, _ := out.Get("timestamp"); v != 0 {
		t.Errorf("timestamp = %v, want 0", v)
	}
}

// The Python "authenticated" branch calls secure_health_check(is_admin=False,
// is_internal=False), which resolves to the CLIENT access level; the response is
// therefore the minimal client dict. Quirk preserved.
func TestSecureConnectionCheckAuthenticatedIsClientShape(t *testing.T) {
	out := SecureConnectionCheck(fakeSecureCtx{userID: secStrptr("alice")}, "authenticated")

	if got := strings.Join(keysOf(out), ","); got != "success,status,timestamp" {
		t.Fatalf("keys = %v, want client shape", keysOf(out))
	}
}

func TestSecureConnectionCheckAdminUsesContextUserID(t *testing.T) {
	out := SecureConnectionCheck(fakeSecureCtx{userID: secStrptr("alice")}, "admin")

	if got := strings.Join(keysOf(out), ","); got != "success,status,server_name,version,authentication,task_management,environment,connections,security_context,timestamp" {
		t.Fatalf("keys = %v", keysOf(out))
	}
	sec := srvGet(out, "security_context", nil)
	if v, ok := srvGet(sec, "user_id", nil).(*string); !ok || v == nil || *v != "alice" {
		t.Errorf("user_id = %v, want alice", srvGet(sec, "user_id", nil))
	}
	if v := srvGet(sec, "access_level", nil); v != "admin" {
		t.Errorf("access_level = %v, want admin", v)
	}
}

func TestSecureConnectionCheckDefaultsUserID(t *testing.T) {
	// ctx present but no user_id attribute -> Python getattr default "admin_user".
	out := SecureConnectionCheck(fakeSecureCtx{}, "admin")
	sec := srvGet(out, "security_context", nil)
	if v, ok := srvGet(sec, "user_id", nil).(*string); !ok || v == nil || *v != "admin_user" {
		t.Errorf("user_id = %v, want admin_user", srvGet(sec, "user_id", nil))
	}
}

func TestFormatSecureHealthResponseClient(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("status", "healthy")
	result.Set("timestamp", 0)

	want := "🟢 Server Status: HEALTHY\n\nTimestamp: 0\n\n" +
		"This is a client-safe health check with minimal information disclosure."
	if got := FormatSecureHealthResponse(result, "client"); got != want {
		t.Errorf("client format:\n got %q\nwant %q", got, want)
	}
}

func TestFormatSecureHealthResponseAuthenticated(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("success", true)
	result.Set("status", "healthy")
	result.Set("server_name", config.ServerName)
	result.Set("version", "2.1.0")
	result.Set("uptime_seconds", 7200.0)
	result.Set("active_connections", 3)
	result.Set("restart_count", 1)
	result.Set("restart_notice", "Server has been restarted")
	result.Set("timestamp", 100.0)

	want := "🟢 Server Health Check - Authenticated View\n\n" +
		"**Server Information:**\n" +
		"• Name: " + config.ServerName + "\n" +
		"• Version: 2.1.0\n" +
		"• Status: HEALTHY\n" +
		"• Uptime: 2.0 hours\n" +
		"• Active Connections: 3\n" +
		"• Restart Count: 1\n" +
		"• Notice: Server has been restarted\n\n" +
		"Timestamp: 100.0"
	if got := FormatSecureHealthResponse(result, "authenticated"); got != want {
		t.Errorf("authenticated format:\n got %q\nwant %q", got, want)
	}
}

func TestFormatSecureHealthResponseAuthenticatedNoRestart(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("status", "unhealthy")
	result.Set("server_name", config.ServerName)
	result.Set("version", "2.1.0")
	result.Set("uptime_seconds", 0.0)
	result.Set("active_connections", 0)
	result.Set("restart_count", 0)
	result.Set("timestamp", 5.0)

	got := FormatSecureHealthResponse(result, "authenticated")
	want := "🔴 Server Health Check - Authenticated View\n\n" +
		"**Server Information:**\n" +
		"• Name: " + config.ServerName + "\n" +
		"• Version: 2.1.0\n" +
		"• Status: UNHEALTHY\n" +
		"• Uptime: 0.0 hours\n" +
		"• Active Connections: 0\n\n" +
		"Timestamp: 5.0"
	if got != want {
		t.Errorf("authenticated no-restart format:\n got %q\nwant %q", got, want)
	}
}

func TestFormatSecureHealthResponseAdmin(t *testing.T) {
	result := entities.NewOrderedMap[any]()
	result.Set("status", "healthy")
	result.Set("server_name", config.ServerName)
	result.Set("version", "2.1.0")
	result.Set("uptime_seconds", 3600.0)

	auth := entities.NewOrderedMap[any]()
	auth.Set("enabled", true)
	auth.Set("mvp_mode", false)
	result.Set("authentication", auth)

	tm := entities.NewOrderedMap[any]()
	tm.Set("task_management_enabled", true)
	tm.Set("enabled_tools_count", 3)
	tm.Set("total_tools_count", 5)
	result.Set("task_management", tm)

	env := entities.NewOrderedMap[any]()
	env.Set("pythonpath", "/app")
	env.Set("supabase_configured", false)
	result.Set("environment", env)

	conns := entities.NewOrderedMap[any]()
	conns.Set("active_connections", 2)
	conns.Set("server_restart_count", 1)
	conns.Set("recommended_action", "no_action_needed")
	bc := entities.NewOrderedMap[any]()
	bc.Set("active", true)
	bc.Set("registered_clients", 4)
	conns.Set("status_broadcasting", bc)
	result.Set("connections", conns)

	sec := entities.NewOrderedMap[any]()
	sec.Set("access_level", "admin")
	sec.Set("user_id", "admin")
	sec.Set("environment", "production")
	result.Set("security_context", sec)

	result.Set("timestamp", 100.0)

	got := FormatSecureHealthResponse(result, "admin")
	want := "🟢 Server Health Check - Administrative View\n\n" +
		"**Server Information:**\n" +
		"• Name: " + config.ServerName + "\n" +
		"• Version: 2.1.0\n" +
		"• Status: HEALTHY\n" +
		"• Uptime: 1.0 hours\n\n" +
		"**Authentication:**\n" +
		"• Enabled: True\n" +
		"• MVP Mode: False\n\n" +
		"**Task Management:**\n" +
		"• Enabled: True\n" +
		"• Tools Count: 3/5\n\n" +
		"**Connections:**\n" +
		"• Active: 2\n" +
		"• Restart Count: 1\n" +
		"• Recommended Action: no_action_needed\n" +
		"• Broadcasting Active: True\n" +
		"• Registered Clients: 4\n\n" +
		"**Environment Configuration:**\n" +
		"• Python Path: /app\n" +
		"• Tasks JSON Path: not set\n" +
		"• Projects File Path: not set\n" +
		"• Cursor Tools Disabled: false\n" +
		"• Supabase Configured: False\n\n" +
		"**Security Context:**\n" +
		"• Access Level: admin\n" +
		"• User ID: admin\n" +
		"• Environment: production\n\n" +
		"Timestamp: 100.0"
	if got != want {
		t.Errorf("admin format:\n got %q\nwant %q", got, want)
	}
}

func TestSecureHealthCheckToolFailureMessage(t *testing.T) {
	// The invalid access level path yields success=False; the tool returns the
	// failure string with the error text.
	got := SecureHealthCheckTool(nil, "bogus")
	want := "❌ Health Check Failed\n\nError: Invalid access level: bogus"
	if got != want {
		t.Errorf("tool = %q, want %q", got, want)
	}
}
