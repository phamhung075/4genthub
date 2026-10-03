// Package repositories defines the persistence ports of the seat_management bounded
// context. Every method takes a context and a userID and every query is tenant-scoped by
// user_id.
package repositories

import (
	"context"
	"errors"
	"fmt"
	"time"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

// Scope values of the overlays.scope CHECK constraint.
const (
	ScopeCompany = "company"
	ScopeRoom    = "room"
	ScopeSeat    = "seat"
)

// Conflicts reported by ModuleRepository; callers match them with errors.Is.
var (
	ErrModuleKindConflict    = errors.New("module kind conflict")
	ErrModuleVersionConflict = errors.New("module version conflict")
	// ErrSeatTypeVersionConflict means the version exists with a different runtime or module refs.
	ErrSeatTypeVersionConflict = errors.New("seat type version conflict")
)

// Module is a tenant-scoped unit of seat content.
type Module struct {
	ID        string
	UserID    string
	Slug      string
	Kind      resolver.ModuleKind
	CreatedAt time.Time
}

// ModuleVersion is one immutable revision of a module, joined with its module.
type ModuleVersion struct {
	ID        string
	UserID    string
	ModuleID  string
	Slug      string
	Kind      resolver.ModuleKind
	Version   string
	Content   string
	Checksum  string
	CreatedAt time.Time
}

// ModuleRepository stores modules and their immutable versions.
type ModuleRepository interface {
	SaveModule(ctx context.Context, userID, slug string, kind resolver.ModuleKind) (*Module, error)
	AddVersion(ctx context.Context, userID, slug, version, content string) (*ModuleVersion, error)
	GetVersion(ctx context.Context, userID, slug, version string) (*ModuleVersion, error)
	LatestVersion(ctx context.Context, userID, slug string) (*ModuleVersion, error)
	// ListLatest returns the newest version of every module, ordered by slug.
	ListLatest(ctx context.Context, userID string) ([]ModuleVersion, error)
}

// SeatType is a tenant-scoped template for a seat.
type SeatType struct {
	ID          string
	UserID      string
	Slug        string
	Name        string
	Description string
	CreatedAt   time.Time
}

// SeatTypeVersion is one immutable revision of a seat type.
type SeatTypeVersion struct {
	ID         string
	UserID     string
	SeatTypeID string
	Slug       string
	Version    string
	// DefaultRuntime is the runtime of a seat that sets none; fixed by the version.
	DefaultRuntime string
	ModuleRefs     []resolver.ModuleRef
	CreatedAt      time.Time
}

// SeatTypeRepository stores seat types and their immutable versions.
type SeatTypeRepository interface {
	Save(ctx context.Context, userID string, seatType SeatType) (*SeatType, error)
	GetByID(ctx context.Context, userID, seatTypeID string) (*SeatType, error)
	List(ctx context.Context, userID string) ([]SeatType, error)
	AddVersion(ctx context.Context, userID, slug, version, defaultRuntime string, moduleRefs []resolver.ModuleRef) (*SeatTypeVersion, error)
	GetVersion(ctx context.Context, userID, slug, version string) (*SeatTypeVersion, error)
	LatestVersion(ctx context.Context, userID, slug string) (*SeatTypeVersion, error)
}

// Room is a tenant-scoped grouping of seats.
type Room struct {
	ID        string
	UserID    string
	Slug      string
	Name      string
	CreatedAt time.Time
	UpdatedAt time.Time
}

// RoomRepository stores rooms.
type RoomRepository interface {
	Save(ctx context.Context, userID string, room Room) (*Room, error)
	GetBySlug(ctx context.Context, userID, slug string) (*Room, error)
	GetByID(ctx context.Context, userID, roomID string) (*Room, error)
	List(ctx context.Context, userID string) ([]Room, error)
	Delete(ctx context.Context, userID, roomID string) error
}

// Seat is a seat inside a room; PinnedVersion nil means follow the seat type's latest
// version.
type Seat struct {
	ID            string
	UserID        string
	RoomID        string
	SeatKey       string
	SeatTypeID    string
	PinnedVersion *string
	Runtime       string
	Model         string
	Status        string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// SeatRepository stores seats.
type SeatRepository interface {
	Create(ctx context.Context, userID string, seat Seat) (*Seat, error)
	GetByID(ctx context.Context, userID, seatID string) (*Seat, error)
	FindByRoomAndKey(ctx context.Context, userID, roomID, seatKey string) (*Seat, error)
	ListByRoom(ctx context.Context, userID, roomID string) ([]Seat, error)
	MarkRemoved(ctx context.Context, userID, seatID string) error
	UpdateOccupant(ctx context.Context, userID, seatID, runtime, model string) error
	Delete(ctx context.Context, userID, seatID string) error
}

// Overlay is the ordered op list applied to one scope target. RoomID and SeatID are set
// according to Scope; an empty value is the NULL target column.
type Overlay struct {
	ID        string
	UserID    string
	Scope     string
	RoomID    string
	SeatID    string
	Ops       []resolver.Op
	CreatedAt time.Time
	UpdatedAt time.Time
}

// ValidateTarget enforces the overlays.scope CHECK: a company overlay has no target, a
// room overlay only a room, a seat overlay only a seat.
func (o Overlay) ValidateTarget() error {
	switch {
	case o.Scope == ScopeCompany && o.RoomID == "" && o.SeatID == "":
	case o.Scope == ScopeRoom && o.RoomID != "" && o.SeatID == "":
	case o.Scope == ScopeSeat && o.SeatID != "" && o.RoomID == "":
	default:
		return fmt.Errorf("overlay scope %q does not match its target (room_id=%q seat_id=%q)", o.Scope, o.RoomID, o.SeatID)
	}
	return nil
}

// OverlayRepository stores one overlay per scope target.
type OverlayRepository interface {
	Upsert(ctx context.Context, userID string, overlay Overlay) (*Overlay, error)
	Find(ctx context.Context, userID, scope, roomID, seatID string) (*Overlay, error)
	DeleteForRoom(ctx context.Context, userID, roomID string) error
	DeleteForSeat(ctx context.Context, userID, seatID string) error
}

// SeatLink is a directed communication edge between two seats.
type SeatLink struct {
	ID         string
	UserID     string
	FromSeatID string
	ToSeatID   string
	Kind       string
	Allow      bool
	CreatedAt  time.Time
}

// SeatLinkRepository stores seat links.
type SeatLinkRepository interface {
	Upsert(ctx context.Context, userID string, link SeatLink) (*SeatLink, error)
	ListFrom(ctx context.Context, userID, seatID string) ([]SeatLink, error)
	// Delete removes the (from, to, kind) link and reports whether it existed.
	Delete(ctx context.Context, userID, fromSeatID, toSeatID, kind string) (bool, error)
	// DeleteBySeat removes every link that starts or ends at the seat.
	DeleteBySeat(ctx context.Context, userID, seatID string) error
}

// ResolvedFile is one rendered file of a resolved seat.
type ResolvedFile struct {
	Path    string
	Content string
}

// ResolvedSeat is one immutable resolved snapshot of a seat.
type ResolvedSeat struct {
	ID        string
	UserID    string
	SeatID    string
	Hash      string
	Runtime   string
	Files     []ResolvedFile
	Policy    map[string]any
	CreatedAt time.Time
}

// ResolvedSeatRepository stores resolved seat snapshots.
type ResolvedSeatRepository interface {
	Save(ctx context.Context, userID string, seat ResolvedSeat) (*ResolvedSeat, error)
	GetLatest(ctx context.Context, userID, seatID string) (*ResolvedSeat, error)
	DeleteBySeat(ctx context.Context, userID, seatID string) error
}

// SeatSettings is one user's company-wide seat defaults. A missing row reads as
// FollowLatest=false.
type SeatSettings struct {
	UserID       string
	FollowLatest bool
}

// SeatSettingsRepository stores one settings row per user.
type SeatSettingsRepository interface {
	Get(ctx context.Context, userID string) (*SeatSettings, error)
	Set(ctx context.Context, userID string, followLatest bool) (*SeatSettings, error)
}

// SeatStatus is the reported state of one seat on a machine.
type SeatStatus struct {
	Room        string
	Seat        string
	State       string
	Runtime     string
	RunningHash string
	Detail      string
	Redacted    bool
	ReportedAt  time.Time
}

// MachineAgent is one herdr agent pane reported by a machine.
type MachineAgent struct {
	Agent  string `json:"agent"`
	Status string `json:"status"`
	PaneID string `json:"pane_id"`
}

// Machine is one bridge machine with its latest seat statuses and agent snapshot.
type Machine struct {
	MachineID string
	LastSeen  time.Time
	Seats     []SeatStatus
	Agents    []MachineAgent
}

// MachineStatusRepository stores the latest status snapshot per machine.
type MachineStatusRepository interface {
	// ReplaceSnapshot upserts the machine with lastSeen and atomically replaces its
	// seat statuses and agent snapshot.
	ReplaceSnapshot(ctx context.Context, userID string, machine Machine) error
	// List returns the user's machines ordered by machine id, seats by room then seat.
	List(ctx context.Context, userID string) ([]Machine, error)
	// DeleteSeatStatusForRoom removes the reported statuses of every seat of the room, on
	// every machine; seat_status stores the room slug, not a foreign key.
	DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error
}
