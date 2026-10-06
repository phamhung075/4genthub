// MCP authentication dependencies, ported from
// agenthub_main/src/fastmcp/auth/mcp_dependencies.py.
//
// The Python module exposes FastAPI dependency callables (Depends/HTTPBearer).
// FastAPI's dependency-injection layer has no Go meaning, so the token
// validation logic is ported as plain functions; callers pass the bearer token
// string directly.
package auth

import (
	"encoding/json"
	"os"
	"time"

	authentities "agenthub/fastmcp/auth/domain/entities"
)

// Frontend JWT configuration (must match frontend_auth_routes.py).
var (
	frontendJWTSecret    = envDefault("JWT_SECRET_KEY", "your-secret-key-here")
	frontendJWTAlgorithm = "HS256"
)

func envDefault(key, def string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return def
}

// GetCurrentMCPUser mirrors get_current_mcp_user: it validates a
// frontend-generated JWT and returns the User, or an HTTPException matching the
// Python raises.
func GetCurrentMCPUser(token string) (*authentities.User, *HTTPException) {
	if frontendJWTSecret == "" {
		return nil, JWTSecretNotSetError()
	}

	payload, err := jwtDecodeHS256Claims(token, frontendJWTSecret, frontendJWTAlgorithm, jwtDecodeOptions{
		VerifyExp: true,
		VerifyIat: true,
		VerifyNbf: true,
	})
	if err != nil {
		if isJWTExpired(err) {
			return nil, &HTTPException{
				StatusCode: 401,
				Detail:     "Token expired",
			}
		}
		// jwt.InvalidTokenError (catch-all after ExpiredSignatureError).
		return nil, &HTTPException{
			StatusCode: 401,
			Detail:     "Invalid token",
		}
	}

	userID := stringClaim(payload["sub"])
	if userID == "" {
		userID = stringClaim(payload["user_id"])
	}
	email := stringClaim(payload["email"])
	username := stringClaim(payload["username"])
	authProvider := stringClaim(payload["auth_provider"])
	if authProvider == "" {
		authProvider = "unknown"
	}

	if userID == "" {
		return nil, &HTTPException{
			StatusCode: 401,
			Detail:     "Invalid token: missing user ID",
		}
	}

	// Check token expiration (PyJWT already verified exp above; kept for parity).
	if exp, ok := payload["exp"]; ok {
		if v, err := jwtClaimInt(exp); err == nil && float64(time.Now().UnixNano())/1e9 > v {
			return nil, &HTTPException{
				StatusCode: 401,
				Detail:     "Token expired",
			}
		}
	}

	if email == "" {
		email = userID + "@" + authProvider + ".local"
	}
	if username == "" {
		if email != "" {
			username = email
		} else {
			username = userID
		}
	}

	uid := userID
	return &authentities.User{
		ID:           &uid,
		Email:        email,
		Username:     username,
		PasswordHash: authProvider + "-authenticated",
	}, nil
}

// GetOptionalMCPUser mirrors get_optional_mcp_user: nil when no credentials or
// on any failure.
func GetOptionalMCPUser(token *string) *authentities.User {
	if token == nil {
		return nil
	}
	user, err := GetCurrentMCPUser(*token)
	if err != nil {
		return nil
	}
	return user
}

func stringClaim(v any) string {
	s, _ := v.(string)
	if s == "" {
		if raw, ok := v.(json.RawMessage); ok {
			var out string
			if json.Unmarshal(raw, &out) == nil {
				return out
			}
		}
	}
	return s
}
