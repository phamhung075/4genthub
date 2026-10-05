// MCP Server configuration with JWT authentication, ported from
// agenthub_main/src/fastmcp/auth/mcp_integration/server_config.py.
//
// Port notes: the Starlette `Middleware` list / `mcp_server.middleware`
// plumbing has no Go meaning (there is no Starlette/MCP server object here), so
// only the configuration and kwargs helpers are ported. configure_jwt_from_env
// returns an OrderedMap because the Python dict key order is observable.
package mcp_integration

import (
	"os"
	"strconv"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ConfigureJWTForMCP mirrors configure_jwt_auth_for_mcp.
func ConfigureJWTForMCP(requiredScopes []string, userRepository MCPUserLookup) (*JWTAuthBackend, error) {
	if requiredScopes == nil {
		requiredScopes = []string{"mcp:access"}
	}
	return CreateJWTAuthBackend(userRepository, requiredScopes)
}

// IntegrateJWTWithHTTPServer mirrors integrate_jwt_with_http_server.
func IntegrateJWTWithHTTPServer(httpServerFactoryKwargs map[string]any, userRepository MCPUserLookup) (*JWTAuthBackend, error) {
	authBackend, err := ConfigureJWTForMCP(nil, userRepository)
	if err != nil {
		return nil, err
	}

	httpServerFactoryKwargs["auth"] = authBackend

	middleware, _ := httpServerFactoryKwargs["middleware"].([]any)
	middleware = append(middleware, getJWTMiddleware(authBackend)...)
	httpServerFactoryKwargs["middleware"] = middleware

	return authBackend, nil
}

// getJWTMiddleware mirrors get_jwt_middleware. The Python fallback sets
// UserContextMiddleware to None when the middleware import fails, yielding an
// empty list; no Go equivalent exists, so it returns none.
func getJWTMiddleware(jwtBackend *JWTAuthBackend) []any {
	return []any{}
}

// ConfigureJWTFromEnv mirrors configure_jwt_from_env.
func ConfigureJWTFromEnv() (*entities.OrderedMap[any], error) {
	config := entities.NewOrderedMap[any]()

	var secretKey any
	if v, ok := os.LookupEnv("JWT_SECRET_KEY"); ok {
		secretKey = v
	} else {
		secretKey = nil
	}
	config.Set("secret_key", secretKey)
	config.Set("issuer", configEnvDefault("JWT_ISSUER", "agenthub"))
	config.Set("audience", "mcp-server")
	config.Set("algorithm", configEnvDefault("JWT_ALGORITHM", "HS256"))

	accessMinutes, err := intEnvDefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
	if err != nil {
		return nil, err
	}
	config.Set("access_token_expire_minutes", accessMinutes)

	refreshDays, err := intEnvDefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
	if err != nil {
		return nil, err
	}
	config.Set("refresh_token_expire_days", refreshDays)

	if secretKey == nil || secretKey == "" {
		return nil, &value_objects.ValueError{Msg: "JWT_SECRET_KEY environment variable must be set"}
	}

	return config, nil
}

// ValidateJWTConfiguration mirrors validate_jwt_configuration.
func ValidateJWTConfiguration() (bool, error) {
	config, err := ConfigureJWTFromEnv()
	if err != nil {
		return false, &value_objects.ValueError{Msg: "JWT configuration validation failed: " + err.Error()}
	}

	secret, _ := config.Get("secret_key")
	secretStr, _ := secret.(string)
	if len(secretStr) < 32 {
		return false, wrapJWTValidationError(&value_objects.ValueError{Msg: "JWT_SECRET_KEY should be at least 32 characters for security"})
	}

	accessMinutes, _ := config.Get("access_token_expire_minutes")
	if v, ok := accessMinutes.(int); ok && v < 5 {
		return false, wrapJWTValidationError(&value_objects.ValueError{Msg: "Access token expiration should be at least 5 minutes"})
	}

	refreshDays, _ := config.Get("refresh_token_expire_days")
	if v, ok := refreshDays.(int); ok && v < 1 {
		return false, wrapJWTValidationError(&value_objects.ValueError{Msg: "Refresh token expiration should be at least 1 day"})
	}

	return true, nil
}

func wrapJWTValidationError(err error) error {
	return &value_objects.ValueError{Msg: "JWT configuration validation failed: " + err.Error()}
}

func intEnvDefault(key, def string) (int, error) {
	v, ok := os.LookupEnv(key)
	if !ok {
		v = def
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return 0, &value_objects.ValueError{Msg: "invalid literal for int() with base 10: '" + v + "'"}
	}
	return n, nil
}

func configEnvDefault(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}
