// Package database holds the rig_safeguards table definition and its row struct: the table the
// safeguard frame (rigd-boundaries.md 7.3) is stored in.
package database

import "time"

// The states a safeguard row reports. The list is rigd-boundaries.md 7.6's "Names a failing test may
// assert": the four values the client may send and the CHECK in rig_safeguard_postgresql.sql accepts.
const (
	StateRunning = "running"
	StateStopped = "stopped"
	StateSilent  = "silent"
	StateFailing = "failing"
)

// The safeguards rigd supervises, one row per rig (7.2). SafeguardRigd is the machine-level row the
// server needs by name: it is the one the dead-man alert (7.3) is raised for, so the server names it
// rather than taking it from a frame.
const (
	SafeguardCompact  = "compact"
	SafeguardWatchdog = "watchdog"
	SafeguardBridge   = "bridge"
	SafeguardRigd     = "rigd"
)

// RigSafeguardORM is a row of rig_safeguards.
//
// It is the SOURCE OF TRUTH for the table's columns, the same rule models.go carries for the
// generated tables: TestRigSafeguardSchemaAgreesWithTheORMRow owns the comparison against the schema
// file (infrastructure/schema/rig_safeguard_postgresql.sql) and the runtime TableDef
// (rig_safeguard_tables.go), and either source drifting from this struct is that test's failure.
//
// THE KEY is (user_id, connector_id, rig, safeguard): one row per safeguard per rig per connector,
// with no id column, because the frame is an UPSERT and the latest state wins (7.3). There is no
// foreign key: connector_id is a connector's own name, not a row of another table, and the project
// keeps every cascade in the application layer.
//
// PID is a pointer because a safeguard that is not running has no process, which is a state rather
// than a missing value - the same reason delivered_at is nullable on seat_messages. LastBeatAt is
// the frame's `at`: WHEN THE CHILD LAST BEAT, which is not when the server received the row. A frame
// that carried no `at` stores NULL rather than the server's clock, so the column never reports a
// beat the child did not make.
//
// 7.2's `started_at` is deliberately NOT here: the safeguard frame (7.3) carries no started_at, so
// the server has no value for it, and a column no code can ever fill is a lie rather than a gap.
type RigSafeguardORM struct {
	UserID      string     `db:"user_id"`
	ConnectorID string     `db:"connector_id"`
	Rig         string     `db:"rig"`
	Safeguard   string     `db:"safeguard"`
	State       string     `db:"state"`
	PID         *int       `db:"pid"`
	Restarts    int64      `db:"restarts"`
	AgeS        int64      `db:"age_s"`
	LastBeatAt  *time.Time `db:"last_beat_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *RigSafeguardORM) GetUserID() string { return r.UserID }
