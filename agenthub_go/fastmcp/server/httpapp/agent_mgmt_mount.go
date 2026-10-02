// agent_mgmt_mount.go mounts the agent management REST router
// (agenthub_main/src/fastmcp/agent_management/interface/rest/agent_management_routes.py)
// on net/http. The route handlers themselves live in
// fastmcp/agent_management/interface/rest; this file only builds the facade from the
// database session, adapts its pointer-based signatures to the rest.Facade surface, and
// serializes the response DTOs the way pydantic v2 does.
package httpapp

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"reflect"
	"strings"
	"time"

	amfacades "agenthub/fastmcp/agent_management/application/facades"
	amentities "agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	amorm "agenthub/fastmcp/agent_management/infrastructure/repositories/orm"
	amrest "agenthub/fastmcp/agent_management/interface/rest"
	"agenthub/fastmcp/auth"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// mountAgentManagementRoutes registers every route of the Python router
// APIRouter(prefix="/api/v2/agent-management", tags=["Agent Management - User Instances"]):
// templates (list/get), instances CRUD plus bulk-create, analytics usage/popular,
// configuration get/put/reset, share/unshare, import and marketplace browse/preview.
func mountAgentManagementRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mountAgentManagementRoutesWithFacade(mux, newAgentManagementFacade(sessions))
}

// newAgentManagementFacade is get_facade: the two ORM repositories over the request
// session wrapped in AgentManagementFacade.
func newAgentManagementFacade(sessions *database.SessionManager) amrest.Facade {
	templateRepo, _ := amorm.NewORMAgentTemplateRepository(sessions)
	instanceRepo, _ := amorm.NewORMUserAgentInstanceRepository(sessions)
	facade := amfacades.NewAgentManagementFacade(templateRepo, instanceRepo, nil, nil)
	facade.HistoryRecorder = agentImportHistoryRecorder{sessions: sessions}
	return agentManagementFacadeAdapter{f: facade}
}

// mountAgentManagementRoutesWithFacade registers the routes against an already built
// facade (the seam the tests use).
func mountAgentManagementRoutesWithFacade(mux *http.ServeMux, facade amrest.Facade) {
	const base = "/api/v2/agent-management"

	// --- agent templates (read-only) ---

	mux.HandleFunc("GET "+base+"/templates", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.ListTemplates(r.Context(), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("GET "+base+"/templates/{slug}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.GetTemplate(r.Context(), r.PathValue("slug"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))

	// --- user agent instances (CRUD) ---

	mux.HandleFunc("GET "+base+"/instances", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.ListUserInstances(r.Context(), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("GET "+base+"/instances/{instance_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.GetInstance(r.Context(), r.PathValue("instance_id"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("POST "+base+"/instances", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		req, ok := agentMgmtCreateInstanceRequest(w, m)
		if !ok {
			return
		}
		body, err := amrest.CreateInstance(r.Context(), req, u, facade)
		writeAgentManagementResult(w, http.StatusCreated, body, err)
	}))
	mux.HandleFunc("POST "+base+"/instances/bulk-create", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.BulkCreateInstances(r.Context(), u, facade)
		writeAgentManagementResult(w, http.StatusCreated, body, err)
	}))
	mux.HandleFunc("PUT "+base+"/instances/{instance_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		body, err := amrest.UpdateInstance(r.Context(), r.PathValue("instance_id"), agentMgmtUpdateInstanceRequest(m), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/instances/{instance_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.DeleteInstance(r.Context(), r.PathValue("instance_id"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))

	// --- usage analytics ---

	mux.HandleFunc("GET "+base+"/analytics/usage", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.GetUserUsageStats(r.Context(), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("GET "+base+"/analytics/popular", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.GetPopularAgents(r.Context(), u, facade, queryIntDefault(r, "limit", 10))
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))

	// --- agent configuration ---

	mux.HandleFunc("GET "+base+"/configuration/{slug}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.GetConfiguration(r.Context(), r.PathValue("slug"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("PUT "+base+"/configuration/{slug}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		body, err := amrest.UpdateConfiguration(r.Context(), r.PathValue("slug"), agentMgmtUpdateConfigurationRequest(m), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("POST "+base+"/configuration/{slug}/reset", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.ResetConfiguration(r.Context(), r.PathValue("slug"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))

	// --- agent sharing ---

	mux.HandleFunc("POST "+base+"/instances/{instance_id}/share", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.ShareAgent(r.Context(), r.PathValue("instance_id"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("POST "+base+"/instances/{instance_id}/unshare", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := amrest.UnshareAgent(r.Context(), r.PathValue("instance_id"), u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))
	mux.HandleFunc("POST "+base+"/import", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		req, ok := agentMgmtImportRequest(w, m)
		if !ok {
			return
		}
		body, err := amrest.ImportAgent(r.Context(), req, u, facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	}))

	// --- marketplace (public: no current_user dependency in Python) ---

	mux.HandleFunc("GET "+base+"/marketplace", func(w http.ResponseWriter, r *http.Request) {
		body, err := amrest.BrowseMarketplace(r.Context(), queryOpt(r, "category"), queryOpt(r, "search"), agentMgmtSortOpt(r),
			queryIntDefault(r, "page", 1), queryIntDefault(r, "page_size", 50), facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	})
	mux.HandleFunc("GET "+base+"/marketplace/{share_token}", func(w http.ResponseWriter, r *http.Request) {
		body, err := amrest.PreviewSharedAgent(r.Context(), r.PathValue("share_token"), facade)
		writeAgentManagementResult(w, http.StatusOK, body, err)
	})
}

// --- request parsing (pydantic request models) ---

func agentMgmtCreateInstanceRequest(w http.ResponseWriter, m map[string]any) (amrest.CreateInstanceRequest, bool) {
	slug, ok := m["template_slug"].(string)
	if !ok {
		writeMissing(w, "body", "template_slug")
		return amrest.CreateInstanceRequest{}, false
	}
	visibility := "private"
	if v, ok := m["visibility"].(string); ok {
		visibility = v
	}
	return amrest.CreateInstanceRequest{
		TemplateSlug: slug,
		AgentName:    optString(m, "agent_name"),
		SystemPrompt: optString(m, "system_prompt"),
		Tools:        stringList(m, "tools"),
		Capabilities: orderedMapOf(m["capabilities"]),
		Rules:        stringList(m, "rules"),
		OutputFormat: optString(m, "output_format"),
		Visibility:   visibility,
	}, true
}

func agentMgmtUpdateInstanceRequest(m map[string]any) amrest.UpdateInstanceRequest {
	return amrest.UpdateInstanceRequest{
		AgentName:    optString(m, "agent_name"),
		IsEnabled:    agentMgmtBoolPtr(m, "is_enabled"),
		SystemPrompt: optString(m, "system_prompt"),
		Tools:        stringList(m, "tools"),
		Capabilities: orderedMapOf(m["capabilities"]),
		Rules:        stringList(m, "rules"),
		OutputFormat: optString(m, "output_format"),
		Visibility:   optString(m, "visibility"),
	}
}

func agentMgmtUpdateConfigurationRequest(m map[string]any) amrest.UpdateConfigurationRequest {
	return amrest.UpdateConfigurationRequest{
		SystemPrompt: optString(m, "system_prompt"),
		Tools:        stringList(m, "tools"),
		Capabilities: orderedMapOf(m["capabilities"]),
		Rules:        stringList(m, "rules"),
		OutputFormat: optString(m, "output_format"),
	}
}

func agentMgmtImportRequest(w http.ResponseWriter, m map[string]any) (amrest.ImportAgentRequest, bool) {
	token, ok := m["share_token"].(string)
	if !ok {
		writeMissing(w, "body", "share_token")
		return amrest.ImportAgentRequest{}, false
	}
	return amrest.ImportAgentRequest{ShareToken: token}, true
}

func agentMgmtBoolPtr(m map[string]any, key string) *bool {
	if v, ok := m[key]; ok {
		if b, ok := v.(bool); ok {
			return &b
		}
	}
	return nil
}

// agentMgmtSortOpt is the FastAPI query parameter sort: str | None = "recent".
func agentMgmtSortOpt(r *http.Request) *string {
	v := queryDefault(r, "sort", "recent")
	return &v
}

// --- response serialization (pydantic v2 model_dump_json) ---

// writeAgentManagementResult writes a rest handler result: an *auth.HTTPException as its
// status with a {"detail": ...} body, otherwise the DTO in pydantic v2 JSON.
func writeAgentManagementResult(w http.ResponseWriter, status int, body any, err error) {
	if err != nil {
		var he *auth.HTTPException
		if errors.As(err, &he) {
			writeDetail(w, he.StatusCode, he.Detail)
			return
		}
		writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
		return
	}
	out, jerr := tmvo.PyJSONDumpsCompact(agentMgmtResponseValue(body))
	if jerr != nil {
		writeDetail(w, http.StatusInternalServerError, "Internal Server Error")
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write([]byte(out))
}

// agentMgmtResponseValue converts a response DTO into the JSON value pydantic v2 emits:
// every struct field is present in declaration order (a nil pointer is null, including the
// optional message/data fields Go's encoding/json would drop with omitempty), dict fields
// stay ordered maps, and datetimes use pydantic's RFC3339 form (Z for UTC, six fractional
// digits when non-zero).
func agentMgmtResponseValue(v any) any {
	if v == nil {
		return nil
	}
	switch x := v.(type) {
	case time.Time:
		return agentMgmtPydanticTime(x)
	case *time.Time:
		if x == nil {
			return nil
		}
		return agentMgmtPydanticTime(*x)
	}
	if _, ok := v.(tmvo.OrderedAny); ok {
		return v
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Pointer, reflect.Interface:
		if rv.IsNil() {
			return nil
		}
		return agentMgmtResponseValue(rv.Elem().Interface())
	case reflect.Slice:
		if rv.IsNil() {
			return nil
		}
		out := make([]any, rv.Len())
		for i := range out {
			out[i] = agentMgmtResponseValue(rv.Index(i).Interface())
		}
		return out
	case reflect.Array:
		out := make([]any, rv.Len())
		for i := range out {
			out[i] = agentMgmtResponseValue(rv.Index(i).Interface())
		}
		return out
	case reflect.Struct:
		m := tmentities.NewOrderedMap[any]()
		typ := rv.Type()
		for i := 0; i < typ.NumField(); i++ {
			f := typ.Field(i)
			if !f.IsExported() {
				continue
			}
			name, _, _ := strings.Cut(f.Tag.Get("json"), ",")
			if name == "-" {
				continue
			}
			if name == "" {
				name = f.Name
			}
			m.Set(name, agentMgmtResponseValue(rv.Field(i).Interface()))
		}
		return m
	}
	return v
}

// agentMgmtPydanticTime is pydantic v2's datetime serialization for an aware datetime.
func agentMgmtPydanticTime(t time.Time) string {
	s := t.Format("2006-01-02T15:04:05")
	if us := t.Nanosecond() / 1000; us != 0 {
		s += fmt.Sprintf(".%06d", us)
	}
	_, off := t.Zone()
	if off == 0 {
		return s + "Z"
	}
	sign := "+"
	if off < 0 {
		sign, off = "-", -off
	}
	return s + fmt.Sprintf("%s%02d:%02d", sign, off/3600, off%3600/60)
}

// --- facade adapter ---

// agentManagementFacadeAPI is the AgentManagementFacade method set the HTTP adapter
// forwards to; *amfacades.AgentManagementFacade implements it.
type agentManagementFacadeAPI interface {
	ListAvailableTemplates(ctx context.Context) ([]*amentities.AgentTemplate, error)
	GetTemplateBySlug(ctx context.Context, agentSlug string) (*amentities.AgentTemplate, error)
	GetTemplateByID(ctx context.Context, templateID string) (*amentities.AgentTemplate, error)
	GetUserInstances(ctx context.Context, userID *amvo.UserId) ([]*amentities.UserAgentInstance, error)
	GetOrCreateInstance(ctx context.Context, userID *amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error)
	BulkCreateInstances(ctx context.Context, userID *amvo.UserId, templateSlugs []string) ([]*amentities.UserAgentInstance, error)
	UpdateInstance(ctx context.Context, userID *amvo.UserId, instanceID string, agentName *string, isEnabled *bool, systemPrompt *string, tools *[]string, capabilities *tmentities.OrderedMap[any], rules *[]string, outputFormat *string, visibility *string) (*amentities.UserAgentInstance, error)
	DeleteInstance(ctx context.Context, userID *amvo.UserId, instanceID string) (bool, error)
	UpdateConfiguration(ctx context.Context, userID *amvo.UserId, agentSlug string, systemPrompt *string, tools *[]string, capabilities *tmentities.OrderedMap[any], rules *[]string, outputFormat *string) (*amentities.UserAgentInstance, error)
	ResetConfiguration(ctx context.Context, userID *amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error)
	ShareAgent(ctx context.Context, userID *amvo.UserId, instanceID string) (*string, error)
	UnshareAgent(ctx context.Context, userID *amvo.UserId, instanceID string) (bool, error)
	ImportAgent(ctx context.Context, shareToken string, importerUserID *amvo.UserId, creatorEmail *string) (*amentities.UserAgentInstance, error)
	GetMarketplaceAgents(ctx context.Context, limit, offset int, orderBy enums.InstanceOrdering) ([]*amentities.UserAgentInstance, error)
	GetSharedAgentPreview(ctx context.Context, shareToken string) (*amentities.UserAgentInstance, error)
}

// agentManagementFacadeAdapter adapts the facade's pointer user ids and pointer option
// lists to the value-based amrest.Facade surface.
type agentManagementFacadeAdapter struct{ f agentManagementFacadeAPI }

var (
	_ amrest.Facade            = agentManagementFacadeAdapter{}
	_ agentManagementFacadeAPI = (*amfacades.AgentManagementFacade)(nil)
)

func (a agentManagementFacadeAdapter) ListAvailableTemplates(ctx context.Context) ([]*amentities.AgentTemplate, error) {
	return a.f.ListAvailableTemplates(ctx)
}

func (a agentManagementFacadeAdapter) GetTemplateBySlug(ctx context.Context, agentSlug string) (*amentities.AgentTemplate, error) {
	return a.f.GetTemplateBySlug(ctx, agentSlug)
}

func (a agentManagementFacadeAdapter) GetTemplateByID(ctx context.Context, templateID string) (*amentities.AgentTemplate, error) {
	return a.f.GetTemplateByID(ctx, templateID)
}

func (a agentManagementFacadeAdapter) GetUserInstances(ctx context.Context, userID amvo.UserId) ([]*amentities.UserAgentInstance, error) {
	return a.f.GetUserInstances(ctx, &userID)
}

func (a agentManagementFacadeAdapter) GetOrCreateInstance(ctx context.Context, userID amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error) {
	return a.f.GetOrCreateInstance(ctx, &userID, agentSlug)
}

func (a agentManagementFacadeAdapter) BulkCreateInstances(ctx context.Context, userID amvo.UserId, templateSlugs []string) ([]*amentities.UserAgentInstance, error) {
	return a.f.BulkCreateInstances(ctx, &userID, templateSlugs)
}

func (a agentManagementFacadeAdapter) UpdateInstance(ctx context.Context, userID amvo.UserId, instanceID string, agentName *string, isEnabled *bool, systemPrompt *string, tools []string, capabilities *tmentities.OrderedMap[any], rules []string, outputFormat *string, visibility *string) (*amentities.UserAgentInstance, error) {
	return a.f.UpdateInstance(ctx, &userID, instanceID, agentName, isEnabled, systemPrompt, agentMgmtSlicePtr(tools), capabilities, agentMgmtSlicePtr(rules), outputFormat, visibility)
}

func (a agentManagementFacadeAdapter) DeleteInstance(ctx context.Context, userID amvo.UserId, instanceID string) (bool, error) {
	return a.f.DeleteInstance(ctx, &userID, instanceID)
}

func (a agentManagementFacadeAdapter) UpdateConfiguration(ctx context.Context, userID amvo.UserId, agentSlug string, systemPrompt *string, tools []string, capabilities *tmentities.OrderedMap[any], rules []string, outputFormat *string) (*amentities.UserAgentInstance, error) {
	return a.f.UpdateConfiguration(ctx, &userID, agentSlug, systemPrompt, agentMgmtSlicePtr(tools), capabilities, agentMgmtSlicePtr(rules), outputFormat)
}

func (a agentManagementFacadeAdapter) ResetConfiguration(ctx context.Context, userID amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error) {
	return a.f.ResetConfiguration(ctx, &userID, agentSlug)
}

func (a agentManagementFacadeAdapter) ShareAgent(ctx context.Context, userID amvo.UserId, instanceID string) (*string, error) {
	return a.f.ShareAgent(ctx, &userID, instanceID)
}

func (a agentManagementFacadeAdapter) UnshareAgent(ctx context.Context, userID amvo.UserId, instanceID string) (bool, error) {
	return a.f.UnshareAgent(ctx, &userID, instanceID)
}

func (a agentManagementFacadeAdapter) ImportAgent(ctx context.Context, shareToken string, importerUserID amvo.UserId, creatorEmail string) (*amentities.UserAgentInstance, error) {
	return a.f.ImportAgent(ctx, shareToken, &importerUserID, &creatorEmail)
}

func (a agentManagementFacadeAdapter) GetMarketplaceAgents(ctx context.Context, limit, offset int) ([]*amentities.UserAgentInstance, error) {
	return a.f.GetMarketplaceAgents(ctx, limit, offset, enums.InstanceOrderingCreatedDesc)
}

func (a agentManagementFacadeAdapter) GetSharedAgentPreview(ctx context.Context, shareToken string) (*amentities.UserAgentInstance, error) {
	return a.f.GetSharedAgentPreview(ctx, shareToken)
}

// agentMgmtSlicePtr is Python's None sentinel for an optional list request field: an
// absent/null list stays nil, an explicitly supplied list (including []) is forwarded.
func agentMgmtSlicePtr(v []string) *[]string {
	if v == nil {
		return nil
	}
	return &v
}

// --- import history ---

// agentImportHistoryRecorder writes the agent_import_history row the Python facade
// commits after a successful import.
type agentImportHistoryRecorder struct{ sessions *database.SessionManager }

var _ amfacades.ImportHistoryRecorder = agentImportHistoryRecorder{}

func (r agentImportHistoryRecorder) RecordAgentImportHistory(ctx context.Context, importerUserID, sourceInstanceID, importedInstanceID, shareToken string) error {
	if r.sessions == nil {
		return nil
	}
	return r.sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`INSERT INTO agent_import_history ("id", "importer_user_id", "source_instance_id", "imported_instance_id", "imported_at", "share_token") `+
				`VALUES ($1, $2, $3, $4, $5, $6)`,
			tmvo.NewUUIDv4(), importerUserID, sourceInstanceID, importedInstanceID, time.Now().UTC(), shareToken)
		return err
	})
}
