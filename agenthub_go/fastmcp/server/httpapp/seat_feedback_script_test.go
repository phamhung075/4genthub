package httpapp

// The shell submission path, exercised for real: the script is executed against the routed server
// over HTTP, and the row it produces is compared with the row the MCP tool produces. Both must be
// one shape, because both must reach one writer.
//
// The script moved to the client package (2026-10-09): scripts/seat_feedback.sh became
// agenthub_client/src/agenthub_client/seat_feedback.sh, byte-identical, when the local scripts were
// relocated into the installed `4genteam` client. This path is the second half of that move: the
// guard executes the real file by relative path, so leaving it pointing at the retired one turns
// the move into a red test rather than a silent loss of the no-MCP door.

import (
	"bytes"
	"encoding/json"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	seatservices "agenthub/fastmcp/seat_management/application/services"
)

// seatFeedbackScriptPath is the submission script inside the local client package, which is where
// it lives now: agenthub_client/src/agenthub_client/seat_feedback.sh, four levels up from this
// package and then into the package. It was scripts/seat_feedback.sh before the 2026-10-09
// relocation, and this helper is what made the move visible instead of quiet.
func seatFeedbackScriptPath(t *testing.T) string {
	t.Helper()
	path := filepath.Join("..", "..", "..", "..",
		"agenthub_client", "src", "agenthub_client", "seat_feedback.sh")
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("cannot find the submission script: %v", err)
	}
	return path
}

func TestSeatFeedbackScriptSubmitsThroughTheSameRoute(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	store := &fakeSeatFeedback{}
	f := newFeedbackFixtureWithStore(t, store)
	server := httptest.NewServer(f.mux)
	defer server.Close()

	script := seatFeedbackScriptPath(t)
	cmd := exec.Command("sh", script,
		"--layer", "openrig",
		"--text", "the script path",
		"--room", "4genthub-min",
		"--seat", "go-dev",
		"--session", "4genthub-min-go-dev@4genthub-min",
		"--url", server.URL,
	)
	cmd.Env = append(os.Environ(), "AGENTHUB_TOKEN=script-test-token")
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("script failed: %v\n%s", err, out)
	}
	var answer map[string]any
	if err := json.Unmarshal(bytes.TrimSpace(out), &answer); err != nil {
		t.Fatalf("script output %s is not the route's JSON answer: %v", out, err)
	}
	if answer["success"] != true || answer["layer"] != "openrig" {
		t.Fatalf("script answer = %v, want success and the stored layer", answer)
	}

	scriptRow := findReport(t, store, "the script path")
	if answer["id"] != scriptRow.ID {
		t.Fatalf("script answer %v does not carry the stored id %q", answer, scriptRow.ID)
	}

	// The MCP tool, over the same store, for the row-shape comparison.
	app := newSubmitFeedbackTestApp(t, seatservices.NewSeatFeedbackService(store))
	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"submit_feedback",`+
		`"arguments":{"room":"4genthub-min","seat":"go-dev","session":"4genthub-min-go-dev@4genthub-min","layer":"openrig","text":"the tool path"}}}`, "")
	_ = toolText(t, rec)
	toolRow := findReport(t, store, "the tool path")

	assertSameRowShape(t, scriptRow, toolRow)
}

// TestSeatFeedbackScriptRefusesBadInputWithoutCallingTheServer: the script validates before it
// dials, so a typo does not become a request the route has to reject.
func TestSeatFeedbackScriptRefusesBadInputWithoutCallingTheServer(t *testing.T) {
	store := &fakeSeatFeedback{}
	f := newFeedbackFixtureWithStore(t, store)
	server := httptest.NewServer(f.mux)
	defer server.Close()

	script := seatFeedbackScriptPath(t)
	cmd := exec.Command("sh", script, "--layer", "harness", "--text", "t", "--url", server.URL)
	cmd.Env = append(os.Environ(), "AGENTHUB_TOKEN=script-test-token")
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("script accepted an unknown layer: %s", out)
	}
	if !strings.Contains(string(out), "is not one of runtime, openrig, cloud, seat-context, workspace, other") {
		t.Fatalf("script output = %s, want the vocabulary", out)
	}
	if len(store.reports) != 0 {
		t.Fatalf("a refused submission reached the store: %+v", store.reports)
	}
}
