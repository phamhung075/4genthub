package httpapp

import (
	"net/http"

	"agenthub/fastmcp/config"
)

// withCORS applies the production CORS policy. Python builds it in
// http_server.py:create_base_app from CORSFactory.get_allowed_origins() and Starlette's
// CORSMiddleware defaults: allow_credentials=True, allow_methods=["*"],
// allow_headers=["*"], expose_headers=["*"], max_age=600.
//
// The allowlist is the CORS_ORIGINS environment variable (comma separated; "*" anywhere
// collapses to the wildcard). A fresh local stack does not set CORS_ORIGINS, so it takes
// the factory fallback of ["*"]; because credentials are enabled, that fallback echoes the
// concrete request origin instead of emitting "Access-Control-Allow-Origin: *" next to
// "Access-Control-Allow-Credentials: true" (a combination browsers reject). Production sets
// CORS_ORIGINS to the real dashboard origins and therefore always echoes an allowlisted one.
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
