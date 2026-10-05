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

const seatSettingsReturning = `"user_id", "follow_latest", "updated_at"`

// ORMSeatSettingsRepository is the ORM SeatSettingsRepository over seat_settings.
type ORMSeatSettingsRepository struct {
	*baserepo.ORMRepository[seatdb.SeatSettingsORM]
}

var _ domainrepo.SeatSettingsRepository = (*ORMSeatSettingsRepository)(nil)

// NewORMSeatSettingsRepository builds the repository over seat_settings.
func NewORMSeatSettingsRepository(sessions *database.SessionManager) (*ORMSeatSettingsRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.SeatSettingsORM]("seat_settings", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMSeatSettingsRepository{ORMRepository: base}, nil
}

// Get returns the user's settings, defaulting to follow_latest=false when no row exists.
func (r *ORMSeatSettingsRepository) Get(ctx context.Context, userID string) (*domainrepo.SeatSettings, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID))
	if err != nil {
		return nil, err
	}
	if row == nil {
		return &domainrepo.SeatSettings{UserID: userID}, nil
	}
	return seatSettingsToDomain(row), nil
}

// Set upserts the user's follow_latest setting.
func (r *ORMSeatSettingsRepository) Set(ctx context.Context, userID string, followLatest bool) (*domainrepo.SeatSettings, error) {
	existing, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID))
	if err != nil {
		return nil, err
	}
	if existing != nil {
		updated, err := r.updateFollowLatest(ctx, userID, followLatest)
		if err != nil {
			return nil, err
		}
		if updated != nil {
			return updated, nil
		}
	}
	created, err := r.ORMRepository.Create(ctx, baserepo.NewKwargs("user_id", userID, "follow_latest", followLatest))
	if err != nil {
		return nil, err
	}
	return seatSettingsToDomain(created), nil
}

func (r *ORMSeatSettingsRepository) updateFollowLatest(ctx context.Context, userID string, followLatest bool) (*domainrepo.SeatSettings, error) {
	row := &seatdb.SeatSettingsORM{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`UPDATE "seat_settings" SET "follow_latest" = $1, "updated_at" = $2 WHERE "user_id" = $3 RETURNING `+seatSettingsReturning,
			followLatest, time.Now().UTC(), userID,
		).Scan(&row.UserID, &row.FollowLatest, &row.UpdatedAt)
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return seatSettingsToDomain(row), nil
}
