package database

import (
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/feedback"
)

// Register seat_feedback with the shared DDL-vs-struct map so TestSeatORMMatchesDDL covers it.
func init() {
	seatTableTypes["seat_feedback"] = reflect.TypeOf(SeatFeedbackORM{})
}

// TestSeatFeedbackLayerCheckMatchesDomain is the constraint half of the same guard the seats
// table has for permission_policy: the vocabulary in domain/feedback is the single source of
// truth, and BOTH DDL copies must list exactly it. The reviewer's rollback lesson is why the
// CONSTRAINT is checked and not only the columns - a value an older binary cannot spell is the
// part that trips it - and TestSeatDDLParity separately checks that the two copies agree with
// each other.
func TestSeatFeedbackLayerCheckMatchesDomain(t *testing.T) {
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	raw, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "..", "schema", "seat_management_postgresql.sql"))
	if err != nil {
		t.Fatal(err)
	}

	quoted := make([]string, len(feedback.Layers))
	for i, layer := range feedback.Layers {
		quoted[i] = "'" + string(layer) + "'"
	}
	want := "CONSTRAINT ck_seat_feedback_layer CHECK (layer IN (" + strings.Join(quoted, ", ") + "))"

	if !strings.Contains(string(raw), want) {
		t.Errorf("schema SQL lacks %q", want)
	}
	found := false
	for _, table := range seatManagementDatabaseTables {
		if table.Name != "seat_feedback" {
			continue
		}
		for _, stmt := range table.DDL {
			found = found || strings.Contains(stmt, want)
		}
	}
	if !found {
		t.Errorf("seat_feedback DDL lacks %q", want)
	}
}
