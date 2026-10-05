package httpapp

// seat_status_mount.go stores and serves the status a per-PC bridge reports:
//
//	POST /api/v2/openrig/seat-status
//	GET  /api/v2/openrig/machines
//
// A report replaces its machine's seat set and agent snapshot. Every string field of a
// report is scanned for credentials before anything is stored. POST takes a machine token
// (see machine_token_mount.go) and stores under the token's user and machine; GET takes a
// user token and is tenant-scoped by the caller's user id.

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
}

type seatStatusReportRow struct {
	Room     string `json:"room"`
	Seat     string `json:"seat"`
	State    string `json:"state"`
	Runtime  string `json:"runtime"`
	Hash     string `json:"hash"`
	Detail   string `json:"detail"`
	Redacted bool   `json:"redacted"`
}

type seatStatusAgent struct {
	Agent  string `json:"agent"`
	Status string `json:"status"`
	PaneID string `json:"pane_id"`
}

func mountSeatStatusRoutes(mux *http.ServeMux, sessions *database.SessionManager) {
	mux.HandleFunc("POST /api/v2/openrig/seat-status", machineAuthed(sessions, func(w http.ResponseWriter, r *http.Request, token *repositories.MachineToken) {
		handlePostSeatStatus(w, r, token, sessions)
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

func handlePostSeatStatus(w http.ResponseWriter, r *http.Request, token *repositories.MachineToken, sessions *database.SessionManager) {
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
	if machine.MachineID != token.MachineID {
		writeDetail(w, http.StatusForbidden, "token is bound to machine \""+token.MachineID+"\"")
		return
	}
	source, ok := seatStatusSourceFor(w, sessions)
	if !ok {
		return
	}
	if err := source.ReplaceSnapshot(r.Context(), token.UserID, *machine); err != nil {
		writeDetail(w, http.StatusInternalServerError, err.Error())
		return
	}
	body := entities.NewOrderedMap[any]()
	body.Set("success", true)
	body.Set("machine_id", machine.MachineID)
	body.Set("seats", len(machine.Seats))
	writeJSON(w, http.StatusOK, body)
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
	machine := &repositories.Machine{
		MachineID: rep.MachineID,
		LastSeen:  lastSeen,
		Seats:     make([]repositories.SeatStatus, 0, len(rep.Seats)),
		Agents:    make([]repositories.MachineAgent, 0, len(rep.Agents)),
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
		if len(s.Hash) > seatStatusMaxField {
			return nil, fmt.Errorf("seats[%d].hash cannot exceed %d characters", i, seatStatusMaxField)
		}
		key := [2]string{s.Room, s.Seat}
		if seen[key] {
			return nil, fmt.Errorf("seats[%d]: duplicate seat %s.%s", i, s.Room, s.Seat)
		}
		seen[key] = true
		machine.Seats = append(machine.Seats, repositories.SeatStatus{
			Room: s.Room, Seat: s.Seat, State: s.State, Runtime: s.Runtime,
			RunningHash: s.Hash, Detail: s.Detail, Redacted: s.Redacted, ReportedAt: reportedAt.UTC(),
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
		seat.Set("hash", s.RunningHash)
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
	body := entities.NewOrderedMap[any]()
	body.Set("machine_id", m.MachineID)
	body.Set("last_seen", m.LastSeen.UTC().Format(time.RFC3339))
	body.Set("online", now.Sub(m.LastSeen) <= machineOnlineWindow)
	body.Set("seats", seats)
	body.Set("agents", agents)
	return body
}
