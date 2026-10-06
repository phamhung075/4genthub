package httpapp

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"

	"agenthub/fastmcp/auth"
	authperm "agenthub/fastmcp/auth/domain"
	"agenthub/fastmcp/auth/middleware"
	"agenthub/fastmcp/config"
	seatcontrollers "agenthub/fastmcp/seat_management/interface/mcp_controllers"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

// DiagnosticsProvider provides server diagnostics for MCP tools.
type DiagnosticsProvider interface {
	GetMCPStatus(reqID, sessionID string) any
	SessionHealthCheck(reqID, sessionID string) any
}

var globalDiagnosticsProvider DiagnosticsProvider

// SetDiagnosticsProvider registers the diagnostics provider.
func SetDiagnosticsProvider(p DiagnosticsProvider) {
	globalDiagnosticsProvider = p
}

type jsonRPCRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      any             `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type jsonRPCResponse struct {
	JSONRPC string        `json:"jsonrpc"`
	ID      any           `json:"id"`
	Result  any           `json:"result,omitempty"`
	Error   *jsonRPCError `json:"error,omitempty"`
}

type jsonRPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// mcpProtocolVersion is the MCP protocol revision this server implements, and it is NOT the
// release identity: a protocol revision names a wire contract, a release names a build.
//
// It is 2025-03-26 because that is what the implementation actually matches, measured rather than
// assumed. Streamable HTTP's single POST+GET endpoint arrived in 2025-03-26 and is what this
// server serves; 2024-11-05's transport is HTTP+SSE, whose `endpoint` event and separate
// /messages POST path this server does not implement at all. JSON-RPC batching is accepted here
// and was removed in 2025-06-18; the `MCP-Protocol-Version` header requirement and structured
// tool output also arrived in 2025-06-18 and are not implemented. Claiming 2025-06-18 would be a
// lie to the client; claiming 2024-11-05 promised a transport no client can use against this
// server.
//
// Both places that advertise it read this one literal - the initialize result and the
// register_mcp_client response - because two surfaces disagreeing is how the version-string
// defect started.
const mcpProtocolVersion = "2025-03-26"

func (a *App) registerMCPRoutes(mux *http.ServeMux) {
	mux.HandleFunc("POST /mcp", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			_ = json.NewEncoder(w).Encode(jsonRPCResponse{
				JSONRPC: "2.0",
				ID:      nil,
				Error:   &jsonRPCError{Code: -32700, Message: "Parse error"},
			})
			return
		}

		trimmed := strings.TrimSpace(string(bodyBytes))
		if strings.HasPrefix(trimmed, "[") {
			var batch []jsonRPCRequest
			if err := json.Unmarshal(bodyBytes, &batch); err != nil {
				_ = json.NewEncoder(w).Encode(jsonRPCResponse{
					JSONRPC: "2.0",
					ID:      nil,
					Error:   &jsonRPCError{Code: -32700, Message: "Parse error"},
				})
				return
			}
			for _, req := range batch {
				if !a.authorizeMCPMethod(w, r, req.Method) {
					return
				}
			}
			var responses []jsonRPCResponse
			for _, req := range batch {
				resp := a.handleJSONRPC(r.Context(), r, req)
				if req.ID != nil {
					responses = append(responses, resp)
				}
			}
			_ = json.NewEncoder(w).Encode(responses)
			return
		}

		var req jsonRPCRequest
		if err := json.Unmarshal(bodyBytes, &req); err != nil {
			_ = json.NewEncoder(w).Encode(jsonRPCResponse{
				JSONRPC: "2.0",
				ID:      nil,
				Error:   &jsonRPCError{Code: -32700, Message: "Parse error"},
			})
			return
		}

		if !a.authorizeMCPMethod(w, r, req.Method) {
			return
		}
		resp := a.handleJSONRPC(r.Context(), r, req)
		if req.ID != nil {
			_ = json.NewEncoder(w).Encode(resp)
		} else {
			// A POST carrying only notifications or responses MUST be answered 202 Accepted with
			// no body (Streamable HTTP, 2025-03-26, "Sending Messages to the Server" step 4).
			// It answered 204, which no revision of the protocol asks for; the revision we now
			// advertise makes the requirement binding.
			w.WriteHeader(http.StatusAccepted)
		}
	})

	mux.HandleFunc("GET /mcp", mcpSSEHandler)
}

// authorizeMCPMethod enforces the bearer authentication the Python MCP
// transport requires for initialize and tools/list. It returns false after
// writing the HTTP error when AUTH_ENABLED is true and the request carries no
// valid bearer token.
func (a *App) authorizeMCPMethod(w http.ResponseWriter, r *http.Request, method string) bool {
	if method != "initialize" && method != "tools/list" {
		return true
	}
	if !mcpAuthEnabled() {
		return true
	}
	token := wsBearerToken(r)
	if token == "" {
		writeDetail(w, http.StatusForbidden, "Not authenticated")
		return false
	}
	if result := auth.ValidateTokenUniversal(r.Context(), token, nil); !result.Valid || result.UserID == nil {
		writeDetail(w, http.StatusUnauthorized, "Invalid authentication credentials")
		return false
	}
	return true
}

// mcpAuthEnabled mirrors os.environ.get("AUTH_ENABLED", "true").lower() == "true".
func mcpAuthEnabled() bool {
	authStatus, ok := os.LookupEnv("AUTH_ENABLED")
	if !ok {
		authStatus = "true"
	}
	return strings.ToLower(authStatus) == "true"
}

func (a *App) handleJSONRPC(ctx context.Context, r *http.Request, req jsonRPCRequest) jsonRPCResponse {
	resp := jsonRPCResponse{
		JSONRPC: "2.0",
		ID:      req.ID,
	}

	switch req.Method {
	case "initialize":
		resp.Result = map[string]any{
			"protocolVersion": mcpProtocolVersion,
			"capabilities": map[string]any{
				"tools":     map[string]any{"listChanged": false},
				"resources": map[string]any{"listChanged": false},
				"prompts":   map[string]any{"listChanged": false},
			},
			"serverInfo": map[string]any{
				"name":    healthServerName,
				"version": config.ReleaseVersion,
			},
		}

	case "notifications/initialized":
		return resp

	case "ping":
		resp.Result = map[string]any{}

	case "tools/list":
		tools, err := a.MCPToolsList()
		if err != nil {
			resp.Error = &jsonRPCError{Code: -32603, Message: "Internal error"}
			return resp
		}
		resp.Result = map[string]any{
			"tools": tools,
		}

	case "resources/list":
		resp.Result = map[string]any{
			"resources": []any{},
		}

	case "prompts/list":
		resp.Result = map[string]any{
			"prompts": []any{},
		}

	case "tools/call":
		var callParams struct {
			Name      string         `json:"name"`
			Arguments map[string]any `json:"arguments"`
		}
		if err := json.Unmarshal(req.Params, &callParams); err != nil {
			resp.Error = &jsonRPCError{Code: -32602, Message: "Invalid params"}
			return resp
		}

		res, isErr := a.dispatchMCPTool(ctx, r, callParams.Name, callParams.Arguments)
		text, err := value_objects.PyJSONDumps(res, 2)
		if err != nil {
			resp.Error = &jsonRPCError{Code: -32603, Message: "Internal error"}
			return resp
		}
		resp.Result = map[string]any{
			"content": []map[string]any{
				{
					"type": "text",
					"text": text,
				},
			},
			"isError": isErr,
		}

	default:
		resp.Error = &jsonRPCError{Code: -32601, Message: fmt.Sprintf("Method not found: %s", req.Method)}
	}

	return resp
}

// ErrMCPToolsRegistryUncomposed is what MCPToolsList returns when the App was built without the MCP tool
// registry. It is a SENTINEL because a caller must be able to assert IDENTITY rather than match prose: the
// one consumer today is a build-time artefact generator, whose guard has to be a test that keeps working
// when the wording changes (the same lesson as everywhere else tonight - a search for a label is not a
// search for the content). The message below still names the fault and the fix.
var ErrMCPToolsRegistryUncomposed = errors.New(
	"the MCP tool registry was not composed: this App has no ToolDefinitions, so the tool surface is " +
		"unknown rather than empty. Wire the registry (the boot path and the test helper both construct " +
		"it) before asking for the list",
)

// MCPToolsList builds the MCP tools/list result from ToolDefinitions(), the
// Python tool registry. manage_seat, call_seat, submit_feedback and the connection tool are registered by
// their own controllers rather than by ToolDefinitions, so their schemas are appended here; every schema is
// converted with the Python-faithful serializer before encoding/json writes it.
//
// EXPORTED because a second reader needs the same entries and must not build them differently: the
// docs generator calls this rather than parsing the appended four out of the source, so an entry added
// here reaches the documentation because it reaches the wire, not because someone remembered to a
// second place. The drift test's independence is unaffected - its witness reads the DISPATCH entries
// in the code, which is a separate reading rather than a second copy of this one.
func (a *App) MCPToolsList() ([]map[string]any, error) {
	if a.mcpTools == nil {
		// REFUSED RATHER THAN EMPTY, and the case that decided it is a BUILD-TIME reader, not the
		// handler: an empty slice and no error is indistinguishable from a platform with no tools, so
		// a generator that composed an App the cheap way would exit 0 and write an artefact saying the
		// tool surface is empty. An unbuilt registry is a wiring fault, and a wiring fault that reads
		// as a fact about the platform is the "looks complete and is not" shape in a new place.
		return nil, ErrMCPToolsRegistryUncomposed
	}
	defs := a.mcpTools.ToolDefinitions()
	tools := make([]map[string]any, 0, len(defs)+4)
	for _, def := range defs {
		schema, err := plainJSON(def.Parameters)
		if err != nil {
			return nil, err
		}
		tools = append(tools, map[string]any{
			"name":        def.Name,
			"description": def.Description,
			"inputSchema": schema,
		})
	}
	seatSchema, err := plainJSON(seatcontrollers.ManageSeatInputSchema())
	if err != nil {
		return nil, err
	}
	tools = append(tools, map[string]any{
		"name":        seatcontrollers.ManageSeatToolName,
		"description": seatcontrollers.ManageSeatToolDescription,
		"inputSchema": seatSchema,
	})
	callSeatSchema, err := plainJSON(seatcontrollers.CallSeatInputSchema())
	if err != nil {
		return nil, err
	}
	tools = append(tools, map[string]any{
		"name":        seatcontrollers.CallSeatToolName,
		"description": seatcontrollers.CallSeatToolDescription,
		"inputSchema": callSeatSchema,
	})
	submitFeedbackSchema, err := plainJSON(seatcontrollers.SubmitFeedbackInputSchema())
	if err != nil {
		return nil, err
	}
	tools = append(tools, map[string]any{
		"name":        seatcontrollers.SubmitFeedbackToolName,
		"description": seatcontrollers.SubmitFeedbackToolDescription,
		"inputSchema": submitFeedbackSchema,
	})
	connTool, err := connectionToolDefinition()
	if err != nil {
		return nil, err
	}
	tools = append(tools, connTool)
	return tools, nil
}

// plainJSON converts an OrderedMap schema into the plain Go JSON tree
// encoding/json can write, using PyJSONDumpsCompact so the *entities.OrderedMap
// is never marshalled with encoding/json (which would emit {}).
func plainJSON(v any) (any, error) {
	encoded, err := value_objects.PyJSONDumpsCompact(v)
	if err != nil {
		return nil, err
	}
	var plain any
	if err := json.Unmarshal([]byte(encoded), &plain); err != nil {
		return nil, err
	}
	return plain, nil
}

func (a *App) dispatchMCPTool(ctx context.Context, r *http.Request, name string, args map[string]any) (any, bool) {
	// Tools that render a seat's MCP fragment (call_seat) have no request of their own, so
	// carry the caller's public origin the way the REST seat routes derive it.
	ctx = withRequestPublicOrigin(ctx, r)

	// Extract session ID and user ID if available
	sessionID := r.Header.Get("X-Session-ID")
	reqID := r.Header.Get("X-Request-ID")

	var userID *string
	if token := wsBearerToken(r); token != "" {
		if result := auth.ValidateTokenUniversal(ctx, token, nil); result.Valid && result.UserID != nil {
			userID = result.UserID
			ctx = mcpAuthContext(ctx, result)
		}
	}
	if userID == nil {
		if envUID := os.Getenv("DEFAULT_USER_ID"); envUID != "" {
			userID = &envUID
		}
	}

	orderedArgs := entities.NewOrderedMap[any]()
	for k, v := range args {
		orderedArgs.Set(k, v)
	}

	action := ""
	if aVal, ok := args["action"].(string); ok {
		action = aVal
	}

	switch name {
	case "get_mcp_status":
		if globalDiagnosticsProvider != nil {
			return globalDiagnosticsProvider.GetMCPStatus(reqID, sessionID), false
		}
		return map[string]any{"status": "ok", "service": "agenthub"}, false

	case "check_session_health":
		if globalDiagnosticsProvider != nil {
			return globalDiagnosticsProvider.SessionHealthCheck(reqID, sessionID), false
		}
		return map[string]any{"status": "healthy"}, false

	case "manage_connection":
		return a.callManageConnection(args, userID), false

	case "manage_task":
		if a.mcpTools != nil && a.mcpTools.TaskController != nil {
			res := a.mcpTools.TaskController.ManageTask(ctx, action, userID, orderedArgs)
			return res, false
		}
		return map[string]any{"error": "TaskController not initialized"}, true

	case "manage_subtask":
		if a.mcpTools != nil && a.mcpTools.SubtaskController != nil {
			taskID := getOptString(args, "task_id")
			res := a.mcpTools.SubtaskController.ManageSubtask(ctx, action, taskID, userID, orderedArgs)
			return res, false
		}
		return map[string]any{"error": "SubtaskController not initialized"}, true

	case "manage_project":
		if a.mcpTools != nil && a.mcpTools.ProjectController != nil {
			pID := getOptStringPtr(args, "project_id", "id")
			pName := getOptStringPtr(args, "name")
			pDesc := getOptStringPtr(args, "description")
			force := getOptBoolPtr(args, "force")
			res := a.mcpTools.ProjectController.ManageProject(ctx, action, pID, pName, pDesc, force, userID)
			return res, false
		}
		return map[string]any{"error": "ProjectController not initialized"}, true

	case "manage_git_branch":
		if a.mcpTools != nil && a.mcpTools.GitBranchController != nil {
			pID := getOptStringPtr(args, "project_id")
			bID := getOptStringPtr(args, "git_branch_id", "branch_id", "id")
			bName := getOptStringPtr(args, "git_branch_name", "name")
			bDesc := getOptStringPtr(args, "git_branch_description", "description")
			agentID := getOptStringPtr(args, "agent_id")
			res := a.mcpTools.GitBranchController.ManageGitBranch(ctx, action, pID, bID, bName, bDesc, agentID, userID)
			return res, false
		}
		return map[string]any{"error": "GitBranchController not initialized"}, true

	case "manage_context":
		if a.mcpTools != nil && a.mcpTools.ContextController != nil {
			level := getOptStringPtr(args, "level")
			contextID := getOptStringPtr(args, "context_id", "id")
			data := getOptStringPtr(args, "data")
			pID := getOptStringPtr(args, "project_id")
			bID := getOptStringPtr(args, "git_branch_id", "branch_id")
			forceRefresh := getOptStringPtr(args, "force_refresh")
			includeInherited := getOptStringPtr(args, "include_inherited")
			propagateChanges := getOptStringPtr(args, "propagate_changes")
			delegateTo := getOptStringPtr(args, "delegate_to")
			delegateData := getOptStringPtr(args, "delegate_data")
			delegationReason := getOptStringPtr(args, "delegation_reason")
			content := getOptStringPtr(args, "content")
			category := getOptStringPtr(args, "category")
			importance := getOptStringPtr(args, "importance")
			agent := getOptStringPtr(args, "agent")
			filters := getOptStringPtr(args, "filters")
			res := a.mcpTools.ContextController.ManageUnifiedContext(ctx, action, level, contextID, data, userID, pID, bID, forceRefresh, includeInherited, propagateChanges, delegateTo, delegateData, delegationReason, content, category, importance, agent, filters)
			return res, false
		}
		return map[string]any{"error": "ContextController not initialized"}, true

	case "manage_agent":
		if a.mcpTools != nil && a.mcpTools.AgentController != nil {
			pID := getOptStringPtr(args, "project_id")
			agID := getOptStringPtr(args, "agent_id", "id")
			name := getOptStringPtr(args, "name")
			callAgent := getOptStringPtr(args, "call_agent")
			bID := getOptStringPtr(args, "git_branch_id", "branch_id")
			res := a.mcpTools.AgentController.ManageAgent(ctx, action, pID, agID, name, callAgent, bID, userID)
			return res, false
		}
		return map[string]any{"error": "AgentController not initialized"}, true

	case seatcontrollers.ManageSeatToolName:
		if a.mcpTools != nil && a.mcpTools.ManageSeatController != nil {
			res := a.mcpTools.ManageSeatController.ManageSeat(ctx, action, getOptStringPtr(args, "room"), getOptStringPtr(args, "seat"),
				getOptStringPtr(args, "runtime"), getOptStringPtr(args, "model"), userID)
			return res, false
		}
		return map[string]any{"error": "ManageSeatController not initialized"}, true

	case seatcontrollers.CallSeatToolName:
		if a.mcpTools != nil && a.mcpTools.CallSeatController != nil {
			res := a.mcpTools.CallSeatController.CallSeat(ctx, getOptStringPtr(args, "room"), getOptStringPtr(args, "seat"), userID)
			return res, false
		}
		return map[string]any{"error": "CallSeatController not initialized"}, true

	case seatcontrollers.SubmitFeedbackToolName:
		if a.mcpTools != nil && a.mcpTools.SubmitFeedbackController != nil {
			res := a.mcpTools.SubmitFeedbackController.SubmitFeedback(ctx,
				getOptString(args, "room"), getOptString(args, "seat"), getOptString(args, "session"),
				getOptString(args, "layer"), getOptString(args, "text"), userID)
			return res, false
		}
		return map[string]any{"error": "SubmitFeedbackController not initialized"}, true

	default:
		return map[string]any{"error": fmt.Sprintf("Unknown tool: %s", name)}, true
	}
}

// Ensure mcpTools is on App
func (a *App) SetMCPTools(tools *interfacelayer.DDDCompliantMCPTools) {
	a.mcpTools = tools
}

func getOptString(m map[string]any, keys ...string) string {
	for _, k := range keys {
		if v, ok := m[k]; ok && v != nil {
			return fmt.Sprintf("%v", v)
		}
	}
	return ""
}

func getOptStringPtr(m map[string]any, keys ...string) *string {
	s := getOptString(m, keys...)
	if s != "" {
		return &s
	}
	return nil
}

func getOptBoolPtr(m map[string]any, keys ...string) *bool {
	for _, k := range keys {
		if v, ok := m[k]; ok && v != nil {
			if b, ok := v.(bool); ok {
				return &b
			}
			b := strings.ToLower(fmt.Sprintf("%v", v)) == "true"
			return &b
		}
	}
	return nil
}

// mcpTokenUser is the request-state user (Python request.state.user) carrying the token payload.
type mcpTokenUser struct{ payload map[string]any }

func (u mcpTokenUser) TokenPayload() map[string]any { return u.payload }

// mcpAuthContext is what DualAuthMiddleware + RequestContextMiddleware leave on the
// request for an authenticated MCP call: the auth state the project and task
// controllers read, plus the user and permission checker the context controller reads.
func mcpAuthContext(ctx context.Context, result auth.UnifiedAuthResult) context.Context {
	payload := map[string]any{"sub": *result.UserID, "scopes": result.Scopes, "roles": result.Roles}
	if result.Email != nil {
		payload["email"] = *result.Email
	}
	state := middleware.AuthState{UserID: result.UserID, AuthInfo: payload}
	ctx = middleware.WithRequestAuthContext(ctx, middleware.CaptureAuthContextFromState(state))
	ctx = context.WithValue(ctx, authperm.UserContextKey, mcpTokenUser{payload})
	return context.WithValue(ctx, authperm.PermissionsContextKey, authperm.NewPermissionChecker(payload))
}
