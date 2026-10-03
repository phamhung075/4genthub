package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
)

type fakeSeatAdminStore struct {
	rooms     []repositories.Room
	seatTypes []repositories.SeatType
	seats     []*repositories.Seat
	updateErr error

	modules  map[string]bool
	versions []*repositories.SeatTypeVersion
	addErr   error
}

func (f *fakeSeatAdminStore) ListRooms(context.Context, string) ([]repositories.Room, error) {
	return f.rooms, nil
}

func (f *fakeSeatAdminStore) GetRoomBySlug(_ context.Context, _, slug string) (*repositories.Room, error) {
	for i := range f.rooms {
		if f.rooms[i].Slug == slug {
			return &f.rooms[i], nil
		}
	}
	return nil, nil
}

func (f *fakeSeatAdminStore) ListSeatTypes(context.Context, string) ([]repositories.SeatType, error) {
	return f.seatTypes, nil
}

func (f *fakeSeatAdminStore) FindSeat(_ context.Context, _, roomID, seatKey string) (*repositories.Seat, error) {
	for _, s := range f.seats {
		if s.RoomID == roomID && s.SeatKey == seatKey {
			copied := *s
			return &copied, nil
		}
	}
	return nil, nil
}

func (f *fakeSeatAdminStore) ListSeats(_ context.Context, _, roomID string) ([]repositories.Seat, error) {
	out := []repositories.Seat{}
	for _, s := range f.seats {
		if s.RoomID == roomID {
			out = append(out, *s)
		}
	}
	return out, nil
}

func (f *fakeSeatAdminStore) UpdateSeatOccupant(_ context.Context, _, seatID, runtime, model string) error {
	if f.updateErr != nil {
		return f.updateErr
	}
	for _, s := range f.seats {
		if s.ID == seatID {
			s.Runtime, s.Model = runtime, model
		}
	}
	return nil
}

func (f *fakeSeatAdminStore) GetModuleVersion(_ context.Context, _, slug, version string) (*repositories.ModuleVersion, error) {
	if !f.modules[slug+"@"+version] {
		return nil, nil
	}
	return &repositories.ModuleVersion{Slug: slug, Version: version}, nil
}

func (f *fakeSeatAdminStore) LatestSeatTypeVersion(context.Context, string, string) (*repositories.SeatTypeVersion, error) {
	if len(f.versions) == 0 {
		return nil, nil
	}
	return f.versions[len(f.versions)-1], nil
}

func (f *fakeSeatAdminStore) AddSeatTypeVersion(_ context.Context, _, slug, version, defaultRuntime string, refs []resolver.ModuleRef) (*repositories.SeatTypeVersion, error) {
	if f.addErr != nil {
		return nil, f.addErr
	}
	created := &repositories.SeatTypeVersion{Slug: slug, Version: version, DefaultRuntime: defaultRuntime, ModuleRefs: refs}
	f.versions = append(f.versions, created)
	return created, nil
}

func newSeatAdminFixture() (*SeatAdminService, *fakeSeatAdminStore) {
	pinned := "1.0.0"
	store := &fakeSeatAdminStore{
		rooms:     []repositories.Room{{ID: "r1", Slug: "dev"}, {ID: "r2", Slug: "ops"}},
		seatTypes: []repositories.SeatType{{ID: "st1", Slug: "coder"}},
		seats: []*repositories.Seat{
			{ID: "s1", RoomID: "r1", SeatKey: "alice", SeatTypeID: "st1", PinnedVersion: &pinned, Runtime: "claude-code", Model: "sonnet", Status: "active"},
			{ID: "s2", RoomID: "r1", SeatKey: "bob", SeatTypeID: "st1", Runtime: "codex", Status: "removed"},
			{ID: "s3", RoomID: "r2", SeatKey: "carol", SeatTypeID: "st1", Runtime: "codex", Status: "active"},
		},
	}
	return NewSeatAdminService(store), store
}

func TestSeatAdminServiceListSeats(t *testing.T) {
	service, _ := newSeatAdminFixture()
	all, err := service.ListSeats(context.Background(), "u", "")
	if err != nil || len(all) != 2 || all[0].Seat.SeatKey != "alice" || all[0].RoomSlug != "dev" || all[0].SeatTypeSlug != "coder" || all[1].RoomSlug != "ops" {
		t.Fatalf("ListSeats(all) = %+v, %v", all, err)
	}
	one, err := service.ListSeats(context.Background(), "u", "ops")
	if err != nil || len(one) != 1 || one[0].Seat.SeatKey != "carol" {
		t.Fatalf("ListSeats(ops) = %+v, %v", one, err)
	}
	if _, err := service.ListSeats(context.Background(), "u", "ghost"); !errors.Is(err, ErrRoomNotFound) {
		t.Fatalf("ListSeats(ghost) error = %v, want ErrRoomNotFound", err)
	}
}

func TestSeatAdminServiceGetSeat(t *testing.T) {
	service, _ := newSeatAdminFixture()
	view, err := service.GetSeat(context.Background(), "u", "dev", "alice")
	if err != nil || view.Seat.ID != "s1" || view.SeatTypeSlug != "coder" {
		t.Fatalf("GetSeat = %+v, %v", view, err)
	}
	cases := map[string]error{"ghost": ErrSeatNotFound, "bob": ErrSeatRemoved}
	for key, want := range cases {
		if _, err := service.GetSeat(context.Background(), "u", "dev", key); !errors.Is(err, want) {
			t.Errorf("GetSeat(%s) error = %v, want %v", key, err, want)
		}
	}
	if _, err := service.GetSeat(context.Background(), "u", "ghost", "alice"); !errors.Is(err, ErrRoomNotFound) {
		t.Errorf("GetSeat(ghost room) error = %v, want ErrRoomNotFound", err)
	}
}

func TestSeatAdminServiceSetOccupantKeepsPin(t *testing.T) {
	service, store := newSeatAdminFixture()
	view, err := service.SetOccupant(context.Background(), "u", "dev", "alice", "codex", "gpt-5.1")
	if err != nil || view.Seat.Runtime != "codex" || view.Seat.Model != "gpt-5.1" {
		t.Fatalf("SetOccupant = %+v, %v", view, err)
	}
	stored := store.seats[0]
	if stored.Runtime != "codex" || stored.Model != "gpt-5.1" || stored.PinnedVersion == nil || *stored.PinnedVersion != "1.0.0" {
		t.Fatalf("stored seat = %+v", stored)
	}
}

func TestSeatAdminServiceSetOccupantErrors(t *testing.T) {
	service, store := newSeatAdminFixture()
	ctx := context.Background()
	invalid := [][2]string{{"gemini", ""}, {"", ""}, {"codex", "-bad"}, {"codex", "a b"}}
	for _, c := range invalid {
		if _, err := service.SetOccupant(ctx, "u", "dev", "alice", c[0], c[1]); !errors.Is(err, ErrInvalidOccupant) {
			t.Errorf("SetOccupant(%q, %q) error = %v, want ErrInvalidOccupant", c[0], c[1], err)
		}
	}
	if _, err := service.SetOccupant(ctx, "u", "ghost", "alice", "codex", ""); !errors.Is(err, ErrRoomNotFound) {
		t.Errorf("unknown room error = %v", err)
	}
	if _, err := service.SetOccupant(ctx, "u", "dev", "ghost", "codex", ""); !errors.Is(err, ErrSeatNotFound) {
		t.Errorf("unknown seat error = %v", err)
	}
	if _, err := service.SetOccupant(ctx, "u", "dev", "bob", "claude-code", ""); !errors.Is(err, ErrSeatRemoved) {
		t.Errorf("removed seat error = %v", err)
	}
	if store.seats[0].Runtime != "claude-code" || store.seats[1].Runtime != "codex" {
		t.Errorf("a rejected call changed a seat: %+v %+v", store.seats[0], store.seats[1])
	}
	boom := errors.New("db down")
	store.updateErr = boom
	if _, err := service.SetOccupant(ctx, "u", "dev", "alice", "codex", ""); !errors.Is(err, boom) {
		t.Errorf("store error = %v, want %v", err, boom)
	}
}

func TestCreateSeatTypeVersion(t *testing.T) {
	svc, store := newSeatAdminFixture()
	store.modules = map[string]bool{"instr@1.0.0": true, "skill-x@2.1.0": true}
	ctx := context.Background()

	first, err := svc.CreateSeatTypeVersion(ctx, "u", "coder", []string{"instr@1.0.0"}, "claude-code")
	if err != nil || first.Version != "1.0.0" || first.DefaultRuntime != "claude-code" {
		t.Fatalf("first = %+v, %v, want 1.0.0 claude-code", first, err)
	}
	second, err := svc.CreateSeatTypeVersion(ctx, "u", "coder", []string{"instr@1.0.0", "skill-x@2.1.0"}, "codex")
	if err != nil || second.Version != "1.0.1" || second.DefaultRuntime != "codex" || len(second.ModuleRefs) != 2 {
		t.Fatalf("second = %+v, %v, want 1.0.1 codex with 2 refs", second, err)
	}
	if first.DefaultRuntime != "claude-code" {
		t.Errorf("the new version changed the earlier one: %+v", first)
	}
}

func TestCreateSeatTypeVersionErrors(t *testing.T) {
	svc, store := newSeatAdminFixture()
	store.modules = map[string]bool{"instr@1.0.0": true}
	boom := errors.New("connection reset")
	cases := []struct {
		name    string
		slug    string
		refs    []string
		runtime string
		addErr  error
		want    error
	}{
		{"unknown seat type", "ghost", nil, "codex", nil, ErrSeatTypeNotFound},
		{"bad runtime", "coder", nil, "gemini", nil, ErrInvalidSeatTypeVersion},
		{"malformed ref", "coder", []string{"instr"}, "codex", nil, ErrInvalidSeatTypeVersion},
		{"duplicate module", "coder", []string{"instr@1.0.0", "instr@1.0.0"}, "codex", nil, ErrInvalidSeatTypeVersion},
		{"unknown module", "coder", []string{"ghost@1.0.0"}, "codex", nil, ErrInvalidSeatTypeVersion},
		{"concurrent writer", "coder", nil, "codex", repositories.ErrSeatTypeVersionConflict, repositories.ErrSeatTypeVersionConflict},
		{"database failure", "coder", nil, "codex", boom, boom},
	}
	for _, c := range cases {
		store.addErr = c.addErr
		_, err := svc.CreateSeatTypeVersion(context.Background(), "u", c.slug, c.refs, c.runtime)
		if !errors.Is(err, c.want) {
			t.Errorf("%s: err = %v, want %v", c.name, err, c.want)
		}
		if c.want == boom && (errors.Is(err, ErrInvalidSeatTypeVersion) || errors.Is(err, repositories.ErrSeatTypeVersionConflict)) {
			t.Errorf("%s: an internal error was typed as a client error: %v", c.name, err)
		}
	}
	if len(store.versions) != 0 {
		t.Errorf("rejected requests created versions: %+v", store.versions)
	}
}
