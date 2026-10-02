package httpapp

// agents_mount.go mounts the five /api/v2/agents endpoints of
// fastmcp/server/routes/agent_routes.py that App.Handler does not already serve.
// GET /metadata and GET /{agent_name} are registered by mountAgentRoutes
// (routes_mount.go); mountAgentsRoutes must not repeat them.
//
// The Python module also exposes GET /capabilities, which is outside this slice: it
// is left unregistered so it cannot collide with mountAgentRoutes' GET
// /api/v2/agents/{agent_name} pattern or with another worker's mount.

import (
	"context"
	"net/http"
	"runtime/debug"
	"strings"

	agentfacades "agenthub/fastmcp/agent_management/application/facades"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	agentorm "agenthub/fastmcp/agent_management/infrastructure/repositories/orm"
	mcpcontrollers "agenthub/fastmcp/agent_management/interface/mcp_controllers"
	authdomain "agenthub/fastmcp/auth/domain/entities"
	usecases "agenthub/fastmcp/task_management/application/use_cases"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// mountAgentsRoutes registers agent_routes.py's assign, unassign, branch
// assignment, project assignments and call endpoints. The leader wires it into
// App.Handler alongside mountRoutes.
func mountAgentsRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	const base = "/api/v2/agents"

	// agent_routes.py's assign_agent_to_branch takes branch_id/agent_id as FastAPI
	// query parameters (no Form/Body annotation), then calls
	// AgentAPIController.assign_agent, which the controller does not define:
	// AttributeError is swallowed by the route's except Exception and returned as
	// 500 "Failed to assign agent". The Go controller likewise has no assignment
	// methods, so the port preserves the Python quirk instead of inventing
	// behaviour.
	mux.HandleFunc("POST "+base+"/assign", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		var missing []string
		if !r.URL.Query().Has("branch_id") {
			missing = append(missing, "branch_id")
		}
		if !r.URL.Query().Has("agent_id") {
			missing = append(missing, "agent_id")
		}
		if len(missing) > 0 {
			writeMissing(w, "query", missing...)
			return
		}
		writeDetail(w, http.StatusInternalServerError, "Failed to assign agent")
	}))

	mux.HandleFunc("DELETE "+base+"/unassign/{branch_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeDetail(w, http.StatusInternalServerError, "Failed to unassign agent")
	}))

	mux.HandleFunc("GET "+base+"/branch/{branch_id}/assignment", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeDetail(w, http.StatusInternalServerError, "Failed to get agent assignment")
	}))

	mux.HandleFunc("GET "+base+"/project/{project_id}/assignments", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeDetail(w, http.StatusInternalServerError, "Failed to get assignments")
	}))

	mux.HandleFunc("POST "+base+"/call", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleAgentCall(w, r, u, sessions)
	}))
}

// handleAgentCall ports agent_routes.py's call_agent POST /call. The Python route
// builds AgentManagementFacade over the request's session and returns
// {"success", "agent", "source", "called_by"}; the Go port drives the same logic
// through CallAgentUseCase, which wraps the ported facade.
func handleAgentCall(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	m, ok := jsonBody(w, r)
	if !ok {
		return
	}
	agentName := getOptString(m, "agent_name")
	if agentName == "" {
		writeDetail(w, http.StatusBadRequest, "agent_name is required")
		return
	}

	// Python builds UserId(current_user.id) before the facade call; a non-UUID id
	// raises ValueError, which the route's except ValueError turns into 404.
	userIDVO, err := amvo.NewUserId(userID(u))
	if err != nil {
		writeDetail(w, http.StatusNotFound, "Agent not found: "+agentName)
		return
	}

	provider, err := newCallAgentProvider(sessions)
	if err != nil {
		writeAgentCallFailure(w, err.Error())
		return
	}
	useCase := usecases.NewCallAgentUseCase(agentCallAuth{userID: userIDVO.Value}, provider)
	result := useCase.Execute(r.Context(), agentName, nil)

	if success, _ := result.Get("success"); success == true {
		result.Set("called_by", u.Email)
		writeJSON(w, http.StatusOK, result)
		return
	}
	if raw, _ := result.Get("error"); isAgentNotFound(raw) {
		writeDetail(w, http.StatusNotFound, "Agent not found: "+agentName)
		return
	}
	message := "unknown error"
	if raw, ok := result.Get("message"); ok {
		if s, ok := raw.(string); ok && s != "" {
			message = s
		}
	}
	writeAgentCallFailure(w, message)
}

// newCallAgentProvider builds the agent-config facade behind POST /call. Python
// constructs ORMAgentTemplateRepository()/ORMUserAgentInstanceRepository() over
// the request session; the Go repositories take the SessionManager. It is a
// package variable so tests can substitute a fake without a database.
var newCallAgentProvider = func(sessions *database.SessionManager) (mcpcontrollers.AgentConfigProvider, error) {
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

// agentCallAuth supplies the already-authenticated user id to CallAgentUseCase.
// The route resolves the bearer token before the handler runs, so no lookup is
// needed here.
type agentCallAuth struct{ userID string }

func (a agentCallAuth) GetAuthenticatedUserID(context.Context, *string, string) (string, error) {
	return a.userID, nil
}

// isAgentNotFound reports whether CallAgentUseCase's error field is its
// ValueError mapping, which the Python route raises as 404.
func isAgentNotFound(raw any) bool {
	s, ok := raw.(string)
	return ok && strings.HasPrefix(s, "Agent not found:")
}

// writeAgentCallFailure is agent_routes.py's except Exception branch: a 200 body
// with the failing error and a traceback, not an HTTP error status.
func writeAgentCallFailure(w http.ResponseWriter, errText string) {
	body := entities.NewOrderedMap[any]()
	body.Set("success", false)
	body.Set("message", "Failed to call agent")
	body.Set("error", errText)
	body.Set("traceback", string(debug.Stack()))
	writeJSON(w, http.StatusOK, body)
}
