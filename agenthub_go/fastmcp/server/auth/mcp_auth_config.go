package auth

import (
	"os"
	"strings"

	"agenthub/fastmcp/server/auth/providers"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// CreateMCPAuthProvider creates an MCP authentication provider based on
// configuration. It returns nil (Python None) when auth is disabled.
func CreateMCPAuthProvider(
	authType string,
	secretKey *string,
	requiredScopes []string,
	checkDatabase bool,
) (any, error) {
	if authType == "none" {
		return nil, nil
	}

	if authType == "env" {
		// Environment bearer auth no longer supported - use JWT instead.
		return nil, nil
	}

	if authType == "jwt" {
		if requiredScopes == nil {
			requiredScopes = []string{"mcp:access"}
		}
		return providers.NewJWTBearerAuthProvider(secretKey, "agenthub", nil, requiredScopes, checkDatabase)
	}

	return nil, &value_objects.ValueError{Msg: "Unknown auth_type: " + authType}
}

// GetDefaultAuthProvider gets the default authentication provider based on
// environment configuration.
func GetDefaultAuthProvider() (any, error) {
	if strings.ToLower(os.Getenv("AUTH_ENABLED")) == "false" {
		return nil, nil
	}

	authType := os.Getenv("MCP_AUTH_TYPE")

	if authType == "" {
		if os.Getenv("JWT_SECRET_KEY") != "" {
			authType = "jwt"
		} else if os.Getenv("MCP_BEARER_TOKEN") != "" {
			authType = "env"
		} else {
			authType = "none"
		}
	}

	return CreateMCPAuthProvider(authType, nil, nil, true)
}

// MCPServerInstance is the minimal shape needed by ConfigureMCPServerAuth.
type MCPServerInstance struct {
	Auth any
}

// ConfigureMCPServerAuth configures authentication for an MCP server instance.
func ConfigureMCPServerAuth(serverInstance *MCPServerInstance) (*MCPServerInstance, error) {
	if serverInstance.Auth == nil {
		provider, err := GetDefaultAuthProvider()
		if err != nil {
			return serverInstance, err
		}
		serverInstance.Auth = provider
	}
	return serverInstance, nil
}
