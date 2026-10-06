// Table metadata for the TEAMS tables, which live in the TEAMS section of
// fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql — placed
// BEFORE rooms there, because rooms.team_id references teams (id).
//
// The base ORM repository resolves tables by name in the shared Tables registry. The row
// structs live in team_orm.go.
//
// CREATION ORDER IS LOAD-BEARING AND THE CREATOR DOES NOT SORT. createAll
// (task_management/infrastructure/database/database_config.go) walks taskdb.Tables in slice
// order and creates each table only when absent, with no dependency sort, and team_members
// has a foreign key to teams, so the two entries below must stay in that order.
//
// THIS FILE REGISTERS NOTHING. seat_tables.go owns the ordered registry and appends these
// two entries FIRST, because rooms.team_id references teams (id) and rooms is one of its
// entries: with Go initialising a package-level variable after the variables it depends on,
// naming teamManagementDatabaseTables there makes the order explicit rather than a
// consequence of file names. Registering them here as well would create teams twice.
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
		"CREATE UNIQUE INDEX uq_team_members_one_owner ON team_members (team_id) WHERE role = 'owner'",
	}},
}
