// Package websocket ports fastmcp/websocket (WebSocket Protocol v2.0).
package websocket

// MessageType is the WebSocket Protocol v2.0 message type literal.
type MessageType string

const (
	MessageTypeUpdate    MessageType = "update"
	MessageTypeBulk      MessageType = "bulk"
	MessageTypeSync      MessageType = "sync"
	MessageTypeHeartbeat MessageType = "heartbeat"
	MessageTypeError     MessageType = "error"
)

// MessageTypeValues lists the literal members in declaration order.
var MessageTypeValues = []MessageType{MessageTypeUpdate, MessageTypeBulk, MessageTypeSync, MessageTypeHeartbeat, MessageTypeError}

// EntityType is the WebSocket Protocol v2.0 entity type literal. It is distinct from
// the cascade calculator's EntityType (types.py declares its own).
type EntityType string

const (
	EntityTypeTask     EntityType = "task"
	EntityTypeBranch   EntityType = "branch"
	EntityTypeProject  EntityType = "project"
	EntityTypeSubtask  EntityType = "subtask"
	EntityTypeContext  EntityType = "context"
	EntityTypeMultiple EntityType = "multiple"
)

// EntityTypeValues lists the literal members in declaration order.
var EntityTypeValues = []EntityType{EntityTypeTask, EntityTypeBranch, EntityTypeProject, EntityTypeSubtask, EntityTypeContext, EntityTypeMultiple}

// ActionType is the WebSocket Protocol v2.0 action type literal.
type ActionType string

const (
	ActionTypeCreate ActionType = "create"
	ActionTypeUpdate ActionType = "update"
	ActionTypeDelete ActionType = "delete"
	ActionTypeBatch  ActionType = "batch"
)

// ActionTypeValues lists the literal members in declaration order.
var ActionTypeValues = []ActionType{ActionTypeCreate, ActionTypeUpdate, ActionTypeDelete, ActionTypeBatch}

// SourceType identifies who or what sent a message.
type SourceType string

const (
	SourceTypeMCPAI  SourceType = "mcp-ai"
	SourceTypeUser   SourceType = "user"
	SourceTypeSystem SourceType = "system"
)

// SourceTypeValues lists the literal members in declaration order.
var SourceTypeValues = []SourceType{SourceTypeMCPAI, SourceTypeUser, SourceTypeSystem}

// ProtocolVersion is the WebSocket Protocol version literal (only v2.0).
type ProtocolVersion string

// ProtocolVersion20 is the only supported protocol version.
const ProtocolVersion20 ProtocolVersion = "2.0"
