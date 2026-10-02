package value_objects

import (
	"math"
	"testing"
	"time"
)

func TestVisionMetricProgress(t *testing.T) {
	m := NewVisionMetric("m", 5, 10, "x")
	if m.ProgressPercentage() != 50 || m.IsAchieved() {
		t.Fatal(m.ProgressPercentage())
	}
	m.BaselineValue, m.CurrentValue = 10, 12
	if m.ProgressPercentage() != 100 { // target == baseline, current >= target
		t.Fatal(m.ProgressPercentage())
	}
	m.CurrentValue = -5
	m.BaselineValue = 0
	if m.ProgressPercentage() != 0 {
		t.Fatal("clamped low")
	}
}

func TestVisionObjectiveDaysAndCompletion(t *testing.T) {
	o := NewVisionObjective()
	if o.IsCompleted() || o.OverallProgress() != 0 {
		t.Fatal("empty objective")
	}
	if _, ok := o.DaysRemaining(); ok {
		t.Fatal("no due date")
	}
	past := now().Add(-48 * time.Hour)
	o.DueDate = &past
	if d, _ := o.DaysRemaining(); d != 0 {
		t.Fatal(d)
	}
	future := now().Add(72*time.Hour + time.Minute)
	o.DueDate = &future
	if d, _ := o.DaysRemaining(); d != 3 {
		t.Fatal(d)
	}
	if pyDays(-time.Hour) != -1 || pyDays(25*time.Hour) != 1 {
		t.Fatal("floor semantics")
	}
}

func TestVisionInsightUrgency(t *testing.T) {
	i := NewVisionInsight()
	i.Impact = "high"
	if i.UrgencyScore() != 0.75 {
		t.Fatal(i.UrgencyScore())
	}
	soon := now().Add(12 * time.Hour)
	i.ExpiresAt = &soon
	if i.UrgencyScore() != 1.0 { // 0.75*1.5 capped
		t.Fatal(i.UrgencyScore())
	}
	week := now().Add(5*24*time.Hour + time.Hour)
	i.ExpiresAt = &week
	if got := i.UrgencyScore(); math.Abs(got-0.9) > 1e-9 {
		t.Fatal(got)
	}
	if a := NewVisionAlignment("t", "o", 0.7, ContributionTypeDirect); !a.IsStrongAlignment() || a.IsWeakAlignment() || a.Confidence != 0.8 {
		t.Fatal(a)
	}
}
