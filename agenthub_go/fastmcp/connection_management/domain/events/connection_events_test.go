package events

import (
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/connection_management/domain/internal/testutil"
)

func TestConnectionEventsMatchPython(t *testing.T) {
	ts := time.Date(2026, 3, 1, 9, 30, 15, 250000000, time.UTC)
	evs := []ConnectionEvent{
		ServerHealthChecked{ts, "srv", "healthy", 12.5},
		ConnectionHealthChecked{ts, "c1", "unhealthy", 3700.25},
		StatusUpdateRequested{ts, "s1", "full"},
		ClientRegisteredForUpdates{ts, "s1", map[string]any{"a": 1, "b": "x"}},
		ServerCapabilitiesRequested{ts, "s2"},
		StatusUpdateBroadcasted{ts, "connection_lost", "s1", map[string]any{"connection_id": "c9"}},
		ClientRegistered{ts, "s1", map[string]any{"k": "v"}},
		ClientUnregistered{ts, "s1", "timeout"},
	}
	cases := testutil.Load(t, "testdata/events_cases.json").([]any)
	if len(cases) != len(evs) {
		t.Fatalf("%d cases", len(cases))
	}
	for i, e := range evs {
		row := cases[i].([]any)
		if e.Name() != row[0] || !reflect.DeepEqual(testutil.Norm(e.ToDict()), row[1]) {
			t.Fatalf("%s:\n got %v\nwant %v", e.Name(), testutil.Norm(e.ToDict()), row[1])
		}
	}
}
