package value_objects

import (
	"fmt"
	"math"
	"math/big"
	"reflect"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
)

// CoordinationType: Types of agent coordination patterns
type CoordinationType string

const (
	CoordinationTypeHandoff       CoordinationType = "handoff"
	CoordinationTypeParallel      CoordinationType = "parallel"
	CoordinationTypeReview        CoordinationType = "review"
	CoordinationTypeEscalation    CoordinationType = "escalation"
	CoordinationTypeCollaboration CoordinationType = "collaboration"
	CoordinationTypeDelegation    CoordinationType = "delegation"
	CoordinationTypeConsultation  CoordinationType = "consultation"
)

// CoordinationTypeValues lists all members in declaration order.
var CoordinationTypeValues = []CoordinationType{CoordinationTypeHandoff, CoordinationTypeParallel, CoordinationTypeReview, CoordinationTypeEscalation, CoordinationTypeCollaboration, CoordinationTypeDelegation, CoordinationTypeConsultation}

func (e CoordinationType) String() string { return string(e) }

// HandoffStatus: Status of work handoff between agents
type HandoffStatus string

const (
	HandoffStatusPending    HandoffStatus = "pending"
	HandoffStatusAccepted   HandoffStatus = "accepted"
	HandoffStatusRejected   HandoffStatus = "rejected"
	HandoffStatusInProgress HandoffStatus = "in_progress"
	HandoffStatusCompleted  HandoffStatus = "completed"
	HandoffStatusCancelled  HandoffStatus = "cancelled"
)

// HandoffStatusValues lists all members in declaration order.
var HandoffStatusValues = []HandoffStatus{HandoffStatusPending, HandoffStatusAccepted, HandoffStatusRejected, HandoffStatusInProgress, HandoffStatusCompleted, HandoffStatusCancelled}

func (e HandoffStatus) String() string { return string(e) }

// ConflictType: Types of conflicts that can occur
type ConflictType string

const (
	ConflictTypeConcurrentEdit       ConflictType = "concurrent_edit"
	ConflictTypeResourceContention   ConflictType = "resource_contention"
	ConflictTypePriorityDisagreement ConflictType = "priority_disagreement"
	ConflictTypeApproachDifference   ConflictType = "approach_difference"
	ConflictTypeDependencyConflict   ConflictType = "dependency_conflict"
	ConflictTypeScheduleConflict     ConflictType = "schedule_conflict"
)

// ConflictTypeValues lists all members in declaration order.
var ConflictTypeValues = []ConflictType{ConflictTypeConcurrentEdit, ConflictTypeResourceContention, ConflictTypePriorityDisagreement, ConflictTypeApproachDifference, ConflictTypeDependencyConflict, ConflictTypeScheduleConflict}

func (e ConflictType) String() string { return string(e) }

// ResolutionStrategy: Strategies for conflict resolution
type ResolutionStrategy string

const (
	ResolutionStrategyMerge       ResolutionStrategy = "merge"
	ResolutionStrategyOverride    ResolutionStrategy = "override"
	ResolutionStrategyVote        ResolutionStrategy = "vote"
	ResolutionStrategyEscalate    ResolutionStrategy = "escalate"
	ResolutionStrategyCollaborate ResolutionStrategy = "collaborate"
	ResolutionStrategyDefer       ResolutionStrategy = "defer"
)

// ResolutionStrategyValues lists all members in declaration order.
var ResolutionStrategyValues = []ResolutionStrategy{ResolutionStrategyMerge, ResolutionStrategyOverride, ResolutionStrategyVote, ResolutionStrategyEscalate, ResolutionStrategyCollaborate, ResolutionStrategyDefer}

func (e ResolutionStrategy) String() string { return string(e) }

// CoordinationStrategy: Strategies for coordinating work between agents
type CoordinationStrategy string

const (
	CoordinationStrategyRoundRobin     CoordinationStrategy = "round_robin"
	CoordinationStrategyExpertiseBased CoordinationStrategy = "expertise_based"
	CoordinationStrategyLoadBalancing  CoordinationStrategy = "load_balancing"
	CoordinationStrategyPriorityFirst  CoordinationStrategy = "priority_first"
	CoordinationStrategyCollaborative  CoordinationStrategy = "collaborative"
	CoordinationStrategySequential     CoordinationStrategy = "sequential"
	CoordinationStrategyParallel       CoordinationStrategy = "parallel"
)

// CoordinationStrategyValues lists all members in declaration order.
var CoordinationStrategyValues = []CoordinationStrategy{CoordinationStrategyRoundRobin, CoordinationStrategyExpertiseBased, CoordinationStrategyLoadBalancing, CoordinationStrategyPriorityFirst, CoordinationStrategyCollaborative, CoordinationStrategySequential, CoordinationStrategyParallel}

func (e CoordinationStrategy) String() string { return string(e) }

// now is the clock used for expiry checks (UTC, like datetime.now(UTC)).
var now = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// IsoFormat mirrors Python datetime.IsoFormat() for timezone-aware values.
func IsoFormat(t time.Time) string {
	s := t.Format("2006-01-02T15:04:05")
	if us := t.Nanosecond() / 1000; us != 0 {
		s += fmt.Sprintf(".%06d", us)
	}
	_, off := t.Zone()
	sign := "+"
	if off < 0 {
		sign, off = "-", -off
	}
	return s + fmt.Sprintf("%s%02d:%02d", sign, off/3600, off%3600/60)
}

func isoOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return IsoFormat(*t)
}

// CoordinationRequest is a request for coordination between agents.
type CoordinationRequest struct {
	RequestID          string
	CoordinationType   CoordinationType
	RequestingAgentID  string
	TargetAgentID      string
	TaskID             string
	CreatedAt          time.Time
	Reason             string
	Context            map[string]any
	Priority           string // low, medium, high, critical (default "medium")
	Deadline           *time.Time
	HandoffNotes       *string
	CompletionCriteria []string
	ReviewItems        []string
	ReviewChecklist    map[string]bool
}

// IsExpired: deadline set and passed.
func (r CoordinationRequest) IsExpired() bool { return r.Deadline != nil && now().After(*r.Deadline) }

// ToNotification converts to the notification format for the target agent.
func (r CoordinationRequest) ToNotification() map[string]any {
	return map[string]any{
		"type":       "coordination_" + string(r.CoordinationType),
		"from_agent": r.RequestingAgentID,
		"task_id":    r.TaskID,
		"priority":   r.Priority,
		"reason":     r.Reason,
		"created_at": IsoFormat(r.CreatedAt),
		"deadline":   isoOrNil(r.Deadline),
		"context":    r.Context,
	}
}

// WorkAssignment is an assignment of work to an agent.
type WorkAssignment struct {
	AssignmentID        string
	TaskID              string
	AssignedAgentID     string
	AssignedByAgentID   string
	AssignedAt          time.Time
	Role                *string
	Responsibilities    []string
	Deliverables        []string
	Constraints         map[string]any
	EstimatedHours      *float64
	DueDate             *time.Time
	CollaboratingAgents []string
	ReportingTo         *string
}

// IsOverdue: due date set and passed.
func (a WorkAssignment) IsOverdue() bool { return a.DueDate != nil && now().After(*a.DueDate) }

// ToTaskContext converts to task context format. As in Python, due_date is the
// raw datetime (not ISO-formatted), or nil.
func (a WorkAssignment) ToTaskContext() map[string]any {
	var due any
	if a.DueDate != nil {
		due = *a.DueDate
	}
	var role any
	if a.Role != nil {
		role = *a.Role
	}
	return map[string]any{"assignment": map[string]any{
		"agent_id":         a.AssignedAgentID,
		"role":             role,
		"assigned_by":      a.AssignedByAgentID,
		"assigned_at":      IsoFormat(a.AssignedAt),
		"responsibilities": a.Responsibilities,
		"deliverables":     a.Deliverables,
		"collaborators":    a.CollaboratingAgents,
		"due_date":         due,
	}}
}

// pyEnumStr mirrors str() of a plain Python Enum member, e.g. "HandoffStatus.PENDING".
func pyEnumStr(typeName, value string) string { return typeName + "." + strings.ToUpper(value) }

// WorkHandoff is a handoff of work between agents (mutable).
type WorkHandoff struct {
	HandoffID          string
	FromAgentID        string
	ToAgentID          string
	TaskID             string
	InitiatedAt        time.Time
	Status             HandoffStatus
	WorkSummary        string
	CompletedItems     []string
	RemainingItems     []string
	KnownIssues        []string
	HandoffNotes       string
	Artifacts          map[string]string // name -> location
	DocumentationLinks []string
	AcceptedAt         *time.Time
	CompletedAt        *time.Time
	RejectionReason    *string
}

// NewWorkHandoff applies the Python defaults (status PENDING).
func NewWorkHandoff(handoffID, from, to, taskID string, initiatedAt time.Time) *WorkHandoff {
	return &WorkHandoff{HandoffID: handoffID, FromAgentID: from, ToAgentID: to, TaskID: taskID,
		InitiatedAt: initiatedAt, Status: HandoffStatusPending, Artifacts: map[string]string{}}
}

// Accept moves PENDING → ACCEPTED.
func (h *WorkHandoff) Accept() error {
	if h.Status != HandoffStatusPending {
		return valueErrorf("Cannot accept handoff in status %s", pyEnumStr("HandoffStatus", string(h.Status)))
	}
	h.Status = HandoffStatusAccepted
	t := now()
	h.AcceptedAt = &t
	return nil
}

// Reject moves PENDING → REJECTED with a reason.
func (h *WorkHandoff) Reject(reason string) error {
	if h.Status != HandoffStatusPending {
		return valueErrorf("Cannot reject handoff in status %s", pyEnumStr("HandoffStatus", string(h.Status)))
	}
	h.Status = HandoffStatusRejected
	h.RejectionReason = &reason
	return nil
}

// Complete moves IN_PROGRESS → COMPLETED.
func (h *WorkHandoff) Complete() error {
	if h.Status != HandoffStatusInProgress {
		return valueErrorf("Cannot complete handoff in status %s", pyEnumStr("HandoffStatus", string(h.Status)))
	}
	h.Status = HandoffStatusCompleted
	t := now()
	h.CompletedAt = &t
	return nil
}

// ToHandoffPackage creates the complete handoff package.
func (h *WorkHandoff) ToHandoffPackage() map[string]any {
	return map[string]any{
		"handoff_id":    h.HandoffID,
		"from_agent":    h.FromAgentID,
		"to_agent":      h.ToAgentID,
		"task_id":       h.TaskID,
		"status":        string(h.Status),
		"summary":       h.WorkSummary,
		"completed":     h.CompletedItems,
		"remaining":     h.RemainingItems,
		"issues":        h.KnownIssues,
		"notes":         h.HandoffNotes,
		"artifacts":     h.Artifacts,
		"documentation": h.DocumentationLinks,
		"timeline": map[string]any{
			"initiated": IsoFormat(h.InitiatedAt),
			"accepted":  isoOrNil(h.AcceptedAt),
			"completed": isoOrNil(h.CompletedAt),
		},
	}
}

// CoordinationConflictResolution is coordination.ConflictResolution (the
// dataclass); rule_enums.ConflictResolution owns the plain name.
type CoordinationConflictResolution struct {
	ConflictID          string
	ConflictType        ConflictType
	InvolvedAgents      []string
	TaskID              string
	DetectedAt          time.Time
	Description         string
	ConflictingElements map[string]any
	ImpactAssessment    string // low, medium, high, critical (default "low")
	ResolutionStrategy  *ResolutionStrategy
	ResolvedBy          *string
	ResolutionDetails   *string
	ResolvedAt          *time.Time
	Votes               map[string]string // agent_id -> choice
}

// IsResolved: resolved_at set.
func (c *CoordinationConflictResolution) IsResolved() bool { return c.ResolvedAt != nil }

// Resolve records the resolution; errors if already resolved.
func (c *CoordinationConflictResolution) Resolve(strategy ResolutionStrategy, resolvedBy, details string) error {
	if c.IsResolved() {
		return valueErrorf("Conflict already resolved")
	}
	c.ResolutionStrategy = &strategy
	c.ResolvedBy = &resolvedBy
	c.ResolutionDetails = &details
	t := now()
	c.ResolvedAt = &t
	return nil
}

// AddVote records an agent's vote.
func (c *CoordinationConflictResolution) AddVote(agentID, choice string) {
	if c.Votes == nil {
		c.Votes = map[string]string{}
	}
	c.Votes[agentID] = choice
}

// GetVoteSummary counts votes per choice.
func (c *CoordinationConflictResolution) GetVoteSummary() map[string]int {
	summary := map[string]int{}
	for _, choice := range c.Votes {
		summary[choice]++
	}
	return summary
}

// AgentCommunication is a communication between agents.
type AgentCommunication struct {
	MessageID        string
	FromAgentID      string
	ToAgentIDs       []string // can be broadcast
	TaskID           *string
	SentAt           time.Time
	MessageType      string // status_update, question, response, notification
	Subject          string
	Content          string
	Priority         string // low, normal, high, urgent (default "normal")
	InReplyTo        *string
	ThreadID         *string
	RequiresResponse bool
	ResponseDeadline *time.Time
	Attachments      []string
}

// IsBroadcast: more than one recipient.
func (c AgentCommunication) IsBroadcast() bool { return len(c.ToAgentIDs) > 1 }

// NeedsUrgentResponse: response required and (high/urgent priority or deadline within 2h).
func (c AgentCommunication) NeedsUrgentResponse() bool {
	if !c.RequiresResponse {
		return false
	}
	if c.Priority == "high" || c.Priority == "urgent" {
		return true
	}
	if c.ResponseDeadline != nil {
		return PyTotalSeconds(c.ResponseDeadline.Sub(now()))/3600 <= 2
	}
	return false
}

// CoordinationMessage is a message for agent coordination and communication.
type CoordinationMessage struct {
	MessageID        string
	MessageType      string // handoff_request, status_update, resource_request, ...
	FromAgentID      string
	ToAgentID        *string // nil for broadcast
	Timestamp        time.Time
	Payload          map[string]any
	Priority         string // default "normal"
	RequiresResponse bool
	CorrelationID    *string
}

// IsBroadcast: no target agent.
func (m CoordinationMessage) IsBroadcast() bool { return m.ToAgentID == nil }

// ToJSON converts to a JSON-serializable map.
func (m CoordinationMessage) ToJSON() map[string]any {
	var to, corr any
	if m.ToAgentID != nil {
		to = *m.ToAgentID
	}
	if m.CorrelationID != nil {
		corr = *m.CorrelationID
	}
	return map[string]any{
		"message_id": m.MessageID, "message_type": m.MessageType, "from_agent_id": m.FromAgentID,
		"to_agent_id": to, "timestamp": IsoFormat(m.Timestamp), "payload": m.Payload,
		"priority": m.Priority, "requires_response": m.RequiresResponse, "correlation_id": corr,
	}
}

// PyStr mirrors Python str(x) for the JSON-like values that reach error text:
// None, bool (True/False), int, float (repr), str, and lists/dicts in Python repr form.
func PyStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return PyRepr(v)
}

// PyRepr mirrors Python repr(x) for JSON-like values (dict keys are sorted).
func PyRepr(v any) string {
	if v == nil {
		return "None"
	}
	if bi, ok := v.(*big.Int); ok {
		return bi.String()
	}
	if o, ok := v.(OrderedAny); ok {
		keys := o.KeysAny()
		parts := make([]string, len(keys))
		for i, k := range keys {
			parts[i] = pyQuote(k) + ": " + PyRepr(o.GetAny(k))
		}
		return "{" + strings.Join(parts, ", ") + "}"
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.String:
		return pyQuote(rv.String())
	case reflect.Bool:
		if rv.Bool() {
			return "True"
		}
		return "False"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return strconv.FormatInt(rv.Int(), 10)
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return strconv.FormatUint(rv.Uint(), 10)
	case reflect.Float32, reflect.Float64:
		return pyFloatRepr(rv.Float())
	case reflect.Slice, reflect.Array:
		parts := make([]string, rv.Len())
		for i := range parts {
			parts[i] = PyRepr(rv.Index(i).Interface())
		}
		return "[" + strings.Join(parts, ", ") + "]"
	case reflect.Map:
		keys := rv.MapKeys()
		sort.Slice(keys, func(i, j int) bool { return fmt.Sprint(keys[i]) < fmt.Sprint(keys[j]) })
		parts := make([]string, len(keys))
		for i, k := range keys {
			parts[i] = PyRepr(k.Interface()) + ": " + PyRepr(rv.MapIndex(k).Interface())
		}
		return "{" + strings.Join(parts, ", ") + "}"
	case reflect.Pointer:
		if rv.IsNil() {
			return "None"
		}
		return PyRepr(rv.Elem().Interface())
	}
	return fmt.Sprint(v)
}

func pyFloatRepr(f float64) string {
	switch {
	case math.IsNaN(f):
		return "nan"
	case math.IsInf(f, 1):
		return "inf"
	case math.IsInf(f, -1):
		return "-inf"
	}
	e := strconv.FormatFloat(f, 'e', -1, 64)
	exp, _ := strconv.Atoi(e[strings.IndexByte(e, 'e')+1:])
	if exp >= -4 && exp < 16 {
		s := strconv.FormatFloat(f, 'f', -1, 64)
		if !strings.Contains(s, ".") {
			s += ".0"
		}
		return s
	}
	return e
}

// pyQuote mirrors repr(str): single quotes unless the text has ' and no ", and non-printable
// characters (Unicode Cc/Cf/Cs/Co/Cn/Zl/Zp/Zs except space) are escaped as \xhh, \uhhhh or \Uhhhhhhhh.
// Go's Unicode tables (15.0) are older than Python 3.14's (16.0): characters assigned in 16.0 are
// escaped here but printed raw by Python (see MIGRATION.md).
func pyQuote(s string) string {
	q := byte('\'')
	if strings.Contains(s, "'") && !strings.Contains(s, "\"") {
		q = '"'
	}
	var b strings.Builder
	b.WriteByte(q)
	for _, r := range s {
		switch {
		case r == '\\':
			b.WriteString("\\\\")
		case r == '\n':
			b.WriteString("\\n")
		case r == '\r':
			b.WriteString("\\r")
		case r == '\t':
			b.WriteString("\\t")
		case r == rune(q):
			b.WriteString("\\" + string(q))
		case unicode.IsPrint(r): // printable per Python's isprintable (ASCII space included)
			b.WriteRune(r)
		case r < 0x100:
			fmt.Fprintf(&b, "\\x%02x", r)
		case r < 0x10000:
			fmt.Fprintf(&b, "\\u%04x", r)
		default:
			fmt.Fprintf(&b, "\\U%08x", r)
		}
	}
	b.WriteByte(q)
	return b.String()
}

// IsoFormatNaive mirrors isoformat() of a naive datetime (no UTC offset), e.g. datetime.utcnow().
func IsoFormatNaive(t time.Time) string {
	s := t.Format("2006-01-02T15:04:05")
	if us := t.Nanosecond() / 1000; us != 0 {
		s += fmt.Sprintf(".%06d", us)
	}
	return s
}

// PyTimedeltaStr mirrors str(timedelta): "H:MM:SS[.ffffff]" with an optional
// "N day(s), " prefix; negative durations floor to days like Python.
func PyTimedeltaStr(d time.Duration) string {
	days := pyDays(d)
	rem := d - time.Duration(days)*24*time.Hour
	h := int(rem / time.Hour)
	m := int(rem % time.Hour / time.Minute)
	s := int(rem % time.Minute / time.Second)
	us := int(rem % time.Second / time.Microsecond)
	out := fmt.Sprintf("%d:%02d:%02d", h, m, s)
	if us != 0 {
		out += fmt.Sprintf(".%06d", us)
	}
	if days != 0 {
		unit := "days"
		if days == 1 || days == -1 {
			unit = "day"
		}
		out = fmt.Sprintf("%d %s, %s", days, unit, out)
	}
	return out
}

// PyRound mirrors Python round(x, ndigits) for floats: the exact binary value
// is rounded half-to-even, which strconv's correctly rounded formatting matches.
func PyRound(x float64, ndigits int) float64 {
	if math.IsNaN(x) || math.IsInf(x, 0) {
		return x
	}
	r, _ := strconv.ParseFloat(strconv.FormatFloat(x, 'f', ndigits, 64), 64)
	return r
}

// PyTitle mirrors Python str.title(): the first cased letter of each run of
// cased letters is upper-cased and the rest lower-cased.
func PyTitle(s string) string {
	var b strings.Builder
	prevCased := false
	for _, r := range s {
		cased := unicode.IsUpper(r) || unicode.IsLower(r) || unicode.IsTitle(r)
		switch {
		case cased && !prevCased:
			b.WriteRune(unicode.ToTitle(r))
		case cased:
			b.WriteRune(unicode.ToLower(r))
		default:
			b.WriteRune(r)
		}
		prevCased = cased
	}
	return b.String()
}

// pyIsSpace is Python's str.isspace for one rune: Unicode whitespace plus the
// ASCII separators \x1c-\x1f (which Go's unicode.IsSpace excludes).
func pyIsSpace(r rune) bool {
	return unicode.IsSpace(r) || (r >= 0x1c && r <= 0x1f)
}

// PyStrip is Python's str.strip() with no arguments.
func PyStrip(s string) string { return strings.TrimFunc(s, pyIsSpace) }
