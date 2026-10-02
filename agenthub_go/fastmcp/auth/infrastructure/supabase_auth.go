// Supabase Authentication Integration
// (Python auth/infrastructure/supabase_auth.py).
//
// The Python module drives the supabase-py client; here the same GoTrue calls are made
// directly over net/http with the exact paths, query strings and compact JSON bodies that
// supabase-py 2.24.0 sends. Logging and the socket reachability probe are dropped.
// If USE_MOCK_AUTH is true the Python import of the (missing) mock_supabase_auth module
// fails, so the Go constructor returns an equivalent error.

package infrastructure

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"reflect"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SupabaseAuthResult is the SupabaseAuthResult dataclass.
type SupabaseAuthResult struct {
	Success                   bool
	User                      *entities.OrderedMap[any]
	Session                   *entities.OrderedMap[any]
	ErrorMessage              *string
	RequiresEmailVerification bool
}

// SupabaseAuthService handles Supabase authentication.
type SupabaseAuthService struct {
	baseURL    string
	anonKey    string
	serviceKey string
	jwtSecret  string
	httpClient *http.Client
}

// NewSupabaseAuthService is __init__ with the GoTrue base URL derived from SUPABASE_URL.
func NewSupabaseAuthService() (*SupabaseAuthService, error) {
	supabaseURL := os.Getenv("SUPABASE_URL")
	anonKey := os.Getenv("SUPABASE_ANON_KEY")
	serviceKey := os.Getenv("SUPABASE_SERVICE_ROLE_KEY")
	jwtSecret := os.Getenv("SUPABASE_JWT_SECRET")

	if supabaseURL == "" || anonKey == "" {
		return nil, value_objects.ValueErrorf("Missing Supabase credentials: SUPABASE_URL and SUPABASE_ANON_KEY must be set")
	}

	if envBoolTrue("USE_MOCK_AUTH", "false") {
		return nil, fmt.Errorf("cannot import MockSupabaseClient from mock_supabase_auth")
	}

	httpClient := &http.Client{}
	if selfHostedIPPattern.MatchString(supabaseURL) {
		httpClient = &http.Client{
			Transport: &http.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}},
			Timeout:   30 * time.Second,
		}
	}
	return &SupabaseAuthService{
		baseURL:    supabaseURL,
		anonKey:    anonKey,
		serviceKey: serviceKey,
		jwtSecret:  jwtSecret,
		httpClient: httpClient,
	}, nil
}

// adminKey is `supabase_service_key or supabase_anon_key`.
func (s *SupabaseAuthService) adminKey() string {
	if s.serviceKey != "" {
		return s.serviceKey
	}
	return s.anonKey
}

func supabaseFrontendURL() string {
	return getenvDefault("FRONTEND_URL", "http://localhost:3800")
}

// supabaseAPIError is the AuthApiError raised for a non-2xx response.
type supabaseAPIError struct {
	StatusCode int
	Message    string
}

func (e *supabaseAPIError) Error() string { return e.Message }

// request performs one GoTrue call and returns the response for a 2xx status.
func (s *SupabaseAuthService) request(ctx context.Context, method, path string, body any, query url.Values, jwt, apiKey string) (*http.Response, error) {
	full := strings.TrimRight(s.baseURL, "/") + "/auth/v1/" + path
	if len(query) > 0 {
		full += "?" + query.Encode()
	}
	var reader io.Reader
	if body != nil {
		encoded, err := supabaseEncodeJSON(body)
		if err != nil {
			return nil, err
		}
		reader = bytes.NewReader(encoded)
	}
	req, err := http.NewRequestWithContext(ctx, method, full, reader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("apikey", apiKey)
	if jwt != "" {
		req.Header.Set("Authorization", "Bearer "+jwt)
	} else {
		req.Header.Set("Authorization", "Bearer "+apiKey)
	}
	req.Header.Set("Content-Type", "application/json;charset=UTF-8")
	req.Header.Set("X-Supabase-Api-Version", "2024-01-01")

	client := s.httpClient
	if client == nil {
		client = http.DefaultClient
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode >= 400 {
		msg := supabaseErrorMessage(resp)
		resp.Body.Close()
		return nil, &supabaseAPIError{StatusCode: resp.StatusCode, Message: msg}
	}
	return resp, nil
}

// supabaseErrorMessage is helpers.get_error_message applied to the error body.
func supabaseErrorMessage(resp *http.Response) string {
	b, _ := io.ReadAll(resp.Body)
	trimmed := strings.TrimSpace(string(b))
	if v, err := entities.DecodeJSON(b); err == nil {
		if om, ok := v.(*entities.OrderedMap[any]); ok {
			for _, key := range []string{"msg", "message", "error_description", "error"} {
				if val, ok := om.Get(key); ok {
					if s, ok := val.(string); ok && s != "" {
						return s
					}
				}
			}
		}
	}
	if trimmed != "" {
		return trimmed
	}
	return resp.Status
}

func decodeSupabaseObject(resp *http.Response) *entities.OrderedMap[any] {
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil
	}
	v, err := entities.DecodeJSON(b)
	if err != nil {
		return nil
	}
	om, _ := v.(*entities.OrderedMap[any])
	return om
}

// supabaseParseAuthResponse is parse_auth_response: a session-shaped body yields the
// session and its user; otherwise the body is the user.
func supabaseParseAuthResponse(obj *entities.OrderedMap[any]) (user, session *entities.OrderedMap[any]) {
	if obj == nil {
		return nil, nil
	}
	if obj.Has("access_token") {
		u, _ := obj.Get("user")
		um, _ := u.(*entities.OrderedMap[any])
		return um, obj
	}
	return obj, nil
}

// SignUp is sign_up.
func (s *SupabaseAuthService) SignUp(ctx context.Context, email, password string, metadata *entities.OrderedMap[any]) SupabaseAuthResult {
	data := metadata
	if data == nil {
		data = entities.NewOrderedMap[any]()
	}
	security := entities.NewOrderedMap[any]()
	security.Set("captcha_token", nil)
	body := entities.NewOrderedMap[any]()
	body.Set("email", email)
	body.Set("password", password)
	body.Set("data", data)
	body.Set("gotrue_meta_security", security)
	query := url.Values{}
	query.Set("redirect_to", supabaseFrontendURL()+"/auth/verify")

	resp, err := s.request(ctx, "POST", "signup", body, query, "", s.anonKey)
	if err != nil {
		return supabaseSignUpError(err.Error())
	}
	defer resp.Body.Close()
	user, session := supabaseParseAuthResponse(decodeSupabaseObject(resp))
	if user != nil {
		if !value_objects.PyTruthy(user.GetAny("confirmed_at")) {
			return SupabaseAuthResult{
				Success:                   true,
				User:                      user,
				Session:                   session,
				RequiresEmailVerification: true,
				ErrorMessage:              stringPtr("Please check your email to verify your account"),
			}
		}
		return SupabaseAuthResult{Success: true, User: user, Session: session}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Failed to create user account")}
}

func supabaseSignUpError(errorMsg string) SupabaseAuthResult {
	switch {
	case strings.Contains(errorMsg, "SSL") || strings.Contains(errorMsg, "CERTIFICATE_VERIFY_FAILED"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Unable to create account. Please try again.")}
	case strings.Contains(errorMsg, "User already registered"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Email already registered")}
	case strings.Contains(errorMsg, "Password should be at least"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Password must be at least 6 characters")}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Unable to create account. Please try again later.")}
}

// SignIn is sign_in.
func (s *SupabaseAuthService) SignIn(ctx context.Context, email, password string) SupabaseAuthResult {
	security := entities.NewOrderedMap[any]()
	security.Set("captcha_token", nil)
	body := entities.NewOrderedMap[any]()
	body.Set("email", email)
	body.Set("password", password)
	body.Set("data", entities.NewOrderedMap[any]())
	body.Set("gotrue_meta_security", security)
	query := url.Values{}
	query.Set("grant_type", "password")

	resp, err := s.request(ctx, "POST", "token", body, query, "", s.anonKey)
	if err != nil {
		return supabaseSignInError(err.Error())
	}
	defer resp.Body.Close()
	user, session := supabaseParseAuthResponse(decodeSupabaseObject(resp))
	if user != nil && session != nil {
		if !value_objects.PyTruthy(user.GetAny("confirmed_at")) {
			return SupabaseAuthResult{
				Success:                   false,
				RequiresEmailVerification: true,
				ErrorMessage:              stringPtr("Please verify your email before signing in"),
			}
		}
		return SupabaseAuthResult{Success: true, User: user, Session: session}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Invalid email or password")}
}

func supabaseSignInError(errorMsg string) SupabaseAuthResult {
	switch {
	case strings.Contains(errorMsg, "SSL") || strings.Contains(errorMsg, "CERTIFICATE_VERIFY_FAILED"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Invalid email or password")}
	case strings.Contains(errorMsg, "Invalid login credentials"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Invalid email or password")}
	case strings.Contains(errorMsg, "Email not confirmed"):
		return SupabaseAuthResult{
			Success:                   false,
			RequiresEmailVerification: true,
			ErrorMessage:              stringPtr("Please verify your email before signing in"),
		}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Authentication service temporarily unavailable. Please try again.")}
}

// SignOut is sign_out; it POSTs logout?scope=global with the access token.
func (s *SupabaseAuthService) SignOut(ctx context.Context, accessToken string) bool {
	query := url.Values{}
	query.Set("scope", "global")
	resp, err := s.request(ctx, "POST", "logout", nil, query, accessToken, s.anonKey)
	if err != nil {
		return false
	}
	resp.Body.Close()
	return true
}

// ResetPasswordRequest is reset_password_request.
func (s *SupabaseAuthService) ResetPasswordRequest(ctx context.Context, email string) SupabaseAuthResult {
	security := entities.NewOrderedMap[any]()
	security.Set("captcha_token", nil)
	body := entities.NewOrderedMap[any]()
	body.Set("email", email)
	body.Set("gotrue_meta_security", security)
	query := url.Values{}
	query.Set("redirect_to", supabaseFrontendURL()+"/auth/reset-password")

	resp, err := s.request(ctx, "POST", "recover", body, query, "", s.anonKey)
	if err != nil {
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Failed to send password reset email")}
	}
	resp.Body.Close()
	return SupabaseAuthResult{Success: true, ErrorMessage: stringPtr("Password reset email sent. Please check your inbox.")}
}

// UpdatePassword is update_password (PUT user with the access token).
func (s *SupabaseAuthService) UpdatePassword(ctx context.Context, accessToken, newPassword string) SupabaseAuthResult {
	body := entities.NewOrderedMap[any]()
	body.Set("password", newPassword)
	resp, err := s.request(ctx, "PUT", "user", body, nil, accessToken, s.anonKey)
	if err != nil {
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr(err.Error())}
	}
	defer resp.Body.Close()
	user := decodeSupabaseObject(resp)
	if user != nil {
		return SupabaseAuthResult{Success: true, User: user}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Failed to update password")}
}

// VerifyToken is verify_token: the admin /user call, then a manual HS256 check.
func (s *SupabaseAuthService) VerifyToken(ctx context.Context, accessToken string) SupabaseAuthResult {
	resp, err := s.request(ctx, "GET", "user", nil, nil, accessToken, s.adminKey())
	if err == nil {
		user := decodeSupabaseObject(resp)
		resp.Body.Close()
		if user != nil {
			return SupabaseAuthResult{Success: true, User: user}
		}
	}
	if s.jwtSecret != "" {
		if user, ok := verifySupabaseAccessToken(accessToken, s.jwtSecret); ok {
			return SupabaseAuthResult{Success: true, User: user}
		}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Invalid or expired token")}
}

// verifySupabaseAccessToken is pyjwt.decode(..., algorithms=["HS256"], audience="authenticated",
// options={"verify_iss": False}) followed by the manually built user dict.
func verifySupabaseAccessToken(token, secret string) (*entities.OrderedMap[any], bool) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, false
	}
	headerBytes, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return nil, false
	}
	var header map[string]any
	if err := json.Unmarshal(headerBytes, &header); err != nil {
		return nil, false
	}
	if header["alg"] != "HS256" {
		return nil, false
	}
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(parts[0] + "." + parts[1]))
	signature, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil || !hmac.Equal(mac.Sum(nil), signature) {
		return nil, false
	}
	payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, false
	}
	decoded, err := entities.DecodeJSON(payloadBytes)
	if err != nil {
		return nil, false
	}
	payload, ok := decoded.(*entities.OrderedMap[any])
	if !ok {
		return nil, false
	}
	now := time.Now().Unix()
	if exp, ok := payload.Get("exp"); ok {
		if f, ok := value_objects.PyFloat(exp); ok && float64(now) > f {
			return nil, false
		}
	}
	if nbf, ok := payload.Get("nbf"); ok {
		if f, ok := value_objects.PyFloat(nbf); ok && float64(now) < f {
			return nil, false
		}
	}
	aud, _ := payload.Get("aud")
	if !supabaseAudienceAuthenticated(aud) {
		return nil, false
	}
	user := entities.NewOrderedMap[any]()
	user.Set("id", supabaseClaim(payload, "sub", nil))
	user.Set("email", supabaseClaim(payload, "email", nil))
	user.Set("phone", supabaseClaim(payload, "phone", ""))
	user.Set("user_metadata", supabaseClaim(payload, "user_metadata", entities.NewOrderedMap[any]()))
	user.Set("app_metadata", supabaseClaim(payload, "app_metadata", entities.NewOrderedMap[any]()))
	user.Set("role", supabaseClaim(payload, "role", "authenticated"))
	user.Set("aal", supabaseClaim(payload, "aal", nil))
	user.Set("amr", supabaseClaim(payload, "amr", []any{}))
	user.Set("session_id", supabaseClaim(payload, "session_id", nil))
	user.Set("is_anonymous", supabaseClaim(payload, "is_anonymous", false))
	user.Set("confirmed_at", true)
	user.Set("email_confirmed_at", true)
	return user, true
}

func supabaseAudienceAuthenticated(aud any) bool {
	switch x := aud.(type) {
	case string:
		return x == "authenticated"
	case []any:
		for _, candidate := range x {
			if s, ok := candidate.(string); ok && s == "authenticated" {
				return true
			}
		}
	}
	return false
}

func supabaseClaim(payload *entities.OrderedMap[any], key string, def any) any {
	if v, ok := payload.Get(key); ok {
		return v
	}
	return def
}

// ResendVerificationEmail is resend_verification_email (a fresh signup with a dummy password).
func (s *SupabaseAuthService) ResendVerificationEmail(ctx context.Context, email string) SupabaseAuthResult {
	randomBytes := make([]byte, 16)
	if _, err := rand.Read(randomBytes); err != nil {
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Failed to resend verification email. Please try again later.")}
	}
	security := entities.NewOrderedMap[any]()
	security.Set("captcha_token", nil)
	body := entities.NewOrderedMap[any]()
	body.Set("email", email)
	body.Set("password", "temporary_resend_"+hex.EncodeToString(randomBytes))
	body.Set("data", entities.NewOrderedMap[any]())
	body.Set("gotrue_meta_security", security)
	query := url.Values{}
	query.Set("redirect_to", supabaseFrontendURL()+"/auth/verify")

	resp, err := s.request(ctx, "POST", "signup", body, query, "", s.anonKey)
	if err != nil {
		return supabaseResendError(err.Error())
	}
	defer resp.Body.Close()
	user, _ := supabaseParseAuthResponse(decodeSupabaseObject(resp))
	if user != nil && !value_objects.PyTruthy(user.GetAny("confirmed_at")) {
		return SupabaseAuthResult{Success: true, ErrorMessage: stringPtr("Verification email sent. Please check your inbox.")}
	} else if user != nil && value_objects.PyTruthy(user.GetAny("confirmed_at")) {
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("This email is already verified. Please try logging in.")}
	}
	return SupabaseAuthResult{Success: true, ErrorMessage: stringPtr("Verification email sent. Please check your inbox.")}
}

func supabaseResendError(errorMsg string) SupabaseAuthResult {
	lower := strings.ToLower(errorMsg)
	switch {
	case strings.Contains(lower, "already been registered") || strings.Contains(lower, "user already registered"):
		return SupabaseAuthResult{Success: true, ErrorMessage: stringPtr("Verification email sent. Please check your inbox.")}
	case strings.Contains(lower, "rate limit"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Too many requests. Please wait 60 seconds before trying again.")}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Failed to resend verification email. Please try again later.")}
}

// SignInWithProvider is sign_in_with_provider, which only builds the OAuth URL.
func (s *SupabaseAuthService) SignInWithProvider(ctx context.Context, provider string) *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	redirectTo := supabaseFrontendURL() + "/auth/callback"
	authorizeURL := strings.TrimRight(s.baseURL, "/") + "/auth/v1/authorize?redirect_to=" +
		url.QueryEscape(redirectTo) + "&provider=" + url.QueryEscape(provider)
	out.Set("url", authorizeURL)
	out.Set("provider", provider)
	return out
}

// RefreshSession is refresh_session.
func (s *SupabaseAuthService) RefreshSession(ctx context.Context, refreshToken string) SupabaseAuthResult {
	body := entities.NewOrderedMap[any]()
	body.Set("refresh_token", refreshToken)
	query := url.Values{}
	query.Set("grant_type", "refresh_token")

	resp, err := s.request(ctx, "POST", "token", body, query, "", s.anonKey)
	if err != nil {
		return supabaseRefreshError(err.Error())
	}
	defer resp.Body.Close()
	user, session := supabaseParseAuthResponse(decodeSupabaseObject(resp))
	if user != nil && session != nil {
		return SupabaseAuthResult{Success: true, User: user, Session: session}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Invalid or expired refresh token")}
}

func supabaseRefreshError(errorMsg string) SupabaseAuthResult {
	switch {
	case strings.Contains(errorMsg, "Invalid Refresh Token") || strings.Contains(errorMsg, "refresh_token"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Refresh token expired or invalid")}
	case strings.Contains(errorMsg, "Network") || strings.Contains(errorMsg, "Connection"):
		return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Network error during token refresh")}
	}
	return SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("Token refresh failed. Please sign in again.")}
}

// supabaseEncodeJSON is httpx's encode_json: compact separators and ensure_ascii=False.
func supabaseEncodeJSON(v any) ([]byte, error) {
	var b strings.Builder
	if err := supabaseWriteJSON(&b, v); err != nil {
		return nil, err
	}
	return []byte(b.String()), nil
}

func supabaseWriteJSON(b *strings.Builder, v any) error {
	if v == nil {
		b.WriteString("null")
		return nil
	}
	switch x := v.(type) {
	case string:
		b.WriteString(jsonStringNoHTML(x))
		return nil
	case bool:
		if x {
			b.WriteString("true")
		} else {
			b.WriteString("false")
		}
		return nil
	case *entities.OrderedMap[any]:
		keys := x.Keys()
		b.WriteByte('{')
		for i, k := range keys {
			if i > 0 {
				b.WriteByte(',')
			}
			b.WriteString(jsonStringNoHTML(k))
			b.WriteByte(':')
			if err := supabaseWriteJSON(b, x.GetAny(k)); err != nil {
				return err
			}
		}
		b.WriteByte('}')
		return nil
	case []any:
		b.WriteByte('[')
		for i, item := range x {
			if i > 0 {
				b.WriteByte(',')
			}
			if err := supabaseWriteJSON(b, item); err != nil {
				return err
			}
		}
		b.WriteByte(']')
		return nil
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		b.WriteString(strconv.FormatInt(rv.Int(), 10))
		return nil
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		b.WriteString(strconv.FormatUint(rv.Uint(), 10))
		return nil
	case reflect.Float32, reflect.Float64:
		b.WriteString(value_objects.PyStr(rv.Float()))
		return nil
	}
	return fmt.Errorf("Object of type %s is not JSON serializable", rv.Type().Name())
}

// jsonStringNoHTML writes a quoted JSON string with ensure_ascii=False and without HTML
// escaping (Python json.dumps defaults).
func jsonStringNoHTML(s string) string {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(s)
	return strings.TrimSuffix(buf.String(), "\n")
}
