package database

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"

	"agenthub/fastmcp/room_decisions/domain/decisions"
)

// Register room_decisions with the shared DDL-vs-struct map so TestSeatORMMatchesDDL covers it.
func init() {
	seatTableTypes["room_decisions"] = reflect.TypeOf(RoomDecisionORM{})
}

// TestRoomDecisionStateCheckMatchesDomain is the constraint half of the guard the seats table has
// for permission_policy and seat_feedback has for layer: the vocabulary in
// domain/decisions is the single source of truth, and BOTH DDL copies must list exactly it.
//
// The state is what the answer route branches on - it is the `state-<state>` refusal and the
// `state` a panel shows - so a value one copy can spell and the other cannot is the drift that
// matters, and TestSeatDDLParity separately checks that the two copies agree with each other.
func TestRoomDecisionStateCheckMatchesDomain(t *testing.T) {
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "..", "schema", "seat_management_postgresql.sql"))
	if err != nil {
		t.Fatal(err)
	}

	quoted := make([]string, len(decisions.States))
	for i, state := range decisions.States {
		quoted[i] = "'" + string(state) + "'"
	}
	want := "CONSTRAINT ck_room_decisions_state CHECK (state IN (" + strings.Join(quoted, ", ") + "))"

	if !strings.Contains(string(raw), want) {
		t.Errorf("schema SQL lacks %q", want)
	}
	found := false
	for _, table := range seatManagementDatabaseTables {
		if table.Name != "room_decisions" {
			continue
		}
		for _, stmt := range table.DDL {
			found = found || strings.Contains(stmt, want)
		}
	}
	if !found {
		t.Errorf("room_decisions DDL lacks %q", want)
	}
}
