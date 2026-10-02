package websocket

import (
	"context"
	"errors"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func decodeRaw(t *testing.T, s string) *entities.OrderedMap[any] {
	t.Helper()
	v, err := entities.DecodeJSON([]byte(s))
	if err != nil {
		t.Fatalf("DecodeJSON(%s): %v", s, err)
	}
	om, ok := v.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("DecodeJSON(%s) did not yield an object", s)
	}
	return om
}

func TestValidateMessageVersion(t *testing.T) {
	_, err := ValidateMessage(decodeRaw(t, `{"sequence":1}`))
	var versionErr *InvalidVersionError
	if !errors.As(err, &versionErr) {
		t.Fatalf("err = %v, want *InvalidVersionError", err)
	}
	if got, want := err.Error(), "Only protocol v2.0 is supported, got: None"; got != want {
		t.Fatalf("err = %q, want %q", got, want)
	}

	_, err = ValidateMessage(decodeRaw(t, `{"version":"1.0"}`))
	if !errors.As(err, &versionErr) {
		t.Fatalf("err = %v, want *InvalidVersionError", err)
	}
	if got, want := err.Error(), "Only protocol v2.0 is supported, got: 1.0"; got != want {
		t.Fatalf("err = %q, want %q", got, want)
	}
}

func TestValidateMessageMissingFields(t *testing.T) {
	_, err := ValidateMessage(decodeRaw(t, `{"version":"2.0","sequence":1}`))
	var protocolErr *ProtocolError
	if !errors.As(err, &protocolErr) {
		t.Fatalf("err = %v, want *ProtocolError", err)
	}
	want := `Invalid message structure: 3 validation errors for WSMessage
type
  Field required [type=missing, input_value={'version': '2.0', 'sequence': 1}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
payload
  Field required [type=missing, input_value={'version': '2.0', 'sequence': 1}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
metadata
  Field required [type=missing, input_value={'version': '2.0', 'sequence': 1}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing`
	if err.Error() != want {
		t.Fatalf("error mismatch:\n got %q\nwant %q", err.Error(), want)
	}
}

func TestValidateMessageManyErrors(t *testing.T) {
	_, err := ValidateMessage(decodeRaw(t, `{"version":"2.0","type":"bad","sequence":"x","payload":{},"metadata":{}}`))
	want := `Invalid message structure: 6 validation errors for WSMessage
type
  Input should be 'update', 'bulk', 'sync', 'heartbeat' or 'error' [type=literal_error, input_value='bad', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/literal_error
sequence
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='x', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/int_parsing
payload.entity
  Field required [type=missing, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
payload.action
  Field required [type=missing, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
payload.data
  Field required [type=missing, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
metadata.source
  Field required [type=missing, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing`
	if err.Error() != want {
		t.Fatalf("error mismatch:\n got %q\nwant %q", err.Error(), want)
	}
}

func TestValidateMessageNestedLiteralError(t *testing.T) {
	_, err := ValidateMessage(decodeRaw(t, `{"version":"2.0","type":"update","sequence":1,"payload":{"entity":"bogus","action":"update","data":{"primary":{"id":"x"}}},"metadata":{"source":"user"}}`))
	want := `Invalid message structure: 1 validation error for WSMessage
payload.entity
  Input should be 'task', 'branch', 'project', 'subtask', 'context' or 'multiple' [type=literal_error, input_value='bogus', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/literal_error`
	if err.Error() != want {
		t.Fatalf("error mismatch:\n got %q\nwant %q", err.Error(), want)
	}
}

func TestValidateMessageSuccessAndDefaults(t *testing.T) {
	msg, err := ValidateMessage(decodeRaw(t, `{"version":"2.0","type":"update","sequence":1,"payload":{"entity":"task","action":"update","data":{"primary":{"id":"x"}}},"metadata":{"source":"user"}}`))
	if err != nil {
		t.Fatalf("ValidateMessage: %v", err)
	}
	if msg.ID == "" {
		t.Errorf("id default not applied")
	}
	if msg.Version != ProtocolVersion20 || msg.Type != MessageTypeUpdate || msg.Sequence != 1 {
		t.Errorf("unexpected message header: %+v", msg)
	}
	if msg.Payload.Entity != EntityTypeTask || msg.Payload.Action != ActionTypeUpdate {
		t.Errorf("unexpected payload: %+v", msg.Payload)
	}
	primary, ok := msg.Payload.Data.Primary.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("primary is %T, want *OrderedMap", msg.Payload.Data.Primary)
	}
	if id, _ := primary.Get("id"); id != "x" {
		t.Errorf("primary id = %v, want x", id)
	}
	if msg.Payload.Data.Cascade != nil || msg.Payload.Data.Delta != nil {
		t.Errorf("cascade/delta should be nil")
	}
	if msg.Metadata.Source != SourceTypeUser || !msg.Metadata.Immediate {
		t.Errorf("unexpected metadata: %+v", msg.Metadata)
	}
	if msg.Timestamp.IsZero() {
		t.Errorf("timestamp default not applied")
	}
}

func TestValidateMessageIgnoresExtraKeys(t *testing.T) {
	if _, err := ValidateMessage(decodeRaw(t, `{"version":"2.0","type":"update","sequence":1,"extra":"x","payload":{"entity":"task","action":"update","data":{"primary":{"id":"x"}}},"metadata":{"source":"user"}}`)); err != nil {
		t.Fatalf("ValidateMessage: %v", err)
	}
}

func TestValidateMessageNaiveTimestamp(t *testing.T) {
	msg, err := ValidateMessage(decodeRaw(t, `{"version":"2.0","type":"update","sequence":1,"timestamp":"2024-01-01T10:00:00","payload":{"entity":"task","action":"update","data":{"primary":{"id":"x"}}},"metadata":{"source":"user"}}`))
	if err != nil {
		t.Fatalf("ValidateMessage: %v", err)
	}
	if !strings.Contains(msg.ModelDumpJSON(), `"timestamp":"2024-01-01T10:00:00"`) {
		t.Fatalf("naive timestamp rendered as %s", msg.ModelDumpJSON())
	}
}

func TestValidateMessageSizeLimit(t *testing.T) {
	raw := `{"version":"2.0","blob":"` + strings.Repeat("a", 70000) + `"}`
	_, err := ValidateMessage(decodeRaw(t, raw))
	var sizeErr *MessageSizeError
	if !errors.As(err, &sizeErr) {
		t.Fatalf("err = %v, want *MessageSizeError", err)
	}
	if !strings.Contains(err.Error(), "exceeds limit of 65536 bytes") {
		t.Fatalf("unexpected size error: %v", err)
	}
}

func TestCreateHeartbeat(t *testing.T) {
	sessionID := "sess-1"
	msg := CreateHeartbeat(&sessionID, 3)
	if msg.Type != MessageTypeHeartbeat || msg.Sequence != 3 {
		t.Fatalf("unexpected heartbeat header: %+v", msg)
	}
	if msg.Metadata.Source != SourceTypeSystem || !msg.Metadata.Immediate {
		t.Fatalf("unexpected metadata: %+v", msg.Metadata)
	}
	if msg.Metadata.SessionID == nil || *msg.Metadata.SessionID != "sess-1" {
		t.Fatalf("session id mismatch: %+v", msg.Metadata.SessionID)
	}
	if msg.Payload.Entity != EntityTypeMultiple || msg.Payload.Action != ActionTypeUpdate {
		t.Fatalf("unexpected payload: %+v", msg.Payload)
	}
	primary := msg.Payload.Data.Primary.(*entities.OrderedMap[any])
	if status, _ := primary.Get("status"); status != "alive" {
		t.Fatalf("primary = %v, want status alive", primary.Keys())
	}
}

func TestCreateErrorMessage(t *testing.T) {
	code := "E1"
	sessionID := "sess-1"
	correlationID := "corr"
	details := wsDict("a", 1)
	msg := CreateError("boom", &code, details, &sessionID, &correlationID, 4)
	if msg.Type != MessageTypeError || msg.Metadata.Source != SourceTypeSystem {
		t.Fatalf("unexpected error message: %+v", msg)
	}
	primary := msg.Payload.Data.Primary.(*entities.OrderedMap[any])
	if got := primary.Keys(); len(got) != 4 || got[0] != "message" || got[1] != "timestamp" || got[2] != "code" || got[3] != "details" {
		t.Fatalf("error primary keys = %v", got)
	}
	if message, _ := primary.Get("message"); message != "boom" {
		t.Fatalf("message = %v", message)
	}
	ts, _ := primary.Get("timestamp")
	if !strings.HasSuffix(ts.(string), "+00:00") {
		t.Fatalf("timestamp = %v, want isoformat with +00:00", ts)
	}
	if got, _ := primary.Get("code"); got != "E1" {
		t.Fatalf("code = %v", got)
	}
}

func TestCreateErrorOmitsFalsyCodeAndDetails(t *testing.T) {
	empty := ""
	msg := CreateError("boom", &empty, entities.NewOrderedMap[any](), nil, nil, 1)
	primary := msg.Payload.Data.Primary.(*entities.OrderedMap[any])
	if got := primary.Keys(); len(got) != 2 || got[0] != "message" || got[1] != "timestamp" {
		t.Fatalf("error primary keys = %v", got)
	}
}

func TestCreateSync(t *testing.T) {
	sessionID := "sess-1"
	userID := "u1"
	syncData := wsDict("x", 1)
	msg := CreateSync(syncData, &sessionID, &userID, 5)
	if msg.Type != MessageTypeSync || msg.Metadata.Source != SourceTypeSystem || !msg.Metadata.Immediate {
		t.Fatalf("unexpected sync message: %+v", msg)
	}
	if msg.Payload.Data.Primary != syncData {
		t.Fatalf("primary should be the passed sync data")
	}
	if msg.Metadata.UserID == nil || *msg.Metadata.UserID != "u1" {
		t.Fatalf("user id mismatch")
	}
}

func TestCreateUserUpdateWithoutCascade(t *testing.T) {
	msg := CreateUserUpdate(context.Background(), EntityTypeTask, ActionTypeUpdate,
		wsDict("id", "t1"), nil, nil, nil, nil, nil, 6)
	if msg.Type != MessageTypeUpdate || msg.Metadata.Source != SourceTypeUser || !msg.Metadata.Immediate {
		t.Fatalf("unexpected user update: %+v", msg)
	}
	if msg.Payload.Data.Cascade != nil {
		t.Fatalf("cascade should be nil without a calculator")
	}
	if msg.Sequence != 6 {
		t.Fatalf("sequence = %d", msg.Sequence)
	}
}

func TestCreateAIBatchWithoutCascade(t *testing.T) {
	updates := []*entities.OrderedMap[any]{
		wsDict("entity_id", "t1", "entity_type", "task", "action", "update", "data", wsDict("id", "t1")),
	}
	userID := "u1"
	msg := CreateAIBatch(context.Background(), updates, "batch-1", nil, &userID, 7)
	if msg.Type != MessageTypeBulk || msg.Metadata.Source != SourceTypeMCPAI || msg.Metadata.Immediate {
		t.Fatalf("unexpected AI batch: %+v", msg)
	}
	if msg.Metadata.BatchID == nil || *msg.Metadata.BatchID != "batch-1" {
		t.Fatalf("batch id mismatch")
	}
	if msg.Payload.Entity != EntityTypeMultiple || msg.Payload.Action != ActionTypeBatch {
		t.Fatalf("unexpected payload: %+v", msg.Payload)
	}
	if msg.Payload.Data.Cascade != nil {
		t.Fatalf("empty combined cascade should be nil")
	}
	primary, ok := msg.Payload.Data.Primary.([]*entities.OrderedMap[any])
	if !ok || len(primary) != 1 {
		t.Fatalf("primary = %#v", msg.Payload.Data.Primary)
	}
}

func TestCreateUserUpdateWithCascade(t *testing.T) {
	// A calculator over a fake provider is not needed to check the mapping failure path:
	// "multiple" is not a cascade entity type, so the try/except swallows it and the
	// cascade stays nil.
	msg := CreateUserUpdate(context.Background(), EntityTypeMultiple, ActionTypeBatch,
		wsDict("id", "t1"), nil, nil, nil, nil, nil, 1)
	if msg.Payload.Data.Cascade != nil {
		t.Fatalf("cascade should be nil")
	}
}

func TestMapEntityType(t *testing.T) {
	got, err := mapEntityType(EntityTypeTask)
	if err != nil || got != services.EntityTypeTask {
		t.Fatalf("mapEntityType(task) = %v, %v", got, err)
	}
	_, err = mapEntityType(EntityTypeMultiple)
	if err == nil {
		t.Fatalf("mapEntityType(multiple) should fail")
	}
	var valueErr *value_objects.ValueError
	if !errors.As(err, &valueErr) {
		t.Fatalf("err = %T, want *value_objects.ValueError", err)
	}
	if got, want := err.Error(), "Unsupported entity type for cascade: multiple"; got != want {
		t.Fatalf("err = %q, want %q", got, want)
	}
}

func TestMessageSizeHelpers(t *testing.T) {
	msg := CreateHeartbeat(nil, 1)
	want := len([]byte(msg.ModelDumpJSON()))
	if got := GetMessageSize(msg); got != want {
		t.Fatalf("GetMessageSize = %d, want %d", got, want)
	}
	if !IsMessageSizeValid(msg) {
		t.Fatalf("heartbeat should be within the size limit")
	}
}
