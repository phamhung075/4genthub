package orm

import (
	"context"
	"sort"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ORMSeatRepository is the ORM SeatRepository over seats.
type ORMSeatRepository struct {
	*baserepo.ORMRepository[seatdb.SeatORM]
}

var _ domainrepo.SeatRepository = (*ORMSeatRepository)(nil)

// NewORMSeatRepository builds the repository over seats.
func NewORMSeatRepository(sessions *database.SessionManager) (*ORMSeatRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.SeatORM]("seats", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMSeatRepository{ORMRepository: base}, nil
}

// Create inserts the seat; an empty status defaults to active.
func (r *ORMSeatRepository) Create(ctx context.Context, userID string, seat domainrepo.Seat) (*domainrepo.Seat, error) {
	status := seat.Status
	if status == "" {
		status = "active"
	}
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"room_id", seat.RoomID,
		"seat_key", seat.SeatKey,
		"seat_type_id", seat.SeatTypeID,
		"pinned_version", seat.PinnedVersion,
		"runtime", seat.Runtime,
		"model", seat.Model,
		"status", status,
	))
	if err != nil {
		return nil, err
	}
	return seatToDomain(created), nil
}

// GetByID returns the seat, or nil when absent.
func (r *ORMSeatRepository) GetByID(ctx context.Context, userID, seatID string) (*domainrepo.Seat, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "id", seatID))
	if err != nil || row == nil {
		return nil, err
	}
	return seatToDomain(row), nil
}

// FindByRoomAndKey returns the seat with (room, seat_key), or nil when absent.
func (r *ORMSeatRepository) FindByRoomAndKey(ctx context.Context, userID, roomID, seatKey string) (*domainrepo.Seat, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "room_id", roomID, "seat_key", seatKey))
	if err != nil || row == nil {
		return nil, err
	}
	return seatToDomain(row), nil
}

// ListByRoom returns the room's seats ordered by seat_key.
func (r *ORMSeatRepository) ListByRoom(ctx context.Context, userID, roomID string) ([]domainrepo.Seat, error) {
	rows, err := r.FindBy(ctx, baserepo.NewKwargs("user_id", userID, "room_id", roomID))
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.Seat, 0, len(rows))
	for _, row := range rows {
		out = append(out, *seatToDomain(row))
	}
	sort.Slice(out, func(i, j int) bool { return out[i].SeatKey < out[j].SeatKey })
	return out, nil
}

// MarkRemoved sets the seat status to removed.
func (r *ORMSeatRepository) MarkRemoved(ctx context.Context, userID, seatID string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`UPDATE "seats" SET "status" = 'removed', "updated_at" = $1 WHERE "user_id" = $2 AND "id" = $3`,
			time.Now().UTC(), userID, id)
		return err
	})
}

// UpdateOccupant sets the runtime and model of the seat.
func (r *ORMSeatRepository) UpdateOccupant(ctx context.Context, userID, seatID, runtime, model string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`UPDATE "seats" SET "runtime" = $1, "model" = $2, "updated_at" = $3 WHERE "user_id" = $4 AND "id" = $5`,
			runtime, model, time.Now().UTC(), userID, id)
		return err
	})
}

// Delete removes the seat row; the application layer removes its dependents first.
func (r *ORMSeatRepository) Delete(ctx context.Context, userID, seatID string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM "seats" WHERE "user_id" = $1 AND "id" = $2`, userID, id)
		return err
	})
}
