// Package routes ports fastmcp/server/routes/session_stream_routes.py.
package routes

import (
	"context"
	"regexp"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/session_stream"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	SessionStreamWriteScope    = "sessions:write"
	SessionStreamMaxMsgChars   = 1024 * 1024
	SessionStreamAuthCode      = 4001
	SessionStreamForbiddenCode = 4003
	SessionStreamNotFoundCode  = 4004
)

var idRegexp = regexp.MustCompile(`^[A-Za-z0-9._:-]{1,64}$`)

// ValidateConnectorID checks if connector ID matches the allowed pattern.
func ValidateConnectorID(connectorID string) bool {
	return idRegexp.MatchString(connectorID)
}

// ListSessions lists sessions for current user.
func ListSessions(ctx context.Context, currentUser *authdomain.User, sessions *database.SessionManager) ([]*entities.OrderedMap[any], error) {
	uid := currentUserID(currentUser)
	if uid == "" {
		return nil, httpErr(401, "Authentication required")
	}
	res, err := session_stream.ListSessions(ctx, sessions, uid)
	if err != nil {
		return nil, httpErr(500, "Failed to list sessions")
	}
	return res, nil
}

// GetSessionEvents returns events for a session after afterSeq with limit.
func GetSessionEvents(ctx context.Context, sessionID string, afterSeq, limit int, currentUser *authdomain.User, sessions *database.SessionManager) ([]*entities.OrderedMap[any], error) {
	uid := currentUserID(currentUser)
	if uid == "" {
		return nil, httpErr(401, "Authentication required")
	}
	res, err := session_stream.ListEvents(ctx, sessions, uid, sessionID, int64(afterSeq), int64(limit))
	if err != nil {
		return nil, httpErr(404, "Session not found")
	}
	return res, nil
}
