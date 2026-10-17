package httpapp

// O9c: the five ai_* actions on manage_task are retired (owner directive 3: delete the server-side AI
// planning package, the five ai_* actions and the ai_* task columns - the architecture does not use a
// server-side model runtime). They were dead stubs: every one of them answered "AI integration is not available: the
// AITaskIntegrationService seam is not wired in this build", so a caller was told to plan with a tool that
// could never plan.
//
// TWO HALVES, and both are asserted here because either alone is satisfiable for the wrong reason:
//   - NOT ADVERTISED: manage_task's own description, as tools/list publishes it, names none of the five.
//   - NOT DISPATCHABLE: calling one is refused as an unknown action, not with the old AI-seam sentence.
// The landmarks keep the registry honest: a tool list that lost manage_task would pass "names no ai_*"
// while proving nothing.

import (
	"encoding/json"
	"net/http"
	"strings"
	"testing"
)

func TestManageTaskPublishesAndDispatchesNoAIActions(t *testing.T) {
	t.Setenv("AUTH_ENABLED", "false")
	app := newMCPTestApp(t)

	rec := postMCP(t, app, `{"jsonrpc":"2.0","id":1,"method":"tools/list"}`, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
	var wire struct {
		Result struct {
			Tools []struct {
				Name        string `json:"name"`
				Description string `json:"description"`
			} `json:"tools"`
		} `json:"result"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &wire); err != nil {
		t.Fatalf("decode tools/list: %v\nbody: %s", err, rec.Body.String())
	}
	description := ""
	published := 0
	for _, tool := range wire.Result.Tools {
		published++
		if tool.Name == "manage_task" {
			description = tool.Description
		}
	}
	if description == "" {
		t.Fatalf("tools/list no longer publishes manage_task, so this case is not reading the registry it thinks it is (%d tools)", published)
	}
	for _, retired := range []string{"ai_plan", "ai_create", "ai_enhance", "ai_analyze", "ai_suggest_agents"} {
		if strings.Contains(description, retired) {
			t.Errorf("manage_task's published description still names %q: the ai_* actions are retired", retired)
		}
	}

	// NOT DISPATCHABLE: the old answer was success=false with the AI-seam sentence; the answer now is an
	// unknown/invalid action, and the AI-seam sentence must be gone with the seam itself.
	call := `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"manage_task","arguments":{"action":"ai_plan","requirements":"r","title":"t","git_branch_id":"b"}}}`
	rec = postMCP(t, app, call, "")
	body := rec.Body.String()
	if strings.Contains(body, "AITaskIntegrationService") {
		t.Errorf("manage_task(action=ai_plan) still answers from the retired AI seam: %s", body)
	}
	if !strings.Contains(body, "ai_plan") {
		t.Errorf("the refusal does not name the action it refused: %s", body)
	}
}
