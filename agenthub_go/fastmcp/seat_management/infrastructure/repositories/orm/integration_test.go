package orm

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
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
	if latest, err := modules.LatestVersion(ctx, userID, "instr"); err != nil || latest == nil || latest.Version != "1.0.0" {
		t.Fatalf("LatestVersion = %+v, %v", latest, err)
	}

	// immutable module versions
	if _, err := modules.AddVersion(ctx, userID, "instr", "1.0.0", "hello"); err != nil {
		t.Fatalf("AddVersion(same checksum) = %v", err)
	}
	if _, err := modules.AddVersion(ctx, userID, "instr", "1.0.0", "changed"); err == nil {
		t.Fatal("AddVersion(different checksum) must fail")
	}

	// seat type + immutable versions
	seatType, err := seatTypeRepo.Save(ctx, userID, domainrepo.SeatType{
		Slug: "seat.standard", Name: "Standard", Description: "d", DefaultRuntime: "go1.23",
	})
	if err != nil {
		t.Fatalf("Save seat type: %v", err)
	}
	refs := []resolver.ModuleRef{{Slug: "instr", Version: "1.0.0"}}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0", refs); err != nil {
		t.Fatalf("AddVersion seat type: %v", err)
	}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0", refs); err != nil {
		t.Fatalf("AddVersion seat type (same refs) = %v", err)
	}
	if _, err := seatTypeRepo.AddVersion(ctx, userID, "seat.standard", "1.0.0",
		[]resolver.ModuleRef{{Slug: "instr", Version: "2.0.0"}}); err == nil {
		t.Fatal("AddVersion seat type (different refs) must fail")
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
		RoomID: room.ID, SeatKey: "alpha", SeatTypeID: seatType.ID, Runtime: "go1.23", Model: "deepseek",
	})
	if err != nil {
		t.Fatalf("Create seat: %v", err)
	}
	if found, err := seats.FindByRoomAndKey(ctx, userID, room.ID, "alpha"); err != nil || found == nil || found.ID != seat.ID {
		t.Fatalf("FindByRoomAndKey = %+v, %v", found, err)
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
	return string(raw)
}
