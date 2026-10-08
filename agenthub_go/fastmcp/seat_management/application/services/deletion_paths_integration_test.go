package services_test

// The two DELETE paths in the shipped surface - a seat link and a room - exercised rather than
// read. They are the only DESTRUCTIVE paths the surface exposes and neither had execution
// coverage before this test: the audit that reported them verified the SQL by READING, and the
// gated database tests were not run for it.
//
// IT SKIPS WHEN SEAT_TEST_DATABASE_URL IS UNSET, in the same form as its neighbour
// seat_resolution_integration_test.go, so the ordinary suite is unaffected.
//
// THE TARGET IS WHATEVER THE VARIABLE NAMES AND THERE IS NO FALLBACK: the harness built from it
// reads only this variable and skips otherwise (see testpg_test.go and orm/integration_test.go),
// so the test cannot be pointed at a real host by accident.
//
// THE LAYER DIVISION, named so a reader knows which layer asserts what: the HTTP status mapping
// (409 for the refusal, 404 for a missing link or room) is asserted by the in-memory mount tests
// TestSeatAdminDeleteRoom and TestSeatAdminDeleteLink. THIS test asserts what those cannot - the
// ROW COUNTS and the store-level scoping - and counts every table that either path could reach,
// in both directions, so a future change that starts touching a neighbouring table fails here.

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// deletionStore is the shipped composition (httpapp's seatAdminRepos) mirrored, so these cases
// run the same wiring the route does rather than a second convention.
type deletionStore struct {
	sessions *database.SessionManager
	rooms    repositories.RoomRepository
	seats    repositories.SeatRepository
	links    repositories.SeatLinkRepository
	overlays repositories.OverlayRepository
	resolved repositories.ResolvedSeatRepository
	machines repositories.MachineStatusRepository
}

func (s *deletionStore) GetRoomBySlug(ctx context.Context, userID, slug string) (*repositories.Room, error) {
	return s.rooms.GetBySlug(ctx, userID, slug)
}

func (s *deletionStore) FindSeat(ctx context.Context, userID, roomID, seatKey string) (*repositories.Seat, error) {
	return s.seats.FindByRoomAndKey(ctx, userID, roomID, seatKey)
}

func (s *deletionStore) ListSeats(ctx context.Context, userID, roomID string) ([]repositories.Seat, error) {
	return s.seats.ListByRoom(ctx, userID, roomID)
}

func (s *deletionStore) DeleteSeatLinksOfSeat(ctx context.Context, userID, seatID string) error {
	return s.links.DeleteBySeat(ctx, userID, seatID)
}

func (s *deletionStore) DeleteSeatOverlay(ctx context.Context, userID, seatID string) error {
	return s.overlays.DeleteForSeat(ctx, userID, seatID)
}

func (s *deletionStore) DeleteResolvedSeats(ctx context.Context, userID, seatID string) error {
	return s.resolved.DeleteBySeat(ctx, userID, seatID)
}

func (s *deletionStore) DeleteSeat(ctx context.Context, userID, seatID string) error {
	return s.seats.Delete(ctx, userID, seatID)
}

func (s *deletionStore) DeleteRoomOverlay(ctx context.Context, userID, roomID string) error {
	return s.overlays.DeleteForRoom(ctx, userID, roomID)
}

func (s *deletionStore) DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error {
	return s.machines.DeleteSeatStatusForRoom(ctx, userID, roomSlug)
}

func (s *deletionStore) DeleteSeatStatusForSeat(ctx context.Context, userID, roomSlug, seatKey string) error {
	return s.machines.DeleteSeatStatusForSeat(ctx, userID, roomSlug, seatKey)
}

func (s *deletionStore) DeleteRoom(ctx context.Context, userID, roomID string) error {
	return s.rooms.Delete(ctx, userID, roomID)
}

func (s *deletionStore) InTransaction(ctx context.Context, fn func(ctx context.Context) error) error {
	return s.sessions.Transaction(ctx, fn)
}

// deletionTables is every table either path could reach, so "nothing else moved" is measured
// rather than asserted.
var deletionTables = []string{"rooms", "seats", "seat_links", "overlays", "resolved_seats", "seat_status", "machines", "seat_types", "seat_type_versions"}

func deletionCounts(t *testing.T, db *sql.DB, userID string) map[string]int {
	t.Helper()
	out := map[string]int{}
	for _, table := range deletionTables {
		var n int
		if err := db.QueryRow(`SELECT count(*) FROM "`+table+`" WHERE user_id = $1`, userID).Scan(&n); err != nil {
			t.Fatalf("count %s: %v", table, err)
		}
		out[table] = n
	}
	return out
}

// deletionDiff names every table whose count moved, which is what makes a neighbouring-table
// regression a failure rather than a surprise.
func deletionDiff(before, after map[string]int) string {
	parts := []string{}
	for _, table := range deletionTables {
		if before[table] != after[table] {
			parts = append(parts, fmt.Sprintf("%s %d->%d", table, before[table], after[table]))
		}
	}
	if len(parts) == 0 {
		return "(no table changed)"
	}
	return strings.Join(parts, ", ")
}

func TestDeletionPathsIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL is required")
	}
	db, err := sql.Open("pgx", url)
	must(t, err)
	defer db.Close()
	ctx := context.Background()
	_, thisFile, _, _ := runtime.Caller(0)
	schema, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "../../infrastructure/schema/seat_management_postgresql.sql"))
	must(t, err)
	// One implicit transaction holds the lock until the schema is applied, so parallel test
	// packages do not race on CREATE EXTENSION.
	if _, err := db.ExecContext(ctx, "SELECT pg_advisory_xact_lock(727274);\n"+string(schema)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	user := fmt.Sprintf("del-%d", time.Now().UnixNano())
	other := fmt.Sprintf("del-other-%d", time.Now().UnixNano())

	rooms, err := seatorm.NewORMRoomRepository(sessions)
	must(t, err)
	seats, err := seatorm.NewORMSeatRepository(sessions)
	must(t, err)
	seatTypes, err := seatorm.NewORMSeatTypeRepository(sessions)
	must(t, err)
	links, err := seatorm.NewORMSeatLinkRepository(sessions)
	must(t, err)
	overlays, err := seatorm.NewORMOverlayRepository(sessions)
	must(t, err)
	resolved, err := seatorm.NewORMResolvedSeatRepository(sessions)
	must(t, err)
	machines, err := seatorm.NewORMMachineStatusRepository(sessions)
	must(t, err)

	store := &deletionStore{sessions: sessions, rooms: rooms, seats: seats, links: links, overlays: overlays, resolved: resolved, machines: machines}
	svc := services.NewRoomDeletionService(store)

	seatType, err := seatTypes.Save(ctx, user, repositories.SeatType{Slug: "del-type", Name: "Deletion type"})
	must(t, err)
	version, err := seatTypes.AddVersion(ctx, user, seatType.Slug, "1.0.0", "claude-code", nil)
	must(t, err)

	room := func(slug string) *repositories.Room {
		r, err := rooms.Save(ctx, user, repositories.Room{Slug: slug, Name: slug})
		must(t, err)
		return r
	}
	seat := func(r *repositories.Room, key string) *repositories.Seat {
		s, err := seats.Create(ctx, user, repositories.Seat{
			RoomID: r.ID, SeatKey: key, SeatTypeID: version.SeatTypeID,
			Runtime: "claude-code", Model: "sonnet", PermissionPolicy: "standard",
		})
		must(t, err)
		return s
	}
	status := func(roomSlug, seatKey string) {
		must(t, machines.ReplaceSnapshot(ctx, user, repositories.Machine{
			MachineID: "del-machine-" + seatKey,
			LastSeen:  time.Now().UTC(),
			Seats: []repositories.SeatStatus{{
				Room: roomSlug, Seat: seatKey, State: "running", Runtime: "claude-code",
				RunningHash: "h", ReportedAt: time.Now().UTC(),
			}},
		}))
	}

	// The fixture carries a SECOND room, "keeper", with its own seat, link, room overlay and
	// reported status: every delete below must leave those rows alone, which is what turns
	// "nothing else was touched" into a measurement.
	probe := room("probe")
	keeper := room("keeper")
	a, b := seat(probe, "a"), seat(probe, "b")
	keeperSeat, keeperSeat2 := seat(keeper, "k"), seat(keeper, "k2")
	link := func(from, to *repositories.Seat, kind string) {
		_, err := links.Upsert(ctx, user, repositories.SeatLink{FromSeatID: from.ID, ToSeatID: to.ID, Kind: kind, Allow: true})
		must(t, err)
	}
	link(a, b, "delegates_to")
	link(a, b, "escalates_to")
	link(b, a, "delegates_to")
	link(keeperSeat, keeperSeat2, "delegates_to")
	overlay := func(scope, roomID, seatID string) {
		_, err := overlays.Upsert(ctx, user, repositories.Overlay{
			Scope: scope, RoomID: roomID, SeatID: seatID,
			Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "del-module", Version: "1.0.0"}},
		})
		must(t, err)
	}
	overlay(repositories.ScopeRoom, probe.ID, "")
	overlay(repositories.ScopeSeat, "", a.ID)
	overlay(repositories.ScopeRoom, keeper.ID, "")
	status("probe", "a")
	status("probe", "ghost") // a reported seat the room does not hold: seat_status is keyed by name
	status("keeper", "k")

	// CLAIM 1: deleting an existing link removes exactly one row and moves no other table.
	before := deletionCounts(t, db, user)
	deleted, err := links.Delete(ctx, user, a.ID, b.ID, "delegates_to")
	must(t, err)
	if !deleted {
		t.Fatalf("CLAIM 1 FAILED: deleting an existing link reported not-deleted")
	}
	after := deletionCounts(t, db, user)
	if d := deletionDiff(before, after); d != "seat_links 4->3" {
		t.Fatalf("CLAIM 1 FAILED: the delete moved %q, want exactly seat_links 4->3", d)
	}

	// CLAIM 2: an absent link is not-found, deletes nothing, and the delete is SCOPED by the
	// triple. The statement is DELETE FROM seat_links WHERE user_id=$1 AND from_seat_id=$2 AND
	// to_seat_id=$3 AND kind=$4, so deleting the neighbouring triple while the real one survives
	// is what excludes a wrong-scoped delete.
	before = deletionCounts(t, db, user)
	gone, err := links.Delete(ctx, user, b.ID, a.ID, "escalates_to") // (b,a) exists as delegates_to only
	must(t, err)
	if gone {
		t.Fatalf("CLAIM 2 FAILED: an absent link reported deleted")
	}
	after = deletionCounts(t, db, user)
	if d := deletionDiff(before, after); d != "(no table changed)" {
		t.Fatalf("CLAIM 2 FAILED: the absent-link delete moved %q", d)
	}
	fromB, err := links.ListFrom(ctx, user, b.ID)
	must(t, err)
	if len(fromB) != 1 || fromB[0].Kind != "delegates_to" {
		t.Fatalf("CLAIM 2 FAILED: the wrong-scoped delete touched the (b,a,delegates_to) row: %+v", fromB)
	}

	// CLAIM 3: a non-empty room is refused WITH THE COUNT and nothing is removed - proved by
	// counts, not by the error.
	before = deletionCounts(t, db, user)
	err = svc.DeleteRoom(ctx, user, "probe")
	if err == nil {
		t.Fatalf("CLAIM 3 FAILED: deleting a non-empty room succeeded")
	}
	if !errors.Is(err, services.ErrRoomNotEmpty) {
		t.Fatalf("CLAIM 3 FAILED: %v, want ErrRoomNotEmpty", err)
	}
	if !strings.Contains(err.Error(), "still holds 2 seat(s)") {
		t.Fatalf("CLAIM 3 FAILED: the refusal does not name the count: %v", err)
	}
	after = deletionCounts(t, db, user)
	if d := deletionDiff(before, after); d != "(no table changed)" {
		t.Fatalf("CLAIM 3 FAILED: the refusal removed %q", d)
	}

	// CLAIM 4: an empty room removes exactly its room overlay, its reported statuses and the
	// room, and nothing else. The seat's own status row went with RemoveSeat above, so what is
	// left to delete is the report for a seat the room does not hold plus the keeper's - and
	// DeleteRoom is scoped by room SLUG, so it must take the probe row and leave the keeper's.
	for _, key := range []string{"a", "b"} {
		must(t, svc.RemoveSeat(ctx, user, "probe", key))
	}
	before = deletionCounts(t, db, user)
	must(t, svc.DeleteRoom(ctx, user, "probe"))
	after = deletionCounts(t, db, user)
	want := "rooms 2->1, overlays 2->1, seat_status 2->1"
	if d := deletionDiff(before, after); d != want {
		t.Fatalf("CLAIM 4 FAILED: DeleteRoom moved %q, want %q", d, want)
	}
	for table, where := range map[string]string{
		"rooms":       `user_id = $1 AND slug = 'keeper'`,
		"seats":       `user_id = $1`,
		"seat_links":  `user_id = $1`,
		"overlays":    `user_id = $1 AND room_id IS NOT NULL`,
		"seat_status": `user_id = $1 AND room = 'keeper'`,
	} {
		var n int
		if err := db.QueryRow(`SELECT count(*) FROM "`+table+`" WHERE `+where, user).Scan(&n); err != nil {
			t.Fatalf("keeper count %s: %v", table, err)
		}
		if n == 0 {
			t.Fatalf("CLAIM 4 FAILED: %s lost the keeper's rows", table)
		}
	}

	// CROSS-OWNER: another user is answered not-found rather than forbidden, at the store level
	// where the user scoping lives, and removes nothing.
	before = deletionCounts(t, db, user)
	if err := svc.DeleteRoom(ctx, other, "keeper"); !errors.Is(err, services.ErrRoomNotFound) {
		t.Fatalf("CROSS-OWNER FAILED: want ErrRoomNotFound, got %v", err)
	}
	absent, err := links.Delete(ctx, other, keeperSeat.ID, keeperSeat2.ID, "delegates_to")
	must(t, err)
	if absent {
		t.Fatalf("CROSS-OWNER FAILED: another user deleted a link it does not own")
	}
	after = deletionCounts(t, db, user)
	if d := deletionDiff(before, after); d != "(no table changed)" {
		t.Fatalf("CROSS-OWNER FAILED: the other user's deletes moved %q", d)
	}

	// CLAIM 5: BOTH DELETES ARE HARD - what they removed can be created AGAIN with the same
	// identity. This is the owner's ruling for a seat (`945648f5`, "removing a seat is a hard
	// delete") and the property RemoveSeat's own doc claims ("so the seat key can be added again
	// from scratch"). NO OTHER CLAIM ABOVE CAN CATCH A TOMBSTONE: a tombstone satisfies every row
	// count and every scoping assertion here, and fails only at the unique constraint, which is
	// what these two creates exercise - the seat key on the room that survived, and the room slug
	// on the room that was deleted.
	must(t, svc.RemoveSeat(ctx, user, "keeper", "k"))
	if _, err := seats.Create(ctx, user, repositories.Seat{
		RoomID: keeper.ID, SeatKey: "k", SeatTypeID: version.SeatTypeID,
		Runtime: "claude-code", Model: "sonnet", PermissionPolicy: "standard",
	}); err != nil {
		t.Fatalf("CLAIM 5 FAILED: a seat key was not reusable after RemoveSeat: %v", err)
	}
	if _, err := rooms.Save(ctx, user, repositories.Room{Slug: "probe", Name: "probe"}); err != nil {
		t.Fatalf("CLAIM 5 FAILED: a room slug was not reusable after DeleteRoom: %v", err)
	}
}
