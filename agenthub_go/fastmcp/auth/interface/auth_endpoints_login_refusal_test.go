package authinterface

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"sync"
	"testing"

	authpkg "agenthub/fastmcp/auth"
)

// capturedForm is the form the fake token endpoint received. It is a struct rather than a returned
// *url.Values because the handler fills it AFTER the helper returns: reassigning a returned pointer
// would leave the caller reading the initial empty map.
type capturedForm struct {
	mu     sync.Mutex
	values url.Values
}

func (c *capturedForm) get(key string) string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.values.Get(key)
}

func (c *capturedForm) String() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.values.Encode()
}

// keycloakRefusal stands in for the realm's token endpoint: it answers one scripted refusal and
// records the form it was sent, so the test drives the real Login path rather than a mock of it.
func keycloakRefusal(t *testing.T, status int, body string) *capturedForm {
	t.Helper()
	seen := &capturedForm{}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/realms/test/protocol/openid-connect/token" {
			t.Errorf("the token request went to %q, want the realm's token endpoint", r.URL.Path)
		}
		raw, _ := io.ReadAll(r.Body)
		if v, err := url.ParseQuery(string(raw)); err == nil {
			seen.mu.Lock()
			seen.values = v
			seen.mu.Unlock()
		}
		w.WriteHeader(status)
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(ts.Close)
	t.Setenv("AUTH_PROVIDER", "keycloak")
	t.Setenv("KEYCLOAK_URL", ts.URL)
	t.Setenv("KEYCLOAK_REALM", "test")
	return seen
}

// TestLoginNamesTheTokenEndpointsRefusal pins the mapping of Keycloak's refusal body onto the verb's
// answer. Before this, every 401 became the same "Invalid credentials": the body was never read, so a
// disabled or temporarily locked account was indistinguishable from a wrong password, and the same
// concurrency measurement (two sign-ins for one account, one answered 401) had nothing to read.
func TestLoginNamesTheTokenEndpointsRefusal(t *testing.T) {
	cases := []struct {
		name       string
		status     int
		body       string
		wantStatus int
		wantDetail string
	}{
		{
			name:       "a wrong password keeps the measured string",
			status:     401,
			body:       `{"error":"invalid_grant","error_description":"Invalid user credentials"}`,
			wantStatus: 401,
			wantDetail: "Invalid credentials",
		},
		{
			name:       "a disabled account is named",
			status:     401,
			body:       `{"error":"invalid_grant","error_description":"Account disabled"}`,
			wantStatus: 403,
			wantDetail: "Account is disabled. Contact an administrator.",
		},
		{
			name:       "a brute-force lockout is named, not called disabled",
			status:     401,
			body:       `{"error":"invalid_grant","error_description":"Account is temporarily disabled"}`,
			wantStatus: 403,
			wantDetail: "Account is temporarily locked after repeated failed sign-ins. Try again later.",
		},
		{
			name:       "an invalid_grant on 400 keeps the friendly 401",
			status:     400,
			body:       `{"error":"invalid_grant","error_description":"invalid_grant"}`,
			wantStatus: 401,
			wantDetail: "Invalid email or password. Please check your credentials and try again.",
		},
		{
			name:       "an account that is not fully set up keeps its registration hint",
			status:     400,
			body:       `{"error":"invalid_grant","error_description":"Account is not fully set up"}`,
			wantStatus: 400,
			wantDetail: "Your account is incomplete. Please try registering again with this email address. The system will handle any existing account issues automatically.",
		},
		{
			name:       "any other description reaches the detail instead of being dropped",
			status:     400,
			body:       `{"error":"invalid_request","error_description":"Missing parameter: username"}`,
			wantStatus: 400,
			wantDetail: "Authentication failed: Missing parameter: username",
		},
		{
			name:       "an empty refusal body does not invent a reason",
			status:     503,
			body:       ``,
			wantStatus: 503,
			wantDetail: "Authentication failed",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_ = keycloakRefusal(t, tc.status, tc.body)

			_, err := NewAuthController().Login(context.Background(), LoginRequest{
				Email:    "seat@example.com",
				Password: "CorrectHorse123!",
			})
			var he *authpkg.HTTPException
			if !errors.As(err, &he) {
				t.Fatalf("Login returned %v, want an HTTPException", err)
			}
			if he.StatusCode != tc.wantStatus || he.Detail != tc.wantDetail {
				t.Fatalf("Login answered %d %q, want %d %q", he.StatusCode, he.Detail, tc.wantStatus, tc.wantDetail)
			}
		})
	}
}

// TestLoginSendsTheAccountAndLogsTheRefusal holds the two facts the mapping depends on: the request
// carries the account the refusal is about, and the server log carries the pair the token endpoint
// sent, so a seat can read the reason without a packet capture.
func TestLoginSendsTheAccountAndLogsTheRefusal(t *testing.T) {
	seen := keycloakRefusal(t, 401, `{"error":"invalid_grant","error_description":"Account disabled"}`)

	var logs bytes.Buffer
	prevLog := log.Writer()
	log.SetOutput(&logs)
	t.Cleanup(func() { log.SetOutput(prevLog) })

	_, _ = NewAuthController().Login(context.Background(), LoginRequest{
		Email:    "seat@example.com",
		Password: "CorrectHorse123!",
	})

	if seen.get("username") != "seat@example.com" || seen.get("grant_type") != "password" {
		t.Fatalf("the token request carried %q, want grant_type=password username=seat@example.com", seen)
	}
	if seen.get("password") != "CorrectHorse123!" {
		t.Fatalf("the token request did not carry the password field: %q", seen)
	}
	line := logs.String()
	if !strings.Contains(line, `description="Account disabled"`) || !strings.Contains(line, "seat@example.com") {
		t.Fatalf("the log does not carry the refusal: %q", line)
	}
	if strings.Contains(line, "CorrectHorse123!") {
		t.Fatalf("the log carries the password: %q", line)
	}
}

// TestLoginResponseMappingIsUnchangedOnSuccess guards the direction the change could break: a 200
// still produces the same LoginResponse fields read from the token and its claims.
func TestLoginResponseMappingIsUnchangedOnSuccess(t *testing.T) {
	token := "e30.eyJzdWIiOiJ1c2VyLTEiLCJlbWFpbCI6InNlYXRAZXhhbXBsZS5jb20ifQ." // {"sub":"user-1","email":"seat@example.com"}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"access_token":"` + token + `","refresh_token":"r-1","expires_in":300}`))
	}))
	t.Cleanup(ts.Close)
	t.Setenv("AUTH_PROVIDER", "keycloak")
	t.Setenv("KEYCLOAK_URL", ts.URL)
	t.Setenv("KEYCLOAK_REALM", "test")

	res, err := NewAuthController().Login(context.Background(), LoginRequest{Email: "seat@example.com", Password: "x"})
	if err != nil || res == nil {
		t.Fatalf("Login returned %v, %v; want the token response", res, err)
	}
	if res.AccessToken != token || res.RefreshToken == nil || *res.RefreshToken != "r-1" {
		t.Fatalf("Login answered %+v, want the token and its refresh token", res)
	}
	if res.UserID == nil || *res.UserID != "user-1" || res.Email == nil || *res.Email != "seat@example.com" {
		t.Fatalf("Login answered user %v, want user-1 and the claim email", res)
	}
	if res.ExpiresIn == nil || *res.ExpiresIn != 300 {
		t.Fatalf("Login answered expires_in %v, want 300", res.ExpiresIn)
	}
	body, _ := json.Marshal(res)
	if !strings.Contains(string(body), `"access_token":"`+token+`"`) {
		t.Fatalf("the response does not marshal the token: %s", body)
	}
}
