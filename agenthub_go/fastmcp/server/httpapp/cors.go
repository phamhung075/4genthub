package httpapp

import (
	"net/http"

	"agenthub/fastmcp/config"
)

// withCORS applies the production CORS policy. Python builds it in
// http_server.py:create_base_app from CORSFactory.get_allowed_origins() and Starlette's
// CORSMiddleware defaults: allow_credentials=True, allow_methods=["*"],
// allow_headers=["*"], expose_headers=["*"], max_age=600. The origins come from
// CORS_ORIGINS (comma separated, "*" collapses to wildcard) or the factory default ["*"].
func withCORS(next http.Handler) http.Handler {
	return config.NewCORSMiddleware(config.CORSOptions{
		AllowOrigins:     config.GetAllowedOrigins(nil),
		AllowCredentials: true,
		AllowMethods:     []string{"*"},
		AllowHeaders:     []string{"*"},
		ExposeHeaders:    []string{"*"},
		MaxAge:           600,
	})(next)
}
