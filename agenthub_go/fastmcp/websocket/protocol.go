package websocket

import (
	"context"
	"fmt"
	"math"
	"math/big"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/services"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// MaxMessageSizeBytes is the maximum message size (64KB).
const MaxMessageSizeBytes = 64 * 1024

// ProtocolError is the base exception for WebSocket protocol errors.
type ProtocolError struct{ Msg string }

func (e *ProtocolError) Error() string { return e.Msg }

// MessageSizeError is raised when a message exceeds the size limit.
type MessageSizeError struct{ Msg string }

func (e *MessageSizeError) Error() string { return e.Msg }

// InvalidVersionError is raised when the message version is not v2.0.
type InvalidVersionError struct{ Msg string }

func (e *InvalidVersionError) Error() string { return e.Msg }

// pydanticDocsVersion is the pydantic version whose ValidationError text is reproduced.
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
func (e *ValidationError) Unwrap() error { return &value_objects.ValueError{Msg: e.Error()} }

// pydanticRepr is pydantic-core's truncate_safe_repr: reprs longer than 50 UTF-8 bytes
// keep a 25-byte prefix and a 24-byte suffix (on character boundaries) around "...".
func pydanticRepr(v any) string {
	r := value_objects.PyRepr(v)
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
	case value_objects.OrderedAny, map[string]any:
		return "dict"
	}
	return "object"
}

type errList struct{ items []ValidationErrorItem }

func (e *errList) add(it ValidationErrorItem) { e.items = append(e.items, it) }

func pyItem(loc, msg, typ string, input any) ValidationErrorItem {
	return ValidationErrorItem{Loc: loc, Msg: msg, Type: typ, InputValue: pydanticRepr(input), InputType: pyTypeName(input)}
}

func missingItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Field required", "missing", input)
}

func stringTypeItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid string", "string_type", input)
}

func intParsingItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid integer, unable to parse string as an integer", "int_parsing", input)
}

func intTypeItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid integer", "int_type", input)
}

func intFromFloatItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid integer, got a number with a fractional part", "int_from_float", input)
}

func boolParsingItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid boolean, unable to interpret input", "bool_parsing", input)
}

func boolTypeItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid boolean", "bool_type", input)
}

func modelTypeItem(loc, model string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid dictionary or instance of "+model, "model_type", input)
}

func listTypeItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid list", "list_type", input)
}

func dictTypeItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid dictionary", "dict_type", input)
}

func datetimeTypeItem(loc string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid datetime", "datetime_type", input)
}

func datetimeParsingItem(loc, detail string, input any) ValidationErrorItem {
	return pyItem(loc, "Input should be a valid datetime or date, "+detail, "datetime_from_date_parsing", input)
}

// literalItem reproduces pydantic's literal_error message for a list of allowed values.
func literalItem(loc string, allowed []string, input any) ValidationErrorItem {
	quoted := make([]string, len(allowed))
	for i, a := range allowed {
		quoted[i] = value_objects.PyRepr(a)
	}
	msg := "Input should be "
	switch len(quoted) {
	case 0:
		// unreachable for the protocol literals
	case 1:
		msg += quoted[0]
	default:
		msg += strings.Join(quoted[:len(quoted)-1], ", ") + " or " + quoted[len(quoted)-1]
	}
	return pyItem(loc, msg, "literal_error", input)
}

func stringsOf[T ~string](vals []T) []string {
	out := make([]string, len(vals))
	for i, v := range vals {
		out[i] = string(v)
	}
	return out
}

func inStrings(allowed []string, s string) bool {
	for _, a := range allowed {
		if a == s {
			return true
		}
	}
	return false
}

// asMap returns an OrderedMap view of a decoded JSON object (or nil for anything else).
func asMap(v any) (*entities.OrderedMap[any], bool) {
	switch x := v.(type) {
	case *entities.OrderedMap[any]:
		return x, true
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		om := entities.NewOrderedMap[any]()
		for _, k := range keys {
			om.Set(k, x[k])
		}
		return om, true
	}
	return nil, false
}

// ValidateMessage validates and parses a WebSocket message according to v2.0.
func ValidateMessage(message *entities.OrderedMap[any]) (*WSMessage, error) {
	version, _ := message.Get("version")
	if s, ok := version.(string); !ok || s != "2.0" {
		return nil, &InvalidVersionError{Msg: fmt.Sprintf("Only protocol v2.0 is supported, got: %s", value_objects.PyStr(version))}
	}

	messageJSON, _ := value_objects.PyJSONDumps(message, -1)
	messageSize := len([]byte(messageJSON))
	if messageSize > MaxMessageSizeBytes {
		return nil, &MessageSizeError{Msg: fmt.Sprintf("Message size %d bytes exceeds limit of %d bytes", messageSize, MaxMessageSizeBytes)}
	}

	msg, verr := validateWSMessage(message)
	if verr != nil {
		return nil, &ProtocolError{Msg: "Invalid message structure: " + verr.Error()}
	}
	return msg, nil
}

func validateWSMessage(raw *entities.OrderedMap[any]) (*WSMessage, *ValidationError) {
	var errs errList
	m := &WSMessage{Version: ProtocolVersion20, Timestamp: nowUTC()}

	if v, ok := raw.Get("id"); ok {
		if s, ok := v.(string); ok {
			m.ID = s
		} else {
			errs.add(stringTypeItem("id", v))
		}
	} else {
		m.ID = value_objects.NewUUIDv4()
	}

	if v, ok := raw.Get("version"); ok {
		if s, ok := v.(string); ok && s == "2.0" {
			m.Version = ProtocolVersion20
		} else {
			errs.add(literalItem("version", []string{"2.0"}, v))
		}
	}

	if v, ok := raw.Get("type"); ok {
		if s, ok := v.(string); ok && inStrings(stringsOf(MessageTypeValues), s) {
			m.Type = MessageType(s)
		} else {
			errs.add(literalItem("type", stringsOf(MessageTypeValues), v))
		}
	} else {
		errs.add(missingItem("type", raw))
	}

	if v, ok := raw.Get("timestamp"); ok {
		if t, item, ok := parseWSDateTime("timestamp", v); ok {
			m.Timestamp = t
		} else {
			errs.add(item)
		}
	}

	if v, ok := raw.Get("sequence"); ok {
		if n, item, ok := parsePyIntField("sequence", v); ok {
			m.Sequence = n
		} else {
			errs.add(item)
		}
	} else {
		errs.add(missingItem("sequence", raw))
	}

	if v, ok := raw.Get("payload"); ok {
		if p, ok := v.(*WSPayload); ok {
			m.Payload = p
		} else if pm, ok := asMap(v); ok {
			m.Payload = validateWSPayload("payload", pm, &errs)
		} else {
			errs.add(modelTypeItem("payload", "WSPayload", v))
		}
	} else {
		errs.add(missingItem("payload", raw))
	}

	if v, ok := raw.Get("metadata"); ok {
		if md, ok := v.(*WSMetadata); ok {
			m.Metadata = md
		} else if mm, ok := asMap(v); ok {
			m.Metadata = validateWSMetadata("metadata", mm, &errs)
		} else {
			errs.add(modelTypeItem("metadata", "WSMetadata", v))
		}
	} else {
		errs.add(missingItem("metadata", raw))
	}

	if len(errs.items) > 0 {
		return nil, &ValidationError{Title: "WSMessage", Errors: errs.items}
	}
	return m, nil
}

func validateWSPayload(prefix string, raw *entities.OrderedMap[any], errs *errList) *WSPayload {
	p := &WSPayload{}

	if v, ok := raw.Get("entity"); ok {
		if s, ok := v.(string); ok && inStrings(stringsOf(EntityTypeValues), s) {
			p.Entity = EntityType(s)
		} else {
			errs.add(literalItem(prefix+".entity", stringsOf(EntityTypeValues), v))
		}
	} else {
		errs.add(missingItem(prefix+".entity", raw))
	}

	if v, ok := raw.Get("action"); ok {
		if s, ok := v.(string); ok && inStrings(stringsOf(ActionTypeValues), s) {
			p.Action = ActionType(s)
		} else {
			errs.add(literalItem(prefix+".action", stringsOf(ActionTypeValues), v))
		}
	} else {
		errs.add(missingItem(prefix+".action", raw))
	}

	if v, ok := raw.Get("data"); ok {
		if d, ok := v.(*WSData); ok {
			p.Data = d
		} else if dm, ok := asMap(v); ok {
			p.Data = validateWSData(prefix+".data", dm, errs)
		} else {
			errs.add(modelTypeItem(prefix+".data", "WSData", v))
		}
	} else {
		errs.add(missingItem(prefix+".data", raw))
	}
	return p
}

func validateWSData(prefix string, raw *entities.OrderedMap[any], errs *errList) *WSData {
	d := &WSData{}

	if v, ok := raw.Get("primary"); ok {
		switch pv := v.(type) {
		case *entities.OrderedMap[any]:
			d.Primary = pv
		default:
			if list, ok := v.([]any); ok {
				var elemErrs []ValidationErrorItem
				for i, e := range list {
					if _, ok := asMap(e); !ok {
						elemErrs = append(elemErrs, dictTypeItem(fmt.Sprintf("%s.primary.list[dict[str,any]].%d", prefix, i), e))
					}
				}
				if len(elemErrs) > 0 {
					errs.add(dictTypeItem(prefix+".primary.dict[str,any]", pv))
					for _, it := range elemErrs {
						errs.add(it)
					}
				} else {
					d.Primary = list
				}
			} else if pm, ok := asMap(v); ok {
				d.Primary = pm
			} else {
				errs.add(dictTypeItem(prefix+".primary.dict[str,any]", pv))
				errs.add(listTypeItem(prefix+".primary.list[dict[str,any]]", pv))
			}
		}
	} else {
		errs.add(missingItem(prefix+".primary", raw))
	}

	if v, ok := raw.Get("cascade"); ok {
		if v == nil {
			d.Cascade = nil
		} else if cd, ok := v.(*CascadeData); ok {
			d.Cascade = cd
		} else if cm, ok := asMap(v); ok {
			d.Cascade = validateCascadeData(prefix+".cascade", cm, errs)
		} else {
			errs.add(modelTypeItem(prefix+".cascade", "CascadeData", v))
		}
	}

	if v, ok := raw.Get("delta"); ok {
		if v == nil {
			d.Delta = nil
		} else if dm, ok := asMap(v); ok {
			d.Delta = dm
		} else {
			errs.add(dictTypeItem(prefix+".delta", v))
		}
	}
	return d
}

func validateCascadeData(prefix string, raw *entities.OrderedMap[any], errs *errList) *CascadeData {
	c := NewCascadeData()
	fields := []struct {
		name string
		dst  *[]any
	}{
		{"branches", &c.Branches},
		{"tasks", &c.Tasks},
		{"projects", &c.Projects},
		{"subtasks", &c.Subtasks},
		{"contexts", &c.Contexts},
	}
	for _, f := range fields {
		v, ok := raw.Get(f.name)
		if !ok {
			*f.dst = []any{}
			continue
		}
		list, ok := v.([]any)
		if !ok {
			errs.add(listTypeItem(prefix+"."+f.name, v))
			continue
		}
		out := make([]any, 0, len(list))
		for i, e := range list {
			if om, ok := asMap(e); ok {
				out = append(out, om)
			} else {
				errs.add(dictTypeItem(fmt.Sprintf("%s.%s.%d", prefix, f.name, i), e))
			}
		}
		*f.dst = out
	}
	return c
}

func validateWSMetadata(prefix string, raw *entities.OrderedMap[any], errs *errList) *WSMetadata {
	m := &WSMetadata{Immediate: true}

	if v, ok := raw.Get("source"); ok {
		if s, ok := v.(string); ok && inStrings(stringsOf(SourceTypeValues), s) {
			m.Source = SourceType(s)
		} else {
			errs.add(literalItem(prefix+".source", stringsOf(SourceTypeValues), v))
		}
	} else {
		errs.add(missingItem(prefix+".source", raw))
	}

	for _, f := range []struct {
		name string
		dst  **string
	}{
		{"user_id", &m.UserID},
		{"session_id", &m.SessionID},
		{"correlation_id", &m.CorrelationID},
		{"batch_id", &m.BatchID},
	} {
		if v, ok := raw.Get(f.name); ok {
			*f.dst = optionalStringField(prefix+"."+f.name, v, errs)
		}
	}

	if v, ok := raw.Get("immediate"); ok {
		m.Immediate = parsePyBoolField(prefix+".immediate", v, errs)
	}
	return m
}

func optionalStringField(loc string, v any, errs *errList) *string {
	if v == nil {
		return nil
	}
	if s, ok := v.(string); ok {
		return &s
	}
	errs.add(stringTypeItem(loc, v))
	return nil
}

func parsePyIntField(loc string, v any) (int, ValidationErrorItem, bool) {
	switch x := v.(type) {
	case bool:
		if x {
			return 1, ValidationErrorItem{}, true
		}
		return 0, ValidationErrorItem{}, true
	case string:
		if n, ok := parsePyIntString(x); ok {
			return int(n), ValidationErrorItem{}, true
		}
		return 0, intParsingItem(loc, v), false
	case *big.Int:
		return int(x.Int64()), ValidationErrorItem{}, true
	case int:
		return x, ValidationErrorItem{}, true
	case int8:
		return int(x), ValidationErrorItem{}, true
	case int16:
		return int(x), ValidationErrorItem{}, true
	case int32:
		return int(x), ValidationErrorItem{}, true
	case int64:
		return int(x), ValidationErrorItem{}, true
	case uint, uint8, uint16, uint32, uint64:
		return int(reflectUint(x)), ValidationErrorItem{}, true
	case float32:
		return intFromFloat(float64(x), loc, v)
	case float64:
		return intFromFloat(x, loc, v)
	}
	return 0, intTypeItem(loc, v), false
}

func reflectUint(v any) uint64 {
	switch x := v.(type) {
	case uint:
		return uint64(x)
	case uint8:
		return uint64(x)
	case uint16:
		return uint64(x)
	case uint32:
		return uint64(x)
	case uint64:
		return x
	}
	return 0
}

func intFromFloat(f float64, loc string, v any) (int, ValidationErrorItem, bool) {
	if math.IsInf(f, 0) || math.IsNaN(f) {
		return 0, intTypeItem(loc, v), false
	}
	if f != math.Trunc(f) {
		return 0, intFromFloatItem(loc, v), false
	}
	return int(f), ValidationErrorItem{}, true
}

// parsePyIntString mirrors pydantic's lax int parsing of a string: int(s) or an integral
// decimal float literal (but not exponent notation).
func parsePyIntString(s string) (int64, bool) {
	if n, ok := value_objects.PyParseInt(s); ok {
		if n.IsInt64() {
			return n.Int64(), true
		}
		return 0, false
	}
	if strings.ContainsAny(s, "eE") {
		return 0, false
	}
	if f, err := strconv.ParseFloat(strings.TrimSpace(s), 64); err == nil {
		if f == math.Trunc(f) && !math.IsInf(f, 0) && !math.IsNaN(f) {
			return int64(f), true
		}
	}
	return 0, false
}

func parsePyBoolField(loc string, v any, errs *errList) bool {
	switch x := v.(type) {
	case bool:
		return x
	case string:
		switch value_objects.PyLower(value_objects.PyStrip(x)) {
		case "true", "1", "yes", "on", "t", "y":
			return true
		case "false", "0", "no", "off", "f", "n":
			return false
		}
		errs.add(boolParsingItem(loc, v))
		return false
	}
	if f, ok := value_objects.PyFloat(v); ok {
		switch f {
		case 0:
			return false
		case 1:
			return true
		}
		errs.add(boolParsingItem(loc, v))
		return false
	}
	errs.add(boolTypeItem(loc, v))
	return false
}

// parseWSDateTime mirrors pydantic's lax datetime parsing: numbers are Unix seconds, a
// digit-only string is also Unix seconds, and strings are parsed as ISO datetime/date.
func parseWSDateTime(loc string, v any) (time.Time, ValidationErrorItem, bool) {
	switch x := v.(type) {
	case string:
		if t, ok := parseUnixSecondsString(x); ok {
			return t, ValidationErrorItem{}, true
		}
		if t, err := time.Parse(time.RFC3339Nano, x); err == nil {
			return t, ValidationErrorItem{}, true
		}
		for _, layout := range []string{"2006-01-02T15:04:05.999999999", "2006-01-02"} {
			if t, err := time.ParseInLocation(layout, x, naiveLocation); err == nil {
				return t, ValidationErrorItem{}, true
			}
		}
		return time.Time{}, datetimeParsingItem(loc, datetimeParseDetail(x), v), false
	case bool:
		return time.Time{}, datetimeTypeItem(loc, v), false
	}
	if f, ok := value_objects.PyFloat(v); ok {
		sec := int64(f)
		nsec := int64((f - float64(sec)) * 1e9)
		return time.Unix(sec, nsec).UTC(), ValidationErrorItem{}, true
	}
	return time.Time{}, datetimeTypeItem(loc, v), false
}

func parseUnixSecondsString(s string) (time.Time, bool) {
	t := s
	if strings.HasPrefix(t, "-") || strings.HasPrefix(t, "+") {
		t = t[1:]
	}
	if t == "" {
		return time.Time{}, false
	}
	for i := 0; i < len(t); i++ {
		if t[i] < '0' || t[i] > '9' {
			return time.Time{}, false
		}
	}
	n, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return time.Time{}, false
	}
	return time.Unix(n, 0).UTC(), true
}

// datetimeParseDetail approximates pydantic/speedate's date-parsing error detail.
func datetimeParseDetail(s string) string {
	if len(s) < 10 {
		return "input is too short"
	}
	if s[0] < '0' || s[0] > '9' {
		return "invalid character in year"
	}
	if s[4] != '-' {
		return "invalid date separator, expected `-`"
	}
	month, err := strconv.Atoi(s[5:7])
	if err != nil {
		return "invalid character in month"
	}
	if month < 1 || month > 12 {
		return "month value is outside expected range of 1-12"
	}
	if s[7] != '-' {
		return "invalid date separator, expected `-`"
	}
	day, err := strconv.Atoi(s[8:10])
	if err != nil {
		return "invalid character in day"
	}
	if day < 1 || day > 31 {
		return "day value is outside expected range"
	}
	if len(s) > 10 {
		return "unexpected extra characters at the end of the input"
	}
	return "invalid character in year"
}

// mapEntityType maps a WebSocket entity type to the cascade calculator entity type.
func mapEntityType(entityType EntityType) (services.EntityType, error) {
	mapping := map[EntityType]services.EntityType{
		EntityTypeTask:    services.EntityTypeTask,
		EntityTypeSubtask: services.EntityTypeSubtask,
		EntityTypeBranch:  services.EntityTypeBranch,
		EntityTypeProject: services.EntityTypeProject,
		EntityTypeContext: services.EntityTypeContext,
	}
	if t, ok := mapping[entityType]; ok {
		return t, nil
	}
	return "", &value_objects.ValueError{Msg: fmt.Sprintf("Unsupported entity type for cascade: %s", entityType)}
}

// convertCascadeResult converts a CascadeResult to a CascadeData model.
func convertCascadeResult(r *services.CascadeResult) *CascadeData {
	return &CascadeData{
		Branches: idsOf(r.AffectedBranches.Items()),
		Tasks:    idsOf(r.AffectedTasks.Items()),
		Projects: idsOf(r.AffectedProjects.Items()),
		Subtasks: idsOf(r.AffectedSubtasks.Items()),
		Contexts: idsOf(r.AffectedContexts.Items()),
	}
}

func idsOf(ids []string) []any {
	out := make([]any, 0, len(ids))
	for _, id := range ids {
		out = append(out, wsDict("id", id))
	}
	return out
}

// mergeCascadeData merges a CascadeResult into existing cascade data, avoiding duplicate
// entity IDs.
func mergeCascadeData(target *CascadeData, r *services.CascadeResult) {
	add := func(dst *[]any, ids []string) {
		existing := map[string]bool{}
		for _, e := range *dst {
			if om, ok := asMap(e); ok {
				if id, ok := om.Get("id"); ok {
					existing[value_objects.PyStr(id)] = true
				}
			}
		}
		for _, id := range ids {
			if !existing[id] {
				existing[id] = true
				*dst = append(*dst, wsDict("id", id))
			}
		}
	}
	add(&target.Branches, r.AffectedBranches.Items())
	add(&target.Tasks, r.AffectedTasks.Items())
	add(&target.Projects, r.AffectedProjects.Items())
	add(&target.Subtasks, r.AffectedSubtasks.Items())
	add(&target.Contexts, r.AffectedContexts.Items())
}

// CreateUserUpdate creates a user-initiated update message with cascade data.
func CreateUserUpdate(ctx context.Context, entityType EntityType, action ActionType, primaryData any,
	cascadeCalculator *services.CascadeCalculator, entityID, userID, sessionID, correlationID *string, sequence int) *WSMessage {

	var cascadeData *CascadeData
	if cascadeCalculator != nil && entityID != nil {
		if cascadeEntityType, err := mapEntityType(entityType); err == nil {
			if result, err := cascadeCalculator.CalculateCascade(ctx, *entityID, &cascadeEntityType, true); err == nil {
				cascadeData = convertCascadeResult(result)
			}
		}
	}

	wsData := &WSData{Primary: primaryData, Cascade: cascadeData}
	payload := &WSPayload{Entity: entityType, Action: action, Data: wsData}
	metadata := &WSMetadata{Source: SourceTypeUser, UserID: userID, SessionID: sessionID, CorrelationID: correlationID, Immediate: true}
	return NewUserUpdateMessage(MessageTypeUpdate, sequence, payload, metadata)
}

// CreateAIBatch creates an AI-initiated batch update message with combined cascade data.
func CreateAIBatch(ctx context.Context, updates []*entities.OrderedMap[any], batchID string,
	cascadeCalculator *services.CascadeCalculator, userID *string, sequence int) *WSMessage {

	combinedCascade := NewCascadeData()
	if cascadeCalculator != nil {
		for _, update := range updates {
			entityIDv, _ := update.Get("entity_id")
			entityTypev, _ := update.Get("entity_type")
			if entityIDv == nil || entityTypev == nil {
				continue
			}
			entityID, ok := entityIDv.(string)
			if !ok {
				continue
			}
			entityTypeStr, ok := entityTypev.(string)
			if !ok {
				continue
			}
			cascadeEntityType, err := mapEntityType(EntityType(entityTypeStr))
			if err != nil {
				continue
			}
			if result, err := cascadeCalculator.CalculateCascade(ctx, entityID, &cascadeEntityType, true); err == nil {
				mergeCascadeData(combinedCascade, result)
			}
		}
	}

	var cascade *CascadeData
	if !combinedCascade.IsEmpty() {
		cascade = combinedCascade
	}
	wsData := &WSData{Primary: updates, Cascade: cascade}
	payload := &WSPayload{Entity: EntityTypeMultiple, Action: ActionTypeBatch, Data: wsData}
	metadata := &WSMetadata{Source: SourceTypeMCPAI, UserID: userID, BatchID: &batchID, Immediate: false}
	return NewAIBatchMessage(MessageTypeBulk, sequence, payload, metadata)
}

// CreateHeartbeat creates a heartbeat message for connection management.
func CreateHeartbeat(sessionID *string, sequence int) *WSMessage {
	wsData := &WSData{Primary: wsDict("status", "alive")}
	payload := &WSPayload{Entity: EntityTypeMultiple, Action: ActionTypeUpdate, Data: wsData}
	metadata := &WSMetadata{Source: SourceTypeSystem, SessionID: sessionID, Immediate: true}
	return NewHeartbeatMessage(sequence, payload, metadata)
}

// CreateError creates an error message with detailed context.
func CreateError(errorMessage string, errorCode *string, errorDetails *entities.OrderedMap[any],
	sessionID, correlationID *string, sequence int) *WSMessage {

	errorData := wsDict("message", errorMessage, "timestamp", value_objects.IsoFormat(nowUTC()))
	if errorCode != nil && *errorCode != "" {
		errorData.Set("code", *errorCode)
	}
	if errorDetails != nil && errorDetails.Len() > 0 {
		errorData.Set("details", errorDetails)
	}

	wsData := &WSData{Primary: errorData}
	payload := &WSPayload{Entity: EntityTypeMultiple, Action: ActionTypeUpdate, Data: wsData}
	metadata := &WSMetadata{Source: SourceTypeSystem, SessionID: sessionID, CorrelationID: correlationID, Immediate: true}
	return NewErrorMessage(sequence, payload, metadata)
}

// CreateSync creates a sync message for client reconnection.
func CreateSync(syncData *entities.OrderedMap[any], sessionID, userID *string, sequence int) *WSMessage {
	wsData := &WSData{Primary: syncData}
	payload := &WSPayload{Entity: EntityTypeMultiple, Action: ActionTypeUpdate, Data: wsData}
	metadata := &WSMetadata{Source: SourceTypeSystem, SessionID: sessionID, UserID: userID, Immediate: true}
	return NewSyncMessage(sequence, payload, metadata)
}

// GetMessageSize is the size of a message in bytes when serialized to JSON.
func GetMessageSize(message *WSMessage) int {
	return len([]byte(message.ModelDumpJSON()))
}

// IsMessageSizeValid reports whether a message is within the 64KB limit.
func IsMessageSizeValid(message *WSMessage) bool {
	return GetMessageSize(message) <= MaxMessageSizeBytes
}
