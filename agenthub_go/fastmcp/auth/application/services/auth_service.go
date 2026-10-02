// Authentication application service, ported from
// agenthub_main/src/fastmcp/auth/application/services/auth_service.py.
package services

import (
	"context"
	"fmt"
	"strings"

	authEntities "agenthub/fastmcp/auth/domain/entities"
	domainservices "agenthub/fastmcp/auth/domain/services"
	authValueObjects "agenthub/fastmcp/auth/domain/value_objects"
	tmvalueobjects "agenthub/fastmcp/task_management/domain/value_objects"
)

// LoginResult is the result of a login attempt (Python dataclass LoginResult).
type LoginResult struct {
	Success                   bool
	User                      *authEntities.User
	AccessToken               *string
	RefreshToken              *string
	ErrorMessage              *string
	RequiresEmailVerification bool
}

// RegistrationResult is the result of a registration attempt (Python RegistrationResult).
type RegistrationResult struct {
	Success           bool
	User              *authEntities.User
	VerificationToken *string
	ErrorMessage      *string
}

// AuthUserRepository is the subset of the user repository used by AuthService. The
// Python service receives an untyped repository; this declares the four methods it calls.
type AuthUserRepository interface {
	GetByEmail(ctx context.Context, email string) (*authEntities.User, error)
	GetByUsername(ctx context.Context, username string) (*authEntities.User, error)
	GetByID(ctx context.Context, userID string) (*authEntities.User, error)
	Save(ctx context.Context, user *authEntities.User) (*authEntities.User, error)
}

// AuthService orchestrates registration, login, password and token operations.
type AuthService struct {
	UserRepository AuthUserRepository
	JWTService     *domainservices.JWTService
}

// NewAuthService mirrors AuthService.__init__ (password_service optional in Python; Go
// uses the package-level password functions).
func NewAuthService(userRepository AuthUserRepository, jwtService *domainservices.JWTService) *AuthService {
	return &AuthService{UserRepository: userRepository, JWTService: jwtService}
}

func authServiceUserID(u *authEntities.User) string {
	if u.ID != nil {
		return *u.ID
	}
	return ""
}

func authServiceRoles(roles []authEntities.UserRole) []string {
	out := make([]string, 0, len(roles))
	for _, r := range roles {
		out = append(out, string(r))
	}
	return out
}

// RegisterUser is register_user.
func (s *AuthService) RegisterUser(ctx context.Context, email, username, password string, fullName *string) RegistrationResult {
	if _, err := authValueObjects.NewEmail(email); err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	existing, err := s.UserRepository.GetByEmail(ctx, email)
	if err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}
	if existing != nil {
		msg := "Email already registered"
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	existing, err = s.UserRepository.GetByUsername(ctx, username)
	if err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}
	if existing != nil {
		msg := "Username already taken"
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	strength := domainservices.CheckPasswordStrength(password)
	if strength.Strength == "weak" {
		msg := fmt.Sprintf("Password too weak. %s", strings.Join(strength.Suggestions, ", "))
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	passwordHash, err := domainservices.HashPassword(password)
	if err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	userID := authValueObjects.GenerateUserId().Value
	user, err := authEntities.NewUser(authEntities.User{
		ID:            &userID,
		Email:         email,
		Username:      username,
		PasswordHash:  passwordHash,
		FullName:      fullName,
		Status:        authEntities.UserStatusPendingVerification,
		EmailVerified: false,
	})
	if err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	saved, err := s.UserRepository.Save(ctx, user)
	if err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	verificationToken, err := s.JWTService.CreateResetToken(authServiceUserID(saved), saved.Email)
	if err != nil {
		msg := fmt.Sprintf("Registration failed: %s", err.Error())
		return RegistrationResult{Success: false, ErrorMessage: &msg}
	}

	return RegistrationResult{Success: true, User: saved, VerificationToken: &verificationToken}
}

// Login is login. ip_address is accepted for signature fidelity (unused by Python too).
func (s *AuthService) Login(ctx context.Context, emailOrUsername, password string, ipAddress *string) LoginResult {
	var user *authEntities.User
	var err error
	if strings.Contains(emailOrUsername, "@") {
		user, err = s.UserRepository.GetByEmail(ctx, emailOrUsername)
	} else {
		user, err = s.UserRepository.GetByUsername(ctx, emailOrUsername)
	}
	if err != nil {
		msg := "Login failed"
		return LoginResult{Success: false, ErrorMessage: &msg}
	}
	if user == nil {
		msg := "Invalid credentials"
		return LoginResult{Success: false, ErrorMessage: &msg}
	}

	if !user.CanLogin() {
		switch {
		case user.IsLocked():
			msg := "Account temporarily locked due to failed login attempts"
			return LoginResult{Success: false, ErrorMessage: &msg}
		case user.Status == authEntities.UserStatusSuspended:
			msg := "Account suspended"
			return LoginResult{Success: false, ErrorMessage: &msg}
		default:
			msg := "Account not active"
			return LoginResult{Success: false, ErrorMessage: &msg}
		}
	}

	if !domainservices.VerifyPassword(password, user.PasswordHash) {
		_ = user.RecordFailedLogin()
		_, _ = s.UserRepository.Save(ctx, user)
		msg := "Invalid credentials"
		return LoginResult{Success: false, ErrorMessage: &msg}
	}

	if !user.EmailVerified {
		msg := "Email verification required"
		return LoginResult{Success: false, RequiresEmailVerification: true, ErrorMessage: &msg}
	}

	if domainservices.NeedsRehash(user.PasswordHash) {
		if hash, herr := domainservices.HashPassword(password); herr == nil {
			user.PasswordHash = hash
		}
	}

	_ = user.RecordSuccessfulLogin()

	accessToken, err := s.JWTService.CreateAccessToken(authServiceUserID(user), user.Email, authServiceRoles(user.Roles), nil, domainservices.DefaultAudience)
	if err != nil {
		msg := "Login failed"
		return LoginResult{Success: false, ErrorMessage: &msg}
	}

	refreshToken, tokenFamily, err := s.JWTService.CreateRefreshToken(authServiceUserID(user), authServiceTokenFamily(user), user.RefreshTokenVersion)
	if err != nil {
		msg := "Login failed"
		return LoginResult{Success: false, ErrorMessage: &msg}
	}

	user.RefreshTokenFamily = &tokenFamily
	if _, err := s.UserRepository.Save(ctx, user); err != nil {
		msg := "Login failed"
		return LoginResult{Success: false, ErrorMessage: &msg}
	}

	return LoginResult{Success: true, User: user, AccessToken: &accessToken, RefreshToken: &refreshToken}
}

// authServiceTokenFamily mirrors Python passing user.refresh_token_family (which may be
// None; CreateRefreshToken accepts None and generates a new family).
func authServiceTokenFamily(u *authEntities.User) string {
	if u.RefreshTokenFamily != nil {
		return *u.RefreshTokenFamily
	}
	return ""
}

// VerifyEmail is verify_email: (success, error_message).
func (s *AuthService) VerifyEmail(ctx context.Context, token string) (bool, *string) {
	payload := s.JWTService.VerifyResetToken(token)
	if payload == nil {
		msg := "Invalid or expired verification token"
		return false, &msg
	}
	userID, _ := payload["sub"].(string)
	user, err := s.UserRepository.GetByID(ctx, userID)
	if err != nil {
		msg := "Email verification failed"
		return false, &msg
	}
	if user == nil {
		msg := "User not found"
		return false, &msg
	}
	if err := user.VerifyEmail(); err != nil {
		msg := "Email verification failed"
		return false, &msg
	}
	if _, err := s.UserRepository.Save(ctx, user); err != nil {
		msg := "Email verification failed"
		return false, &msg
	}
	return true, nil
}

// RequestPasswordReset is request_password_reset: (success, reset_token, error_message).
func (s *AuthService) RequestPasswordReset(ctx context.Context, email string) (bool, *string, *string) {
	user, err := s.UserRepository.GetByEmail(ctx, email)
	if err != nil {
		msg := "Password reset request failed"
		return false, nil, &msg
	}
	if user == nil {
		return true, nil, nil
	}

	resetToken, err := domainservices.GenerateResetToken(32)
	if err != nil {
		msg := "Password reset request failed"
		return false, nil, &msg
	}
	jwtToken, err := s.JWTService.CreateResetToken(authServiceUserID(user), user.Email)
	if err != nil {
		msg := "Password reset request failed"
		return false, nil, &msg
	}
	if err := user.InitiatePasswordReset(resetToken, 24); err != nil {
		msg := "Password reset request failed"
		return false, nil, &msg
	}
	if _, err := s.UserRepository.Save(ctx, user); err != nil {
		msg := "Password reset request failed"
		return false, nil, &msg
	}
	return true, &jwtToken, nil
}

// ResetPassword is reset_password: (success, error_message).
func (s *AuthService) ResetPassword(ctx context.Context, token, newPassword string) (bool, *string) {
	payload := s.JWTService.VerifyResetToken(token)
	if payload == nil {
		msg := "Invalid or expired reset token"
		return false, &msg
	}
	userID, _ := payload["sub"].(string)
	user, err := s.UserRepository.GetByID(ctx, userID)
	if err != nil {
		msg := "Password reset failed"
		return false, &msg
	}
	if user == nil {
		msg := "User not found"
		return false, &msg
	}

	strength := domainservices.CheckPasswordStrength(newPassword)
	if strength.Strength == "weak" {
		msg := fmt.Sprintf("Password too weak. %s", strings.Join(strength.Suggestions, ", "))
		return false, &msg
	}

	passwordHash, err := domainservices.HashPassword(newPassword)
	if err != nil {
		msg := "Password reset failed"
		return false, &msg
	}
	if err := user.CompletePasswordReset(passwordHash); err != nil {
		msg := "Password reset failed"
		return false, &msg
	}
	if _, err := s.UserRepository.Save(ctx, user); err != nil {
		msg := "Password reset failed"
		return false, &msg
	}
	return true, nil
}

// RefreshTokens is refresh_tokens: (access, refresh, ok).
func (s *AuthService) RefreshTokens(ctx context.Context, refreshToken string) (string, string, bool) {
	payload := s.JWTService.VerifyRefreshToken(refreshToken)
	if payload == nil {
		return "", "", false
	}
	userID, _ := payload["sub"].(string)
	user, err := s.UserRepository.GetByID(ctx, userID)
	if err != nil || user == nil {
		return "", "", false
	}

	tokenFamily, _ := payload["family"].(string)
	// Python payload.get("version", 0): absent -> 0.
	tokenVersion, _ := tmvalueobjects.PyFloat(payload["version"])

	if user.RefreshTokenFamily == nil || *user.RefreshTokenFamily != tokenFamily || float64(user.RefreshTokenVersion) > tokenVersion {
		return "", "", false
	}

	accessToken, err := s.JWTService.CreateAccessToken(authServiceUserID(user), user.Email, authServiceRoles(user.Roles), nil, domainservices.DefaultAudience)
	if err != nil {
		return "", "", false
	}
	newRefreshToken, _, err := s.JWTService.CreateRefreshToken(authServiceUserID(user), tokenFamily, user.RefreshTokenVersion+1)
	if err != nil {
		return "", "", false
	}

	user.RefreshTokenVersion++
	if _, err := s.UserRepository.Save(ctx, user); err != nil {
		return "", "", false
	}
	return accessToken, newRefreshToken, true
}

// Logout is logout.
func (s *AuthService) Logout(ctx context.Context, userID string, revokeAllTokens bool) bool {
	user, err := s.UserRepository.GetByID(ctx, userID)
	if err != nil || user == nil {
		return false
	}
	if revokeAllTokens {
		user.RefreshTokenVersion++
		if _, err := s.UserRepository.Save(ctx, user); err != nil {
			return false
		}
	}
	return true
}

// GetCurrentUser is get_current_user.
func (s *AuthService) GetCurrentUser(ctx context.Context, accessToken string) *authEntities.User {
	payload := s.JWTService.VerifyAccessToken(accessToken, "")
	if payload == nil {
		return nil
	}
	userID, _ := payload["sub"].(string)
	user, err := s.UserRepository.GetByID(ctx, userID)
	if err != nil {
		return nil
	}
	return user
}
