package orm

import (
	"context"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const seatMessageReturning = `"id"::text, "user_id", "room", "seat", "text", "created_at", "delivered_at", "machine_id"`

// ORMSeatMessageRepository is the ORM SeatMessageRepository over seat_messages.
type ORMSeatMessageRepository struct {
	*baserepo.ORMRepository[seatdb.SeatMessageORM]
}

var _ domainrepo.SeatMessageRepository = (*ORMSeatMessageRepository)(nil)

// NewORMSeatMessageRepository builds the repository over seat_messages.
func NewORMSeatMessageRepository(sessions *database.SessionManager) (*ORMSeatMessageRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.SeatMessageORM]("seat_messages", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMSeatMessageRepository{ORMRepository: base}, nil
}

// Create stores one message and returns the stored row.
//
// The id is generated HERE rather than left to the column default, the same choice the seat feedback
// repository makes: the table's runtime DDL has no DEFAULT on id because createAll (the path a fresh
// database takes) does not create the uuid-ossp extension, so uuid_generate_v4() does not exist
// there. created_at is the caller's clock rather than now(), so the answer the route returns and the
// row it stored carry the same instant.
//
// delivered_at and machine_id are written as NULL and the empty string RATHER THAN TAKEN FROM THE
// CALLER, because a newly stored message is pending by definition: there is no way to create an
// already-delivered row, and therefore no way to create one no client will ever be handed.
func (r *ORMSeatMessageRepository) Create(ctx context.Context, message domainrepo.SeatMessage) (*domainrepo.SeatMessage, error) {
	row := &seatdb.SeatMessageORM{}
	id := message.ID
	if id == "" {
		id = value_objects.NewUUIDv4()
	}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`INSERT INTO "seat_messages" ("id", "user_id", "room", "seat", "text", "created_at", "delivered_at", "machine_id") `+
				`VALUES ($1, $2, $3, $4, $5, $6, NULL, '') RETURNING `+seatMessageReturning,
			id, message.UserID, message.Room, message.Seat, message.Text, message.CreatedAt,
		).Scan(&row.ID, &row.UserID, &row.Room, &row.Seat, &row.Text, &row.CreatedAt, &row.DeliveredAt, &row.MachineID)
	})
	if err != nil {
		return nil, err
	}
	out := seatMessageToDomain(row)
	return &out, nil
}

// ListPending returns the seat's undelivered messages OLDEST FIRST, which is the order a seat should
// receive them in.
//
// THE PAGE BOUNDARY IS A KEYSET, NOT AN OFFSET. The ORDER BY and the comparison are the same pair
// (created_at, id), so a message that lands while a client is paging cannot make the next page skip a
// row or repeat one — an offset moves under exactly that write, and this store exists to not lose
// text. The id is compared and ordered as a uuid, so the comparison and the sort are the same order.
// An absent cursor (the zero time) is the first page rather than a special case in SQL.
func (r *ORMSeatMessageRepository) ListPending(ctx context.Context, userID, room, seat string, afterCreatedAt time.Time, afterID string, limit int) ([]domainrepo.SeatMessage, error) {
	const head = `SELECT ` + seatMessageReturning + ` FROM "seat_messages" ` +
		`WHERE "user_id" = $1 AND "room" = $2 AND "seat" = $3 AND "delivered_at" IS NULL `
	const order = ` ORDER BY "created_at", "id" LIMIT `
	query := head + order + `$4`
	args := []any{userID, room, seat, limit}
	if !afterCreatedAt.IsZero() {
		query = head + `AND ("created_at", "id") > ($4, $5::uuid)` + order + `$6`
		args = []any{userID, room, seat, afterCreatedAt, afterID, limit}
	}

	rows := []*seatdb.SeatMessageORM{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		cursor, err := s.QueryContext(ctx, query, args...)
		if err != nil {
			return err
		}
		defer func() { _ = cursor.Close() }()
		for cursor.Next() {
			row := &seatdb.SeatMessageORM{}
			if err := cursor.Scan(&row.ID, &row.UserID, &row.Room, &row.Seat, &row.Text,
				&row.CreatedAt, &row.DeliveredAt, &row.MachineID); err != nil {
				return err
			}
			rows = append(rows, row)
		}
		return cursor.Err()
	})
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.SeatMessage, 0, len(rows))
	for _, row := range rows {
		out = append(out, seatMessageToDomain(row))
	}
	return out, nil
}

// Ack marks one PENDING message delivered by machineID, and reports whether it found one.
//
// `"delivered_at" IS NULL` IS THE WHOLE SAFETY. A second ack of an id that has already been delivered
// updates nothing and reports false, so the row keeps the FIRST machine and instant that took it
// rather than the last one to say so — and the caller can tell "delivered" from "was not pending",
// which a client retrying after a dropped response needs to hear apart.
func (r *ORMSeatMessageRepository) Ack(ctx context.Context, userID, room, seat, id, machineID string, deliveredAt time.Time) (bool, error) {
	found := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		result, err := s.ExecContext(ctx,
			`UPDATE "seat_messages" SET "delivered_at" = $5, "machine_id" = $6 `+
				`WHERE "user_id" = $1 AND "room" = $2 AND "seat" = $3 AND "id" = $4::uuid AND "delivered_at" IS NULL`,
			userID, room, seat, id, deliveredAt, machineID)
		if err != nil {
			return err
		}
		n, err := result.RowsAffected()
		if err != nil {
			return err
		}
		found = n > 0
		return nil
	})
	if err != nil {
		return false, err
	}
	return found, nil
}

// DeleteForSeat removes one seat's messages, delivered or not. It is the application-layer cascade
// this schema requires wherever CASCADE would otherwise be, and the seat's removal is what calls it.
func (r *ORMSeatMessageRepository) DeleteForSeat(ctx context.Context, userID, room, seat string) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`DELETE FROM "seat_messages" WHERE "user_id" = $1 AND "room" = $2 AND "seat" = $3`,
			userID, room, seat)
		return err
	})
}

// DeleteForRoom removes every message in one room, for a room's own deletion. Rooms are deleted only
// when empty (RoomDeletionService refuses a room that still holds seats), so this is the room-level
// half of the same explicit cascade rather than a shortcut around the seat-level one.
func (r *ORMSeatMessageRepository) DeleteForRoom(ctx context.Context, userID, room string) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`DELETE FROM "seat_messages" WHERE "user_id" = $1 AND "room" = $2`, userID, room)
		return err
	})
}

func seatMessageToDomain(row *seatdb.SeatMessageORM) domainrepo.SeatMessage {
	return domainrepo.SeatMessage{
		ID:          row.ID,
		UserID:      row.UserID,
		Room:        row.Room,
		Seat:        row.Seat,
		Text:        row.Text,
		CreatedAt:   row.CreatedAt,
		DeliveredAt: row.DeliveredAt,
		MachineID:   row.MachineID,
	}
}
