package httpapp

import (
	"context"
	"testing"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestNewAppAssignsTheOwnershipChecker is the fail-first case for row 0413a1ce. Before this wiring,
// routes.Ownership stayed nil after NewApp, so Rule 2 of IsUserAuthorizedForMessage could only answer
// from its ENVIRONMENT fallback: production refused every system-triggered cross-user frame while
// development delivered it to every connection, and no ownership was ever consulted. The assignment
// IS the defect, so the assignment is what this asserts.
func TestNewAppAssignsTheOwnershipChecker(t *testing.T) {
	previous := routes.Ownership
	t.Cleanup(func() { routes.Ownership = previous })
	routes.Ownership = nil

	if _, err := NewApp(context.Background(), database.NewSessionManager(&database.DatabaseConfig{})); err != nil {
		t.Fatalf("NewApp: %v", err)
	}
	if routes.Ownership == nil {
		t.Fatal("NewApp left routes.Ownership nil: Rule 2 can only answer from the ENVIRONMENT string, " +
			"so a system-triggered frame is decided by an environment variable rather than by ownership")
	}
}

// TestWireOwnershipCheckerAssignsGlobal pins the assignment alone, so a failure above has one
// unambiguous reason. Delete the assignment in wireOwnershipChecker and this case goes red.
func TestWireOwnershipCheckerAssignsGlobal(t *testing.T) {
	previous := routes.Ownership
	t.Cleanup(func() { routes.Ownership = previous })
	routes.Ownership = nil

	wireOwnershipChecker(database.NewSessionManager(&database.DatabaseConfig{}))

	if routes.Ownership == nil {
		t.Fatal("routes.Ownership is nil after wiring: Rule 2 would answer from ENVIRONMENT, not ownership")
	}
}
