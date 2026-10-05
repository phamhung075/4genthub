package services

import (
	"context"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
)

type resolutionSeatTypes struct {
	repositories.SeatTypeRepository
	versions []*repositories.SeatTypeVersion
}

func (f *resolutionSeatTypes) GetByID(context.Context, string, string) (*repositories.SeatType, error) {
	return &repositories.SeatType{ID: "st1", Slug: "coder"}, nil
}

func (f *resolutionSeatTypes) GetVersion(_ context.Context, _, _, version string) (*repositories.SeatTypeVersion, error) {
	for _, v := range f.versions {
		if v.Version == version {
			return v, nil
		}
	}
	return nil, nil
}

func (f *resolutionSeatTypes) LatestVersion(context.Context, string, string) (*repositories.SeatTypeVersion, error) {
	return f.versions[len(f.versions)-1], nil
}

type resolutionRooms struct{ repositories.RoomRepository }

func (resolutionRooms) GetBySlug(context.Context, string, string) (*repositories.Room, error) {
	return &repositories.Room{ID: "r1", Slug: "dev"}, nil
}

type resolutionSeats struct {
	repositories.SeatRepository
	seats []repositories.Seat
}

func (f resolutionSeats) FindByRoomAndKey(_ context.Context, _, _, key string) (*repositories.Seat, error) {
	for i := range f.seats {
		if f.seats[i].SeatKey == key {
			return &f.seats[i], nil
		}
	}
	return nil, nil
}

type resolutionOverlays struct{ repositories.OverlayRepository }

func (resolutionOverlays) Find(context.Context, string, string, string, string) (*repositories.Overlay, error) {
	return nil, nil
}

type resolutionLinks struct {
	repositories.SeatLinkRepository
}

func (resolutionLinks) ListFrom(context.Context, string, string) ([]repositories.SeatLink, error) {
	return nil, nil
}

type resolutionSnapshots struct {
	repositories.ResolvedSeatRepository
}

func (resolutionSnapshots) Save(_ context.Context, _ string, seat repositories.ResolvedSeat) (*repositories.ResolvedSeat, error) {
	return &seat, nil
}

type emptyCatalog struct{}

func (emptyCatalog) Get(string, string) (resolver.ModuleVersion, bool) {
	return resolver.ModuleVersion{}, false
}
func (emptyCatalog) Err() error { return nil }

// A pinned seat that sets no runtime takes the default runtime of its pinned version, so
// publishing a newer version with another runtime must not change it; a follow-latest seat
// moves with the newest version.
func TestResolveSeatRuntimeComesFromThePinnedVersion(t *testing.T) {
	pinned := "1.0.0"
	seatTypes := &resolutionSeatTypes{versions: []*repositories.SeatTypeVersion{
		{Slug: "coder", Version: "1.0.0", DefaultRuntime: "claude-code"},
	}}
	svc := &SeatResolutionService{
		SeatTypes: seatTypes, Rooms: resolutionRooms{}, Overlays: resolutionOverlays{}, Links: resolutionLinks{},
		Resolved: resolutionSnapshots{},
		Seats: resolutionSeats{seats: []repositories.Seat{
			{ID: "s-pinned", RoomID: "r1", SeatKey: "pinned", SeatTypeID: "st1", PinnedVersion: &pinned},
			{ID: "s-latest", RoomID: "r1", SeatKey: "latest", SeatTypeID: "st1"},
			{ID: "s-own", RoomID: "r1", SeatKey: "own", SeatTypeID: "st1", PinnedVersion: &pinned, Runtime: "codex"},
		}},
		NewCatalog: func(string) CheckedCatalog { return emptyCatalog{} },
		MCPURL:     "https://api.example.test/mcp",
	}
	runtimeOf := func(seatKey string) string {
		t.Helper()
		resolved, err := svc.ResolveSeat(context.Background(), "u", "dev", seatKey)
		if err != nil {
			t.Fatalf("ResolveSeat(%s): %v", seatKey, err)
		}
		return resolved.Runtime
	}
	for _, seat := range []string{"pinned", "latest"} {
		if got := runtimeOf(seat); got != "claude-code" {
			t.Fatalf("%s before the new version: runtime = %q, want claude-code", seat, got)
		}
	}

	seatTypes.versions = append(seatTypes.versions, &repositories.SeatTypeVersion{Slug: "coder", Version: "1.0.1", DefaultRuntime: "codex"})

	if got := runtimeOf("pinned"); got != "claude-code" {
		t.Errorf("pinned seat after a new version: runtime = %q, want claude-code", got)
	}
	if got := runtimeOf("latest"); got != "codex" {
		t.Errorf("follow-latest seat after a new version: runtime = %q, want codex", got)
	}
	if got := runtimeOf("own"); got != "codex" {
		t.Errorf("seat with its own runtime: runtime = %q, want codex", got)
	}
}

// moduleCatalog is a catalog that gains module versions after the first resolve.
type moduleCatalog map[string]map[string]resolver.ModuleVersion

func (c moduleCatalog) publish(slug, version, content string) {
	if c[slug] == nil {
		c[slug] = map[string]resolver.ModuleVersion{}
	}
	c[slug][version] = resolver.ModuleVersion{Slug: slug, Version: version, Kind: resolver.KindInstruction, Content: content}
}

func (c moduleCatalog) Get(slug, version string) (resolver.ModuleVersion, bool) {
	m, ok := c[slug][version]
	return m, ok
}

func (moduleCatalog) Err() error { return nil }

// G5: references are concrete, so publishing a module version changes no seat by itself. A
// seat moves to it only through a new seat type version that references it, and only when
// the seat follows latest; a pinned seat keeps its resolved content.
func TestResolveSeatModulesMoveOnlyWithANewSeatTypeVersion(t *testing.T) {
	pinned := "1.0.0"
	catalog := moduleCatalog{}
	catalog.publish("rules", "1.0.0", "rules text v1")
	seatTypes := &resolutionSeatTypes{versions: []*repositories.SeatTypeVersion{
		{Slug: "coder", Version: "1.0.0", DefaultRuntime: "claude-code", ModuleRefs: []resolver.ModuleRef{{Slug: "rules", Version: "1.0.0"}}},
	}}
	svc := &SeatResolutionService{
		SeatTypes: seatTypes, Rooms: resolutionRooms{}, Overlays: resolutionOverlays{}, Links: resolutionLinks{},
		Resolved: resolutionSnapshots{},
		Seats: resolutionSeats{seats: []repositories.Seat{
			{ID: "s-pinned", RoomID: "r1", SeatKey: "pinned", SeatTypeID: "st1", PinnedVersion: &pinned},
			{ID: "s-latest", RoomID: "r1", SeatKey: "latest", SeatTypeID: "st1"},
		}},
		NewCatalog: func(string) CheckedCatalog { return catalog },
		MCPURL:     "https://api.example.test/mcp",
	}
	resolve := func(seatKey string) (hash, guidance string) {
		t.Helper()
		resolved, err := svc.ResolveSeat(context.Background(), "u", "dev", seatKey)
		if err != nil {
			t.Fatalf("ResolveSeat(%s): %v", seatKey, err)
		}
		for _, f := range resolved.Files {
			if f.Path == "guidance/role.md" {
				guidance = f.Content
			}
		}
		return resolved.Hash, guidance
	}
	pinnedHash, pinnedGuidance := resolve("pinned")
	latestHash, _ := resolve("latest")
	if !strings.Contains(pinnedGuidance, "rules text v1") {
		t.Fatalf("pinned guidance lacks the v1 module:\n%s", pinnedGuidance)
	}

	catalog.publish("rules", "1.1.0", "rules text v1.1")
	for seat, before := range map[string]string{"pinned": pinnedHash, "latest": latestHash} {
		if hash, _ := resolve(seat); hash != before {
			t.Errorf("%s seat changed when only a module version was published", seat)
		}
	}

	seatTypes.versions = append(seatTypes.versions, &repositories.SeatTypeVersion{
		Slug: "coder", Version: "1.0.1", DefaultRuntime: "claude-code", ModuleRefs: []resolver.ModuleRef{{Slug: "rules", Version: "1.1.0"}},
	})
	if hash, guidance := resolve("pinned"); hash != pinnedHash || !strings.Contains(guidance, "rules text v1") || strings.Contains(guidance, "v1.1") {
		t.Errorf("pinned seat moved to a new seat type version (hash %s, want %s)", hash, pinnedHash)
	}
	hash, guidance := resolve("latest")
	if hash == latestHash || !strings.Contains(guidance, "rules text v1.1") {
		t.Errorf("follow-latest seat did not move to the new seat type version (hash %s, old %s):\n%s", hash, latestHash, guidance)
	}
}
