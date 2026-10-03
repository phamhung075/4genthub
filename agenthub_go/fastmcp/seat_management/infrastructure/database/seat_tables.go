// Table metadata for the seat_management schema
// (fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql).
//
// The generated task_management metadata does not include these tables, so they are
// registered into the shared Tables registry here (the base ORM repository resolves tables
// by name there). The row structs live in seat_orm.go.
package database

import (
	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

var seatManagementDatabaseTables = []taskdb.TableDef{
	{Name: "modules", Model: "ModuleORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "slug", Attr: "slug", GoField: "Slug", SQLType: "TEXT", Nullable: false},
		{Name: "kind", Attr: "kind", GoField: "Kind", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE modules (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tslug TEXT NOT NULL,\n" +
			"\tkind TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_modules_user_slug UNIQUE (user_id, slug),\n" +
			"\tCONSTRAINT ck_modules_kind CHECK (kind IN ('instruction', 'document', 'skill', 'tool', 'memory'))\n" +
			")",
		"CREATE INDEX ix_modules_user_id ON modules (user_id)",
	}},
	{Name: "module_versions", Model: "ModuleVersionORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "module_id", Attr: "module_id", GoField: "ModuleID", SQLType: "UUID", Nullable: false},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "TEXT", Nullable: false},
		{Name: "content", Attr: "content", GoField: "Content", SQLType: "TEXT", Nullable: false},
		{Name: "checksum", Attr: "checksum", GoField: "Checksum", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE module_versions (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tmodule_id UUID NOT NULL REFERENCES modules (id),\n" +
			"\tversion TEXT NOT NULL,\n" +
			"\tcontent TEXT NOT NULL,\n" +
			"\tchecksum TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_module_versions_module_version UNIQUE (module_id, version)\n" +
			")",
		"CREATE INDEX ix_module_versions_user_id ON module_versions (user_id)",
		"CREATE INDEX ix_module_versions_module_id ON module_versions (module_id)",
	}},
	{Name: "seat_types", Model: "SeatTypeORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "slug", Attr: "slug", GoField: "Slug", SQLType: "TEXT", Nullable: false},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "TEXT", Nullable: false},
		{Name: "description", Attr: "description", GoField: "Description", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE seat_types (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tslug TEXT NOT NULL,\n" +
			"\tname TEXT NOT NULL,\n" +
			"\tdescription TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_seat_types_user_slug UNIQUE (user_id, slug)\n" +
			")",
		"CREATE INDEX ix_seat_types_user_id ON seat_types (user_id)",
	}},
	{Name: "seat_type_versions", Model: "SeatTypeVersionORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "seat_type_id", Attr: "seat_type_id", GoField: "SeatTypeID", SQLType: "UUID", Nullable: false},
		{Name: "version", Attr: "version", GoField: "Version", SQLType: "TEXT", Nullable: false},
		{Name: "default_runtime", Attr: "default_runtime", GoField: "DefaultRuntime", SQLType: "TEXT", Nullable: false},
		{Name: "module_refs", Attr: "module_refs", GoField: "ModuleRefs", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyList},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE seat_type_versions (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tseat_type_id UUID NOT NULL REFERENCES seat_types (id),\n" +
			"\tversion TEXT NOT NULL,\n" +
			"\tdefault_runtime TEXT NOT NULL,\n" +
			"\tmodule_refs JSONB NOT NULL DEFAULT '[]'::jsonb,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_seat_type_versions_seat_type_version UNIQUE (seat_type_id, version)\n" +
			")",
		"CREATE INDEX ix_seat_type_versions_user_id ON seat_type_versions (user_id)",
		"CREATE INDEX ix_seat_type_versions_seat_type_id ON seat_type_versions (seat_type_id)",
	}},
	{Name: "rooms", Model: "RoomORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "slug", Attr: "slug", GoField: "Slug", SQLType: "TEXT", Nullable: false},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE rooms (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tslug TEXT NOT NULL,\n" +
			"\tname TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_rooms_user_slug UNIQUE (user_id, slug)\n" +
			")",
		"CREATE INDEX ix_rooms_user_id ON rooms (user_id)",
	}},
	{Name: "seats", Model: "SeatORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "room_id", Attr: "room_id", GoField: "RoomID", SQLType: "UUID", Nullable: false},
		{Name: "seat_key", Attr: "seat_key", GoField: "SeatKey", SQLType: "TEXT", Nullable: false},
		{Name: "seat_type_id", Attr: "seat_type_id", GoField: "SeatTypeID", SQLType: "UUID", Nullable: false},
		{Name: "pinned_version", Attr: "pinned_version", GoField: "PinnedVersion", SQLType: "TEXT", Nullable: true},
		{Name: "runtime", Attr: "runtime", GoField: "Runtime", SQLType: "TEXT", Nullable: false},
		{Name: "model", Attr: "model", GoField: "Model", SQLType: "TEXT", Nullable: false},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "TEXT", Nullable: false, Default: taskdb.DefaultString, DefaultValue: "\"active\""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE seats (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\troom_id UUID NOT NULL REFERENCES rooms (id),\n" +
			"\tseat_key TEXT NOT NULL,\n" +
			"\tseat_type_id UUID NOT NULL REFERENCES seat_types (id),\n" +
			"\tpinned_version TEXT,\n" +
			"\truntime TEXT NOT NULL,\n" +
			"\tmodel TEXT NOT NULL,\n" +
			"\tstatus TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_seats_room_seat_key UNIQUE (room_id, seat_key),\n" +
			"\tCONSTRAINT ck_seats_status CHECK (status IN ('active', 'removed'))\n" +
			")",
		"CREATE INDEX ix_seats_user_id ON seats (user_id)",
		"CREATE INDEX ix_seats_room_id ON seats (room_id)",
		"CREATE INDEX ix_seats_seat_type_id ON seats (seat_type_id)",
	}},
	{Name: "overlays", Model: "OverlayORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "scope", Attr: "scope", GoField: "Scope", SQLType: "TEXT", Nullable: false},
		{Name: "room_id", Attr: "room_id", GoField: "RoomID", SQLType: "UUID", Nullable: true},
		{Name: "seat_id", Attr: "seat_id", GoField: "SeatID", SQLType: "UUID", Nullable: true},
		{Name: "ops", Attr: "ops", GoField: "Ops", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyList},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE overlays (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tscope TEXT NOT NULL,\n" +
			"\troom_id UUID REFERENCES rooms (id),\n" +
			"\tseat_id UUID REFERENCES seats (id),\n" +
			"\tops JSONB NOT NULL DEFAULT '[]'::jsonb,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT ck_overlays_scope CHECK (scope IN ('company', 'room', 'seat')),\n" +
			"\tCONSTRAINT ck_overlays_scope_target CHECK (\n" +
			"\t\t(scope = 'company' AND room_id IS NULL AND seat_id IS NULL)\n" +
			"\t\tOR (scope = 'room' AND room_id IS NOT NULL AND seat_id IS NULL)\n" +
			"\t\tOR (scope = 'seat' AND seat_id IS NOT NULL AND room_id IS NULL)\n" +
			"\t)\n" +
			")",
		"CREATE INDEX ix_overlays_user_id ON overlays (user_id)",
		"CREATE INDEX ix_overlays_room_id ON overlays (room_id)",
		"CREATE INDEX ix_overlays_seat_id ON overlays (seat_id)",
		"CREATE UNIQUE INDEX uq_overlays_target ON overlays (user_id, scope, COALESCE(room_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(seat_id, '00000000-0000-0000-0000-000000000000'::uuid))",
	}},
	{Name: "seat_links", Model: "SeatLinkORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "from_seat_id", Attr: "from_seat_id", GoField: "FromSeatID", SQLType: "UUID", Nullable: false},
		{Name: "to_seat_id", Attr: "to_seat_id", GoField: "ToSeatID", SQLType: "UUID", Nullable: false},
		{Name: "kind", Attr: "kind", GoField: "Kind", SQLType: "TEXT", Nullable: false},
		{Name: "allow", Attr: "allow", GoField: "Allow", SQLType: "BOOLEAN", Nullable: false, Default: taskdb.DefaultBool, DefaultValue: "true"},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE seat_links (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tfrom_seat_id UUID NOT NULL REFERENCES seats (id),\n" +
			"\tto_seat_id UUID NOT NULL REFERENCES seats (id),\n" +
			"\tkind TEXT NOT NULL,\n" +
			"\tallow BOOLEAN NOT NULL DEFAULT true,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_seat_links_from_to_kind UNIQUE (from_seat_id, to_seat_id, kind),\n" +
			"\tCONSTRAINT ck_seat_links_kind CHECK (kind IN ('delegates_to', 'spawned_by', 'can_observe', 'collaborates_with', 'escalates_to')),\n" +
			"\tCONSTRAINT ck_seat_links_distinct CHECK (from_seat_id <> to_seat_id)\n" +
			")",
		"CREATE INDEX ix_seat_links_user_id ON seat_links (user_id)",
		"CREATE INDEX ix_seat_links_from_seat_id ON seat_links (from_seat_id)",
		"CREATE INDEX ix_seat_links_to_seat_id ON seat_links (to_seat_id)",
	}},
	{Name: "resolved_seats", Model: "ResolvedSeatORM", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false},
		{Name: "seat_id", Attr: "seat_id", GoField: "SeatID", SQLType: "UUID", Nullable: false},
		{Name: "hash", Attr: "hash", GoField: "Hash", SQLType: "TEXT", Nullable: false},
		{Name: "runtime", Attr: "runtime", GoField: "Runtime", SQLType: "TEXT", Nullable: false},
		{Name: "files", Attr: "files", GoField: "Files", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyList},
		{Name: "policy", Attr: "policy", GoField: "Policy", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyDict},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE resolved_seats (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tseat_id UUID NOT NULL REFERENCES seats (id),\n" +
			"\thash TEXT NOT NULL,\n" +
			"\truntime TEXT NOT NULL,\n" +
			"\tfiles JSONB NOT NULL DEFAULT '[]'::jsonb,\n" +
			"\tpolicy JSONB NOT NULL DEFAULT '{}'::jsonb,\n" +
			"\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT uq_resolved_seats_seat_hash UNIQUE (seat_id, hash)\n" +
			")",
		"CREATE INDEX ix_resolved_seats_user_id ON resolved_seats (user_id)",
		"CREATE INDEX ix_resolved_seats_seat_id ON resolved_seats (seat_id)",
	}},
	{Name: "seat_settings", Model: "SeatSettingsORM", Columns: []taskdb.ColumnDef{
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "follow_latest", Attr: "follow_latest", GoField: "FollowLatest", SQLType: "BOOLEAN", Nullable: false, Default: taskdb.DefaultBool, DefaultValue: "false"},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
	}, DDL: []string{
		"CREATE TABLE seat_settings (\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tfollow_latest BOOLEAN NOT NULL DEFAULT false,\n" +
			"\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tPRIMARY KEY (user_id)\n" +
			")",
	}},
	{Name: "machines", Model: "MachineORM", Columns: []taskdb.ColumnDef{
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "machine_id", Attr: "machine_id", GoField: "MachineID", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "last_seen", Attr: "last_seen", GoField: "LastSeen", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTC},
		{Name: "agents", Attr: "agents", GoField: "Agents", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyList},
	}, DDL: []string{
		"CREATE TABLE machines (\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tmachine_id TEXT NOT NULL,\n" +
			"\tlast_seen TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),\n" +
			"\tagents JSONB NOT NULL DEFAULT '[]'::jsonb,\n" +
			"\tPRIMARY KEY (user_id, machine_id)\n" +
			")",
	}},
	{Name: "seat_status", Model: "SeatStatusORM", Columns: []taskdb.ColumnDef{
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "machine_id", Attr: "machine_id", GoField: "MachineID", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "room", Attr: "room", GoField: "Room", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "seat", Attr: "seat", GoField: "Seat", SQLType: "TEXT", Nullable: false, PrimaryKey: true},
		{Name: "state", Attr: "state", GoField: "State", SQLType: "TEXT", Nullable: false},
		{Name: "runtime", Attr: "runtime", GoField: "Runtime", SQLType: "TEXT", Nullable: false},
		{Name: "running_hash", Attr: "running_hash", GoField: "RunningHash", SQLType: "TEXT", Nullable: false, Default: taskdb.DefaultString, DefaultValue: "\"\""},
		{Name: "detail", Attr: "detail", GoField: "Detail", SQLType: "TEXT", Nullable: false, Default: taskdb.DefaultString, DefaultValue: "\"\""},
		{Name: "redacted", Attr: "redacted", GoField: "Redacted", SQLType: "BOOLEAN", Nullable: false, Default: taskdb.DefaultBool, DefaultValue: "false"},
		{Name: "reported_at", Attr: "reported_at", GoField: "ReportedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: false},
	}, DDL: []string{
		"CREATE TABLE seat_status (\n" +
			"\tuser_id TEXT NOT NULL,\n" +
			"\tmachine_id TEXT NOT NULL,\n" +
			"\troom TEXT NOT NULL,\n" +
			"\tseat TEXT NOT NULL,\n" +
			"\tstate TEXT NOT NULL,\n" +
			"\truntime TEXT NOT NULL,\n" +
			"\trunning_hash TEXT NOT NULL DEFAULT '',\n" +
			"\tdetail TEXT NOT NULL DEFAULT '',\n" +
			"\tredacted BOOLEAN NOT NULL DEFAULT false,\n" +
			"\treported_at TIMESTAMP WITH TIME ZONE NOT NULL,\n" +
			"\tPRIMARY KEY (user_id, machine_id, room, seat)\n" +
			")",
	}},
}

func init() { taskdb.Tables = append(taskdb.Tables, seatManagementDatabaseTables...) }
