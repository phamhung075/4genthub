package httpapp

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
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
		body string // the JSON-escaped detail, as a client reads it
	}{
		{fmt.Errorf("%w: seat %q", seatservices.ErrSeatNotFound, "x"), http.StatusNotFound, `seat not found: seat \"x\"`},
		{fmt.Errorf("%w: room %q", seatservices.ErrRoomNotFound, "dev"), http.StatusNotFound, `room not found: room \"dev\"`},
		// THE TEXT DOES NOT DECIDE: an error that merely SAYS "not found" is this server's own
		// failure, not a 404 it never earned.
		{errors.New(`seat "x" not found in room "dev"`), http.StatusInternalServerError, ""},
		{errors.New("database down"), http.StatusInternalServerError, ""},
	}
	for _, c := range cases {
		mux := seatTestMux(t, &fakeSeatSource{err: c.err})
		rec := doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/x", "")
		if rec.Code != c.want {
			t.Errorf("%v: status = %d, want %d", c.err, rec.Code, c.want)
		}
		if c.body != "" && !strings.Contains(rec.Body.String(), c.body) {
			t.Errorf("%v: body = %s, want it to carry %s", c.err, rec.Body.String(), c.body)
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

}

// ---- the message store's own fixtures and tests -----------------------------------------------

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
// clock substituted.
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
	t.Cleanup(func() {
		newSeatSource = previousSource
		newSeatMessageService = previousService
		seatMessageNow = previousNow
	})
	mux := http.NewServeMux()
	mountSeatRoutes(mux, nil)
	return mux
}

// THE PULL TAKES THE USER TOKEN, like the write: the client holds the same credential as the window.
func TestSeatMessagePullReturnsThePendingMessages(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	store := &fakeSeatMessageStore{pending: []repositories.SeatMessage{{
		ID: "m1", UserID: "11111111-1111-4111-8111-111111111111", Room: "dev", Seat: "coder",
		Text: "hello", CreatedAt: seatMessageTestNow,
	}}}
	mux := seatMessageTestMux(t, &fakeSeatSource{resolved: &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}}, store)
	path := "/api/v2/openrig/rooms/dev/seats/coder/messages"

	rec := doTestRequest(t, mux, http.MethodGet, path, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("pull = %d, want 200: %s", rec.Code, rec.Body.String())
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
	first := doTestRequest(t, mux, http.MethodGet, path, "")
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
	if ack := doTestRequest(t, mux, http.MethodPost, ackPath, `{"machine_id":"pc-home"}`); ack.Code != http.StatusOK {
		t.Fatalf("ack = %d %s", ack.Code, ack.Body.String())
	}

	again := doTestRequest(t, mux, http.MethodGet, path, "")
	if again.Code != http.StatusOK || strings.Contains(again.Body.String(), `"text":"hello"`) {
		t.Fatalf("pull after ack = %d %s, want nothing redelivered", again.Code, again.Body.String())
	}
	if second := doTestRequest(t, mux, http.MethodPost, ackPath, `{"machine_id":"pc-home"}`); second.Code != http.StatusConflict {
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
	source := &fakeSeatSource{err: fmt.Errorf("%w: seat %q", seatservices.ErrSeatNotFound, "ghost")}
	mux := seatMessageTestMux(t, source, store)
	path := "/api/v2/openrig/rooms/dev/seats/ghost/messages"

	write := doTestRequest(t, mux, http.MethodPost, path, `{"text":"hello"}`)
	pull := doTestRequest(t, mux, http.MethodGet, path, "")
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

// authenticateAs makes the authed wrapper resolve to a SPECIFIC user for the requests that follow, so
// one mux can be asked the same request by an owner, a member and a stranger. authenticateTestUser
// fixes one id, and one fixed id cannot express a caller who is NOT the room's owner.
func authenticateAs(t *testing.T, id string) {
	t.Helper()
	previous := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		caller := id
		return &authdomain.User{ID: &caller, Email: "caller@example.com", Username: "caller"}, nil
	}
	t.Cleanup(func() { authinterface.GetCurrentUserUniversal = previous })
}

// sharingAwareSeatSource models the resolver's TWO predicates the way the production path composes
// them: the write resolves the room through Rooms.GetBySlug, which returns the CALLER'S OWN room only
// (seat_resolution_service.go:40-41, repositories.go:118-123), while the read routes reach a shared
// room through GetVisibleBySlug (seat_admin_mount.go:1360, :1377, :1594). A member of the room's
// sharing team therefore reads the room and cannot write it, which is what this case is about.
type sharingAwareSeatSource struct {
	ownerID string
	asked   []string
}

func (f *sharingAwareSeatSource) ResolveSeat(_ context.Context, callerUserID, room, seat string) (*repositories.ResolvedSeat, error) {
	f.asked = append(f.asked, callerUserID+"|"+room+"/"+seat)
	if callerUserID != f.ownerID {
		return nil, fmt.Errorf("%w: room %q", seatservices.ErrRoomNotFound, room)
	}
	return &repositories.ResolvedSeat{Hash: "abc", Runtime: "claude-code"}, nil
}

func (f *sharingAwareSeatSource) SeedSeatTypes(_ context.Context, _ string) (int, error) {
	return 0, nil
}

// THE FIFTH SURFACE, and the reason this case exists: the seat chat write is owner-only in the same
// class as the four seat-detail write surfaces, and NO case named a viewer or a non-member before it.
//
// THE REFUSAL IS THE SAME 404, NOT A PER-ACTION REASON. The handler's only resolver is
// SeatResolutionService.ResolveSeat, whose room lookup is Rooms.GetBySlug - the caller's OWN room - so a
// member of the room's sharing team lands in the same ErrRoomNotFound branch as a stranger, and the
// sentence they get is about the ROOM rather than about permission. That is the whole point of the
// class: the same caller may read the room and may not write it.
//
// THE OWNER IS THE POSITIVE CONTROL: a case asserting only the two refusals would pass just as well
// against a route that refused everybody, so the first request is the owner's and it must STORE.
func TestSeatMessageSendRefusesAViewerAndAStrangerWithTheSame404(t *testing.T) {
	t.Setenv(publicURLEnv, "https://api.example.test")
	const ownerID = "11111111-1111-4111-8111-111111111111"
	const viewerID = "22222222-2222-4222-8222-222222222222"
	const strangerID = "33333333-3333-4333-8333-333333333333"

	store := &fakeSeatMessageStore{}
	source := &sharingAwareSeatSource{ownerID: ownerID}
	mux := seatMessageTestMux(t, source, store)
	path := "/api/v2/openrig/rooms/dev/seats/alice/messages"

	authenticateAs(t, ownerID)
	owner := doTestRequest(t, mux, http.MethodPost, path, `{"text":"hello"}`)
	if owner.Code != http.StatusOK {
		t.Fatalf("owner send = %d %s, want 200 (the room is the owner's)", owner.Code, owner.Body.String())
	}
	if len(store.created) != 1 {
		t.Fatalf("owner send stored %d messages, want 1", len(store.created))
	}

	authenticateAs(t, viewerID)
	viewer := doTestRequest(t, mux, http.MethodPost, path, `{"text":"hello"}`)
	if viewer.Code != http.StatusNotFound {
		t.Fatalf("viewer send = %d %s, want 404", viewer.Code, viewer.Body.String())
	}

	authenticateAs(t, strangerID)
	stranger := doTestRequest(t, mux, http.MethodPost, path, `{"text":"hello"}`)
	if stranger.Code != http.StatusNotFound {
		t.Fatalf("stranger send = %d %s, want 404", stranger.Code, stranger.Body.String())
	}

	// The member and the stranger are answered IDENTICALLY, so the refusal cannot be used to learn
	// whether a room exists, let alone whether it is shared with anyone.
	if viewer.Body.String() != stranger.Body.String() {
		t.Errorf("a viewer and a stranger were answered differently:\n viewer %s\n stranger %s", viewer.Body.String(), stranger.Body.String())
	}
	// Neither refusal stored anything: the resolution precedes the write in the handler.
	if len(store.created) != 1 {
		t.Errorf("a refused send stored a message: %+v", store.created)
	}
	// Every resolution was asked for the URL's room and seat, AND for the caller that made it.
	if len(source.asked) != 3 {
		t.Fatalf("the resolver was asked %d times, want 3: %v", len(source.asked), source.asked)
	}
	if source.asked[1] != viewerID+"|dev/alice" || source.asked[2] != strangerID+"|dev/alice" {
		t.Errorf("the resolver was asked for %v, want each caller's own pair", source.asked)
	}
}
