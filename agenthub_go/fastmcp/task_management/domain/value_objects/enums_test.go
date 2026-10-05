package value_objects

import "testing"

func TestContextLevel(t *testing.T) {
	l, err := ContextLevelFromString("BRANCH")
	if err != nil || l != ContextLevelBranch {
		t.Fatal(l, err)
	}
	p, ok := l.GetParentLevel()
	if !ok || p != ContextLevelProject {
		t.Fatal(p, ok)
	}
	if _, ok := ContextLevelGlobal.GetParentLevel(); ok {
		t.Fatal("global has no parent")
	}
	_, err = ContextLevelFromString("x")
	if err == nil || err.Error() != "Invalid context level: x. Valid levels are: global, project, branch, task" {
		t.Fatal(err)
	}
}

func TestProgressState(t *testing.T) {
	if ProgressStateFromProgressPercentage(50) != ProgressStateInProgress || ProgressStateFromTaskStatus("Finished") != ProgressStateComplete {
		t.Fatal("mapping")
	}
	if !IsValidProgressState("complete") || IsValidProgressState("nope") {
		t.Fatal("validity")
	}
	if ProgressStateInProgress.GetVisualIndicator() != "◐" || ProgressStateComplete.GetStepNumber() != 3 {
		t.Fatal("stepper")
	}
}

func TestRuleEnums(t *testing.T) {
	if !RuleFormatIsValidFormat("MDC") || RuleFormatIsValidFormat("pdf") {
		t.Fatal("format")
	}
	if !SyncStatusCompleted.IsTerminal() || !SyncStatusPending.IsActive() || SyncStatusConflict.IsActive() {
		t.Fatal("sync status")
	}
}

func TestEstimatedEffort(t *testing.T) {
	cases := []struct {
		in    string
		hours float64
		level string
	}{
		{"quick", 0.25, "quick"}, {"2h", 2, "medium"}, {"1h 30m", 1.5, "medium"},
		{"45m", 0.75, "small"}, {"3 hours", 3, "large"}, {"30 minutes", 0.5, "short"}, {"100h", 100, "massive"},
	}
	for _, c := range cases {
		e, err := NewEstimatedEffort(c.in)
		h, ok := e.GetHours()
		if err != nil || !ok || h != c.hours || e.GetLevel() != c.level {
			t.Errorf("%q: %v %v %v %q", c.in, err, h, ok, e.GetLevel())
		}
	}
	if _, err := NewEstimatedEffort("soon"); err == nil {
		t.Error("expected error")
	}
	if e, err := NewEstimatedEffort(""); err != nil || e.GetLevel() != "medium" {
		t.Error("empty allowed")
	}
	if EstimatedEffortFromHours(3).Value != "medium" { // |2-3| == |4-3|, first wins
		t.Error("tie-break")
	}
}
