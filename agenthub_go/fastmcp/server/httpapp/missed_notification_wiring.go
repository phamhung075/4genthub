package httpapp

import (
	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/repositories/orm"
)

// wireMissedNotificationStore assigns the missed-notification store the websocket replay
// (wsReplayMissedNotifications) and the offline store path (routes.StoreMissedNotification) read.
// routes.MissedStore is an injected global that no production code assigned, so it stayed nil:
// StoreMissedNotification returned nil and the next-connect replay always fetched an empty list,
// while the broadcast still answered broadcast_sent. NewApp calls this so the server binary gets
// the real store.
func wireMissedNotificationStore(sessions *database.SessionManager) error {
	store, err := orm.NewMissedNotificationRepository(sessions)
	if err != nil {
		return err
	}
	routes.MissedStore = store
	return nil
}
