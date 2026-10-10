package value_objects

import (
	"testing"
	"time"
)

func TestIsoformat(t *testing.T) {
	a := time.Date(2026, 9, 30, 21, 14, 50, 709000000, time.UTC)
	b := time.Date(2026, 9, 30, 21, 14, 50, 0, time.UTC)
	if IsoFormat(a) != "2026-09-30T21:14:50.709000+00:00" || IsoFormat(b) != "2026-09-30T21:14:50+00:00" {
		t.Fatal(IsoFormat(a), IsoFormat(b))
	}
	est := time.FixedZone("x", -5*3600-30*60)
	if got := IsoFormat(time.Date(2026, 1, 2, 3, 4, 5, 0, est)); got != "2026-01-02T03:04:05-05:30" {
		t.Fatal(got)
	}
}

func TestWorkHandoffStateMachine(t *testing.T) {
	h := NewWorkHandoff("h", "a", "b", "t", time.Now())
	if err := h.Complete(); err == nil || err.Error() != "Cannot complete handoff in status HandoffStatus.PENDING" {
		t.Fatal(err)
	}
	if err := h.Accept(); err != nil || h.AcceptedAt == nil {
		t.Fatal(err)
	}
	if err := h.Reject("no"); err == nil || err.Error() != "Cannot reject handoff in status HandoffStatus.ACCEPTED" {
		t.Fatal(err)
	}
}

func TestHints(t *testing.T) {
	md := func(c float64) HintMetadata { m, _ := NewHintMetadata("s", c, "r", nil, nil, nil); return m }
	if _, err := NewHintMetadata("s", 1.5, "r", nil, nil, nil); err == nil || err.Error() != "Confidence must be between 0.0 and 1.0" {
		t.Fatal(err)
	}
	c := &HintCollection{TaskID: "t"}
	past := time.Now().Add(-time.Hour)
	for _, h := range []WorkflowHint{
		CreateWorkflowHint("t", HintTypeOptimization, HintPriorityLow, "low", "", md(0.9), nil, nil),
		CreateWorkflowHint("t", HintTypeCompletion, HintPriorityHigh, "high-lo", "", md(0.2), nil, nil),
		CreateWorkflowHint("t", HintTypeCompletion, HintPriorityHigh, "high-hi", "", md(0.8), nil, nil),
		CreateWorkflowHint("t", HintTypeNextAction, HintPriorityCritical, "expired", "", md(1), nil, &past),
	} {
		if err := c.AddHint(h); err != nil {
			t.Fatal(err)
		}
	}
	if err := c.AddHint(CreateWorkflowHint("other", HintTypeCompletion, HintPriorityLow, "", "", md(0), nil, nil)); err == nil {
		t.Fatal("task mismatch should fail")
	}
	top := c.GetTopHints(2)
	if len(top) != 2 || top[0].Message != "high-hi" || top[1].Message != "high-lo" {
		t.Fatal(top)
	}
	if c.RemoveExpiredHints() != 1 || c.ClearHintsByType(HintTypeCompletion) != 2 || len(c.Hints) != 1 {
		t.Fatal("removal counts")
	}
}

func TestGetTopHintsNegativeLimit(t *testing.T) {
	c := &HintCollection{TaskID: "t"}
	m, _ := NewHintMetadata("s", 0.5, "r", nil, nil, nil)
	for _, msg := range []string{"a", "b", "c"} {
		c.AddHint(CreateWorkflowHint("t", HintTypeCompletion, HintPriorityHigh, msg, "", m, nil, nil))
	}
	if got := c.GetTopHints(-1); len(got) != 2 { // Python [:-1]
		t.Fatal(len(got))
	}
	if got := c.GetTopHints(-10); len(got) != 0 || len(c.GetTopHints(10)) != 3 {
		t.Fatal("clamping")
	}
}
