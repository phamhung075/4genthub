package infrastructure

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func newTestSupabaseService(t *testing.T, handler http.HandlerFunc) *SupabaseAuthService {
	t.Helper()
	server := httptest.NewServer(handler)
	t.Cleanup(server.Close)
	return &SupabaseAuthService{
		baseURL:    server.URL,
		anonKey:    "anon-key",
		serviceKey: "service-key",
		jwtSecret:  "test-jwt-secret",
		httpClient: server.Client(),
	}
}

func TestSupabaseSignUpSession(t *testing.T) {
	var path, query, body, apiKey string
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		path = r.URL.Path
		query = r.URL.RawQuery
		apiKey = r.Header.Get("apikey")
		raw, _ := io.ReadAll(r.Body)
		body = string(raw)
		io.WriteString(w, `{"access_token":"at","refresh_token":"rt","expires_in":3600,"token_type":"bearer","user":{"id":"u1","email":"a@b.com","confirmed_at":"2025-01-01T00:00:00Z"}}`)
	})

	result := svc.SignUp(context.Background(), "a@b.com", "pw", nil)
	if !result.Success || result.User == nil || result.Session == nil {
		t.Fatalf("unexpected result: %+v", result)
	}
	if result.User.GetAny("id") != "u1" || result.Session.GetAny("access_token") != "at" {
		t.Fatalf("mapping wrong: user=%v session=%v", result.User, result.Session)
	}
	if path != "/auth/v1/signup" {
		t.Fatalf("path = %q", path)
	}
	if query != "redirect_to=http%3A%2F%2Flocalhost%3A3800%2Fauth%2Fverify" {
		t.Fatalf("query = %q", query)
	}
	if apiKey != "anon-key" {
		t.Fatalf("apikey = %q", apiKey)
	}
	wantBody := `{"email":"a@b.com","password":"pw","data":{},"gotrue_meta_security":{"captcha_token":null}}`
	if body != wantBody {
		t.Fatalf("body = %s want %s", body, wantBody)
	}
}

func TestSupabaseSignUpRequiresVerification(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, `{"user":{"id":"u1","email":"a@b.com","confirmed_at":null}}`)
	})
	result := svc.SignUp(context.Background(), "a@b.com", "pw", nil)
	if !result.Success || !result.RequiresEmailVerification {
		t.Fatalf("result = %+v", result)
	}
	if result.ErrorMessage == nil || *result.ErrorMessage != "Please check your email to verify your account" {
		t.Fatalf("error = %v", result.ErrorMessage)
	}
}

func TestSupabaseSignUpErrorMapping(t *testing.T) {
	cases := []struct {
		status int
		body   string
		want   string
	}{
		{400, `{"msg":"User already registered"}`, "Email already registered"},
		{422, `{"msg":"Password should be at least 6 characters"}`, "Password must be at least 6 characters"},
		{500, `{"msg":"boom"}`, "Unable to create account. Please try again later."},
	}
	for _, tc := range cases {
		svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(tc.status)
			io.WriteString(w, tc.body)
		})
		result := svc.SignUp(context.Background(), "a@b.com", "pw", nil)
		if result.Success || result.ErrorMessage == nil || *result.ErrorMessage != tc.want {
			t.Fatalf("status %d: %+v want %q", tc.status, result, tc.want)
		}
	}
}

func TestSupabaseSignIn(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/auth/v1/token" || r.URL.Query().Get("grant_type") != "password" {
			t.Errorf("unexpected request %s?%s", r.URL.Path, r.URL.RawQuery)
		}
		io.WriteString(w, `{"access_token":"at","refresh_token":"rt","expires_in":3600,"token_type":"bearer","user":{"id":"u1","confirmed_at":"2025-01-01T00:00:00Z"}}`)
	})
	result := svc.SignIn(context.Background(), "a@b.com", "pw")
	if !result.Success || result.Session == nil {
		t.Fatalf("result = %+v", result)
	}
}

func TestSupabaseSignInUnconfirmed(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		io.WriteString(w, `{"access_token":"at","refresh_token":"rt","expires_in":3600,"token_type":"bearer","user":{"id":"u1","confirmed_at":null}}`)
	})
	result := svc.SignIn(context.Background(), "a@b.com", "pw")
	if result.Success || !result.RequiresEmailVerification {
		t.Fatalf("result = %+v", result)
	}
}

func TestSupabaseSignInErrorMapping(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(400)
		io.WriteString(w, `{"msg":"Invalid login credentials"}`)
	})
	result := svc.SignIn(context.Background(), "a@b.com", "pw")
	if result.Success || result.ErrorMessage == nil || *result.ErrorMessage != "Invalid email or password" {
		t.Fatalf("result = %+v", result)
	}
}

func TestSupabaseVerifyTokenAdmin(t *testing.T) {
	var auth, apiKey string
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		auth = r.Header.Get("Authorization")
		apiKey = r.Header.Get("apikey")
		if r.Method != "GET" || r.URL.Path != "/auth/v1/user" {
			t.Errorf("unexpected request %s %s", r.Method, r.URL.Path)
		}
		io.WriteString(w, `{"id":"u1","email":"a@b.com","confirmed_at":"2025-01-01T00:00:00Z"}`)
	})
	result := svc.VerifyToken(context.Background(), "the-access-token")
	if !result.Success || result.User == nil || result.User.GetAny("id") != "u1" {
		t.Fatalf("result = %+v", result)
	}
	if auth != "Bearer the-access-token" || apiKey != "service-key" {
		t.Fatalf("headers auth=%q apikey=%q", auth, apiKey)
	}
}

// Generated with PyJWT for secret "test-jwt-secret" (aud authenticated, exp 2100-01-01).
const validSupabaseJWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoiYWxpY2VAZXhhbXBsZS5jb20iLCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImF1ZCI6ImF1dGhlbnRpY2F0ZWQiLCJleHAiOjQxMDI0NDQ4MDAsInVzZXJfbWV0YWRhdGEiOnsidXNlcm5hbWUiOiJhbGljZSJ9LCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCJ9LCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzAwMDAwMDAwfV0sInNlc3Npb25faWQiOiJzZXNzLTEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ._1SZ5ZepM6gBKhCs7_Cy0AVBYmVK293EpVMj2XfGg_g"

const expiredSupabaseJWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoiYWxpY2VAZXhhbXBsZS5jb20iLCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImF1ZCI6ImF1dGhlbnRpY2F0ZWQiLCJleHAiOjEwMDAwMDAwMDAsInVzZXJfbWV0YWRhdGEiOnsidXNlcm5hbWUiOiJhbGljZSJ9LCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCJ9LCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzAwMDAwMDAwfV0sInNlc3Npb25faWQiOiJzZXNzLTEiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.FVOhTQR6sG28BY76pgFEyb8z4qPLEY-4b5-j-E1cdRU"

func TestSupabaseVerifyTokenManualJWTFallback(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(401)
		io.WriteString(w, `{"msg":"invalid"}`)
	})
	result := svc.VerifyToken(context.Background(), validSupabaseJWT)
	if !result.Success || result.User == nil {
		t.Fatalf("manual validation failed: %+v", result)
	}
	if result.User.GetAny("id") != "user-123" || result.User.GetAny("role") != "authenticated" {
		t.Fatalf("user = %v", result.User)
	}
	if result.User.GetAny("confirmed_at") != true || result.User.GetAny("email_confirmed_at") != true {
		t.Fatalf("confirmed flags = %v", result.User)
	}
	userMetadata, _ := result.User.Get("user_metadata")
	um, ok := userMetadata.(*entities.OrderedMap[any])
	if !ok || um.GetAny("username") != "alice" {
		t.Fatalf("user_metadata = %v", userMetadata)
	}

	expired := svc.VerifyToken(context.Background(), expiredSupabaseJWT)
	if expired.Success {
		t.Fatalf("expired token accepted: %+v", expired)
	}
}

func TestSupabaseSignInWithProviderURL(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		t.Fatalf("sign_in_with_provider must not make a request")
	})
	out := svc.SignInWithProvider(context.Background(), "google")
	want := svc.baseURL + "/auth/v1/authorize?redirect_to=http%3A%2F%2Flocalhost%3A3800%2Fauth%2Fcallback&provider=google"
	if out.GetAny("url") != want || out.GetAny("provider") != "google" {
		t.Fatalf("out = %v want url %q", out, want)
	}
}

func TestSupabaseRefreshSession(t *testing.T) {
	var body string
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Query().Get("grant_type") != "refresh_token" {
			t.Errorf("grant_type = %q", r.URL.Query().Get("grant_type"))
		}
		raw, _ := io.ReadAll(r.Body)
		body = string(raw)
		io.WriteString(w, `{"access_token":"at2","refresh_token":"rt2","expires_in":3600,"token_type":"bearer","user":{"id":"u1"}}`)
	})
	result := svc.RefreshSession(context.Background(), "rt")
	if !result.Success || result.Session == nil {
		t.Fatalf("result = %+v", result)
	}
	if body != `{"refresh_token":"rt"}` {
		t.Fatalf("body = %s", body)
	}
}

func TestSupabaseResetAndResend(t *testing.T) {
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/auth/v1/recover":
			io.WriteString(w, `{}`)
		case "/auth/v1/signup":
			io.WriteString(w, `{"id":"u1","email":"a@b.com","confirmed_at":"2025-01-01T00:00:00Z"}`)
		default:
			t.Errorf("unexpected path %s", r.URL.Path)
		}
	})
	reset := svc.ResetPasswordRequest(context.Background(), "a@b.com")
	if !reset.Success || reset.ErrorMessage == nil || *reset.ErrorMessage != "Password reset email sent. Please check your inbox." {
		t.Fatalf("reset = %+v", reset)
	}
	resend := svc.ResendVerificationEmail(context.Background(), "a@b.com")
	if resend.Success || resend.ErrorMessage == nil || *resend.ErrorMessage != "This email is already verified. Please try logging in." {
		t.Fatalf("resend = %+v", resend)
	}
}

func TestSupabaseResendVerificationUnconfirmed(t *testing.T) {
	var body string
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		raw, _ := io.ReadAll(r.Body)
		body = string(raw)
		io.WriteString(w, `{"id":"u1","email":"a@b.com","confirmed_at":null}`)
	})
	result := svc.ResendVerificationEmail(context.Background(), "a@b.com")
	if !result.Success || result.ErrorMessage == nil || *result.ErrorMessage != "Verification email sent. Please check your inbox." {
		t.Fatalf("resend = %+v", result)
	}
	if !strings.HasPrefix(body, `{"email":"a@b.com","password":"temporary_resend_`) {
		t.Fatalf("body = %s", body)
	}
}

func TestSupabaseSignOut(t *testing.T) {
	var path, query string
	svc := newTestSupabaseService(t, func(w http.ResponseWriter, r *http.Request) {
		path = r.URL.Path
		query = r.URL.RawQuery
		w.WriteHeader(204)
	})
	if !svc.SignOut(context.Background(), "token") {
		t.Fatal("SignOut returned false")
	}
	if path != "/auth/v1/logout" || query != "scope=global" {
		t.Fatalf("path=%q query=%q", path, query)
	}
}
