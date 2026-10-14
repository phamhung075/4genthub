package services

import (
	"context"
	"encoding/json"
	"errors"
	"path/filepath"
	"testing"

	"agenthub/fastmcp/room_decisions/domain/decisions"
)

var ladderQuestions = json.RawMessage(`[{"id":"q1","question":"Which db?","options":[
	{"id":"opt_pg","label":"PostgreSQL","recommended":true},{"id":"opt_sqlite","label":"SQLite"}]}]`)

func ladderService(t *testing.T, eval *fakeDecisionEvaluator) *RoomDecisionService {
	t.Helper()
	SetJevDecisionLogPath(filepath.Join(t.TempDir(), "jev_decisions.log"))
	t.Cleanup(func() { SetJevDecisionLogPath("") })
	return NewRoomDecisionService(&fakeRoomDecisionStore{}).WithEvaluator(eval, "jev-1.13.0", 0.8)
}

func TestEvaluateLadder(t *testing.T) {
	ctx := context.Background()
	pick := func(conf float64) *fakeDecisionEvaluator {
		return &fakeDecisionEvaluator{selections: map[string]DecisionChoiceSelection{"q1": {SelectedOptionID: "opt_pg", Confidence: conf}}}
	}

	t.Run("seat_at_0.9_decides_without_reaching_the_lead", func(t *testing.T) {
		out, err := ladderService(t, pick(0.9)).Evaluate(ctx, decisions.TierSeat, decisions.CategoryGeneral, "db", "pick", ladderQuestions, serviceTestNow)
		if err != nil || !out.Decided || out.Answers["q1"] != "opt_pg" || out.EscalateTo != "" {
			t.Fatalf("outcome = %+v, err = %v; want decided opt_pg, no escalation", out, err)
		}
	})
	t.Run("seat_at_0.6_escalates_one_level_with_the_recommendation", func(t *testing.T) {
		out, err := ladderService(t, pick(0.6)).Evaluate(ctx, decisions.TierSeat, decisions.CategoryGeneral, "db", "pick", ladderQuestions, serviceTestNow)
		if err != nil || out.Decided || out.EscalateTo != decisions.TierLead || out.Questions[0].Recommended != "opt_pg" {
			t.Fatalf("outcome = %+v, err = %v; want escalate to lead carrying opt_pg", out, err)
		}
	})
	t.Run("lead_below_threshold_escalates_to_the_owner", func(t *testing.T) {
		out, err := ladderService(t, pick(0.79)).Evaluate(ctx, decisions.TierLead, decisions.CategoryGeneral, "db", "pick", ladderQuestions, serviceTestNow)
		if err != nil || out.Decided || out.EscalateTo != decisions.TierOwner {
			t.Fatalf("outcome = %+v, err = %v; want escalate to owner", out, err)
		}
	})
	t.Run("credential_question_at_0.95_still_reaches_the_owner_without_asking_jev", func(t *testing.T) {
		eval := pick(0.95)
		eval.err = errors.New("must not be called")
		out, err := ladderService(t, eval).Evaluate(ctx, decisions.TierSeat, "credentials", "token", "rotate", ladderQuestions, serviceTestNow)
		if err != nil || out.Decided || out.EscalateTo != decisions.TierOwner {
			t.Fatalf("outcome = %+v, err = %v; want owner from the seat tier", out, err)
		}
	})
	t.Run("evaluator_error_escalates_instead_of_deciding", func(t *testing.T) {
		out, err := ladderService(t, &fakeDecisionEvaluator{err: errors.New("down")}).Evaluate(ctx, decisions.TierSeat, decisions.CategoryGeneral, "db", "pick", ladderQuestions, serviceTestNow)
		if err != nil || out.Decided || out.EscalateTo != decisions.TierLead {
			t.Fatalf("outcome = %+v, err = %v; want escalate to lead", out, err)
		}
	})
	t.Run("owner_tier_is_refused", func(t *testing.T) {
		if _, err := ladderService(t, pick(0.9)).Evaluate(ctx, decisions.TierOwner, decisions.CategoryGeneral, "db", "pick", ladderQuestions, serviceTestNow); err == nil {
			t.Fatal("tier owner was accepted")
		}
	})
}

func TestOwnerOnlyCategoriesAreConfigurableNotFixed(t *testing.T) {
	set, err := decisions.ParseOwnerOnly("omp_cap, Deploy-Prod")
	if err != nil {
		t.Fatal(err)
	}
	for _, c := range []decisions.Category{"credentials", "spend", "omp_cap", "deploy-prod"} {
		if !set.Has(c) {
			t.Errorf("%s is not owner-only", c)
		}
	}
	if set.Has("general") {
		t.Error("general is owner-only")
	}
	if defaults, _ := decisions.ParseOwnerOnly(""); defaults.Has("omp_cap") {
		t.Error("omp_cap is built into the defaults; it is this project's configuration")
	}
	if _, err := decisions.ParseCategory("has space"); err == nil {
		t.Error("a malformed category was accepted")
	}
}
