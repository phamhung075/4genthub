package httpapp

import (
	"context"
	"errors"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/application/facades"
	"agenthub/fastmcp/task_management/application/factories"
	"agenthub/fastmcp/task_management/application/services"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/interface/api_controllers"
	taskapicontroller "agenthub/fastmcp/task_management/interface/api_controllers/task_api_controller"
	"agenthub/fastmcp/types"
)

// routeDeps are the controllers and callbacks mountRoutes registers. app.go's
// Handler already mounts the project, branch, task, subtask, session, MCP, auth
// and supabase route sets; everything here is what it does not mount yet.
type routeDeps struct {
	sessions *database.SessionManager

	taskRoutes    routes.TaskRoutesController
	subtaskRoutes routes.SubtaskRoutesController
	userSubtasks  routes.UserSubtaskController
	contexts      routes.ContextController
	tokens        routes.TokenRouteController
	broadcast     routes.BroadcastFunc
}

// newRouteDeps adapts the App composition root to the controllers mountRoutes
// needs. It reuses the raw controllers behind the httpapp adapters and rebuilds
// the context and token controllers over the same facades app.go wires.
func newRouteDeps(a *App) routeDeps {
	if a == nil {
		return routeDeps{}
	}
	deps := routeDeps{sessions: a.Sessions}
	if ta, ok := a.tasks.(userTaskControllerAdapter); ok && ta.c != nil {
		deps.taskRoutes = taskRoutesAdapter{c: ta.c}
	}
	if sa, ok := a.subtasks.(subtaskControllerAdapter); ok && sa.c != nil {
		deps.subtaskRoutes = subtaskRoutesAdapter{c: sa.c}
		deps.userSubtasks = userSubtaskAdapter{c: sa.c}
	}
	ctxFactory := factories.NewUnifiedContextFacadeFactory(context.Background(), a.Sessions)
	deps.contexts = contextRoutesAdapter{c: api_controllers.NewContextAPIController(contextFacadeProvider{factory: ctxFactory})}
	deps.tokens = tokenRoutesAdapter{c: api_controllers.NewTokenAPIController(facadeServiceTokenProvider{})}
	deps.broadcast = broadcastAdapter
	return deps
}

// broadcastAdapter adapts websocket_routes.BroadcastDataChange (data any) to
// routes.BroadcastFunc (data *OrderedMap).
func broadcastAdapter(ctx context.Context, eventType, entityType, entityID, userID string, data, metadata *entities.OrderedMap[any]) error {
	return routes.BroadcastDataChange(ctx, eventType, entityType, entityID, userID, data, metadata)
}

// mountRoutes registers every HTTP route set under fastmcp/server/routes that
// App.Handler does not already mount. Handler must call it after its own
// registrations and before returning the mux:
//
//	mountRoutes(mux, newRouteDeps(a))
func mountRoutes(mux *http.ServeMux, deps routeDeps) {
	mountConnectionRoutes(mux)
	mountAlertRoutes(mux)
	mountPerformanceRoutes(mux)
	mountBroadcastRoutes(mux, deps)
	mountContextRoutes(mux, deps)
	mountTokenRoutes(mux, deps)
	mountTaskSummaryRoutes(mux, deps)
}

// --- connection_routes.py (/api/v2/connections) ---

func mountConnectionRoutes(mux *http.ServeMux) {
	const base = "/api/v2/connections"
	mux.HandleFunc("GET "+base+"/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, routes.HealthCheck(queryBoolPtr(r, "include_details")))
	})
	mux.HandleFunc("GET "+base+"/status", func(w http.ResponseWriter, r *http.Request) {
		body, err := routes.ConnectionStatus()
		writeResult(w, body, err)
	})
}

// --- alert_system_routes.py (/api/v1/alerts) ---

func mountAlertRoutes(mux *http.ServeMux) {
	const base = "/api/v1/alerts"

	mux.HandleFunc("GET "+base+"/rules", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeJSON(w, http.StatusOK, routes.ListAlertRules())
	}))
	mux.HandleFunc("POST "+base+"/rules", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		data, ok := jsonOrderedBody(w, r)
		if !ok {
			return
		}
		body, err := routes.CreateAlertRule(data)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("PUT "+base+"/rules/{rule_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		data, ok := jsonOrderedBody(w, r)
		if !ok {
			return
		}
		body, err := routes.UpdateAlertRule(r.PathValue("rule_id"), data)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/rules/{rule_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.DeleteAlertRule(r.PathValue("rule_id"))
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/events", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeJSON(w, http.StatusOK, routes.ListAlertEvents(queryIntDefault(r, "limit", 50), queryOpt(r, "severity"), queryBoolPtr(r, "acknowledged")))
	}))
	mux.HandleFunc("POST "+base+"/events/{event_index}/acknowledge", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		index, err := strconv.Atoi(r.PathValue("event_index"))
		if err != nil {
			writeDetail(w, http.StatusUnprocessableEntity, "Input should be a valid integer, unable to parse string as an integer")
			return
		}
		body, herr := routes.AcknowledgeAlert(index)
		writeResult(w, body, herr)
	}))
	mux.HandleFunc("POST "+base+"/check-rules", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeJSON(w, http.StatusOK, routes.CheckAlertRules(r.Context(), nil))
	}))
	mux.HandleFunc("POST "+base+"/test-webhook", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		data, ok := jsonOrderedBody(w, r)
		if !ok {
			return
		}
		body, err := routes.TestWebhook(data)
		writeResult(w, body, err)
	}))
}

// --- performance_metrics_routes.py (/api/v1/performance) ---

func mountPerformanceRoutes(mux *http.ServeMux) {
	const base = "/api/v1/performance"
	mux.HandleFunc("GET "+base+"/metrics/overview", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetPerformanceOverview(queryBoolDefault(r, "include_details", false))
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/metrics/timeseries", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetPerformanceTimeseries(queryIntDefault(r, "hours", 24), queryDefault(r, "interval", "1h"))
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/metrics/alerts", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetPerformanceAlerts()
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/metrics/clear-cache", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.ClearPerformanceCache(queryOpt(r, "cache_name"))
		writeResult(w, body, err)
	}))
}

// --- broadcast_routes.py (/api/v2/broadcast) ---

func mountBroadcastRoutes(mux *http.ServeMux, deps routeDeps) {
	// The bridge is the only caller and it holds a machine token, so the ingress is
	// machine-authenticated and the target user is the token's user, never the body's.
	mux.HandleFunc("POST /api/v2/broadcast/notify", machineAuthed(deps.sessions, func(w http.ResponseWriter, r *http.Request, token *repositories.MachineToken) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		var missing []string
		for _, f := range []string{"event_type", "entity_type", "entity_id"} {
			if _, has := m[f]; !has {
				missing = append(missing, f)
			}
		}
		if len(missing) > 0 {
			writeMissing(w, "body", missing...)
			return
		}
		req := routes.BroadcastRequest{
			EventType:  getOptString(m, "event_type"),
			EntityType: getOptString(m, "entity_type"),
			EntityID:   getOptString(m, "entity_id"),
			UserID:     token.UserID,
			Data:       orderedMapOf(m["data"]),
			Metadata:   orderedMapOf(m["metadata"]),
		}
		if deps.broadcast == nil {
			writeDetail(w, http.StatusInternalServerError, "Broadcast is not configured")
			return
		}
		body, err := routes.TriggerBroadcast(r.Context(), req, deps.broadcast)
		writeResult(w, body, err)
	}))
}

// --- context_routes.py (/api/v2/contexts) ---

func mountContextRoutes(mux *http.ServeMux, deps routeDeps) {
	if deps.contexts == nil {
		return
	}
	c := deps.contexts
	const base = "/api/v2/contexts"

	mux.HandleFunc("POST "+base+"/{level}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		if _, has := m["context_id"]; !has {
			writeMissing(w, "body", "context_id")
			return
		}
		req := routes.ContextCreateRequest{
			ContextID:   getOptString(m, "context_id"),
			Data:        orderedMapOf(m["data"]),
			ProjectID:   getOptStringPtr(m, "project_id"),
			GitBranchID: getOptStringPtr(m, "git_branch_id"),
		}
		body, err := routes.CreateContext(r.Context(), r.PathValue("level"), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{level}/{context_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetContext(r.Context(), r.PathValue("level"), r.PathValue("context_id"),
			queryBoolDefault(r, "include_inherited", false), queryBoolDefault(r, "force_refresh", false), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("PUT "+base+"/{level}/{context_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		if _, has := m["data"]; !has {
			writeMissing(w, "body", "data")
			return
		}
		req := routes.ContextUpdateRequest{Data: orderedMapOf(m["data"]), PropagateChanges: bodyBoolDefault(m["propagate_changes"], true)}
		body, err := routes.UpdateContext(r.Context(), r.PathValue("level"), r.PathValue("context_id"), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/{level}/{context_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.DeleteContext(r.Context(), r.PathValue("level"), r.PathValue("context_id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{level}/{context_id}/resolve", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.ResolveContext(r.Context(), r.PathValue("level"), r.PathValue("context_id"), queryBoolDefault(r, "force_refresh", false), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/{level}/{context_id}/delegate", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		req := routes.ContextDelegateRequest{
			DelegateTo:       getOptString(m, "delegate_to"),
			DelegateData:     orderedMapOf(m["delegate_data"]),
			DelegationReason: getOptStringPtr(m, "delegation_reason"),
		}
		body, err := routes.DelegateContext(r.Context(), r.PathValue("level"), r.PathValue("context_id"), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/{level}/{context_id}/insights", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		req := routes.ContextInsightRequest{
			Content:    getOptString(m, "content"),
			Category:   getOptStringPtr(m, "category"),
			Importance: getOptStringPtr(m, "importance"),
			Agent:      getOptStringPtr(m, "agent"),
		}
		body, err := routes.AddInsight(r.Context(), r.PathValue("level"), r.PathValue("context_id"), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/{level}/{context_id}/progress", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		m, ok := jsonBody(w, r)
		if !ok {
			return
		}
		req := routes.ContextProgressRequest{Content: getOptString(m, "content"), Agent: getOptStringPtr(m, "agent")}
		body, err := routes.AddProgress(r.Context(), r.PathValue("level"), r.PathValue("context_id"), req, u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{level}/list", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.ListContexts(r.Context(), r.PathValue("level"), queryOpt(r, "filters"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("GET "+base+"/{level}/{context_id}/summary", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetContextSummary(r.Context(), r.PathValue("level"), r.PathValue("context_id"), u)
		writeResult(w, body, err)
	}))
}

// --- token_router.py (/api/v2/tokens) ---

func mountTokenRoutes(mux *http.ServeMux, deps routeDeps) {
	if deps.tokens == nil {
		return
	}
	c := deps.tokens
	const base = "/api/v2/tokens"

	create := authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		req, ok := parseTokenCreate(w, r)
		if !ok {
			return
		}
		body, err := routes.GenerateTokenHandler(r.Context(), req, u, c)
		writeResult(w, body, err)
	})
	mux.HandleFunc("POST "+base, create)
	mux.HandleFunc("POST "+base+"/", create)
	mux.HandleFunc("POST "+base+"/generate", create)

	list := authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.ListTokens(r.Context(), u, c, queryIntDefault(r, "skip", 0), queryIntDefault(r, "limit", 100))
		writeResult(w, body, err)
	})
	mux.HandleFunc("GET "+base, list)
	mux.HandleFunc("GET "+base+"/", list)
	mux.HandleFunc("GET "+base+"/legacy/tokens", list)
	mux.HandleFunc("GET "+base+"/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, routes.TokenServiceHealth())
	})

	mux.HandleFunc("GET "+base+"/{token_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.GetTokenDetails(r.Context(), r.PathValue("token_id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("DELETE "+base+"/{token_id}", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.DeleteToken(r.Context(), r.PathValue("token_id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("PATCH "+base+"/{token_id}/revoke", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.RevokeToken(r.Context(), r.PathValue("token_id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("PATCH "+base+"/{token_id}/reactivate", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.ReactivateToken(r.Context(), r.PathValue("token_id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/{token_id}/rotate", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.RotateToken(r.Context(), r.PathValue("token_id"), u, c)
		writeResult(w, body, err)
	}))
	mux.HandleFunc("POST "+base+"/validate", func(w http.ResponseWriter, r *http.Request) {
		token, ok := queryReq(w, r, "token")
		if !ok {
			return
		}
		body, err := routes.ValidateTokenEndpoint(r.Context(), token, c)
		writeResult(w, body, err)
	})
	mux.HandleFunc("POST "+base+"/cleanup", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		body, err := routes.CleanupExpiredTokens(r.Context(), u, c)
		writeResult(w, body, err)
	}))
}

func parseTokenCreate(w http.ResponseWriter, r *http.Request) (routes.TokenCreateRequest, bool) {
	m, ok := jsonBody(w, r)
	if !ok {
		return routes.TokenCreateRequest{}, false
	}
	if _, ok := m["name"].(string); !ok {
		writeMissing(w, "body", "name")
		return routes.TokenCreateRequest{}, false
	}
	return routes.TokenCreateRequest{
		Name:          getOptString(m, "name"),
		Scopes:        stringList(m, "scopes"),
		ExpiresInDays: optIntDefault(m["expires_in_days"], 30),
		RateLimit:     optIntPtr(m["rate_limit"]),
		Metadata:      orderedMapOf(m["metadata"]),
	}, true
}

// --- task_routes.py (/api) and the remaining task_user_routes.py endpoint ---

func mountTaskSummaryRoutes(mux *http.ServeMux, deps routeDeps) {
	if deps.taskRoutes != nil && deps.contexts != nil {
		mux.HandleFunc("POST /api/tasks/summaries", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
			m, ok := jsonBody(w, r)
			if !ok {
				return
			}
			req := routes.TaskSummariesRequest{
				GitBranchID:    getOptStringPtr(m, "git_branch_id"),
				Page:           optIntPtr(m["page"]),
				Limit:          optIntPtr(m["limit"]),
				StatusFilter:   getOptStringPtr(m, "status_filter"),
				PriorityFilter: getOptStringPtr(m, "priority_filter"),
			}
			body, err := routes.GetTaskSummaries(r.Context(), req, u, deps.taskRoutes, deps.contexts)
			writeResult(w, body, err)
		}))
		mux.HandleFunc("GET /api/tasks/{task_id}/context/summary", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
			body, err := routes.GetTaskContextSummary(r.Context(), r.PathValue("task_id"), u, deps.contexts)
			writeResult(w, body, err)
		}))
	}
	if deps.subtaskRoutes != nil {
		mux.HandleFunc("POST /api/subtasks/summaries", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
			m, ok := jsonBody(w, r)
			if !ok {
				return
			}
			body, err := routes.GetTaskRouteSubtaskSummaries(r.Context(), getOptString(m, "parent_task_id"), bodyBoolDefault(m["include_counts"], true), u, deps.subtaskRoutes)
			writeResult(w, body, err)
		}))
	}
	mux.HandleFunc("GET /api/performance/metrics", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		writeJSON(w, http.StatusOK, routes.GetPerformanceMetrics(redisCacheEnabled(), nil))
	}))
	mux.HandleFunc("POST /api/v2/tasks/{task_id}/subtasks/summaries", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		if deps.userSubtasks == nil {
			writeDetail(w, http.StatusInternalServerError, "Failed to fetch subtasks")
			return
		}
		body, err := routes.GetUserSubtaskSummaries(r.Context(), r.PathValue("task_id"), u, deps.userSubtasks)
		writeResult(w, body, err)
	}))
}

// redisCacheEnabled mirrors task_routes.py REDIS_CACHE_ENABLED: True only when
// the redis cache decorator imported. Go reads the deployment flag instead.
func redisCacheEnabled() bool {
	return strings.EqualFold(os.Getenv("REDIS_CACHE_ENABLED"), "true")
}

// --- adapters: controllers -> routes interfaces ---

// contextFacadeProvider is api_controllers.ctxFacadeProvider over the unified
// context facade factory app.go builds.
type contextFacadeProvider struct {
	factory *factories.UnifiedContextFacadeFactory
}

func (p contextFacadeProvider) GetContextFacade(userID, projectID, gitBranchID *string) (*facades.UnifiedContextFacade, error) {
	if p.factory == nil {
		return nil, errors.New("unified context facade factory is not configured")
	}
	return p.factory.CreateFacade(context.Background(), userID, projectID, gitBranchID)
}

// contextRoutesAdapter satisfies routes.ContextController over ContextAPIController.
type contextRoutesAdapter struct {
	c *api_controllers.ContextAPIController
}

func contextResult(r *types.ContextResponse) routes.ControllerResult {
	return routes.ControllerResult{Success: r.Success, Error: r.Error, Message: r.Message, Body: r.ModelDump()}
}

func (a contextRoutesAdapter) CreateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string) (routes.ControllerResult, error) {
	return contextResult(a.c.CreateContext(ctx, level, contextID, data, userID, nil)), nil
}

func (a contextRoutesAdapter) GetContext(ctx context.Context, level, contextID string, includeInherited bool, userID string) (routes.ControllerResult, error) {
	return contextResult(a.c.GetContext(ctx, level, contextID, includeInherited, userID, nil)), nil
}

func (a contextRoutesAdapter) UpdateContext(ctx context.Context, level, contextID string, data *entities.OrderedMap[any], userID string) (routes.ControllerResult, error) {
	return contextResult(a.c.UpdateContext(ctx, level, contextID, data, userID, nil)), nil
}

func (a contextRoutesAdapter) DeleteContext(ctx context.Context, level, contextID, userID string) (routes.ControllerResult, error) {
	r := a.c.DeleteContext(ctx, level, contextID, userID, nil)
	return routes.ControllerResult{Success: r.Success, Error: r.Error, Message: r.Message, Body: r.ModelDump()}, nil
}

func (a contextRoutesAdapter) ResolveContext(ctx context.Context, level, contextID string, forceRefresh bool, userID string) (routes.ControllerResult, error) {
	return contextResult(a.c.ResolveContext(ctx, level, contextID, userID, nil, forceRefresh)), nil
}

// facadeServiceTokenProvider is api_controllers.TokenFacadeProvider over the
// FacadeService singleton NewApp installs.
type facadeServiceTokenProvider struct{}

func (facadeServiceTokenProvider) GetTokenFacade() (any, error) {
	s := services.GetInstance()
	if s == nil {
		return nil, errors.New("facade service is not configured")
	}
	return s.GetTokenFacade()
}

// tokenRoutesAdapter satisfies routes.TokenRouteController over TokenAPIController.
type tokenRoutesAdapter struct {
	c *api_controllers.TokenAPIController
}

func tokenOpResult(m *entities.OrderedMap[any]) routes.TokenOperationResult {
	res := routes.TokenOperationResult{Success: mountBool(m, "success"), Error: mountStrPtr(m, "error"), Message: mountStrPtr(m, "message")}
	if v, ok := mountGet(m, "token_data"); ok {
		res.TokenData, _ = v.(*entities.OrderedMap[any])
	}
	return res
}

func (a tokenRoutesAdapter) GenerateAPIToken(ctx context.Context, userID, name string, scopes []string, expiresInDays int, rateLimit *int) (routes.TokenOperationResult, error) {
	m, err := a.c.GenerateAPIToken(ctx, userID, name, scopes, expiresInDays, rateLimit, nil)
	if err != nil {
		return routes.TokenOperationResult{}, err
	}
	return tokenOpResult(m), nil
}

func (a tokenRoutesAdapter) ListUserTokens(ctx context.Context, userID string) (routes.TokenRouteListResult, error) {
	m, err := a.c.ListUserTokens(ctx, userID, nil, 0, 100)
	if err != nil {
		return routes.TokenRouteListResult{}, err
	}
	return routes.TokenRouteListResult{Success: mountBool(m, "success"), Error: mountStrPtr(m, "error"), Tokens: mountMapList(m, "tokens"), Total: mountInt(m, "total")}, nil
}

func (a tokenRoutesAdapter) GetTokenDetails(ctx context.Context, tokenID, userID string) (routes.TokenOperationResult, error) {
	m, err := a.c.GetTokenDetails(ctx, tokenID, userID, nil)
	if err != nil {
		return routes.TokenOperationResult{}, err
	}
	return tokenOpResult(m), nil
}

func (a tokenRoutesAdapter) DeleteToken(ctx context.Context, tokenID, userID string) (routes.TokenOperationResult, error) {
	m, err := a.c.DeleteToken(ctx, tokenID, userID, nil)
	if err != nil {
		return routes.TokenOperationResult{}, err
	}
	return tokenOpResult(m), nil
}

func (a tokenRoutesAdapter) RevokeToken(ctx context.Context, tokenID, userID string) (routes.TokenOperationResult, error) {
	m, err := a.c.RevokeToken(ctx, tokenID, userID, nil)
	if err != nil {
		return routes.TokenOperationResult{}, err
	}
	return tokenOpResult(m), nil
}

func (a tokenRoutesAdapter) ReactivateToken(ctx context.Context, tokenID, userID string) (routes.TokenOperationResult, error) {
	m, err := a.c.ReactivateToken(ctx, tokenID, userID, nil)
	if err != nil {
		return routes.TokenOperationResult{}, err
	}
	return tokenOpResult(m), nil
}

func (a tokenRoutesAdapter) RotateToken(ctx context.Context, tokenID, userID string) (routes.TokenOperationResult, error) {
	m, err := a.c.RotateToken(ctx, tokenID, userID, nil)
	if err != nil {
		return routes.TokenOperationResult{}, err
	}
	return tokenOpResult(m), nil
}

func (a tokenRoutesAdapter) ValidateToken(ctx context.Context, token string) (routes.TokenValidateResult, error) {
	m, err := a.c.ValidateToken(ctx, token, nil)
	if err != nil {
		return routes.TokenValidateResult{}, err
	}
	res := routes.TokenValidateResult{Success: mountBool(m, "success"), Error: mountStrPtr(m, "error")}
	if v, ok := mountGet(m, "claims"); ok {
		res.Claims, _ = v.(*entities.OrderedMap[any])
	}
	return res, nil
}

func (a tokenRoutesAdapter) CleanupExpiredTokens(ctx context.Context, userID string) (routes.TokenCleanupResult, error) {
	m, err := a.c.CleanupExpiredTokens(ctx)
	if err != nil {
		return routes.TokenCleanupResult{}, err
	}
	return routes.TokenCleanupResult{Success: mountBool(m, "success"), Error: mountStrPtr(m, "error"), Message: mountStrPtr(m, "message"), DeletedCount: mountInt(m, "deleted_count")}, nil
}

// taskRoutesAdapter satisfies routes.TaskRoutesController over TaskAPIController.
type taskRoutesAdapter struct {
	c *taskapicontroller.TaskAPIController
}

func (a taskRoutesAdapter) CountTasks(ctx context.Context, filters *entities.OrderedMap[any], userID string) (routes.TaskCountResult, error) {
	r := a.c.CountTasks(ctx, filters, userID)
	count := 0
	if r.Count != nil {
		count = *r.Count
	}
	return routes.TaskCountResult{Success: r.Success, Error: r.Error, Count: count}, nil
}

func (a taskRoutesAdapter) ListTasksSummary(ctx context.Context, filters *entities.OrderedMap[any], offset, limit int, userID string) (routes.TaskListSummaryResult, error) {
	r := a.c.ListTasksSummary(ctx, filters, offset, limit, userID)
	tasks := make([]*entities.OrderedMap[any], 0, len(r.Tasks))
	for _, t := range r.Tasks {
		if t != nil {
			tasks = append(tasks, t.ModelDump())
		}
	}
	return routes.TaskListSummaryResult{Success: r.Success, Error: r.Error, Tasks: tasks}, nil
}

// subtaskRoutesAdapter satisfies routes.SubtaskRoutesController over SubtaskAPIController.
type subtaskRoutesAdapter struct {
	c *api_controllers.SubtaskAPIController
}

func (a subtaskRoutesAdapter) ListSubtasksSummary(ctx context.Context, parentTaskID string, includeCounts bool, userID string) (routes.SubtaskSummaryResult, error) {
	r := a.c.ListSubtasksSummary(ctx, parentTaskID, includeCounts, userID)
	return routes.SubtaskSummaryResult{Success: r.Success, Error: r.Error, Subtasks: subtaskDTOMaps(r.Subtasks)}, nil
}

// userSubtaskAdapter satisfies routes.UserSubtaskController over SubtaskAPIController.
type userSubtaskAdapter struct {
	c *api_controllers.SubtaskAPIController
}

func (a userSubtaskAdapter) ListSubtasks(ctx context.Context, taskID, userID string) (routes.UserSubtaskResult, error) {
	r := a.c.ListSubtasks(ctx, taskID, userID)
	return routes.UserSubtaskResult{Success: r.Success, Error: r.Error, Subtasks: subtaskDTOMaps(r.Subtasks)}, nil
}

func subtaskDTOMaps(in []*types.SubtaskDTO) []*entities.OrderedMap[any] {
	out := make([]*entities.OrderedMap[any], 0, len(in))
	for _, s := range in {
		if s != nil {
			out = append(out, s.ModelDump())
		}
	}
	return out
}

// --- small helpers ---

func jsonOrderedBody(w http.ResponseWriter, r *http.Request) (*entities.OrderedMap[any], bool) {
	m, ok := jsonBody(w, r)
	if !ok {
		return nil, false
	}
	return mapToOrderedMap(m), true
}

func mapToOrderedMap(m map[string]any) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		out.Set(k, m[k])
	}
	return out
}

func orderedMapOf(v any) *entities.OrderedMap[any] {
	if m, ok := v.(map[string]any); ok {
		return mapToOrderedMap(m)
	}
	return nil
}

func optIntPtr(v any) *int {
	switch n := v.(type) {
	case int:
		return &n
	case int64:
		i := int(n)
		return &i
	case float64:
		i := int(n)
		return &i
	}
	return nil
}

func optIntDefault(v any, def int) int {
	if p := optIntPtr(v); p != nil {
		return *p
	}
	return def
}

func bodyBoolDefault(v any, def bool) bool {
	if b, ok := v.(bool); ok {
		return b
	}
	return def
}

func queryBoolPtr(r *http.Request, key string) *bool {
	if !r.URL.Query().Has(key) {
		return nil
	}
	b := queryBoolValue(r.URL.Query().Get(key))
	return &b
}

func queryBoolDefault(r *http.Request, key string, def bool) bool {
	if p := queryBoolPtr(r, key); p != nil {
		return *p
	}
	return def
}

func queryBoolValue(v string) bool {
	switch strings.ToLower(v) {
	case "true", "1", "yes", "on":
		return true
	}
	return false
}

func queryDefault(r *http.Request, key, def string) string {
	if !r.URL.Query().Has(key) {
		return def
	}
	return r.URL.Query().Get(key)
}

func queryIntDefault(r *http.Request, key string, def int) int {
	if !r.URL.Query().Has(key) {
		return def
	}
	n, err := strconv.Atoi(r.URL.Query().Get(key))
	if err != nil {
		return def
	}
	return n
}

func mountGet(m *entities.OrderedMap[any], key string) (any, bool) {
	if m == nil {
		return nil, false
	}
	return m.Get(key)
}

func mountBool(m *entities.OrderedMap[any], key string) bool {
	v, _ := mountGet(m, key)
	b, _ := v.(bool)
	return b
}

func mountStrPtr(m *entities.OrderedMap[any], key string) *string {
	v, _ := mountGet(m, key)
	if s, ok := v.(string); ok {
		return &s
	}
	return nil
}

func mountInt(m *entities.OrderedMap[any], key string) int {
	v, _ := mountGet(m, key)
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	}
	return 0
}

func mountMapList(m *entities.OrderedMap[any], key string) []*entities.OrderedMap[any] {
	v, _ := mountGet(m, key)
	switch list := v.(type) {
	case []*entities.OrderedMap[any]:
		return list
	case []any:
		out := make([]*entities.OrderedMap[any], 0, len(list))
		for _, item := range list {
			if om, ok := item.(*entities.OrderedMap[any]); ok {
				out = append(out, om)
			}
		}
		return out
	}
	return nil
}
