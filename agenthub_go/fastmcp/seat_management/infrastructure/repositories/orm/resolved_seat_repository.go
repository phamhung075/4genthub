package orm

import (
	"context"
	"database/sql"
	"errors"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ORMResolvedSeatRepository is the ORM ResolvedSeatRepository over resolved_seats.
type ORMResolvedSeatRepository struct {
	*baserepo.ORMRepository[seatdb.ResolvedSeatORM]
}

var _ domainrepo.ResolvedSeatRepository = (*ORMResolvedSeatRepository)(nil)

// NewORMResolvedSeatRepository builds the repository over resolved_seats.
func NewORMResolvedSeatRepository(sessions *database.SessionManager) (*ORMResolvedSeatRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.ResolvedSeatORM]("resolved_seats", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMResolvedSeatRepository{ORMRepository: base}, nil
}

// Save appends the snapshot. Re-saving the same (seat_id, hash) is a no-op.
func (r *ORMResolvedSeatRepository) Save(ctx context.Context, userID string, seat domainrepo.ResolvedSeat) (*domainrepo.ResolvedSeat, error) {
	existing, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "seat_id", seat.SeatID, "hash", seat.Hash))
	if err != nil {
		return nil, err
	}
	if existing != nil {
		return resolvedSeatToDomain(existing)
	}
	files, err := encodeFiles(seat.Files)
	if err != nil {
		return nil, err
	}
	policy, err := encodePolicy(seat.Policy)
	if err != nil {
		return nil, err
	}
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"seat_id", seat.SeatID,
		"hash", seat.Hash,
		"runtime", seat.Runtime,
		"files", files,
		"policy", policy,
	))
	if err != nil {
		return nil, err
	}
	return resolvedSeatToDomain(created)
}

// GetLatest returns the newest snapshot of a seat by created_at then id, or nil when absent.
func (r *ORMResolvedSeatRepository) GetLatest(ctx context.Context, userID, seatID string) (*domainrepo.ResolvedSeat, error) {
	var (
		id, rowUserID, rowSeatID, hash, runtime string
		rawFiles, rawPolicy                     []byte
		createdAt                               time.Time
	)
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`SELECT "id"::text, "user_id", "seat_id"::text, "hash", "runtime", "files", "policy", "created_at" `+
				`FROM "resolved_seats" WHERE "user_id" = $1 AND "seat_id" = $2 `+
				`ORDER BY "created_at" DESC, "id" DESC LIMIT 1`,
			userID, seatID,
		).Scan(&id, &rowUserID, &rowSeatID, &hash, &runtime, &rawFiles, &rawPolicy, &createdAt)
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	files, err := decodeFiles(rawFiles)
	if err != nil {
		return nil, err
	}
	policy, err := decodePolicy(rawPolicy)
	if err != nil {
		return nil, err
	}
	return &domainrepo.ResolvedSeat{
		ID: id, UserID: rowUserID, SeatID: rowSeatID, Hash: hash, Runtime: runtime,
		Files: files, Policy: policy, CreatedAt: createdAt,
	}, nil
}
