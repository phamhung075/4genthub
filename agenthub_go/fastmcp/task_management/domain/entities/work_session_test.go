package entities

import (
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestPyTimedeltaStr(t *testing.T) {
	for want, d := range map[string]time.Duration{
		"0:00:00": 0, "1:02:03": time.Hour + 2*time.Minute + 3*time.Second,
		"1 day, 2:03:04.456789": 26*time.Hour + 3*time.Minute + 4*time.Second + 456789*time.Microsecond,
		"-1 day, 23:00:00":      -time.Hour, "2 days, 0:00:00": 48 * time.Hour, "0:00:00.500000": 500 * time.Millisecond,
	} {
		if got := value_objects.PyTimedeltaStr(d); got != want {
			t.Errorf("%v: got %q want %q", d, got, want)
		}
	}
}

func TestWorkSessionLifecycle(t *testing.T) {
	s, err := CreateWorkSession("a1", "t1", "main", 1.5)
	if err != nil || !strings.HasPrefix(s.ID, "a1_t1_") || *s.MaxDuration != 90*time.Minute || len(s.ProgressUpdates) != 1 {
		t.Fatal(s, err)
	}
	if err := s.ResumeSession(); err == nil || err.Error() != "Cannot resume session in active state" {
		t.Fatal(err)
	}
	if err := s.PauseSession("lunch"); err != nil || s.Status != SessionStatusPaused || s.PausedAt == nil {
		t.Fatal(err)
	}
	time.Sleep(3 * time.Millisecond)
	if err := s.ResumeSession(); err != nil || s.TotalPausedDuration <= 0 || s.PausedAt != nil {
		t.Fatal(err)
	}
	s.LockResource("r1")
	s.LockResource("r1")
	if len(s.ResourcesLocked) != 1 {
		t.Fatal("lock idempotent")
	}
	s.UnlockAllResources()
	if err := s.CompleteSession(false, "n"); err != nil || !strings.Contains(s.SessionNotes, "Completion notes: n") {
		t.Fatal(err)
	}
	last := s.ProgressUpdates[len(s.ProgressUpdates)-1]
	if last["message"] != "Session completed (unsuccessful)" {
		t.Fatal(last)
	}
	sum := s.GetSessionSummary()
	if sum["status"] != "completed" || sum["configuration"].(map[string]any)["max_duration"] != "1:30:00" {
		t.Fatal(sum)
	}
	if err := s.PauseSession(""); err == nil || err.Error() != "Cannot pause session in completed state" {
		t.Fatal(err)
	}
}

func TestWorkSessionValidation(t *testing.T) {
	now := time.Now()
	for want, ws := range map[string]WorkSession{
		"WorkSession id cannot be empty":              {AgentID: "a", TaskID: "t", GitBranchName: "b", StartedAt: &now},
		"WorkSession started_at cannot be None":       {ID: "i", AgentID: "a", TaskID: "t", GitBranchName: "b"},
		"WorkSession git_branch_name cannot be empty": {ID: "i", AgentID: "a", TaskID: "t", StartedAt: &now},
	} {
		if _, err := NewWorkSession(ws); err == nil || err.Error() != want {
			t.Errorf("want %q got %v", want, err)
		}
	}
}
