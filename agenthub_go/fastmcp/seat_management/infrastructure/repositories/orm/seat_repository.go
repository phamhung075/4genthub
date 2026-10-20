package orm

import (
	"context"
	"sort"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/domain/value_objects"
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

// Create inserts the seat.
func (r *ORMSeatRepository) Create(ctx context.Context, userID string, seat domainrepo.Seat) (*domainrepo.Seat, error) {
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"room_id", seat.RoomID,
		"seat_key", seat.SeatKey,
		"seat_type_id", seat.SeatTypeID,
		"pinned_version", seat.PinnedVersion,
		"runtime", seat.Runtime,
		"model", seat.Model,
		"permission_policy", seat.PermissionPolicy,
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

// UpdateOccupant sets the runtime and model of the seat and records the change, both in one
// transaction. The previous values are read under the row lock, so the record names exactly the
// pair the overwrite replaced; a no-op writes neither the seat nor a record.
func (r *ORMSeatRepository) UpdateOccupant(ctx context.Context, userID, seatID, runtime, model, actor string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var fromRuntime, fromModel string
		if err := s.QueryRowContext(ctx,
			`SELECT "runtime", "model" FROM "seats" WHERE "user_id" = $1 AND "id" = $2 FOR UPDATE`,
			userID, id).Scan(&fromRuntime, &fromModel); err != nil {
			return err
		}
		if fromRuntime == runtime && fromModel == model {
			return nil // nothing changed: no UPDATE, no record
		}
		at := time.Now().UTC()
		if _, err := s.ExecContext(ctx,
			`UPDATE "seats" SET "runtime" = $1, "model" = $2, "updated_at" = $3 WHERE "user_id" = $4 AND "id" = $5`,
			runtime, model, at, userID, id); err != nil {
			return err
		}
		_, err := s.ExecContext(ctx,
			`INSERT INTO "seat_occupant_changes" ("id", "user_id", "seat_id", "actor", "at", "from_runtime", "from_model", "to_runtime", "to_model") `+
				`VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
			value_objects.NewUUIDv4(), userID, id, actor, at, fromRuntime, fromModel, runtime, model)
		return err
	})
}

// ListOccupantChanges returns the seat's recorded occupant changes, newest first. It is
// tenant-scoped and returns an empty slice, never nil, when there are none.
func (r *ORMSeatRepository) ListOccupantChanges(ctx context.Context, userID, seatID string) ([]domainrepo.OccupantChange, error) {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.OccupantChange, 0)
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT "id"::text, "user_id", "seat_id"::text, "actor", "at", "from_runtime", "from_model", "to_runtime", "to_model" `+
				`FROM "seat_occupant_changes" WHERE "user_id" = $1 AND "seat_id" = $2 ORDER BY "at" DESC`,
			userID, id)
		if err != nil {
			return err
		}
		defer func() { _ = rows.Close() }()
		for rows.Next() {
			var change domainrepo.OccupantChange
			if err := rows.Scan(&change.ID, &change.UserID, &change.SeatID, &change.Actor, &change.At,
				&change.FromRuntime, &change.FromModel, &change.ToRuntime, &change.ToModel); err != nil {
				return err
			}
			out = append(out, change)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// UpdatePermissionPolicy sets the permission policy of the seat.
func (r *ORMSeatRepository) UpdatePermissionPolicy(ctx context.Context, userID, seatID, permissionPolicy string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`UPDATE "seats" SET "permission_policy" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4`,
			permissionPolicy, time.Now().UTC(), userID, id)
		return err
	})
}

// UpdatePinnedVersion sets the seat type version the seat is pinned to.
func (r *ORMSeatRepository) UpdatePinnedVersion(ctx context.Context, userID, seatID, pinnedVersion string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`UPDATE "seats" SET "pinned_version" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4`,
			pinnedVersion, time.Now().UTC(), userID, id)
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
