package httpapp

// openrig_mount.go serves the user's agents as OpenRig AgentSpec directories.
// OpenRig is the client and 4genthub is the cloud: OpenRig resolves agent_ref only
// from local:/path: directories (rigspec-schema.ts, agent-resolver.ts), so the client
// downloads these files and writes them to disk (scripts/openrig_sync.py).
//
//	GET /api/v2/openrig/agents          every available agent
//	GET /api/v2/openrig/agents/{slug}   one agent
//
// Each spec is rendered from the caller's own agent instance, so customizations made
// in 4genthub reach the OpenRig seat.

import (
	"context"
	"net/http"
	"os"
	"strings"

	agentfacades "agenthub/fastmcp/agent_management/application/facades"
	agentservices "agenthub/fastmcp/agent_management/application/services"
	amentities "agenthub/fastmcp/agent_management/domain/entities"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	agentorm "agenthub/fastmcp/agent_management/infrastructure/repositories/orm"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// publicURLEnv names the externally reachable base URL of this server. Rendered specs
// embed it so a seat can call back into the 4genthub MCP endpoint.
const publicURLEnv = "AGENTHUB_PUBLIC_URL"

// openRigAgentSource is the facade surface the OpenRig routes need.
type openRigAgentSource interface {
	GetOrCreateInstance(ctx context.Context, userID *amvo.UserId, agentSlug string) (*amentities.UserAgentInstance, error)
	GetTemplateBySlug(ctx context.Context, agentSlug string) (*amentities.AgentTemplate, error)
	ListAvailableTemplates(ctx context.Context) ([]*amentities.AgentTemplate, error)
}

// newOpenRigAgentSource is a package variable so tests can substitute a fake without
// a database, like newCallAgentProvider.
var newOpenRigAgentSource = func(sessions *database.SessionManager) (openRigAgentSource, error) {
	templateRepo, err := agentorm.NewORMAgentTemplateRepository(sessions)
	if err != nil {
		return nil, err
	}
	instanceRepo, err := agentorm.NewORMUserAgentInstanceRepository(sessions)
	if err != nil {
		return nil, err
	}
	return agentfacades.NewAgentManagementFacade(templateRepo, instanceRepo, nil, nil), nil
}

func mountOpenRigRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	const base = "/api/v2/openrig/agents"
	mux.HandleFunc("GET "+base, authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleOpenRigAgents(w, r, u, sessions, "")
	}))
	mux.HandleFunc("GET "+base+"/{slug}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleOpenRigAgents(w, r, u, sessions, r.PathValue("slug"))
	}))
}

// handleOpenRigAgents renders one agent when slug is set, otherwise every template.
func handleOpenRigAgents(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager, slug string) {
	publicURL := strings.TrimRight(os.Getenv(publicURLEnv), "/")
	if publicURL == "" {
		writeDetail(w, http.StatusInternalServerError, publicURLEnv+" is not set")
		return
	}
	mcpURL := publicURL + "/mcp"

	uid, err := amvo.NewUserId(userID(u))
	if err != nil {
		writeDetail(w, http.StatusUnauthorized, "Invalid user id")
		return
	}
	source, err := newOpenRigAgentSource(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}

	ctx := r.Context()
	var templates []*amentities.AgentTemplate
	if slug != "" {
		template, err := source.GetTemplateBySlug(ctx, slug)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, err.Error())
			return
		}
		if template == nil {
			writeDetail(w, http.StatusNotFound, "Agent not found: "+slug)
			return
		}
		templates = []*amentities.AgentTemplate{template}
	} else if templates, err = source.ListAvailableTemplates(ctx); err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}

	specs := make([]any, 0, len(templates))
	for _, template := range templates {
		instance, err := source.GetOrCreateInstance(ctx, &uid, template.Slug)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, "load "+template.Slug+": "+err.Error())
			return
		}
		spec, err := agentservices.RenderOpenRigSpec(template, *instance.Configuration, mcpURL)
		if err != nil {
			writeDetail(w, http.StatusInternalServerError, "render "+template.Slug+": "+err.Error())
			return
		}
		specs = append(specs, openRigSpecBody(spec))
	}

	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	if slug != "" {
		body.Set("agent", specs[0])
	} else {
		body.Set("agents", specs)
		body.Set("count", len(specs))
	}
	writeJSON(w, http.StatusOK, body)
}

func openRigSpecBody(spec *agentservices.OpenRigSpec) *entities.OrderedMap[any] {
	files := make([]any, 0, len(spec.Files))
	for _, f := range spec.Files {
		file := entities.NewOrderedMap[any]()
		file.Set("path", f.Path)
		file.Set("content", f.Content)
		files = append(files, file)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("slug", spec.Slug)
	body.Set("name", spec.Name)
	body.Set("version", spec.Version)
	body.Set("files", files)
	return body
}
