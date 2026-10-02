package infrastructure

import (
	"context"
	"errors"
	"testing"

	"agenthub/fastmcp/auth/infrastructure/repositories"
	"agenthub/fastmcp/task_management/domain/entities"
)

type fakeSupabaseAuth struct {
	signUpResult SupabaseAuthResult
	resetResult  SupabaseAuthResult
	signUpCalls  int
}

func (f *fakeSupabaseAuth) SignUp(ctx context.Context, email, password string, metadata *entities.OrderedMap[any]) SupabaseAuthResult {
	f.signUpCalls++
	return f.signUpResult
}

func (f *fakeSupabaseAuth) ResetPasswordRequest(ctx context.Context, email string) SupabaseAuthResult {
	return f.resetResult
}

type fakeEmailService struct {
	verificationResult       EmailResult
	resetResult              EmailResult
	changedResult            EmailResult
	welcomeResult            EmailResult
	testResult               EmailResult
	lastVerificationUsername *string
	lastResetUsername        *string
}

func (f *fakeEmailService) SendVerificationEmail(ctx context.Context, email string, userName *string, verificationURL *string) EmailResult {
	f.lastVerificationUsername = userName
	return f.verificationResult
}

func (f *fakeEmailService) SendPasswordResetEmail(ctx context.Context, email string, userName *string, resetURL *string) EmailResult {
	f.lastResetUsername = userName
	return f.resetResult
}

func (f *fakeEmailService) SendPasswordChangedEmail(ctx context.Context, email string, userName, ipAddress, userAgent *string) EmailResult {
	return f.changedResult
}

func (f *fakeEmailService) SendWelcomeEmail(ctx context.Context, email string, userName *string, dashboardURL *string) EmailResult {
	return f.welcomeResult
}

func (f *fakeEmailService) TestConnection(ctx context.Context) EmailResult {
	return f.testResult
}

type fakeEmailTokenRepository struct {
	saved          []*repositories.EmailToken
	saveResult     bool
	saveErr        error
	validateResult *repositories.EmailToken
	validateErr    error
	cleanupCount   int
	cleanupErr     error
	stats          *entities.OrderedMap[any]
	statsErr       error
}

func (f *fakeEmailTokenRepository) SaveToken(ctx context.Context, token *repositories.EmailToken) (bool, error) {
	f.saved = append(f.saved, token)
	return f.saveResult, f.saveErr
}

func (f *fakeEmailTokenRepository) ValidateToken(ctx context.Context, token, email, tokenType string, markUsed bool) (*repositories.EmailToken, error) {
	return f.validateResult, f.validateErr
}

func (f *fakeEmailTokenRepository) CleanupExpiredTokens(ctx context.Context, olderThanDays int) (int, error) {
	return f.cleanupCount, f.cleanupErr
}

func (f *fakeEmailTokenRepository) GetTokenStats(ctx context.Context) (*entities.OrderedMap[any], error) {
	return f.stats, f.statsErr
}

func newEnhancedService(supabase SupabaseAuthInterface, email EmailServiceInterface, repo EmailTokenRepository) *EnhancedAuthService {
	return &EnhancedAuthService{supabase: supabase, emailService: email, tokenRepository: repo}
}

func TestEnhancedRegisterUserSuccess(t *testing.T) {
	user := entities.NewOrderedMap[any]()
	user.Set("id", "u1")
	supabase := &fakeSupabaseAuth{signUpResult: SupabaseAuthResult{
		Success:                   true,
		User:                      user,
		RequiresEmailVerification: true,
	}}
	email := &fakeEmailService{verificationResult: EmailResult{Success: true}}
	repo := &fakeEmailTokenRepository{saveResult: true}
	svc := newEnhancedService(supabase, email, repo)

	metadata := entities.NewOrderedMap[any]()
	metadata.Set("username", "alice")
	result := svc.RegisterUser(context.Background(), "a@b.com", "pw", metadata, true)

	if !result.Success || !result.EmailSent || !result.RequiresEmailVerification {
		t.Fatalf("result = %+v", result)
	}
	if result.ErrorMessage == nil || *result.ErrorMessage != "Registration successful. Please check your email to verify your account." {
		t.Fatalf("error_message = %v", result.ErrorMessage)
	}
	if result.TokenData == nil || result.TokenData.GetAny("type") != "verification" {
		t.Fatalf("token_data = %v", result.TokenData)
	}
	if len(repo.saved) != 1 {
		t.Fatalf("saved = %d", len(repo.saved))
	}
	saved := repo.saved[0]
	if saved.TokenType != "verification" || saved.Email != "a@b.com" {
		t.Fatalf("saved token = %+v", saved)
	}
	if saved.UserID == nil || *saved.UserID != "u1" {
		t.Fatalf("saved user id = %v", saved.UserID)
	}
	if saved.Metadata == nil || saved.Metadata.GetAny("registration") != true {
		t.Fatalf("saved metadata = %v", saved.Metadata)
	}
	if email.lastVerificationUsername == nil || *email.lastVerificationUsername != "alice" {
		t.Fatalf("email user name = %v", email.lastVerificationUsername)
	}
}

func TestEnhancedRegisterUserSupabaseFailure(t *testing.T) {
	supabase := &fakeSupabaseAuth{signUpResult: SupabaseAuthResult{Success: false, ErrorMessage: stringPtr("nope")}}
	email := &fakeEmailService{}
	repo := &fakeEmailTokenRepository{saveResult: true}
	svc := newEnhancedService(supabase, email, repo)

	result := svc.RegisterUser(context.Background(), "a@b.com", "pw", nil, true)
	if result.Success || result.ErrorMessage == nil || *result.ErrorMessage != "nope" {
		t.Fatalf("result = %+v", result)
	}
	if len(repo.saved) != 0 {
		t.Fatalf("token saved on failure: %d", len(repo.saved))
	}
}

func TestEnhancedRegisterUserEmailFailure(t *testing.T) {
	supabase := &fakeSupabaseAuth{signUpResult: SupabaseAuthResult{Success: true}}
	email := &fakeEmailService{verificationResult: EmailResult{Success: false, ErrorMessage: stringPtr("smtp down")}}
	repo := &fakeEmailTokenRepository{saveResult: true}
	svc := newEnhancedService(supabase, email, repo)

	result := svc.RegisterUser(context.Background(), "a@b.com", "pw", nil, true)
	if !result.Success || result.EmailSent {
		t.Fatalf("result = %+v", result)
	}
	if result.EmailError == nil || *result.EmailError != "smtp down" {
		t.Fatalf("email_error = %v", result.EmailError)
	}
}

func TestEnhancedVerifyEmailTokenInvalid(t *testing.T) {
	svc := newEnhancedService(&fakeSupabaseAuth{}, &fakeEmailService{}, &fakeEmailTokenRepository{validateResult: nil})
	result := svc.VerifyEmailToken(context.Background(), "tok", "a@b.com")
	if result.Success || result.ErrorMessage == nil || *result.ErrorMessage != "Invalid or expired verification token" {
		t.Fatalf("result = %+v", result)
	}
}

func TestEnhancedVerifyEmailTokenSendsWelcome(t *testing.T) {
	userMetadata := entities.NewOrderedMap[any]()
	userMetadata.Set("full_name", "Alice Smith")
	metadata := entities.NewOrderedMap[any]()
	metadata.Set("user_metadata", userMetadata)
	repo := &fakeEmailTokenRepository{validateResult: &repositories.EmailToken{Metadata: metadata}}
	email := &fakeEmailService{welcomeResult: EmailResult{Success: true}}
	svc := newEnhancedService(&fakeSupabaseAuth{}, email, repo)

	result := svc.VerifyEmailToken(context.Background(), "tok", "a@b.com")
	if !result.Success || !result.EmailSent {
		t.Fatalf("result = %+v", result)
	}
	if result.ErrorMessage == nil || *result.ErrorMessage != "Email verified successfully! Welcome to Oracle Server." {
		t.Fatalf("error_message = %v", result.ErrorMessage)
	}
}

func TestEnhancedResendVerification(t *testing.T) {
	saveFail := &fakeEmailTokenRepository{saveResult: false}
	svc := newEnhancedService(&fakeSupabaseAuth{}, &fakeEmailService{}, saveFail)
	result := svc.ResendVerificationEmail(context.Background(), "a@b.com")
	if result.Success || result.ErrorMessage == nil || *result.ErrorMessage != "Failed to generate verification token" {
		t.Fatalf("result = %+v", result)
	}

	repo := &fakeEmailTokenRepository{saveResult: true}
	email := &fakeEmailService{verificationResult: EmailResult{Success: true}}
	svc = newEnhancedService(&fakeSupabaseAuth{}, email, repo)
	result = svc.ResendVerificationEmail(context.Background(), "a@b.com")
	if !result.Success || !result.EmailSent || result.TokenData == nil {
		t.Fatalf("result = %+v", result)
	}
}

func TestEnhancedRequestPasswordReset(t *testing.T) {
	repo := &fakeEmailTokenRepository{saveResult: true}
	email := &fakeEmailService{resetResult: EmailResult{Success: true}}
	svc := newEnhancedService(&fakeSupabaseAuth{}, email, repo)

	result := svc.RequestPasswordReset(context.Background(), "a@b.com", true)
	if !result.Success || !result.EmailSent {
		t.Fatalf("result = %+v", result)
	}
	if result.ErrorMessage == nil || *result.ErrorMessage != "Password reset email sent. Please check your inbox." {
		t.Fatalf("error_message = %v", result.ErrorMessage)
	}
	if len(repo.saved) != 1 || repo.saved[0].TokenType != "password_reset" {
		t.Fatalf("saved = %+v", repo.saved)
	}
}

func TestEnhancedCleanupAndStatsAndTest(t *testing.T) {
	stats := entities.NewOrderedMap[any]()
	stats.Set("total_tokens", int64(3))
	repo := &fakeEmailTokenRepository{cleanupCount: 3, stats: stats}
	email := &fakeEmailService{testResult: EmailResult{Success: true}}
	svc := newEnhancedService(&fakeSupabaseAuth{}, email, repo)

	cleaned := svc.CleanupExpiredTokens(context.Background(), 7)
	if cleaned.GetAny("success") != true || cleaned.GetAny("deleted_tokens") != 3 {
		t.Fatalf("cleanup = %v", cleaned)
	}
	if cleaned.GetAny("message") != "Cleaned up 3 expired tokens" {
		t.Fatalf("cleanup message = %v", cleaned.GetAny("message"))
	}

	reported := svc.GetEmailStats(context.Background())
	if reported.GetAny("success") != true || reported.GetAny("stats") != stats {
		t.Fatalf("stats = %v", reported)
	}

	tested := svc.TestEmailService(context.Background())
	if tested.GetAny("success") != true || tested.GetAny("message") != "Email service connection test completed" {
		t.Fatalf("test = %v", tested)
	}

	repo.cleanupErr = errors.New("db down")
	failed := svc.CleanupExpiredTokens(context.Background(), 7)
	if failed.GetAny("success") != false || failed.GetAny("error_message") != "db down" {
		t.Fatalf("failed cleanup = %v", failed)
	}
}
