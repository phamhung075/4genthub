// Row structs for the seat_management schema
// (fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql).
//
// Each struct mirrors one table: one Go field per column, tagged with the `db` column
// name, in DDL order. json.RawMessage carries JSONB, string carries UUID, *string carries a
// nullable text/UUID column, and time.Time carries a TIMESTAMP WITH TIME ZONE column
// (the same conventions as task_management/infrastructure/database/models.go).
//
// The tables are tenant-scoped by user_id (TEXT) and use no foreign key CASCADE.
package database

import (
	"encoding/json"
	"time"
)

// ModuleORM is a row of modules.
type ModuleORM struct {
	ID        string    `db:"id"`
	UserID    string    `db:"user_id"`
	Slug      string    `db:"slug"`
	Kind      string    `db:"kind"`
	CreatedAt time.Time `db:"created_at"`
}

// ModuleVersionORM is a row of module_versions. Immutable: append-only, never updated.
type ModuleVersionORM struct {
	ID        string    `db:"id"`
	UserID    string    `db:"user_id"`
	ModuleID  string    `db:"module_id"`
	Version   string    `db:"version"`
	Content   string    `db:"content"`
	Checksum  string    `db:"checksum"`
	CreatedAt time.Time `db:"created_at"`
}

// SeatTypeORM is a row of seat_types.
type SeatTypeORM struct {
	ID          string    `db:"id"`
	UserID      string    `db:"user_id"`
	Slug        string    `db:"slug"`
	Name        string    `db:"name"`
	Description string    `db:"description"`
	CreatedAt   time.Time `db:"created_at"`
}

// SeatTypeVersionORM is a row of seat_type_versions. Immutable: append-only, never updated.
type SeatTypeVersionORM struct {
	ID             string          `db:"id"`
	UserID         string          `db:"user_id"`
	SeatTypeID     string          `db:"seat_type_id"`
	Version        string          `db:"version"`
	DefaultRuntime string          `db:"default_runtime"`
	ModuleRefs     json.RawMessage `db:"module_refs"`
	CreatedAt      time.Time       `db:"created_at"`
}

// RoomORM is a row of rooms.
type RoomORM struct {
	ID        string    `db:"id"`
	UserID    string    `db:"user_id"`
	Slug      string    `db:"slug"`
	Name      string    `db:"name"`
	CreatedAt time.Time `db:"created_at"`
	UpdatedAt time.Time `db:"updated_at"`
}

// SeatORM is a row of seats. PinnedVersion nil means follow the seat type's latest version.
type SeatORM struct {
	ID            string    `db:"id"`
	UserID        string    `db:"user_id"`
	RoomID        string    `db:"room_id"`
	SeatKey       string    `db:"seat_key"`
	SeatTypeID    string    `db:"seat_type_id"`
	PinnedVersion *string   `db:"pinned_version"`
	Runtime       string    `db:"runtime"`
	Model         string    `db:"model"`
	Status        string    `db:"status"`
	CreatedAt     time.Time `db:"created_at"`
	UpdatedAt     time.Time `db:"updated_at"`
}

// OverlayORM is a row of overlays. RoomID/SeatID are set according to Scope.
type OverlayORM struct {
	ID        string          `db:"id"`
	UserID    string          `db:"user_id"`
	Scope     string          `db:"scope"`
	RoomID    *string         `db:"room_id"`
	SeatID    *string         `db:"seat_id"`
	Ops       json.RawMessage `db:"ops"`
	CreatedAt time.Time       `db:"created_at"`
	UpdatedAt time.Time       `db:"updated_at"`
}

// SeatLinkORM is a row of seat_links.
type SeatLinkORM struct {
	ID         string    `db:"id"`
	UserID     string    `db:"user_id"`
	FromSeatID string    `db:"from_seat_id"`
	ToSeatID   string    `db:"to_seat_id"`
	Kind       string    `db:"kind"`
	Allow      bool      `db:"allow"`
	CreatedAt  time.Time `db:"created_at"`
}

// ResolvedSeatORM is a row of resolved_seats. Immutable: append-only, never updated.
type ResolvedSeatORM struct {
	ID        string          `db:"id"`
	UserID    string          `db:"user_id"`
	SeatID    string          `db:"seat_id"`
	Hash      string          `db:"hash"`
	Runtime   string          `db:"runtime"`
	Files     json.RawMessage `db:"files"`
	Policy    json.RawMessage `db:"policy"`
	CreatedAt time.Time       `db:"created_at"`
}

// SeatSettingsORM is a row of seat_settings. user_id is the primary key.
type SeatSettingsORM struct {
	UserID       string    `db:"user_id"`
	FollowLatest bool      `db:"follow_latest"`
	UpdatedAt    time.Time `db:"updated_at"`
}

// MachineORM is a row of machines. (user_id, machine_id) is the primary key.
type MachineORM struct {
	UserID    string          `db:"user_id"`
	MachineID string          `db:"machine_id"`
	LastSeen  time.Time       `db:"last_seen"`
	Agents    json.RawMessage `db:"agents"`
}

// SeatStatusORM is a row of seat_status. (user_id, machine_id, room, seat) is the primary key.
type SeatStatusORM struct {
	UserID      string    `db:"user_id"`
	MachineID   string    `db:"machine_id"`
	Room        string    `db:"room"`
	Seat        string    `db:"seat"`
	State       string    `db:"state"`
	Runtime     string    `db:"runtime"`
	RunningHash string    `db:"running_hash"`
	Detail      string    `db:"detail"`
	Redacted    bool      `db:"redacted"`
	ReportedAt  time.Time `db:"reported_at"`
}
