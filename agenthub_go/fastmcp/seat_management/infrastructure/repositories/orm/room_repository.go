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

// roomReturning is the rooms column list every read here shares, in DDL order, with team_id
// cast so a NULL arrives as nil.
const roomReturning = `"id"::text, "user_id", "slug", "name", "team_id"::text, "created_at", "updated_at"`

// roomVisibilitySQL is the D5 sharing predicate: a room is visible to its owner or to a member
// of the team it is shared with. ONE TEAM ID, VIEWER READ-ONLY — the predicate only ever WIDENS
// READS: every write below still matches "user_id" = the caller, so a viewer cannot mutate, and
// a caller who is neither the owner nor a member matches nothing (the handlers answer 404).
//
// team_members belongs to another bounded context (team_management) but shares this schema, so
// the membership check is a subquery rather than a join these ports would have to model.
const roomVisibilitySQL = `("user_id" = $1 OR "team_id" IN (
	SELECT "team_id" FROM "team_members" WHERE "user_id" = $1))`

// ORMRoomRepository is the ORM RoomRepository over rooms.
type ORMRoomRepository struct {
	*baserepo.ORMRepository[seatdb.RoomORM]
}

var _ domainrepo.RoomRepository = (*ORMRoomRepository)(nil)

// NewORMRoomRepository builds the repository over rooms.
func NewORMRoomRepository(sessions *database.SessionManager) (*ORMRoomRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.RoomORM]("rooms", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMRoomRepository{ORMRepository: base}, nil
}

// Save get-or-creates the room by user_id + slug. It is owner-scoped: creating, or finding,
// another owner's room is not something a viewer may do by posting a room.
func (r *ORMRoomRepository) Save(ctx context.Context, userID string, room domainrepo.Room) (*domainrepo.Room, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", room.Slug))
	if err != nil {
		return nil, err
	}
	if row != nil {
		return roomToDomain(row), nil
	}
	created, err := r.Create(ctx, baserepo.NewKwargs("user_id", userID, "slug", room.Slug, "name", room.Name))
	if err != nil {
		return nil, err
	}
	return roomToDomain(created), nil
}

// GetBySlug returns the caller's OWN room with the slug, or nil when absent. Writes resolve the
// room through this method, so it stays owner-scoped; reads that a viewer may perform use
// GetVisibleBySlug.
func (r *ORMRoomRepository) GetBySlug(ctx context.Context, userID, slug string) (*domainrepo.Room, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "slug", slug))
	if err != nil || row == nil {
		return nil, err
	}
	return roomToDomain(row), nil
}

// GetByID returns the caller's own room with the id, or nil when absent.
func (r *ORMRoomRepository) GetByID(ctx context.Context, userID, roomID string) (*domainrepo.Room, error) {
	row, err := r.FindOneBy(ctx, baserepo.NewKwargs("user_id", userID, "id", roomID))
	if err != nil || row == nil {
		return nil, err
	}
	return roomToDomain(row), nil
}

// List returns the caller's own rooms plus the rooms shared with a team the caller belongs to,
// ordered by slug.
func (r *ORMRoomRepository) List(ctx context.Context, userID string) ([]domainrepo.Room, error) {
	var out []domainrepo.Room
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT `+roomReturning+` FROM "rooms" WHERE `+roomVisibilitySQL+` ORDER BY "slug"`, userID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var row seatdb.RoomORM
			if err := rows.Scan(&row.ID, &row.UserID, &row.Slug, &row.Name, &row.TeamID,
				&row.CreatedAt, &row.UpdatedAt); err != nil {
				return err
			}
			out = append(out, *roomToDomain(&row))
		}
		return rows.Err()
	})
	if err != nil {
		return nil, err
	}
	return out, nil
}

// GetVisibleBySlug returns the caller's own room with the slug, or a room shared with a team the
// caller belongs to, or nil when the caller has neither. A slug is unique per owner rather than
// globally, so when the caller owns a room with the same slug the caller's own room wins.
func (r *ORMRoomRepository) GetVisibleBySlug(ctx context.Context, userID, slug string) (*domainrepo.Room, error) {
	var (
		row   seatdb.RoomORM
		found bool
	)
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		err := s.QueryRowContext(ctx,
			`SELECT `+roomReturning+` FROM "rooms" WHERE `+roomVisibilitySQL+` AND "slug" = $2 `+
				`ORDER BY ("user_id" = $1) DESC LIMIT 1`,
			userID, slug).Scan(&row.ID, &row.UserID, &row.Slug, &row.Name, &row.TeamID,
			&row.CreatedAt, &row.UpdatedAt)
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		found = true
		return nil
	})
	if err != nil || !found {
		return nil, err
	}
	return roomToDomain(&row), nil
}

// SetTeam shares the room with teamID, or makes it private again when teamID is empty. The
// update matches the room's owner, so a viewer's attempt changes nothing and returns
// ErrRoomNotOwned.
func (r *ORMRoomRepository) SetTeam(ctx context.Context, userID, roomID, teamID string) error {
	id, err := database.UnifiedUUIDBindParam(roomID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			`UPDATE "rooms" SET "team_id" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4`,
			nullableUUID(teamID), time.Now().UTC(), userID, id)
		if err != nil {
			return err
		}
		n, err := res.RowsAffected()
		if err != nil {
			return err
		}
		if n == 0 {
			return domainrepo.ErrRoomNotOwned
		}
		return nil
	})
}

// Delete removes the room row; the application layer removes its seats and overlay first.
func (r *ORMRoomRepository) Delete(ctx context.Context, userID, roomID string) error {
	id, err := database.UnifiedUUIDBindParam(roomID, database.DialectPostgres)
	if err != nil {
		return err
	}
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM "rooms" WHERE "user_id" = $1 AND "id" = $2`, userID, id)
		return err
	})
}
