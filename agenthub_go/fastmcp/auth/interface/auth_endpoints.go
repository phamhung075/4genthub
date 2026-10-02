// Package authinterface ports fastmcp/auth/interface/auth_endpoints.py.
package authinterface

import (
	"bytes"
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"hash/fnv"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"

	authpkg "agenthub/fastmcp/auth"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

var (
	emailRegex    = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)
	usernameRegex = regexp.MustCompile(`^[a-zA-Z0-9_-]+$`)
	upperRegex    = regexp.MustCompile(`[A-Z]`)
	lowerRegex    = regexp.MustCompile(`[a-z]`)
	digitRegex    = regexp.MustCompile(`\d`)
	specialRegex  = regexp.MustCompile(`[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\/;` + "`" + `~]`)
)

func getKeycloakConfig() (url, realm, clientID, clientSecret string, emailVerifiedAuto bool) {
	url = authInterfaceEnvOr("KEYCLOAK_URL", "http://localhost:8080")
	realm = authInterfaceEnvOr("KEYCLOAK_REALM", "agenthub")
	clientID = authInterfaceEnvOr("KEYCLOAK_CLIENT_ID", "agenthub-client")
	clientSecret = os.Getenv("KEYCLOAK_CLIENT_SECRET")
	emailVerifiedAuto = strings.ToLower(os.Getenv("EMAIL_VERIFIED_AUTO")) == "true"
	return
}

// Request and Response models

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type LoginResponse struct {
	AccessToken  string  `json:"access_token"`
	TokenType    string  `json:"token_type"`
	RefreshToken *string `json:"refresh_token,omitempty"`
	ExpiresIn    *int    `json:"expires_in,omitempty"`
	UserID       *string `json:"user_id,omitempty"`
	Email        *string `json:"email,omitempty"`
}

type RegisterRequest struct {
	Email    string  `json:"email"`
	Password string  `json:"password"`
	Username *string `json:"username,omitempty"`
}

type RegisterResponse struct {
	Success        bool     `json:"success"`
	UserID         string   `json:"user_id"`
	Email          string   `json:"email"`
	Username       *string  `json:"username,omitempty"`
	Message        string   `json:"message"`
	MessageType    string   `json:"message_type"`
	DisplayColor   string   `json:"display_color"`
	NextSteps      []string `json:"next_steps,omitempty"`
	AutoLoginToken *string  `json:"auto_login_token,omitempty"`
}

type PasswordValidationResult struct {
	Valid        bool     `json:"valid"`
	Strength     string   `json:"strength"`
	Score        int      `json:"score"`
	MaxScore     int      `json:"max_score"`
	Issues       []string `json:"issues"`
	Suggestions  []string `json:"suggestions"`
	Length       int      `json:"length"`
	HasUppercase bool     `json:"has_uppercase"`
	HasLowercase bool     `json:"has_lowercase"`
	HasDigits    bool     `json:"has_digits"`
	HasSpecial   bool     `json:"has_special"`
}

// Validation helpers

func ValidateEmail(email string) (string, error) {
	if !emailRegex.MatchString(email) {
		return "", errors.New("Please enter a valid email address (e.g., user@example.com)")
	}
	return strings.ToLower(email), nil
}

func ValidateUsername(username string) error {
	if username == "" {
		return nil
	}
	if len(username) < 3 {
		return errors.New("Username must be at least 3 characters long")
	}
	if len(username) > 20 {
		return errors.New("Username must not exceed 20 characters")
	}
	if !usernameRegex.MatchString(username) {
		return errors.New("Username can only contain letters, numbers, underscore (_) and hyphen (-)")
	}
	return nil
}

func ValidatePassword(v string) error {
	var errs []string
	if len(v) < 8 {
		errs = append(errs, "at least 8 characters")
	}
	if !upperRegex.MatchString(v) {
		errs = append(errs, "at least 1 uppercase letter (A-Z)")
	}
	if !lowerRegex.MatchString(v) {
		errs = append(errs, "at least 1 lowercase letter (a-z)")
	}
	if !digitRegex.MatchString(v) {
		errs = append(errs, "at least 1 number (0-9)")
	}
	if !specialRegex.MatchString(v) {
		errs = append(errs, "at least 1 special character (!@#$%^&*()-_+=)")
	}

	if len(errs) > 0 {
		msg := fmt.Sprintf("Password does not meet requirements. It must contain: %s. Your password has %d characters.", strings.Join(errs, ", "), len(v))
		if len(errs) == 1 && strings.Contains(errs[0], "special character") {
			msg += " Try adding a special character like ! or @ to your password."
		} else if len(errs) == 1 && strings.Contains(errs[0], "uppercase") {
			msg += " Try capitalizing the first letter of your password."
		} else if len(errs) > 1 {
			msg += " Example of a valid password: Password123!"
		}
		return errors.New(msg)
	}
	return nil
}

func ValidatePasswordRequirements(password string) PasswordValidationResult {
	var issues []string
	var suggestions []string

	if len(password) < 8 {
		issues = append(issues, "Too short - needs at least 8 characters")
		suggestions = append(suggestions, fmt.Sprintf("Add %d more characters", 8-len(password)))
	}
	if !upperRegex.MatchString(password) {
		issues = append(issues, "Missing uppercase letter")
		suggestions = append(suggestions, "Try capitalizing the first letter")
	}
	if !lowerRegex.MatchString(password) {
		issues = append(issues, "Missing lowercase letter")
		suggestions = append(suggestions, "Add some lowercase letters")
	}
	if !digitRegex.MatchString(password) {
		issues = append(issues, "Missing number")
		suggestions = append(suggestions, "Add a number like your birth year or favorite number")
	}
	if !specialRegex.MatchString(password) {
		issues = append(issues, "Missing special character")
		suggestions = append(suggestions, "Add a special character like ! or @")
	}

	strength := "weak"
	strengthScore := 0
	if len(password) >= 8 {
		strengthScore++
	}
	if len(password) >= 12 {
		strengthScore++
	}
	if upperRegex.MatchString(password) && lowerRegex.MatchString(password) {
		strengthScore++
	}
	if digitRegex.MatchString(password) {
		strengthScore++
	}
	if specialRegex.MatchString(password) {
		strengthScore++
	}

	if strengthScore >= 5 {
		strength = "strong"
	} else if strengthScore >= 3 {
		strength = "medium"
	}

	return PasswordValidationResult{
		Valid:        len(issues) == 0,
		Strength:     strength,
		Score:        strengthScore,
		MaxScore:     5,
		Issues:       issues,
		Suggestions:  suggestions,
		Length:       len(password),
		HasUppercase: upperRegex.MatchString(password),
		HasLowercase: lowerRegex.MatchString(password),
		HasDigits:    digitRegex.MatchString(password),
		HasSpecial:   specialRegex.MatchString(password),
	}
}

// AuthController manages authentication routes.
type AuthController struct {
	httpClient *http.Client
}

// NewAuthController creates a new AuthController.
func NewAuthController() *AuthController {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	return &AuthController{
		httpClient: &http.Client{Transport: tr, Timeout: 15 * time.Second},
	}
}

func parseUnverifiedJWT(token string) (map[string]any, error) {
	parts := strings.Split(token, ".")
	if len(parts) < 2 {
		return nil, errors.New("invalid jwt token")
	}
	payloadSegment := parts[1]
	// Pad base64 if needed
	switch len(payloadSegment) % 4 {
	case 2:
		payloadSegment += "=="
	case 3:
		payloadSegment += "="
	}
	bytes, err := base64.URLEncoding.DecodeString(payloadSegment)
	if err != nil {
		bytes, err = base64.RawURLEncoding.DecodeString(payloadSegment)
		if err != nil {
			return nil, err
		}
	}
	var claims map[string]any
	if err := json.Unmarshal(bytes, &claims); err != nil {
		return nil, err
	}
	return claims, nil
}

func createDevJWT(email, userID, secret string) (string, error) {
	now := time.Now().UTC()
	exp := now.Add(24 * time.Hour)

	header := map[string]string{"alg": "HS256", "typ": "JWT"}
	payload := map[string]any{
		"sub":      userID,
		"email":    email,
		"username": strings.Split(email, "@")[0],
		"iat":      now.Unix(),
		"exp":      exp.Unix(),
		"type":     "local_dev",
	}

	hBytes, _ := json.Marshal(header)
	pBytes, _ := json.Marshal(payload)

	hB64 := base64.RawURLEncoding.EncodeToString(hBytes)
	pB64 := base64.RawURLEncoding.EncodeToString(pBytes)
	signingInput := hB64 + "." + pB64

	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write([]byte(signingInput))
	sig := base64.RawURLEncoding.EncodeToString(mac.Sum(nil))

	return signingInput + "." + sig, nil
}

// GetKeycloakAdminToken retrieves Keycloak admin access token.
func (c *AuthController) GetKeycloakAdminToken(ctx context.Context) (string, error) {
	kcURL, realm, clientID, clientSecret, _ := getKeycloakConfig()
	tokenURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/token", kcURL, realm)

	// Try client credentials
	data := url.Values{
		"grant_type":    {"client_credentials"},
		"client_id":     {clientID},
		"client_secret": {clientSecret},
	}

	req, err := http.NewRequestWithContext(ctx, "POST", tokenURL, strings.NewReader(data.Encode()))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := c.httpClient.Do(req)
	if err == nil && resp.StatusCode == 200 {
		defer resp.Body.Close()
		var res map[string]any
		if json.NewDecoder(resp.Body).Decode(&res) == nil {
			if token, ok := res["access_token"].(string); ok && token != "" {
				return token, nil
			}
		}
	}
	if resp != nil {
		resp.Body.Close()
	}

	// Fallback to admin username/password
	adminPass := os.Getenv("KEYCLOAK_ADMIN_PASSWORD")
	adminData := url.Values{
		"grant_type": {"password"},
		"client_id":  {"admin-cli"},
		"username":   {"admin"},
		"password":   {adminPass},
	}
	masterURL := fmt.Sprintf("%s/realms/master/protocol/openid-connect/token", kcURL)
	req2, err := http.NewRequestWithContext(ctx, "POST", masterURL, strings.NewReader(adminData.Encode()))
	if err != nil {
		return "", err
	}
	req2.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp2, err := c.httpClient.Do(req2)
	if err == nil && resp2.StatusCode == 200 {
		defer resp2.Body.Close()
		var res map[string]any
		if json.NewDecoder(resp2.Body).Decode(&res) == nil {
			if token, ok := res["access_token"].(string); ok && token != "" {
				return token, nil
			}
		}
	}
	if resp2 != nil {
		resp2.Body.Close()
	}

	return "", errors.New("Failed to get Keycloak admin token")
}

// CleanupIncompleteAccount removes incomplete account to allow re-registration.
func (c *AuthController) CleanupIncompleteAccount(ctx context.Context, email string) (map[string]any, error) {
	provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))
	if provider != "keycloak" {
		return map[string]any{"success": false, "message": "Account cleanup not supported for this provider"}, nil
	}

	adminToken, err := c.GetKeycloakAdminToken(ctx)
	if err != nil || adminToken == "" {
		return map[string]any{"success": false, "message": "Unable to obtain admin access"}, nil
	}

	kcURL, realm, _, _, _ := getKeycloakConfig()
	usersURL := fmt.Sprintf("%s/admin/realms/%s/users?email=%s&exact=true", kcURL, realm, url.QueryEscape(email))

	req, err := http.NewRequestWithContext(ctx, "GET", usersURL, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+adminToken)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return map[string]any{"success": false, "message": "Authentication service unavailable"}, nil
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return map[string]any{"success": false, "message": "Failed to search for user"}, nil
	}

	var users []map[string]any
	if err := json.NewDecoder(resp.Body).Decode(&users); err != nil || len(users) == 0 {
		return map[string]any{"success": false, "message": "No account found with this email address.", "can_register": true}, nil
	}

	user := users[0]
	userID, _ := user["id"].(string)
	emailVerified, _ := user["emailVerified"].(bool)
	accountEnabled := true
	if en, ok := user["enabled"].(bool); ok {
		accountEnabled = en
	}
	var reqActions []string
	if ra, ok := user["requiredActions"].([]any); ok {
		for _, a := range ra {
			reqActions = append(reqActions, fmt.Sprintf("%v", a))
		}
	}
	var creds []any
	if cr, ok := user["credentials"].([]any); ok {
		creds = cr
	}

	shouldCleanup := !emailVerified && len(reqActions) > 0 && (!accountEnabled || len(creds) == 0)
	if shouldCleanup {
		delURL := fmt.Sprintf("%s/admin/realms/%s/users/%s", kcURL, realm, userID)
		delReq, _ := http.NewRequestWithContext(ctx, "DELETE", delURL, nil)
		delReq.Header.Set("Authorization", "Bearer "+adminToken)
		delResp, err := c.httpClient.Do(delReq)
		if err == nil {
			delResp.Body.Close()
			if delResp.StatusCode == 204 {
				return map[string]any{
					"success":      true,
					"message":      "Incomplete account removed. Ready for registration.",
					"can_register": true,
				}, nil
			}
		}
		return map[string]any{"success": false, "message": "Failed to clean up account"}, nil
	}

	return map[string]any{
		"success":      false,
		"message":      "Account is verified and properly set up. Please use the login page instead.",
		"can_register": false,
		"reason":       "account_complete_and_verified",
	}, nil
}

// SetupUserRoles configures user roles in Keycloak.
func (c *AuthController) SetupUserRoles(ctx context.Context, adminToken, userID, userEmail string) error {
	kcURL, realm, clientID, _, emailVerifiedAuto := getKeycloakConfig()
	userURL := fmt.Sprintf("%s/admin/realms/%s/users/%s", kcURL, realm, userID)

	// Fetch user to preserve username
	getReq, _ := http.NewRequestWithContext(ctx, "GET", userURL, nil)
	getReq.Header.Set("Authorization", "Bearer "+adminToken)
	getResp, err := c.httpClient.Do(getReq)
	if err == nil && getResp.StatusCode == 200 {
		var curUser map[string]any
		_ = json.NewDecoder(getResp.Body).Decode(&curUser)
		getResp.Body.Close()

		username, _ := curUser["username"].(string)
		if username == "" {
			username = userEmail
		}

		attrs := make(map[string]any)
		if curAttrs, ok := curUser["attributes"].(map[string]any); ok {
			for k, v := range curAttrs {
				attrs[k] = v
			}
		}
		attrs["account_setup_complete"] = []string{"true"}
		attrs["email_verified_auto"] = []string{fmt.Sprintf("%v", emailVerifiedAuto)}
		attrs["registration_complete"] = []string{"true"}

		updateData := map[string]any{
			"username":        username,
			"email":           userEmail,
			"enabled":         true,
			"emailVerified":   emailVerifiedAuto,
			"requiredActions": []string{},
			"attributes":      attrs,
		}
		bodyBytes, _ := json.Marshal(updateData)
		putReq, _ := http.NewRequestWithContext(ctx, "PUT", userURL, bytes.NewReader(bodyBytes))
		putReq.Header.Set("Authorization", "Bearer "+adminToken)
		putReq.Header.Set("Content-Type", "application/json")
		if putResp, err := c.httpClient.Do(putReq); err == nil {
			putResp.Body.Close()
		}
	} else if getResp != nil {
		getResp.Body.Close()
	}

	// Assign client-specific roles
	clientsURL := fmt.Sprintf("%s/admin/realms/%s/clients?clientId=%s", kcURL, realm, url.QueryEscape(clientID))
	clReq, _ := http.NewRequestWithContext(ctx, "GET", clientsURL, nil)
	clReq.Header.Set("Authorization", "Bearer "+adminToken)
	if clResp, err := c.httpClient.Do(clReq); err == nil && clResp.StatusCode == 200 {
		var clients []map[string]any
		_ = json.NewDecoder(clResp.Body).Decode(&clients)
		clResp.Body.Close()

		if len(clients) > 0 {
			clientUUID, _ := clients[0]["id"].(string)
			clientRolesURL := fmt.Sprintf("%s/admin/realms/%s/clients/%s/roles", kcURL, realm, clientUUID)
			crReq, _ := http.NewRequestWithContext(ctx, "GET", clientRolesURL, nil)
			crReq.Header.Set("Authorization", "Bearer "+adminToken)
			if crResp, err := c.httpClient.Do(crReq); err == nil && crResp.StatusCode == 200 {
				var clientRoles []map[string]any
				_ = json.NewDecoder(crResp.Body).Decode(&clientRoles)
				crResp.Body.Close()

				if len(clientRoles) > 0 {
					assignURL := fmt.Sprintf("%s/admin/realms/%s/users/%s/role-mappings/clients/%s", kcURL, realm, userID, clientUUID)
					b, _ := json.Marshal(clientRoles)
					asReq, _ := http.NewRequestWithContext(ctx, "POST", assignURL, bytes.NewReader(b))
					asReq.Header.Set("Authorization", "Bearer "+adminToken)
					asReq.Header.Set("Content-Type", "application/json")
					if asResp, err := c.httpClient.Do(asReq); err == nil {
						asResp.Body.Close()
					}
				}
			} else if crResp != nil {
				crResp.Body.Close()
			}
		}
	} else if clResp != nil {
		clResp.Body.Close()
	}

	// Assign realm roles
	realmRolesURL := fmt.Sprintf("%s/admin/realms/%s/roles", kcURL, realm)
	rrReq, _ := http.NewRequestWithContext(ctx, "GET", realmRolesURL, nil)
	rrReq.Header.Set("Authorization", "Bearer "+adminToken)
	if rrResp, err := c.httpClient.Do(rrReq); err == nil && rrResp.StatusCode == 200 {
		var availRoles []map[string]any
		_ = json.NewDecoder(rrResp.Body).Decode(&availRoles)
		rrResp.Body.Close()

		requiredRoles := []string{"user", "offline_access", "uma_authorization"}
		var rolesToAssign []map[string]any
		for _, reqName := range requiredRoles {
			for _, r := range availRoles {
				if r["name"] == reqName {
					rolesToAssign = append(rolesToAssign, map[string]any{
						"id":          r["id"],
						"name":        r["name"],
						"description": r["description"],
					})
					break
				}
			}
		}

		if len(rolesToAssign) > 0 {
			userRolesURL := fmt.Sprintf("%s/admin/realms/%s/users/%s/role-mappings/realm", kcURL, realm, userID)
			b, _ := json.Marshal(rolesToAssign)
			postReq, _ := http.NewRequestWithContext(ctx, "POST", userRolesURL, bytes.NewReader(b))
			postReq.Header.Set("Authorization", "Bearer "+adminToken)
			postReq.Header.Set("Content-Type", "application/json")
			if postResp, err := c.httpClient.Do(postReq); err == nil {
				postResp.Body.Close()
			}
		}
	} else if rrResp != nil {
		rrResp.Body.Close()
	}

	return nil
}

// Register registers a new user.
func (c *AuthController) Register(ctx context.Context, req RegisterRequest) (any, error) {
	email, err := ValidateEmail(req.Email)
	if err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 422, Detail: err.Error()}
	}
	req.Email = email

	if err := ValidatePassword(req.Password); err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 422, Detail: err.Error()}
	}

	if req.Username != nil {
		if err := ValidateUsername(*req.Username); err != nil {
			return nil, &authpkg.HTTPException{StatusCode: 422, Detail: err.Error()}
		}
	}

	provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))

	if provider == "keycloak" {
		kcURL, realm, clientID, clientSecret, emailVerifiedAuto := getKeycloakConfig()
		adminToken, err := c.GetKeycloakAdminToken(ctx)
		if err != nil || adminToken == "" {
			return nil, &authpkg.HTTPException{StatusCode: 503, Detail: "Registration service not properly configured. Please contact administrator."}
		}

		adminURL := fmt.Sprintf("%s/admin/realms/%s/users", kcURL, realm)
		tokenURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/token", kcURL, realm)

		userData := map[string]any{
			"username":      req.Email,
			"email":         req.Email,
			"enabled":       true,
			"emailVerified": emailVerifiedAuto,
			"credentials": []map[string]any{
				{
					"type":      "password",
					"value":     req.Password,
					"temporary": false,
				},
			},
		}
		if req.Username != nil && *req.Username != "" {
			userData["username"] = *req.Username
		}
		if !emailVerifiedAuto {
			userData["requiredActions"] = []string{"VERIFY_EMAIL"}
		}

		b, _ := json.Marshal(userData)
		createReq, err := http.NewRequestWithContext(ctx, "POST", adminURL, bytes.NewReader(b))
		if err != nil {
			return nil, &authpkg.HTTPException{StatusCode: 500, Detail: err.Error()}
		}
		createReq.Header.Set("Authorization", "Bearer "+adminToken)
		createReq.Header.Set("Content-Type", "application/json")

		createResp, err := c.httpClient.Do(createReq)
		if err != nil {
			return nil, &authpkg.HTTPException{StatusCode: 503, Detail: "Registration service is temporarily unavailable. Please try again in a few moments."}
		}
		defer createResp.Body.Close()

		if createResp.StatusCode == 201 {
			loc := createResp.Header.Get("Location")
			userID := "new-user"
			if loc != "" {
				parts := strings.Split(loc, "/")
				userID = parts[len(parts)-1]
			}

			if userID != "" && userID != "new-user" {
				_ = c.SetupUserRoles(ctx, adminToken, userID, req.Email)
			}

			// Auto login attempt
			var autoLoginToken *string
			loginData := url.Values{
				"grant_type": {"password"},
				"client_id":  {clientID},
				"username":   {req.Email},
				"password":   {req.Password},
				"scope":      {"openid"},
			}
			if clientSecret != "" {
				loginData.Set("client_secret", clientSecret)
			}

			for attempt := 0; attempt < 3; attempt++ {
				if attempt > 0 {
					time.Sleep(1 * time.Second)
				}
				lReq, _ := http.NewRequestWithContext(ctx, "POST", tokenURL, strings.NewReader(loginData.Encode()))
				lReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")
				if lResp, err := c.httpClient.Do(lReq); err == nil {
					if lResp.StatusCode == 200 {
						var td map[string]any
						_ = json.NewDecoder(lResp.Body).Decode(&td)
						lResp.Body.Close()
						if tok, ok := td["access_token"].(string); ok && tok != "" {
							autoLoginToken = &tok
							break
						}
					}
					lResp.Body.Close()
				}
			}

			msg := "🎉 SUCCESS: Your account has been created successfully!"
			msgType := "success"
			color := "green"
			nextSteps := []string{
				"You can now log in with your email and password",
				"Check your email for verification (if enabled)",
				"Complete your profile settings",
			}
			if autoLoginToken != nil {
				nextSteps[0] = "You have been automatically logged in"
				msg = "🎉 SUCCESS: Account created and you have been automatically logged in!"
			} else if !emailVerifiedAuto {
				msg = "📧 Account created! Please check your email to verify your account before logging in."
				msgType = "warning"
				color = "yellow"
				nextSteps = []string{
					"Check your email for the verification link",
					"Click the verification link to activate your account",
					"After verification, you can log in with your credentials",
				}
			}

			return RegisterResponse{
				Success:        true,
				UserID:         userID,
				Email:          req.Email,
				Username:       req.Username,
				Message:        msg,
				MessageType:    msgType,
				DisplayColor:   color,
				NextSteps:      nextSteps,
				AutoLoginToken: autoLoginToken,
			}, nil
		}

		if createResp.StatusCode == 409 {
			cleanupRes, _ := c.CleanupIncompleteAccount(ctx, req.Email)
			canRegister, _ := cleanupRes["can_register"].(bool)
			if canRegister {
				// Retry creation
				retryReq, _ := http.NewRequestWithContext(ctx, "POST", adminURL, bytes.NewReader(b))
				retryReq.Header.Set("Authorization", "Bearer "+adminToken)
				retryReq.Header.Set("Content-Type", "application/json")
				if retryResp, err := c.httpClient.Do(retryReq); err == nil && retryResp.StatusCode == 201 {
					defer retryResp.Body.Close()
					loc := retryResp.Header.Get("Location")
					userID := "new-user"
					if loc != "" {
						parts := strings.Split(loc, "/")
						userID = parts[len(parts)-1]
					}
					_ = c.SetupUserRoles(ctx, adminToken, userID, req.Email)
					return RegisterResponse{
						Success:      true,
						UserID:       userID,
						Email:        req.Email,
						Username:     req.Username,
						Message:      "🎉 SUCCESS: Account issue resolved and registration completed!",
						MessageType:  "success",
						DisplayColor: "green",
						NextSteps: []string{
							"Previous account issue has been resolved",
							"You can now log in with your credentials",
							"Your account is fully set up and ready to use",
						},
					}, nil
				}
			}
			return nil, &authpkg.HTTPException{StatusCode: 409, Detail: "An account with this email already exists. Please try logging in instead."}
		}

		// Other Keycloak errors
		respBody, _ := io.ReadAll(createResp.Body)
		detailMsg := string(respBody)
		if strings.Contains(strings.ToLower(detailMsg), "password") {
			detailMsg = "Password does not meet security requirements. Example: Password123!"
		}
		return nil, &authpkg.HTTPException{StatusCode: 400, Detail: detailMsg}

	} else if provider == "supabase" {
		return nil, &authpkg.HTTPException{StatusCode: 501, Detail: "Supabase registration is not yet implemented. Please contact administrator."}
	}

	// Test/Local Mode
	dummyID := fmt.Sprintf("test-user-%d", time.Now().UnixNano()%100000)
	return RegisterResponse{
		Success:      true,
		UserID:       dummyID,
		Email:        req.Email,
		Username:     req.Username,
		Message:      "✅ SUCCESS: Registration completed! (Test Mode)",
		MessageType:  "success",
		DisplayColor: "green",
		NextSteps: []string{
			"This is test mode - no real account was created",
			"Configure Keycloak for real registration",
			fmt.Sprintf("Test User ID: %s", dummyID),
		},
	}, nil
}

// Login authenticates with Keycloak, Supabase, or development mode.
func (c *AuthController) Login(ctx context.Context, req LoginRequest) (*LoginResponse, error) {
	provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))

	if provider == "keycloak" {
		kcURL, realm, clientID, clientSecret, _ := getKeycloakConfig()
		tokenURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/token", kcURL, realm)

		data := url.Values{
			"grant_type": {"password"},
			"client_id":  {clientID},
			"username":   {req.Email},
			"password":   {req.Password},
			"scope":      {"openid"},
		}
		if clientSecret != "" {
			data.Set("client_secret", clientSecret)
		}

		httpReq, err := http.NewRequestWithContext(ctx, "POST", tokenURL, strings.NewReader(data.Encode()))
		if err != nil {
			return nil, &authpkg.HTTPException{StatusCode: 500, Detail: err.Error()}
		}
		httpReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")

		resp, err := c.httpClient.Do(httpReq)
		if err != nil {
			// Check development fallback
			env := value_objects.PyLower(authInterfaceEnvOr("ENV", "production"))
			if env == "local" || env == "development" || env == "dev" {
				secret := os.Getenv("JWT_SECRET_KEY")
				if secret != "" {
					h := fnv.New32a()
					h.Write([]byte(req.Email))
					devUID := fmt.Sprintf("dev-user-%d", h.Sum32()%10000)
					tok, err := createDevJWT(req.Email, devUID, secret)
					if err == nil {
						exp := 86400
						return &LoginResponse{
							AccessToken: tok,
							TokenType:   "bearer",
							UserID:      &devUID,
							Email:       &req.Email,
							ExpiresIn:   &exp,
						}, nil
					}
				}
			}
			return nil, &authpkg.HTTPException{StatusCode: 503, Detail: "Authentication service unavailable"}
		}
		defer resp.Body.Close()

		if resp.StatusCode == 200 {
			var td map[string]any
			if err := json.NewDecoder(resp.Body).Decode(&td); err != nil {
				return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Failed to parse token response"}
			}
			tok, _ := td["access_token"].(string)
			var refTok *string
			if rt, ok := td["refresh_token"].(string); ok && rt != "" {
				refTok = &rt
			}
			var expIn *int
			if exp, ok := td["expires_in"].(float64); ok {
				n := int(exp)
				expIn = &n
			}

			claims, _ := parseUnverifiedJWT(tok)
			var uid *string
			if sub, ok := claims["sub"].(string); ok && sub != "" {
				uid = &sub
			}
			em := req.Email
			if claimEmail, ok := claims["email"].(string); ok && claimEmail != "" {
				em = claimEmail
			}

			return &LoginResponse{
				AccessToken:  tok,
				TokenType:    "bearer",
				RefreshToken: refTok,
				ExpiresIn:    expIn,
				UserID:       uid,
				Email:        &em,
			}, nil
		}

		if resp.StatusCode == 401 {
			return nil, &authpkg.HTTPException{StatusCode: 401, Detail: "Invalid credentials"}
		}

		if resp.StatusCode == 400 {
			var errData map[string]any
			_ = json.NewDecoder(resp.Body).Decode(&errData)
			errMsg := fmt.Sprintf("%v", errData["error_description"])
			if strings.Contains(strings.ToLower(errMsg), "not fully set up") {
				return nil, &authpkg.HTTPException{
					StatusCode: 400,
					Detail:     "Your account is incomplete. Please try registering again with this email address. The system will handle any existing account issues automatically.",
				}
			}
			if strings.Contains(strings.ToLower(errMsg), "invalid_grant") {
				return nil, &authpkg.HTTPException{
					StatusCode: 401,
					Detail:     "Invalid email or password. Please check your credentials and try again.",
				}
			}
			return nil, &authpkg.HTTPException{StatusCode: 400, Detail: fmt.Sprintf("Authentication failed: %s", errMsg)}
		}

		return nil, &authpkg.HTTPException{StatusCode: resp.StatusCode, Detail: "Authentication failed"}

	} else if provider == "supabase" {
		return nil, &authpkg.HTTPException{StatusCode: 501, Detail: "Supabase authentication not implemented"}
	}

	// Test mode
	exp := 3600
	uid := "test-user-001"
	return &LoginResponse{
		AccessToken: "test-token-12345",
		TokenType:   "bearer",
		UserID:      &uid,
		Email:       &req.Email,
		ExpiresIn:   &exp,
	}, nil
}

// RefreshToken refreshes tokens using refresh token.
func (c *AuthController) RefreshToken(ctx context.Context, refreshToken string) (map[string]any, error) {
	if refreshToken == "" {
		return nil, &authpkg.HTTPException{StatusCode: 422, Detail: "refresh_token is required"}
	}

	provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))

	if provider == "keycloak" {
		kcURL, realm, clientID, clientSecret, _ := getKeycloakConfig()
		tokenURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/token", kcURL, realm)

		data := url.Values{
			"grant_type":    {"refresh_token"},
			"client_id":     {clientID},
			"refresh_token": {refreshToken},
		}
		if clientSecret != "" {
			data.Set("client_secret", clientSecret)
		}

		httpReq, err := http.NewRequestWithContext(ctx, "POST", tokenURL, strings.NewReader(data.Encode()))
		if err != nil {
			return nil, &authpkg.HTTPException{StatusCode: 500, Detail: err.Error()}
		}
		httpReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")

		resp, err := c.httpClient.Do(httpReq)
		if err != nil {
			return nil, &authpkg.HTTPException{StatusCode: 503, Detail: "Authentication service unavailable"}
		}
		defer resp.Body.Close()

		if resp.StatusCode == 200 {
			var td map[string]any
			if err := json.NewDecoder(resp.Body).Decode(&td); err != nil {
				return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "Failed to parse refresh response"}
			}
			newRefTok := refreshToken
			if rt, ok := td["refresh_token"].(string); ok && rt != "" {
				newRefTok = rt
			}
			claims, _ := parseUnverifiedJWT(fmt.Sprintf("%v", td["access_token"]))
			return map[string]any{
				"access_token":  td["access_token"],
				"refresh_token": newRefTok,
				"expires_in":    td["expires_in"],
				"user_id":       claims["sub"],
				"email":         claims["email"],
			}, nil
		}

		return nil, &authpkg.HTTPException{StatusCode: 401, Detail: "Invalid refresh token"}

	} else if provider == "supabase" {
		return nil, &authpkg.HTTPException{StatusCode: 501, Detail: "Supabase token refresh is not yet implemented"}
	}

	return map[string]any{
		"access_token":  fmt.Sprintf("test-refreshed-token-%d", time.Now().Unix()),
		"refresh_token": refreshToken,
		"expires_in":    3600,
		"user_id":       "test-user-001",
		"email":         "test@example.com",
	}, nil
}

// DevLogin handles local development login.
func (c *AuthController) DevLogin(ctx context.Context) (*LoginResponse, error) {
	env := value_objects.PyLower(authInterfaceEnvOr("ENV", "production"))
	if env != "local" && env != "development" && env != "dev" {
		return nil, &authpkg.HTTPException{StatusCode: 404, Detail: "Not found"}
	}

	secret := os.Getenv("JWT_SECRET_KEY")
	if secret == "" {
		return nil, &authpkg.HTTPException{StatusCode: 500, Detail: "JWT_SECRET_KEY not configured"}
	}

	devUID := "dev-user-001"
	devEmail := "dev@example.com"
	tok, err := createDevJWT(devEmail, devUID, secret)
	if err != nil {
		return nil, &authpkg.HTTPException{StatusCode: 500, Detail: err.Error()}
	}

	exp := 86400
	return &LoginResponse{
		AccessToken: tok,
		TokenType:   "bearer",
		UserID:      &devUID,
		Email:       &devEmail,
		ExpiresIn:   &exp,
	}, nil
}

// Logout logs out current user.
func (c *AuthController) Logout(ctx context.Context, refreshToken string) (map[string]any, error) {
	provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))
	if provider == "keycloak" && refreshToken != "" {
		kcURL, realm, clientID, clientSecret, _ := getKeycloakConfig()
		logoutURL := fmt.Sprintf("%s/realms/%s/protocol/openid-connect/logout", kcURL, realm)

		data := url.Values{
			"client_id":     {clientID},
			"refresh_token": {refreshToken},
		}
		if clientSecret != "" {
			data.Set("client_secret", clientSecret)
		}

		httpReq, _ := http.NewRequestWithContext(ctx, "POST", logoutURL, strings.NewReader(data.Encode()))
		httpReq.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		if resp, err := c.httpClient.Do(httpReq); err == nil {
			resp.Body.Close()
		}
	}
	return map[string]any{"message": "Logged out successfully"}, nil
}

// GetProviderConfig returns auth provider configuration.
func (c *AuthController) GetProviderConfig() map[string]any {
	provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))
	kcURL, realm, clientID, _, _ := getKeycloakConfig()
	if provider == "keycloak" {
		return map[string]any{
			"provider":           provider,
			"keycloak_url":       kcURL,
			"keycloak_realm":     realm,
			"keycloak_client_id": clientID,
		}
	}
	return map[string]any{
		"provider":           provider,
		"keycloak_url":       nil,
		"keycloak_realm":     nil,
		"keycloak_client_id": nil,
	}
}

// HandleRegistrationSuccess provides onboarding information after registration.
func (c *AuthController) HandleRegistrationSuccess(userID, email string) map[string]any {
	return map[string]any{
		"success":         true,
		"user_id":         userID,
		"email":           email,
		"welcome_message": fmt.Sprintf("🎆 Welcome to MCP Platform, %s!", email),
		"onboarding_steps": []map[string]any{
			{
				"step":        1,
				"title":       "Verify Your Email",
				"description": "Check your inbox for a verification email",
				"status":      "pending",
				"optional":    false,
			},
			{
				"step":        2,
				"title":       "Complete Your Profile",
				"description": "Add your name, avatar, and preferences",
				"status":      "pending",
				"optional":    false,
			},
			{
				"step":        3,
				"title":       "Create Your First Project",
				"description": "Start by creating a new project or importing an existing one",
				"status":      "pending",
				"optional":    true,
			},
			{
				"step":        4,
				"title":       "Explore Features",
				"description": "Check out our documentation and tutorials",
				"status":      "pending",
				"optional":    true,
			},
		},
		"quick_links": []map[string]any{
			{"title": "Documentation", "url": "/ai_docs"},
			{"title": "Profile Settings", "url": "/settings/profile"},
			{"title": "Create Project", "url": "/projects/new"},
			{"title": "Support", "url": "/support"},
		},
		"tips": []string{
			"Your password is securely encrypted and never stored in plain text",
			"Enable two-factor authentication for extra security",
			"You can change your email and username in profile settings",
			"Join our community forum to connect with other users",
		},
	}
}

// RegisterRoutes registers all authentication routes on an http.ServeMux.
func (c *AuthController) RegisterRoutes(mux *http.ServeMux) {
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

	mux.HandleFunc("POST /api/auth/register", func(w http.ResponseWriter, r *http.Request) {
		var req RegisterRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.Register(r.Context(), req)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /api/auth/login", func(w http.ResponseWriter, r *http.Request) {
		var req LoginRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.Login(r.Context(), req)
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /api/auth/refresh", func(w http.ResponseWriter, r *http.Request) {
		var body map[string]string
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			writeJSON(w, http.StatusUnprocessableEntity, map[string]any{"detail": "Invalid request body"})
			return
		}
		res, err := c.RefreshToken(r.Context(), body["refresh_token"])
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /api/auth/dev-login", func(w http.ResponseWriter, r *http.Request) {
		res, err := c.DevLogin(r.Context())
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("POST /api/auth/logout", func(w http.ResponseWriter, r *http.Request) {
		var body map[string]string
		_ = json.NewDecoder(r.Body).Decode(&body)
		res, err := c.Logout(r.Context(), body["refresh_token"])
		if err != nil {
			writeHTTPError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, res)
	})

	mux.HandleFunc("GET /api/auth/provider", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, c.GetProviderConfig())
	})

	mux.HandleFunc("POST /api/auth/registration-success", func(w http.ResponseWriter, r *http.Request) {
		var body map[string]string
		_ = json.NewDecoder(r.Body).Decode(&body)
		writeJSON(w, http.StatusOK, c.HandleRegistrationSuccess(body["user_id"], body["email"]))
	})

	mux.HandleFunc("GET /api/auth/verify", func(w http.ResponseWriter, r *http.Request) {
		provider := value_objects.PyLower(authInterfaceEnvOr("AUTH_PROVIDER", "keycloak"))
		writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "provider": provider})
	})

	mux.HandleFunc("GET /api/auth/password-requirements", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{
			"requirements": []map[string]any{
				{"rule": "min_length", "value": 8, "description": "At least 8 characters"},
				{"rule": "uppercase", "value": 1, "description": "At least 1 uppercase letter (A-Z)"},
				{"rule": "lowercase", "value": 1, "description": "At least 1 lowercase letter (a-z)"},
				{"rule": "digits", "value": 1, "description": "At least 1 number (0-9)"},
				{"rule": "special", "value": 1, "description": "At least 1 special character (!@#$%^&*()-_+=)"},
			},
			"example_passwords": []string{"Password123!", "SecurePass@2024", "MyP@ssw0rd"},
			"tips": []string{
				"Use a mix of uppercase and lowercase letters",
				"Include numbers and special characters",
				"Avoid using personal information",
				"Make it memorable but hard to guess",
			},
		})
	})

	mux.HandleFunc("POST /api/auth/validate-password", func(w http.ResponseWriter, r *http.Request) {
		var body map[string]string
		_ = json.NewDecoder(r.Body).Decode(&body)
		res := ValidatePasswordRequirements(body["password"])
		writeJSON(w, http.StatusOK, res)
	})
}
