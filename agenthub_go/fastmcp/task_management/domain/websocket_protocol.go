package domain

import (
	"fmt"
	"math/big"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// WebSocket Protocol v2.0: type-safe communication models. Pydantic validation is
// reproduced for the checks the Python models perform; a ValidationError renders the same
// text as pydantic 2.12 (errors.pydantic.dev/2.12).

const pydanticDocsVersion = "2.12"

// ValidationErrorItem is one pydantic error line.
type ValidationErrorItem struct {
	Loc        string
	Msg        string
	Type       string
	InputValue string // repr, already truncated like pydantic-core
	InputType  string
}

// ValidationError mirrors pydantic_core.ValidationError (a ValueError).
type ValidationError struct {
	Title  string
	Errors []ValidationErrorItem
}

func (e *ValidationError) Error() string {
	var b strings.Builder
	plural := "s"
	if len(e.Errors) == 1 {
		plural = ""
	}
	fmt.Fprintf(&b, "%d validation error%s for %s", len(e.Errors), plural, e.Title)
	for _, it := range e.Errors {
		fmt.Fprintf(&b, "\n%s\n  %s [type=%s, input_value=%s, input_type=%s]\n    For further information visit https://errors.pydantic.dev/%s/v/%s",
			it.Loc, it.Msg, it.Type, it.InputValue, it.InputType, pydanticDocsVersion, it.Type)
	}
	return b.String()
}

// Unwrap exposes the ValueError base class.
func (e *ValidationError) Unwrap() error { return &tmvo.ValueError{Msg: e.Error()} }

// KeyError mirrors Python's KeyError: its text is the repr of the key. Raw, when set, is
// that repr already (for keys that are not strings, e.g. a slice).
type KeyError struct{ Msg, Raw string }

func (e *KeyError) Error() string {
	if e.Raw != "" {
		return e.Raw
	}
	return tmvo.PyRepr(e.Msg)
}

// pydanticRepr is pydantic-core's truncate_safe_repr: reprs longer than 50 UTF-8 bytes
// keep a 25-byte prefix and a 24-byte suffix (on character boundaries) around "...".
func pydanticRepr(v any) string {
	r := tmvo.PyRepr(v)
	if bi, ok := v.(*big.Int); ok {
		r = bi.String()
	}
	if len(r) <= 50 {
		return r
	}
	end := 0
	for i, c := range r {
		n := i + utf8.RuneLen(c)
		if n > 25 {
			break
		}
		end = n
	}
	start := len(r)
	for i := len(r) - 1; i >= 0 && len(r)-i <= 24; i-- {
		if utf8.RuneStart(r[i]) {
			start = i
		}
	}
	return r[:end] + "..." + r[start:]
}

func pyTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case string:
		return "str"
	case bool:
		return "bool"
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64, *big.Int:
		return "int"
	case float32, float64:
		return "float"
	case []any, []string:
		return "list"
	case tmvo.OrderedAny, map[string]any:
		return "dict"
	}
	return "object"
}

func valueErrorItem(loc, msg string, input any) ValidationErrorItem {
	return ValidationErrorItem{Loc: loc, Msg: "Value error, " + msg, Type: "value_error", InputValue: pydanticRepr(input), InputType: pyTypeName(input)}
}

func stringTypeItem(loc string, input any) ValidationErrorItem {
	return ValidationErrorItem{Loc: loc, Msg: "Input should be a valid string", Type: "string_type", InputValue: pydanticRepr(input), InputType: pyTypeName(input)}
}

// optString reads a `str | None` field from a dynamic value.
func optString(loc string, v any, errs *[]ValidationErrorItem) *string {
	switch s := v.(type) {
	case nil:
		return nil
	case string:
		return &s
	}
	*errs = append(*errs, stringTypeItem(loc, v))
	return nil
}

func blank(s string) bool { return s == "" || tmvo.PyStrip(s) == "" }

func optAny(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

func dump(kv ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i < len(kv); i += 2 {
		m.Set(kv[i].(string), kv[i+1])
	}
	return m
}

func strList(s []string) any {
	if s == nil {
		return nil
	}
	return s
}

func optInt(i *int) any {
	if i == nil {
		return nil
	}
	return *i
}

// Payload is a typed entity payload; ModelDump is pydantic's model_dump().
type Payload interface {
	ModelDump() *entities.OrderedMap[any]
}

// ---- project payloads

type ProjectCreatePayload struct {
	ID, Name             string
	Description          *string
	CreatedAt, UpdatedAt *string
}

func (p ProjectCreatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "name", p.Name, "description", optAny(p.Description), "created_at", optAny(p.CreatedAt), "updated_at", optAny(p.UpdatedAt))
}

type ProjectUpdatePayload struct {
	ID, Name    string
	Description *string
	UpdatedAt   *string
}

func (p ProjectUpdatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "name", p.Name, "description", optAny(p.Description), "updated_at", optAny(p.UpdatedAt))
}

// ProjectDeletePayload requires a non-blank id and name.
type ProjectDeletePayload struct{ ID, Name string }

func NewProjectDeletePayload(id, name string) (*ProjectDeletePayload, error) {
	var errs []ValidationErrorItem
	if blank(id) {
		errs = append(errs, valueErrorItem("id", "Project ID cannot be empty", id))
	}
	if blank(name) {
		errs = append(errs, valueErrorItem("name", "Project name cannot be empty", name))
	}
	if errs != nil {
		return nil, &ValidationError{Title: "ProjectDeletePayload", Errors: errs}
	}
	return &ProjectDeletePayload{ID: id, Name: name}, nil
}

func (p ProjectDeletePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "name", p.Name)
}

// ---- branch payloads

type BranchCreatePayload struct {
	ID, Name, GitBranchName, ProjectID string
	Description, Status, CreatedAt     *string
}

func (p BranchCreatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "name", p.Name, "git_branch_name", p.GitBranchName, "project_id", p.ProjectID,
		"description", optAny(p.Description), "status", optAny(p.Status), "created_at", optAny(p.CreatedAt))
}

type BranchUpdatePayload struct {
	ID, Name, GitBranchName, ProjectID string
	Description, Status, UpdatedAt     *string
}

func (p BranchUpdatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "name", p.Name, "git_branch_name", p.GitBranchName, "project_id", p.ProjectID,
		"description", optAny(p.Description), "status", optAny(p.Status), "updated_at", optAny(p.UpdatedAt))
}

// BranchDeletePayload requires non-blank id, name and project_id.
type BranchDeletePayload struct{ ID, Name, ProjectID string }

func NewBranchDeletePayload(id, name, projectID string) (*BranchDeletePayload, error) {
	var errs []ValidationErrorItem
	if blank(id) {
		errs = append(errs, valueErrorItem("id", "ID cannot be empty", id))
	}
	if blank(name) {
		errs = append(errs, valueErrorItem("name", "Branch name cannot be empty", name))
	}
	if blank(projectID) {
		errs = append(errs, valueErrorItem("project_id", "ID cannot be empty", projectID))
	}
	if errs != nil {
		return nil, &ValidationError{Title: "BranchDeletePayload", Errors: errs}
	}
	return &BranchDeletePayload{ID: id, Name: name, ProjectID: projectID}, nil
}

func (p BranchDeletePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "name", p.Name, "project_id", p.ProjectID)
}

// ---- task payloads (nil slice = None)

type TaskCreatePayload struct {
	ID, Title                     string
	Description                   *string
	Status, Priority, GitBranchID string
	ProjectID                     *string
	Assignees, Labels             []string
	CreatedAt                     *string
}

func (p TaskCreatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "description", optAny(p.Description), "status", p.Status, "priority", p.Priority,
		"git_branch_id", p.GitBranchID, "project_id", optAny(p.ProjectID), "assignees", strList(p.Assignees), "labels", strList(p.Labels),
		"created_at", optAny(p.CreatedAt))
}

type TaskUpdatePayload struct {
	ID, Title                     string
	Description                   *string
	Status, Priority, GitBranchID string
	Assignees, Labels             []string
	UpdatedAt                     *string
}

func (p TaskUpdatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "description", optAny(p.Description), "status", p.Status, "priority", p.Priority,
		"git_branch_id", p.GitBranchID, "assignees", strList(p.Assignees), "labels", strList(p.Labels), "updated_at", optAny(p.UpdatedAt))
}

// TaskDeletePayload requires a non-blank id and title.
type TaskDeletePayload struct {
	ID, Title              string
	GitBranchID, ProjectID *string
}

func NewTaskDeletePayload(id, title string, gitBranchID, projectID *string) (*TaskDeletePayload, error) {
	var errs []ValidationErrorItem
	if blank(id) {
		errs = append(errs, valueErrorItem("id", "Task ID cannot be empty", id))
	}
	if blank(title) {
		errs = append(errs, valueErrorItem("title", "Task title cannot be empty", title))
	}
	if errs != nil {
		return nil, &ValidationError{Title: "TaskDeletePayload", Errors: errs}
	}
	return &TaskDeletePayload{ID: id, Title: title, GitBranchID: gitBranchID, ProjectID: projectID}, nil
}

func (p TaskDeletePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "git_branch_id", optAny(p.GitBranchID), "project_id", optAny(p.ProjectID))
}

// TaskCompletePayload always has status "done".
type TaskCompletePayload struct {
	ID, Title                                    string
	CompletionSummary, TestingNotes, CompletedAt *string
}

func (p TaskCompletePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "status", "done", "completion_summary", optAny(p.CompletionSummary),
		"testing_notes", optAny(p.TestingNotes), "completed_at", optAny(p.CompletedAt))
}

// ---- subtask payloads

type SubtaskCreatePayload struct {
	ID, Title            string
	Description          *string
	Status, TaskID       string
	ProgressPercentage   *int
	CreatedAt, UpdatedAt *string
}

func (p SubtaskCreatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "description", optAny(p.Description), "status", p.Status, "task_id", p.TaskID,
		"progress_percentage", optInt(p.ProgressPercentage), "created_at", optAny(p.CreatedAt), "updated_at", optAny(p.UpdatedAt))
}

type SubtaskUpdatePayload struct {
	ID, Title            string
	Description          *string
	Status, TaskID       string
	ProgressPercentage   *int
	CreatedAt, UpdatedAt *string
}

func (p SubtaskUpdatePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "description", optAny(p.Description), "status", p.Status, "task_id", p.TaskID,
		"progress_percentage", optInt(p.ProgressPercentage), "created_at", optAny(p.CreatedAt), "updated_at", optAny(p.UpdatedAt))
}

// SubtaskDeletePayload requires a non-blank id and task_id.
type SubtaskDeletePayload struct {
	ID, TaskID string
	Title      *string
}

func NewSubtaskDeletePayload(id, taskID string, title *string) (*SubtaskDeletePayload, error) {
	var errs []ValidationErrorItem
	if blank(id) {
		errs = append(errs, valueErrorItem("id", "ID cannot be empty", id))
	}
	if blank(taskID) {
		errs = append(errs, valueErrorItem("task_id", "ID cannot be empty", taskID))
	}
	if errs != nil {
		return nil, &ValidationError{Title: "SubtaskDeletePayload", Errors: errs}
	}
	return &SubtaskDeletePayload{ID: id, TaskID: taskID, Title: title}, nil
}

func (p SubtaskDeletePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "task_id", p.TaskID, "title", optAny(p.Title))
}

// SubtaskCompletePayload always has status "done" and progress_percentage 100.
type SubtaskCompletePayload struct {
	ID, Title, TaskID                 string
	CompletionSummary                 *string
	CreatedAt, UpdatedAt, CompletedAt *string
}

func (p SubtaskCompletePayload) ModelDump() *entities.OrderedMap[any] {
	return dump("id", p.ID, "title", p.Title, "status", "done", "task_id", p.TaskID, "completion_summary", optAny(p.CompletionSummary),
		"progress_percentage", 100, "created_at", optAny(p.CreatedAt), "updated_at", optAny(p.UpdatedAt), "completed_at", optAny(p.CompletedAt))
}

// ---- message structure

// WSMetadata is the contextual metadata; Extra holds the extra="allow" fields.
type WSMetadata struct {
	Source                                            string
	UserID, SessionID, CorrelationID                  *string
	EntityType, EntityID, EventType                   *string
	ProjectID, GitBranchID, TaskID                    *string
	ProjectName, BranchTitle, TaskTitle, SubtaskTitle *string
	Timestamp                                         *string
	Extra                                             *entities.OrderedMap[any]
}

// wsMetadataModule is the module path Python prints in TypeError messages.
const wsMetadataModule = "fastmcp.task_management.domain.websocket_protocol"

// NewWSMetadata builds metadata the way the message factories do: source="user", the
// fixed keyword arguments, then `**metadata_overrides`. An override that repeats one of the
// fixed keywords is a TypeError; a declared string field of another type is a
// ValidationError; any other key is kept as an extra field.
func NewWSMetadata(userID, entityType, entityID, eventType string, overrides *entities.OrderedMap[any]) (*WSMetadata, error) {
	m := &WSMetadata{Source: "user", UserID: &userID, EntityType: &entityType, EntityID: &entityID, EventType: &eventType,
		Extra: entities.NewOrderedMap[any]()}
	declared := []struct {
		key string
		dst **string
	}{
		{"sessionId", &m.SessionID}, {"correlationId", &m.CorrelationID}, {"project_id", &m.ProjectID},
		{"git_branch_id", &m.GitBranchID}, {"task_id", &m.TaskID}, {"project_name", &m.ProjectName},
		{"branch_title", &m.BranchTitle}, {"task_title", &m.TaskTitle}, {"subtask_title", &m.SubtaskTitle}, {"timestamp", &m.Timestamp},
	}
	isDeclared := map[string]bool{}
	for _, d := range declared {
		isDeclared[d.key] = true
	}
	if overrides == nil {
		overrides = entities.NewOrderedMap[any]()
	}
	for _, k := range overrides.Keys() {
		switch k {
		case "source", "userId", "entity_type", "entity_id", "event_type":
			return nil, &tmvo.TypeError{Msg: fmt.Sprintf("%s.WSMetadata() got multiple values for keyword argument %s", wsMetadataModule, tmvo.PyRepr(k))}
		}
	}
	var errs []ValidationErrorItem
	for _, d := range declared {
		if v, ok := overrides.Get(d.key); ok {
			*d.dst = optString(d.key, v, &errs)
		}
	}
	if errs != nil {
		return nil, &ValidationError{Title: "WSMetadata", Errors: errs}
	}
	for _, k := range overrides.Keys() {
		if !isDeclared[k] {
			v, _ := overrides.Get(k)
			m.Extra.Set(k, v)
		}
	}
	return m, nil
}

func (m *WSMetadata) ModelDump() *entities.OrderedMap[any] {
	d := dump("source", m.Source, "userId", optAny(m.UserID), "sessionId", optAny(m.SessionID), "correlationId", optAny(m.CorrelationID),
		"entity_type", optAny(m.EntityType), "entity_id", optAny(m.EntityID), "event_type", optAny(m.EventType),
		"project_id", optAny(m.ProjectID), "git_branch_id", optAny(m.GitBranchID), "task_id", optAny(m.TaskID),
		"project_name", optAny(m.ProjectName), "branch_title", optAny(m.BranchTitle), "task_title", optAny(m.TaskTitle),
		"subtask_title", optAny(m.SubtaskTitle), "timestamp", optAny(m.Timestamp))
	for _, k := range m.Extra.Keys() {
		v, _ := m.Extra.Get(k)
		d.Set(k, v)
	}
	return d
}

// WSPayloadData holds the primary entity data (which must include "id") and the cascade.
type WSPayloadData struct {
	Primary *entities.OrderedMap[any]
	Cascade *entities.OrderedMap[[]any] // nil = None
}

func NewWSPayloadData(primary *entities.OrderedMap[any], cascade *entities.OrderedMap[[]any]) (*WSPayloadData, error) {
	if !primary.Has("id") {
		return nil, &ValidationError{Title: "WSPayloadData", Errors: []ValidationErrorItem{
			valueErrorItem("primary", "Payload primary data MUST include 'id' field", primary)}}
	}
	return &WSPayloadData{Primary: primary, Cascade: cascade}, nil
}

func (d *WSPayloadData) ModelDump() *entities.OrderedMap[any] {
	var cascade any
	if d.Cascade != nil {
		c := entities.NewOrderedMap[any]()
		for _, k := range d.Cascade.Keys() {
			v, _ := d.Cascade.Get(k)
			c.Set(k, v)
		}
		cascade = c
	}
	return dump("primary", d.Primary, "cascade", cascade)
}

var wsEntities = []string{"project", "branch", "task", "subtask", "context", "agent"}
var wsActions = []string{"created", "updated", "deleted", "completed", "assigned", "unassigned"}

func literalItem(loc string, allowed []string, input string) ValidationErrorItem {
	quoted := make([]string, len(allowed))
	for i, a := range allowed {
		quoted[i] = tmvo.PyRepr(a)
	}
	msg := "Input should be " + strings.Join(quoted[:len(quoted)-1], ", ") + " or " + quoted[len(quoted)-1]
	return ValidationErrorItem{Loc: loc, Msg: msg, Type: "literal_error", InputValue: pydanticRepr(input), InputType: "str"}
}

func inList(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

// WSPayload is the payload structure; entity and action are literals.
type WSPayload struct {
	Entity, Action string
	Data           *WSPayloadData
}

func NewWSPayload(entity, action string, data *WSPayloadData) (*WSPayload, error) {
	var errs []ValidationErrorItem
	if !inList(wsEntities, entity) {
		errs = append(errs, literalItem("entity", wsEntities, entity))
	}
	if !inList(wsActions, action) {
		errs = append(errs, literalItem("action", wsActions, action))
	}
	if errs != nil {
		return nil, &ValidationError{Title: "WSPayload", Errors: errs}
	}
	return &WSPayload{Entity: entity, Action: action, Data: data}, nil
}

func (p *WSPayload) ModelDump() *entities.OrderedMap[any] {
	return dump("entity", p.Entity, "action", p.Action, "data", p.Data.ModelDump())
}

// WSMessage is the complete v2.0 message.
type WSMessage struct {
	ID        string
	Version   string
	Type      string
	Timestamp string
	Sequence  int
	Payload   *WSPayload
	Metadata  *WSMetadata
}

// NewWSMessage applies the defaults (id "ws-<12 hex>", version 2.0, now, sequence 0).
func NewWSMessage(typ string, payload *WSPayload, metadata *WSMetadata) *WSMessage {
	return &WSMessage{ID: "ws-" + strings.ReplaceAll(tmvo.NewUUIDv4(), "-", "")[:12], Version: "2.0", Type: typ,
		Timestamp: tmvo.IsoFormat(time.Now().UTC()), Payload: payload, Metadata: metadata}
}

func (m *WSMessage) ModelDump() *entities.OrderedMap[any] {
	return dump("id", m.ID, "version", m.Version, "type", m.Type, "timestamp", m.Timestamp, "sequence", m.Sequence,
		"payload", m.Payload.ModelDump(), "metadata", m.Metadata.ModelDump())
}

// ---- message factories

func createMessage(entity string, payload Payload, userID, eventType string, overrides *entities.OrderedMap[any]) (*WSMessage, error) {
	dict := payload.ModelDump()
	id, _ := dict.Get("id")
	meta, err := NewWSMetadata(userID, entity, id.(string), eventType, overrides)
	if err != nil {
		return nil, err
	}
	data, err := NewWSPayloadData(dict, nil)
	if err != nil {
		return nil, err
	}
	wsPayload, err := NewWSPayload(entity, eventType, data)
	if err != nil {
		return nil, err
	}
	return NewWSMessage("update", wsPayload, meta), nil
}

// CreateDeleteMessage builds the WebSocket message for a DELETE operation.
func CreateDeleteMessage(entity string, payload Payload, userID string, overrides *entities.OrderedMap[any]) (*WSMessage, error) {
	return createMessage(entity, payload, userID, "deleted", overrides)
}

// CreateUpdateMessage builds the WebSocket message for an UPDATE operation.
func CreateUpdateMessage(entity string, payload Payload, userID string, overrides *entities.OrderedMap[any]) (*WSMessage, error) {
	return createMessage(entity, payload, userID, "updated", overrides)
}

// CreateCreateMessage builds the WebSocket message for a CREATE operation.
func CreateCreateMessage(entity string, payload Payload, userID string, overrides *entities.OrderedMap[any]) (*WSMessage, error) {
	return createMessage(entity, payload, userID, "created", overrides)
}

// ---- validation helpers

// ValidateDeletePayload checks a delete payload has an id and a name or title.
func ValidateDeletePayload(data map[string]any) (bool, []string) {
	errs := []string{}
	if !tmvo.PyTruthy(data["id"]) {
		errs = append(errs, "Missing required field: id (string)")
	}
	if !tmvo.PyTruthy(data["name"]) && !tmvo.PyTruthy(data["title"]) {
		errs = append(errs, "Missing required field: name or title (string)")
	}
	return len(errs) == 0, errs
}

// ConvertBranchDeleteLegacy builds a typed branch delete payload.
func ConvertBranchDeleteLegacy(branchID, branchName, projectID string) (*BranchDeletePayload, error) {
	return NewBranchDeletePayload(branchID, branchName, projectID)
}

// ConvertTaskDeleteLegacy converts a task snapshot into a typed payload, falling back to
// "Task <first 8 characters of id>" for a missing title.
func ConvertTaskDeleteLegacy(snapshot *entities.OrderedMap[any]) (*TaskDeletePayload, error) {
	if snapshot == nil || snapshot.Len() == 0 {
		return nil, &tmvo.TypeError{Msg: "task_snapshot cannot be None or empty"}
	}
	if !snapshot.Has("id") {
		return nil, &KeyError{Msg: "task_snapshot must contain 'id' field"}
	}
	taskID, _ := snapshot.Get("id")
	if idStr, isStr := taskID.(string); !tmvo.PyTruthy(taskID) || (isStr && blank(idStr)) {
		return nil, &tmvo.ValueError{Msg: "Task ID cannot be empty"}
	}
	title, _ := snapshot.Get("title")
	if titleStr, isStr := title.(string); !tmvo.PyTruthy(title) || (isStr && blank(titleStr)) {
		switch id := taskID.(type) {
		case string:
			r := []rune(id)
			if len(r) > 8 {
				r = r[:8]
			}
			title = "Task " + string(r)
		case []any:
			if len(id) > 8 {
				id = id[:8]
			}
			title = "Task " + tmvo.PyStr(id)
		case tmvo.OrderedAny:
			return nil, &KeyError{Raw: "slice(None, 8, None)"} // dict[slice] is a plain hashable lookup
		default:
			return nil, &tmvo.TypeError{Msg: fmt.Sprintf("'%s' object is not subscriptable", pyTypeName(taskID))}
		}
	}
	var errs []ValidationErrorItem
	idStr, idOK := taskID.(string)
	if !idOK {
		errs = append(errs, stringTypeItem("id", taskID))
	}
	titleStr, titleOK := title.(string)
	if !titleOK {
		errs = append(errs, stringTypeItem("title", title))
	}
	gitBranch, _ := snapshot.Get("git_branch_id")
	project, _ := snapshot.Get("project_id")
	gb := optString("git_branch_id", gitBranch, &errs)
	pr := optString("project_id", project, &errs)
	if errs != nil {
		return nil, &ValidationError{Title: "TaskDeletePayload", Errors: errs}
	}
	return NewTaskDeletePayload(idStr, titleStr, gb, pr)
}

// ConvertSubtaskDeleteLegacy builds a typed subtask delete payload.
func ConvertSubtaskDeleteLegacy(subtaskID, taskID string, title *string) (*SubtaskDeletePayload, error) {
	return NewSubtaskDeletePayload(subtaskID, taskID, title)
}
