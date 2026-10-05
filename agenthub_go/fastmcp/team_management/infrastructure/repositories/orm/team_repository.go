// Package orm is the PostgreSQL implementation of the team_management repositories.
package orm

import (
	"context"
	"database/sql"
	"errors"
	"sort"
	"strings"

	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
	domainrepo "agenthub/fastmcp/team_management/domain/repositories"
)

// ORMTeamRepository is the ORM TeamRepository over teams and team_members.
type ORMTeamRepository struct {
	teams    *baserepo.ORMRepository[seatdb.TeamORM]
	members  *baserepo.ORMRepository[seatdb.TeamMemberORM]
	sessions *database.SessionManager
}

var _ domainrepo.TeamRepository = (*ORMTeamRepository)(nil)

// NewORMTeamRepository builds the repository over teams and team_members.
func NewORMTeamRepository(sessions *database.SessionManager) (*ORMTeamRepository, error) {
	teams, err := baserepo.NewORMRepository[seatdb.TeamORM]("teams", sessions)
	if err != nil {
		return nil, err
	}
	members, err := baserepo.NewORMRepository[seatdb.TeamMemberORM]("team_members", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMTeamRepository{teams: teams, members: members, sessions: sessions}, nil
}

// Create inserts the team and its owner membership in one transaction.
func (r *ORMTeamRepository) Create(ctx context.Context, slug, name, ownerUserID string) (*domainrepo.Team, error) {
	existing, err := r.findByOwnerSlug(ctx, ownerUserID, slug)
	if err != nil {
		return nil, err
	}
	if existing != nil {
		return nil, domainrepo.ErrTeamExists
	}
	var created *seatdb.TeamORM
	err = r.sessions.Transaction(ctx, func(ctx context.Context) error {
		row, err := r.teams.Create(ctx, baserepo.NewKwargs("user_id", ownerUserID, "slug", slug, "name", name))
		if err != nil {
			return err
		}
		if _, err := r.members.Create(ctx, baserepo.NewKwargs(
			"team_id", row.ID, "user_id", ownerUserID, "role", domainrepo.RoleOwner,
		)); err != nil {
			return err
		}
		created = row
		return nil
	})
	if err != nil {
		if isUniqueViolation(err) {
			return nil, domainrepo.ErrTeamExists
		}
		return nil, err
	}
	return teamToDomain(created), nil
}

// findByOwnerSlug returns the owning user's team with the slug, or nil when absent. Create
// uses it so the duplicate check is explicit rather than left to the unique index alone.
func (r *ORMTeamRepository) findByOwnerSlug(ctx context.Context, ownerUserID, slug string) (*seatdb.TeamORM, error) {
	return r.teams.FindOneBy(ctx, baserepo.NewKwargs("user_id", ownerUserID, "slug", slug))
}

// FindForMember joins the caller's membership to the team with the slug, or nil when the
// caller is not a member. The join is what makes the slug unambiguous: two owners may hold
// the same slug.
func (r *ORMTeamRepository) FindForMember(ctx context.Context, userID, slug string) (*domainrepo.Team, error) {
	var out *seatdb.TeamORM
	err := r.teams.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row := &seatdb.TeamORM{}
		err := s.QueryRowContext(ctx,
			`SELECT t."id"::text, t."user_id", t."slug", t."name", t."created_at", t."updated_at" `+
				`FROM "teams" AS t JOIN "team_members" AS m ON m."team_id" = t."id" `+
				`WHERE m."user_id" = $1 AND t."slug" = $2 LIMIT 1`, userID, slug,
		).Scan(&row.ID, &row.UserID, &row.Slug, &row.Name, &row.CreatedAt, &row.UpdatedAt)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		out = row
		return nil
	})
	if err != nil || out == nil {
		return nil, err
	}
	return teamToDomain(out), nil
}

// ListForMember joins the caller's memberships to the teams, ordered by slug.
func (r *ORMTeamRepository) ListForMember(ctx context.Context, userID string) ([]domainrepo.Membership, error) {
	var out []domainrepo.Membership
	err := r.teams.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT t."id"::text, t."user_id", t."slug", t."name", t."created_at", t."updated_at", m."role" `+
				`FROM "teams" AS t JOIN "team_members" AS m ON m."team_id" = t."id" `+
				`WHERE m."user_id" = $1 ORDER BY t."slug"`, userID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var row seatdb.TeamORM
			var role string
			if err := rows.Scan(&row.ID, &row.UserID, &row.Slug, &row.Name, &row.CreatedAt, &row.UpdatedAt, &role); err != nil {
				return err
			}
			out = append(out, domainrepo.Membership{Team: *teamToDomain(&row), Role: role})
		}
		return rows.Err()
	})
	return out, err
}

// Delete removes the team and its member rows, members first (there is no foreign key
// CASCADE; the application layer cascades).
func (r *ORMTeamRepository) Delete(ctx context.Context, teamID string) error {
	id, err := database.UnifiedUUIDBindParam(teamID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.sessions.Transaction(ctx, func(ctx context.Context) error {
		if err := r.members.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, `DELETE FROM "team_members" WHERE "team_id" = $1`, id)
			return err
		}); err != nil {
			return err
		}
		return r.teams.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			_, err := s.ExecContext(ctx, `DELETE FROM "teams" WHERE "id" = $1`, id)
			return err
		})
	})
}

// Membership returns the member row, or nil when userID is not a member.
func (r *ORMTeamRepository) Membership(ctx context.Context, teamID, userID string) (*domainrepo.TeamMember, error) {
	row, err := r.members.FindOneBy(ctx, baserepo.NewKwargs("team_id", teamID, "user_id", userID))
	if err != nil || row == nil {
		return nil, err
	}
	return memberToDomain(row), nil
}

// ListMembers returns the members, owner first then by user id.
func (r *ORMTeamRepository) ListMembers(ctx context.Context, teamID string) ([]domainrepo.TeamMember, error) {
	rows, err := r.members.FindBy(ctx, baserepo.NewKwargs("team_id", teamID))
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.TeamMember, 0, len(rows))
	for _, row := range rows {
		out = append(out, *memberToDomain(row))
	}
	sort.Slice(out, func(i, j int) bool {
		if (out[i].Role == domainrepo.RoleOwner) != (out[j].Role == domainrepo.RoleOwner) {
			return out[i].Role == domainrepo.RoleOwner
		}
		return out[i].UserID < out[j].UserID
	})
	return out, nil
}

// AddMember inserts a member; ErrMemberExists when the team already has that member.
func (r *ORMTeamRepository) AddMember(ctx context.Context, teamID, userID, role string) (*domainrepo.TeamMember, error) {
	created, err := r.members.Create(ctx, baserepo.NewKwargs("team_id", teamID, "user_id", userID, "role", role))
	if err != nil {
		if isUniqueViolation(err) {
			return nil, domainrepo.ErrMemberExists
		}
		return nil, err
	}
	return memberToDomain(created), nil
}

// UpdateRole changes a member's role; ErrTeamNotFound when the member is absent.
func (r *ORMTeamRepository) UpdateRole(ctx context.Context, teamID, userID, role string) error {
	id, err := database.UnifiedUUIDBindParam(teamID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.members.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`UPDATE "team_members" SET "role" = $1 WHERE "team_id" = $2 AND "user_id" = $3`, role, id, userID)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		if err != nil {
			return err
		}
		if n == 0 {
			return domainrepo.ErrTeamNotFound
		}
		return nil
	})
}

// RemoveMember deletes a member row and reports whether it existed.
func (r *ORMTeamRepository) RemoveMember(ctx context.Context, teamID, userID string) (bool, error) {
	id, err := database.UnifiedUUIDBindParam(teamID, database.DialectPostgres)
	if err != nil {
		return false, err
	}
	removed := false
	err = r.members.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`DELETE FROM "team_members" WHERE "team_id" = $1 AND "user_id" = $2`, id, userID)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		removed = n > 0
		return err
	})
	return removed, err
}

func teamToDomain(row *seatdb.TeamORM) *domainrepo.Team {
	return &domainrepo.Team{
		ID: row.ID, UserID: row.UserID, Slug: row.Slug, Name: row.Name,
		CreatedAt: row.CreatedAt, UpdatedAt: row.UpdatedAt,
	}
}

func memberToDomain(row *seatdb.TeamMemberORM) *domainrepo.TeamMember {
	return &domainrepo.TeamMember{
		ID: row.ID, TeamID: row.TeamID, UserID: row.UserID, Role: row.Role, CreatedAt: row.CreatedAt,
	}
}

// isUniqueViolation reports a PostgreSQL unique violation (SQLSTATE 23505). The base
// repository turns driver errors into exceptions that keep only the driver's message, which
// ends in "(SQLSTATE <code>)", so the code is read from the text. Same helper as the
// seat_management ORM repositories (it is unexported there).
func isUniqueViolation(err error) bool {
	var integrity *exceptions.DatabaseIntegrityException
	return errors.As(err, &integrity) && strings.Contains(err.Error(), "(SQLSTATE 23505)")
}
