package orm

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"testing"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestSeatRepositoriesIntegration exercises the repositories against a real PostgreSQL when
// SEAT_TEST_DATABASE_URL is set; it applies the seat schema SQL first.
func TestSeatRepositoriesIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if err := db.PingContext(ctx); err != nil {
		t.Fatalf("ping: %v", err)
	}
	if _, err := db.ExecContext(ctx, seatIntegrationSchema(t)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	userID := fmt.Sprintf("seat-it-%d", time.Now().UnixNano())

	modules, err := NewORMModuleRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	seatTypeRepo, err := NewORMSeatTypeRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	rooms, err := NewORMRoomRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	seats, err := NewORMSeatRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	overlays, err := NewORMOverlayRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	resolved, err := NewORMResolvedSeatRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	settings, err := NewORMSeatSettingsRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}

	machines, err := NewORMMachineStatusRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}

	// create
	if _, err := modules.SaveModule(ctx, userID, "instr", resolver.KindInstruction); err != nil {
		t.Fatalf("SaveModule: %v", err)
	}
	mv, err := modules.AddVersion(ctx, userID, "instr", "1.0.0", "hello")
	if err != nil || mv.Checksum != moduleVersionChecksum("hello") {
		t.Fatalf("AddVersion = %+v, %v", mv, err)
	}
	if got, err := modules.GetVersion(ctx, userID, "instr", "1.0.0"); err != nil || got == nil || got.Content != "hello" {
		t.Fatalf("GetVersion = %+v, %v", got, err)
	}
	if latest, err := modules.ListLatest(ctx, userID); err != nil || len(latest) != 1 || latest[0].Version != "1.0.0" {
		t.Fatalf("ListLatest = %+v, %v", latest, err)
	}

	// immutable module versions
	if _, err := modules.AddVersion(ctx, userID, "instr", "1.0.0", "hello"); err != nil {
		t.Fatalf("AddVersion(same checksum) = %v", err)
	}
	if _, err := modules.AddVersion(ctx, userID, "instr", "1.0.0", "changed"); err == nil {
		t.Fatal("AddVersion(different checksum) must fail")
	}

	// latest module version per slug, tenant scoped
	if _, err := modules.AddVersion(ctx, userID, "instr", "1.1.0", "newer"); err != nil {
		t.Fatalf("AddVersion 1.1.0: %v", err)
	}
	if listed, err := modules.ListLatest(ctx, userID); err != nil || len(listed) != 1 || listed[0].Slug != "instr" || listed[0].Version != "1.1.0" || listed[0].Checksum != moduleVersionChecksum("newer") {
		t.Fatalf("ListLatest = %+v, %v", listed, err)
	}
	if listed, err := modules.ListLatest(ctx, "other-user"); err != nil || len(listed) != 0 {
		t.Fatalf("ListLatest other tenant = %+v, %v", listed, err)
	}

	// seat type + immutable versions
	seatType, err := seatTypeRepo.Save(ctx, userID, domainrepo.SeatType{
		Slug: "seat.standard", Name: "Standard", Description: "d",
	})
	if err != nil {
		t.Fatalf("Save seat type: %v", err)
	}
	refs := []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0", "go1.23", refs); err != nil {
		t.Fatalf("AddVersion seat type: %v", err)
	}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0", "go1.23", refs); err != nil {
		t.Fatalf("AddVersion seat type (same refs) = %v", err)
	}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0", "go1.23",
		[]resolver.ModuleRef{{Slug: "instr", Version: "2.0.0"}}); !errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) {
		t.Fatalf("AddVersion seat type (different refs) = %v, want ErrSeatTypeVersionConflict", err)
	}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0", "codex", refs); !errors.Is(err, domainrepo.ErrSeatTypeVersionConflict) {
		t.Fatalf("AddVersion seat type (different runtime) = %v, want ErrSeatTypeVersionConflict", err)
	}
	if _, err := seatTypeRepo.AddVersion(ctx, "other-user", "seat.standard", "1.0.1", "codex", refs); err == nil {
		t.Fatal("another tenant must not add a version to this seat type")
	}
	if got, err := seatTypeRepo.GetVersion(ctx, userID, "seat.standard", "1.0.0"); err != nil || got == nil || got.DefaultRuntime != "go1.23" {
		t.Fatalf("version runtime = %+v, %v, want go1.23", got, err)
	}
	if other, err := seatTypeRepo.LatestVersion(ctx, "other-user", "seat.standard"); err != nil || other != nil {
		t.Fatalf("LatestVersion other tenant = %+v, %v, want nil", other, err)
	}
	latestSeatType, err := seatTypeRepo.LatestVersion(ctx, userID, "seat.standard")
	if err != nil || latestSeatType == nil || latestSeatType.Version != "1.0.0" {
		t.Fatalf("LatestVersion seat type = %+v, %v", latestSeatType, err)
	}
	seatTypeList, err := seatTypeRepo.List(ctx, userID)
	if err != nil || len(seatTypeList) != 1 || seatTypeList[0].Slug != "seat.standard" {
		t.Fatalf("List seat types = %+v, %v", seatTypeList, err)
	}

	// room + seat
	room, err := rooms.Save(ctx, userID, domainrepo.Room{Slug: "room-1", Name: "Room 1"})
	if err != nil {
		t.Fatalf("Save room: %v", err)
	}
	seat, err := seats.Create(ctx, userID, domainrepo.Seat{
		RoomID: room.ID, SeatKey: "alpha", SeatTypeID: seatType.ID, Runtime: "go1.23", Model: "deepseek", PermissionPolicy: "standard",
	})
	if err != nil {
		t.Fatalf("Create seat: %v", err)
	}
	if found, err := seats.FindByRoomAndKey(ctx, userID, room.ID, "alpha"); err != nil || found == nil || found.ID != seat.ID {
		t.Fatalf("FindByRoomAndKey = %+v, %v", found, err)
	}

	if err := seats.UpdateOccupant(ctx, userID, seat.ID, "codex", "gpt-5.1"); err != nil {
		t.Fatalf("UpdateOccupant: %v", err)
	}
	if found, err := seats.GetByID(ctx, userID, seat.ID); err != nil || found == nil || found.Runtime != "codex" || found.Model != "gpt-5.1" {
		t.Fatalf("seat after UpdateOccupant = %+v, %v", found, err)
	}
	if err := seats.UpdateOccupant(ctx, "other-user", seat.ID, "claude-code", ""); err != nil {
		t.Fatalf("UpdateOccupant other tenant: %v", err)
	}
	if found, _ := seats.GetByID(ctx, userID, seat.ID); found == nil || found.Runtime != "codex" {
		t.Fatalf("another tenant changed the seat: %+v", found)
	}

	if found, _ := seats.GetByID(ctx, userID, seat.ID); found == nil || found.PermissionPolicy != "standard" {
		t.Fatalf("created seat lost its permission policy: %+v", found)
	}
	if err := seats.UpdatePermissionPolicy(ctx, "other-user", seat.ID, "yolo"); err != nil {
		t.Fatalf("UpdatePermissionPolicy other tenant: %v", err)
	}
	if found, _ := seats.GetByID(ctx, userID, seat.ID); found == nil || found.PermissionPolicy != "standard" {
		t.Fatalf("another tenant changed the permission policy: %+v", found)
	}
	if err := seats.UpdatePermissionPolicy(ctx, userID, seat.ID, "locked"); err != nil {
		t.Fatalf("UpdatePermissionPolicy: %v", err)
	}
	if found, _ := seats.GetByID(ctx, userID, seat.ID); found == nil || found.PermissionPolicy != "locked" || found.Runtime != "codex" {
		t.Fatalf("seat after UpdatePermissionPolicy = %+v", found)
	}

	// resolved seat is idempotent by (seat_id, hash)
	snapshot := domainrepo.ResolvedSeat{
		SeatID: seat.ID, Hash: "hash-1", Runtime: "go1.23",
		Files:  []domainrepo.ResolvedFile{{Path: "main.go", Content: "package main"}},
		Policy: map[string]any{"allow": true},
	}
	if _, err := resolved.Save(ctx, userID, snapshot); err != nil {
		t.Fatalf("Save resolved: %v", err)
	}
	if _, err := resolved.Save(ctx, userID, snapshot); err != nil {
		t.Fatalf("Save resolved (again): %v", err)
	}
	var resolvedCount int
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM "resolved_seats" WHERE "user_id" = $1 AND "seat_id" = $2`, userID, seat.ID).Scan(&resolvedCount); err != nil {
		t.Fatal(err)
	}
	if resolvedCount != 1 {
		t.Fatalf("resolved seats for (seat, hash) = %d, want 1", resolvedCount)
	}
	if got, err := resolved.GetLatest(ctx, userID, seat.ID); err != nil || got == nil || got.Hash != "hash-1" || len(got.Files) != 1 {
		t.Fatalf("GetLatest = %+v, %v", got, err)
	}

	// overlay upsert uniqueness: one row per scope target, ops replaced
	first := domainrepo.Overlay{Scope: domainrepo.ScopeCompany, Ops: []resolver.Op{{Kind: resolver.OpAdd, Slug: "instr", Version: "1.0.0"}}}
	if _, err := overlays.Upsert(ctx, userID, first); err != nil {
		t.Fatalf("Upsert overlay: %v", err)
	}
	second := domainrepo.Overlay{Scope: domainrepo.ScopeCompany, Ops: []resolver.Op{{Kind: resolver.OpRemove, Slug: "instr"}}}
	if _, err := overlays.Upsert(ctx, userID, second); err != nil {
		t.Fatalf("Upsert overlay (again): %v", err)
	}
	var overlayCount int
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM "overlays" WHERE "user_id" = $1 AND "scope" = 'company'`, userID).Scan(&overlayCount); err != nil {
		t.Fatal(err)
	}
	if overlayCount != 1 {
		t.Fatalf("company overlays = %d, want 1", overlayCount)
	}
	found, err := overlays.Find(ctx, userID, domainrepo.ScopeCompany, "", "")
	if err != nil || found == nil || len(found.Ops) != 1 || found.Ops[0].Kind != resolver.OpRemove {
		t.Fatalf("Find overlay = %+v, %v", found, err)
	}

	// settings default false, upsert true, then flip back to false
	settingsDefault, err := settings.Get(ctx, userID)
	if err != nil || settingsDefault == nil || settingsDefault.UserID != userID || settingsDefault.FollowLatest {
		t.Fatalf("Get settings default = %+v, %v", settingsDefault, err)
	}
	settingsSet, err := settings.Set(ctx, userID, true)
	if err != nil || settingsSet == nil || !settingsSet.FollowLatest {
		t.Fatalf("Set settings(true) = %+v, %v", settingsSet, err)
	}
	settingsTrue, err := settings.Get(ctx, userID)
	if err != nil || settingsTrue == nil || !settingsTrue.FollowLatest {
		t.Fatalf("Get settings after set(true) = %+v, %v", settingsTrue, err)
	}
	settingsFalse, err := settings.Set(ctx, userID, false)
	if err != nil || settingsFalse == nil || settingsFalse.FollowLatest {
		t.Fatalf("Set settings(false) = %+v, %v", settingsFalse, err)
	}

	// machine status: a report replaces the machine's seat set, tenants stay isolated
	reportedAt := time.Now().UTC().Truncate(time.Second)
	firstReport := domainrepo.Machine{
		MachineID: "pc-home", LastSeen: reportedAt,
		Seats: []domainrepo.SeatStatus{
			{Room: "eng", Seat: "coder", State: "running", Runtime: "claude-code", RunningHash: "h1", Detail: "busy", ReportedAt: reportedAt},
			{Room: "eng", Seat: "qa", State: "idle", Runtime: "codex", Redacted: true, ReportedAt: reportedAt},
		},
		Agents: []domainrepo.MachineAgent{{Agent: "claude", Status: "working", PaneID: "w5:p3"}},
	}
	if err := machines.ReplaceSnapshot(ctx, userID, firstReport); err != nil {
		t.Fatalf("ReplaceSnapshot first: %v", err)
	}
	secondReport := domainrepo.Machine{
		MachineID: "pc-home", LastSeen: reportedAt.Add(time.Minute),
		Seats:  []domainrepo.SeatStatus{{Room: "eng", Seat: "coder", State: "idle", Runtime: "claude-code", ReportedAt: reportedAt.Add(time.Minute)}},
		Agents: []domainrepo.MachineAgent{},
	}
	if err := machines.ReplaceSnapshot(ctx, userID, secondReport); err != nil {
		t.Fatalf("ReplaceSnapshot second: %v", err)
	}
	listed, err := machines.List(ctx, userID)
	if err != nil || len(listed) != 1 || listed[0].MachineID != "pc-home" ||
		len(listed[0].Seats) != 1 || listed[0].Seats[0].State != "idle" || listed[0].Seats[0].RunningHash != "" ||
		len(listed[0].Agents) != 0 || !listed[0].LastSeen.Equal(reportedAt.Add(time.Minute)) {
		t.Fatalf("List machines after replace = %+v, %v", listed, err)
	}
	if other, err := machines.List(ctx, userID+"-other"); err != nil || len(other) != 0 {
		t.Fatalf("List machines for another tenant = %+v, %v", other, err)
	}
}

// TestSeatDeletesIntegration checks the delete repositories against a real PostgreSQL: another
// tenant deletes nothing, and a parent row cannot go before its dependents (no FK cascade).
func TestSeatDeletesIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, seatIntegrationSchema(t)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	userID := fmt.Sprintf("seat-del-%d", time.Now().UnixNano())
	const other = "seat-del-other-user"

	seatTypes, _ := NewORMSeatTypeRepository(sessions)
	rooms, _ := NewORMRoomRepository(sessions)
	seats, _ := NewORMSeatRepository(sessions)
	links, _ := NewORMSeatLinkRepository(sessions)
	overlays, _ := NewORMOverlayRepository(sessions)
	resolved, _ := NewORMResolvedSeatRepository(sessions)
	machines, _ := NewORMMachineStatusRepository(sessions)

	seatType, err := seatTypes.Save(ctx, userID, domainrepo.SeatType{Slug: "coder", Name: "Coder", Description: "d"})
	if err != nil {
		t.Fatal(err)
	}
	room, err := rooms.Save(ctx, userID, domainrepo.Room{Slug: "dev", Name: "Dev"})
	if err != nil {
		t.Fatal(err)
	}
	a, err := seats.Create(ctx, userID, domainrepo.Seat{RoomID: room.ID, SeatKey: "alice", SeatTypeID: seatType.ID, Runtime: "claude-code", PermissionPolicy: "standard"})
	if err != nil {
		t.Fatal(err)
	}
	b, err := seats.Create(ctx, userID, domainrepo.Seat{RoomID: room.ID, SeatKey: "bob", SeatTypeID: seatType.ID, Runtime: "claude-code", PermissionPolicy: "standard"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := links.Upsert(ctx, userID, domainrepo.SeatLink{FromSeatID: a.ID, ToSeatID: b.ID, Kind: "delegates_to", Allow: true}); err != nil {
		t.Fatal(err)
	}
	if _, err := links.Upsert(ctx, userID, domainrepo.SeatLink{FromSeatID: b.ID, ToSeatID: a.ID, Kind: "escalates_to", Allow: true}); err != nil {
		t.Fatal(err)
	}
	ops := []resolver.Op{{Kind: resolver.OpRemove, Slug: "instr"}}
	if _, err := overlays.Upsert(ctx, userID, domainrepo.Overlay{Scope: domainrepo.ScopeRoom, RoomID: room.ID, Ops: ops}); err != nil {
		t.Fatal(err)
	}
	if _, err := overlays.Upsert(ctx, userID, domainrepo.Overlay{Scope: domainrepo.ScopeSeat, SeatID: a.ID, Ops: ops}); err != nil {
		t.Fatal(err)
	}
	if _, err := resolved.Save(ctx, userID, domainrepo.ResolvedSeat{SeatID: a.ID, Hash: "h", Runtime: "claude-code"}); err != nil {
		t.Fatal(err)
	}
	reportedAt := time.Now().UTC()
	for _, user := range []string{userID, other} {
		if err := machines.ReplaceSnapshot(ctx, user, domainrepo.Machine{
			MachineID: "pc", LastSeen: reportedAt,
			Seats: []domainrepo.SeatStatus{
				{Room: "dev", Seat: "alice", State: "running", Runtime: "claude-code", ReportedAt: reportedAt},
				{Room: "ops", Seat: "carol", State: "idle", Runtime: "codex", ReportedAt: reportedAt},
			},
			Agents: []domainrepo.MachineAgent{},
		}); err != nil {
			t.Fatal(err)
		}
	}
	count := func(query string, args ...any) int {
		t.Helper()
		var n int
		if err := db.QueryRowContext(ctx, query, args...).Scan(&n); err != nil {
			t.Fatal(err)
		}
		return n
	}

	// another tenant deletes nothing
	if deleted, err := links.Delete(ctx, other, a.ID, b.ID, "delegates_to"); err != nil || deleted {
		t.Fatalf("Delete link other tenant = %v, %v", deleted, err)
	}
	for name, fn := range map[string]func() error{
		"links":    func() error { return links.DeleteBySeat(ctx, other, a.ID) },
		"overlays": func() error { return overlays.DeleteForSeat(ctx, other, a.ID) },
		"room ov.": func() error { return overlays.DeleteForRoom(ctx, other, room.ID) },
		"resolved": func() error { return resolved.DeleteBySeat(ctx, other, a.ID) },
		"seat":     func() error { return seats.Delete(ctx, other, a.ID) },
		"room":     func() error { return rooms.Delete(ctx, other, room.ID) },
	} {
		if err := fn(); err != nil {
			t.Fatalf("%s delete as another tenant: %v", name, err)
		}
	}
	if n := count(`SELECT (SELECT count(*) FROM seat_links WHERE user_id = $1) + (SELECT count(*) FROM overlays WHERE user_id = $1) + (SELECT count(*) FROM resolved_seats WHERE user_id = $1) + (SELECT count(*) FROM seats WHERE user_id = $1) + (SELECT count(*) FROM rooms WHERE user_id = $1)`, userID); n != 8 {
		t.Fatalf("rows after another tenant's deletes = %d, want 8", n)
	}

	// no cascade: the seat cannot go while a link still references it
	if err := seats.Delete(ctx, userID, a.ID); err == nil {
		t.Fatal("Delete seat with links must fail: foreign keys do not cascade")
	}

	// one link, then everything under the room in dependency order
	if deleted, err := links.Delete(ctx, userID, a.ID, b.ID, "delegates_to"); err != nil || !deleted {
		t.Fatalf("Delete link = %v, %v", deleted, err)
	}
	if deleted, err := links.Delete(ctx, userID, a.ID, b.ID, "delegates_to"); err != nil || deleted {
		t.Fatalf("Delete link again = %v, %v", deleted, err)
	}
	if n := count(`SELECT count(*) FROM seat_links WHERE user_id = $1`, userID); n != 1 {
		t.Fatalf("links after one delete = %d, want 1", n)
	}
	for _, seat := range []*domainrepo.Seat{a, b} {
		if err := links.DeleteBySeat(ctx, userID, seat.ID); err != nil {
			t.Fatal(err)
		}
		if err := overlays.DeleteForSeat(ctx, userID, seat.ID); err != nil {
			t.Fatal(err)
		}
		if err := resolved.DeleteBySeat(ctx, userID, seat.ID); err != nil {
			t.Fatal(err)
		}
		if err := seats.Delete(ctx, userID, seat.ID); err != nil {
			t.Fatal(err)
		}
	}
	if err := overlays.DeleteForRoom(ctx, userID, room.ID); err != nil {
		t.Fatal(err)
	}
	if err := machines.DeleteSeatStatusForRoom(ctx, other, "dev"); err != nil {
		t.Fatal(err)
	}
	if n := count(`SELECT count(*) FROM seat_status WHERE user_id = $1`, userID); n != 2 {
		t.Fatalf("seat_status after another tenant's delete = %d, want 2", n)
	}
	if err := machines.DeleteSeatStatusForRoom(ctx, userID, "dev"); err != nil {
		t.Fatal(err)
	}
	if n := count(`SELECT count(*) FROM seat_status WHERE user_id = $1 AND room = 'dev'`, userID); n != 0 {
		t.Fatalf("seat_status of the deleted room = %d, want 0", n)
	}
	if n := count(`SELECT count(*) FROM seat_status WHERE user_id = $1 AND room = 'ops'`, userID); n != 1 {
		t.Fatalf("seat_status of another room = %d, want 1", n)
	}
	for _, c := range []struct{ user, room, seat string }{{userID, "ops", "alice"}, {userID, "dev", "carol"}} {
		if err := machines.DeleteSeatStatusForSeat(ctx, c.user, c.room, c.seat); err != nil {
			t.Fatal(err)
		}
	}
	if n := count(`SELECT count(*) FROM seat_status WHERE user_id = $1 AND room = 'ops'`, userID); n != 1 {
		t.Fatalf("seat_status after deletes of another tenant, seat and room = %d, want 1", n)
	}
	if err := machines.DeleteSeatStatusForSeat(ctx, userID, "ops", "carol"); err != nil {
		t.Fatal(err)
	}
	if n := count(`SELECT count(*) FROM seat_status WHERE user_id = $1 AND room = 'ops'`, userID); n != 0 {
		t.Fatalf("seat_status of the deleted seat = %d, want 0", n)
	}
	if n := count(`SELECT count(*) FROM seat_status WHERE user_id = $1 AND room = 'ops' AND seat = 'carol'`, other); n != 1 {
		t.Fatalf("another tenant's seat_status of the same seat = %d, want 1 (the delete is tenant-scoped)", n)
	}
	if err := rooms.Delete(ctx, userID, room.ID); err != nil {
		t.Fatal(err)
	}
	if n := count(`SELECT (SELECT count(*) FROM seat_links WHERE user_id = $1) + (SELECT count(*) FROM overlays WHERE user_id = $1) + (SELECT count(*) FROM resolved_seats WHERE user_id = $1) + (SELECT count(*) FROM seats WHERE user_id = $1) + (SELECT count(*) FROM rooms WHERE user_id = $1)`, userID); n != 0 {
		t.Fatalf("rows left after deletes = %d, want 0", n)
	}
}

// TestMachineTokensIntegration checks the machine token repository against a real PostgreSQL:
// one active token per (user, machine), revocation, and lookup by hash only.
func TestMachineTokensIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, seatIntegrationSchema(t)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	tokens, err := NewORMMachineTokenRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	stamp := time.Now().UnixNano()
	userA, userB := fmt.Sprintf("tok-a-%d", stamp), fmt.Sprintf("tok-b-%d", stamp)
	hashA, hashA2, hashB := fmt.Sprintf("hash-a-%d", stamp), fmt.Sprintf("hash-a2-%d", stamp), fmt.Sprintf("hash-b-%d", stamp)

	created, err := tokens.Create(ctx, userA, "pc-home", hashA)
	if err != nil || created.UserID != userA || created.MachineID != "pc-home" || created.RevokedAt != nil {
		t.Fatalf("Create = %+v, %v", created, err)
	}
	if _, err := tokens.Create(ctx, userA, "pc-home", hashA2); !errors.Is(err, domainrepo.ErrMachineTokenExists) {
		t.Fatalf("second active token = %v, want ErrMachineTokenExists", err)
	}
	if _, err := tokens.Create(ctx, userB, "pc-home", hashB); err != nil {
		t.Fatalf("the same machine id for another user: %v", err)
	}
	if found, err := tokens.FindActive(ctx, hashA); err != nil || found == nil || found.UserID != userA || found.MachineID != "pc-home" {
		t.Fatalf("FindActive = %+v, %v", found, err)
	}
	if found, err := tokens.FindActive(ctx, "no-such-hash"); err != nil || found != nil {
		t.Fatalf("FindActive unknown = %+v, %v", found, err)
	}

	if revoked, err := tokens.Revoke(ctx, userB, "pc-other"); err != nil || revoked {
		t.Fatalf("Revoke of a machine without a token = %v, %v", revoked, err)
	}
	if found, _ := tokens.FindActive(ctx, hashA); found == nil {
		t.Fatal("another user's revoke attempt changed this token")
	}
	if revoked, err := tokens.Revoke(ctx, userA, "pc-home"); err != nil || !revoked {
		t.Fatalf("Revoke = %v, %v", revoked, err)
	}
	if found, err := tokens.FindActive(ctx, hashA); err != nil || found != nil {
		t.Fatalf("FindActive after revoke = %+v, %v, want nil", found, err)
	}
	if found, _ := tokens.FindActive(ctx, hashB); found == nil {
		t.Fatal("revoking user A's token revoked user B's")
	}
	if revoked, err := tokens.Revoke(ctx, userA, "pc-home"); err != nil || revoked {
		t.Fatalf("second Revoke = %v, %v, want false", revoked, err)
	}
	if _, err := tokens.Create(ctx, userA, "pc-home", hashA2); err != nil {
		t.Fatalf("a revoked machine can be registered again: %v", err)
	}
}

// seatIntegrationSchema reads the seat schema DDL next to this test.
func seatIntegrationSchema(t *testing.T) string {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	path := filepath.Join(filepath.Dir(thisFile), "..", "..", "schema", "seat_management_postgresql.sql")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read schema %s: %v", path, err)
	}
	return seatSchemaApplyLock + string(raw)
}

// seatSchemaApplyLock serializes schema applies from parallel test packages: the statement
// batch runs as one implicit transaction, so the transaction-scoped lock is held until the
// whole schema is applied. Without it, concurrent CREATE EXTENSION runs hit a unique violation.
const seatSchemaApplyLock = "SELECT pg_advisory_xact_lock(727274);\n"

// TestMachineExpectedHashIntegration checks the expected hash of a reported seat against a real
// PostgreSQL: the newest snapshot wins, a seat missing from the cloud has none, and another
// tenant's snapshot of the same room and seat names never shows up.
func TestMachineExpectedHashIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if _, err := db.ExecContext(ctx, seatIntegrationSchema(t)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	userID := fmt.Sprintf("seat-sync-%d", time.Now().UnixNano())
	other := userID + "-other" // per run: rows from an earlier run would collide on uq_seats_room_seat_key

	seatTypes, _ := NewORMSeatTypeRepository(sessions)
	rooms, _ := NewORMRoomRepository(sessions)
	seats, _ := NewORMSeatRepository(sessions)
	resolved, _ := NewORMResolvedSeatRepository(sessions)
	machines, _ := NewORMMachineStatusRepository(sessions)

	// both tenants own a room "dev" with seat "alice"; the other tenant's snapshot is newer
	seed := func(user string, hashes ...string) {
		t.Helper()
		seatType, err := seatTypes.Save(ctx, user, domainrepo.SeatType{Slug: "coder", Name: "Coder", Description: "d"})
		if err != nil {
			t.Fatal(err)
		}
		room, err := rooms.Save(ctx, user, domainrepo.Room{Slug: "dev", Name: "Dev"})
		if err != nil {
			t.Fatal(err)
		}
		seat, err := seats.Create(ctx, user, domainrepo.Seat{RoomID: room.ID, SeatKey: "alice", SeatTypeID: seatType.ID, Runtime: "claude-code", PermissionPolicy: "standard"})
		if err != nil {
			t.Fatal(err)
		}
		for _, hash := range hashes {
			if _, err := resolved.Save(ctx, user, domainrepo.ResolvedSeat{SeatID: seat.ID, Hash: hash, Runtime: "claude-code"}); err != nil {
				t.Fatal(err)
			}
		}
	}
	seed(userID, "h1", "h2")
	seed(other, "other-hash")

	report := func(user, hash string) {
		t.Helper()
		now := time.Now().UTC()
		if err := machines.ReplaceSnapshot(ctx, user, domainrepo.Machine{
			MachineID: "pc", LastSeen: now,
			Seats: []domainrepo.SeatStatus{
				{Room: "dev", Seat: "alice", State: "running", Runtime: "claude-code", RunningHash: hash, ReportedAt: now},
				{Room: "dev", Seat: "ghost", State: "idle", Runtime: "claude-code", RunningHash: hash, ReportedAt: now},
				{Room: "nowhere", Seat: "alice", State: "idle", Runtime: "claude-code", RunningHash: hash, ReportedAt: now},
			},
			Agents: []domainrepo.MachineAgent{},
		}); err != nil {
			t.Fatal(err)
		}
	}
	expected := func(user string) map[string]string {
		t.Helper()
		listed, err := machines.List(ctx, user)
		if err != nil || len(listed) != 1 {
			t.Fatalf("List = %+v, %v", listed, err)
		}
		if len(listed[0].Seats) != 3 {
			t.Fatalf("List returned %d seat rows, want exactly 3 (a map would hide duplicates): %+v", len(listed[0].Seats), listed[0].Seats)
		}
		out := map[string]string{}
		for _, s := range listed[0].Seats {
			out[s.Room+"/"+s.Seat] = s.ExpectedHash
		}
		return out
	}
	want := map[string]string{"dev/alice": "h2", "dev/ghost": "", "nowhere/alice": ""}

	report(userID, "h1") // running an older snapshot: the expected hash is still the newest
	if got := expected(userID); !reflect.DeepEqual(got, want) {
		t.Fatalf("expected hashes after reporting h1 = %v, want %v", got, want)
	}
	report(userID, "h2")
	if got := expected(userID); !reflect.DeepEqual(got, want) {
		t.Fatalf("expected hashes after reporting h2 = %v, want %v", got, want)
	}
	report(other, "x")
	if got := expected(other); got["dev/alice"] != "other-hash" {
		t.Fatalf("other tenant expected hashes = %v, want its own snapshot", got)
	}
}
