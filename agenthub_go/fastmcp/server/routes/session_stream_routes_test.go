package routes

import (
	"context"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/session_stream"
)

// A database failure is a 500, not the 404 that means "no such session of yours".
func TestGetSessionEventsDatabaseFailureIsNotA404(t *testing.T) {
	session_stream.DefaultSessions = nil
	id := "user-1"
	_, err := GetSessionEvents(context.Background(), "s1", 0, 10, &authdomain.User{ID: &id}, nil)
	if err == nil {
		t.Fatal("want the database error")
	}
	if err.Error() != "database configuration not available" {
		t.Fatalf("err = %v", err)
	}
}
