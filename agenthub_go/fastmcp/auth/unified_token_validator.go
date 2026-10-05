package auth

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"

	"agenthub/fastmcp/auth/domain/services"
	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UnifiedAuthResult is the unified token validation result.
type UnifiedAuthResult struct {
	Valid      bool
	UserID     *string
	Email      *string
	AuthMethod *string
	Error      *string

	TokenID  *string
	Roles    []any
	Scopes   []any
	UserData *taskentities.OrderedMap[any]
}

func strPtr(s string) *string { return &s }

// ValidateTokenUniversal validates any token type: Keycloak, API token, or MCP
// token.
func ValidateTokenUniversal(ctx context.Context, token string, clientInfo *taskentities.OrderedMap[any]) UnifiedAuthResult {
	if token == "" {
		return UnifiedAuthResult{Valid: false, Error: strPtr("No token provided")}
	}

	// 1. Check if it's a JWT token and try validation.
	if strings.HasPrefix(token, "eyJ") {
		unverifiedPayload, err := jwtUnverifiedClaims(token)
		if err == nil {
			authProvider := value_objects.PyLower(envOr("AUTH_PROVIDER", "keycloak"))
			issuer, _ := unverifiedPayload["iss"].(string)
			keycloakURL := os.Getenv("KEYCLOAK_URL")
			cleanKeycloakURL := strings.TrimRight(keycloakURL, "/")

			if authProvider == "keycloak" && (keycloakURL != "" && strings.HasPrefix(issuer, cleanKeycloakURL) || strings.Contains(issuer, "/realms/")) {
				result := validateUnifiedKeycloakToken(ctx, token)
				if result.Valid {
					return result
				}
				if result.Error != nil {
					log.Printf("[auth] Keycloak validation failed: %s (iss=%s, keycloakURL=%s)", *result.Error, issuer, keycloakURL)
				}
			} else {
				tokenID, _ := unverifiedPayload["token_id"]
				typ, _ := unverifiedPayload["type"].(string)
				if value_objects.PyTruthy(tokenID) || typ == "api_token" {
					result := validateUnifiedAPIToken(token)
					if result.Valid {
						return result
					}
				}
			}
		}

		// Try general local JWT validation.
		result := validateUnifiedLocalJWT(token)
		if result.Valid {
			return result
		}
	}

	// 2. Try MCP token validation (for generated tokens).
	result := validateUnifiedMCPToken(ctx, token, clientInfo)
	if result.Valid {
		return result
	}

	return UnifiedAuthResult{Valid: false, Error: strPtr("Invalid token: no validation method succeeded")}
}

func validateUnifiedKeycloakToken(ctx context.Context, token string) UnifiedAuthResult {
	user, err := ValidateKeycloakToken(ctx, token)
	if err != nil {
		return UnifiedAuthResult{Valid: false, Error: strPtr(fmt.Sprintf("Keycloak validation failed: %s", err.Error()))}
	}
	userID := ""
	if user.ID != nil {
		userID = *user.ID
	}
	userData := taskentities.NewOrderedMap[any]()
	userData.Set("id", userID)
	userData.Set("email", user.Email)
	userData.Set("username", user.Username)
	return UnifiedAuthResult{
		Valid:      true,
		UserID:     strPtr(userID),
		Email:      strPtr(user.Email),
		AuthMethod: strPtr("keycloak"),
		UserData:   userData,
	}
}

func validateUnifiedAPIToken(token string) UnifiedAuthResult {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		return UnifiedAuthResult{Valid: false, Error: strPtr("JWT_SECRET_KEY not configured")}
	}

	jwtService, err := services.NewJWTService(jwtSecret, services.DefaultIssuer)
	if err != nil {
		return UnifiedAuthResult{Valid: false, Error: strPtr(fmt.Sprintf("API token validation failed: %s", err.Error()))}
	}

	payload := jwtService.VerifyToken(token, "api_token", "")
	if payload != nil {
		userID := payloadString(payload, "user_id")
		if userID == "" {
			userID = payloadString(payload, "sub")
		}
		result := UnifiedAuthResult{
			Valid:      true,
			UserID:     strPtr(userID),
			Email:      optStringPtr(payload, "email"),
			AuthMethod: strPtr("api_token"),
			TokenID:    firstNonEmptyPtr(payload, "token_id", "jti"),
			Scopes:     toAnySlice(payload["scopes"]),
			Roles:      toAnySlice(payload["roles"]),
		}
		return result
	}

	return UnifiedAuthResult{Valid: false, Error: strPtr("API token validation failed")}
}

func validateUnifiedLocalJWT(token string) UnifiedAuthResult {
	jwtSecret := envOr("JWT_SECRET_KEY", "default-secret-key-change-in-production")
	supabaseJWTSecret := os.Getenv("SUPABASE_JWT_SECRET")

	type secretEntry struct {
		name  string
		value string
	}
	var secretsToTry []secretEntry
	if supabaseJWTSecret != "" {
		secretsToTry = append(secretsToTry, secretEntry{"SUPABASE_JWT_SECRET", supabaseJWTSecret})
	}
	if jwtSecret != "" && jwtSecret != "default-secret-key-change-in-production" {
		secretsToTry = append(secretsToTry, secretEntry{"JWT_SECRET_KEY", jwtSecret})
	}

	for _, secret := range secretsToTry {
		jwtService, err := services.NewJWTService(secret.value, services.DefaultIssuer)
		if err != nil {
			continue
		}

		if secret.name == "SUPABASE_JWT_SECRET" {
			payload, err := jwtDecodeHS256Claims(token, secret.value, "HS256", jwtDecodeOptions{
				VerifyAud: true,
				Audience:  "authenticated",
				VerifyIss: false,
				VerifyExp: true,
				VerifyIat: true,
				VerifyNbf: true,
			})
			if err == nil && payload != nil {
				userID := payloadString(payload, "user_id")
				if userID == "" {
					userID = payloadString(payload, "sub")
				}
				return UnifiedAuthResult{
					Valid:      true,
					UserID:     strPtr(userID),
					Email:      optStringPtr(payload, "email"),
					AuthMethod: strPtr("local_jwt"),
					Roles:      toAnySlice(payload["roles"]),
				}
			}
		}

		for _, tokenType := range []string{"api_token", "access"} {
			payload := jwtService.VerifyToken(token, tokenType, "")
			if payload != nil {
				userID := payloadString(payload, "user_id")
				if userID == "" {
					userID = payloadString(payload, "sub")
				}
				return UnifiedAuthResult{
					Valid:      true,
					UserID:     strPtr(userID),
					Email:      optStringPtr(payload, "email"),
					AuthMethod: strPtr("local_jwt"),
					TokenID:    firstNonEmptyPtr(payload, "token_id", "jti"),
					Scopes:     toAnySlice(payload["scopes"]),
					Roles:      toAnySlice(payload["roles"]),
				}
			}
		}
	}

	return UnifiedAuthResult{Valid: false, Error: strPtr("Local JWT validation failed with all secrets")}
}

func validateUnifiedMCPToken(ctx context.Context, token string, clientInfo *taskentities.OrderedMap[any]) UnifiedAuthResult {
	tokenValidator := NewTokenValidator(nil)
	tokenInfo, err := tokenValidator.ValidateToken(ctx, token, clientInfo)
	if err != nil {
		return UnifiedAuthResult{Valid: false, Error: strPtr(fmt.Sprintf("MCP token validation failed: %s", err.Error()))}
	}

	userData := taskentities.NewOrderedMap[any]()
	if tokenInfo.CreatedAt.IsZero() {
		userData.Set("created_at", nil)
	} else {
		userData.Set("created_at", value_objects.IsoFormat(tokenInfo.CreatedAt))
	}
	if tokenInfo.ExpiresAt == nil {
		userData.Set("expires_at", nil)
	} else {
		userData.Set("expires_at", value_objects.IsoFormat(*tokenInfo.ExpiresAt))
	}

	return UnifiedAuthResult{
		Valid:      true,
		UserID:     strPtr(tokenInfo.UserID),
		AuthMethod: strPtr("mcp_token"),
		UserData:   userData,
	}
}

func payloadString(payload map[string]any, key string) string {
	if s, ok := payload[key].(string); ok {
		return s
	}
	return ""
}

func optStringPtr(payload map[string]any, key string) *string {
	if s, ok := payload[key].(string); ok {
		return &s
	}
	return nil
}

func firstNonEmptyPtr(payload map[string]any, keys ...string) *string {
	for _, key := range keys {
		if s, ok := payload[key].(string); ok && s != "" {
			return &s
		}
	}
	return nil
}

// toAnySlice converts a decoded JSON list to []any (nil when absent).
func toAnySlice(v any) []any {
	switch x := v.(type) {
	case []any:
		return x
	case []string:
		out := make([]any, len(x))
		for i, s := range x {
			out[i] = s
		}
		return out
	}
	return nil
}
