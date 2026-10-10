package auth

import (
	"context"
	"reflect"
	"testing"

	entities "agenthub/fastmcp/task_management/domain/entities"
)

func newTestMCPAuth() *MCPKeycloakAuth {
	return newMCPKeycloakAuthWithProvider(&KeycloakAuthProvider{ClientID: "mcp-backend"})
}

// Expectations transcribed from mcp_keycloak_auth.py.
func TestBuildMCPPermissions(t *testing.T) {
	a := newTestMCPAuth()

	cases := []struct {
		roles []string
		want  []string
	}{
		{[]string{"mcp-admin"}, []string{"*"}},
		{[]string{"mcp-user"}, []string{"tools:list", "tools:describe", "context:read"}},
		{[]string{"mcp-developer"}, []string{"tools:*", "context:*", "projects:*"}},
		{[]string{"nobody"}, nil},
	}
	for _, c := range cases {
		got := a.BuildMCPPermissions(c.roles)
		if !sameSet(got, c.want) {
			t.Errorf("BuildMCPPermissions(%v) = %v, want set %v", c.roles, got, c.want)
		}
	}
}

func TestGetAllowedTools(t *testing.T) {
	a := newTestMCPAuth()

	admin := a.GetAllowedTools([]string{"mcp-admin"})
	if got := keys(admin); !reflect.DeepEqual(got, []string{"all"}) {
		t.Fatalf("admin keys = %v", got)
	}
	all, _ := admin.Get("all")
	if !reflect.DeepEqual(all, []string{"*"}) {
		t.Fatalf("admin all = %v", all)
	}

	// "admin" is also full access.
	if got := keys(a.GetAllowedTools([]string{"admin"})); !reflect.DeepEqual(got, []string{"all"}) {
		t.Fatalf("admin-role keys = %v", got)
	}

	dev := a.GetAllowedTools([]string{"mcp-developer"})
	if got := keys(dev); !reflect.DeepEqual(got, []string{"project", "task", "context", "development"}) {
		t.Fatalf("developer keys = %v", got)
	}
	devTask, _ := dev.Get("task")
	if !reflect.DeepEqual(devTask, []string{"manage_task", "manage_subtask"}) {
		t.Fatalf("developer task = %v", devTask)
	}

	// mcp-tools merges into the existing task/context keys.
	merged := a.GetAllowedTools([]string{"mcp-developer", "mcp-tools"})
	mergedTask, _ := merged.Get("task")
	if !sameSet(mergedTask.([]string), []string{"manage_task", "manage_subtask", "search_task"}) {
		t.Fatalf("merged task = %v", mergedTask)
	}

	if got := keys(a.GetAllowedTools([]string{"mcp-user"})); !reflect.DeepEqual(got, []string{"task", "context"}) {
		t.Fatalf("user keys = %v", got)
	}
	if got := keys(a.GetAllowedTools(nil)); len(got) != 0 {
		t.Fatalf("unknown roles keys = %v", got)
	}
}

func TestValidateMCPTokenDevMode(t *testing.T) {
	a := newTestMCPAuth()
	a.MCPAuthEnabled = false

	got, err := a.ValidateMCPToken(context.Background(), "ignored")
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"active", "sub", "email", "roles", "permissions"}
	if !reflect.DeepEqual(keys(got), want) {
		t.Fatalf("dev keys = %v, want %v", keys(got), want)
	}
	if v, _ := got.Get("sub"); v != "dev-user" {
		t.Fatalf("dev sub = %v", v)
	}
}

func TestValidateToolRequest(t *testing.T) {
	a := newTestMCPAuth()

	adminUser := entities.NewOrderedMap[any]()
	adminUser.Set("mcp_tools", a.GetAllowedTools([]string{"admin"}))
	adminUser.Set("roles", []string{"admin"})
	if !a.ValidateToolRequest("anything", adminUser, nil) {
		t.Fatal("admin should access anything")
	}

	devUser := entities.NewOrderedMap[any]()
	devUser.Set("mcp_tools", a.GetAllowedTools([]string{"mcp-developer"}))
	devUser.Set("roles", []string{"mcp-developer"})
	if !a.ValidateToolRequest("manage_task", devUser, nil) {
		t.Fatal("manage_task should be allowed for developer")
	}
	// "development": ["*"] makes any tool name match for a developer.
	if !a.ValidateToolRequest("unknown_tool", devUser, nil) {
		t.Fatal("unknown_tool should match the developer wildcard")
	}

	userUser := entities.NewOrderedMap[any]()
	userUser.Set("mcp_tools", a.GetAllowedTools([]string{"mcp-user"}))
	userUser.Set("roles", []string{"mcp-user"})
	if a.ValidateToolRequest("unknown_tool", userUser, nil) {
		t.Fatal("unknown_tool should be denied for mcp-user")
	}

	params := entities.NewOrderedMap[any]()
	params.Set("action", "delete")
	if a.ValidateToolRequest("manage_project", devUser, params) {
		t.Fatal("non-admin delete should be denied")
	}
	devUser.Set("roles", []string{"mcp-admin"})
	if !a.ValidateToolRequest("manage_project", devUser, params) {
		t.Fatal("mcp-admin delete should be allowed")
	}
}

func TestCreateMCPSession(t *testing.T) {
	a := newTestMCPAuth()
	user := entities.NewOrderedMap[any]()
	user.Set("sub", "user-123")
	user.Set("email", "u@example.com")
	user.Set("roles", []string{"mcp-user"})
	user.Set("mcp_permissions", []string{"tools:list"})
	user.Set("mcp_tools", entities.NewOrderedMap[any]())

	session := a.CreateMCPSession(user)
	want := []string{"session_id", "user_id", "email", "roles", "permissions", "tools", "created_at", "expires_at"}
	if !reflect.DeepEqual(keys(session), want) {
		t.Fatalf("session keys = %v, want %v", keys(session), want)
	}
	if v, _ := session.Get("user_id"); v != "user-123" {
		t.Fatalf("user_id = %v", v)
	}
}

func keys(m *entities.OrderedMap[any]) []string {
	if m == nil {
		return nil
	}
	return m.Keys()
}

func sameSet(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	seen := map[string]int{}
	for _, x := range a {
		seen[x]++
	}
	for _, x := range b {
		seen[x]--
	}
	for _, n := range seen {
		if n != 0 {
			return false
		}
	}
	return true
}
