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
		return nil, fmt.Errorf("%w: room %q", ErrRoomNotFound, roomSlug)
	}
	seat, err := s.Seats.FindByRoomAndKey(ctx, userID, room.ID, seatKey)
	if err != nil {
		return nil, err
	}
	if seat == nil {
		return nil, fmt.Errorf("%w: seat %q", ErrSeatNotFound, seatKey)
	}
	seatType, err := s.SeatTypes.GetByID(ctx, userID, seat.SeatTypeID)
	if err != nil {
		return nil, err
	}
	if seatType == nil {
		return nil, fmt.Errorf("%w: seat %q", ErrSeatTypeNotFound, seatKey)
	}
	version, err := s.seatTypeVersion(ctx, userID, seatType.Slug, seat)
	if err != nil {
		return nil, err
	}
	overlays, err := s.overlayStack(ctx, userID, room.ID, seat.ID, nil)
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
	// Where the seat lives travels with it into the render: the MCP block names the seat so a call
	// can be attributed to it, and the renderer refuses to emit an http block without it.
	resolved.RoomSlug, resolved.SeatKey = roomSlug, seatKey
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

// overlayStack assembles the seat's three overlays in scope order (company, then room, then
// seat), appending the ones that exist. candidate, when not nil, is the overlay a write
// proposes: it replaces any overlay already stored at its own scope while the other scopes
// stay as stored. Resolving a seat and validating a candidate overlay fold this one stack.
func (s *SeatResolutionService) overlayStack(ctx context.Context, userID, roomID, seatID string, candidate *repositories.Overlay) ([]resolver.Overlay, error) {
	targets := []struct{ scope, roomID, seatID string }{
		{repositories.ScopeCompany, "", ""},
		{repositories.ScopeRoom, roomID, ""},
		{repositories.ScopeSeat, "", seatID},
	}
	var out []resolver.Overlay
	for _, t := range targets {
		var overlay *repositories.Overlay
		if candidate != nil && candidate.Scope == t.scope && candidate.RoomID == t.roomID && candidate.SeatID == t.seatID {
			overlay = candidate
		} else {
			found, err := s.Overlays.Find(ctx, userID, t.scope, t.roomID, t.seatID)
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

// ValidateOverlayResolution resolves every seat the candidate overlay would affect as if the
// overlay were already stored: the candidate replaces any overlay stored at its own scope and
// the other scopes stay as they are. It returns the resolver's error, prefixed with the scope,
// as soon as one affected seat would no longer resolve, so the write can be refused before it
// is stored. A scope that reaches no seat cannot break one and always succeeds.
func (s *SeatResolutionService) ValidateOverlayResolution(ctx context.Context, userID string, candidate repositories.Overlay) error {
	seats, err := s.overlayAffectedSeats(ctx, userID, candidate)
	if err != nil {
		return err
	}
	if len(seats) == 0 {
		return nil
	}
	types, err := s.SeatTypes.List(ctx, userID)
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
		version, err := s.seatTypeVersion(ctx, userID, seatType.Slug, &seat)
		if err != nil {
			return err
		}
		overlays, err := s.overlayStack(ctx, userID, seat.RoomID, seat.ID, &candidate)
		if err != nil {
			return err
		}
		runtime := seat.Runtime
		if runtime == "" {
			runtime = version.DefaultRuntime
		}
		catalog := s.NewCatalog(userID)
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
func (s *SeatResolutionService) overlayAffectedSeats(ctx context.Context, userID string, candidate repositories.Overlay) ([]repositories.Seat, error) {
	rooms, err := s.Rooms.List(ctx, userID)
	if err != nil {
		return nil, err
	}
	var seats []repositories.Seat
	for _, room := range rooms {
		if candidate.Scope == repositories.ScopeRoom && room.ID != candidate.RoomID {
			continue
		}
		found, err := s.Seats.ListByRoom(ctx, userID, room.ID)
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
