package entities

import (
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/connection_management/domain/events"
	"agenthub/fastmcp/connection_management/domain/internal/testutil"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

var pinned = time.Date(2026, 3, 1, 10, 0, 0, 500000000, time.UTC)

func normEvents(evs []events.ConnectionEvent) any {
	out := []any{}
	for _, e := range evs {
		out = append(out, []any{e.Name(), testutil.Norm(e.ToDict())})
	}
	return out
}

func sec(f float64) time.Duration { return time.Duration(f * float64(time.Second)) }

func od(v any) *tmentities.OrderedMap[any] {
	m := tmentities.NewOrderedMap[any]()
	for _, p := range v.(map[string]any)["__od__"].([]any) {
		pp := p.([]any)
		m.Set(pp[0].(string), pp[1])
	}
	return m
}

func TestEntitiesMatchPython(t *testing.T) {
	Now = func() time.Time { return pinned }
	fx := testutil.Load(t, "testdata/entities_cases.json").(map[string]any)

	for _, c := range fx["conn"].([]any) {
		w := c.(map[string]any)
		in := w["in"].([]any)
		conn := NewConnection("c1", map[string]any{"agent": "x"}, pinned.Add(-sec(in[0].(float64))), pinned.Add(-sec(in[1].(float64))))
		conn.Status = in[2].(string)
		h, err := conn.DiagnoseHealth()
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(testutil.Norm(h.ToDict()), w["health"]) || !reflect.DeepEqual(normEvents(conn.GetEvents()), w["events"]) {
			t.Fatalf("conn %v:\n got %v\nwant %v", in, testutil.Norm(h.ToDict()), w["health"])
		}
		active := []any{conn.IsActive(30), conn.IsActive(1), conn.IsActive(0)}
		if !reflect.DeepEqual(active, w["active"]) || seconds(conn.GetIdleTime()) != w["idle"] || seconds(conn.GetConnectionDuration()) != w["dur"] {
			t.Fatalf("conn %v: active %v idle %v dur %v want %v", in, active, seconds(conn.GetIdleTime()), seconds(conn.GetConnectionDuration()), w)
		}
	}

	c := CreateConnection("n1", map[string]any{"a": 1})
	c.Disconnect()
	d := fx["disc"].([]any)
	if c.Status != d[0] || tmvo.IsoFormatNaive(c.LastActivity) != d[1] || float64(len(c.GetEvents())) != d[2] {
		t.Fatalf("disconnect %+v want %v", c, d)
	}
	c2 := CreateConnection("n2", map[string]any{})
	_, _ = c2.DiagnoseHealth()
	_, _ = c2.DiagnoseHealth()
	n2 := len(c2.GetEvents())
	c2.ClearEvents()
	if ev := fx["ev"].([]any); float64(n2) != ev[0] || float64(len(c2.GetEvents())) != ev[1] {
		t.Fatalf("events %d / %d want %v", n2, len(c2.GetEvents()), ev)
	}

	for i, sc := range fx["srv"].([]any) {
		w := sc.(map[string]any)
		restarts := []int{2, 0, 0, 0}[i] // the generator's restart counts
		off := w["off"].(float64)
		env := tmentities.NewOrderedMap[any]()
		env.Set("env", "dev")
		tm := tmentities.NewOrderedMap[any]()
		tm.Set("tm", true)
		s := &Server{Name: "srv", Version: "1.2.3", StartedAt: pinned.Add(-sec(off)), RestartCount: restarts, Environment: env, Authentication: od(w["auth"]), TaskManagement: tm}
		st, err := s.CheckHealth()
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(testutil.Norm(st.ToDict()), w["status"]) || !reflect.DeepEqual(normEvents(s.GetEvents()), w["events"]) {
			t.Fatalf("server %v:\n got %v\nwant %v", w["auth"], testutil.Norm(st.ToDict()), w["status"])
		}
		caps, cerr := s.GetCapabilities()
		want := w["caps"].(map[string]any)
		if cerr != nil || !reflect.DeepEqual(testutil.Norm(caps.ToDict()), want["ok"]) {
			t.Fatalf("caps %v: %v\n got %v\nwant %v", w["auth"], cerr, testutil.Norm(caps.ToDict()), want)
		}
	}

	s := CreateServer("n", "v", nil, nil, nil)
	s.Restart()
	r := fx["restart"].([]any)
	if float64(s.RestartCount) != r[0] || tmvo.IsoFormatNaive(s.StartedAt) != r[1] {
		t.Fatalf("restart %d %v want %v", s.RestartCount, s.StartedAt, r)
	}
}
