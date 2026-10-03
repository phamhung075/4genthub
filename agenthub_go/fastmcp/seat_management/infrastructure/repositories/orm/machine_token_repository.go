package orm

import (
	"context"
	"database/sql"
	"errors"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ORMMachineTokenRepository is the ORM MachineTokenRepository over machine_tokens.
type ORMMachineTokenRepository struct {
	*baserepo.ORMRepository[seatdb.MachineTokenORM]
}

var _ domainrepo.MachineTokenRepository = (*ORMMachineTokenRepository)(nil)

// NewORMMachineTokenRepository builds the repository over machine_tokens.
func NewORMMachineTokenRepository(sessions *database.SessionManager) (*ORMMachineTokenRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.MachineTokenORM]("machine_tokens", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMMachineTokenRepository{ORMRepository: base}, nil
}

// Create stores an active token. The partial unique index uq_machine_tokens_active allows one
// active token per (user, machine); a violation is ErrMachineTokenExists.
func (r *ORMMachineTokenRepository) Create(ctx context.Context, userID, machineID, tokenHash string) (*domainrepo.MachineToken, error) {
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"machine_id", machineID,
		"token_hash", tokenHash,
	))
	var integrity *exceptions.DatabaseIntegrityException
	if errors.As(err, &integrity) {
		return nil, domainrepo.ErrMachineTokenExists
	}
	if err != nil {
		return nil, err
	}
	return machineTokenToDomain(created), nil
}

// Revoke sets revoked_at on the machine's active token and reports whether there was one.
func (r *ORMMachineTokenRepository) Revoke(ctx context.Context, userID, machineID string) (bool, error) {
	revoked := false
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`UPDATE "machine_tokens" SET "revoked_at" = $1 WHERE "user_id" = $2 AND "machine_id" = $3 AND "revoked_at" IS NULL`,
			time.Now().UTC(), userID, machineID)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		revoked = n > 0
		return err
	})
	return revoked, err
}

// FindActive returns the active token with the hash, or nil.
func (r *ORMMachineTokenRepository) FindActive(ctx context.Context, tokenHash string) (*domainrepo.MachineToken, error) {
	var out *domainrepo.MachineToken
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row := &seatdb.MachineTokenORM{}
		err := s.QueryRowContext(ctx,
			`SELECT "id"::text, "user_id", "machine_id", "token_hash", "created_at", "revoked_at" `+
				`FROM "machine_tokens" WHERE "token_hash" = $1 AND "revoked_at" IS NULL`, tokenHash,
		).Scan(&row.ID, &row.UserID, &row.MachineID, &row.TokenHash, &row.CreatedAt, &row.RevokedAt)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		out = machineTokenToDomain(row)
		return nil
	})
	return out, err
}

func machineTokenToDomain(row *seatdb.MachineTokenORM) *domainrepo.MachineToken {
	return &domainrepo.MachineToken{
		ID: row.ID, UserID: row.UserID, MachineID: row.MachineID, TokenHash: row.TokenHash,
		CreatedAt: row.CreatedAt, RevokedAt: row.RevokedAt,
	}
}
