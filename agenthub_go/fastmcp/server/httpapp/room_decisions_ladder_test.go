package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"path/filepath"
	"strings"
	"testing"

	roomservices "agenthub/fastmcp/room_decisions/application/services"
	roomdecisions "agenthub/fastmcp/room_decisions/domain/decisions"
	roomquestions "agenthub/fastmcp/room_decisions/domain/questions"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type ladderStubEvaluator struct{ confidence float64 }

func (e ladderStubEvaluator) SelectDecisionChoices(_ context.Context, _, _, _ string, qs []roomquestions.HumanQuestion) (map[string]roomservices.DecisionChoiceSelection, error) {
	out := map[string]roomservices.DecisionChoiceSelection{}
	for _, q := range qs {
		out[q.ID] = roomservices.DecisionChoiceSelection{SelectedOptionID: q.Options[0].ID, Confidence: e.confidence}
	}
	return out, nil
}

func ladderBody(tier, category string) string {
	return `{"tier":"` + tier + `","category":"` + category + `","summary":"db","detail":"pick one",` +
		`"questions":[{"id":"q1","question":"Which db?","options":[{"id":"pg","label":"PostgreSQL","recommended":true},{"id":"lite","label":"SQLite"}]}]}`
}

// TestRoomDecisionEvaluateIsTheLadderStep pins the route: a seat at 0.9 is answered where it asked, a
// seat at 0.6 is sent to the lead with its recommendation, and a credential question at 0.95 is sent
// to the owner whatever Jev says.
func TestRoomDecisionEvaluateIsTheLadderStep(t *testing.T) {
	roomservices.SetJevDecisionLogPath(filepath.Join(t.TempDir(), "jev_decisions.log"))
	t.Cleanup(func() { roomservices.SetJevDecisionLogPath("") })
	f := newRoomDecisionFixture(t).withRows().mount()
	confidence := 0.9
	newRoomDecisionService = func(*database.SessionManager) (*roomservices.RoomDecisionService, error) {
		return roomservices.NewRoomDecisionService(f.store).WithEvaluator(ladderStubEvaluator{confidence}, "jev-1.13.0", 0.8), nil
	}
	evaluate := func(body string) map[string]any {
		t.Helper()
		rec := f.do(http.MethodPost, "/api/v2/openrig/decisions/evaluate", "user-jwt", body)
		if rec.Code != http.StatusOK {
			t.Fatalf("evaluate = %d %s, want 200", rec.Code, rec.Body.String())
		}
		var out map[string]any
		if err := json.Unmarshal(rec.Body.Bytes(), &out); err != nil {
			t.Fatal(err)
		}
		return out
	}

	if out := evaluate(ladderBody("seat", "general")); out["decided"] != true || out["escalate_to"] != nil {
		t.Errorf("seat at 0.9 = %v, want decided with no escalation", out)
	}
	confidence = 0.6
	out := evaluate(ladderBody("seat", "general"))
	if out["decided"] != false || out["escalate_to"] != "lead" || !strings.Contains(string(mustJSON(t, out)), `"recommended":"pg"`) {
		t.Errorf("seat at 0.6 = %v, want escalate to lead carrying pg", out)
	}
	confidence = 0.95
	if out := evaluate(ladderBody("seat", "credentials")); out["decided"] != false || out["escalate_to"] != "owner" {
		t.Errorf("credential at 0.95 = %v, want owner", out)
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/decisions/evaluate", "user-jwt", ladderBody("owner", "general")); rec.Code != http.StatusBadRequest {
		t.Errorf("tier owner = %d, want 400", rec.Code)
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/decisions/evaluate", "", ladderBody("seat", "general")); rec.Code != http.StatusForbidden {
		t.Errorf("unauthenticated = %d, want 403", rec.Code)
	}
}

func mustJSON(t *testing.T, v any) []byte {
	t.Helper()
	raw, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	return raw
}

// TestRoomDecisionServiceReadsOwnerOnlyCategoriesFromTheEnvironment pins the wiring the stubbed tests
// above skip: the real factory reads DECISION_OWNER_ONLY_CATEGORIES, so a category the project names
// goes to the owner without a Jev call (the factory's Jev client is never reached here), and a
// malformed list is refused when the service is built rather than silently ignored.
func TestRoomDecisionServiceReadsOwnerOnlyCategoriesFromTheEnvironment(t *testing.T) {
	roomservices.SetJevDecisionLogPath(filepath.Join(t.TempDir(), "jev_decisions.log"))
	t.Cleanup(func() { roomservices.SetJevDecisionLogPath("") })
	sessions := database.NewSessionManager(&database.DatabaseConfig{})
	questions := json.RawMessage(`[{"id":"q1","question":"Cap?","options":[{"id":"a","label":"A","recommended":true},{"id":"b","label":"B"}]}]`)

	t.Setenv("DECISION_OWNER_ONLY_CATEGORIES", "omp_cap")
	service, err := newRoomDecisionService(sessions)
	if err != nil {
		t.Fatal(err)
	}
	for _, category := range []roomdecisions.Category{"omp_cap", "credentials"} {
		outcome, err := service.Evaluate(context.Background(), roomdecisions.TierSeat, category, "cap", "detail", questions, roomDecisionNow())
		if err != nil {
			t.Fatal(err)
		}
		if outcome.Decided || outcome.EscalateTo != roomdecisions.TierOwner || outcome.Questions[0].Recommended != "a" {
			t.Errorf("%s = %+v, want owner escalation carrying the recommendation", category, outcome)
		}
	}

	t.Setenv("DECISION_OWNER_ONLY_CATEGORIES", "has space")
	if _, err := newRoomDecisionService(sessions); err == nil {
		t.Error("a malformed DECISION_OWNER_ONLY_CATEGORIES built a service")
	}
}
