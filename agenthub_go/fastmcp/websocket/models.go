package websocket

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// naiveLocation is the sentinel location for a parsed naive datetime. pydantic renders
// a naive datetime with no UTC offset; a zero-offset fixed zone would render as "Z".
var naiveLocation = time.FixedZone("", 0)

// pydanticISO renders a datetime the way pydantic v2 does when serializing to JSON:
// UTC as "Z", a naive datetime with no offset, otherwise isoformat with the offset.
func pydanticISO(t time.Time) string {
	if t.Location() == naiveLocation {
		return value_objects.IsoFormatNaive(t)
	}
	if _, off := t.Zone(); off == 0 {
		return value_objects.IsoFormatNaive(t) + "Z"
	}
	return value_objects.IsoFormat(t)
}

// wsDict builds an OrderedMap from alternating key/value arguments.
func wsDict(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

// optString returns nil for a nil pointer, otherwise the pointed-to string (Python None).
func optString(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// anyList returns an empty list for a nil slice, matching Python's default_factory=list.
func anyList(v []any) []any {
	if v == nil {
		return []any{}
	}
	return v
}

// CascadeData contains all affected entities for a change.
type CascadeData struct {
	Branches []any
	Tasks    []any
	Projects []any
	Subtasks []any
	Contexts []any
}

// NewCascadeData builds cascade data with the Python default empty lists.
func NewCascadeData() *CascadeData {
	return &CascadeData{Branches: []any{}, Tasks: []any{}, Projects: []any{}, Subtasks: []any{}, Contexts: []any{}}
}

// GetTotalEntities is the total count of entities in the cascade data.
func (c *CascadeData) GetTotalEntities() int {
	return len(c.Branches) + len(c.Tasks) + len(c.Projects) + len(c.Subtasks) + len(c.Contexts)
}

// IsEmpty reports whether the cascade data contains no entities.
func (c *CascadeData) IsEmpty() bool { return c.GetTotalEntities() == 0 }

// ModelDump is pydantic's model_dump() in field-declaration order.
func (c *CascadeData) ModelDump() *entities.OrderedMap[any] {
	return wsDict(
		"branches", anyList(c.Branches),
		"tasks", anyList(c.Tasks),
		"projects", anyList(c.Projects),
		"subtasks", anyList(c.Subtasks),
		"contexts", anyList(c.Contexts),
	)
}

// WSData is the data payload with cascade and delta support. Primary holds either an
// *entities.OrderedMap[any] (dict) or []any (list of dicts).
type WSData struct {
	Primary any
	Cascade *CascadeData
	Delta   *entities.OrderedMap[any]
}

// ModelDump is pydantic's model_dump() in field-declaration order.
func (d *WSData) ModelDump() *entities.OrderedMap[any] {
	var cascade any
	if d.Cascade != nil {
		cascade = d.Cascade.ModelDump()
	}
	var delta any
	if d.Delta != nil {
		delta = d.Delta
	}
	return wsDict("primary", d.Primary, "cascade", cascade, "delta", delta)
}

// WSPayload defines the operation and data.
type WSPayload struct {
	Entity EntityType
	Action ActionType
	Data   *WSData
}

// ModelDump is pydantic's model_dump() in field-declaration order.
func (p *WSPayload) ModelDump() *entities.OrderedMap[any] {
	var data any
	if p.Data != nil {
		data = p.Data.ModelDump()
	}
	return wsDict("entity", p.Entity, "action", p.Action, "data", data)
}

// WSMetadata carries source tracking and correlation.
type WSMetadata struct {
	Source        SourceType
	UserID        *string
	SessionID     *string
	CorrelationID *string
	BatchID       *string
	Immediate     bool
}

// ModelDump is pydantic's model_dump() in field-declaration order.
func (m *WSMetadata) ModelDump() *entities.OrderedMap[any] {
	return wsDict(
		"source", m.Source,
		"user_id", optString(m.UserID),
		"session_id", optString(m.SessionID),
		"correlation_id", optString(m.CorrelationID),
		"batch_id", optString(m.BatchID),
		"immediate", m.Immediate,
	)
}

// WSMessage is the base WebSocket v2.0 message structure. The specialized message types
// (UserUpdateMessage, AIBatchMessage, ...) share this shape; their only difference in
// Python is the default `type` and the metadata source/immediate overrides applied by
// their __init__, which the constructors below reproduce.
type WSMessage struct {
	ID        string
	Version   ProtocolVersion
	Type      MessageType
	Timestamp time.Time
	Sequence  int
	Payload   *WSPayload
	Metadata  *WSMetadata
}

// Specialized message type names (Python subclasses with the same fields).
type (
	UserUpdateMessage = WSMessage
	AIBatchMessage    = WSMessage
	SystemMessage     = WSMessage
	HeartbeatMessage  = WSMessage
	ErrorMessage      = WSMessage
	SyncMessage       = WSMessage
)

// ModelDump is pydantic's model_dump() in field-declaration order. The datetime is
// rendered the way pydantic serializes it.
func (m *WSMessage) ModelDump() *entities.OrderedMap[any] {
	var payload any
	if m.Payload != nil {
		payload = m.Payload.ModelDump()
	}
	var metadata any
	if m.Metadata != nil {
		metadata = m.Metadata.ModelDump()
	}
	return wsDict(
		"id", m.ID,
		"version", m.Version,
		"type", m.Type,
		"timestamp", pydanticISO(m.Timestamp),
		"sequence", m.Sequence,
		"payload", payload,
		"metadata", metadata,
	)
}

// ModelDumpJSON is pydantic's model_dump_json(): compact JSON with no spaces. (pydantic
// leaves non-ASCII characters unescaped; PyJSONDumpsCompact escapes them, the one known
// difference.)
func (m *WSMessage) ModelDumpJSON() string {
	s, _ := value_objects.PyJSONDumpsCompact(m.ModelDump())
	return s
}

// nowUTC is datetime.now(UTC), truncated to microseconds like Python.
func nowUTC() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

func newWSMessage(typ MessageType, sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	return &WSMessage{
		ID: value_objects.NewUUIDv4(), Version: ProtocolVersion20, Type: typ,
		Timestamp: nowUTC(), Sequence: sequence, Payload: payload, Metadata: metadata,
	}
}

// NewUserUpdateMessage mirrors UserUpdateMessage: metadata source forced to "user" and
// immediate forced to true; type defaults to "update".
func NewUserUpdateMessage(typ MessageType, sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	if typ == "" {
		typ = MessageTypeUpdate
	}
	metadata.Source = SourceTypeUser
	metadata.Immediate = true
	return newWSMessage(typ, sequence, payload, metadata)
}

// NewAIBatchMessage mirrors AIBatchMessage: metadata source forced to "mcp-ai" and
// immediate forced to false; type defaults to "bulk".
func NewAIBatchMessage(typ MessageType, sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	if typ == "" {
		typ = MessageTypeBulk
	}
	metadata.Source = SourceTypeMCPAI
	metadata.Immediate = false
	return newWSMessage(typ, sequence, payload, metadata)
}

// NewSystemMessage mirrors SystemMessage: metadata source forced to "system".
func NewSystemMessage(typ MessageType, sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	metadata.Source = SourceTypeSystem
	return newWSMessage(typ, sequence, payload, metadata)
}

// NewHeartbeatMessage mirrors HeartbeatMessage (type "heartbeat").
func NewHeartbeatMessage(sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	return NewSystemMessage(MessageTypeHeartbeat, sequence, payload, metadata)
}

// NewErrorMessage mirrors ErrorMessage (type "error").
func NewErrorMessage(sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	return NewSystemMessage(MessageTypeError, sequence, payload, metadata)
}

// NewSyncMessage mirrors SyncMessage (type "sync").
func NewSyncMessage(sequence int, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	return NewSystemMessage(MessageTypeSync, sequence, payload, metadata)
}
