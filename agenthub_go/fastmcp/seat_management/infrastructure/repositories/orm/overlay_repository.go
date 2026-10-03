package orm

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const overlayReturning = `"id"::text, "user_id", "scope", "room_id"::text, "seat_id"::text, ` +
	`"ops", "created_at", "updated_at"`

// ORMOverlayRepository is the ORM OverlayRepository over overlays.
type ORMOverlayRepository struct {
	*baserepo.ORMRepository[seatdb.OverlayORM]
}

var _ domainrepo.OverlayRepository = (*ORMOverlayRepository)(nil)

// NewORMOverlayRepository builds the repository over overlays.
func NewORMOverlayRepository(sessions *database.SessionManager) (*ORMOverlayRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.OverlayORM]("overlays", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMOverlayRepository{ORMRepository: base}, nil
}

// Find returns the overlay of one scope target, or nil when absent.
func (r *ORMOverlayRepository) Find(ctx context.Context, userID, scope, roomID, seatID string) (*domainrepo.Overlay, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"scope", scope,
		"room_id", nullableUUID(roomID),
		"seat_id", nullableUUID(seatID),
	))
	if err != nil || row == nil {
		return nil, err
	}
	return overlayToDomain(row)
}

// Upsert creates or replaces the single overlay of a scope target.
func (r *ORMOverlayRepository) Upsert(ctx context.Context, userID string, overlay domainrepo.Overlay) (*domainrepo.Overlay, error) {
	if err := overlay.ValidateTarget(); err != nil {
		return nil, err
	}
	ops, err := encodeOps(overlay.Ops)
	if err != nil {
		return nil, err
	}
	existing, err := r.Find(ctx, userID, overlay.Scope, overlay.RoomID, overlay.SeatID)
	if err != nil {
		return nil, err
	}
	if existing != nil {
		row, err := r.updateOps(ctx, userID, existing.ID, ops)
		if err != nil {
			return nil, err
		}
		if row == nil {
			return nil, nil
		}
		return overlayToDomain(row)
	}
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"scope", overlay.Scope,
		"room_id", nullableUUID(overlay.RoomID),
		"seat_id", nullableUUID(overlay.SeatID),
		"ops", ops,
	))
	if err != nil {
		return nil, err
	}
	return overlayToDomain(created)
}

func (r *ORMOverlayRepository) updateOps(ctx context.Context, userID, overlayID string, ops json.RawMessage) (*seatdb.OverlayORM, error) {
	id, err := database.UnifiedUUIDBindParam(overlayID, database.DialectPostgres)
	if err != nil {
		return nil, err
	}
	row := &seatdb.OverlayORM{}
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`UPDATE "overlays" SET "ops" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4 RETURNING `+overlayReturning,
			string(ops), time.Now().UTC(), userID, id,
		).Scan(&row.ID, &row.UserID, &row.Scope, &row.RoomID, &row.SeatID, &row.Ops, &row.CreatedAt, &row.UpdatedAt)
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return row, nil
}
