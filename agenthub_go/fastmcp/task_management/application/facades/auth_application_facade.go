package facades

import (
	"context"
	"os"
	"strings"

	authservice "agenthub/fastmcp/auth/application/services"
	authentities "agenthub/fastmcp/auth/domain/entities"
	authjwt "agenthub/fastmcp/auth/domain/services"
	authinfra "agenthub/fastmcp/auth/infrastructure/repositories"
	tmdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// AuthApplicationFacade ports auth_application_facade.AuthApplicationFacade.
//
// Python constructs JWTService(secret_key=...) directly; the Go JWT service
// requires an issuer, so authjwt.DefaultIssuer is used (the Python JWTService
// default). The Supabase branch of dual_authenticate depends on
// get_supabase_client()/find_or_create_from_supabase() (auth/infrastructure
// supabase_client, owned by the server team and not yet ported), so it is
// reached through the SupabaseAuthenticator interface: when SUPABASE_ENABLED is
// "true" and Supabase is set, it is tried first; otherwise local JWT is used.
type AuthApplicationFacade struct {
	JWTService  *authjwt.JWTService
	AuthService *authservice.AuthService
	// Supabase is get_supabase_client() + auth.get_user + find_or_create_from_supabase
	// in one call; nil = get_supabase_client() returned None.
	Supabase SupabaseAuthenticator
}

// SupabaseAuthenticator verifies a Supabase token and returns the matching local
// user (found or created), or nil when the token is not a valid Supabase token.
type SupabaseAuthenticator interface {
	AuthenticateToken(ctx context.Context, token string) (*authentities.User, error)
}

// NewAuthApplicationFacade mirrors __init__(session): it reads JWT_SECRET_KEY
// (default "default-secret-key-change-in-production"), builds the user
// repository from the session and wires the auth service.
func NewAuthApplicationFacade(session *tmdb.SessionManager) (*AuthApplicationFacade, error) {
	jwtSecret := os.Getenv("JWT_SECRET_KEY")
	if jwtSecret == "" {
		jwtSecret = "default-secret-key-change-in-production"
	}
	jwtService, err := authjwt.NewJWTService(jwtSecret, authjwt.DefaultIssuer)
	if err != nil {
		return nil, err
	}
	userRepository, err := authinfra.NewUserRepository(session)
	if err != nil {
		return nil, err
	}
	authService := authservice.NewAuthService(userRepository, jwtService)
	return &AuthApplicationFacade{JWTService: jwtService, AuthService: authService}, nil
}

// VerifyJWTToken ports verify_jwt_token: it tries an api_token, then an access
// token, and returns the user or nil. All errors yield nil (Python swallows them).
func (f *AuthApplicationFacade) VerifyJWTToken(ctx context.Context, token string) (user *authentities.User) {
	defer func() {
		if recover() != nil { // Python: except Exception -> None
			user = nil
		}
	}()
	payload := f.JWTService.VerifyToken(token, "api_token", "")
	if payload == nil {
		payload = f.JWTService.VerifyToken(token, "access", "")
	}
	if payload != nil {
		if userID, ok := payload["user_id"]; ok {
			if id, ok := userID.(string); ok && id != "" {
				user, err := f.AuthService.UserRepository.GetByID(ctx, id)
				if err == nil && user != nil {
					return user
				}
			}
		}
	}
	return nil
}

// DualAuthenticate ports dual_authenticate: Supabase first when enabled (errors
// are swallowed), then local JWT.
func (f *AuthApplicationFacade) DualAuthenticate(ctx context.Context, token string) *authentities.User {
	if token == "" {
		return nil
	}
	if strings.ToLower(os.Getenv("SUPABASE_ENABLED")) == "true" && f.Supabase != nil {
		if user := f.supabaseUser(ctx, token); user != nil {
			return user
		}
	}
	return f.VerifyJWTToken(ctx, token)
}

// ExtractTokenFromHeaders ports extract_token_from_headers.
func (f *AuthApplicationFacade) ExtractTokenFromHeaders(headers map[string]string) *string {
	authHeader := headers["authorization"]
	if authHeader != "" && strings.HasPrefix(authHeader, "Bearer ") {
		token := strings.Replace(authHeader, "Bearer ", "", 1)
		return &token
	}
	if apiToken := headers["x-api-token"]; apiToken != "" {
		return &apiToken
	}
	return nil
}

// ExtractTokenFromCookies ports extract_token_from_cookies.
func (f *AuthApplicationFacade) ExtractTokenFromCookies(cookies map[string]string) *string {
	token, ok := cookies["access_token"]
	if !ok {
		return nil
	}
	return &token
}

func (f *AuthApplicationFacade) supabaseUser(ctx context.Context, token string) (user *authentities.User) {
	defer func() {
		if recover() != nil {
			user = nil
		}
	}()
	user, err := f.Supabase.AuthenticateToken(ctx, token)
	if err != nil {
		return nil
	}
	return user
}
