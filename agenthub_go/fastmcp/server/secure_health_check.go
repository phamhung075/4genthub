package server

import (
	"os"
	"strings"
	"time"

	"agenthub/fastmcp/config"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// AccessLevel mirrors the Python AccessLevel enum.
type AccessLevel string

const (
	AccessLevelClient        AccessLevel = "client"
	AccessLevelAuthenticated AccessLevel = "authenticated"
	AccessLevelAdmin         AccessLevel = "admin"
)

// SecurityContext mirrors the Python SecurityContext dataclass. UserID is nil
// for Python None, Environment defaults to "production".
type SecurityContext struct {
	AccessLevel AccessLevel
	UserID      *string
	IsInternal  bool
	Environment string
}

// NewSecurityContextFromRequest mirrors SecurityContext.from_request.
func NewSecurityContextFromRequest(userID *string, isAdmin, isInternal bool, environment *string) SecurityContext {
	var accessLevel AccessLevel
	switch {
	case isAdmin && isInternal:
		accessLevel = AccessLevelAdmin
	case userID != nil && *userID != "" && (isAdmin || isInternal):
		accessLevel = AccessLevelAuthenticated
	default:
		accessLevel = AccessLevelClient
	}

	env := ""
	if environment != nil {
		env = *environment
	}
	if env == "" {
		env = envOr("ENVIRONMENT", "production")
	}

	return SecurityContext{
		AccessLevel: accessLevel,
		UserID:      userID,
		IsInternal:  isInternal,
		Environment: env,
	}
}

// SecureHealthChecker mirrors the Python SecureHealthChecker.
type SecureHealthChecker struct {
	ServerName string
	Version    string
}

// NewSecureHealthChecker mirrors SecureHealthChecker.__init__.
func NewSecureHealthChecker() *SecureHealthChecker {
	return &SecureHealthChecker{
		ServerName: config.ServerName,
		Version:    "2.1.0",
	}
}

// secureNow mirrors time.time() (seconds since the epoch as a float).
func secureNow() float64 {
	return float64(time.Now().UnixNano()) / 1e9
}

// CheckHealth mirrors SecureHealthChecker.check_health.
func (c *SecureHealthChecker) CheckHealth(sc SecurityContext) (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = c.getErrorResponse(panicString(r), sc)
		}
	}()

	basicStatus := c.getBasicStatus()

	switch sc.AccessLevel {
	case AccessLevelClient:
		return c.getClientResponse(basicStatus)
	case AccessLevelAuthenticated:
		return c.getAuthenticatedResponse(basicStatus, sc)
	default:
		return c.getAdminResponse(basicStatus, sc)
	}
}

// getBasicStatus mirrors SecureHealthChecker._get_basic_status. The Python
// `except Exception` fallback is the deferred recover.
func (c *SecureHealthChecker) getBasicStatus() (out *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			out = entities.NewOrderedMap[any]()
			out.Set("server_healthy", true)
			out.Set("active_connections", 0)
			out.Set("uptime_seconds", 0)
			out.Set("restart_count", 0)
			out.Set("broadcaster_active", false)
			out.Set("registered_clients", 0)
			out.Set("auth_enabled", true)
			out.Set("mvp_mode", false)
			out.Set("partial_status", true)
			out.Set("status_error", panicString(r))
		}
	}()

	connectionManager := GetConnectionManager()
	connectionStats := connectionManager.GetConnectionStats()
	statusBroadcaster := GetStatusBroadcaster(connectionManager)

	connections := srvGet(connectionStats, "connections", nil)
	serverInfo := srvGet(connectionStats, "server_info", nil)

	basic := entities.NewOrderedMap[any]()
	basic.Set("server_healthy", true)
	basic.Set("active_connections", srvGet(connections, "active_connections", 0))
	basic.Set("uptime_seconds", srvGet(serverInfo, "uptime_seconds", 0))
	basic.Set("restart_count", srvGet(serverInfo, "restart_count", 0))
	basic.Set("broadcaster_active", true)
	basic.Set("registered_clients", statusBroadcaster.GetClientCount())
	basic.Set("auth_enabled", strings.ToLower(envOr("AUTH_ENABLED", "true")) == "true")
	basic.Set("mvp_mode", strings.ToLower(envOr("PRODUCTION", "false")) == "true")
	return basic
}

// getClientResponse mirrors SecureHealthChecker._get_client_response.
func (c *SecureHealthChecker) getClientResponse(basicStatus *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	status := "unhealthy"
	if value_objects.PyTruthy(srvGet(basicStatus, "server_healthy", nil)) {
		status = "healthy"
	}

	om := entities.NewOrderedMap[any]()
	om.Set("success", true)
	om.Set("status", status)
	om.Set("timestamp", secureNow())
	return om
}

// getAuthenticatedResponse mirrors SecureHealthChecker._get_authenticated_response.
func (c *SecureHealthChecker) getAuthenticatedResponse(basicStatus *entities.OrderedMap[any], _ SecurityContext) *entities.OrderedMap[any] {
	status := "unhealthy"
	if value_objects.PyTruthy(srvGet(basicStatus, "server_healthy", nil)) {
		status = "healthy"
	}

	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("status", status)
	response.Set("server_name", c.ServerName)
	response.Set("version", c.Version)
	response.Set("uptime_seconds", srvGet(basicStatus, "uptime_seconds", 0))
	response.Set("active_connections", srvGet(basicStatus, "active_connections", 0))
	response.Set("timestamp", secureNow())

	if restartCount := srvInt(srvGet(basicStatus, "restart_count", 0)); restartCount > 0 {
		response.Set("restart_count", restartCount)
		response.Set("restart_notice", "Server has been restarted")
	}

	return response
}

// getAdminResponse mirrors SecureHealthChecker._get_admin_response.
func (c *SecureHealthChecker) getAdminResponse(basicStatus *entities.OrderedMap[any], sc SecurityContext) *entities.OrderedMap[any] {
	environment := c.getEnvironmentInfo()
	authentication := c.getAuthenticationInfo()
	taskManagement := c.getTaskManagementInfo()
	connections := c.getConnectionsInfo(basicStatus)

	status := "unhealthy"
	if value_objects.PyTruthy(srvGet(basicStatus, "server_healthy", nil)) {
		status = "healthy"
	}

	securityContext := entities.NewOrderedMap[any]()
	securityContext.Set("access_level", string(sc.AccessLevel))
	securityContext.Set("user_id", sc.UserID)
	securityContext.Set("environment", sc.Environment)

	response := entities.NewOrderedMap[any]()
	response.Set("success", true)
	response.Set("status", status)
	response.Set("server_name", c.ServerName)
	response.Set("version", c.Version)
	response.Set("authentication", authentication)
	response.Set("task_management", taskManagement)
	response.Set("environment", environment)
	response.Set("connections", connections)
	response.Set("security_context", securityContext)
	response.Set("timestamp", secureNow())
	return response
}

// getEnvironmentInfo mirrors SecureHealthChecker._get_environment_info.
func (c *SecureHealthChecker) getEnvironmentInfo() *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("pythonpath", envOr("PYTHONPATH", "not set"))
	om.Set("tasks_json_path", envOr("TASKS_JSON_PATH", "not set"))
	om.Set("projects_file_path", envOr("PROJECTS_FILE_PATH", "not set"))
	om.Set("auth_enabled", envOr("AUTH_ENABLED", "true"))
	om.Set("cursor_tools_disabled", envOr("AGENTHUB_DISABLE_CURSOR_TOOLS", "false"))
	om.Set("mvp_mode", envOr("PRODUCTION", "false"))
	supabase, _ := os.LookupEnv("SUPABASE_URL")
	om.Set("supabase_configured", supabase != "")
	return om
}

// getAuthenticationInfo mirrors SecureHealthChecker._get_authentication_info.
func (c *SecureHealthChecker) getAuthenticationInfo() *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("enabled", strings.ToLower(envOr("AUTH_ENABLED", "true")) == "true")
	om.Set("mvp_mode", strings.ToLower(envOr("PRODUCTION", "false")) == "true")
	return om
}

// getTaskManagementInfo mirrors SecureHealthChecker._get_task_management_info.
func (c *SecureHealthChecker) getTaskManagementInfo() *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("task_management_enabled", true)
	om.Set("enabled_tools_count", 0)
	om.Set("total_tools_count", 0)
	om.Set("enabled_tools", []any{})
	return om
}

// getConnectionsInfo mirrors SecureHealthChecker._get_connections_info.
func (c *SecureHealthChecker) getConnectionsInfo(basicStatus *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	activeConnections := srvInt(srvGet(basicStatus, "active_connections", 0))
	recommendedAction := "check_client_connection"
	if activeConnections > 0 {
		recommendedAction = "no_action_needed"
	}

	broadcasting := entities.NewOrderedMap[any]()
	broadcasting.Set("active", srvGet(basicStatus, "broadcaster_active", false))
	broadcasting.Set("registered_clients", srvGet(basicStatus, "registered_clients", 0))
	broadcasting.Set("last_broadcast", nil)
	broadcasting.Set("last_broadcast_time", nil)

	om := entities.NewOrderedMap[any]()
	om.Set("active_connections", srvGet(basicStatus, "active_connections", 0))
	om.Set("server_restart_count", srvGet(basicStatus, "restart_count", 0))
	om.Set("uptime_seconds", srvGet(basicStatus, "uptime_seconds", 0))
	om.Set("recommended_action", recommendedAction)
	om.Set("status_broadcasting", broadcasting)
	return om
}

// getErrorResponse mirrors SecureHealthChecker._get_error_response.
func (c *SecureHealthChecker) getErrorResponse(err string, sc SecurityContext) *entities.OrderedMap[any] {
	om := entities.NewOrderedMap[any]()
	om.Set("success", false)
	om.Set("status", "error")
	if sc.AccessLevel != AccessLevelClient {
		message := "Service temporarily unavailable"
		if sc.AccessLevel == AccessLevelAdmin {
			message = err
		}
		om.Set("error", message)
	}
	om.Set("timestamp", secureNow())
	return om
}

// secureHealthChecker mirrors the module-level _secure_health_checker instance.
var secureHealthChecker = NewSecureHealthChecker()

// SecureHealthCheck mirrors secure_health_check().
func SecureHealthCheck(userID *string, isAdmin, isInternal bool, environment *string) *entities.OrderedMap[any] {
	securityContext := NewSecurityContextFromRequest(userID, isAdmin, isInternal, environment)
	return secureHealthChecker.CheckHealth(securityContext)
}

// ClientHealthCheck mirrors client_health_check().
func ClientHealthCheck() *entities.OrderedMap[any] {
	return SecureHealthCheck(nil, false, false, nil)
}

// AdminHealthCheck mirrors admin_health_check(user_id="admin").
func AdminHealthCheck(userID string) *entities.OrderedMap[any] {
	return SecureHealthCheck(&userID, true, true, nil)
}
