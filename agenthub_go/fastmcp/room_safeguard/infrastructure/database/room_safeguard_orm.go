// Package database holds the room_safeguards table definition and its row struct: the table the
// safeguard frame (agent-boundaries.md 7.3) is stored in.
package database

import "time"

// The states a safeguard row reports. The list is agent-boundaries.md 7.6's "Names a failing test may
// assert": the four values the client may send and the CHECK in rig_safeguard_postgresql.sql accepts.
const (
	StateRunning = "running"
	StateStopped = "stopped"
	StateSilent  = "silent"
	StateFailing = "failing"
)

// The safeguards the connector supervises (7.2), one row per safeguard per room per connector. This
// is the CLIENT's wire vocabulary, adopted whole: the client is the side that produces these rows
// (`Verify` and `publishRows`), so the closed set lives on the side that writes it and the server
// refuses a name that is not one of the seven.
//
// THE SCOPE IS PART OF THE NAME'S MEANING, and it decides the row's room:
//
//	room-scoped     (room 1..255): compact, watchdog, messages, roomguard, budget   one row per room
//	machine-scoped (room exactly ""): bridge, agent                        one row per connector
//
// EXACTLY empty for the machine-scoped two, not "anything": room is part of the primary key
// (user_id, connector_id, room, safeguard), so an arbitrary room on a machine row would let one
// machine-level row exist under several spellings and the upsert would stop being idempotent.
//
// `agent` is the machine-level supervisor the client renamed from `rigd` (bc725e6, 2026-10-15); the
// old name is DELETED rather than aliased. SafeguardAgent is the one the SERVER needs by name: it is
// the machine-level row the dead-man alert (7.3) is raised for, so the server names it rather than
// taking it from a frame.
const (
	SafeguardCompact   = "compact"
	SafeguardWatchdog  = "watchdog"
	SafeguardMessages  = "messages"
	SafeguardRoomGuard = "roomguard"
	SafeguardBudget    = "budget"
	SafeguardBridge    = "bridge"
	SafeguardAgent     = "agent"
)

// RoomSafeguardORM is a row of room_safeguards.
//
// It is the SOURCE OF TRUTH for the table's columns, the same rule models.go carries for the
// generated tables: TestRoomSafeguardSchemaAgreesWithTheORMRow owns the comparison against the schema
// file (infrastructure/schema/rig_safeguard_postgresql.sql) and the runtime TableDef
// (rig_safeguard_tables.go), and either source drifting from this struct is that test's failure.
//
// THE KEY is (user_id, connector_id, room, safeguard): one row per safeguard per room per connector,
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
type RoomSafeguardORM struct {
	UserID      string     `db:"user_id"`
	ConnectorID string     `db:"connector_id"`
	Room        string     `db:"room"`
	Safeguard   string     `db:"safeguard"`
	State       string     `db:"state"`
	PID         *int       `db:"pid"`
	Restarts    int64      `db:"restarts"`
	AgeS        int64      `db:"age_s"`
	LastBeatAt  *time.Time `db:"last_beat_at"`
}

// GetUserID satisfies repositories.HasUserID (user isolation).
func (r *RoomSafeguardORM) GetUserID() string { return r.UserID }
