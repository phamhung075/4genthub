package value_objects

import (
	"testing"
	"time"
)

func TestProgressTimeline(t *testing.T) {
	tl := NewProgressTimeline("t")
	base := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	mk := func(pt ProgressType, pct float64, off int) ProgressSnapshot {
		s, err := NewProgressSnapshot(ProgressSnapshot{TaskID: "t", ProgressType: pt, Percentage: pct, Timestamp: base.Add(time.Duration(off) * time.Hour)})
		if err != nil {
			t.Fatal(err)
		}
		return s
	}
	for _, s := range []ProgressSnapshot{mk(ProgressTypeDesign, 10, 2), mk(ProgressTypeDesign, 50, 3), mk(ProgressTypeTesting, 30, 1)} {
		if err := tl.AddSnapshot(s); err != nil {
			t.Fatal(err)
		}
	}
	if got := tl.GetOverallProgress(); got != 40 { // (50+30)/2
		t.Fatal(got)
	}
	if last, _ := tl.GetLatestSnapshot(); last.Percentage != 50 {
		t.Fatal(last)
	}
	if err := tl.AddMilestone("m", 101); err == nil || err.Error() != "Milestone percentage must be between 0 and 100, got 101.0" {
		t.Fatal(err)
	}
	tl.AddMilestone("half", 40)
	if !tl.IsMilestoneReached("half") || tl.IsMilestoneReached("nope") {
		t.Fatal("milestones")
	}
	if err := tl.AddSnapshot(ProgressSnapshot{TaskID: "x"}); err == nil || err.Error() != "Snapshot task_id x doesn't match timeline task_id t" {
		t.Fatal(err)
	}
}

func TestSnapshotRoundTrip(t *testing.T) {
	s, err := NewProgressSnapshot(ProgressSnapshot{TaskID: "t", Percentage: 12.5, Timestamp: time.Date(2026, 1, 1, 1, 2, 3, 456000000, time.UTC)})
	if err != nil {
		t.Fatal(err)
	}
	d := s.ToDict()
	if d["timestamp"] != "2026-01-01T01:02:03.456000+00:00" || d["progress_type"] != "general" || d["status"] != "not_started" {
		t.Fatal(d)
	}
	back, err := ProgressSnapshotFromDict(d)
	if err != nil || !back.Timestamp.Equal(s.Timestamp) || back.Percentage != 12.5 || back.ID != s.ID {
		t.Fatal(back, err)
	}
	if _, err := ProgressSnapshotFromDict(map[string]any{"progress_type": "bogus"}); err == nil || err.Error() != "'bogus' is not a valid ProgressType" {
		t.Fatal(err)
	}
}

func TestProgressStrategies(t *testing.T) {
	var s ProgressCalculationStrategy
	if got := s.CalculateWeightedAverage([]KeyedProgress{{"a", 100}, {"b", 0}}, map[string]float64{"a": 3}); got != 75 {
		t.Fatal(got)
	}
	subs := []map[string]any{{"status": "blocked", "progress": 0.0}, {"status": "done", "progress": 100.0}, {"progress": 50}}
	if got := s.CalculateFromSubtasks(subs, false); got != 75 {
		t.Fatal(got)
	}
	if got := s.CalculateByMilestones([]string{"a", "zz"}, map[string]float64{"a": 25, "b": 50}); got != 25 {
		t.Fatal(got)
	}
}
