package auth

import (
	"context"
	"fmt"
	"time"

	entities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// MCPKeycloakAuth ports auth/mcp_keycloak_auth.py:MCPKeycloakAuth.
//
// The FastAPI surface of the Python module (Depends/HTTPBearer, the
// get_current_user dependency, the require_mcp_permission/require_tool_access
// decorators and the module-level get_mcp_user/require_mcp_auth helpers) is not
// ported: those exist only to inject the current user into FastAPI routes and
// have no Go meaning. The class logic, dict shapes and error mapping are kept.
type MCPKeycloakAuth struct {
	KeycloakProvider *KeycloakAuthProvider
	MCPAuthEnabled   bool
	RequiredRoles    []string
	JWKSCache        any
	JWKSCacheTime    *time.Time
}

// NewMCPKeycloakAuth mirrors MCPKeycloakAuth.__init__ (including the module
// level `mcp_auth = MCPKeycloakAuth()` construction).
func NewMCPKeycloakAuth() (*MCPKeycloakAuth, error) {
	provider, err := NewKeycloakAuthProvider("", "", "", "", true, true, 300, 3600)
	if err != nil {
		return nil, err
	}
	return newMCPKeycloakAuthWithProvider(provider), nil
}

// newMCPKeycloakAuthWithProvider allows tests to inject a provider without
// requiring a live Keycloak URL. It is the same object graph as __init__.
func newMCPKeycloakAuthWithProvider(provider *KeycloakAuthProvider) *MCPKeycloakAuth {
	return &MCPKeycloakAuth{
		KeycloakProvider: provider,
		MCPAuthEnabled:   value_objects.PyLower(envOr("AUTH_ENABLED", "true")) == "true",
		RequiredRoles: []string{
			"mcp-user",
			"mcp-tools",
			"mcp-developer",
			"mcp-admin",
			"admin",
		},
		JWKSCache:     nil,
		JWKSCacheTime: nil,
	}
}

// ValidateMCPToken ports validate_mcp_token. It returns the validated token
// data (OrderedMap in Python key order) or an *HTTPException with the Python
// status/detail.
func (a *MCPKeycloakAuth) ValidateMCPToken(ctx context.Context, token string) (*entities.OrderedMap[any], error) {
	if !a.MCPAuthEnabled {
		d := entities.NewOrderedMap[any]()
		d.Set("active", true)
		d.Set("sub", "dev-user")
		d.Set("email", "dev@localhost")
		d.Set("roles", []string{"mcp-user", "mcp-tools", "admin"})
		d.Set("permissions", []string{"*"})
		return d, nil
	}

	tokenData := a.KeycloakProvider.ValidateToken(ctx, token)
	if tokenData == nil {
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid or expired token"}
	}

	var roles []string
	if realmAccess, ok := tokenData["realm_access"].(map[string]any); ok {
		roles = append(roles, stringList(realmAccess["roles"])...)
	}
	if resourceAccess, ok := tokenData["resource_access"].(map[string]any); ok {
		if clientAccess, ok := resourceAccess[a.KeycloakProvider.ClientID].(map[string]any); ok {
			if len(clientAccess) > 0 {
				roles = append(roles, stringList(clientAccess["roles"])...)
			}
		}
	}

	hasMCPAccess := false
	for _, role := range roles {
		if containsString(a.RequiredRoles, role) {
			hasMCPAccess = true
			break
		}
	}
	if !hasMCPAccess {
		return nil, &HTTPException{
			StatusCode: 403,
			Detail:     fmt.Sprintf("Insufficient permissions. Required roles: %s", value_objects.PyRepr(a.RequiredRoles)),
		}
	}

	permissions := a.BuildMCPPermissions(roles)

	d := entities.NewOrderedMap[any]()
	d.Set("active", true)
	d.Set("sub", tokenData["sub"])
	d.Set("email", tokenData["email"])
	d.Set("preferred_username", tokenData["preferred_username"])
	d.Set("roles", roles)
	d.Set("mcp_access", true)
	d.Set("mcp_permissions", permissions)
	d.Set("mcp_tools", a.GetAllowedTools(roles))
	d.Set("exp", tokenData["exp"])
	d.Set("iat", tokenData["iat"])
	return d, nil
}

// BuildMCPPermissions ports _build_mcp_permissions. Python returns
// list(set(permissions)), whose order is unspecified; this keeps first-seen
// order so the result is deterministic.
func (a *MCPKeycloakAuth) BuildMCPPermissions(roles []string) []string {
	rolePermissions := map[string][]string{
		"mcp-admin":     {"*"},
		"mcp-tools":     {"tools:execute", "tools:list", "tools:describe", "context:read", "context:write"},
		"mcp-user":      {"tools:list", "tools:describe", "context:read"},
		"mcp-developer": {"tools:*", "context:*", "agents:*", "projects:*"},
	}

	var permissions []string
	for _, role := range roles {
		if perms, ok := rolePermissions[role]; ok {
			permissions = append(permissions, perms...)
		}
	}
	return uniqueStrings(permissions)
}

// MergeToolPermissions ports _merge_tool_permissions. Python uses
// list(set(...)) for the merged list; first-seen order is used here.
func (a *MCPKeycloakAuth) MergeToolPermissions(target, source *entities.OrderedMap[any]) {
	for _, category := range source.Keys() {
		tools, _ := source.Get(category)
		srcTools, _ := tools.([]string)
		if existing, ok := target.Get(category); ok {
			existingTools, _ := existing.([]string)
			target.Set(category, uniqueStrings(append(append([]string{}, existingTools...), srcTools...)))
		} else {
			target.Set(category, append([]string{}, srcTools...))
		}
	}
}

// GetAllowedTools ports _get_allowed_tools.
func (a *MCPKeycloakAuth) GetAllowedTools(roles []string) *entities.OrderedMap[any] {
	if containsString(roles, "mcp-admin") || containsString(roles, "admin") {
		d := entities.NewOrderedMap[any]()
		d.Set("all", []string{"*"})
		return d
	}

	allowedTools := entities.NewOrderedMap[any]()

	if containsString(roles, "mcp-developer") {
		src := entities.NewOrderedMap[any]()
		src.Set("project", []string{"manage_project", "manage_git_branch"})
		src.Set("task", []string{"manage_task", "manage_subtask"})
		src.Set("context", []string{"manage_context"})
		src.Set("agent", []string{"call_agent", "manage_agent"})
		src.Set("development", []string{"*"})
		a.MergeToolPermissions(allowedTools, src)
	}

	if containsString(roles, "mcp-tools") {
		src := entities.NewOrderedMap[any]()
		src.Set("task", []string{"manage_task", "search_task"})
		src.Set("context", []string{"manage_context"})
		src.Set("agent", []string{"call_agent"})
		a.MergeToolPermissions(allowedTools, src)
	}

	if containsString(roles, "mcp-user") {
		src := entities.NewOrderedMap[any]()
		src.Set("task", []string{"search_task"})
		src.Set("context", []string{"get_context"})
		a.MergeToolPermissions(allowedTools, src)
	}

	return allowedTools
}

// CreateMCPSession ports create_mcp_session.
func (a *MCPKeycloakAuth) CreateMCPSession(userData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	sub, _ := userData.Get("sub")
	now := time.Now().UTC()
	sessionID := fmt.Sprintf("mcp-%s-%s", value_objects.PyStr(sub), value_objects.PyStr(float64(now.UnixNano())/1e9))

	d := entities.NewOrderedMap[any]()
	d.Set("session_id", sessionID)
	d.Set("user_id", sub)
	d.Set("email", mapGet(userData, "email"))
	d.Set("roles", mapGetOr(userData, "roles", []string{}))
	d.Set("permissions", mapGetOr(userData, "mcp_permissions", []string{}))
	d.Set("tools", mapGetOr(userData, "mcp_tools", entities.NewOrderedMap[any]()))
	d.Set("created_at", value_objects.IsoFormat(now))
	d.Set("expires_at", value_objects.IsoFormat(now.Add(24*time.Hour)))
	return d
}

// ValidateToolRequest ports validate_tool_request.
func (a *MCPKeycloakAuth) ValidateToolRequest(toolName string, userData *entities.OrderedMap[any], parameters *entities.OrderedMap[any]) bool {
	allowedToolsAny, _ := userData.Get("mcp_tools")
	allowedTools, _ := allowedToolsAny.(*entities.OrderedMap[any])
	if allowedTools == nil {
		allowedTools = entities.NewOrderedMap[any]()
	}

	if all, ok := allowedTools.Get("all"); ok {
		if allList, ok := all.([]string); ok && len(allList) == 1 && allList[0] == "*" {
			return true
		}
	}

	toolAllowed := false
	for _, category := range allowedTools.Keys() {
		tools, _ := allowedTools.Get(category)
		toolList, _ := tools.([]string)
		if containsString(toolList, "*") || containsString(toolList, toolName) {
			toolAllowed = true
			break
		}
	}
	if !toolAllowed {
		return false
	}

	if parameters != nil && parameters.Len() > 0 {
		if toolName == "manage_project" {
			if action, _ := parameters.Get("action"); action == "delete" {
				if rolesAny, ok := userData.Get("roles"); ok {
					if roles, ok := rolesAny.([]string); ok && !containsString(roles, "mcp-admin") {
						return false
					}
					if _, ok := rolesAny.([]string); !ok {
						return false
					}
				} else {
					return false
				}
			}
		}
	}

	return true
}

func mapGet(m *entities.OrderedMap[any], key string) any {
	v, _ := m.Get(key)
	return v
}

func mapGetOr(m *entities.OrderedMap[any], key string, def any) any {
	if v, ok := m.Get(key); ok {
		return v
	}
	return def
}

// uniqueStrings is the deterministic stand-in for list(set(xs)).
func uniqueStrings(xs []string) []string {
	seen := map[string]bool{}
	out := []string{}
	for _, x := range xs {
		if !seen[x] {
			seen[x] = true
			out = append(out, x)
		}
	}
	return out
}
