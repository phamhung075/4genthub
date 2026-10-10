package httpapp

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	seatservices "agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// authenticateTestUser makes currentUser resolve to a valid UUID user so the authed
// handlers run instead of returning 403.
func authenticateTestUser(t *testing.T) {
	t.Helper()
	previous := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		id := "11111111-1111-4111-8111-111111111111"
		return &authdomain.User{ID: &id, Email: "dev@example.com", Username: "dev"}, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = previous })
}

func doTestRequest(t *testing.T, mux *http.ServeMux, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Authorization", "Bearer test-token")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

type fakeSeatSource struct {
	resolved *repositories.ResolvedSeat
	err      error
	seeded   int
	// asked records the room/seat pair of every resolution, so a test can prove WHICH pair the
	// handler resolved rather than only that it resolved something.
	asked []string
}

func (f *fakeSeatSource) ResolveSeat(_ context.Context, _, room, seat string) (*repositories.ResolvedSeat, error) {
	f.asked = append(f.asked, room+"/"+seat)
	return f.resolved, f.err
}

func (f *fakeSeatSource) SeedSeatTypes(_ context.Context, _ string) (int, error) {
	return f.seeded, f.err
}

func seatTestMux(t *testing.T, source seatSource) *http.ServeMux {
	t.Helper()
	previous := newSeatSource
	newSeatSource = func(*database.SessionManager, string) (seatSource, error) { return source, nil }
	t.Cleanup(func() { newSeatSource = previous })
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux
}

func TestResolveSeatReturnsSnapshot(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{
		Hash: "abc", Runtime: "claude-code",
		Files:  []repositories.ResolvedFile{{Path: "agent.yaml", Content: "name: x"}},
		Policy: map[string]any{"Seat": "coder"},
	}})
	rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/coder", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"hash":"abc"`, `"room":"dev"`, `"seat":"coder"`, `"path":"agent.yaml"`, `"Seat":"coder"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("body missing %s: %s", want, rec.Body.String())
		}
	}
}

func TestResolveSeatStatusMapping(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	cases := []struct {
		err  error
		want int
	}{
		{errors.New(`seat "x" not found in room "dev"`), http.StatusNotFound},
		{errors.New("database down"), http.StatusInternalServerError},
	}
	for _, c := range cases {
		mux := seatTestMux(t, &fakeSeatSource{err: c.err})
		if rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", ""); rec.Code != c.want {
			t.Errorf("%v: status = %d, want %d", c.err, rec.Code, c.want)
		}
	}
}

// capturedSeatMux is seatTestMux with the mcpURL newSeatSource is constructed with captured,
// so a test can assert which origin a rendered seat rewrites its MCP server URL to.
func capturedSeatMux(t *testing.T, source seatSource) (*http.ServeMux, *string) {
	t.Helper()
	var mcpURL string
	previous := newSeatSource
	newSeatSource = func(_ *database.SessionManager, u string) (seatSource, error) {
		mcpURL = u
		return source, nil
	}
	t.Cleanup(func() { newSeatSource = previous })
	authenticateTestUser(t)
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux, &mcpURL
}

// authedSeatRequest is a seat GET with the given public origin signals and a bearer token.
func authedSeatRequest(host string, tlsTerminated bool, headers map[string]string) *http.Request {
	req := httptest.NewRequest(http.MethodGet, "/api/v2/openrig/seats/dev/coder", nil)
	if host != "" {
		req.Host = host
	}
	if tlsTerminated {
		req.TLS = &tls.ConnectionState{}
	}
	for k, v := range headers {
		req.Header.Set(k, v)
	}
	req.Header.Set("Authorization", "Bearer test-token")
	return req
}

func TestResolveSeatDerivesPublicURLFromRequest(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux, mcpURL := capturedSeatMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, authedSeatRequest("seats.example.test", true, nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("without %s: status = %d, want 200: %s", publicURLEnv, rec.Code, rec.Body.String())
	}
	if *mcpURL != "https://seats.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the request origin", *mcpURL)
	}
}

func TestResolveSeatPinnedURLWinsOverRequestHost(t *testing.T) {
	t.Setenv(publicURLEnv, "https://pinned.example.test/")
	mux, mcpURL := capturedSeatMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, authedSeatRequest("seats.example.test", true, nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if *mcpURL != "https://pinned.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the pinned override", *mcpURL)
	}
}

func TestResolveSeatTrustsForwardedOrigin(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux, mcpURL := capturedSeatMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})

	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, authedSeatRequest("internal:8000", false, map[string]string{
		"X-Forwarded-Proto": "https",
		"X-Forwarded-Host":  "public.example.test, internal",
	}))
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if *mcpURL != "https://public.example.test/mcp" {
		t.Errorf("rendered MCP URL = %q, want the forwarded origin", *mcpURL)
	}
}

func TestSeatRoutesDerivePublicURLAndRequireAuth(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}})
	if rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", ""); rec.Code != http.StatusOK {
		t.Errorf("without %s: status = %d, want 200", publicURLEnv, rec.Code)
	}
	bare := httptest.NewRecorder()
	mux.ServeHTTP(bare, httptest.NewRequest(http.MethodGet, "/api/v2/openrig/seats/dev/x", nil))
	if bare.Code == http.StatusNotFound || bare.Code == http.StatusOK {
		t.Errorf("unauthenticated request: status = %d, want 401/403", bare.Code)
	}
}

func TestSeedSeatTypesReportsCount(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := seatTestMux(t, &fakeSeatSource{seeded: 9})
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seat_types":9`) {
		t.Errorf("seed: %d %s", rec.Code, rec.Body.String())
	}
}

func TestSeedSeatTypesWorksWithoutPublicURL(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{seeded: 9})
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"seat_types":9`) {
		t.Errorf("seed without %s: status = %d %s", publicURLEnv, rec.Code, rec.Body.String())
	}
}

func TestSeedSeatTypesErrorMapping(t *testing.T) {
	t.Setenv(publicURLEnv, "")
	mux := seatTestMux(t, &fakeSeatSource{err: errors.New("database down")})
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/seed", "")
	if rec.Code != http.StatusInternalServerError {
		t.Errorf("seed error: status = %d, want 500", rec.Code)
	}
}

// THE PROPERTY THIS PROTECTS IS THE VERB ON THE MESSAGE PATH, in the shape the tree now has: the
// same path carries the two DIRECTIONS of one store, so a POST reaches the WRITER and stores the
// text while a GET reaches the PULLER — and the puller is machine-authenticated, which is the refusal
// a user token gets. The resolution answers on its OWN room-scoped path, where it already lived and
// where nothing here touches it. This is a ROUTING test rather than a validation one: each pattern
// must be reached by the path and the method it names.
func TestSeatMessageRouteIsVerbScoped(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	store := &fakeSeatMessageStore{}
	mux := seatMessageTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{
		Hash: "abc", Runtime: "claude-code", Policy: map[string]any{"Seat": "coder"},
	}}, store)

	// POST on the room-scoped path reaches the writer, and the answer is a success carrying the stored
	// id: the message IS held, so a refusal here would be a lie about the store.
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats/coder/messages", `{"text":"hello"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("POST /rooms/dev/seats/coder/messages = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"success":true`, `"id":"m1"`, `"room":"dev"`, `"seat":"coder"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("POST body missing %s: %s", want, rec.Body.String())
		}
	}
	if len(store.created) != 1 || store.created[0].Text != "hello" {
		t.Fatalf("stored = %+v, want exactly the text the body carried", store.created)
	}

	// A GET on that same path is the PULL, and the proof that this request reached it rather than a
	// writer or a 405 is the refusal only the pull's auth can give: the header doTestRequest sends is
	// a user token, which is not a machine token.
	if getRec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats/coder/messages", ""); getRec.Code != http.StatusUnauthorized {
		t.Fatalf("GET /rooms/dev/seats/coder/messages with a user token = %d, want the machine-auth 401: %s", getRec.Code, getRec.Body.String())
	}

	// The resolution is not on this path and never was: it answers on its own room-scoped path,
	// /seats/{room}/{seat}. The key-only two-segment path that once collided with the message
	// route now resolves alone, with "messages" as the seat key - the shape a client resolving a
	// seat still calls.
	getRec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/coder/messages", "")
	if getRec.Code != http.StatusOK {
		t.Fatalf("GET /seats/coder/messages = %d, want the resolution 200: %s", getRec.Code, getRec.Body.String())
	}
	for _, want := range []string{`"room":"coder"`, `"seat":"messages"`} {
		if !strings.Contains(getRec.Body.String(), want) {
			t.Errorf("GET /seats/coder/messages body missing %s: %s", want, getRec.Body.String())
		}
	}

	// AND THE ROUTE REALLY MOVED: the retired key-only path no longer takes the POST - only the
	// GET-only resolution pattern matches it now, so the window's own call would be answered the
	// 405 this row exists to stop being the answer.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/coder/messages", `{"text":"hello"}`); rec.Code != http.StatusMethodNotAllowed {
		t.Fatalf("POST /seats/coder/messages = %d, want 405: the retired key-only shape still takes the message POST", rec.Code)
	}
}

// The refusals that come from ROUTING, so that a later change cannot make this route's answer
// depend on what the caller sent.
func TestSeatMessageRouteRefusalsComeFromRouting(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	fake := &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}}
	mux := seatTestMux(t, fake)

	// A malformed body is refused for being malformed, which is only reachable if routing
	// already chose this route.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats/coder/messages", `{"text":`); rec.Code != http.StatusBadRequest {
		t.Errorf("malformed body: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	// The body is {text} and nothing else: an unknown field is refused, the room included,
	// because the room is the path's to carry.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats/coder/messages", `{"room":"dev"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("unknown field: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	// AND THE BODY IS DECODED BEFORE THE SEAT IS RESOLVED: a refused body must not have reached
	// the resolver, so a malformed request can never be answered for the seat's absence.
	if len(fake.asked) != 0 {
		t.Errorf("the resolver was asked %v for a request whose body was refused", fake.asked)
	}
	// The resolution route is GET-only, so its own pattern answers the wrong method.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/dev/coder", `{"text":"x"}`); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("POST on the resolution path: status = %d, want 405", rec.Code)
	}
	// A three-segment path matches no pattern at all.
	if rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seats/a/b/c", `{"text":"x"}`); rec.Code != http.StatusNotFound {
		t.Errorf("unknown subpath: status = %d, want 404", rec.Code)
	}
}

// An unauthenticated window is refused by the auth layer before the handler, with a sentence the
// UI can render.
func TestSeatMessageRouteRequiresAuth(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)

	// The header is what decides: no usable bearer is the 403 the routes layer answers itself,
	// and it never reaches the handler. A present-but-unusable bearer instead goes through the
	// auth layer, whose answer is the auth layer's to give.
	for _, tc := range []struct {
		name   string
		header string
	}{
		{"no authorization header", ""},
		{"not a bearer scheme", "Basic abc"},
		{"bearer with no token", "Bearer "},
	} {
		req := httptest.NewRequest(http.MethodPost, "/api/v2/openrig/rooms/dev/seats/coder/messages", strings.NewReader(`{"text":"hello"}`))
		if tc.header != "" {
			req.Header.Set("Authorization", tc.header)
		}
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code != http.StatusForbidden || !strings.Contains(rec.Body.String(), "Not authenticated") {
			t.Errorf("%s: POST = %d %s, want 403 with a detail", tc.name, rec.Code, rec.Body.String())
		}
	}
}

// THE ROW'S POINT: the seat is resolved in the room the URL names, so a seat that is not in that
// room is answered 404 - which the key-only path could not do at all - and the pair the resolver is
// asked for is the pair the URL carries rather than a guessed room.
//
// THE REFUSALS ONLY. A seat that DOES resolve now reaches the store, and the store's own answers are
// asserted where they belong: a success and its stored row in TestSeatMessageRouteIsVerbScoped, a
// refused credential in TestSeatMessageSendRefusesACredentialWithTheChannelsOwnBody, and the pull's
// two directions in TestSeatMessagePullNeedsAMachineToken and TestSeatMessageDeliveredOnceAndNotAgain.
// Keeping a 200 case here would mean asserting, in a table whose every other row carries a "detail",
// a body that has none.
func TestSeatMessageRouteResolvesTheSeatInTheRoomTheURLNames(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	cases := []struct {
		name       string
		fake       *fakeSeatSource
		want       int
		wantInBody string
	}{
		{
			"a seat that is not in the room the URL names",
			&fakeSeatSource{err: errors.New(`seat "ghost" not found in room "dev"`)},
			http.StatusNotFound,
			"not found",
		},
		{
			"the resolver failing for another reason",
			&fakeSeatSource{err: errors.New("database down")},
			http.StatusInternalServerError,
			"",
		},
	}
	for _, c := range cases {
		mux := seatTestMux(t, c.fake)
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats/ghost/messages", `{"text":"hello"}`)
		if rec.Code != c.want {
			t.Errorf("%s: status = %d, want %d: %s", c.name, rec.Code, c.want, rec.Body.String())
		}
		// Every answer above is a sentence the window renders, so a bare status is not enough.
		if !strings.Contains(rec.Body.String(), `"detail"`) {
			t.Errorf("%s: the answer carries no detail for the window to render: %s", c.name, rec.Body.String())
		}
		if c.wantInBody != "" && !strings.Contains(rec.Body.String(), c.wantInBody) {
			t.Errorf("%s: body missing %q: %s", c.name, c.wantInBody, rec.Body.String())
		}
		// The room and the seat are the URL's, never a guess.
		if len(c.fake.asked) != 1 || c.fake.asked[0] != "dev/ghost" {
			t.Errorf("%s: the resolver was asked for %v, want [dev/ghost]", c.name, c.fake.asked)
		}
	}
}

// ---- the message store's own fixtures and tests -----------------------------------------------

// seatMessageTestToken is the machine token of machine pc-home of the test user. The pull and the ack
// take a MACHINE token, because the component that can reach a seat's terminal is the client on the
// machine that holds it; the writer takes the window's user token.
const seatMessageTestToken = "mt_seat-message-test-token"

var seatMessageTestNow = time.Date(2026, 10, 10, 9, 0, 0, 0, time.UTC)

// fakeSeatMessageStore is the message store in memory, holding the contract's two behaviours: a stored
// message is PENDING, and an acked one never comes back. The SQL behind them — the keyset page, the
// `delivered_at IS NULL` update — is the real repository's and is exercised where a database is
// available; what these route tests prove is that the routes reach the store, hand it the cursor and
// the page, and map its answers to the statuses the client acts on.
type fakeSeatMessageStore struct {
	pending []repositories.SeatMessage
	created []repositories.SeatMessage
}

func (f *fakeSeatMessageStore) Create(_ context.Context, message repositories.SeatMessage) (*repositories.SeatMessage, error) {
	message.ID = "m" + strconv.Itoa(len(f.created)+1)
	f.created = append(f.created, message)
	f.pending = append(f.pending, message)
	stored := message
	return &stored, nil
}

func (f *fakeSeatMessageStore) ListPending(_ context.Context, _, room, seat string, afterCreatedAt time.Time, _ string, limit int) ([]repositories.SeatMessage, error) {
	out := []repositories.SeatMessage{}
	for _, m := range f.pending {
		if m.Room != room || m.Seat != seat {
			continue
		}
		if !afterCreatedAt.IsZero() && !m.CreatedAt.After(afterCreatedAt) {
			continue
		}
		out = append(out, m)
	}
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

func (f *fakeSeatMessageStore) Ack(_ context.Context, _, room, seat, id, _ string, _ time.Time) (bool, error) {
	for i, m := range f.pending {
		if m.ID == id && m.Room == room && m.Seat == seat {
			f.pending = append(f.pending[:i], f.pending[i+1:]...)
			return true, nil
		}
	}
	return false, nil
}

// seatMessageTestMux mounts the seat routes with the seat source, the message service and the server
// clock substituted, and a machine token registered for the test user's machine pc-home.
func seatMessageTestMux(t *testing.T, source seatSource, store *fakeSeatMessageStore) *http.ServeMux {
	t.Helper()
	authenticateTestUser(t)
	previousSource := newSeatSource
	newSeatSource = func(*database.SessionManager, string) (seatSource, error) { return source, nil }
	previousService := newSeatMessageService
	newSeatMessageService = func(*database.SessionManager) (*seatservices.SeatMessageService, error) {
		return seatservices.NewSeatMessageService(store), nil
	}
	previousNow := seatMessageNow
	seatMessageNow = func() time.Time { return seatMessageTestNow }
	previousTokens := newMachineTokenRepo
	tokens := &fakeMachineTokens{tokens: []*repositories.MachineToken{{
		ID: "tok", UserID: "11111111-1111-4111-8111-111111111111", MachineID: "pc-home",
		TokenHash: seatservices.HashMachineToken(seatMessageTestToken),
	}}}
	newMachineTokenRepo = func(*database.SessionManager) (repositories.MachineTokenRepository, error) { return tokens, nil }
	t.Cleanup(func() {
		newSeatSource = previousSource
		newSeatMessageService = previousService
		seatMessageNow = previousNow
		newMachineTokenRepo = previousTokens
	})
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux
}

// machineSeatMessage is a message request bearing the machine token the pull and the ack need.
func machineSeatMessage(mux *http.ServeMux, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	req.Header.Set("Authorization", "Bearer "+seatMessageTestToken)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	return rec
}

// THE TWO CREDENTIALS ARE NOT INTERCHANGEABLE: the window's user token writes, and only the machine
// token pulls, because the puller is the component that can put text into a terminal.
func TestSeatMessagePullNeedsAMachineToken(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	store := &fakeSeatMessageStore{pending: []repositories.SeatMessage{{
		ID: "m1", UserID: "11111111-1111-4111-8111-111111111111", Room: "dev", Seat: "coder",
		Text: "hello", CreatedAt: seatMessageTestNow,
	}}}
	mux := seatMessageTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}}, store)
	path := "/api/v2/openrig/rooms/dev/seats/coder/messages"

	if rec := doTestRequest(t, mux, http.MethodGet, path, ""); rec.Code != http.StatusUnauthorized {
		t.Fatalf("user token = %d, want 401: %s", rec.Code, rec.Body.String())
	}

	rec := machineSeatMessage(mux, http.MethodGet, path, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("machine token = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	for _, want := range []string{`"success":true`, `"id":"m1"`, `"text":"hello"`, `"cursor":"2026-10-10T09:00:00Z|m1"`} {
		if !strings.Contains(rec.Body.String(), want) {
			t.Errorf("pull body missing %s: %s", want, rec.Body.String())
		}
	}
}

// THE DELIVERY CONTRACT AT THE ROUTE, and the ruling it implements: at-least-once with the ack AFTER
// the delivery. A message is handed out until the client acks it, so an interruption redelivers
// rather than loses; once acked it never comes back; and a second ack of the same id is refused
// rather than counted as a second delivery.
func TestSeatMessageDeliveredOnceAndNotAgain(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	store := &fakeSeatMessageStore{}
	mux := seatMessageTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}}, store)
	path := "/api/v2/openrig/rooms/dev/seats/coder/messages"

	if rec := doTestRequest(t, mux, http.MethodPost, path, `{"text":"hello"}`); rec.Code != http.StatusOK {
		t.Fatalf("send = %d: %s", rec.Code, rec.Body.String())
	}

	// Unacked, it is handed out: this pull is the delivery the client has not confirmed yet.
	first := machineSeatMessage(mux, http.MethodGet, path, "")
	var body struct {
		Messages []struct {
			ID string `json:"id"`
		} `json:"messages"`
		Cursor string `json:"cursor"`
	}
	if err := json.Unmarshal(first.Body.Bytes(), &body); err != nil || len(body.Messages) != 1 {
		t.Fatalf("first pull = %d %s (%v), want one message", first.Code, first.Body.String(), err)
	}
	if body.Messages[0].ID != "m1" || body.Cursor == "" {
		t.Fatalf("first pull = %s, want the stored id and the cursor that continues after it", first.Body.String())
	}

	ackPath := path + "/" + body.Messages[0].ID + "/ack"
	if ack := machineSeatMessage(mux, http.MethodPost, ackPath, ""); ack.Code != http.StatusOK {
		t.Fatalf("ack = %d %s", ack.Code, ack.Body.String())
	}

	again := machineSeatMessage(mux, http.MethodGet, path, "")
	if again.Code != http.StatusOK || strings.Contains(again.Body.String(), `"text":"hello"`) {
		t.Fatalf("pull after ack = %d %s, want nothing redelivered", again.Code, again.Body.String())
	}
	if second := machineSeatMessage(mux, http.MethodPost, ackPath, ""); second.Code != http.StatusConflict {
		t.Fatalf("second ack = %d %s, want 409: the state, not a typo", second.Code, second.Body.String())
	}
}

// THE CREDENTIAL SCAN AT THE ROUTE, in the friction channel's own body: a 422 whose error names the
// field, an answer that never repeats the credential, and nothing stored.
func TestSeatMessageSendRefusesACredentialWithTheChannelsOwnBody(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	const secret = "ghp_0123456789012345678901234567890123"
	store := &fakeSeatMessageStore{}
	mux := seatMessageTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}}, store)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats/coder/messages",
		`{"text":"the call failed with `+secret+` in the header"}`)
	if rec.Code != http.StatusUnprocessableEntity {
		t.Fatalf("status = %d, want 422: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "secret detected in field text") {
		t.Errorf("body = %s, want the field named", rec.Body.String())
	}
	if strings.Contains(rec.Body.String(), secret) {
		t.Errorf("the answer repeats the credential: %s", rec.Body.String())
	}
	if len(store.created) != 0 {
		t.Errorf("a refused message was stored: %+v", store.created)
	}
}

// THE SAME 404 ON BOTH DIRECTIONS, byte for byte: a seat that is not in the room the URL names is
// refused identically whether the writer or the puller asks, so neither can be used to learn which
// seat keys exist.
func TestSeatMessageBothDirectionsRefuseAMissingSeatIdentically(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	store := &fakeSeatMessageStore{}
	source := &fakeSeatSource{err: errors.New(`seat "ghost" not found in room "dev"`)}
	mux := seatMessageTestMux(t, source, store)
	path := "/api/v2/openrig/rooms/dev/seats/ghost/messages"

	write := doTestRequest(t, mux, http.MethodPost, path, `{"text":"hello"}`)
	pull := machineSeatMessage(mux, http.MethodGet, path, "")
	if write.Code != http.StatusNotFound || pull.Code != http.StatusNotFound {
		t.Fatalf("write = %d, pull = %d, want 404 for both", write.Code, pull.Code)
	}
	if write.Body.String() != pull.Body.String() {
		t.Errorf("the two directions answered differently:\n write %s\n pull  %s", write.Body.String(), pull.Body.String())
	}
	if len(store.created) != 0 {
		t.Errorf("a message was stored for a seat that did not resolve: %+v", store.created)
	}
	// And the pair the resolver was asked for is the URL's, on both directions.
	if len(source.asked) != 2 || source.asked[0] != "dev/ghost" || source.asked[1] != "dev/ghost" {
		t.Errorf("the resolver was asked for %v, want dev/ghost twice", source.asked)
	}
}
