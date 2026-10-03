package orm

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const seatTypeVersionJoinSelect = `stv."id"::text, stv."user_id", stv."seat_type_id"::text, ` +
	`stv."version", stv."default_runtime", stv."module_refs", stv."created_at", st."slug"`

// ORMSeatTypeRepository is the ORM SeatTypeRepository over seat_types and seat_type_versions.
type ORMSeatTypeRepository struct {
	*baserepo.ORMRepository[seatdb.SeatTypeORM]
	versions *baserepo.ORMRepository[seatdb.SeatTypeVersionORM]
}

var _ domainrepo.SeatTypeRepository = (*ORMSeatTypeRepository)(nil)

// NewORMSeatTypeRepository builds the repository over seat_types and seat_type_versions.
func NewORMSeatTypeRepository(sessions *database.SessionManager) (*ORMSeatTypeRepository, error) {
	seatTypes, err := baserepo.NewORMRepository[seatdb.SeatTypeORM]("seat_types", sessions)
	if err != nil {
		return nil, err
	}
	versions, err := baserepo.NewORMRepository[seatdb.SeatTypeVersionORM]("seat_type_versions", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMSeatTypeRepository{ORMRepository: seatTypes, versions: versions}, nil
}

// Save get-or-creates the seat type by user_id + slug.
func (r *ORMSeatTypeRepository) Save(ctx context.Context, userID string, seatType domainrepo.SeatType) (*domainrepo.SeatType, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", seatType.Slug))
	if err != nil {
		return nil, err
	}
	if row != nil {
		return seatTypeToDomain(row), nil
	}
	created, err := r.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"slug", seatType.Slug,
		"name", seatType.Name,
		"description", seatType.Description,
	))
	if err != nil {
		return nil, err
	}
	return seatTypeToDomain(created), nil
}

// GetByID returns the seat type, or nil when absent.
func (r *ORMSeatTypeRepository) GetByID(ctx context.Context, userID, seatTypeID string) (*domainrepo.SeatType, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "id", seatTypeID))
	if err != nil || row == nil {
		return nil, err
	}
	return seatTypeToDomain(row), nil
}

// List returns the user's seat types ordered by slug.
func (r *ORMSeatTypeRepository) List(ctx context.Context, userID string) ([]domainrepo.SeatType, error) {
	rows, err := r.FindBy(ctx, baserepo.NewKwargs("user_id", userID))
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.SeatType, 0, len(rows))
	for _, row := range rows {
		out = append(out, *seatTypeToDomain(row))
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Slug < out[j].Slug })
	return out, nil
}

// AddVersion appends an immutable seat type version in one insert. Re-adding the same
// (slug, version) with the same runtime and module refs is a no-op; anything different is
// ErrSeatTypeVersionConflict.
func (r *ORMSeatTypeRepository) AddVersion(ctx context.Context, userID, slug, version, defaultRuntime string, moduleRefs []resolver.ModuleRef) (*domainrepo.SeatTypeVersion, error) {
	seatType, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", slug))
	if err != nil {
		return nil, err
	}
	if seatType == nil {
		return nil, fmt.Errorf("seat type %q not found", slug)
	}
	encoded, err := encodeModuleRefs(moduleRefs)
	if err != nil {
		return nil, err
	}
	checksum, err := moduleRefsChecksum(encoded)
	if err != nil {
		return nil, err
	}
	existing, err := r.versions.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "seat_type_id", seatType.ID, "version", version))
	if err != nil {
		return nil, err
	}
	if existing != nil {
		existingChecksum, err := moduleRefsChecksum(existing.ModuleRefs)
		if err != nil {
			return nil, err
		}
		if existing.DefaultRuntime != defaultRuntime || existingChecksum != checksum {
			return nil, fmt.Errorf("seat type %q version %q already exists with a different runtime or module refs: %w", slug, version, domainrepo.ErrSeatTypeVersionConflict)
		}
		out, err := seatTypeVersionToDomain(existing)
		if err != nil {
			return nil, err
		}
		out.Slug = seatType.Slug
		return out, nil
	}
	created, err := r.versions.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"seat_type_id", seatType.ID,
		"version", version,
		"default_runtime", defaultRuntime,
		"module_refs", encoded,
	))
	if err != nil {
		return nil, err
	}
	out, err := seatTypeVersionToDomain(created)
	if err != nil {
		return nil, err
	}
	out.Slug = seatType.Slug
	return out, nil
}

// GetVersion returns one version by slug, or nil when absent.
func (r *ORMSeatTypeRepository) GetVersion(ctx context.Context, userID, slug, version string) (*domainrepo.SeatTypeVersion, error) {
	query := `SELECT ` + seatTypeVersionJoinSelect + ` FROM seat_type_versions AS stv ` +
		`JOIN seat_types AS st ON st."id" = stv."seat_type_id" ` +
		`WHERE stv."user_id" = $1 AND st."slug" = $2 AND stv."version" = $3 LIMIT 1`
	return r.seatTypeVersionQuery(ctx, query, userID, slug, version)
}

// LatestVersion returns the newest version by created_at then id, or nil when absent.
func (r *ORMSeatTypeRepository) LatestVersion(ctx context.Context, userID, slug string) (*domainrepo.SeatTypeVersion, error) {
	query := `SELECT ` + seatTypeVersionJoinSelect + ` FROM seat_type_versions AS stv ` +
		`JOIN seat_types AS st ON st."id" = stv."seat_type_id" ` +
		`WHERE stv."user_id" = $1 AND st."slug" = $2 ` +
		`ORDER BY stv."created_at" DESC, stv."id" DESC LIMIT 1`
	return r.seatTypeVersionQuery(ctx, query, userID, slug)
}

func (r *ORMSeatTypeRepository) seatTypeVersionQuery(ctx context.Context, query string, args ...any) (*domainrepo.SeatTypeVersion, error) {
	var (
		id, userID, seatTypeID, version, defaultRuntime, slug string
		raw                                                   []byte
		createdAt                                             time.Time
	)
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, query, args...).Scan(&id, &userID, &seatTypeID, &version, &defaultRuntime, &raw, &createdAt, &slug)
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	refs, err := decodeModuleRefs(json.RawMessage(raw))
	if err != nil {
		return nil, err
	}
	return &domainrepo.SeatTypeVersion{
		ID: id, UserID: userID, SeatTypeID: seatTypeID, Slug: slug, Version: version,
		DefaultRuntime: defaultRuntime, ModuleRefs: refs, CreatedAt: createdAt,
	}, nil
}
