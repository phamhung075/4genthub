package orm

import (
	"context"
	"database/sql"
	"errors"
	"sort"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const seatLinkReturning = `"id"::text, "user_id", "from_seat_id"::text, "to_seat_id"::text, ` +
	`"kind", "allow", "created_at"`

// ORMSeatLinkRepository is the ORM SeatLinkRepository over seat_links.
type ORMSeatLinkRepository struct {
	*baserepo.ORMRepository[seatdb.SeatLinkORM]
}

var _ domainrepo.SeatLinkRepository = (*ORMSeatLinkRepository)(nil)

// NewORMSeatLinkRepository builds the repository over seat_links.
func NewORMSeatLinkRepository(sessions *database.SessionManager) (*ORMSeatLinkRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.SeatLinkORM]("seat_links", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMSeatLinkRepository{ORMRepository: base}, nil
}

// Upsert creates the link or updates its allow flag; (from, to, kind) is unique.
func (r *ORMSeatLinkRepository) Upsert(ctx context.Context, userID string, link domainrepo.SeatLink) (*domainrepo.SeatLink, error) {
	existing, err := r.FindOneBy(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"from_seat_id", link.FromSeatID,
		"to_seat_id", link.ToSeatID,
		"kind", link.Kind,
	))
	if err != nil {
		return nil, err
	}
	if existing != nil {
		row, err := r.updateAllow(ctx, userID, existing.ID, link.Allow)
		if err != nil {
			return nil, err
		}
		if row == nil {
			return nil, nil
		}
		return seatLinkToDomain(row), nil
	}
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"from_seat_id", link.FromSeatID,
		"to_seat_id", link.ToSeatID,
		"kind", link.Kind,
		"allow", link.Allow,
	))
	if err != nil {
		return nil, err
	}
	return seatLinkToDomain(created), nil
}

func (r *ORMSeatLinkRepository) updateAllow(ctx context.Context, userID, linkID string, allow bool) (*seatdb.SeatLinkORM, error) {
	id, err := database.UnifiedUUIDBindParam(linkID, database.DialectPostgres)
	if err != nil {
		return nil, err
	}
	row := &seatdb.SeatLinkORM{}
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`UPDATE "seat_links" SET "allow" = $1 WHERE "user_id" = $2 AND "id" = $3 RETURNING `+seatLinkReturning,
			allow, userID, id,
		).Scan(&row.ID, &row.UserID, &row.FromSeatID, &row.ToSeatID, &row.Kind, &row.Allow, &row.CreatedAt)
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return row, nil
}

// Delete removes the link and reports whether it existed.
func (r *ORMSeatLinkRepository) Delete(ctx context.Context, userID, fromSeatID, toSeatID, kind string) (bool, error) {
	from, err := database.UnifiedUUIDBindParam(fromSeatID, database.DialectPostgres)
	if err != nil {
		return false, err
	}
	to, err := database.UnifiedUUIDBindParam(toSeatID, database.DialectPostgres)
	if err != nil {
		return false, err
	}
	deleted := false
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`DELETE FROM "seat_links" WHERE "user_id" = $1 AND "from_seat_id" = $2 AND "to_seat_id" = $3 AND "kind" = $4`,
			userID, from, to, kind)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		deleted = n > 0
		return err
	})
	return deleted, err
}

// DeleteBySeat removes every link that starts or ends at the seat.
func (r *ORMSeatLinkRepository) DeleteBySeat(ctx context.Context, userID, seatID string) error {
	id, err := database.UnifiedUUIDBindParam(seatID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`DELETE FROM "seat_links" WHERE "user_id" = $1 AND ("from_seat_id" = $2 OR "to_seat_id" = $2)`, userID, id)
		return err
	})
}

// ListFrom returns the links originating at a seat, ordered by target then kind.
func (r *ORMSeatLinkRepository) ListFrom(ctx context.Context, userID, seatID string) ([]domainrepo.SeatLink, error) {
	rows, err := r.FindBy(ctx, baserepo.NewKwargs("user_id", userID, "from_seat_id", seatID))
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.SeatLink, 0, len(rows))
	for _, row := range rows {
		out = append(out, *seatLinkToDomain(row))
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].ToSeatID != out[j].ToSeatID {
			return out[i].ToSeatID < out[j].ToSeatID
		}
		return out[i].Kind < out[j].Kind
	})
	return out, nil
}
