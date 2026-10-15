package httpapp

// The startup half of the sweep's environment contract, at the seam main.go calls: a malformed
// interval must refuse to COMPOSE, which is what makes `log.Fatalf("task lifecycle sweeper: %v")` in
// cmd/agenthub/main.go fire before the server binds (the guide's "malformed ones fail startup").
//
// It needs no database on purpose: the schedule is read BEFORE anything is reached, and passing a nil
// session manager is what proves it - a composition that touched the database first would panic here
// instead of returning the error the operator has to see.

import (
	"context"
	"strings"
	"testing"
)

func TestNewTaskLifecycleSweeperRefusesAMalformedInterval(t *testing.T) {
	t.Setenv("TASK_SWEEP_INTERVAL", "hour")

	sweeper, err := NewTaskLifecycleSweeper(context.Background(), nil)
	if err == nil {
		t.Fatal("a malformed TASK_SWEEP_INTERVAL was accepted: the process would start on a schedule nobody chose")
	}
	if sweeper != nil {
		t.Fatal("a refused composition returned a sweeper, so the caller could start it anyway")
	}
	if !strings.Contains(err.Error(), "TASK_SWEEP_INTERVAL") {
		t.Fatalf("the error does not name the variable the operator has to fix: %v", err)
	}
}

// TestNewTaskLifecycleSweeperComposesOnTheDocumentedDefaults is the other half of the same seam: with
// no TASK_* variable set, the composition builds - so the defaults are what a deployment that sets
// nothing really runs on, rather than only what the config function returns.
func TestNewTaskLifecycleSweeperComposesOnTheDocumentedDefaults(t *testing.T) {
	for _, key := range []string{"TASK_SWEEP_INTERVAL", "TASK_PRUNE_AFTER", "TASK_ESCALATE_AFTER", "TASK_BLOCK_AFTER"} {
		t.Setenv(key, "")
	}

	sweeper, err := NewTaskLifecycleSweeper(context.Background(), nil)
	if err != nil {
		t.Fatalf("an unset schedule must compose: %v", err)
	}
	if sweeper == nil {
		t.Fatal("an unset schedule composed no sweeper")
	}
}
