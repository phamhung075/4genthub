package httpapp

// seat_status_mount.go stores and serves the status a per-PC bridge reports:
//
//	POST /api/v2/openrig/seat-status
//	GET  /api/v2/openrig/machines
//
// A report replaces its machine's seat set, agent snapshot and edge set. Every string field of a
// report is scanned for credentials before anything is stored. Both routes take the
// user token and are tenant-scoped by the caller's user id; the POST names its machine in the body.

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"time"
	"unicode/utf8"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	"agenthub/fastmcp/seat_management/domain/commpolicy"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seatsync"
	"agenthub/fastmcp/seat_management/domain/secretscan"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

const (
	seatStatusMaxBody   = 1 << 20
	seatStatusMaxSeats  = 500
	seatStatusMaxDetail = 200
	seatStatusMaxField  = 128
	// seatStatusMaxEdges caps one machine's reported topology. A room's edge list is small - the
	// five kinds over the room's seats - so the cap is a body-size guard, not a product limit.
	seatStatusMaxEdges  = 1000
	machineOnlineWindow = 90 * time.Second
)

var (
	seatStates    = map[string]bool{"running": true, "idle": true, "blocked": true, "stopped": true, "unknown": true}
	agentStatuses = map[string]bool{"idle": true, "working": true, "blocked": true, "done": true, "unknown": true}
)

// validSeatRuntime reports whether a status report may carry runtime: a runtime the seat
// renderer supports, or one of the two values the bridge adds for a seat it cannot classify.
func validSeatRuntime(runtime string) bool {
	return resolver.CheckRuntime(runtime) == nil || runtime == "terminal" || runtime == "unknown"
}

// seatStatusSource is the repository surface the status routes use.
type seatStatusSource interface {
	ReplaceSnapshot(ctx context.Context, userID string, machine repositories.Machine) error
	List(ctx context.Context, userID string) ([]repositories.Machine, error)
}

// newSeatStatusSource is a package variable so tests can substitute a fake without a database.
var newSeatStatusSource = func(sessions *database.SessionManager) (seatStatusSource, error) {
	return seatorm.NewORMMachineStatusRepository(sessions)
}

// seatStatusNow is the server clock; tests substitute a fixed one.
var seatStatusNow = time.Now

type seatStatusReport struct {
	MachineID  string                `json:"machine_id"`
	ReportedAt string                `json:"reported_at"`
	Seats      []seatStatusReportRow `json:"seats"`
	Agents     []seatStatusAgent     `json:"agents"`
	// Edges is the machine's topology, flat rather than nested per rig: one entry per directed
	// link. It is optional in the wire sense - a bridge that sends no `edges` key reports no
	// topology, and a report replaces the machine's edge set like its seats and agents.
	Edges []seatStatusEdge `json:"edges"`
}

// seatStatusEdge is one reported link: the room (pod) it belongs to and the two ends, with the
// kind one of OpenRig's five. The ends are `from` and `to` on the wire, which is also how a
// rendered rigspec names them.
type seatStatusEdge struct {
	Room string `json:"room"`
	From string `json:"from"`
	To   string `json:"to"`
	Kind string `json:"kind"`
}

type seatStatusReportRow struct {
	Room    string `json:"room"`
	Seat    string `json:"seat"`
	State   string `json:"state"`
	Runtime string `json:"runtime"`
	// PinnedHash is the hash of the resolved-seat snapshot the reporting seat actually has PINNED,
	// which the bridge reads from the seat's own pin. It is NOT the cloud's intended hash - that is
	// the stored seat's ExpectedHash, and the sync verdict compares this one against it. The name
	// says which, because a bare `hash` left an operator unable to tell the two apart.
	PinnedHash string `json:"pinned_hash"`
	Detail     string `json:"detail"`
	Redacted   bool   `json:"redacted"`
}

type seatStatusAgent struct {
	Agent  string `json:"agent"`
	Status string `json:"status"`
	PaneID string `json:"pane_id"`
}

func mountSeatStatusRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("POST /api/v2/openrig/seat-status", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handlePostSeatStatus(w, r, u, sessions)
	}))
	mux.HandleFunc("GET /api/v2/openrig/machines", authed(func(w http.ResponseWriter, r *http.Request, u *authdomain.User) {
		handleListMachines(w, r, u, sessions)
	}))
}

func seatStatusSourceFor(w http.ResponseWriter, sessions *database.SessionManager) (seatStatusSource, bool) {
	source, err := newSeatStatusSource(sessions)
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return nil, false
	}
	return source, true
}

func handlePostSeatStatus(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	raw, ok := readSeatStatusBody(w, r)
	if !ok {
		return
	}
	var report seatStatusReport
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&report); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	var generic any
	if err := json.Unmarshal(raw, &generic); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	if path, found := findSecret(generic, ""); found {
		writeSeatStatusError(w, http.StatusUnprocessableEntity, "secret detected in field "+path)
		return
	}
	machine, err := report.toMachine(seatStatusNow().UTC())
	if err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return
	}
	source, ok := seatStatusSourceFor(w, sessions)
	if !ok {
		return
	}
	if err := source.ReplaceSnapshot(r.Context(), userID(u), *machine); err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	// The machine is told what the cloud expects for what it just reported: the same expected
	// hash and verdict GET /machines derives, read back through the same join so the two views
	// cannot disagree. A client records the hash it was last in sync with from this answer.
	machines, err := source.List(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("machine_id", machine.MachineID)
	body.Set("seats", len(machine.Seats))
	body.Set("verdicts", seatVerdicts(machines, machine.MachineID))
	writeJSON(w, http.StatusOK, body)
}

// seatVerdicts is the per-seat expected hash and sync verdict for one machine, carrying the same
// two derived fields machineBody renders per seat (expected_hash and sync) and nothing else: the
// other fields that route sets describe the reported state, which this answer does not repeat. No
// machine matches (or it has no seats) means no verdicts.
func seatVerdicts(machines []repositories.Machine, machineID string) []any {
	for _, m := range machines {
		if m.MachineID != machineID {
			continue
		}
		out := make([]any, 0, len(m.Seats))
		for _, s := range m.Seats {
			verdict := entities.NewOrderedMap[any]()
			verdict.Set("room", s.Room)
			verdict.Set("seat", s.Seat)
			verdict.Set("expected_hash", s.ExpectedHash)
			verdict.Set("sync", seatsync.Sync(s.RunningHash, s.ExpectedHash))
			out = append(out, verdict)
		}
		return out
	}
	return []any{}
}

func readSeatStatusBody(w http.ResponseWriter, r *http.Request) ([]byte, bool) {
	buf := new(bytes.Buffer)
	if _, err := buf.ReadFrom(http.MaxBytesReader(w, r.Body, seatStatusMaxBody)); err != nil {
		writeDetail(w, http.StatusBadRequest, err.Error())
		return nil, false
	}
	return buf.Bytes(), true
}

func writeSeatStatusError(w http.ResponseWriter, status int, message string) {
	body := entities.NewOrderedMap[any]()
	body.Set("success", false)
	body.Set("error", message)
	writeJSON(w, status, body)
}

// findSecret walks the decoded JSON and returns the JSON path of the first string
// holding a credential; the value itself is never returned.
func findSecret(v any, path string) (string, bool) {
	switch x := v.(type) {
	case string:
		return path, secretscan.Contains(x)
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			child := k
			if path != "" {
				child = path + "." + k
			}
			if p, found := findSecret(x[k], child); found {
				return p, true
			}
		}
	case []any:
		for i, item := range x {
			if p, found := findSecret(item, path+"["+strconv.Itoa(i)+"]"); found {
				return p, true
			}
		}
	}
	return "", false
}

// toMachine validates the report and converts it; lastSeen is the server time.
func (rep *seatStatusReport) toMachine(lastSeen time.Time) (*repositories.Machine, error) {
	if err := repositories.ValidateName("machine id", rep.MachineID); err != nil {
		return nil, err
	}
	reportedAt, err := time.Parse(time.RFC3339, rep.ReportedAt)
	if err != nil {
		return nil, fmt.Errorf("reported_at must be RFC3339: %v", err)
	}
	if len(rep.Seats) > seatStatusMaxSeats {
		return nil, fmt.Errorf("seats cannot exceed %d", seatStatusMaxSeats)
	}
	if len(rep.Edges) > seatStatusMaxEdges {
		return nil, fmt.Errorf("edges cannot exceed %d", seatStatusMaxEdges)
	}
	machine := &repositories.Machine{
		MachineID: rep.MachineID,
		LastSeen:  lastSeen,
		Seats:     make([]repositories.SeatStatus, 0, len(rep.Seats)),
		Agents:    make([]repositories.MachineAgent, 0, len(rep.Agents)),
		Edges:     make([]repositories.MachineEdge, 0, len(rep.Edges)),
	}
	seen := make(map[[2]string]bool, len(rep.Seats))
	for i, s := range rep.Seats {
		if err := repositories.ValidateName("room slug", s.Room); err != nil {
			return nil, fmt.Errorf("seats[%d]: %v", i, err)
		}
		if err := repositories.ValidateName("seat key", s.Seat); err != nil {
			return nil, fmt.Errorf("seats[%d]: %v", i, err)
		}
		if !seatStates[s.State] {
			return nil, fmt.Errorf("seats[%d].state %q is invalid", i, s.State)
		}
		if !validSeatRuntime(s.Runtime) {
			return nil, fmt.Errorf("seats[%d].runtime %q is invalid", i, s.Runtime)
		}
		if utf8.RuneCountInString(s.Detail) > seatStatusMaxDetail {
			return nil, fmt.Errorf("seats[%d].detail cannot exceed %d characters", i, seatStatusMaxDetail)
		}
		if len(s.PinnedHash) > seatStatusMaxField {
			return nil, fmt.Errorf("seats[%d].pinned_hash cannot exceed %d characters", i, seatStatusMaxField)
		}
		key := [2]string{s.Room, s.Seat}
		if seen[key] {
			return nil, fmt.Errorf("seats[%d]: duplicate seat %s.%s", i, s.Room, s.Seat)
		}
		seen[key] = true
		machine.Seats = append(machine.Seats, repositories.SeatStatus{
			Room: s.Room, Seat: s.Seat, State: s.State, Runtime: s.Runtime,
			RunningHash: s.PinnedHash, Detail: s.Detail, Redacted: s.Redacted, ReportedAt: reportedAt.UTC(),
		})
	}
	for i, a := range rep.Agents {
		if a.Agent == "" || len(a.Agent) > seatStatusMaxField {
			return nil, fmt.Errorf("agents[%d].agent must be 1-%d characters", i, seatStatusMaxField)
		}
		if !agentStatuses[a.Status] {
			return nil, fmt.Errorf("agents[%d].status %q is invalid", i, a.Status)
		}
		if len(a.PaneID) > seatStatusMaxField {
			return nil, fmt.Errorf("agents[%d].pane_id cannot exceed %d characters", i, seatStatusMaxField)
		}
		machine.Agents = append(machine.Agents, repositories.MachineAgent{Agent: a.Agent, Status: a.Status, PaneID: a.PaneID})
	}
	// The topology. A repeated link is refused rather than stored twice: the table's primary key
	// would silently collapse it, so a bridge whose dump carries a duplicate learns that its own
	// dump is wrong instead of reading back fewer edges than it sent.
	seenEdges := make(map[repositories.MachineEdge]bool, len(rep.Edges))
	for i, e := range rep.Edges {
		if err := repositories.ValidateName("room slug", e.Room); err != nil {
			return nil, fmt.Errorf("edges[%d]: %v", i, err)
		}
		if err := repositories.ValidateName("seat key", e.From); err != nil {
			return nil, fmt.Errorf("edges[%d]: %v", i, err)
		}
		if err := repositories.ValidateName("seat key", e.To); err != nil {
			return nil, fmt.Errorf("edges[%d]: %v", i, err)
		}
		// The kind vocabulary is commpolicy's, so a kind added to OpenRig's language is accepted
		// here without a second list to keep in step.
		if !commpolicy.ValidKind(commpolicy.LinkKind(e.Kind)) {
			return nil, fmt.Errorf("edges[%d].kind %q is invalid", i, e.Kind)
		}
		if e.From == e.To {
			return nil, fmt.Errorf("edges[%d]: from and to are the same seat %q", i, e.From)
		}
		edge := repositories.MachineEdge{Room: e.Room, From: e.From, To: e.To, Kind: e.Kind}
		if seenEdges[edge] {
			return nil, fmt.Errorf("edges[%d]: duplicate edge %s.%s -> %s (%s)", i, e.Room, e.From, e.To, e.Kind)
		}
		seenEdges[edge] = true
		machine.Edges = append(machine.Edges, edge)
	}
	return machine, nil
}

func handleListMachines(w http.ResponseWriter, r *http.Request, u *authdomain.User, sessions *database.SessionManager) {
	source, ok := seatStatusSourceFor(w, sessions)
	if !ok {
		return
	}
	machines, err := source.List(r.Context(), userID(u))
	if err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	now := seatStatusNow()
	out := make([]any, 0, len(machines))
	for i := range machines {
		out = append(out, machineBody(&machines[i], now))
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("machines", out)
	writeJSON(w, http.StatusOK, body)
}

func machineBody(m *repositories.Machine, now time.Time) *entities.OrderedMap[any] {
	seats := make([]any, 0, len(m.Seats))
	for _, s := range m.Seats {
		seat := entities.NewOrderedMap[any]()
		seat.Set("room", s.Room)
		seat.Set("seat", s.Seat)
		seat.Set("state", s.State)
		seat.Set("runtime", s.Runtime)
		seat.Set("pinned_hash", s.RunningHash)
		seat.Set("expected_hash", s.ExpectedHash)
		seat.Set("sync", seatsync.Sync(s.RunningHash, s.ExpectedHash))
		seat.Set("detail", s.Detail)
		seat.Set("redacted", s.Redacted)
		seat.Set("reported_at", s.ReportedAt.UTC().Format(time.RFC3339))
		seats = append(seats, seat)
	}
	agents := make([]any, 0, len(m.Agents))
	for _, a := range m.Agents {
		agent := entities.NewOrderedMap[any]()
		agent.Set("agent", a.Agent)
		agent.Set("status", a.Status)
		agent.Set("pane_id", a.PaneID)
		agents = append(agents, agent)
	}
	// Always present, empty when the machine reported none, so a consumer reads the topology the
	// same way whether or not the bridge that fed this row sends edges.
	edges := make([]any, 0, len(m.Edges))
	for _, e := range m.Edges {
		edge := entities.NewOrderedMap[any]()
		edge.Set("room", e.Room)
		edge.Set("from", e.From)
		edge.Set("to", e.To)
		edge.Set("kind", e.Kind)
		edges = append(edges, edge)
	}
	body := entities.NewOrderedMap[any]()
	body.Set("machine_id", m.MachineID)
	body.Set("last_seen", m.LastSeen.UTC().Format(time.RFC3339))
	body.Set("online", now.Sub(m.LastSeen) <= machineOnlineWindow)
	body.Set("seats", seats)
	body.Set("agents", agents)
	body.Set("edges", edges)
	return body
}
