package domain

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"testing"
)

type permFixture struct {
	Checker []struct {
		Payload map[string]any `json:"payload"`
		Dict    struct {
			Scopes           []string                  `json:"scopes"`
			Roles            []string                  `json:"roles"`
			Permissions      map[string]map[string]any `json:"permissions"`
			AllowedResources []string                  `json:"allowed_resources"`
		} `json:"dict"`
		Matrix  map[string][]bool   `json:"matrix"`
		Allowed map[string][]string `json:"allowed"`
		AnyAll  map[string][]bool   `json:"anyall"`
		Has     map[string][]bool   `json:"has"`
	} `json:"checker"`
	FromScope []struct {
		Scope string  `json:"scope"`
		Out   *string `json:"out"`
	} `json:"from_scope"`
	Decorators []struct {
		Deco  string `json:"deco"`
		State string `json:"state"`
		Out   struct {
			Ok      *string `json:"ok"`
			PermSet bool    `json:"perm_set"`
			Status  int     `json:"status"`
			Detail  string  `json:"detail"`
		} `json:"out"`
	} `json:"decorators"`
}

func loadPermFixture(t *testing.T) permFixture {
	t.Helper()
	raw, err := os.ReadFile("testdata/permissions_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var f permFixture
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	return f
}

func TestPermissionCheckerParity(t *testing.T) {
	for i, c := range loadPermFixture(t).Checker {
		ch := NewPermissionChecker(c.Payload)
		d := ch.ToDict()
		if !reflect.DeepEqual(d.Scopes, c.Dict.Scopes) || !reflect.DeepEqual(d.Roles, c.Dict.Roles) ||
			!reflect.DeepEqual(d.AllowedResources, c.Dict.AllowedResources) {
			t.Errorf("#%d dict: got %+v want %+v", i, d, c.Dict)
		}
		gotPerms, _ := json.Marshal(d.Permissions)
		wantPerms, _ := json.Marshal(c.Dict.Permissions)
		if string(gotPerms) != string(wantPerms) {
			t.Errorf("#%d permissions: got %s want %s", i, gotPerms, wantPerms)
		}
		for _, r := range AllResourceTypes {
			var row []bool
			for _, a := range AllPermissionActions {
				row = append(row, ch.HasPermission(r, a))
			}
			if !reflect.DeepEqual(row, c.Matrix[string(r)]) {
				t.Errorf("#%d matrix %s: got %v want %v", i, r, row, c.Matrix[string(r)])
			}
			var allowed []string
			for _, a := range ch.GetAllowedActions(r) {
				allowed = append(allowed, string(a))
			}
			if !reflect.DeepEqual(allowed, append([]string{}, c.Allowed[string(r)]...)) && !(len(allowed) == 0 && len(c.Allowed[string(r)]) == 0) {
				t.Errorf("#%d allowed %s: got %v want %v", i, r, allowed, c.Allowed[string(r)])
			}
			aa := []bool{ch.HasAnyPermission(r, []PermissionAction{ActionCreate, ActionRead}), ch.HasAllPermissions(r, []PermissionAction{ActionCreate, ActionRead}),
				ch.HasAnyPermission(r, nil), ch.HasAllPermissions(r, nil)}
			if !reflect.DeepEqual(aa, c.AnyAll[string(r)]) {
				t.Errorf("#%d any/all %s: got %v want %v", i, r, aa, c.AnyAll[string(r)])
			}
		}
		scopes := []bool{ch.HasScope("projects:read"), ch.HasScope("tasks:create"), ch.HasScope("mcp-api"), ch.HasScope("")}
		roles := []bool{ch.HasRole("admin"), ch.HasRole("user"), ch.HasRole("dev"), ch.HasRole("")}
		if !reflect.DeepEqual(scopes, c.Has["scopes"]) || !reflect.DeepEqual(roles, c.Has["roles"]) {
			t.Errorf("#%d has: scopes %v roles %v, want %v", i, scopes, roles, c.Has)
		}
	}
}

func TestResourcePermissionFromScopeParity(t *testing.T) {
	for _, c := range loadPermFixture(t).FromScope {
		p := ResourcePermissionFromScope(c.Scope)
		switch {
		case c.Out == nil && p != nil:
			t.Errorf("%q: got %v, want nil", c.Scope, p.ScopeName())
		case c.Out != nil && (p == nil || p.ScopeName() != *c.Out):
			t.Errorf("%q: got %v, want %q", c.Scope, p, *c.Out)
		}
	}
}

type tokenUser struct{ payload map[string]any }

func (u tokenUser) TokenPayload() map[string]any { return u.payload }

func TestPermissionMiddlewareParity(t *testing.T) {
	states := map[string]any{
		"nouser": nil, "nulluser": nil, "notoken": tokenUser{}, "emptytoken": tokenUser{map[string]any{}},
		"admin":   tokenUser{map[string]any{"realm_roles": []any{"admin"}}},
		"reader":  tokenUser{map[string]any{"scope": "projects:read"}},
		"creator": tokenUser{map[string]any{"scopes": []any{"tasks:create", "mcp-api"}}},
	}
	decos := map[string]func(http.Handler) http.Handler{
		"perm_projects_read": RequirePermission(ResourceProjects, ActionRead),
		"perm_tasks_create":  RequirePermission(ResourceTasks, ActionCreate),
		"any_tasks":          RequireAnyPermission(ResourcePermission{ResourceTasks, ActionCreate}, ResourcePermission{ResourceTasks, ActionUpdate}),
		"any_proj":           RequireAnyPermission(ResourcePermission{ResourceProjects, ActionDelete}, ResourcePermission{ResourceAgents, ActionRead}),
		"scope_mcp":          RequireScope("mcp-api"),
		"scope_other":        RequireScope("other"),
	}
	for _, c := range loadPermFixture(t).Decorators {
		permSet := false
		h := decos[c.Deco](http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			permSet = PermissionsFromContext(r.Context()) != nil
			_, _ = w.Write([]byte("ok"))
		}))
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		if u := states[c.State]; u != nil {
			req = req.WithContext(context.WithValue(req.Context(), UserContextKey, u.(TokenPayloadProvider)))
		}
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if c.Out.Ok != nil {
			if rec.Code != 200 || rec.Body.String() != "ok" || permSet != c.Out.PermSet {
				t.Errorf("%s/%s: got %d %q permSet=%v, want ok permSet=%v", c.Deco, c.State, rec.Code, rec.Body.String(), permSet, c.Out.PermSet)
			}
			continue
		}
		var body struct{ Detail string }
		_ = json.Unmarshal(rec.Body.Bytes(), &body)
		if rec.Code != c.Out.Status || body.Detail != c.Out.Detail {
			t.Errorf("%s/%s: got %d %q, want %d %q", c.Deco, c.State, rec.Code, body.Detail, c.Out.Status, c.Out.Detail)
		}
	}
}
