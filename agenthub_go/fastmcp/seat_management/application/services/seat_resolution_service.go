// Package services holds the seat_management use cases.
package services

import (
	"context"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"

	"agenthub/fastmcp/seat_management/domain/commpolicy"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seatrenderer"
)

// CheckedCatalog is a resolver.Catalog whose lookups can fail; Err reports the first
// database error, which the bool-only Catalog methods cannot carry.
type CheckedCatalog interface {
	resolver.Catalog
	Err() error
}

// SeatResolutionService resolves a seat (seat type version, company, room and seat
// overlays), renders it for its runtime and stores the immutable snapshot.
type SeatResolutionService struct {
	SeatTypes  repositories.SeatTypeRepository
	Rooms      repositories.RoomRepository
	Seats      repositories.SeatRepository
	Overlays   repositories.OverlayRepository
	Links      repositories.SeatLinkRepository
	Resolved   repositories.ResolvedSeatRepository
	NewCatalog func(userID string) CheckedCatalog
	MCPURL     string
}

// ResolveSeat returns the stored snapshot for the seat's current definition. The same
// definition always yields the same snapshot hash, so repeated calls store one row.
func (s *SeatResolutionService) ResolveSeat(ctx context.Context, userID, roomSlug, seatKey string) (*repositories.ResolvedSeat, error) {
	room, err := s.Rooms.GetBySlug(ctx, userID, roomSlug)
	if err != nil {
		return nil, err
	}
	if room == nil {
		return nil, fmt.Errorf("room %q not found", roomSlug)
	}
	seat, err := s.Seats.FindByRoomAndKey(ctx, userID, room.ID, seatKey)
	if err != nil {
		return nil, err
	}
	if seat == nil {
		return nil, fmt.Errorf("seat %q not found in room %q", seatKey, roomSlug)
	}
	seatType, err := s.SeatTypes.GetByID(ctx, userID, seat.SeatTypeID)
	if err != nil {
		return nil, err
	}
	if seatType == nil {
		return nil, fmt.Errorf("seat type of seat %q not found", seatKey)
	}
	version, err := s.seatTypeVersion(ctx, userID, seatType.Slug, seat)
	if err != nil {
		return nil, err
	}
	overlays, err := s.overlays(ctx, userID, room.ID, seat.ID)
	if err != nil {
		return nil, err
	}

	runtime := seat.Runtime
	if runtime == "" {
		runtime = version.DefaultRuntime
	}
	catalog := s.NewCatalog(userID)
	resolved, err := resolver.Resolve(catalog, resolver.SeatTypeVersion{
		Slug: seatType.Slug, Version: version.Version, Runtime: runtime, Modules: version.ModuleRefs,
	}, overlays)
	if catalogErr := catalog.Err(); catalogErr != nil {
		return nil, catalogErr
	}
	if err != nil {
		return nil, err
	}
	spec, err := seatrenderer.RenderSeat(resolved, s.MCPURL)
	if err != nil {
		return nil, err
	}
	policy, policyHash, err := s.policy(ctx, userID, seat)
	if err != nil {
		return nil, err
	}

	files := make([]repositories.ResolvedFile, len(spec.Files))
	for i, f := range spec.Files {
		files[i] = repositories.ResolvedFile{Path: f.Path, Content: f.Content}
	}
	return s.Resolved.Save(ctx, userID, repositories.ResolvedSeat{
		SeatID:  seat.ID,
		Hash:    snapshotHash(resolved.Hash, policyHash, spec.Files),
		Runtime: runtime,
		Files:   files,
		Policy:  policy,
	})
}

// seatTypeVersion is the seat's pinned version, or the latest when the seat follows latest.
func (s *SeatResolutionService) seatTypeVersion(ctx context.Context, userID, slug string, seat *repositories.Seat) (*repositories.SeatTypeVersion, error) {
	var version *repositories.SeatTypeVersion
	var err error
	if seat.PinnedVersion != nil {
		version, err = s.SeatTypes.GetVersion(ctx, userID, slug, *seat.PinnedVersion)
	} else {
		version, err = s.SeatTypes.LatestVersion(ctx, userID, slug)
	}
	if err != nil {
		return nil, err
	}
	if version == nil {
		return nil, fmt.Errorf("seat type %q has no usable version for seat %q", slug, seat.SeatKey)
	}
	return version, nil
}

func (s *SeatResolutionService) overlays(ctx context.Context, userID, roomID, seatID string) ([]resolver.Overlay, error) {
	targets := []struct{ scope, roomID, seatID string }{
		{repositories.ScopeCompany, "", ""},
		{repositories.ScopeRoom, roomID, ""},
		{repositories.ScopeSeat, "", seatID},
	}
	var out []resolver.Overlay
	for _, t := range targets {
		overlay, err := s.Overlays.Find(ctx, userID, t.scope, t.roomID, t.seatID)
		if err != nil {
			return nil, err
		}
		if overlay != nil {
			out = append(out, resolver.Overlay{Scope: t.scope, Ops: overlay.Ops})
		}
	}
	return out, nil
}

// OverlayResolutionStore is the read surface ValidateOverlayResolution needs: the seats a
// candidate overlay would reach, their seat types, the overlays already stored and the module
// versions the resolver folds.
type OverlayResolutionStore interface {
	ListRooms(ctx context.Context, userID string) ([]repositories.Room, error)
	ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error)
	ListSeatTypes(ctx context.Context, userID string) ([]repositories.SeatType, error)
	LatestSeatTypeVersion(ctx context.Context, userID, slug string) (*repositories.SeatTypeVersion, error)
	GetSeatTypeVersion(ctx context.Context, userID, slug, version string) (*repositories.SeatTypeVersion, error)
	FindOverlay(ctx context.Context, userID, scope, roomID, seatID string) (*repositories.Overlay, error)
	GetModuleVersion(ctx context.Context, userID, slug, version string) (*repositories.ModuleVersion, error)
}

// ValidateOverlayResolution resolves every seat the candidate overlay would affect as if the
// overlay were already stored: the candidate replaces any overlay stored at its own scope and
// the other scopes stay as they are. It returns the resolver's error, prefixed with the scope,
// as soon as one affected seat would no longer resolve, so the write can be refused before it
// is stored. A scope that reaches no seat cannot break one and always succeeds.
func ValidateOverlayResolution(ctx context.Context, store OverlayResolutionStore, userID string, candidate repositories.Overlay) error {
	seats, err := overlayAffectedSeats(ctx, store, userID, candidate)
	if err != nil {
		return err
	}
	if len(seats) == 0 {
		return nil
	}
	types, err := store.ListSeatTypes(ctx, userID)
	if err != nil {
		return err
	}
	byID := make(map[string]repositories.SeatType, len(types))
	for _, seatType := range types {
		byID[seatType.ID] = seatType
	}
	for i := range seats {
		seat := seats[i]
		seatType, ok := byID[seat.SeatTypeID]
		if !ok {
			return fmt.Errorf("overlay %s: seat %q: seat type %q not found", candidate.Scope, seat.SeatKey, seat.SeatTypeID)
		}
		version, err := overlaySeatTypeVersion(ctx, store, userID, seatType.Slug, seat)
		if err != nil {
			return err
		}
		overlays, err := overlayStack(ctx, store, userID, seat, candidate)
		if err != nil {
			return err
		}
		runtime := seat.Runtime
		if runtime == "" {
			runtime = version.DefaultRuntime
		}
		catalog := &overlayCatalog{ctx: ctx, store: store, userID: userID}
		if _, err := resolver.Resolve(catalog, resolver.SeatTypeVersion{
			Slug: seatType.Slug, Version: version.Version, Runtime: runtime, Modules: version.ModuleRefs,
		}, overlays); err != nil {
			return fmt.Errorf("overlay %s: %w", candidate.Scope, err)
		}
		if err := catalog.Err(); err != nil {
			return err
		}
	}
	return nil
}

// overlayAffectedSeats lists the seats a candidate overlay would reach: every seat for a
// company overlay, the room's seats for a room overlay and the one seat for a seat overlay.
func overlayAffectedSeats(ctx context.Context, store OverlayResolutionStore, userID string, candidate repositories.Overlay) ([]repositories.Seat, error) {
	rooms, err := store.ListRooms(ctx, userID)
	if err != nil {
		return nil, err
	}
	var seats []repositories.Seat
	for _, room := range rooms {
		if candidate.Scope == repositories.ScopeRoom && room.ID != candidate.RoomID {
			continue
		}
		found, err := store.ListSeats(ctx, userID, room.ID)
		if err != nil {
			return nil, err
		}
		for _, seat := range found {
			if candidate.Scope == repositories.ScopeSeat && seat.ID != candidate.SeatID {
				continue
			}
			seats = append(seats, seat)
		}
	}
	return seats, nil
}

// overlaySeatTypeVersion mirrors the seat's pinned version, or the latest when the seat follows latest.
func overlaySeatTypeVersion(ctx context.Context, store OverlayResolutionStore, userID, slug string, seat repositories.Seat) (*repositories.SeatTypeVersion, error) {
	var (
		version *repositories.SeatTypeVersion
		err     error
	)
	if seat.PinnedVersion != nil {
		version, err = store.GetSeatTypeVersion(ctx, userID, slug, *seat.PinnedVersion)
	} else {
		version, err = store.LatestSeatTypeVersion(ctx, userID, slug)
	}
	if err != nil {
		return nil, err
	}
	if version == nil {
		return nil, fmt.Errorf("seat type %q has no usable version for seat %q", slug, seat.SeatKey)
	}
	return version, nil
}

// overlayStack assembles the seat's three overlays with the candidate replacing the stored
// overlay at its own scope; the other scopes stay as stored.
func overlayStack(ctx context.Context, store OverlayResolutionStore, userID string, seat repositories.Seat, candidate repositories.Overlay) ([]resolver.Overlay, error) {
	targets := []struct{ scope, roomID, seatID string }{
		{repositories.ScopeCompany, "", ""},
		{repositories.ScopeRoom, seat.RoomID, ""},
		{repositories.ScopeSeat, "", seat.ID},
	}
	var out []resolver.Overlay
	for _, t := range targets {
		var overlay *repositories.Overlay
		if candidate.Scope == t.scope && candidate.RoomID == t.roomID && candidate.SeatID == t.seatID {
			overlay = &candidate
		} else {
			found, err := store.FindOverlay(ctx, userID, t.scope, t.roomID, t.seatID)
			if err != nil {
				return nil, err
			}
			overlay = found
		}
		if overlay != nil {
			out = append(out, resolver.Overlay{Scope: t.scope, Ops: overlay.Ops})
		}
	}
	return out, nil
}

// overlayCatalog adapts GetModuleVersion to the resolver's catalog and carries the first
// error, which the bool-only Catalog interface cannot.
type overlayCatalog struct {
	ctx    context.Context
	store  OverlayResolutionStore
	userID string
	err    error
}

func (c *overlayCatalog) Get(slug, version string) (resolver.ModuleVersion, bool) {
	if c.err != nil {
		return resolver.ModuleVersion{}, false
	}
	module, err := c.store.GetModuleVersion(c.ctx, c.userID, slug, version)
	if err != nil {
		c.err = err
		return resolver.ModuleVersion{}, false
	}
	if module == nil {
		return resolver.ModuleVersion{}, false
	}
	return resolver.ModuleVersion{Slug: module.Slug, Version: module.Version, Kind: module.Kind, Content: module.Content}, true
}

func (c *overlayCatalog) Err() error { return c.err }

// policy builds the sending seat's communication policy snapshot from its outgoing links.
func (s *SeatResolutionService) policy(ctx context.Context, userID string, seat *repositories.Seat) (map[string]any, string, error) {
	links, err := s.Links.ListFrom(ctx, userID, seat.ID)
	if err != nil {
		return nil, "", err
	}
	policy := commpolicy.Policy{Seat: seat.SeatKey, Links: []commpolicy.Link{}}
	for _, link := range links {
		target, err := s.Seats.GetByID(ctx, userID, link.ToSeatID)
		if err != nil {
			return nil, "", err
		}
		if target == nil {
			continue
		}
		policy.Links = append(policy.Links, commpolicy.Link{
			From: seat.SeatKey, To: target.SeatKey, Kind: commpolicy.LinkKind(link.Kind), Allow: link.Allow,
		})
	}
	encoded, err := json.Marshal(policy)
	if err != nil {
		return nil, "", err
	}
	var asMap map[string]any
	if err := json.Unmarshal(encoded, &asMap); err != nil {
		return nil, "", err
	}
	return asMap, commpolicy.PolicyHash(policy), nil
}

// snapshotHash identifies a resolved seat: the module hash alone would not change when
// only the policy or the rendered files change, and a stale snapshot would be reused.
func snapshotHash(moduleHash, policyHash string, files []seatrenderer.OpenRigSpecFile) string {
	h := sha256.New()
	write := func(s string) {
		var n [8]byte
		binary.BigEndian.PutUint64(n[:], uint64(len(s)))
		h.Write(n[:])
		h.Write([]byte(s))
	}
	write(moduleHash)
	write(policyHash)
	for _, f := range files {
		write(f.Path)
		write(f.Content)
	}
	return hex.EncodeToString(h.Sum(nil))
}
