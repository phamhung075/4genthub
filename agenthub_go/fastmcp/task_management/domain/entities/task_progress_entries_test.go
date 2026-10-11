package entities

import (
	"strings"
	"testing"
)

// The column reader must not invent a note out of a value it cannot read, and the reason is not
// tidiness: an invented entry carries the empty string under number 0, which renders as a blank line
// AND claims that identity in ProgressTextWith, where the merge uses it to drop the ledger's own copy
// of a note. The two discards this case exists for are the pattern that hid the original defect
// (`2c4582de`: the decode boundary left each entry in a container the reader could not assert, and the
// reader answered with an empty note rather than a report).
func TestProgressEntriesSkipAValueThatIsNotANote(t *testing.T) {
	task := &Task{ProgressHistory: map[string]any{
		"progress_1": map[string]any{"content": "1. a real note", "progress_number": float64(1)},
		"progress_2": "not an object at all",
		"progress_3": map[string]any{"content": float64(7), "progress_number": float64(3)},
		"progress_4": map[string]any{"progress_number": float64(4)},
	}}

	entries := task.ProgressEntries()
	if len(entries) != 1 {
		t.Fatalf("read %d notes from a column holding one note and three unreadable values: %+v", len(entries), entries)
	}
	if entries[0].Content != "1. a real note" || entries[0].Number != 1 {
		t.Fatalf("the readable note came back as %+v", entries[0])
	}
	if got := task.GetProgressHistoryText(); got != "1. a real note" {
		t.Errorf("the joined text is %q, want the one note with no blank lines from the others", got)
	}
}

// The same rule on the other side of the merge, and the case that shows WHY the invented entry
// mattered: a ledger event whose payload carries no readable note must not render either, and it must
// not be able to suppress a real ledger note by claiming an identity.
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
