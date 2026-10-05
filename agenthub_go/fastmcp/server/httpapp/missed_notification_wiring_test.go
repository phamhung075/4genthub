package httpapp

import (
	"testing"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestWireMissedNotificationStoreAssignsGlobal pins the assignment the defect was about: no
// production code assigned routes.MissedStore, so it stayed nil, StoreMissedNotification returned
// nil and wsReplayMissedNotifications fetched an empty list while the broadcast still answered
// broadcast_sent. Delete the assignment in wireMissedNotificationStore and this test goes red.
func TestWireMissedNotificationStoreAssignsGlobal(t *testing.T) {
	previous := routes.MissedStore
	t.Cleanup(func() { routes.MissedStore = previous })
	routes.MissedStore = nil

	if err := wireMissedNotificationStore(database.NewSessionManager(&database.DatabaseConfig{})); err != nil {
		t.Fatalf("wireMissedNotificationStore: %v", err)
	}
	if routes.MissedStore == nil {
		t.Fatal("routes.MissedStore is nil after wiring: offline notifications would be silently dropped")
	}
}
