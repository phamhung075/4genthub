package httpapp

// This file exists for ONE reason, and it is worth the extra file: it makes the red-then-green for
// the `edges` key a runnable artifact instead of a claim about a working tree.
//
// The test below uses only symbols that ALREADY EXIST at 02bfd416^ - the payload constant, the
// fake repository, the mux and the two HTTP helpers - and none of the types this change adds. So a
// stranger can reproduce the red exactly:
//
//	git archive 02bfd416^ agenthub_go | tar -x -C /tmp/parent
//	cp agenthub_go/fastmcp/server/httpapp/seat_status_no_edges_test.go /tmp/parent/agenthub_go/fastmcp/server/httpapp/
//	cd /tmp/parent/agenthub_go && go test ./fastmcp/server/httpapp/ -run TestSeatStatusPostWithoutEdges
//
// and should see it FAIL on "the machine body carries no edges key" - the old server never set that
// key - then pass in the current tree. Keeping it beside the tests that DO need the new symbols
// would have made the parent checkout fail to COMPILE instead, which proves nothing about the wire.
//
// The contract it pins: a report WITHOUT edges is still accepted, its seats and agents are still
// stored, and the machine reads back with an EMPTY edge set rather than a missing key. That last
// point is the one the frontend depends on - it may read `edges` without a presence check.

import (
	"encoding/json"
	"net/http"
	"testing"
)

func TestSeatStatusPostWithoutEdgesIsAcceptedAndServesAnEmptyEdgeSet(t *testing.T) {
	fake := &fakeSeatStatus{}
	mux := seatStatusTestMux(t, fake)
	if rec := postSeatStatus(mux, validSeatStatusBody); rec.Code != http.StatusOK {
		t.Fatalf("POST without an edges key = %d %s", rec.Code, rec.Body.String())
	}
	if stored := fake.byUser["11111111-1111-4111-8111-111111111111"]["pc-home"]; len(stored.Seats) != 1 {
		t.Fatalf("the report without edges must still store its seats: %+v", stored)
	}
	rec := getMachines(mux)
	var got struct {
		Machines []map[string]json.RawMessage `json:"machines"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v\n%s", err, rec.Body.String())
	}
	if len(got.Machines) != 1 {
		t.Fatalf("GET = %s", rec.Body.String())
	}
	edges, ok := got.Machines[0]["edges"]
	if !ok {
		t.Fatalf("the machine body carries no edges key: %s", rec.Body.String())
	}
	if string(edges) != "[]" {
		t.Fatalf("edges = %s, want []", edges)
	}
}
