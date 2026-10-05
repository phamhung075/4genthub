// Row structs for the team_management tables, which live in the TEAMS section of
// fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql.
//
// Same conventions as seat_orm.go: one Go field per column, tagged with the `db` column
// name, in DDL order; string carries UUID, time.Time carries TIMESTAMP WITH TIME ZONE.
//
// The tables are tenant-scoped by user_id (TEXT) and use no foreign key CASCADE.
package database

import "time"

// TeamORM is a row of teams. UserID is the owning user; slice 1 is single-owner.
type TeamORM struct {
	ID        string    `db:"id"`
	UserID    string    `db:"user_id"`
	Slug      string    `db:"slug"`
	Name      string    `db:"name"`
	CreatedAt time.Time `db:"created_at"`
	UpdatedAt time.Time `db:"updated_at"`
}

// TeamMemberORM is a row of team_members. TeamID is the team_id on the account boundary;
// Role is 'owner' or 'viewer'.
type TeamMemberORM struct {
	ID        string    `db:"id"`
	TeamID    string    `db:"team_id"`
	UserID    string    `db:"user_id"`
	Role      string    `db:"role"`
	CreatedAt time.Time `db:"created_at"`
}
