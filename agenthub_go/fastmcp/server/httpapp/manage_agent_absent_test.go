package httpapp

// STEP 1(a) of the agent-library retirement (item 3, CHOICE B; the plan is
// PLAN-call-agent-agent-library-retirement-2026-10-10.md, section 4).
//
// manage_agent is the tool that reads and writes the `agents` table and the 32-role registry, and it
// is the second identity system the seat model replaces: register -> seat create, assign -> a task
// assignee of `@<seat_key>`, list/get -> `manage_seat list`, rebalance -> the lead's queue. Its
// responses also carry a `call_agent` field naming a tool that has not existed since T6, so the
// registry advertises an identity model whose entry point is gone.
//
// THE FULL REGISTRY IS THE SUBJECT, so this case builds it through newMCPTestApp - the same
// constructor the production app uses - rather than wiring only the tools it cares about: a registry
// handed one tool cannot show an absence, because every other name is absent from it too.
//
// The vacuity guard matters as much as the assertion. A registry that came back empty, or that lost
// the tools this case uses as landmarks, would satisfy "manage_agent is not published" while proving
// nothing at all.
//
// The `call_agent` half of the same absence was asserted in call_seat_mcp_test.go (T6 retired that
// tool); it belongs with the rest of the retirement, so it moved here and that guard was removed.

import (
	"encoding/json"
	"net/http"
	"testing"
)

func TestMCPToolsListDoesNotPublishManageAgent(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newMCPTestApp(t)

	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			Tools []struct {
				Name string `json:"name"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode tools/list: %v\nbody: %s", err, rec.Body.String())
	}

	published := make(map[string]bool, len(wire.Result.Tools))
	for _, tool := range wire.Result.Tools {
		published[tool.Name] = true
	}

	// The landmarks: three tools that must still be there, so an empty or truncated registry fails
	// here instead of passing the absence check below for the wrong reason.
	for _, present := range []string{"manage_task", "manage_seat", "call_seat"} {
		if !published[present] {
			t.Fatalf("tools/list no longer publishes %s, so this case is not reading the registry it thinks it is (%d tools)",
				present, len(wire.Result.Tools))
		}
	}

	if published["manage_agent"] {
		t.Error("tools/list still publishes manage_agent: the agents table and the role registry are retired, and '@<seat_key>' is the only assignee identity")
	}
	if published["call_agent"] {
		t.Error("tools/list still publishes call_agent: the agent identity model it addressed is retired, and seats are addressed with call_seat")
	}
}
