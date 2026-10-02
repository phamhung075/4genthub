// Authentication factory, ported from
// agenthub_main/src/fastmcp/auth/application/auth_factory.py.
//
// The Python module picks one of three auth providers (Supabase, Keycloak, Local)
// and adapts each concrete service to a unified AuthResult. The Python adapters
// reach into infrastructure / a DB session in __init__ or _get_auth_service; in Go
// the concrete dependencies are injected so the application layer never touches the
// database package. Logging calls are dropped as instructed.
package application

import (
	"context"
	"os"
	"strings"

	authroot "agenthub/fastmcp/auth"
	"agenthub/fastmcp/auth/application/services"
	authentities "agenthub/fastmcp/auth/domain/entities"
	domainservices "agenthub/fastmcp/auth/domain/services"
	"agenthub/fastmcp/auth/infrastructure"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// AuthProvider enumerates the supported authentication providers.
type AuthProvider string

const (
	AuthProviderSupabase AuthProvider = "supabase"
	AuthProviderKeycloak AuthProvider = "keycloak"
	AuthProviderLocal    AuthProvider = "local"
)

// AuthResult is the unified authentication result (Python pydantic AuthResult).
type AuthResult struct {
	Success                   bool
	ErrorMessage              *string
	User                      *tmentities.OrderedMap[any]
	AccessToken               *string
	RefreshToken              *string
	RequiresEmailVerification bool
	ExpiresIn                 int
}

// authResultDefault returns an AuthResult with the pydantic default expires_in=900.
func authResultDefault() AuthResult { return AuthResult{ExpiresIn: 900} }

// AuthServiceInterface is the abstract authentication service interface.
type AuthServiceInterface interface {
	SignUp(ctx context.Context, email, password string, username, fullName *string) AuthResult
	SignIn(ctx context.Context, email, password string) AuthResult
	SignOut(ctx context.Context, accessToken string) bool
	RefreshToken(ctx context.Context, refreshToken string) AuthResult
	VerifyToken(ctx context.Context, accessToken string) AuthResult
	ResetPasswordRequest(ctx context.Context, email string) AuthResult
	ResetPasswordConfirm(ctx context.Context, token, newPassword string) AuthResult
}

// ---------------------------------------------------------------------------
// Supabase adapter
// ---------------------------------------------------------------------------

// SupabaseAuthProvider is the subset of infrastructure.SupabaseAuthService used by
// the adapter. The Python adapter instantiates the concrete service; this declares
// the exact methods it calls.
type SupabaseAuthProvider interface {
	SignUp(ctx context.Context, email, password string, metadata *tmentities.OrderedMap[any]) infrastructure.SupabaseAuthResult
	SignIn(ctx context.Context, email, password string) infrastructure.SupabaseAuthResult
	SignOut(ctx context.Context, accessToken string) bool
	RefreshSession(ctx context.Context, refreshToken string) infrastructure.SupabaseAuthResult
	VerifyToken(ctx context.Context, accessToken string) infrastructure.SupabaseAuthResult
	ResetPasswordRequest(ctx context.Context, email string) infrastructure.SupabaseAuthResult
	UpdatePassword(ctx context.Context, accessToken, newPassword string) infrastructure.SupabaseAuthResult
}

// SupabaseAuthAdapter adapts a Supabase auth service to AuthServiceInterface.
type SupabaseAuthAdapter struct {
	Service SupabaseAuthProvider
}

// NewSupabaseAuthAdapter mirrors SupabaseAuthAdapter.__init__.
func NewSupabaseAuthAdapter(service SupabaseAuthProvider) *SupabaseAuthAdapter {
	return &SupabaseAuthAdapter{Service: service}
}

func (a *SupabaseAuthAdapter) SignUp(ctx context.Context, email, password string, username, fullName *string) AuthResult {
	metadata := tmentities.NewOrderedMap[any]()
	if username != nil {
		metadata.Set("username", *username)
	}
	if fullName != nil {
		metadata.Set("full_name", *fullName)
	}
	result := a.Service.SignUp(ctx, email, password, metadata)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	r.User = supabaseFormatUser(result.User)
	r.AccessToken = supabaseSessionField(result.Session, "access_token")
	r.RefreshToken = supabaseSessionField(result.Session, "refresh_token")
	r.RequiresEmailVerification = result.RequiresEmailVerification
	return r
}

func (a *SupabaseAuthAdapter) SignIn(ctx context.Context, email, password string) AuthResult {
	result := a.Service.SignIn(ctx, email, password)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	r.User = supabaseFormatUser(result.User)
	r.AccessToken = supabaseSessionField(result.Session, "access_token")
	r.RefreshToken = supabaseSessionField(result.Session, "refresh_token")
	r.RequiresEmailVerification = result.RequiresEmailVerification
	return r
}

func (a *SupabaseAuthAdapter) SignOut(ctx context.Context, accessToken string) bool {
	return a.Service.SignOut(ctx, accessToken)
}

func (a *SupabaseAuthAdapter) RefreshToken(ctx context.Context, refreshToken string) AuthResult {
	result := a.Service.RefreshSession(ctx, refreshToken)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	r.User = supabaseFormatUser(result.User)
	r.AccessToken = supabaseSessionField(result.Session, "access_token")
	r.RefreshToken = supabaseSessionField(result.Session, "refresh_token")
	return r
}

func (a *SupabaseAuthAdapter) VerifyToken(ctx context.Context, accessToken string) AuthResult {
	result := a.Service.VerifyToken(ctx, accessToken)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	r.User = supabaseFormatUser(result.User)
	r.AccessToken = &accessToken // Python returns the same token
	return r
}

func (a *SupabaseAuthAdapter) ResetPasswordRequest(ctx context.Context, email string) AuthResult {
	result := a.Service.ResetPasswordRequest(ctx, email)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	return r
}

func (a *SupabaseAuthAdapter) ResetPasswordConfirm(ctx context.Context, token, newPassword string) AuthResult {
	result := a.Service.UpdatePassword(ctx, token, newPassword)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	return r
}

// supabaseFormatUser is _format_user (Supabase). The returned dict always carries
// all seven keys in the Python literal's order; missing attributes are nil.
func supabaseFormatUser(user *tmentities.OrderedMap[any]) *tmentities.OrderedMap[any] {
	if user == nil {
		return nil
	}
	out := tmentities.NewOrderedMap[any]()
	out.Set("id", orderedGet(user, "id"))
	out.Set("email", orderedGet(user, "email"))
	var metadata *tmentities.OrderedMap[any]
	if raw, ok := user.Get("user_metadata"); ok {
		if m, ok := raw.(*tmentities.OrderedMap[any]); ok {
			metadata = m
		}
	}
	out.Set("username", orderedGet(metadata, "username"))
	out.Set("full_name", orderedGet(metadata, "full_name"))
	confirmed, ok := user.Get("confirmed_at")
	out.Set("email_verified", ok && confirmed != nil)
	created, ok := user.Get("created_at")
	if ok {
		out.Set("created_at", pyString(created))
	} else {
		out.Set("created_at", "")
	}
	out.Set("roles", []string{"user"})
	return out
}

func orderedGet(m *tmentities.OrderedMap[any], key string) any {
	if m == nil {
		return nil
	}
	v, _ := m.Get(key)
	return v
}

func supabaseSessionField(session *tmentities.OrderedMap[any], key string) *string {
	if session == nil {
		return nil
	}
	v, ok := session.Get(key)
	if !ok || v == nil {
		return nil
	}
	s, ok := v.(string)
	if !ok {
		return nil
	}
	return &s
}

// pyString approximates Python str() for the scalar values seen in Supabase payloads.
func pyString(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	if v == nil {
		return "None"
	}
	return tmvo.PyStr(v)
}

// ---------------------------------------------------------------------------
// Keycloak adapter
// ---------------------------------------------------------------------------

// KeycloakAuthAdapter adapts the Keycloak auth service to AuthServiceInterface.
type KeycloakAuthAdapter struct {
	Keycloak *authroot.KeycloakAuth
}

// NewKeycloakAuthAdapter mirrors KeycloakAuthAdapter.__init__: the Python constructor
// catches a failure to build the service and leaves keycloak=None.
func NewKeycloakAuthAdapter() *KeycloakAuthAdapter {
	service, err := authroot.NewKeycloakAuth()
	if err != nil {
		return &KeycloakAuthAdapter{Keycloak: nil}
	}
	return &KeycloakAuthAdapter{Keycloak: service}
}

func (a *KeycloakAuthAdapter) SignUp(ctx context.Context, email, password string, username, fullName *string) AuthResult {
	r := authResultDefault()
	r.Success = false
	msg := "Keycloak signup not implemented"
	r.ErrorMessage = &msg
	return r
}

func (a *KeycloakAuthAdapter) SignIn(ctx context.Context, email, password string) AuthResult {
	if a.Keycloak == nil {
		r := authResultDefault()
		r.Success = false
		msg := "Keycloak service not available"
		r.ErrorMessage = &msg
		return r
	}
	result := a.Keycloak.Login(ctx, email, password)
	if !result.Success {
		r := authResultDefault()
		r.Success = false
		msg := "Invalid credentials"
		if result.Error != nil {
			msg = *result.Error
		}
		r.ErrorMessage = &msg
		return r
	}
	var userData *tmentities.OrderedMap[any]
	if result.User != nil {
		userData = tmentities.NewOrderedMap[any]()
		id := orderedGet(result.User, "sub")
		if id == nil {
			if v := orderedGet(result.User, "id"); v != nil {
				id = v
			} else {
				id = email
			}
		}
		userEmail := orderedGet(result.User, "email")
		if userEmail == nil {
			userEmail = email
		}
		uname := orderedGet(result.User, "preferred_username")
		if uname == nil {
			uname = emailPrefix(email)
		}
		userData.Set("id", id)
		userData.Set("email", userEmail)
		userData.Set("username", uname)
		if len(result.Roles) > 0 {
			userData.Set("roles", result.Roles)
		} else {
			userData.Set("roles", []string{"user"})
		}
	}
	r := authResultDefault()
	r.Success = true
	r.User = userData
	r.AccessToken = result.AccessToken
	r.RefreshToken = result.RefreshToken
	return r
}

func (a *KeycloakAuthAdapter) SignOut(ctx context.Context, accessToken string) bool { return false }

func (a *KeycloakAuthAdapter) RefreshToken(ctx context.Context, refreshToken string) AuthResult {
	r := authResultDefault()
	r.Success = false
	msg := "Keycloak token refresh not implemented"
	r.ErrorMessage = &msg
	return r
}

func (a *KeycloakAuthAdapter) VerifyToken(ctx context.Context, accessToken string) AuthResult {
	r := authResultDefault()
	r.Success = false
	msg := "Keycloak token verification not implemented"
	r.ErrorMessage = &msg
	return r
}

func (a *KeycloakAuthAdapter) ResetPasswordRequest(ctx context.Context, email string) AuthResult {
	r := authResultDefault()
	r.Success = false
	msg := "Keycloak password reset not implemented"
	r.ErrorMessage = &msg
	return r
}

func (a *KeycloakAuthAdapter) ResetPasswordConfirm(ctx context.Context, token, newPassword string) AuthResult {
	r := authResultDefault()
	r.Success = false
	msg := "Keycloak password reset confirm not implemented"
	r.ErrorMessage = &msg
	return r
}

// ---------------------------------------------------------------------------
// Local adapter
// ---------------------------------------------------------------------------

// LocalAuthAdapter adapts the local JWT/AuthService stack to AuthServiceInterface.
// The Python _get_auth_service opens a DB session per call and closes it in a
// finally block; GetAuthService returns that (service, close) pair so the adapter
// keeps the same lifetime semantics without importing the database package.
type LocalAuthAdapter struct {
	JWTService     *domainservices.JWTService
	GetAuthService func(ctx context.Context) (*services.AuthService, func(), error)
}

// NewLocalAuthAdapter mirrors LocalAuthAdapter.__init__ with injected dependencies.
func NewLocalAuthAdapter(jwtService *domainservices.JWTService, getAuthService func(ctx context.Context) (*services.AuthService, func(), error)) *LocalAuthAdapter {
	return &LocalAuthAdapter{JWTService: jwtService, GetAuthService: getAuthService}
}

func (a *LocalAuthAdapter) open(ctx context.Context) (*services.AuthService, func(), error) {
	if a.GetAuthService == nil {
		return nil, nil, errLocalAuthUnavailable
	}
	return a.GetAuthService(ctx)
}

func (a *LocalAuthAdapter) SignUp(ctx context.Context, email, password string, username, fullName *string) AuthResult {
	svc, closeFn, err := a.open(ctx)
	if err != nil {
		return localFailure("Registration failed")
	}
	defer closeFn()
	name := emailPrefix(email)
	if username != nil {
		name = *username
	}
	result := svc.RegisterUser(ctx, email, name, password, fullName)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	r.User = localFormatUser(result.User)
	r.RequiresEmailVerification = true
	return r
}

func (a *LocalAuthAdapter) SignIn(ctx context.Context, email, password string) AuthResult {
	svc, closeFn, err := a.open(ctx)
	if err != nil {
		return localFailure("Sign in failed")
	}
	defer closeFn()
	result := svc.Login(ctx, email, password, nil)
	r := authResultDefault()
	r.Success = result.Success
	r.ErrorMessage = result.ErrorMessage
	r.User = localFormatUser(result.User)
	r.AccessToken = result.AccessToken
	r.RefreshToken = result.RefreshToken
	r.RequiresEmailVerification = result.RequiresEmailVerification
	r.ExpiresIn = 900
	return r
}

func (a *LocalAuthAdapter) SignOut(ctx context.Context, accessToken string) bool {
	svc, closeFn, err := a.open(ctx)
	if err != nil {
		return false
	}
	defer closeFn()
	payload := a.JWTService.VerifyAccessToken(accessToken, "")
	if userID, ok := payload["sub"].(string); ok && userID != "" {
		return svc.Logout(ctx, userID, true)
	}
	return false
}

func (a *LocalAuthAdapter) RefreshToken(ctx context.Context, refreshToken string) AuthResult {
	svc, closeFn, err := a.open(ctx)
	if err != nil {
		return localFailure("Token refresh failed")
	}
	defer closeFn()
	accessToken, newRefreshToken, ok := svc.RefreshTokens(ctx, refreshToken)
	if ok {
		r := authResultDefault()
		r.Success = true
		r.AccessToken = &accessToken
		r.RefreshToken = &newRefreshToken
		r.ExpiresIn = 900
		return r
	}
	return localFailure("Token refresh failed")
}

func (a *LocalAuthAdapter) VerifyToken(ctx context.Context, accessToken string) AuthResult {
	payload := a.JWTService.VerifyAccessToken(accessToken, "")
	if len(payload) > 0 {
		user := tmentities.NewOrderedMap[any]()
		user.Set("id", payload["sub"])
		user.Set("email", payload["email"])
		user.Set("username", payload["username"])
		if roles, ok := payload["roles"]; ok {
			user.Set("roles", roles)
		} else {
			user.Set("roles", []string{"user"})
		}
		r := authResultDefault()
		r.Success = true
		r.User = user
		r.AccessToken = &accessToken
		return r
	}
	return localFailure("Invalid token")
}

func (a *LocalAuthAdapter) ResetPasswordRequest(ctx context.Context, email string) AuthResult {
	svc, closeFn, err := a.open(ctx)
	if err != nil {
		return localFailure("Password reset request failed")
	}
	defer closeFn()
	success, _, errorMessage := svc.RequestPasswordReset(ctx, email)
	r := authResultDefault()
	r.Success = success
	r.ErrorMessage = errorMessage
	return r
}

func (a *LocalAuthAdapter) ResetPasswordConfirm(ctx context.Context, token, newPassword string) AuthResult {
	svc, closeFn, err := a.open(ctx)
	if err != nil {
		return localFailure("Password reset failed")
	}
	defer closeFn()
	success, errorMessage := svc.ResetPassword(ctx, token, newPassword)
	r := authResultDefault()
	r.Success = success
	r.ErrorMessage = errorMessage
	return r
}

// localFormatUser is _format_user for the local User entity. Key order mirrors the
// Python dict literal: id, email, username, full_name, provider, email_verified,
// status, roles.
func localFormatUser(user *authentities.User) *tmentities.OrderedMap[any] {
	if user == nil {
		return nil
	}
	out := tmentities.NewOrderedMap[any]()
	out.Set("id", user.ID)
	out.Set("email", user.Email)
	out.Set("username", user.Username)
	out.Set("full_name", user.FullName)
	out.Set("provider", "local")
	out.Set("email_verified", user.EmailVerified)
	out.Set("status", string(user.Status))
	if len(user.Roles) > 0 {
		roles := make([]string, 0, len(user.Roles))
		for _, role := range user.Roles {
			roles = append(roles, string(role))
		}
		out.Set("roles", roles)
	} else {
		out.Set("roles", []string{"user"})
	}
	return out
}

func localFailure(message string) AuthResult {
	r := authResultDefault()
	r.Success = false
	r.ErrorMessage = &message
	return r
}

// errLocalAuthUnavailable stands in for the Python exception when the local service
// cannot be built (it is caught by the caller and turned into a failure AuthResult).
var errLocalAuthUnavailable = &localAuthError{}

type localAuthError struct{}

func (*localAuthError) Error() string { return "local auth service unavailable" }

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

// AuthFactory creates (and caches) one auth service per provider.
type AuthFactory struct {
	instances     map[AuthProvider]AuthServiceInterface
	BuildSupabase func() AuthServiceInterface
	BuildKeycloak func() AuthServiceInterface
	BuildLocal    func() AuthServiceInterface
}

// NewAuthFactory builds a factory with the per-provider constructors injected.
func NewAuthFactory(buildSupabase, buildKeycloak, buildLocal func() AuthServiceInterface) *AuthFactory {
	return &AuthFactory{
		instances:     map[AuthProvider]AuthServiceInterface{},
		BuildSupabase: buildSupabase,
		BuildKeycloak: buildKeycloak,
		BuildLocal:    buildLocal,
	}
}

// CreateAuthService mirrors AuthFactory.create_auth_service. A nil provider falls
// back to AUTH_PROVIDER (lowercased) and an unknown value falls back to local.
func (f *AuthFactory) CreateAuthService(provider *AuthProvider) AuthServiceInterface {
	if provider == nil {
		selected := authFactoryCurrentAuthProvider()
		provider = &selected
	}
	if _, ok := f.instances[*provider]; !ok {
		switch *provider {
		case AuthProviderSupabase:
			f.instances[*provider] = f.build(f.BuildSupabase)
		case AuthProviderKeycloak:
			f.instances[*provider] = f.build(f.BuildKeycloak)
		default:
			f.instances[*provider] = f.build(f.BuildLocal)
		}
	}
	return f.instances[*provider]
}

func (f *AuthFactory) build(fn func() AuthServiceInterface) AuthServiceInterface {
	if fn == nil {
		return nil
	}
	return fn()
}

// GetCurrentProvider mirrors AuthFactory.get_current_provider.
func (f *AuthFactory) GetCurrentProvider() AuthProvider {
	return authFactoryCurrentAuthProvider()
}

// IsProviderAvailable mirrors AuthFactory.is_provider_available.
func (f *AuthFactory) IsProviderAvailable(provider AuthProvider) bool {
	switch provider {
	case AuthProviderSupabase:
		return os.Getenv("SUPABASE_URL") != "" && os.Getenv("SUPABASE_ANON_KEY") != ""
	case AuthProviderKeycloak:
		return os.Getenv("KEYCLOAK_URL") != "" && os.Getenv("KEYCLOAK_CLIENT_ID") != "" && os.Getenv("KEYCLOAK_CLIENT_SECRET") != ""
	default:
		return os.Getenv("JWT_SECRET_KEY") != ""
	}
}

func authFactoryCurrentAuthProvider() AuthProvider {
	value := strings.ToLower(authFactoryEnvOr("AUTH_PROVIDER", "local"))
	switch AuthProvider(value) {
	case AuthProviderSupabase:
		return AuthProviderSupabase
	case AuthProviderKeycloak:
		return AuthProviderKeycloak
	default:
		return AuthProviderLocal
	}
}

// authFactoryEnvOr is os.getenv(key) or default (Python treats an empty string as
// unset for the .lower() path, matching os.getenv which returns "" only if set).
func authFactoryEnvOr(key, def string) string {
	if v, ok := os.LookupEnv(key); ok {
		return v
	}
	return def
}

// emailPrefix is email.split("@")[0].
func emailPrefix(email string) string {
	if idx := strings.Index(email, "@"); idx >= 0 {
		return email[:idx]
	}
	return email
}
