package database_test

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
	"time"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type entity struct{ created, updated *time.Time }

func (e *entity) GetCreatedAt() *time.Time  { return e.created }
func (e *entity) SetCreatedAt(t *time.Time) { e.created = t }
func (e *entity) GetUpdatedAt() *time.Time  { return e.updated }
func (e *entity) SetUpdatedAt(t *time.Time) { e.updated = t }
func (e *entity) Touch()                    {}

type noTouch struct{ created, updated *time.Time }

func parse(t *testing.T, s *string) *time.Time {
	if s == nil {
		return nil
	}
	tm, err := tmvo.ParseISO(*s)
	if err != nil {
		t.Fatal(err)
	}
	return &tm
}

func iso(t *time.Time) any {
	if t == nil {
		return nil
	}
	s := tmvo.IsoFormat(*t)
	if !strings.HasPrefix(s, "1999-") {
		return "<ts>"
	}
	return s
}

func TestTimestampHandlersParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/ts_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		Created, Updated *string
		Kind, Handler    string
		Out              [2]any
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for i, c := range cases {
		var target any
		var e *entity
		if c.Kind == "ent" {
			e = &entity{parse(t, c.Created), parse(t, c.Updated)}
			target = e
		} else {
			target = &noTouch{parse(t, c.Created), parse(t, c.Updated)}
		}
		if c.Handler == "insert" {
			database.BeforeInsertTimestamps(target)
		} else {
			database.BeforeUpdateTimestamps(target)
		}
		var got [2]any
		if e != nil {
			got = [2]any{iso(e.created), iso(e.updated)}
		} else {
			nt := target.(*noTouch)
			got = [2]any{iso(nt.created), iso(nt.updated)}
		}
		want := c.Out
		if c.Kind == "notouch" { // untouched: a naive input stays as given (read as UTC in Go)
			for j, v := range want {
				if str, ok := v.(string); ok && str != "<ts>" {
					want[j] = iso(parse(t, &str))
				}
			}
		}
		if got != want {
			t.Fatalf("case %d %+v: got %v want %v", i, c, got, want)
		}
	}
}

func TestTimestampEventsRegistration(t *testing.T) {
	database.SetupTimestampEvents()
	if !database.TimestampEventsActive() {
		t.Fatal("not active after setup")
	}
	database.CleanupTimestampEvents()
	if database.TimestampEventsActive() {
		t.Fatal("active after cleanup")
	}
}
