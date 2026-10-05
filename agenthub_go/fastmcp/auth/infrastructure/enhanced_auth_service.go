// Enhanced Authentication Service with Email Integration
// (Python auth/infrastructure/enhanced_auth_service.py).
//
// The Go constructor takes the collaborators explicitly; the global getter keeps the
// Python lazy-singleton shape but needs the arguments. The email service and Supabase
// service are behind the two minimal interfaces below so the service can be exercised
// without SMTP/HTTP.

package infrastructure

import (
	"context"
	"fmt"
	"time"

	"agenthub/fastmcp/auth/infrastructure/repositories"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// EmailServiceInterface is the subset of SMTPEmailService used here.
type EmailServiceInterface interface {
	SendVerificationEmail(ctx context.Context, email string, userName *string, verificationURL *string) EmailResult
	SendPasswordResetEmail(ctx context.Context, email string, userName *string, resetURL *string) EmailResult
	SendPasswordChangedEmail(ctx context.Context, email string, userName, ipAddress, userAgent *string) EmailResult
	SendWelcomeEmail(ctx context.Context, email string, userName *string, dashboardURL *string) EmailResult
	TestConnection(ctx context.Context) EmailResult
}

// SupabaseAuthInterface is the subset of SupabaseAuthService used here.
type SupabaseAuthInterface interface {
	SignUp(ctx context.Context, email, password string, metadata *entities.OrderedMap[any]) SupabaseAuthResult
	ResetPasswordRequest(ctx context.Context, email string) SupabaseAuthResult
}

// EmailTokenRepository is the repository protocol used here; it is satisfied by
// *repositories.EmailTokenRepository.
type EmailTokenRepository interface {
	SaveToken(ctx context.Context, token *repositories.EmailToken) (bool, error)
	ValidateToken(ctx context.Context, token, email, tokenType string, markUsed bool) (*repositories.EmailToken, error)
	CleanupExpiredTokens(ctx context.Context, olderThanDays int) (int, error)
	GetTokenStats(ctx context.Context) (*entities.OrderedMap[any], error)
}

// EnhancedAuthResult is the EnhancedAuthResult dataclass.
type EnhancedAuthResult struct {
	Success                   bool
	User                      *entities.OrderedMap[any]
	Session                   *entities.OrderedMap[any]
	ErrorMessage              *string
	RequiresEmailVerification bool
	EmailSent                 bool
	EmailError                *string
	TokenData                 *entities.OrderedMap[any]
}

// EnhancedAuthService is the enhanced authentication service.
type EnhancedAuthService struct {
	supabase        SupabaseAuthInterface
	emailService    EmailServiceInterface
	tokenRepository EmailTokenRepository
}

// NewEnhancedAuthService is __init__; nil supabase / email collaborators fall back to
// the package singletons, and a token repository is required by the Go port.
func NewEnhancedAuthService(supabaseService SupabaseAuthInterface, emailService EmailServiceInterface, tokenRepository EmailTokenRepository) (*EnhancedAuthService, error) {
	if supabaseService == nil {
		s, err := NewSupabaseAuthService()
		if err != nil {
			return nil, err
		}
		supabaseService = s
	}
	if emailService == nil {
		e, err := GetEmailService()
		if err != nil {
			return nil, err
		}
		emailService = e
	}
	if tokenRepository == nil {
		return nil, value_objects.ValueErrorf("email token repository is required")
	}
	return &EnhancedAuthService{
		supabase:        supabaseService,
		emailService:    emailService,
		tokenRepository: tokenRepository,
	}, nil
}

var enhancedAuthServiceInstance *EnhancedAuthService

// GetEnhancedAuthService is get_enhanced_auth_service (the global instance).
func GetEnhancedAuthService(supabaseService SupabaseAuthInterface, emailService EmailServiceInterface, tokenRepository EmailTokenRepository) (*EnhancedAuthService, error) {
	if enhancedAuthServiceInstance == nil {
		s, err := NewEnhancedAuthService(supabaseService, emailService, tokenRepository)
		if err != nil {
			return nil, err
		}
		enhancedAuthServiceInstance = s
	}
	return enhancedAuthServiceInstance, nil
}

// metadataUserName is `metadata.get("username") or metadata.get("full_name")`.
func metadataUserName(metadata *entities.OrderedMap[any]) *string {
	if metadata == nil {
		return nil
	}
	for _, key := range []string{"username", "full_name"} {
		if v, ok := metadata.Get(key); ok && value_objects.PyTruthy(v) {
			if s, ok := v.(string); ok {
				return &s
			}
		}
	}
	return nil
}

// supabaseUserID is `supabase_result.user.get("id")`.
func supabaseUserID(user *entities.OrderedMap[any]) *string {
	if user == nil {
		return nil
	}
	if v, ok := user.Get("id"); ok && v != nil {
		if s, ok := v.(string); ok {
			return &s
		}
	}
	return nil
}

// verificationToken creates the EmailToken for a generated token dict.
func verificationToken(tokenData *entities.OrderedMap[any], email, tokenType string, metadata *entities.OrderedMap[any]) *repositories.EmailToken {
	tokenValue, _ := tokenData.Get("token")
	hash, _ := tokenData.Get("hash")
	expiresAt, _ := tokenData.Get("expires_at")
	createdAt, _ := tokenData.Get("created_at")
	token := &repositories.EmailToken{
		Token:     fmt.Sprint(tokenValue),
		Email:     email,
		TokenType: tokenType,
		TokenHash: fmt.Sprint(hash),
		Metadata:  metadata,
	}
	if t, ok := expiresAt.(time.Time); ok {
		token.ExpiresAt = t
	}
	if t, ok := createdAt.(time.Time); ok {
		token.CreatedAt = t
	}
	return token
}

// RegisterUser is register_user.
func (s *EnhancedAuthService) RegisterUser(ctx context.Context, email, password string, metadata *entities.OrderedMap[any], sendCustomEmail bool) EnhancedAuthResult {
	supabaseResult := s.supabase.SignUp(ctx, email, password, metadata)
	if !supabaseResult.Success {
		return EnhancedAuthResult{
			Success:      false,
			ErrorMessage: supabaseResult.ErrorMessage,
			User:         supabaseResult.User,
			Session:      supabaseResult.Session,
		}
	}

	emailSent := false
	var emailError *string
	var tokenData *entities.OrderedMap[any]

	if sendCustomEmail {
		tm := TokenManager{}
		tokenData = tm.GenerateVerificationToken(email, "verification")
		meta := entities.NewOrderedMap[any]()
		meta.Set("registration", true)
		if metadata != nil {
			meta.Set("user_metadata", metadata)
		} else {
			meta.Set("user_metadata", entities.NewOrderedMap[any]())
		}
		emailToken := verificationToken(tokenData, email, "verification", meta)
		emailToken.UserID = supabaseUserID(supabaseResult.User)
		_, _ = s.tokenRepository.SaveToken(ctx, emailToken)

		emailResult := s.emailService.SendVerificationEmail(ctx, email, metadataUserName(metadata), nil)
		emailSent = emailResult.Success
		if !emailResult.Success {
			emailError = emailResult.ErrorMessage
		}
	}

	var errorMessage *string
	if emailSent {
		errorMessage = stringPtr("Registration successful. Please check your email to verify your account.")
	} else {
		errorMessage = supabaseResult.ErrorMessage
	}
	return EnhancedAuthResult{
		Success:                   true,
		User:                      supabaseResult.User,
		Session:                   supabaseResult.Session,
		RequiresEmailVerification: supabaseResult.RequiresEmailVerification,
		EmailSent:                 emailSent,
		EmailError:                emailError,
		TokenData:                 tokenData,
		ErrorMessage:              errorMessage,
	}
}

// RequestPasswordReset is request_password_reset.
func (s *EnhancedAuthService) RequestPasswordReset(ctx context.Context, email string, sendCustomEmail bool) EnhancedAuthResult {
	_ = s.supabase.ResetPasswordRequest(ctx, email)

	emailSent := false
	var emailError *string
	var tokenData *entities.OrderedMap[any]

	if sendCustomEmail {
		tm := TokenManager{}
		tokenData = tm.GenerateVerificationToken(email, "password_reset")
		meta := entities.NewOrderedMap[any]()
		meta.Set("password_reset", true)
		emailToken := verificationToken(tokenData, email, "password_reset", meta)
		_, _ = s.tokenRepository.SaveToken(ctx, emailToken)

		emailResult := s.emailService.SendPasswordResetEmail(ctx, email, nil, nil)
		emailSent = emailResult.Success
		if !emailResult.Success {
			emailError = emailResult.ErrorMessage
		}
	}

	return EnhancedAuthResult{
		Success:      true,
		EmailSent:    emailSent,
		EmailError:   emailError,
		TokenData:    tokenData,
		ErrorMessage: stringPtr("Password reset email sent. Please check your inbox."),
	}
}

// VerifyEmailToken is verify_email_token.
func (s *EnhancedAuthService) VerifyEmailToken(ctx context.Context, token, email string) EnhancedAuthResult {
	emailToken, _ := s.tokenRepository.ValidateToken(ctx, token, email, "verification", true)
	if emailToken == nil {
		return EnhancedAuthResult{Success: false, ErrorMessage: stringPtr("Invalid or expired verification token")}
	}

	emailSent := false
	var emailError *string
	var userName *string
	if emailToken.Metadata != nil {
		if v, ok := emailToken.Metadata.Get("user_metadata"); ok {
			if userMetadata, ok := v.(*entities.OrderedMap[any]); ok {
				userName = metadataUserName(userMetadata)
			}
		}
	}
	emailResult := s.emailService.SendWelcomeEmail(ctx, email, userName, nil)
	emailSent = emailResult.Success
	if !emailResult.Success {
		emailError = emailResult.ErrorMessage
	}

	return EnhancedAuthResult{
		Success:      true,
		EmailSent:    emailSent,
		EmailError:   emailError,
		ErrorMessage: stringPtr("Email verified successfully! Welcome to Oracle Server."),
	}
}

// ResetPasswordWithToken is reset_password_with_token.
func (s *EnhancedAuthService) ResetPasswordWithToken(ctx context.Context, token, email, newPassword string, ipAddress, userAgent *string) EnhancedAuthResult {
	emailToken, _ := s.tokenRepository.ValidateToken(ctx, token, email, "password_reset", true)
	if emailToken == nil {
		return EnhancedAuthResult{Success: false, ErrorMessage: stringPtr("Invalid or expired reset token")}
	}

	emailSent := false
	var emailError *string
	emailResult := s.emailService.SendPasswordChangedEmail(ctx, email, nil, ipAddress, userAgent)
	emailSent = emailResult.Success
	if !emailResult.Success {
		emailError = emailResult.ErrorMessage
	}

	return EnhancedAuthResult{
		Success:      true,
		EmailSent:    emailSent,
		EmailError:   emailError,
		ErrorMessage: stringPtr("Password reset successfully. You can now log in with your new password."),
	}
}

// ResendVerificationEmail is resend_verification_email.
func (s *EnhancedAuthService) ResendVerificationEmail(ctx context.Context, email string) EnhancedAuthResult {
	tm := TokenManager{}
	tokenData := tm.GenerateVerificationToken(email, "verification")
	meta := entities.NewOrderedMap[any]()
	meta.Set("resend", true)
	emailToken := verificationToken(tokenData, email, "verification", meta)
	saved, _ := s.tokenRepository.SaveToken(ctx, emailToken)
	if !saved {
		return EnhancedAuthResult{Success: false, ErrorMessage: stringPtr("Failed to generate verification token")}
	}

	emailResult := s.emailService.SendVerificationEmail(ctx, email, nil, nil)
	if emailResult.Success {
		return EnhancedAuthResult{
			Success:      true,
			EmailSent:    true,
			TokenData:    tokenData,
			ErrorMessage: stringPtr("Verification email sent. Please check your inbox."),
		}
	}
	return EnhancedAuthResult{
		Success:      false,
		EmailSent:    false,
		EmailError:   emailResult.ErrorMessage,
		ErrorMessage: stringPtr("Failed to send verification email"),
	}
}

// CleanupExpiredTokens is cleanup_expired_tokens.
func (s *EnhancedAuthService) CleanupExpiredTokens(ctx context.Context, olderThanDays int) *entities.OrderedMap[any] {
	deletedCount, err := s.tokenRepository.CleanupExpiredTokens(ctx, olderThanDays)
	if err != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error_message", err.Error())
		return out
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("deleted_tokens", deletedCount)
	out.Set("message", fmt.Sprintf("Cleaned up %d expired tokens", deletedCount))
	return out
}

// GetEmailStats is get_email_stats.
func (s *EnhancedAuthService) GetEmailStats(ctx context.Context) *entities.OrderedMap[any] {
	stats, err := s.tokenRepository.GetTokenStats(ctx)
	if err != nil {
		out := entities.NewOrderedMap[any]()
		out.Set("success", false)
		out.Set("error_message", err.Error())
		return out
	}
	out := entities.NewOrderedMap[any]()
	out.Set("success", true)
	out.Set("stats", stats)
	return out
}

// TestEmailService is test_email_service.
func (s *EnhancedAuthService) TestEmailService(ctx context.Context) *entities.OrderedMap[any] {
	result := s.emailService.TestConnection(ctx)
	out := entities.NewOrderedMap[any]()
	out.Set("success", result.Success)
	out.Set("error_message", result.ErrorMessage)
	out.Set("message", "Email service connection test completed")
	return out
}
