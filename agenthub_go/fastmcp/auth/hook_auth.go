package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Hook-specific JWT configuration from environment (module import time).
var hookJWTAlgorithm = envOr("HOOK_JWT_ALGORITHM", "HS256")

// HookAuthValidator validates tokens from Claude hooks (from .mcp.json file).
type HookAuthValidator struct {
	Algorithm string
	Secret    string
}

// NewHookAuthValidator mirrors HookAuthValidator.__init__ plus the module-level
// HOOK_JWT_SECRET guard. Python raises ValueError at import; Go returns it here.
func NewHookAuthValidator() (*HookAuthValidator, error) {
	secret := os.Getenv("HOOK_JWT_SECRET")
	if secret == "" {
		return nil, &value_objects.ValueError{
			Msg: "HOOK_JWT_SECRET environment variable is required for hook authentication",
		}
	}
	return &HookAuthValidator{Algorithm: hookJWTAlgorithm, Secret: secret}, nil
}

// jwtEncodeHS256 is jose jwt.encode(claims, secret, algorithm).
func jwtEncodeHS256(claims *taskentities.OrderedMap[any], secret, algorithm string) (string, error) {
	header := fmt.Sprintf(`{"alg":%q,"typ":"JWT"}`, algorithm)
	payload, err := value_objects.PyJSONDumpsCompact(claims)
	if err != nil {
		return "", err
	}
	signingInput := base64.RawURLEncoding.EncodeToString([]byte(header)) + "." +
		base64.RawURLEncoding.EncodeToString([]byte(payload))
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signingInput))
	return signingInput + "." + base64.RawURLEncoding.EncodeToString(mac.Sum(nil)), nil
}

// ValidateHookToken validates a hook JWT token.
func (v *HookAuthValidator) ValidateHookToken(token string) (map[string]any, error) {
	unverified, err := jwtUnverifiedClaims(token)
	if err != nil {
		return nil, &HTTPException{StatusCode: 401, Detail: "Invalid token format"}
	}

	typ, _ := unverified["type"].(string)
	iss, _ := unverified["iss"].(string)
	if typ == "api_token" || iss == "agenthub" {
		payload, decodeErr := jwtDecodeHS256Claims(token, v.Secret, v.Algorithm, jwtDecodeOptions{
			VerifyAud: true,
			Audience:  "mcp-server",
			VerifyExp: true,
			VerifyIat: true,
			VerifyNbf: true,
		})
		if decodeErr != nil {
			if isJWTExpired(decodeErr) {
				return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
			}
			if value_objects.PyLower(envOr("AUTH_ENABLED", "true")) == "false" {
				return unverified, nil
			}
			return nil, &HTTPException{StatusCode: 401, Detail: "Invalid hook token signature"}
		}

		if exp, ok := payload["exp"]; ok {
			if expSeconds, err := jwtClaimInt(exp); err == nil {
				if float64(time.Now().UTC().UnixNano())/1e9 > expSeconds {
					return nil, &HTTPException{StatusCode: 401, Detail: "Token expired"}
				}
			}
		}
		return payload, nil
	}

	return nil, &HTTPException{StatusCode: 401, Detail: "Not a valid hook token"}
}

// IsHookRequest checks if a request is coming from a Claude hook.
func IsHookRequest(requestHeaders map[string]string) bool {
	userAgent := ""
	for k, val := range requestHeaders {
		if value_objects.PyLower(k) == "user-agent" {
			userAgent = value_objects.PyLower(val)
			break
		}
	}

	hookIndicators := []string{"python", "requests", "aiohttp", "httpx", "claude-hook", "mcp-client"}
	for _, indicator := range hookIndicators {
		if strings.Contains(userAgent, indicator) {
			return true
		}
	}
	return false
}

// hookProjectRoot mirrors Path(__file__).parent.parent.parent.parent.parent for
// the Go source layout (agenthub_go/fastmcp/auth -> repository root).
func hookProjectRoot() string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return ""
	}
	dir := filepath.Dir(file)
	return filepath.Dir(filepath.Dir(filepath.Dir(dir)))
}

// GetTokenFromMCPJSON extracts the Bearer token from .mcp.json if available.
func GetTokenFromMCPJSON() *string {
	root := hookProjectRoot()
	if root == "" {
		return nil
	}
	mcpJSONPath := filepath.Join(root, ".mcp.json")

	data, err := os.ReadFile(mcpJSONPath)
	if err != nil {
		return nil
	}
	var mcpConfig map[string]any
	if err := json.Unmarshal(data, &mcpConfig); err != nil {
		return nil
	}

	agenthubConfig := map[string]any{}
	if servers, ok := mcpConfig["mcpServers"].(map[string]any); ok {
		if ac, ok := servers["agenthub_http"].(map[string]any); ok {
			agenthubConfig = ac
		}
	}
	authHeader := ""
	if headers, ok := agenthubConfig["headers"].(map[string]any); ok {
		if a, ok := headers["Authorization"].(string); ok {
			authHeader = a
		}
	}

	if strings.HasPrefix(authHeader, "Bearer ") {
		token := authHeader[7:]
		return &token
	}
	return nil
}

// CreateHookToken creates a new hook authentication token.
func CreateHookToken(userID string, expiresInDays int) (string, error) {
	now := time.Now().UTC()
	expire := now.Add(time.Duration(expiresInDays) * 24 * time.Hour)

	payload := taskentities.NewOrderedMap[any]()
	payload.Set("sub", userID)
	payload.Set("type", "api_token")
	payload.Set("iss", "agenthub")
	payload.Set("aud", "mcp-server")
	payload.Set("iat", float64(now.UnixNano())/1e9)
	payload.Set("exp", float64(expire.UnixNano())/1e9)
	payload.Set("jti", fmt.Sprintf("hook_%d", now.UnixNano()/1000))
	payload.Set("scopes", []string{
		"mcp-api",
		"tasks:read",
		"tasks:create",
		"tasks:update",
		"contexts:read",
		"projects:read",
		"branches:read",
	})

	return jwtEncodeHS256(payload, os.Getenv("HOOK_JWT_SECRET"), hookJWTAlgorithm)
}
