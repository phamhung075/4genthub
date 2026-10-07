package httpapp

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type fakeSeatStatus struct {
	byUser map[string]map[string]repositories.Machine
	err    error
	// expected is the cloud's expected hash per "room/seat", the value the repository's LEFT
	// JOIN to the seat's newest resolved snapshot supplies on read. ReplaceSnapshot is a no-op
	// for it (the write ignores ExpectedHash), so the fake applies it in List.
	expected map[string]string
}

func (f *fakeSeatStatus) ReplaceSnapshot(_ context.Context, userID string, m repositories.Machine) error {
	if f.err != nil {
		return f.err
	}
	if f.byUser == nil {
		f.byUser = map[string]map[string]repositories.Machine{}
	}
	if f.byUser[userID] == nil {
		f.byUser[userID] = map[string]repositories.Machine{}
	}
	f.byUser[userID][m.MachineID] = m
	return nil
}

func (f *fakeSeatStatus) List(_ context.Context, userID string) ([]repositories.Machine, error) {
	if f.err != nil {
		return nil, f.err
	}
	out := []repositories.Machine{}
	for _, m := range f.byUser[userID] {
		if f.expected != nil {
			seats := make([]repositories.SeatStatus, len(m.Seats))
			copy(seats, m.Seats)
			for i := range seats {
				seats[i].ExpectedHash = f.expected[seats[i].Room+"/"+seats[i].Seat]
			}
			m.Seats = seats
		}
		out = append(out, m)
	}
	return out, nil
}

var seatStatusTestNow = time.Date(2026, 10, 3, 12, 0, 0, 0, time.UTC)

// seatStatusTestToken is the machine token of machine pc-home of the test user.
const seatStatusTestToken = "mt_seat-status-test-token"

func seatStatusTestMux(t *testing.T, source seatStatusSource) *http.ServeMux {
	t.Helper()
	previous := newSeatStatusSource
	newSeatStatusSource = func(*database.SessionManager) (seatStatusSource, error) { return source, nil }
	previousNow := seatStatusNow
	seatStatusNow = func() time.Time { return seatStatusTestNow }
	previousTokens := newMachineTokenRepo
	tokens := &fakeMachineTokens{tokens: []*repositories.MachineToken{{
		ID: "tok", UserID: "11111111-1111-4111-8111-111111111111", MachineID: "pc-home",
		TokenHash: seatservices.HashMachineToken(seatStatusTestToken),
	}}}
	newMachineTokenRepo = func(*database.SessionManager) (repositories.MachineTokenRepository, error) { return tokens, nil }
	t.Cleanup(func() {
		newSeatStatusSource = previous
		seatStatusNow = previousNow
		newMachineTokenRepo = previousTokens
	})
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatStatusRoutes(mux, nil)
	return mux
}

func postSeatStatus(mux *http.ServeMux, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, "/api/v2/openrig/seat-status", strings.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+seatStatusTestToken)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

func getMachines(mux *http.ServeMux) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, "/api/v2/openrig/machines", nil)
	req.Header.Set("Authorization", "Bearer test-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

const validSeatStatusBody = `{"machine_id":"pc-home","reported_at":"2026-10-03T11:59:30Z",` +
	`"seats":[{"room":"eng","seat":"coder","state":"running","runtime":"claude-code","pinned_hash":"abc123","detail":"working","redacted":false}],` +
	`"agents":[{"agent":"claude","status":"idle","pane_id":"w5:p3"}]}`

func TestSeatStatusPostStoresAndGetServes(t *testing.T) {
	fake := &fakeSeatStatus{}
	mux := seatStatusTestMux(t, fake)

	rec := postSeatStatus(mux, validSeatStatusBody)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seats":1`) {
		t.Fatalf("POST = %d %s", rec.Code, rec.Body.String())
	}
	stored := fake.byUser["11111111-1111-4111-8111-111111111111"]["pc-home"]
	if !stored.LastSeen.Equal(seatStatusTestNow) || len(stored.Seats) != 1 || stored.Seats[0].RunningHash != "abc123" {
		t.Fatalf("stored = %+v", stored)
	}

	rec = getMachines(mux)
	var got struct {
		Success  bool `json:"success"`
		Machines []struct {
			MachineID string `json:"machine_id"`
			Online    bool   `json:"online"`
			Seats     []struct {
				Room, Seat, State, Runtime, Detail string
				PinnedHash                         string `json:"pinned_hash"`
				ReportedAt                         string `json:"reported_at"`
			} `json:"seats"`
			Agents []struct {
				Agent  string `json:"agent"`
				PaneID string `json:"pane_id"`
			} `json:"agents"`
		} `json:"machines"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v\n%s", err, rec.Body.String())
	}
	if len(got.Machines) != 1 || got.Machines[0].MachineID != "pc-home" || !got.Machines[0].Online ||
		len(got.Machines[0].Seats) != 1 || got.Machines[0].Seats[0].ReportedAt != "2026-10-03T11:59:30Z" ||
		len(got.Machines[0].Agents) != 1 || got.Machines[0].Agents[0].PaneID != "w5:p3" {
		t.Fatalf("GET = %s", rec.Body.String())
	}

	// THE ASSERTION THAT MATTERS, and it is why the field is named rather than left as `hash`: the two
	// hashes come from DIFFERENT SOURCES - the reported one is what the seat has PINNED, the expected one
	// is the cloud's newest stored snapshot - so a wiring that served the intended hash under
	// `pinned_hash` would satisfy every check above while telling an operator nothing. The fake's stored
	// expected hash is set to a value DIFFERENT from the posted one, so each field can only be right by
	// reading its own source, and the two must differ for the test to mean anything at all.
	fake.expected = map[string]string{"eng/coder": "cloud999"}
	if rec = getMachines(mux); rec.Code != http.StatusOK {
		t.Fatalf("GET after setting the expected hash = %d", rec.Code)
	}
	if body := rec.Body.String(); !strings.Contains(body, `"pinned_hash":"abc123","expected_hash":"cloud999"`) {
		t.Fatalf("the served pair must be the seat's PINNED hash and the cloud's EXPECTED one, got: %s", body)
	}
}

func TestSeatStatusGetMarksStaleMachineOffline(t *testing.T) {
	fake := &fakeSeatStatus{byUser: map[string]map[string]repositories.Machine{
		"11111111-1111-4111-8111-111111111111": {
			"edge":  {MachineID: "edge", LastSeen: seatStatusTestNow.Add(-91 * time.Second)},
			"fresh": {MachineID: "fresh", LastSeen: seatStatusTestNow.Add(-90 * time.Second)},
		},
		"someone-else": {"other": {MachineID: "other", LastSeen: seatStatusTestNow}},
	}}
	mux := seatStatusTestMux(t, fake)
	rec := getMachines(mux)
	var got struct {
		Machines []struct {
			MachineID string `json:"machine_id"`
			Online    bool   `json:"online"`
		} `json:"machines"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	online := map[string]bool{}
	for _, m := range got.Machines {
		online[m.MachineID] = m.Online
	}
	if len(online) != 2 || online["edge"] || !online["fresh"] {
		t.Fatalf("online = %v (other tenants must not appear; 91s is offline, 90s online)", online)
	}
}

// Every runtime the renderer supports can be reported, plus the two the bridge adds itself.
func TestSeatStatusPostAcceptsEverySeatRuntime(t *testing.T) {
	for _, runtime := range []string{resolver.RuntimeClaudeCode, resolver.RuntimeCodex, resolver.RuntimeAgy, resolver.RuntimeOmp, "terminal", "unknown"} {
		body := strings.Replace(validSeatStatusBody, `"claude-code"`, `"`+runtime+`"`, 1)
		rec := postSeatStatus(seatStatusTestMux(t, &fakeSeatStatus{}), body)
		if rec.Code != http.StatusOK {
			t.Errorf("runtime %q: status = %d, want 200 (%s)", runtime, rec.Code, rec.Body.String())
		}
	}
}

func TestSeatStatusPostRejectsInvalidReports(t *testing.T) {
	cases := map[string]string{
		"unknown field":  strings.Replace(validSeatStatusBody, `"agents"`, `"extra":1,"agents"`, 1),
		"bad machine":    strings.Replace(validSeatStatusBody, `pc-home`, `pc.home`, 1),
		"bad room":       strings.Replace(validSeatStatusBody, `"room":"eng"`, `"room":"e/ng"`, 1),
		"bad state":      strings.Replace(validSeatStatusBody, `"running"`, `"flying"`, 1),
		"bad runtime":    strings.Replace(validSeatStatusBody, `"claude-code"`, `"vim"`, 1),
		"bad status":     strings.Replace(validSeatStatusBody, `"idle"`, `"asleep"`, 1),
		"bad time":       strings.Replace(validSeatStatusBody, `2026-10-03T11:59:30Z`, `yesterday`, 1),
		"long detail":    strings.Replace(validSeatStatusBody, `"working"`, `"`+strings.Repeat("x", 201)+`"`, 1),
		"duplicate seat": strings.Replace(validSeatStatusBody, `"redacted":false}]`, `"redacted":false},{"room":"eng","seat":"coder","state":"idle","runtime":"codex"}]`, 1),
		"not json":       `{`,
	}
	for name, body := range cases {
		fake := &fakeSeatStatus{}
		rec := postSeatStatus(seatStatusTestMux(t, fake), body)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("%s: status = %d, want 400 (%s)", name, rec.Code, rec.Body.String())
		}
		if len(fake.byUser) != 0 {
			t.Errorf("%s: invalid report was stored", name)
		}
	}
}

func TestSeatStatusPostRejectsSecretsWithoutEchoing(t *testing.T) {
	const secret = "sk-abcdefghijklmnopqrstuvwxyz0123456789ABCD"
	cases := map[string]struct{ body, field string }{
		"detail":      {strings.Replace(validSeatStatusBody, `"working"`, `"key `+secret+`"`, 1), "seats[0].detail"},
		"pinned_hash": {strings.Replace(validSeatStatusBody, `abc123`, secret, 1), "seats[0].pinned_hash"},
		"pane":        {strings.Replace(validSeatStatusBody, `w5:p3`, `token=abc123def456`, 1), "agents[0].pane_id"},
		"machine":     {strings.Replace(validSeatStatusBody, `pc-home`, secret, 1), "machine_id"},
	}
	for name, tc := range cases {
		fake := &fakeSeatStatus{}
		rec := postSeatStatus(seatStatusTestMux(t, fake), tc.body)
		if rec.Code != http.StatusUnprocessableEntity {
			t.Errorf("%s: status = %d, want 422 (%s)", name, rec.Code, rec.Body.String())
			continue
		}
		want := `{"success":false,"error":"secret detected in field ` + tc.field + `"}`
		if rec.Body.String() != want {
			t.Errorf("%s: body = %s, want %s", name, rec.Body.String(), want)
		}
		if strings.Contains(rec.Body.String(), "sk-") || len(fake.byUser) != 0 {
			t.Errorf("%s: secret echoed or stored", name)
		}
	}
}

func TestSeatStatusRepositoryErrorIs500(t *testing.T) {
	mux := seatStatusTestMux(t, &fakeSeatStatus{err: errors.New("boom")})
	if rec := postSeatStatus(mux, validSeatStatusBody); rec.Code != http.StatusInternalServerError {
		t.Fatalf("POST = %d", rec.Code)
	}
	rec := getMachines(mux)
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("GET = %d", rec.Code)
	}
}

// The report response tells the machine what the cloud expects, per seat, in the same shape
// GET /machines renders - the only way a bridge, which holds no user token, can record the hash
// it was last in sync with. The discrimination is exercised by making the hashes differ.
func TestSeatStatusPostReportsVerdictsPerSeat(t *testing.T) {
	fake := &fakeSeatStatus{expected: map[string]string{
		"eng/coder": "cloud456",
		"eng/same":  "cloud456",
	}}
	mux := seatStatusTestMux(t, fake)
	body := `{"machine_id":"pc-home","reported_at":"2026-10-03T11:59:30Z","seats":[` +
		`{"room":"eng","seat":"coder","state":"running","runtime":"claude-code","pinned_hash":"run123","detail":"","redacted":false},` +
		`{"room":"eng","seat":"same","state":"idle","runtime":"claude-code","pinned_hash":"cloud456","detail":"","redacted":false},` +
		`{"room":"eng","seat":"none","state":"idle","runtime":"claude-code","pinned_hash":"run123","detail":"","redacted":false}` +
		`],"agents":[]}`

	rec := postSeatStatus(mux, body)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST = %d %s", rec.Code, rec.Body.String())
	}
	var got struct {
		Verdicts []struct {
			Room, Seat   string
			ExpectedHash string `json:"expected_hash"`
			Sync         string `json:"sync"`
		} `json:"verdicts"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v\n%s", err, rec.Body.String())
	}
	want := map[string]string{"coder": "drift", "same": "in_sync", "none": "unknown"}
	if len(got.Verdicts) != 3 {
		t.Fatalf("verdicts = %s", rec.Body.String())
	}
	for _, v := range got.Verdicts {
		if v.Sync != want[v.Seat] {
			t.Errorf("seat %s sync = %q, want %q", v.Seat, v.Sync, want[v.Seat])
		}
		if v.Seat == "coder" && v.ExpectedHash != "cloud456" {
			t.Errorf("coder expected_hash = %q: the response must carry the cloud value, not the reported hash", v.ExpectedHash)
		}
	}
}

func TestSeatStatusGetReportsExpectedHashAndSync(t *testing.T) {
	const user = "11111111-1111-4111-8111-111111111111"
	seat := func(name, running, expected string) repositories.SeatStatus {
		return repositories.SeatStatus{Room: "eng", Seat: name, State: "running", Runtime: "claude-code",
			RunningHash: running, ExpectedHash: expected, ReportedAt: seatStatusTestNow}
	}
	fake := &fakeSeatStatus{byUser: map[string]map[string]repositories.Machine{user: {
		"pc": {MachineID: "pc", LastSeen: seatStatusTestNow, Seats: []repositories.SeatStatus{
			seat("same", "h1", "h1"), seat("old", "h1", "h2"), seat("none", "h1", ""), seat("silent", "", "h2"),
		}},
	}}}
	rec := getMachines(seatStatusTestMux(t, fake))
	if rec.Code != http.StatusOK {
		t.Fatalf("GET = %d", rec.Code)
	}
	var got struct {
		Machines []struct {
			Seats []struct {
				Seat         string `json:"seat"`
				PinnedHash   string `json:"pinned_hash"`
				ExpectedHash string `json:"expected_hash"`
				Sync         string `json:"sync"`
			} `json:"seats"`
		} `json:"machines"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatal(err)
	}
	wantSync := map[string]string{"same": "in_sync", "old": "drift", "none": "unknown", "silent": "unknown"}
	if len(got.Machines) != 1 || len(got.Machines[0].Seats) != 4 {
		t.Fatalf("GET = %s", rec.Body.String())
	}
	for _, s := range got.Machines[0].Seats {
		if s.Sync != wantSync[s.Seat] {
			t.Errorf("seat %s sync = %q, want %q", s.Seat, s.Sync, wantSync[s.Seat])
		}
	}
	// key order: runtime, pinned_hash (what the seat has PINNED), expected_hash, sync, detail
	if !strings.Contains(rec.Body.String(), `"runtime":"claude-code","pinned_hash":"h1","expected_hash":"h1","sync":"in_sync","detail":`) {
		t.Fatalf("seat keys out of order: %s", rec.Body.String())
	}
}
