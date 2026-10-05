package orm

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const moduleVersionJoinSelect = `mv."id"::text, mv."user_id", mv."module_id"::text, mv."version", ` +
	`mv."content", mv."checksum", mv."created_at", m."slug", m."kind"`

// ORMModuleRepository is the ORM ModuleRepository over modules and module_versions.
type ORMModuleRepository struct {
	*baserepo.ORMRepository[seatdb.ModuleORM]
	versions *baserepo.ORMRepository[seatdb.ModuleVersionORM]
}

var _ domainrepo.ModuleRepository = (*ORMModuleRepository)(nil)

// NewORMModuleRepository builds the repository over modules and module_versions.
func NewORMModuleRepository(sessions *database.SessionManager) (*ORMModuleRepository, error) {
	modules, err := baserepo.NewORMRepository[seatdb.ModuleORM]("modules", sessions)
	if err != nil {
		return nil, err
	}
	versions, err := baserepo.NewORMRepository[seatdb.ModuleVersionORM]("module_versions", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMModuleRepository{ORMRepository: modules, versions: versions}, nil
}

// SaveModule get-or-creates the module by user_id + slug; kind is immutable.
func (r *ORMModuleRepository) SaveModule(ctx context.Context, userID, slug string, kind resolver.ModuleKind) (*domainrepo.Module, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", slug))
	if err != nil {
		return nil, err
	}
	if row != nil {
		if row.Kind != string(kind) {
			return nil, fmt.Errorf("module %q already exists with kind %q: %w", slug, row.Kind, domainrepo.ErrModuleKindConflict)
		}
		return moduleToDomain(row), nil
	}
	created, err := r.Create(ctx, baserepo.NewKwargs("user_id", userID, "slug", slug, "kind", string(kind)))
	if err != nil {
		return nil, err
	}
	return moduleToDomain(created), nil
}

// AddVersion appends an immutable module version. Re-adding the same (slug, version)
// with the same content checksum is a no-op; a different checksum is an error.
func (r *ORMModuleRepository) AddVersion(ctx context.Context, userID, slug, version, content string) (*domainrepo.ModuleVersion, error) {
	module, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", slug))
	if err != nil {
		return nil, err
	}
	if module == nil {
		return nil, fmt.Errorf("module %q not found", slug)
	}
	checksum := moduleVersionChecksum(content)
	existing, err := r.versions.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "module_id", module.ID, "version", version))
	if err != nil {
		return nil, err
	}
	if existing != nil {
		if existing.Checksum != checksum {
			return nil, fmt.Errorf("module %q version %q already exists with a different checksum: %w", slug, version, domainrepo.ErrModuleVersionConflict)
		}
		out := moduleVersionToDomain(existing)
		out.Slug, out.Kind = module.Slug, resolver.ModuleKind(module.Kind)
		return out, nil
	}
	created, err := r.versions.Create(ctx, baserepo.NewKwargs(
		"user_id", userID,
		"module_id", module.ID,
		"version", version,
		"content", content,
		"checksum", checksum,
	))
	if err != nil {
		return nil, err
	}
	out := moduleVersionToDomain(created)
	out.Slug, out.Kind = module.Slug, resolver.ModuleKind(module.Kind)
	return out, nil
}

// GetVersion returns one version by slug, or nil when absent.
func (r *ORMModuleRepository) GetVersion(ctx context.Context, userID, slug, version string) (*domainrepo.ModuleVersion, error) {
	query := `SELECT ` + moduleVersionJoinSelect + ` FROM module_versions AS mv ` +
		`JOIN modules AS m ON m."id" = mv."module_id" ` +
		`WHERE mv."user_id" = $1 AND m."slug" = $2 AND mv."version" = $3 LIMIT 1`
	return r.moduleVersionQuery(ctx, query, userID, slug, version)
}

// ListLatest returns the newest version of every module ordered by slug; Content is not loaded.
func (r *ORMModuleRepository) ListLatest(ctx context.Context, userID string) ([]domainrepo.ModuleVersion, error) {
	query := `SELECT DISTINCT ON (m."slug") mv."id"::text, mv."module_id"::text, mv."version", mv."checksum", ` +
		`mv."created_at", m."slug", m."kind" FROM module_versions AS mv ` +
		`JOIN modules AS m ON m."id" = mv."module_id" WHERE mv."user_id" = $1 ` +
		`ORDER BY m."slug", mv."created_at" DESC, mv."id" DESC`
	out := []domainrepo.ModuleVersion{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx, query, userID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			mv := domainrepo.ModuleVersion{UserID: userID}
			var kind string
			if err := rows.Scan(&mv.ID, &mv.ModuleID, &mv.Version, &mv.Checksum, &mv.CreatedAt, &mv.Slug, &kind); err != nil {
				return err
			}
			mv.Kind = resolver.ModuleKind(kind)
			out = append(out, mv)
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (r *ORMModuleRepository) moduleVersionQuery(ctx context.Context, query string, args ...any) (*domainrepo.ModuleVersion, error) {
	var (
		id, userID, moduleID, version, content, checksum, slug, kind string
		createdAt                                                    time.Time
	)
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, query, args...).Scan(
			&id, &userID, &moduleID, &version, &content, &checksum, &createdAt, &slug, &kind)
	})
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &domainrepo.ModuleVersion{
		ID: id, UserID: userID, ModuleID: moduleID, Slug: slug, Kind: resolver.ModuleKind(kind),
		Version: version, Content: content, Checksum: checksum, CreatedAt: createdAt,
	}, nil
}
