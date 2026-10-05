// Package api ports fastmcp/auth/api/supabase_endpoints.py.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strings"

	authpkg "agenthub/fastmcp/auth"
	"agenthub/fastmcp/auth/infrastructure"
	"agenthub/fastmcp/task_management/domain/entities"
)

// SignUpRequest model.
type SignUpRequest struct {
	Email    string  `json:"email"`
	Password string  `json:"password"`
	Username *string `json:"username,omitempty"`
	FullName *string `json:"full_name,omitempty"`
}

// SignInRequest model.
type SignInRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// PasswordResetRequest model.
type PasswordResetRequest struct {
	Email string `json:"email"`
}

// UpdatePasswordRequest model.
type UpdatePasswordRequest struct {
	NewPassword string `json:"new_password"`
}

// ResendVerificationRequest model.
type ResendVerificationRequest struct {
	Email string `json:"email"`
}

// AuthResponse model.
type AuthResponse struct {
	Success                   bool           `json:"success"`
	Message                   string         `json:"message"`
	User                      map[string]any `json:"user,omitempty"`
	AccessToken               *string        `json:"access_token,omitempty"`
	RefreshToken              *string        `json:"refresh_token,omitempty"`
	RequiresEmailVerification bool           `json:"requires_email_verification"`
}

// ExtractBearerToken extracts bearer token from authorization header.
func ExtractBearerToken(r *http.Request) (string, error) {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return "", &authpkg.HTTPException{StatusCode: 401, Detail: "Authorization header missing"}
	}
	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
		return "", &authpkg.HTTPException{StatusCode: 401, Detail: "Invalid authorization header format"}
	}
	return parts[1], nil
}

// FormatAuthResponse formats Supabase result into API response.
func FormatAuthResponse(result infrastructure.SupabaseAuthResult) AuthResponse {
	msg := "Operation successful"
	if result.ErrorMessage != nil && *result.ErrorMessage != "" {
		msg = *result.ErrorMessage
	}

	resp := AuthResponse{
		Success:                   result.Success,
		Message:                   msg,
		RequiresEmailVerification: result.RequiresEmailVerification,
	}

	if result.User != nil {
		userMap := make(map[string]any)
		if id, ok := result.User.Get("id"); ok {
			userMap["id"] = id
		}
		if email, ok := result.User.Get("email"); ok {
			userMap["email"] = email
		}
		if confirmedAt, ok := result.User.Get("confirmed_at"); ok {
			userMap["email_confirmed"] = confirmedAt != nil
		} else {
			userMap["email_confirmed"] = false
		}
		if createdAt, ok := result.User.Get("created_at"); ok {
			userMap["created_at"] = fmt.Sprintf("%v", createdAt)
		}
		if userMeta, ok := result.User.Get("user_metadata"); ok {
			userMap["user_metadata"] = userMeta
		} else {
			userMap["user_metadata"] = map[string]any{}
		}
		resp.User = userMap
	}

	if result.Session != nil {
		if at, ok := result.Session.Get("access_token"); ok && at != nil {
			s := fmt.Sprintf("%v", at)
			resp.AccessToken = &s
		}
		if rt, ok := result.Session.Get("refresh_token"); ok && rt != nil {
			s := fmt.Sprintf("%v", rt)
			resp.RefreshToken = &s
		}
	}

	return resp
}

// SupabaseAuthController implements Supabase authentication endpoints.
type SupabaseAuthController struct {
	Service *infrastructure.SupabaseAuthService
}

// NewSupabaseAuthController creates a new controller.
func NewSupabaseAuthController(svc ...*infrastructure.SupabaseAuthService) *SupabaseAuthController {
	var s *infrastructure.SupabaseAuthService
	if len(svc) > 0 && svc[0] != nil {
		s = svc[0]
	} else {
		inst, err := infrastructure.NewSupabaseAuthService()
		if err == nil {
			s = inst
		}
	}
	return &SupabaseAuthController{Service: s}
}

func (c *SupabaseAuthController) getService() (*infrastructure.SupabaseAuthService, error) {
	if c.Service != nil {
		return c.Service, nil
	}
	s, err := infrastructure.NewSupabaseAuthService()
	if err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Supabase auth service not configured"}
	}
	c.Service = s
	return s, nil
}

// SignUp handles user registration.
func (c *SupabaseAuthController) SignUp(ctx context.Context, req SignUpRequest) (*AuthResponse, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	if len(req.Password) < 6 {
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: "Password must be at least 6 characters"}
	}

	meta := entities.NewOrderedMap[any]()
	if req.Username != nil {
		meta.Set("username", *req.Username)
	}
	if req.FullName != nil {
		meta.Set("full_name", *req.FullName)
	}

	result := svc.SignUp(ctx, req.Email, req.Password, meta)
	if !result.Success {
		msg := "Signup failed"
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: msg}
	}
	resp := FormatAuthResponse(result)
	return &resp, nil
}

// SignIn handles user login.
func (c *SupabaseAuthController) SignIn(ctx context.Context, req SignInRequest) (*AuthResponse, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	result := svc.SignIn(ctx, req.Email, req.Password)
	if !result.Success {
		if result.RequiresEmailVerification {
			return nil, &authpkg.HTTPException{StatusCode: 403, Detail: "Please verify your email before signing in"}
		}
		msg := "Invalid credentials"
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: msg}
	}
	resp := FormatAuthResponse(result)
	return &resp, nil
}

// SignOut handles user logout.
func (c *SupabaseAuthController) SignOut(ctx context.Context, token string) (map[string]any, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	success := svc.SignOut(ctx, token)
	if !success {
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: "Failed to sign out"}
	}
	return map[string]any{"success": true, "message": "Signed out successfully"}, nil
}

// PasswordReset handles password reset email requests.
func (c *SupabaseAuthController) PasswordReset(ctx context.Context, req PasswordResetRequest) (*AuthResponse, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	result := svc.ResetPasswordRequest(ctx, req.Email)
	if !result.Success {
		msg := "Password reset request failed"
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: msg}
	}
	resp := FormatAuthResponse(result)
	return &resp, nil
}

// UpdatePassword updates user password.
func (c *SupabaseAuthController) UpdatePassword(ctx context.Context, token, newPassword string) (*AuthResponse, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	if len(newPassword) < 6 {
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: "Password must be at least 6 characters"}
	}
	result := svc.UpdatePassword(ctx, token, newPassword)
	if !result.Success {
		msg := "Password update failed"
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: msg}
	}
	resp := FormatAuthResponse(result)
	return &resp, nil
}

// VerifyToken verifies token and returns user details.
func (c *SupabaseAuthController) VerifyToken(ctx context.Context, token string) (*AuthResponse, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	result := svc.VerifyToken(ctx, token)
	if !result.Success {
		msg := "Invalid or expired token"
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: msg}
	}
	resp := FormatAuthResponse(result)
	return &resp, nil
}

// ResendVerification resends verification email.
func (c *SupabaseAuthController) ResendVerification(ctx context.Context, req ResendVerificationRequest) (*AuthResponse, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	result := svc.ResendVerificationEmail(ctx, req.Email)
	if !result.Success {
		msg := "Failed to resend verification email"
		if result.ErrorMessage != nil {
			msg = *result.ErrorMessage
		}
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: msg}
	}
	resp := FormatAuthResponse(result)
	return &resp, nil
}

// GetOAuthURL returns OAuth URL for third-party provider.
func (c *SupabaseAuthController) GetOAuthURL(ctx context.Context, provider string) (map[string]any, error) {
	svc, err := c.getService()
	if err != nil {
		return nil, err
	}
	result := svc.SignInWithProvider(ctx, provider)
	if result == nil {
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: "Provider not supported"}
	}
	if errVal, ok := result.Get("error"); ok && errVal != nil {
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: fmt.Sprintf("%v", errVal)}
	}
	urlVal, _ := result.Get("url")
	providerVal, _ := result.Get("provider")
	return map[string]any{
		"success":  true,
		"url":      urlVal,
		"provider": providerVal,
	}, nil
}

// HealthCheck checks if Supabase Auth is configured.
func (c *SupabaseAuthController) HealthCheck() map[string]any {
	url := os.Getenv("SUPABASE_URL")
	key := os.Getenv("SUPABASE_ANON_KEY")
	if url != "" && key != "" {
		return map[string]any{
			"status":     "healthy",
			"service":    "Supabase Auth",
			"configured": true,
		}
	}
	return map[string]any{
		"status":     "unhealthy",
		"service":    "Supabase Auth",
		"configured": false,
		"error":      "Missing configuration",
	}
}

// RegisterRoutes registers all Supabase authentication HTTP routes.
func (c *SupabaseAuthController) RegisterRoutes(mux *http.ServeMux) {
	writeJSON := func(w http.ResponseWriter, status int, data any) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(status)
		_ = json.NewEncoder(w).Encode(data)
	}

	writeHTTPError := func(w http.ResponseWriter, err error) {
		var he *authpkg.HTTPException
		if errors.As(err, &he) {
			writeJSON(w, he.StatusCode, map[string]any{"detail": he.Detail})
			return
		}
		writeJSON(w, http.StatusInternalServerError, map[string]any{"detail": err.Error()})
	}

	mux.HandleFunc("POST /auth/supabase/signup", func(w http.ResponseWriter, r *http.Request) {
		var req SignUpRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.SignUp(r.Context(), req)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /auth/supabase/signin", func(w http.ResponseWriter, r *http.Request) {
		var req SignInRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.SignIn(r.Context(), req)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /auth/supabase/signout", func(w http.ResponseWriter, r *http.Request) {
		token, err := ExtractBearerToken(r)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		res, err := c.SignOut(r.Context(), token)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /auth/supabase/password-reset", func(w http.ResponseWriter, r *http.Request) {
		var req PasswordResetRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.PasswordReset(r.Context(), req)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /auth/supabase/update-password", func(w http.ResponseWriter, r *http.Request) {
		token, err := ExtractBearerToken(r)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		var req UpdatePasswordRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.UpdatePassword(r.Context(), token, req.NewPassword)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("GET /auth/supabase/verify-token", func(w http.ResponseWriter, r *http.Request) {
		token, err := ExtractBearerToken(r)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		res, err := c.VerifyToken(r.Context(), token)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /auth/supabase/resend-verification", func(w http.ResponseWriter, r *http.Request) {
		var req ResendVerificationRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.ResendVerification(r.Context(), req)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("GET /auth/supabase/oauth/", func(w http.ResponseWriter, r *http.Request) {
		parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/auth/supabase/oauth/"), "/")
		provider := parts[0]
		res, err := c.GetOAuthURL(r.Context(), provider)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("GET /auth/supabase/me", func(w http.ResponseWriter, r *http.Request) {
		token, err := ExtractBearerToken(r)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		res, err := c.VerifyToken(r.Context(), token)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("GET /auth/supabase/health", func(w http.ResponseWriter, r *http.Request) {
		res := c.HealthCheck()
		status := http.StatusOK
		if res["status"] != "healthy" {
			status = http.StatusServiceUnavailable
		}
		writeJSON(w, status, res)
	})
}
