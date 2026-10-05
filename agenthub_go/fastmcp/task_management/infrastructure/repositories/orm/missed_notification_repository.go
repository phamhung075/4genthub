package orm

// MissedNotificationRepository is the persistence store behind routes.MissedStore, the port the
// websocket helpers (store_missed_notification / fetch_missed_notifications / ...) call. It is
// the first non-test implementation of routes.MissedNotificationStore: without it routes.MissedStore
// stays nil, StoreMissedNotification returns nil and every notification posted while a user is
// offline is dropped.
//
// The row type is database.MissedNotification (task_management/infrastructure/database/models.go);
// its message column is JSON and is serialized with the project's Python-faithful serializer
// (value_objects.PyJSONDumpsCompact), never encoding/json, so the stored document matches what
// Python's json.dumps would write (key order and escaping included).

import (
	"context"
	"encoding/json"
	"time"

	"agenthub/fastmcp/server/routes"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// MissedNotificationRepository is the ORM store over missed_notifications.
type MissedNotificationRepository struct {
	*baserepo.ORMRepository[database.MissedNotification]
}

var _ routes.MissedNotificationStore = (*MissedNotificationRepository)(nil)

// NewMissedNotificationRepository builds the store over missed_notifications.
func NewMissedNotificationRepository(sessions *database.SessionManager) (*MissedNotificationRepository, error) {
	base, err := baserepo.NewORMRepository[database.MissedNotification]("missed_notifications", sessions)
	if err != nil {
		return nil, err
	}
	return &MissedNotificationRepository{ORMRepository: base}, nil
}

// Store inserts one offline notification for userID and returns its id. The id is a fresh UUID,
// delivered starts false, delivery_attempts starts 0 and created_at is now (UTC).
func (r *MissedNotificationRepository) Store(ctx context.Context, userID string, message *entities.OrderedMap[any]) (string, error) {
	serialized, err := value_objects.PyJSONDumpsCompact(message)
	if err != nil {
		return "", err
	}
	created, err := r.Create(ctx, baserepo.NewKwargs(
		"id", value_objects.NewUUIDv4(),
		"user_id", userID,
		"message", json.RawMessage(serialized),
		"created_at", time.Now().UTC(),
		"delivered", false,
		"delivery_attempts", int64(0),
	))
	if err != nil {
		return "", err
	}
	return created.ID, nil
}

// Fetch returns userID's notifications with the given delivered flag, oldest first, capped at
// limit when limit > 0. The user_id filter is the tenant boundary: a user can never see another
// user's missed notifications.
func (r *MissedNotificationRepository) Fetch(ctx context.Context, userID string, delivered bool, limit int) ([]*routes.MissedNotification, error) {
	out := []*routes.MissedNotification{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		query := `SELECT "id", "message", "created_at", "delivery_attempts" FROM "missed_notifications" ` +
			`WHERE "user_id" = $1 AND "delivered" = $2 ORDER BY "created_at" ASC`
		args := []any{userID, delivered}
		if limit > 0 {
			args = append(args, limit)
			query += " LIMIT $3"
		}
		rows, err := s.QueryContext(ctx, query, args...)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var (
				id        string
				raw       json.RawMessage
				createdAt time.Time
				attempts  int64
			)
			if err := rows.Scan(&id, &raw, &createdAt, &attempts); err != nil {
				return err
			}
			decoded, err := entities.DecodeJSON(raw)
			if err != nil {
				return err
			}
			message, _ := decoded.(*entities.OrderedMap[any])
			out = append(out, &routes.MissedNotification{
				ID:               id,
				Message:          message,
				CreatedAt:        createdAt,
				DeliveryAttempts: int(attempts),
			})
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// MarkDelivered sets delivered = true and reports whether a row was updated. The port identifies
// the row by its primary key only; ids are unique across users.
func (r *MissedNotificationRepository) MarkDelivered(ctx context.Context, notificationID string) (bool, error) {
	updated := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`UPDATE "missed_notifications" SET "delivered" = $1 WHERE "id" = $2`, true, notificationID)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		if err != nil {
			return err
		}
		updated = n > 0
		return nil
	})
	return updated, err
}

// IncrementDeliveryAttempts adds one to delivery_attempts, stamps last_attempt_at with now (UTC)
// and reports whether a row was updated.
func (r *MissedNotificationRepository) IncrementDeliveryAttempts(ctx context.Context, notificationID string) (bool, error) {
	updated := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`UPDATE "missed_notifications" SET "delivery_attempts" = "delivery_attempts" + 1, `+
				`"last_attempt_at" = $1 WHERE "id" = $2`,
			time.Now().UTC(), notificationID)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		if err != nil {
			return err
		}
		updated = n > 0
		return nil
	})
	return updated, err
}

// CleanupExpired deletes rows created more than olderThanHours ago and returns the deleted count.
func (r *MissedNotificationRepository) CleanupExpired(ctx context.Context, olderThanHours int) (int, error) {
	deleted := 0
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		cutoff := time.Now().UTC().Add(-time.Duration(olderThanHours) * time.Hour)
		res, err := s.ExecContext(ctx,
			`DELETE FROM "missed_notifications" WHERE "created_at" < $1`, cutoff)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		if err != nil {
			return err
		}
		deleted = int(n)
		return nil
	})
	return deleted, err
}
