package services

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

type fakeSeatAdminStore struct {
	rooms     []repositories.Room
	seatTypes []repositories.SeatType
	seats     []*repositories.Seat
	updateErr error
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
