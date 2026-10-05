package entities

import (
	"testing"
	"time"
)

func TestLabelValidationAndTimestamps(t *testing.T) {
	l, err := NewLabel(7, "bug", "", "d", nil, nil)
	if err != nil || l.Color != "#0066cc" || l.CreatedAt == nil || !l.UpdatedAt.Equal(*l.CreatedAt) {
		t.Fatal(l, err)
	}
	if evs := l.GetDomainEvents(); len(evs) != 1 || evs[0].EventType() != "timestamp_created" {
		t.Fatal(evs)
	}
	if _, err := NewLabel(1, "  ", "", "", nil, nil); err == nil || err.Error() != "Label name cannot be empty" {
		t.Fatal(err)
	}
	if _, err := NewLabel(1, "x", "#12", "", nil, nil); err == nil || err.Error() != "Invalid color format: #12. Expected hex color (e.g., #ff0000)" {
		t.Fatal(err)
	}
	if _, err := NewLabel(1, "x", "#abc", "", nil, nil); err != nil {
		t.Fatal(err)
	}
	if l.GetEntityID() != "7" || l.String() != "Label(bug)" {
		t.Fatal(l.GetEntityID())
	}
}

func TestTouchAndOrdering(t *testing.T) {
	l, _ := NewLabel(0, "x", "", "", nil, nil)
	if l.GetEntityID() != "unknown" {
		t.Fatal("unknown id")
	}
	before := *l.UpdatedAt
	time.Sleep(2 * time.Millisecond)
	if err := l.Touch("r"); err != nil || !l.UpdatedAt.After(before) {
		t.Fatal(err)
	}
	evs := l.GetDomainEvents()
	if len(evs) != 2 || evs[1].EventType() != "timestamp_updated" || evs[1].ToDict()["old_timestamp"] == nil {
		t.Fatal(evs)
	}
	l.ClearDomainEvents()
	if len(l.GetDomainEvents()) != 0 {
		t.Fatal("clear")
	}
	later := time.Now().Add(-time.Hour)
	if _, err := NewLabel(1, "x", "", "", &later, &time.Time{}); err == nil {
		t.Fatal("updated before created must fail")
	}
}
