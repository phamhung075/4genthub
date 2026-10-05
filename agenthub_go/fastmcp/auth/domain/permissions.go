package domain

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ResourceType enumerates the MCP resource types.
type ResourceType string

const (
	ResourceProjects ResourceType = "projects"
	ResourceTasks    ResourceType = "tasks"
	ResourceSubtasks ResourceType = "subtasks"
	ResourceContexts ResourceType = "contexts"
	ResourceAgents   ResourceType = "agents"
	ResourceBranches ResourceType = "branches"
	ResourceMCP      ResourceType = "mcp"
)

// AllResourceTypes is the enum iteration order.
var AllResourceTypes = []ResourceType{ResourceProjects, ResourceTasks, ResourceSubtasks, ResourceContexts, ResourceAgents, ResourceBranches, ResourceMCP}

// PermissionAction enumerates the CRUD actions for resources.
type PermissionAction string

const (
	ActionCreate   PermissionAction = "create"
	ActionRead     PermissionAction = "read"
	ActionUpdate   PermissionAction = "update"
	ActionDelete   PermissionAction = "delete"
	ActionExecute  PermissionAction = "execute"
	ActionDelegate PermissionAction = "delegate"
)

// AllPermissionActions is the enum iteration order.
var AllPermissionActions = []PermissionAction{ActionCreate, ActionRead, ActionUpdate, ActionDelete, ActionExecute, ActionDelegate}

// ResourcePermission is a permission for a specific resource and action.
type ResourcePermission struct {
	Resource ResourceType
	Action   PermissionAction
}

// ScopeName is the scope in the format "resource:action".
func (p ResourcePermission) ScopeName() string { return string(p.Resource) + ":" + string(p.Action) }

// ResourcePermissionFromScope parses a scope string; nil when it is not a known scope.
func ResourcePermissionFromScope(scope string) *ResourcePermission {
	i := strings.Index(scope, ":")
	if i < 0 {
		return nil
	}
	resourceStr, actionStr := scope[:i], scope[i+1:]
	var resource ResourceType
	for _, r := range AllResourceTypes {
		if string(r) == resourceStr {
			resource = r
			break
		}
	}
	if resource == "" {
		return nil
	}
	for _, a := range AllPermissionActions {
		if string(a) == actionStr {
			return &ResourcePermission{resource, a}
		}
	}
	return nil
}

// PermissionChecker checks resource permissions against a decoded JWT payload.
// Sets are unordered in Python; ToDict returns them sorted.
type PermissionChecker struct {
	TokenPayload map[string]any
	Scopes       map[string]struct{}
	Permissions  map[string]map[string]any
	Roles        map[string]struct{}
}

// NewPermissionChecker extracts scopes, permissions and roles from the payload.
func NewPermissionChecker(payload map[string]any) *PermissionChecker {
	c := &PermissionChecker{TokenPayload: payload}
	c.Scopes = c.extractScopes()
	c.Permissions = c.extractPermissions()
	c.Roles = c.extractRoles()
	return c
}

// stringItems returns the string elements of a JSON array (non-strings are skipped).
func stringItems(v any) ([]string, bool) {
	list, ok := v.([]any)
	if !ok {
		if ss, ok := v.([]string); ok {
			return ss, true
		}
		return nil, false
	}
	out := []string{}
	for _, e := range list {
		if s, ok := e.(string); ok {
			out = append(out, s)
		}
	}
	return out, true
}

func (c *PermissionChecker) extractScopes() map[string]struct{} {
	scopes := map[string]struct{}{}
	if s, ok := c.TokenPayload["scope"].(string); ok {
		for _, f := range value_objects.PySplit(s) {
			scopes[f] = struct{}{}
		}
	}
	if list, ok := stringItems(c.TokenPayload["scopes"]); ok {
		for _, s := range list {
			scopes[s] = struct{}{}
		}
	}
	return scopes
}

func (c *PermissionChecker) extractPermissions() map[string]map[string]any {
	perms := map[string]map[string]any{}
	if raw, ok := c.TokenPayload["permissions"].(map[string]any); ok {
		for resource, actions := range raw {
			switch a := actions.(type) {
			case map[string]any:
				copied := make(map[string]any, len(a))
				for k, v := range a {
					copied[k] = v
				}
				perms[resource] = copied
			case bool:
				perms[resource] = map[string]any{"all": a}
			}
		}
	}
	for scope := range c.Scopes {
		if p := ResourcePermissionFromScope(scope); p != nil {
			r := string(p.Resource)
			if perms[r] == nil {
				perms[r] = map[string]any{}
			}
			perms[r][string(p.Action)] = true
		}
	}
	return perms
}

func (c *PermissionChecker) extractRoles() map[string]struct{} {
	roles := map[string]struct{}{}
	if list, ok := stringItems(c.TokenPayload["realm_roles"]); ok {
		for _, r := range list {
			roles[r] = struct{}{}
		}
	}
	if access, ok := c.TokenPayload["realm_access"].(map[string]any); ok {
		if list, ok := stringItems(access["roles"]); ok {
			for _, r := range list {
				roles[r] = struct{}{}
			}
		}
	}
	return roles
}

// HasPermission: admin role, the exact scope, the resource action, the resource "all"
// flag, or the global action flag.
func (c *PermissionChecker) HasPermission(resource ResourceType, action PermissionAction) bool {
	if _, ok := c.Roles["admin"]; ok {
		return true
	}
	if _, ok := c.Scopes[string(resource)+":"+string(action)]; ok {
		return true
	}
	rp := c.Permissions[string(resource)]
	if value_objects.PyTruthy(rp[string(action)]) || value_objects.PyTruthy(rp["all"]) {
		return true
	}
	return value_objects.PyTruthy(c.Permissions["global"][string(action)])
}

func (c *PermissionChecker) HasScope(scope string) bool { _, ok := c.Scopes[scope]; return ok }
func (c *PermissionChecker) HasRole(role string) bool   { _, ok := c.Roles[role]; return ok }

func (c *PermissionChecker) HasAnyPermission(resource ResourceType, actions []PermissionAction) bool {
	for _, a := range actions {
		if c.HasPermission(resource, a) {
			return true
		}
	}
	return false
}

func (c *PermissionChecker) HasAllPermissions(resource ResourceType, actions []PermissionAction) bool {
	for _, a := range actions {
		if !c.HasPermission(resource, a) {
			return false
		}
	}
	return true
}

func (c *PermissionChecker) GetAllowedActions(resource ResourceType) []PermissionAction {
	allowed := []PermissionAction{}
	for _, a := range AllPermissionActions {
		if c.HasPermission(resource, a) {
			allowed = append(allowed, a)
		}
	}
	return allowed
}

func (c *PermissionChecker) GetAllowedResources() []ResourceType {
	allowed := []ResourceType{}
	for _, r := range AllResourceTypes {
		if c.HasAnyPermission(r, AllPermissionActions) {
			allowed = append(allowed, r)
		}
	}
	return allowed
}

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// PermissionsDict is the to_dict() shape.
type PermissionsDict struct {
	Scopes           []string
	Roles            []string
	Permissions      map[string]map[string]any
	AllowedResources []string
}

func (c *PermissionChecker) ToDict() PermissionsDict {
	res := []string{}
	for _, r := range c.GetAllowedResources() {
		res = append(res, string(r))
	}
	return PermissionsDict{sortedKeys(c.Scopes), sortedKeys(c.Roles), c.Permissions, res}
}

type contextKey string

// UserContextKey stores the authenticated user (a TokenPayloadProvider) in the request
// context (Python: request.state.user); PermissionsContextKey stores the
// *PermissionChecker (request.state.permissions).
const (
	UserContextKey        contextKey = "user"
	PermissionsContextKey contextKey = "permissions"
)

// TokenPayloadProvider is the authenticated user's token (Python: user.token).
type TokenPayloadProvider interface{ TokenPayload() map[string]any }

// PermissionsFromContext returns the checker stored by the middleware.
func PermissionsFromContext(ctx context.Context) *PermissionChecker {
	c, _ := ctx.Value(PermissionsContextKey).(*PermissionChecker)
	return c
}

func writeDetail(w http.ResponseWriter, status int, detail string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]string{"detail": detail})
}

// authorize is the shared body of the Python decorators: it resolves the checker or
// writes the 401 response.
func authorize(w http.ResponseWriter, r *http.Request) *PermissionChecker {
	user, _ := r.Context().Value(UserContextKey).(TokenPayloadProvider)
	if user == nil {
		writeDetail(w, http.StatusUnauthorized, "Not authenticated")
		return nil
	}
	payload := user.TokenPayload()
	if len(payload) == 0 {
		writeDetail(w, http.StatusUnauthorized, "No token payload found")
		return nil
	}
	return NewPermissionChecker(payload)
}

func withChecker(r *http.Request, c *PermissionChecker) *http.Request {
	return r.WithContext(context.WithValue(r.Context(), PermissionsContextKey, c))
}

// RequirePermission is the require_permission decorator as HTTP middleware.
func RequirePermission(resource ResourceType, action PermissionAction) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c := authorize(w, r)
			if c == nil {
				return
			}
			if !c.HasPermission(resource, action) {
				writeDetail(w, http.StatusForbidden, fmt.Sprintf("Permission denied: %s:%s", resource, action))
				return
			}
			next.ServeHTTP(w, withChecker(r, c))
		})
	}
}

// RequireAnyPermission is the require_any_permission decorator as HTTP middleware.
func RequireAnyPermission(permissions ...ResourcePermission) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c := authorize(w, r)
			if c == nil {
				return
			}
			has := false
			for _, p := range permissions {
				if c.HasPermission(p.Resource, p.Action) {
					has = true
					break
				}
			}
			if !has {
				strs := make([]string, len(permissions))
				for i, p := range permissions {
					strs[i] = p.ScopeName()
				}
				writeDetail(w, http.StatusForbidden, "Permission denied: requires any of "+strings.Join(strs, ", "))
				return
			}
			next.ServeHTTP(w, withChecker(r, c))
		})
	}
}

// RequireScope is the require_scope decorator as HTTP middleware.
func RequireScope(scope string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c := authorize(w, r)
			if c == nil {
				return
			}
			if !c.HasScope(scope) {
				writeDetail(w, http.StatusForbidden, "Scope required: "+scope)
				return
			}
			next.ServeHTTP(w, withChecker(r, c))
		})
	}
}
