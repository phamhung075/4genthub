package entities

import (
	"strings"
	"testing"
)

// A ledger event whose payload carries no readable note must not render: an unreadable entry is not a
// note, and rendering it would leave a blank line a reader has to explain. This is the ledger-side
// half of the rule the deleted column reader followed (`2c4582de`: the decode boundary left an entry
// in a container the reader could not assert, and it answered with an empty note rather than a
// report).
func TestProgressTextWithSkipsALedgerEventWithNoReadableNote(t *testing.T) {
	task := &Task{}
	events := []*TaskEvent{
		{Kind: TaskEventKindProgress, Payload: map[string]any{"content": "2. a note from the ledger", "progress_number": float64(2)}},
		{Kind: TaskEventKindProgress, Payload: map[string]any{"content": float64(9), "progress_number": float64(9)}},
	}

	got := task.ProgressTextWith(events)
	if !strings.Contains(got, "2. a note from the ledger") {
		t.Errorf("the ledger's readable note is missing from %q", got)
	}
	// One readable note and nothing else: no separator, no leading or trailing blank entry.
	if strings.Contains(got, "\n\n") || strings.TrimSpace(got) != got {
		t.Errorf("an unreadable event left a blank entry in %q", got)
	}
}
