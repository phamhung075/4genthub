package database

import (
	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// rig_safeguards is a NEW table - it has no generated home, because models.go is generated from the
// tables that existed before it - so it registers here the way seat_management's tables do
// (infrastructure/database/seat_tables.go): createAll walks the shared Tables registry and creates a
// table only when it is ABSENT, which is exactly what a new table needs on a database that already
// holds every other one. No ensurer is needed for a table rather than a column.
//
// The DDL below and infrastructure/schema/rig_safeguard_postgresql.sql are the two sources a human
// and createAll respectively execute. TestRigSafeguardSchemaAgreesWithTheORMRow compares them against
// each other AND against the row struct's db tags, so a column in one source and not the other is a
// failure rather than a schema that differs by creation path.
var rigSafeguardTables = []taskdb.TableDef{
	{Name: "rig_safeguards", Model: "RigSafeguardORM", Columns: []taskdb.ColumnDef{
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR(64)", Nullable: false},
		{Name: "connector_id", Attr: "connector_id", GoField: "ConnectorID", SQLType: "VARCHAR(64)", Nullable: false},
		{Name: "rig", Attr: "rig", GoField: "Rig", SQLType: "VARCHAR(255)", Nullable: false},
		{Name: "safeguard", Attr: "safeguard", GoField: "Safeguard", SQLType: "VARCHAR(32)", Nullable: false},
		{Name: "state", Attr: "state", GoField: "State", SQLType: "VARCHAR(20)", Nullable: false},
		{Name: "pid", Attr: "pid", GoField: "PID", SQLType: "INTEGER", Nullable: true},
		{Name: "restarts", Attr: "restarts", GoField: "Restarts", SQLType: "INTEGER", Nullable: false},
		{Name: "age_s", Attr: "age_s", GoField: "AgeS", SQLType: "INTEGER", Nullable: false},
		{Name: "last_beat_at", Attr: "last_beat_at", GoField: "LastBeatAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
	}, DDL: []string{
		"CREATE TABLE rig_safeguards (\n" +
			"\tuser_id VARCHAR(64) NOT NULL,\n" +
			"\tconnector_id VARCHAR(64) NOT NULL,\n" +
			"\trig VARCHAR(255) NOT NULL,\n" +
			"\tsafeguard VARCHAR(32) NOT NULL,\n" +
			"\tstate VARCHAR(20) NOT NULL,\n" +
			"\tpid INTEGER,\n" +
			"\trestarts INTEGER NOT NULL,\n" +
			"\tage_s INTEGER NOT NULL,\n" +
			"\tlast_beat_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tPRIMARY KEY (user_id, connector_id, rig, safeguard),\n" +
			"\tCONSTRAINT ck_rig_safeguards_state CHECK (state IN ('running', 'stopped', 'silent', 'failing')),\n" +
			"\tCONSTRAINT ck_rig_safeguards_safeguard CHECK (safeguard IN ('compact', 'watchdog', 'bridge', 'rigd'))\n" +
			")",
		"CREATE INDEX ix_rig_safeguards_user_connector ON rig_safeguards (user_id, connector_id)",
	}},
}

func init() { taskdb.Tables = append(taskdb.Tables, rigSafeguardTables...) }
