// Table metadata for the TEAMS section of
// fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql.
//
// Registered into the shared Tables registry here (the base ORM repository resolves tables
// by name there). The row structs live in team_orm.go. Appended by a second init() so the
// teams come after the seat tables (team_members references teams).
package database

import (
	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

var teamManagementDatabaseTables = []taskdb.TableDef{
	{Name: "teams", Model: "TeamORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "slug", Attr: "slug", GoField: "Slug", SQLType: "TEXT", Nullable: false},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE teams (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tslug TEXT NOT NULL,\n" +
			"\tname TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_teams_user_slug UNIQUE (user_id, slug)\n" +
			")",
		"CREATE INDEX ix_teams_user_id ON teams (user_id)",
	}},
	{Name: "team_members", Model: "TeamMemberORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "team_id", Attr: "team_id", GoField: "TeamID", SQLType: "UUID", Nullable: false},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "role", Attr: "role", GoField: "Role", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE team_members (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tteam_id UUID NOT NULL REFERENCES teams (id),\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\trole TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_team_members_team_user UNIQUE (team_id, user_id),\n" +
			"\tCONSTRAINT ck_team_members_role CHECK (role IN ('owner', 'viewer'))\n" +
			")",
		"CREATE INDEX ix_team_members_team_id ON team_members (team_id)",
		"CREATE INDEX ix_team_members_user_id ON team_members (user_id)",
	}},
}

func init() { taskdb.Tables = append(taskdb.Tables, teamManagementDatabaseTables...) }
