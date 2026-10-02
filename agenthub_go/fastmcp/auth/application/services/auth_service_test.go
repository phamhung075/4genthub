package services

import (
	"context"
	"testing"
	"time"

	authEntities "agenthub/fastmcp/auth/domain/entities"
	domainservices "agenthub/fastmcp/auth/domain/services"
)

type fakeUserRepo struct {
	byEmail    map[string]*authEntities.User
	byUsername map[string]*authEntities.User
	byID       map[string]*authEntities.User
	saveErr    error
}

func newFakeUserRepo() *fakeUserRepo {
	return &fakeUserRepo{byEmail: map[string]*authEntities.User{}, byUsername: map[string]*authEntities.User{}, byID: map[string]*authEntities.User{}}
}

func (f *fakeUserRepo) GetByEmail(_ context.Context, email string) (*authEntities.User, error) {
	return f.byEmail[email], nil
}
func (f *fakeUserRepo) GetByUsername(_ context.Context, username string) (*authEntities.User, error) {
	return f.byUsername[username], nil
}
func (f *fakeUserRepo) GetByID(_ context.Context, userID string) (*authEntities.User, error) {
	return f.byID[userID], nil
}
func (f *fakeUserRepo) Save(_ context.Context, user *authEntities.User) (*authEntities.User, error) {
	if f.saveErr != nil {
		return nil, f.saveErr
	}
	if user.ID != nil {
		f.byID[*user.ID] = user
	}
	f.byEmail[user.Email] = user
	f.byUsername[user.Username] = user
	return user, nil
}

func fixedJWT() *domainservices.JWTService {
	svc, err := domainservices.NewJWTService("test-secret", "agenthub")
	if err != nil {
		panic(err)
	}
	t := time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC)
	svc.Now = func() time.Time { return t }
	svc.TokenHex = func(int) string { return "0123456789abcdef0123456789abcdef" }
	return svc
}

func mustUser(t *testing.T, u authEntities.User) *authEntities.User {
	t.Helper()
	id := "11111111-1111-1111-1111-111111111111"
	u.ID = &id
	out, err := authEntities.NewUser(u)
	if err != nil {
		t.Fatalf("NewUser: %v", err)
	}
	return out
}

func TestRegisterUserSuccess(t *testing.T) {
	repo := newFakeUserRepo()
	svc := NewAuthService(repo, fixedJWT())
	res := svc.RegisterUser(context.Background(), "alice@example.com", "alice", "StrongPass1!", nil)
	if !res.Success {
		t.Fatalf("expected success, got error %v", res.ErrorMessage)
	}
	if res.User == nil || res.User.Status != authEntities.UserStatusPendingVerification || res.User.EmailVerified {
		t.Fatalf("unexpected user state: %+v", res.User)
	}
	if res.VerificationToken == nil || *res.VerificationToken == "" {
		t.Fatal("expected verification token")
	}
	if res.User.Roles == nil || len(res.User.Roles) != 1 || res.User.Roles[0] != authEntities.UserRoleUser {
		t.Fatalf("expected default [user] role, got %v", res.User.Roles)
	}
}

func TestRegisterUserInvalidEmail(t *testing.T) {
	svc := NewAuthService(newFakeUserRepo(), fixedJWT())
	res := svc.RegisterUser(context.Background(), "notanemail", "u", "StrongPass1!", nil)
	if res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Registration failed: Invalid email format: notanemail" {
		t.Fatalf("unexpected result: %+v", res)
	}
}

func TestRegisterUserDuplicateAndWeakPassword(t *testing.T) {
	repo := newFakeUserRepo()
	existing, _ := authEntities.NewUser(authEntities.User{Email: "a@b.com", Username: "a", PasswordHash: "h"})
	repo.byEmail["a@b.com"] = existing
	repo.byUsername["a"] = existing
	svc := NewAuthService(repo, fixedJWT())

	res := svc.RegisterUser(context.Background(), "a@b.com", "other", "StrongPass1!", nil)
	if res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Email already registered" {
		t.Fatalf("dup email result: %+v", res)
	}

	res = svc.RegisterUser(context.Background(), "new@b.com", "a", "StrongPass1!", nil)
	if res.Success || res.ErrorMessage == nil || *res.ErrorMessage != "Username already taken" {
		t.Fatalf("dup username result: %+v", res)
	}

	res = svc.RegisterUser(context.Background(), "new@b.com", "newuser", "abc", nil)
	want := "Password too weak. Add uppercase letters, Add numbers, Add special characters, Use at least 12 characters for better security"
	if res.Success || res.ErrorMessage == nil || *res.ErrorMessage != want {
		t.Fatalf("weak password result: got %v want %v", res.ErrorMessage, want)
	}
}

func TestLoginFlow(t *testing.T) {
	hash, _ := domainservices.HashPassword("StrongPass1!")
	repo := newFakeUserRepo()
	user := mustUser(t, authEntities.User{Email: "bob@example.com", Username: "bob", PasswordHash: hash, Status: authEntities.UserStatusActive, EmailVerified: true})
	repo.byEmail["bob@example.com"] = user
	repo.byID[*user.ID] = user
	svc := NewAuthService(repo, fixedJWT())

	res := svc.Login(context.Background(), "bob@example.com", "StrongPass1!", nil)
	if !res.Success {
		t.Fatalf("login failed: %v", res.ErrorMessage)
	}
	if res.AccessToken == nil || res.RefreshToken == nil || *res.AccessToken == "" || *res.RefreshToken == "" {
		t.Fatal("expected tokens")
	}
	if user.RefreshTokenFamily == nil || *user.RefreshTokenFamily == "" {
		t.Fatal("expected refresh token family set")
	}

	bad := svc.Login(context.Background(), "bob@example.com", "wrong", nil)
	if bad.Success || bad.ErrorMessage == nil || *bad.ErrorMessage != "Invalid credentials" {
		t.Fatalf("bad login: %+v", bad)
	}
	if user.FailedLoginAttempts != 1 {
		t.Fatalf("expected 1 failed attempt, got %d", user.FailedLoginAttempts)
	}
}

func TestLoginEmailVerificationRequired(t *testing.T) {
	hash, _ := domainservices.HashPassword("StrongPass1!")
	repo := newFakeUserRepo()
	user := mustUser(t, authEntities.User{Email: "c@example.com", Username: "c", PasswordHash: hash, Status: authEntities.UserStatusActive})
	repo.byEmail["c@example.com"] = user
	repo.byID[*user.ID] = user
	svc := NewAuthService(repo, fixedJWT())

	res := svc.Login(context.Background(), "c@example.com", "StrongPass1!", nil)
	if res.Success || !res.RequiresEmailVerification || res.ErrorMessage == nil || *res.ErrorMessage != "Email verification required" {
		t.Fatalf("unexpected: %+v", res)
	}
}

func TestResetAndRefreshTokens(t *testing.T) {
	hash, _ := domainservices.HashPassword("StrongPass1!")
	repo := newFakeUserRepo()
	user := mustUser(t, authEntities.User{Email: "d@example.com", Username: "d", PasswordHash: hash, Status: authEntities.UserStatusActive, EmailVerified: true})
	repo.byEmail["d@example.com"] = user
	repo.byID[*user.ID] = user
	jwt := fixedJWT()
	svc := NewAuthService(repo, jwt)

	login := svc.Login(context.Background(), "d@example.com", "StrongPass1!", nil)
	if !login.Success {
		t.Fatalf("login failed: %v", login.ErrorMessage)
	}
	access, refresh, ok := svc.RefreshTokens(context.Background(), *login.RefreshToken)
	if !ok || access == "" || refresh == "" {
		t.Fatal("expected refreshed tokens")
	}
	if user.RefreshTokenVersion != 1 {
		t.Fatalf("expected version 1, got %d", user.RefreshTokenVersion)
	}

	resetTok, err := jwt.CreateResetToken(*user.ID, user.Email)
	if err != nil {
		t.Fatal(err)
	}
	okReset, errMsg := svc.ResetPassword(context.Background(), resetTok, "NewStrong1!")
	if !okReset || errMsg != nil {
		t.Fatalf("reset failed: %v", errMsg)
	}
	if !domainservices.VerifyPassword("NewStrong1!", user.PasswordHash) {
		t.Fatal("new password not stored")
	}
}

func TestLogoutAndGetCurrentUser(t *testing.T) {
	repo := newFakeUserRepo()
	user := mustUser(t, authEntities.User{Email: "e@example.com", Username: "e", PasswordHash: "h", Status: authEntities.UserStatusActive})
	repo.byID[*user.ID] = user
	jwt := fixedJWT()
	svc := NewAuthService(repo, jwt)

	if !svc.Logout(context.Background(), *user.ID, true) {
		t.Fatal("logout failed")
	}
	if user.RefreshTokenVersion != 1 {
		t.Fatalf("expected version 1, got %d", user.RefreshTokenVersion)
	}
	if svc.Logout(context.Background(), "missing", false) {
		t.Fatal("logout of missing user should be false")
	}

	tok, err := jwt.CreateAccessToken(*user.ID, user.Email, []string{"user"}, nil, domainservices.DefaultAudience)
	if err != nil {
		t.Fatal(err)
	}
	if got := svc.GetCurrentUser(context.Background(), tok); got == nil || got.Email != "e@example.com" {
		t.Fatalf("unexpected current user: %+v", got)
	}
	if got := svc.GetCurrentUser(context.Background(), "garbage"); got != nil {
		t.Fatalf("expected nil for invalid token, got %+v", got)
	}
}

func TestVerifyEmailMessage(t *testing.T) {
	svc := NewAuthService(newFakeUserRepo(), fixedJWT())
	ok, msg := svc.VerifyEmail(context.Background(), "garbage")
	if ok || msg == nil || *msg != "Invalid or expired verification token" {
		t.Fatalf("unexpected: %v %v", ok, msg)
	}
}
