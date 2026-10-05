package httpapp

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type fakeMachineTokens struct {
	tokens []*repositories.MachineToken
	err    error
}

func (f *fakeMachineTokens) Create(_ context.Context, userID, machineID, tokenHash string) (*repositories.MachineToken, error) {
	if f.err != nil {
		return nil, f.err
	}
	for _, t := range f.tokens {
		if t.UserID == userID && t.MachineID == machineID && t.RevokedAt == nil {
			return nil, repositories.ErrMachineTokenExists
		}
	}
	created := &repositories.MachineToken{ID: "tok-" + machineID, UserID: userID, MachineID: machineID, TokenHash: tokenHash}
	f.tokens = append(f.tokens, created)
	return created, nil
}

func (f *fakeMachineTokens) Revoke(_ context.Context, userID, machineID string) (bool, error) {
	if f.err != nil {
		return false, f.err
	}
	for _, t := range f.tokens {
		if t.UserID == userID && t.MachineID == machineID && t.RevokedAt == nil {
			now := time.Now()
			t.RevokedAt = &now
			return true, nil
		}
	}
	return false, nil
}

func (f *fakeMachineTokens) FindActive(_ context.Context, tokenHash string) (*repositories.MachineToken, error) {
	if f.err != nil {
		return nil, f.err
	}
	for _, t := range f.tokens {
		if t.TokenHash == tokenHash && t.RevokedAt == nil {
			return t, nil
		}
	}
	return nil, nil
}

const (
	tokenTestUserA = "11111111-1111-4111-8111-111111111111"
	tokenTestUserB = "22222222-2222-4222-8222-222222222222"
)

// tokenFixture mounts the bridge routes over in-memory repositories. Like the real user
// validator, its user authenticator rejects machine tokens.
type tokenFixture struct {
	t      *testing.T
	mux    *http.ServeMux
	status *fakeSeatStatus
	tokens *fakeMachineTokens
	user   string
}

func newTokenFixture(t *testing.T) *tokenFixture {
	t.Helper()
	f := &tokenFixture{t: t, status: &fakeSeatStatus{}, tokens: &fakeMachineTokens{}, user: tokenTestUserA}
	previousUsers := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(_ context.Context, token string) (*authdomain.User, error) {
		if strings.HasPrefix(token, "mt_") {
			return nil, errors.New("not a user token")
		}
		id := f.user
		return &authdomain.User{ID: &id, Email: "dev@example.com", Username: "dev"}, nil
	}
	previousStatus, previousTokens, previousNow := newSeatStatusSource, newMachineTokenRepo, seatStatusNow
	newSeatStatusSource = func(*database.SessionManager) (seatStatusSource, error) { return f.status, nil }
	newMachineTokenRepo = func(*database.SessionManager) (repositories.MachineTokenRepository, error) { return f.tokens, nil }
	seatStatusNow = func() time.Time { return seatStatusTestNow }
	t.Cleanup(func() {
		authinterface.GetCurrentUserUniversal = previousUsers
		newSeatStatusSource, newMachineTokenRepo, seatStatusNow = previousStatus, previousTokens, previousNow
	})
	f.mux = http.NewServeMux()
	mountSeatStatusRoutes(f.mux, nil)
	mountMachineTokenRoutes(f.mux, nil)
	mountSeatAdminRoutes(f.mux, nil)
	return f
}

func (f *tokenFixture) do(method, path, bearer, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if bearer != "" {
		req.Header.Set("Authorization", "Bearer "+bearer)
	}
	rec := httptest.NewRecorder()
	f.mux.ServeHTTP(rec, req)
	return rec
}

// register registers machineID as the current user and returns the plaintext token.
func (f *tokenFixture) register(machineID string) string {
	f.t.Helper()
	rec := f.do(http.MethodPost, "/api/v2/openrig/machines", "user-jwt", `{"machine_id":"`+machineID+`"}`)
	if rec.Code != http.StatusOK {
		f.t.Fatalf("register %s: %d %s", machineID, rec.Code, rec.Body.String())
	}
	var body struct {
		Success   bool   `json:"success"`
		MachineID string `json:"machine_id"`
		Token     string `json:"token"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil || !body.Success || body.MachineID != machineID || body.Token == "" {
		f.t.Fatalf("register %s body: %s (%v)", machineID, rec.Body.String(), err)
	}
	return body.Token
}

func reportFor(machineID string) string {
	return strings.Replace(validSeatStatusBody, "pc-home", machineID, 1)
}

func TestMachineTokenRegistrationShowsTokenOnceAndStoresOnlyItsHash(t *testing.T) {
	f := newTokenFixture(t)
	token := f.register("pc-home")
	if !strings.HasPrefix(token, "mt_") || len(token) < 40 {
		t.Fatalf("token %q: want mt_ prefix and at least 40 characters", token)
	}
	sum := sha256.Sum256([]byte(token))
	if len(f.tokens.tokens) != 1 || f.tokens.tokens[0].TokenHash != hex.EncodeToString(sum[:]) || f.tokens.tokens[0].UserID != tokenTestUserA {
		t.Fatalf("stored = %+v, want one row holding the SHA-256 of the token for user A", f.tokens.tokens)
	}
	// The token appears in no later response: not when listing, not on a duplicate registration.
	for _, rec := range []*httptest.ResponseRecorder{
		f.do(http.MethodGet, "/api/v2/openrig/machines", "user-jwt", ""),
		f.do(http.MethodPost, "/api/v2/openrig/machines", "user-jwt", `{"machine_id":"pc-home"}`),
	} {
		if strings.Contains(rec.Body.String(), token) || strings.Contains(rec.Body.String(), f.tokens.tokens[0].TokenHash) {
			t.Errorf("response leaks the token or its hash: %s", rec.Body.String())
		}
	}
}

func TestMachineTokenRejectsASecondActiveTokenForTheSameMachine(t *testing.T) {
	f := newTokenFixture(t)
	f.register("pc-home")
	if rec := f.do(http.MethodPost, "/api/v2/openrig/machines", "user-jwt", `{"machine_id":"pc-home"}`); rec.Code != http.StatusConflict {
		t.Fatalf("second registration: %d, want 409: %s", rec.Code, rec.Body.String())
	}
}

func TestMachineTokenRegistrationValidatesInput(t *testing.T) {
	f := newTokenFixture(t)
	for name, body := range map[string]string{
		"bad id":        `{"machine_id":"pc.home"}`,
		"empty":         `{"machine_id":""}`,
		"unknown field": `{"machine_id":"pc-home","x":1}`,
		"not json":      `{`,
	} {
		if rec := f.do(http.MethodPost, "/api/v2/openrig/machines", "user-jwt", body); rec.Code != http.StatusBadRequest {
			t.Errorf("%s: %d, want 400: %s", name, rec.Code, rec.Body.String())
		}
	}
	if len(f.tokens.tokens) != 0 {
		t.Error("an invalid registration stored a token")
	}
}

func TestMachineTokenValidTokenIsAccepted(t *testing.T) {
	f := newTokenFixture(t)
	token := f.register("pc-home")
	rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", token, validSeatStatusBody)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"machine_id":"pc-home"`) {
		t.Fatalf("POST with a valid token: %d %s", rec.Code, rec.Body.String())
	}
	stored := f.status.byUser[tokenTestUserA]["pc-home"]
	if len(stored.Seats) != 1 || !stored.LastSeen.Equal(seatStatusTestNow) {
		t.Fatalf("stored = %+v, want the report under user A and machine pc-home", stored)
	}
}

func TestMachineTokenRevokedTokenIs401(t *testing.T) {
	f := newTokenFixture(t)
	token := f.register("pc-home")
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", token, validSeatStatusBody); rec.Code != http.StatusOK {
		t.Fatalf("before revoke: %d", rec.Code)
	}
	if rec := f.do(http.MethodDelete, "/api/v2/openrig/machines/pc-home/token", "user-jwt", ""); rec.Code != http.StatusOK {
		t.Fatalf("revoke: %d %s", rec.Code, rec.Body.String())
	}
	f.status.byUser = nil
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", token, validSeatStatusBody); rec.Code != http.StatusUnauthorized {
		t.Fatalf("revoked token: %d, want 401: %s", rec.Code, rec.Body.String())
	}
	if len(f.status.byUser) != 0 {
		t.Error("a revoked token stored a report")
	}

	// The machine can be registered again; the old token stays dead and the new one works.
	fresh := f.register("pc-home")
	if fresh == token {
		t.Fatal("re-registration returned the revoked token")
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", token, validSeatStatusBody); rec.Code != http.StatusUnauthorized {
		t.Errorf("old token after re-registration: %d, want 401", rec.Code)
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", fresh, validSeatStatusBody); rec.Code != http.StatusOK {
		t.Errorf("new token: %d, want 200", rec.Code)
	}
}

func TestMachineTokenOfMachineACannotReportForMachineB(t *testing.T) {
	f := newTokenFixture(t)
	tokenA := f.register("pc-a")
	f.register("pc-b")
	rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", tokenA, reportFor("pc-b"))
	if rec.Code != http.StatusForbidden {
		t.Fatalf("A's token for B: %d, want 403: %s", rec.Code, rec.Body.String())
	}
	if len(f.status.byUser) != 0 {
		t.Errorf("a report for the wrong machine was stored: %+v", f.status.byUser)
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", tokenA, reportFor("pc-a")); rec.Code != http.StatusOK {
		t.Errorf("A's token for A: %d, want 200", rec.Code)
	}
}

func TestMachineTokenOtherUserCannotRevokeAndGetsItsOwnNamespace(t *testing.T) {
	f := newTokenFixture(t)
	tokenA := f.register("pc-home")

	f.user = tokenTestUserB
	if rec := f.do(http.MethodDelete, "/api/v2/openrig/machines/pc-home/token", "user-jwt", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("other user's revoke: %d, want 404: %s", rec.Code, rec.Body.String())
	}
	tokenB := f.register("pc-home") // the same machine id is a different machine for user B
	if tokenB == tokenA {
		t.Fatal("two users got the same token")
	}

	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", tokenA, validSeatStatusBody); rec.Code != http.StatusOK {
		t.Fatalf("A's token after B's attempt: %d, want 200", rec.Code)
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", tokenB, validSeatStatusBody); rec.Code != http.StatusOK {
		t.Fatalf("B's token: %d, want 200", rec.Code)
	}
	if len(f.status.byUser[tokenTestUserA]) != 1 || len(f.status.byUser[tokenTestUserB]) != 1 {
		t.Errorf("reports must land under each token's own user: %+v", f.status.byUser)
	}
}

func TestMachineTokenRevokeUnknownMachineIs404(t *testing.T) {
	f := newTokenFixture(t)
	if rec := f.do(http.MethodDelete, "/api/v2/openrig/machines/ghost/token", "user-jwt", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("revoke unknown machine: %d, want 404", rec.Code)
	}
	f.register("pc-home")
	f.do(http.MethodDelete, "/api/v2/openrig/machines/pc-home/token", "user-jwt", "")
	if rec := f.do(http.MethodDelete, "/api/v2/openrig/machines/pc-home/token", "user-jwt", ""); rec.Code != http.StatusNotFound {
		t.Fatalf("revoke twice: %d, want 404", rec.Code)
	}
}

func TestMachineTokenScopeIsTheBridgeReportEndpointOnly(t *testing.T) {
	f := newTokenFixture(t)
	token := f.register("pc-home")
	for _, c := range []struct{ method, path, body string }{
		{http.MethodGet, "/api/v2/openrig/machines", ""},
		{http.MethodPost, "/api/v2/openrig/machines", `{"machine_id":"other"}`},
		{http.MethodDelete, "/api/v2/openrig/machines/pc-home/token", ""},
	} {
		if rec := f.do(c.method, c.path, token, c.body); rec.Code != http.StatusUnauthorized && rec.Code != http.StatusForbidden {
			t.Errorf("machine token on %s %s: %d, want 401/403", c.method, c.path, rec.Code)
		}
	}
	// the user-authenticated admin routes reject a machine token before touching any data
	for _, c := range []struct{ method, path, body string }{
		{http.MethodGet, "/api/v2/openrig/rooms", ""},
		{http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"x","name":"x"}`},
		{http.MethodGet, "/api/v2/openrig/seat-types", ""},
		{http.MethodPost, "/api/v2/openrig/seat-types/coder/versions", `{"module_refs":[],"default_runtime":"codex"}`},
	} {
		if rec := f.do(c.method, c.path, token, c.body); rec.Code != http.StatusUnauthorized && rec.Code != http.StatusForbidden {
			t.Errorf("machine token on %s %s: %d, want 401/403", c.method, c.path, rec.Code)
		}
	}
	if len(f.tokens.tokens) != 1 || f.tokens.tokens[0].RevokedAt != nil {
		t.Errorf("a machine token changed token state: %+v", f.tokens.tokens)
	}
	// A user token is not a bridge credential.
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", "user-jwt", validSeatStatusBody); rec.Code != http.StatusUnauthorized {
		t.Errorf("user token on seat-status: %d, want 401", rec.Code)
	}
}

func TestMachineTokenBadCredentials(t *testing.T) {
	f := newTokenFixture(t)
	f.register("pc-home")
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", "", validSeatStatusBody); rec.Code != http.StatusForbidden {
		t.Errorf("no Authorization header: %d, want 403", rec.Code)
	}
	for name, bearer := range map[string]string{
		"garbage":                "nope",
		"right prefix, unknown":  "mt_" + strings.Repeat("a", 43),
		"prefix only":            "mt_",
		"user token shaped like": "eyJhbGciOiJSUzI1NiJ9.e30.sig",
	} {
		rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", bearer, validSeatStatusBody)
		if rec.Code != http.StatusUnauthorized {
			t.Errorf("%s: %d, want 401", name, rec.Code)
		}
		if strings.Contains(rec.Body.String(), bearer) && bearer != "" {
			t.Errorf("%s: the response echoes the credential", name)
		}
	}
}

// An unknown, a revoked and a malformed token get the same 401 body, so a caller cannot tell
// a once-valid token from a made-up one.
func TestMachineTokenRejectionsHaveIdenticalBodies(t *testing.T) {
	f := newTokenFixture(t)
	revoked := f.register("pc-home")
	if rec := f.do(http.MethodDelete, "/api/v2/openrig/machines/pc-home/token", "user-jwt", ""); rec.Code != http.StatusOK {
		t.Fatalf("revoke: %d %s", rec.Code, rec.Body.String())
	}
	f.register("pc-home")
	bodies := map[string]string{}
	for name, bearer := range map[string]string{
		"revoked":   revoked,
		"unknown":   "mt_" + strings.Repeat("a", 43),
		"malformed": "nope",
	} {
		rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", bearer, validSeatStatusBody)
		if rec.Code != http.StatusUnauthorized {
			t.Fatalf("%s: %d, want 401", name, rec.Code)
		}
		bodies[name] = rec.Body.String()
	}
	if bodies["revoked"] != bodies["unknown"] || bodies["unknown"] != bodies["malformed"] {
		t.Fatalf("rejection bodies differ: %v", bodies)
	}
}

func TestMachineTokenRepositoryErrorIs500NotAuthFailure(t *testing.T) {
	f := newTokenFixture(t)
	token := f.register("pc-home")
	f.tokens.err = errors.New("database down")
	if rec := f.do(http.MethodPost, "/api/v2/openrig/seat-status", token, validSeatStatusBody); rec.Code != http.StatusInternalServerError {
		t.Errorf("auth lookup failure: %d, want 500", rec.Code)
	}
	if rec := f.do(http.MethodPost, "/api/v2/openrig/machines", "user-jwt", `{"machine_id":"pc-x"}`); rec.Code != http.StatusInternalServerError {
		t.Errorf("register failure: %d, want 500", rec.Code)
	}
}

func TestMachineTokenRoutesNeedUserAuth(t *testing.T) {
	f := newTokenFixture(t)
	for _, c := range []struct{ method, path string }{
		{http.MethodPost, "/api/v2/openrig/machines"},
		{http.MethodDelete, "/api/v2/openrig/machines/pc-home/token"},
	} {
		if rec := f.do(c.method, c.path, "", ""); rec.Code != http.StatusForbidden {
			t.Errorf("%s %s without credentials: %d, want 403", c.method, c.path, rec.Code)
		}
	}
}
