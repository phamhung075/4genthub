package websocket

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

func valueJSON(v any) (string, error) { return value_objects.PyJSONDumpsCompact(v) }

func TestPydanticISORendersLikePydantic(t *testing.T) {
	cases := []struct {
		name string
		when time.Time
		want string
	}{
		{"utc microseconds", time.Date(2024, 1, 1, 10, 0, 0, 123456000, time.UTC), "2024-01-01T10:00:00.123456Z"},
		{"utc no fraction", time.Date(2024, 1, 1, 10, 0, 0, 0, time.UTC), "2024-01-01T10:00:00Z"},
		{"naive", time.Date(2024, 1, 1, 10, 0, 0, 0, naiveLocation), "2024-01-01T10:00:00"},
		{"offset", time.Date(2024, 1, 1, 10, 0, 0, 123000000, time.FixedZone("", 2*3600)), "2024-01-01T10:00:00.123000+02:00"},
	}
	for _, c := range cases {
		if got := pydanticISO(c.when); got != c.want {
			t.Errorf("%s: pydanticISO = %q, want %q", c.name, got, c.want)
		}
	}
}

func TestWSMessageModelDumpJSON(t *testing.T) {
	msg := &WSMessage{
		ID:        "id-1",
		Version:   ProtocolVersion20,
		Type:      MessageTypeUpdate,
		Timestamp: time.Date(2026, 10, 1, 16, 49, 7, 199197000, time.UTC),
		Sequence:  1,
		Payload: &WSPayload{
			Entity: EntityTypeTask,
			Action: ActionTypeUpdate,
			Data:   &WSData{Primary: wsDict("id", "x")},
		},
		Metadata: &WSMetadata{Source: SourceTypeUser, Immediate: true},
	}
	want := `{"id":"id-1","version":"2.0","type":"update","timestamp":"2026-10-01T16:49:07.199197Z","sequence":1,` +
		`"payload":{"entity":"task","action":"update","data":{"primary":{"id":"x"},"cascade":null,"delta":null}},` +
		`"metadata":{"source":"user","user_id":null,"session_id":null,"correlation_id":null,"batch_id":null,"immediate":true}}`
	if got := msg.ModelDumpJSON(); got != want {
		t.Errorf("ModelDumpJSON mismatch:\n got %s\nwant %s", got, want)
	}
}

func TestWSMessageModelDumpFieldOrder(t *testing.T) {
	msg := &WSMessage{
		ID: "id-1", Version: ProtocolVersion20, Type: MessageTypeUpdate,
		Timestamp: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC), Sequence: 2,
		Payload:  &WSPayload{Entity: EntityTypeMultiple, Action: ActionTypeBatch, Data: &WSData{Primary: []any{}}},
		Metadata: &WSMetadata{Source: SourceTypeSystem, Immediate: true},
	}
	want := []string{"id", "version", "type", "timestamp", "sequence", "payload", "metadata"}
	got := msg.ModelDump().Keys()
	if len(got) != len(want) {
		t.Fatalf("keys = %v, want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("keys = %v, want %v", got, want)
		}
	}
}

func TestCascadeData(t *testing.T) {
	c := NewCascadeData()
	if !c.IsEmpty() || c.GetTotalEntities() != 0 {
		t.Fatalf("new cascade data should be empty")
	}
	c.Branches = []any{wsDict("id", "b1")}
	c.Tasks = []any{wsDict("id", "t1"), wsDict("id", "t2")}
	if c.IsEmpty() {
		t.Fatalf("cascade data should not be empty")
	}
	if got := c.GetTotalEntities(); got != 3 {
		t.Fatalf("GetTotalEntities = %d, want 3", got)
	}
	wantKeys := []string{"branches", "tasks", "projects", "subtasks", "contexts"}
	got := c.ModelDump().Keys()
	for i := range wantKeys {
		if got[i] != wantKeys[i] {
			t.Fatalf("cascade ModelDump keys = %v, want %v", got, wantKeys)
		}
	}
}

func TestEmptyCascadeDataDumpsEmptyLists(t *testing.T) {
	c := &CascadeData{}
	got, err := valueJSON(c.ModelDump())
	if err != nil {
		t.Fatalf("dumps: %v", err)
	}
	want := `{"branches":[],"tasks":[],"projects":[],"subtasks":[],"contexts":[]}`
	if got != want {
		t.Fatalf("empty cascade JSON = %s, want %s", got, want)
	}
}
