package httpapp

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	amentities "agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
)

// --- test fixtures ---

func agentMgmtTestUser() *authdomain.User {
	id := "11111111-1111-1111-1111-111111111111"
	return &authdomain.User{ID: &id, Email: "dev@example.com"}
}

func agentMgmtTestTemplate(t *testing.T) *amentities.AgentTemplate {
	t.Helper()
	id, err := amvo.NewAgentTemplateId("33333333-3333-3333-3333-333333333333")
	if err != nil {
		t.Fatal(err)
	}
	created := time.Date(2024, 1, 2, 3, 4, 5, 123456000, time.UTC)
	return &amentities.AgentTemplate{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &created},
		ID:                  &id, Slug: "coding-agent", Name: "Coding Agent", Description: "d",
		Category: "development", Version: "1.0.0",
		DefaultConfiguration: &amvo.AgentConfiguration{
			SystemPrompt: "prompt", Tools: []string{"read", "write"},
			Capabilities: tmentities.NewOrderedMap[any](),
		},
		Metadata: tmentities.NewOrderedMap[any](),
	}
}

func agentMgmtTestInstance(t *testing.T, name string, usage int) *amentities.UserAgentInstance {
	t.Helper()
	id, err := amvo.NewUserAgentInstanceId("22222222-2222-2222-2222-222222222222")
	if err != nil {
		t.Fatal(err)
	}
	uid, err := amvo.NewUserId("11111111-1111-1111-1111-111111111111")
	if err != nil {
		t.Fatal(err)
	}
	tid, err := amvo.NewAgentTemplateId("33333333-3333-3333-3333-333333333333")
	if err != nil {
		t.Fatal(err)
	}
	created := time.Date(2024, 1, 2, 3, 4, 5, 123456000, time.UTC)
	return &amentities.UserAgentInstance{
		BaseTimestampEntity: base.BaseTimestampEntity{CreatedAt: &created, UpdatedAt: &created},
		ID:                  &id, UserID: &uid, TemplateID: &tid,
		AgentName: name, IsEnabled: true, Visibility: "private", UsageCount: usage,
		Configuration: &amvo.AgentConfiguration{
			SystemPrompt: "prompt", Tools: []string{"read"},
			Capabilities: tmentities.NewOrderedMap[any](), Rules: []string{"r1"},
		},
	}
}

func withAgentMgmtUser(t *testing.T) {
	t.Helper()
	u := agentMgmtTestUser()
	prev := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		return u, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = prev })
}

// --- fake rest.Facade ---

type fakeAgentMgmtFacade struct {
	templates []*amentities.AgentTemplate
	instances []*amentities.UserAgentInstance
	shared    *amentities.UserAgentInstance
	failWith  *auth.HTTPException
}

func (f *fakeAgentMgmtFacade) fail() error {
	if f.failWith != nil {
		return f.failWith
	}
	return nil
}

func (f *fakeAgentMgmtFacade) ListAvailableTemplates(context.Context) ([]*amentities.AgentTemplate, error) {
	return f.templates, f.fail()
}
func (f *fakeAgentMgmtFacade) GetTemplateBySlug(_ context.Context, slug string) (*amentities.AgentTemplate, error) {
	for _, t := range f.templates {
		if t.Slug == slug {
			return t, f.fail()
		}
	}
	return nil, f.fail()
}
func (f *fakeAgentMgmtFacade) GetTemplateByID(_ context.Context, id string) (*amentities.AgentTemplate, error) {
	for _, t := range f.templates {
		if t.ID.Value == id {
			return t, f.fail()
		}
	}
	return nil, f.fail()
}
func (f *fakeAgentMgmtFacade) GetUserInstances(context.Context, amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	return f.instances, f.fail()
}
func (f *fakeAgentMgmtFacade) GetOrCreateInstance(context.Context, amvo.UserId, string) (*amentities.UserAgentInstance, error) {
	return f.instances[0], f.fail()
}
func (f *fakeAgentMgmtFacade) BulkCreateInstances(context.Context, amvo.UserId, []string) ([]*amentities.UserAgentInstance, error) {
	return f.instances, f.fail()
}
func (f *fakeAgentMgmtFacade) UpdateInstance(context.Context, amvo.UserId, string, *string, *bool, *string, []string, *tmentities.OrderedMap[any], []string, *string, *string) (*amentities.UserAgentInstance, error) {
	return f.instances[0], f.fail()
}
func (f *fakeAgentMgmtFacade) DeleteInstance(context.Context, amvo.UserId, string) (bool, error) {
	return true, f.fail()
}
func (f *fakeAgentMgmtFacade) UpdateConfiguration(context.Context, amvo.UserId, string, *string, []string, *tmentities.OrderedMap[any], []string, *string) (*amentities.UserAgentInstance, error) {
	return f.instances[0], f.fail()
}
func (f *fakeAgentMgmtFacade) ResetConfiguration(context.Context, amvo.UserId, string) (*amentities.UserAgentInstance, error) {
	return f.instances[0], f.fail()
}
func (f *fakeAgentMgmtFacade) ShareAgent(context.Context, amvo.UserId, string) (*string, error) {
	tok := strings.Repeat("a", 64)
	return &tok, f.fail()
}
func (f *fakeAgentMgmtFacade) UnshareAgent(context.Context, amvo.UserId, string) (bool, error) {
	return true, f.fail()
}
func (f *fakeAgentMgmtFacade) ImportAgent(context.Context, string, amvo.UserId, string) (*amentities.UserAgentInstance, error) {
	return f.instances[0], f.fail()
}
func (f *fakeAgentMgmtFacade) GetMarketplaceAgents(context.Context, int, int) ([]*amentities.UserAgentInstance, error) {
	return nil, f.fail()
}
func (f *fakeAgentMgmtFacade) GetSharedAgentPreview(context.Context, string) (*amentities.UserAgentInstance, error) {
	return f.shared, f.fail()
}

func agentMgmtTestMux(t *testing.T, f *fakeAgentMgmtFacade) *http.ServeMux {
	t.Helper()
	mux := http.NewServeMux()
	mountAgentManagementRoutesWithFacade(mux, f)
	return mux
}

func agentMgmtDo(mux http.Handler, method, path, body string, authed bool) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	if authed {
		req.Header.Set("Authorization", "Bearer test-token")
	}
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

// --- route registration ---

func TestAgentMgmtMountRegistersEveryRoute(t *testing.T) {
	withAgentMgmtUser(t)
	tmpl := agentMgmtTestTemplate(t)
	inst := agentMgmtTestInstance(t, "coding-agent", 3)
	shared := agentMgmtTestInstance(t, "shared-agent", 1)
	tok := strings.Repeat("a", 64)
	shared.ShareToken = &tok
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{templates: []*amentities.AgentTemplate{tmpl}, instances: []*amentities.UserAgentInstance{inst}, shared: shared})

	probes := []struct {
		method string
		path   string
		body   string
		authed bool
	}{
		{http.MethodGet, "/api/v2/agent-management/templates", "", true},
		{http.MethodGet, "/api/v2/agent-management/templates/coding-agent", "", true},
		{http.MethodGet, "/api/v2/agent-management/instances", "", true},
		{http.MethodGet, "/api/v2/agent-management/instances/22222222-2222-2222-2222-222222222222", "", true},
		{http.MethodPost, "/api/v2/agent-management/instances", `{"template_slug":"coding-agent"}`, true},
		{http.MethodPost, "/api/v2/agent-management/instances/bulk-create", "", true},
		{http.MethodPut, "/api/v2/agent-management/instances/22222222-2222-2222-2222-222222222222", `{"agent_name":"x"}`, true},
		{http.MethodDelete, "/api/v2/agent-management/instances/22222222-2222-2222-2222-222222222222", "", true},
		{http.MethodGet, "/api/v2/agent-management/analytics/usage", "", true},
		{http.MethodGet, "/api/v2/agent-management/analytics/popular", "", true},
		{http.MethodGet, "/api/v2/agent-management/configuration/coding-agent", "", true},
		{http.MethodPut, "/api/v2/agent-management/configuration/coding-agent", `{"system_prompt":"p"}`, true},
		{http.MethodPost, "/api/v2/agent-management/configuration/coding-agent/reset", "", true},
		{http.MethodPost, "/api/v2/agent-management/instances/22222222-2222-2222-2222-222222222222/share", "", true},
		{http.MethodPost, "/api/v2/agent-management/instances/22222222-2222-2222-2222-222222222222/unshare", "", true},
		{http.MethodPost, "/api/v2/agent-management/import", `{"share_token":"` + tok + `"}`, true},
		{http.MethodGet, "/api/v2/agent-management/marketplace", "", false},
		{http.MethodGet, "/api/v2/agent-management/marketplace/" + tok, "", false},
	}
	for _, p := range probes {
		rec := agentMgmtDo(mux, p.method, p.path, p.body, p.authed)
		if rec.Code == http.StatusNotFound {
			t.Errorf("%s %s: not registered (404)", p.method, p.path)
		}
	}
}

func TestAgentMgmtMountRequiresAuth(t *testing.T) {
	withAgentMgmtUser(t)
	tmpl := agentMgmtTestTemplate(t)
	inst := agentMgmtTestInstance(t, "coding-agent", 0)
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{templates: []*amentities.AgentTemplate{tmpl}, instances: []*amentities.UserAgentInstance{inst}})

	for _, path := range []string{
		"/api/v2/agent-management/templates",
		"/api/v2/agent-management/instances",
		"/api/v2/agent-management/analytics/usage",
		"/api/v2/agent-management/configuration/coding-agent",
	} {
		rec := agentMgmtDo(mux, http.MethodGet, path, "", false)
		if rec.Code != http.StatusForbidden {
			t.Errorf("GET %s without token: got %d, want 403", path, rec.Code)
		}
	}
	// Marketplace is public: it must not return 403 (it has no current_user dependency).
	rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/marketplace", "", false)
	if rec.Code != http.StatusOK {
		t.Errorf("public marketplace without token: got %d, want 200", rec.Code)
	}
}

func TestAgentMgmtMountStatusCodes(t *testing.T) {
	withAgentMgmtUser(t)
	tmpl := agentMgmtTestTemplate(t)
	inst := agentMgmtTestInstance(t, "coding-agent", 0)
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{templates: []*amentities.AgentTemplate{tmpl}, instances: []*amentities.UserAgentInstance{inst}})

	if rec := agentMgmtDo(mux, http.MethodPost, "/api/v2/agent-management/instances", `{"template_slug":"coding-agent"}`, true); rec.Code != http.StatusCreated {
		t.Errorf("POST /instances: got %d, want 201", rec.Code)
	}
	if rec := agentMgmtDo(mux, http.MethodPost, "/api/v2/agent-management/instances/bulk-create", "", true); rec.Code != http.StatusCreated {
		t.Errorf("POST /instances/bulk-create: got %d, want 201", rec.Code)
	}
	if rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/instances", "", true); rec.Code != http.StatusOK {
		t.Errorf("GET /instances: got %d, want 200", rec.Code)
	}
}

func TestAgentMgmtMountRequiredFields(t *testing.T) {
	withAgentMgmtUser(t)
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{templates: []*amentities.AgentTemplate{agentMgmtTestTemplate(t)}, instances: []*amentities.UserAgentInstance{agentMgmtTestInstance(t, "coding-agent", 0)}})

	rec := agentMgmtDo(mux, http.MethodPost, "/api/v2/agent-management/instances", `{}`, true)
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("POST /instances {}: got %d, want 422", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "template_slug") {
		t.Fatalf("422 body missing template_slug: %s", rec.Body.String())
	}

	rec = agentMgmtDo(mux, http.MethodPost, "/api/v2/agent-management/import", `{}`, true)
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("POST /import {}: got %d, want 422", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "share_token") {
		t.Fatalf("422 body missing share_token: %s", rec.Body.String())
	}
}

func TestAgentMgmtMountMarketplaceValidation(t *testing.T) {
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{})
	if rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/marketplace?page=0", "", false); rec.Code != http.StatusBadRequest {
		t.Errorf("page=0: got %d, want 400", rec.Code)
	}
	if rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/marketplace?page_size=101", "", false); rec.Code != http.StatusBadRequest {
		t.Errorf("page_size=101: got %d, want 400", rec.Code)
	}
}

func TestAgentMgmtMountMapsHTTPException(t *testing.T) {
	withAgentMgmtUser(t)
	// A missing template is an HTTPException raised by the handler itself.
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{})
	rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/templates/x", "", true)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("got %d, want 404", rec.Code)
	}
	if got, want := rec.Body.String(), `{"detail":"Template 'x' not found"}`; got != want {
		t.Fatalf("body = %s, want %s", got, want)
	}

	// A facade failure is a caught generic exception: 500.
	mux = agentMgmtTestMux(t, &fakeAgentMgmtFacade{failWith: &auth.HTTPException{StatusCode: http.StatusTeapot, Detail: "boom"}})
	rec = agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/templates", "", true)
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("facade failure: got %d, want 500", rec.Code)
	}
}

func TestAgentMgmtMountPopularShape(t *testing.T) {
	withAgentMgmtUser(t)
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{})
	rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/analytics/popular", "", true)
	want := `{"success":true,"user_stats":null,"popular_agents":[],"message":"Global analytics not yet implemented"}`
	if rec.Code != http.StatusOK || rec.Body.String() != want {
		t.Fatalf("got %d %s, want 200 %s", rec.Code, rec.Body.String(), want)
	}
}

func TestAgentMgmtMountNullMessageAndPydanticTime(t *testing.T) {
	withAgentMgmtUser(t)
	mux := agentMgmtTestMux(t, &fakeAgentMgmtFacade{templates: []*amentities.AgentTemplate{agentMgmtTestTemplate(t)}})
	rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/templates", "", true)
	body := rec.Body.String()
	if !strings.Contains(body, `"message":null`) {
		t.Errorf("list response must keep the nullable message field: %s", body)
	}
	if !strings.Contains(body, `"created_at":"2024-01-02T03:04:05.123456Z"`) {
		t.Errorf("datetime must use pydantic v2 form: %s", body)
	}
	if !strings.Contains(body, `"rules":null`) {
		t.Errorf("nil rules must serialize as null: %s", body)
	}
}

func TestAgentMgmtPydanticTime(t *testing.T) {
	cases := []struct {
		in   time.Time
		want string
	}{
		{time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC), "2024-01-01T00:00:00Z"},
		{time.Date(2024, 1, 1, 0, 0, 0, 500000000, time.UTC), "2024-01-01T00:00:00.500000Z"},
		{time.Date(2024, 1, 1, 0, 0, 0, 1000000, time.UTC), "2024-01-01T00:00:00.001000Z"},
	}
	for _, c := range cases {
		if got := agentMgmtPydanticTime(c.in); got != c.want {
			t.Errorf("agentMgmtPydanticTime(%v) = %s, want %s", c.in, got, c.want)
		}
	}
}

func TestAgentMgmtMountWithNilSessionsDoesNotPanic(t *testing.T) {
	defer func() {
		if r := recover(); r != nil {
			t.Fatalf("mountAgentManagementRoutes(nil) panicked: %v", r)
		}
	}()
	mux := http.NewServeMux()
	mountAgentManagementRoutes(mux, nil)
	// Auth rejects before any database access.
	if rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/templates", "", false); rec.Code != http.StatusForbidden {
		t.Fatalf("got %d, want 403", rec.Code)
	}
	// Pagination validation runs before the facade lookup.
	if rec := agentMgmtDo(mux, http.MethodGet, "/api/v2/agent-management/marketplace?page=0", "", false); rec.Code != http.StatusBadRequest {
		t.Fatalf("got %d, want 400", rec.Code)
	}
}

// --- facade adapter ---

type baseAgentMgmtAPI struct{}

func (baseAgentMgmtAPI) ListAvailableTemplates(context.Context) ([]*amentities.AgentTemplate, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) GetTemplateBySlug(context.Context, string) (*amentities.AgentTemplate, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) GetTemplateByID(context.Context, string) (*amentities.AgentTemplate, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) GetUserInstances(context.Context, *amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) GetOrCreateInstance(context.Context, *amvo.UserId, string) (*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) BulkCreateInstances(context.Context, *amvo.UserId, []string) ([]*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) UpdateInstance(context.Context, *amvo.UserId, string, *string, *bool, *string, *[]string, *tmentities.OrderedMap[any], *[]string, *string, *string) (*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) DeleteInstance(context.Context, *amvo.UserId, string) (bool, error) {
	return false, nil
}
func (baseAgentMgmtAPI) UpdateConfiguration(context.Context, *amvo.UserId, string, *string, *[]string, *tmentities.OrderedMap[any], *[]string, *string) (*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) ResetConfiguration(context.Context, *amvo.UserId, string) (*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) ShareAgent(context.Context, *amvo.UserId, string) (*string, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) UnshareAgent(context.Context, *amvo.UserId, string) (bool, error) {
	return false, nil
}
func (baseAgentMgmtAPI) ImportAgent(context.Context, string, *amvo.UserId, *string) (*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) GetMarketplaceAgents(context.Context, int, int, enums.InstanceOrdering) ([]*amentities.UserAgentInstance, error) {
	return nil, nil
}
func (baseAgentMgmtAPI) GetSharedAgentPreview(context.Context, string) (*amentities.UserAgentInstance, error) {
	return nil, nil
}

type recordingAgentMgmtAPI struct {
	baseAgentMgmtAPI
	user    *amvo.UserId
	tools   *[]string
	rules   *[]string
	email   *string
	limit   int
	offset  int
	orderBy enums.InstanceOrdering
}

func (r *recordingAgentMgmtAPI) GetUserInstances(_ context.Context, userID *amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	r.user = userID
	return nil, nil
}

func (r *recordingAgentMgmtAPI) UpdateInstance(_ context.Context, _ *amvo.UserId, _ string, _ *string, _ *bool, _ *string, tools *[]string, _ *tmentities.OrderedMap[any], rules *[]string, _ *string, _ *string) (*amentities.UserAgentInstance, error) {
	r.tools, r.rules = tools, rules
	return nil, nil
}

func (r *recordingAgentMgmtAPI) ImportAgent(_ context.Context, _ string, _ *amvo.UserId, email *string) (*amentities.UserAgentInstance, error) {
	r.email = email
	return nil, nil
}

func (r *recordingAgentMgmtAPI) GetMarketplaceAgents(_ context.Context, limit, offset int, orderBy enums.InstanceOrdering) ([]*amentities.UserAgentInstance, error) {
	r.limit, r.offset, r.orderBy = limit, offset, orderBy
	return nil, nil
}

func TestAgentMgmtFacadeAdapterConvertsSignatures(t *testing.T) {
	uid, err := amvo.NewUserId("11111111-1111-1111-1111-111111111111")
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()

	rec := &recordingAgentMgmtAPI{}
	adapter := agentManagementFacadeAdapter{f: rec}
	if _, err := adapter.GetUserInstances(ctx, uid); err != nil {
		t.Fatal(err)
	}
	if rec.user == nil || rec.user.Value != uid.Value {
		t.Fatalf("GetUserInstances user = %+v, want %s", rec.user, uid.Value)
	}

	// Absent/None list stays nil; an explicit (even empty) list is forwarded non-nil.
	rec = &recordingAgentMgmtAPI{}
	adapter = agentManagementFacadeAdapter{f: rec}
	if _, err := adapter.UpdateInstance(ctx, uid, "i", nil, nil, nil, nil, nil, nil, nil, nil); err != nil {
		t.Fatal(err)
	}
	if rec.tools != nil || rec.rules != nil {
		t.Fatalf("nil lists must stay nil: tools=%v rules=%v", rec.tools, rec.rules)
	}
	if _, err := adapter.UpdateInstance(ctx, uid, "i", nil, nil, nil, []string{}, nil, []string{"r"}, nil, nil); err != nil {
		t.Fatal(err)
	}
	if rec.tools == nil || len(*rec.tools) != 0 {
		t.Fatalf("explicit empty list must be forwarded non-nil: %v", rec.tools)
	}
	if rec.rules == nil || len(*rec.rules) != 1 {
		t.Fatalf("rules = %v, want one element", rec.rules)
	}

	rec = &recordingAgentMgmtAPI{}
	adapter = agentManagementFacadeAdapter{f: rec}
	if _, err := adapter.ImportAgent(ctx, "tok", uid, "a@b.c"); err != nil {
		t.Fatal(err)
	}
	if rec.email == nil || *rec.email != "a@b.c" {
		t.Fatalf("ImportAgent email = %v, want a@b.c", rec.email)
	}

	rec = &recordingAgentMgmtAPI{}
	adapter = agentManagementFacadeAdapter{f: rec}
	if _, err := adapter.GetMarketplaceAgents(ctx, 5, 10); err != nil {
		t.Fatal(err)
	}
	if rec.limit != 5 || rec.offset != 10 || rec.orderBy != enums.InstanceOrderingCreatedDesc {
		t.Fatalf("marketplace args = %d/%d/%s", rec.limit, rec.offset, rec.orderBy)
	}
}
