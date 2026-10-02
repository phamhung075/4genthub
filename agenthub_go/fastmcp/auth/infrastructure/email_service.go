// Email Service for Authentication Workflows
// (Python auth/infrastructure/email_service.py).
//
// smtplib maps to net/smtp + crypto/tls; the jinja2 templates are embedded here and
// rendered by a small renderer (see EmailTemplateEngine) that reproduces the exact output
// of the built-in templates. Logging calls are dropped. Template files are still written
// to the templates directory when missing, and an existing file wins over the built-in
// string, like Jinja2's FileSystemLoader.

package infrastructure

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"net"
	"net/smtp"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// selfHostedIPPattern is the `re.search(r"\d+\.\d+\.\d+\.\d+", host)` check shared by
// this module and supabase_auth.go.
var selfHostedIPPattern = regexp.MustCompile(`\d+\.\d+\.\d+\.\d+`)

// EmailConfig is the EmailConfig dataclass.
type EmailConfig struct {
	SMTPHost          string
	SMTPPort          int
	SMTPUsername      string
	SMTPPassword      string
	SMTPFrom          string
	SMTPFromName      string
	SMTPTLS           bool
	SMTPSecure        bool
	SMTPRequireTLS    bool
	SMTPAuth          bool
	ConnectionTimeout int
	GreetingTimeout   int
	SocketTimeout     int
}

// NewEmailConfig builds the required fields and applies the dataclass defaults.
func NewEmailConfig(smtpHost string, smtpPort int, smtpUsername, smtpPassword, smtpFrom, smtpFromName string) EmailConfig {
	return EmailConfig{
		SMTPHost:          smtpHost,
		SMTPPort:          smtpPort,
		SMTPUsername:      smtpUsername,
		SMTPPassword:      smtpPassword,
		SMTPFrom:          smtpFrom,
		SMTPFromName:      smtpFromName,
		SMTPTLS:           true,
		SMTPSecure:        false,
		SMTPRequireTLS:    true,
		SMTPAuth:          true,
		ConnectionTimeout: 10000,
		GreetingTimeout:   5000,
		SocketTimeout:     10000,
	}
}

// EmailMessage is the EmailMessage dataclass.
type EmailMessage struct {
	ToEmail      string
	ToName       *string
	Subject      string
	HTMLBody     string
	TextBody     string
	Template     *string
	TemplateData map[string]any
	Attachments  []map[string]any
}

// EmailResult is the EmailResult dataclass.
type EmailResult struct {
	Success      bool
	MessageID    *string
	ErrorMessage *string
	Recipient    *string
}

// stringPtr is a small helper shared by the infrastructure package.
func stringPtr(s string) *string { return &s }

// TokenManager manages email verification and password reset tokens.
type TokenManager struct{}

// GenerateToken is secrets.token_urlsafe(length).
func (TokenManager) GenerateToken(length int) string {
	if length < 0 {
		length = 0
	}
	b := make([]byte, length)
	if _, err := rand.Read(b); err != nil {
		return ""
	}
	return base64.RawURLEncoding.EncodeToString(b)
}

// GenerateVerificationToken is generate_verification_token: the metadata dict
// (token, email, type, expires_at, hash, created_at).
func (TokenManager) GenerateVerificationToken(email string, tokenType string) *entities.OrderedMap[any] {
	tm := TokenManager{}
	token := tm.GenerateToken(32)
	expiresAt := time.Now().UTC().Add(24 * time.Hour)
	sum := sha256.Sum256([]byte(email + ":" + token + ":" + tokenType))
	out := entities.NewOrderedMap[any]()
	out.Set("token", token)
	out.Set("email", email)
	out.Set("type", tokenType)
	out.Set("expires_at", expiresAt)
	out.Set("hash", hex.EncodeToString(sum[:]))
	out.Set("created_at", time.Now().UTC())
	return out
}

// ValidateToken is validate_token.
func (TokenManager) ValidateToken(token, email, tokenHash, tokenType string) bool {
	sum := sha256.Sum256([]byte(email + ":" + token + ":" + tokenType))
	return hex.EncodeToString(sum[:]) == tokenHash
}

// EmailTemplateEngine handles email template rendering.
type EmailTemplateEngine struct {
	TemplatesDir string
}

var builtinEmailTemplateNames = []string{
	"verification.html",
	"password_reset.html",
	"password_changed.html",
	"welcome.html",
	"base.html",
}

var builtinEmailTemplates = map[string]string{
	"verification.html":     emailVerificationTemplate,
	"password_reset.html":   emailPasswordResetTemplate,
	"password_changed.html": emailPasswordChangedTemplate,
	"welcome.html":          emailWelcomeTemplate,
	"base.html":             emailBaseTemplate,
}

// NewEmailTemplateEngine builds the engine over templatesDir (nil -> the default path).
func NewEmailTemplateEngine(templatesDir *string) *EmailTemplateEngine {
	dir := defaultEmailTemplatesDir()
	if templatesDir != nil {
		dir = *templatesDir
	}
	_ = os.MkdirAll(dir, 0o755)
	e := &EmailTemplateEngine{TemplatesDir: dir}
	e.ensureDefaultTemplates()
	return e
}

// defaultEmailTemplatesDir is the analogue of os.path.dirname(__file__)/../../../../templates/email,
// rooted at the Go module (agenthub_go/templates/email).
func defaultEmailTemplatesDir() string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return filepath.Join("templates", "email")
	}
	return filepath.Join(filepath.Dir(file), "..", "..", "..", "templates", "email")
}

// ensureDefaultTemplates creates the built-in templates when missing.
func (e *EmailTemplateEngine) ensureDefaultTemplates() {
	for _, name := range builtinEmailTemplateNames {
		path := filepath.Join(e.TemplatesDir, name)
		if _, err := os.Stat(path); err == nil {
			continue
		}
		_ = os.WriteFile(path, []byte(builtinEmailTemplates[name]), 0o644)
	}
}

// loadTemplate prefers an existing file, then the built-in string.
func (e *EmailTemplateEngine) loadTemplate(name string) (string, error) {
	if b, err := os.ReadFile(filepath.Join(e.TemplatesDir, name)); err == nil {
		return string(b), nil
	}
	if t, ok := builtinEmailTemplates[name]; ok {
		return t, nil
	}
	return "", fmt.Errorf("TemplateNotFound: %s", name)
}

// RenderTemplate is render_template(template_name, **context).
func (e *EmailTemplateEngine) RenderTemplate(templateName string, context map[string]any) (string, error) {
	text, err := e.loadTemplate(templateName)
	if err != nil {
		return "", err
	}
	return e.renderTemplateText(text, context), nil
}

var (
	emailExtendsRe = regexp.MustCompile(`\{%\s*extends\s+"([^"]+)"\s*%\}`)
	emailBlockRe   = regexp.MustCompile(`(?s)\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}`)
	emailIfRe      = regexp.MustCompile(`(?s)\{%\s*if\s+([^%]+?)\s*%\}(.*?)\{%\s*endif\s*%\}`)
	emailExprRe    = regexp.MustCompile(`\{\{\s*(.*?)\s*\}\}`)
)

func (e *EmailTemplateEngine) renderTemplateText(text string, context map[string]any) string {
	if m := emailExtendsRe.FindStringSubmatch(text); m != nil {
		if parent, err := e.loadTemplate(m[1]); err == nil {
			blocks := map[string]string{}
			for _, b := range emailBlockRe.FindAllStringSubmatch(text, -1) {
				blocks[b[1]] = b[2]
			}
			substituted := emailBlockRe.ReplaceAllStringFunc(parent, func(match string) string {
				sub := emailBlockRe.FindStringSubmatch(match)
				if body, ok := blocks[sub[1]]; ok {
					return body
				}
				return sub[2]
			})
			return renderEmailBody(substituted, context)
		}
	}
	return renderEmailBody(text, context)
}

func renderEmailBody(tpl string, context map[string]any) string {
	tpl = emailBlockRe.ReplaceAllStringFunc(tpl, func(match string) string {
		sub := emailBlockRe.FindStringSubmatch(match)
		return renderEmailBody(sub[2], context)
	})
	for {
		loc := emailIfRe.FindStringSubmatchIndex(tpl)
		if loc == nil {
			break
		}
		expr := strings.TrimSpace(tpl[loc[2]:loc[3]])
		body := tpl[loc[4]:loc[5]]
		replacement := ""
		if value_objects.PyTruthy(evalEmailExpr(expr, context)) {
			replacement = renderEmailBody(body, context)
		}
		tpl = tpl[:loc[0]] + replacement + tpl[loc[1]:]
	}
	return emailExprRe.ReplaceAllStringFunc(tpl, func(match string) string {
		sub := emailExprRe.FindStringSubmatch(match)
		return htmlEscapeJinja(emailStringify(evalEmailExpr(sub[1], context)))
	})
}

// evalEmailExpr evaluates the limited expressions used by the templates: `name` or
// `name or "literal"`.
func evalEmailExpr(expr string, context map[string]any) any {
	expr = strings.TrimSpace(expr)
	if i := strings.Index(expr, " or "); i >= 0 {
		name := strings.TrimSpace(expr[:i])
		literal := strings.Trim(strings.TrimSpace(expr[i+4:]), `"'`)
		if v := context[name]; value_objects.PyTruthy(v) {
			return v
		}
		return literal
	}
	return context[expr]
}

// emailStringify mirrors Jinja2's output of a value (Undefined / None render as "").
func emailStringify(v any) string {
	switch x := v.(type) {
	case nil:
		return ""
	case string:
		return x
	case bool:
		if x {
			return "True"
		}
		return "False"
	case int:
		return strconv.Itoa(x)
	case int64:
		return strconv.FormatInt(x, 10)
	case float64:
		return value_objects.PyStr(x)
	default:
		return value_objects.PyStr(v)
	}
}

// htmlEscapeJinja is markupsafe.escape (autoescape on all .html templates).
func htmlEscapeJinja(s string) string {
	return strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		"'", "&#39;",
		`"`, "&#34;",
	).Replace(s)
}

// SMTPEmailService is the SMTP-based email service.
type SMTPEmailService struct {
	Config         EmailConfig
	TemplateEngine *EmailTemplateEngine
	TokenManager   TokenManager
}

// NewSMTPEmailService is __init__; a nil config loads the environment.
func NewSMTPEmailService(config *EmailConfig) (*SMTPEmailService, error) {
	cfg := EmailConfig{}
	if config == nil {
		var err error
		cfg, err = loadEmailConfigFromEnv()
		if err != nil {
			return nil, err
		}
	} else {
		cfg = *config
	}
	svc := &SMTPEmailService{
		Config:         cfg,
		TemplateEngine: NewEmailTemplateEngine(nil),
		TokenManager:   TokenManager{},
	}
	if err := svc.validateConfig(); err != nil {
		return nil, err
	}
	return svc, nil
}

// loadEmailConfigFromEnv is _load_config_from_env.
func loadEmailConfigFromEnv() (EmailConfig, error) {
	port, err := strconv.Atoi(getenvDefault("SMTP_PORT", "587"))
	if err != nil {
		return EmailConfig{}, value_objects.ValueErrorf("invalid literal for int() with base 10: %s", getenvDefault("SMTP_PORT", "587"))
	}
	connectionTimeout, err := strconv.Atoi(getenvDefault("SMTP_CONNECTION_TIMEOUT", "10000"))
	if err != nil {
		return EmailConfig{}, value_objects.ValueErrorf("invalid literal for int() with base 10: %s", getenvDefault("SMTP_CONNECTION_TIMEOUT", "10000"))
	}
	greetingTimeout, err := strconv.Atoi(getenvDefault("SMTP_GREETING_TIMEOUT", "5000"))
	if err != nil {
		return EmailConfig{}, value_objects.ValueErrorf("invalid literal for int() with base 10: %s", getenvDefault("SMTP_GREETING_TIMEOUT", "5000"))
	}
	socketTimeout, err := strconv.Atoi(getenvDefault("SMTP_SOCKET_TIMEOUT", "10000"))
	if err != nil {
		return EmailConfig{}, value_objects.ValueErrorf("invalid literal for int() with base 10: %s", getenvDefault("SMTP_SOCKET_TIMEOUT", "10000"))
	}
	return EmailConfig{
		SMTPHost:          getenvDefault("SMTP_HOST", "localhost"),
		SMTPPort:          port,
		SMTPUsername:      getenvDefault("SMTP_USERNAME", ""),
		SMTPPassword:      getenvDefault("SMTP_PASSWORD", ""),
		SMTPFrom:          getenvDefault("SMTP_FROM", "noreply@example.com"),
		SMTPFromName:      getenvDefault("SMTP_FROM_NAME", "Oracle Server"),
		SMTPTLS:           envBoolTrue("SMTP_TLS", "true"),
		SMTPSecure:        envBoolTrue("SMTP_SECURE", "false"),
		SMTPRequireTLS:    envBoolTrue("SMTP_REQUIRE_TLS", "true"),
		SMTPAuth:          envBoolTrue("SMTP_AUTH", "true"),
		ConnectionTimeout: connectionTimeout,
		GreetingTimeout:   greetingTimeout,
		SocketTimeout:     socketTimeout,
	}, nil
}

func getenvDefault(name, def string) string {
	if v, ok := os.LookupEnv(name); ok {
		return v
	}
	return def
}

func envBoolTrue(name, def string) bool {
	switch strings.ToLower(getenvDefault(name, def)) {
	case "true", "1", "yes":
		return true
	}
	return false
}

// validateConfig is _validate_config.
func (s *SMTPEmailService) validateConfig() error {
	if s.Config.SMTPHost == "" {
		return value_objects.ValueErrorf("SMTP_HOST is required")
	}
	if s.Config.SMTPUsername == "" {
		return value_objects.ValueErrorf("SMTP_USERNAME is required")
	}
	if s.Config.SMTPPassword == "" {
		return value_objects.ValueErrorf("SMTP_PASSWORD is required")
	}
	if s.Config.SMTPFrom == "" {
		return value_objects.ValueErrorf("SMTP_FROM is required")
	}
	return nil
}

// SendEmail is send_email.
func (s *SMTPEmailService) SendEmail(ctx context.Context, message *EmailMessage) EmailResult {
	if message.Template != nil && *message.Template != "" && message.TemplateData != nil {
		html, err := s.TemplateEngine.RenderTemplate(*message.Template, message.TemplateData)
		if err != nil {
			return EmailResult{
				Success:      false,
				ErrorMessage: stringPtr("Template rendering error: " + err.Error()),
				Recipient:    stringPtr(message.ToEmail),
			}
		}
		message.HTMLBody = html
	}

	raw, err := buildMIMEMessage(message, s.Config)
	if err != nil {
		msg := err.Error()
		return EmailResult{Success: false, ErrorMessage: &msg, Recipient: stringPtr(message.ToEmail)}
	}
	return s.sendSMTPMessage(ctx, raw, message.ToEmail)
}

// sendSMTPMessage is _send_smtp_message.
func (s *SMTPEmailService) sendSMTPMessage(ctx context.Context, raw []byte, recipient string) EmailResult {
	client, err := s.openSMTPClient(ctx)
	if err != nil {
		return smtpErrorResult(err, recipient)
	}
	defer client.Close()

	if err := client.Mail(s.Config.SMTPFrom); err != nil {
		return smtpErrorResult(err, recipient)
	}
	if err := client.Rcpt(recipient); err != nil {
		return smtpErrorResult(err, recipient)
	}
	w, err := client.Data()
	if err != nil {
		return smtpErrorResult(err, recipient)
	}
	if _, err := w.Write(raw); err != nil {
		_ = w.Close()
		return smtpErrorResult(err, recipient)
	}
	if err := w.Close(); err != nil {
		return smtpErrorResult(err, recipient)
	}
	if err := client.Quit(); err != nil {
		return smtpErrorResult(err, recipient)
	}
	return EmailResult{Success: true, Recipient: &recipient}
}

// openSMTPClient connects (SMTP_SSL when secure), starttls and authenticates.
func (s *SMTPEmailService) openSMTPClient(ctx context.Context) (*smtp.Client, error) {
	isSelfHosted := selfHostedIPPattern.MatchString(s.Config.SMTPHost)
	tlsConfig := &tls.Config{ServerName: s.Config.SMTPHost}
	if isSelfHosted {
		tlsConfig.InsecureSkipVerify = true
	}
	timeout := time.Duration(s.Config.ConnectionTimeout) * time.Millisecond
	addr := net.JoinHostPort(s.Config.SMTPHost, strconv.Itoa(s.Config.SMTPPort))

	var client *smtp.Client
	if s.Config.SMTPSecure {
		dialer := &tls.Dialer{NetDialer: &net.Dialer{Timeout: timeout}, Config: tlsConfig}
		conn, err := dialer.DialContext(ctx, "tcp", addr)
		if err != nil {
			return nil, err
		}
		client, err = smtp.NewClient(conn, s.Config.SMTPHost)
		if err != nil {
			return nil, err
		}
	} else {
		conn, err := (&net.Dialer{Timeout: timeout}).DialContext(ctx, "tcp", addr)
		if err != nil {
			return nil, err
		}
		client, err = smtp.NewClient(conn, s.Config.SMTPHost)
		if err != nil {
			return nil, err
		}
		if s.Config.SMTPTLS || s.Config.SMTPRequireTLS {
			if err := client.StartTLS(tlsConfig); err != nil {
				client.Close()
				return nil, err
			}
		}
	}

	if s.Config.SMTPAuth {
		auth := smtp.PlainAuth("", s.Config.SMTPUsername, s.Config.SMTPPassword, s.Config.SMTPHost)
		if err := client.Auth(auth); err != nil {
			client.Close()
			return nil, err
		}
	}
	return client, nil
}

// smtpErrorResult applies the user-friendly message mapping.
func smtpErrorResult(err error, recipient string) EmailResult {
	msg := err.Error()
	lower := strings.ToLower(msg)
	switch {
	case strings.Contains(lower, "authentication failed"):
		msg = "SMTP authentication failed. Please check credentials."
	case strings.Contains(lower, "connection refused"):
		msg = "Cannot connect to SMTP server. Please check host and port."
	case strings.Contains(lower, "timeout"):
		msg = "SMTP connection timeout. Please try again."
	}
	return EmailResult{Success: false, ErrorMessage: &msg, Recipient: &recipient}
}

// buildMIMEMessage builds the multipart/alternative message (attachments included inside
// the alternative container, like Python's MIMEMultipart("alternative")).
func buildMIMEMessage(message *EmailMessage, cfg EmailConfig) ([]byte, error) {
	var b bytes.Buffer
	boundary := mimeBoundary()
	from := fmt.Sprintf("%s <%s>", cfg.SMTPFromName, cfg.SMTPFrom)
	to := "<" + message.ToEmail + ">"
	if message.ToName != nil && *message.ToName != "" {
		to = *message.ToName + " <" + message.ToEmail + ">"
	}
	fmt.Fprintf(&b, "From: %s\r\n", from)
	fmt.Fprintf(&b, "To: %s\r\n", to)
	fmt.Fprintf(&b, "Subject: %s\r\n", message.Subject)
	b.WriteString("MIME-Version: 1.0\r\n")
	fmt.Fprintf(&b, "Content-Type: multipart/alternative; boundary=\"%s\"\r\n", boundary)
	b.WriteString("\r\n")

	writeTextPart := func(contentType, body string) {
		b.WriteString("--" + boundary + "\r\n")
		fmt.Fprintf(&b, "Content-Type: %s; charset=\"utf-8\"\r\n", contentType)
		b.WriteString("MIME-Version: 1.0\r\n")
		b.WriteString("Content-Transfer-Encoding: base64\r\n\r\n")
		b.WriteString(wrapBase64(base64.StdEncoding.EncodeToString([]byte(body))))
		b.WriteString("\r\n")
	}
	if message.TextBody != "" {
		writeTextPart("text/plain", message.TextBody)
	}
	if message.HTMLBody != "" {
		writeTextPart("text/html", message.HTMLBody)
	}
	for _, attachment := range message.Attachments {
		data, err := os.ReadFile(fmt.Sprint(attachment["path"]))
		if err != nil {
			continue
		}
		filename := "attachment"
		if v, ok := attachment["filename"]; ok {
			filename = fmt.Sprint(v)
		}
		b.WriteString("--" + boundary + "\r\n")
		b.WriteString("Content-Type: application/octet-stream\r\n")
		b.WriteString("MIME-Version: 1.0\r\n")
		b.WriteString("Content-Transfer-Encoding: base64\r\n")
		fmt.Fprintf(&b, "Content-Disposition: attachment; filename= %s\r\n\r\n", filename)
		b.WriteString(wrapBase64(base64.StdEncoding.EncodeToString(data)))
		b.WriteString("\r\n")
	}
	b.WriteString("--" + boundary + "--\r\n")
	return b.Bytes(), nil
}

func mimeBoundary() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "boundary"
	}
	return "===============" + hex.EncodeToString(b) + "=="
}

func wrapBase64(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i += 76 {
		end := i + 76
		if end > len(s) {
			end = len(s)
		}
		b.WriteString(s[i:end])
		b.WriteString("\r\n")
	}
	return b.String()
}

// SendVerificationEmail sends the verification email.
func (s *SMTPEmailService) SendVerificationEmail(ctx context.Context, email string, userName *string, verificationURL *string) EmailResult {
	tokenData := s.TokenManager.GenerateVerificationToken(email, "verification")
	url := ""
	if verificationURL != nil {
		url = *verificationURL
	}
	if url == "" {
		baseURL := getenvDefault("FRONTEND_URL", "http://localhost:3800")
		url = fmt.Sprintf("%s/auth/verify?token=%v&email=%s", baseURL, tokenData.GetAny("token"), email)
	}
	message := &EmailMessage{
		ToEmail:  email,
		ToName:   userName,
		Subject:  "Verify your email address",
		Template: stringPtr("verification.html"),
		TemplateData: map[string]any{
			"user_name":        userName,
			"verification_url": url,
			"company_name":     getenvDefault("SMTP_FROM_NAME", "Oracle Server"),
			"current_year":     time.Now().Year(),
		},
	}
	return s.SendEmail(ctx, message)
}

// SendPasswordResetEmail sends the password reset email.
func (s *SMTPEmailService) SendPasswordResetEmail(ctx context.Context, email string, userName *string, resetURL *string) EmailResult {
	tokenData := s.TokenManager.GenerateVerificationToken(email, "password_reset")
	url := ""
	if resetURL != nil {
		url = *resetURL
	}
	if url == "" {
		baseURL := getenvDefault("FRONTEND_URL", "http://localhost:3800")
		url = fmt.Sprintf("%s/auth/reset-password?token=%v&email=%s", baseURL, tokenData.GetAny("token"), email)
	}
	message := &EmailMessage{
		ToEmail:  email,
		ToName:   userName,
		Subject:  "Reset your password",
		Template: stringPtr("password_reset.html"),
		TemplateData: map[string]any{
			"user_name":    userName,
			"reset_url":    url,
			"company_name": getenvDefault("SMTP_FROM_NAME", "Oracle Server"),
			"current_year": time.Now().Year(),
		},
	}
	return s.SendEmail(ctx, message)
}

// SendPasswordChangedEmail sends the password changed confirmation.
func (s *SMTPEmailService) SendPasswordChangedEmail(ctx context.Context, email string, userName, ipAddress, userAgent *string) EmailResult {
	message := &EmailMessage{
		ToEmail:  email,
		ToName:   userName,
		Subject:  "Password changed successfully",
		Template: stringPtr("password_changed.html"),
		TemplateData: map[string]any{
			"user_name":    userName,
			"change_date":  time.Now().Format("2006-01-02 15:04:05") + " UTC",
			"ip_address":   ipAddress,
			"user_agent":   userAgent,
			"company_name": getenvDefault("SMTP_FROM_NAME", "Oracle Server"),
			"current_year": time.Now().Year(),
		},
	}
	return s.SendEmail(ctx, message)
}

// SendWelcomeEmail sends the welcome email after verification.
func (s *SMTPEmailService) SendWelcomeEmail(ctx context.Context, email string, userName *string, dashboardURL *string) EmailResult {
	url := ""
	if dashboardURL != nil {
		url = *dashboardURL
	}
	if url == "" {
		url = getenvDefault("FRONTEND_URL", "http://localhost:3800")
	}
	message := &EmailMessage{
		ToEmail:  email,
		ToName:   userName,
		Subject:  "Welcome! Your account is ready",
		Template: stringPtr("welcome.html"),
		TemplateData: map[string]any{
			"user_name":     userName,
			"dashboard_url": url,
			"company_name":  getenvDefault("SMTP_FROM_NAME", "Oracle Server"),
			"current_year":  time.Now().Year(),
		},
	}
	return s.SendEmail(ctx, message)
}

// TestConnection is test_connection.
func (s *SMTPEmailService) TestConnection(ctx context.Context) EmailResult {
	client, err := s.openSMTPClient(ctx)
	if err != nil {
		msg := err.Error()
		return EmailResult{Success: false, ErrorMessage: &msg, Recipient: stringPtr("test")}
	}
	_ = client.Quit()
	return EmailResult{Success: true, MessageID: stringPtr("connection_test"), Recipient: stringPtr("test")}
}

var emailServiceInstance *SMTPEmailService

// GetEmailService is get_email_service (the global instance).
func GetEmailService() (*SMTPEmailService, error) {
	if emailServiceInstance == nil {
		s, err := NewSMTPEmailService(nil)
		if err != nil {
			return nil, err
		}
		emailServiceInstance = s
	}
	return emailServiceInstance, nil
}

// SendVerificationEmail is the module-level convenience function.
func SendVerificationEmail(ctx context.Context, email string, userName *string) (EmailResult, error) {
	service, err := GetEmailService()
	if err != nil {
		return EmailResult{}, err
	}
	return service.SendVerificationEmail(ctx, email, userName, nil), nil
}

// SendPasswordResetEmail is the module-level convenience function.
func SendPasswordResetEmail(ctx context.Context, email string, userName *string) (EmailResult, error) {
	service, err := GetEmailService()
	if err != nil {
		return EmailResult{}, err
	}
	return service.SendPasswordResetEmail(ctx, email, userName, nil), nil
}

// SendPasswordChangedEmail is the module-level convenience function.
func SendPasswordChangedEmail(ctx context.Context, email string, userName *string) (EmailResult, error) {
	service, err := GetEmailService()
	if err != nil {
		return EmailResult{}, err
	}
	return service.SendPasswordChangedEmail(ctx, email, userName, nil, nil), nil
}

// SendWelcomeEmail is the module-level convenience function.
func SendWelcomeEmail(ctx context.Context, email string, userName *string) (EmailResult, error) {
	service, err := GetEmailService()
	if err != nil {
		return EmailResult{}, err
	}
	return service.SendWelcomeEmail(ctx, email, userName, nil), nil
}

// The built-in templates below are copied verbatim from email_service.py; the renderer
// reproduces Jinja2's output for them.

const emailBaseTemplate = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title or "Oracle Server" }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 2px solid #007cba; padding-bottom: 20px; margin-bottom: 20px; }
        .logo { color: #007cba; font-size: 24px; font-weight: bold; }
        .content { margin: 20px 0; }
        .button { display: inline-block; background: #007cba; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .button:hover { background: #005a87; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 4px; margin: 15px 0; }
        .code { font-family: monospace; background: #f8f9fa; padding: 8px 12px; border-radius: 4px; letter-spacing: 2px; font-size: 18px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{ company_name or "Oracle Server" }}</div>
            {% if subtitle %}<p style="margin: 10px 0 0 0; color: #666;">{{ subtitle }}</p>{% endif %}
        </div>
        
        <div class="content">
            {% block content %}{% endblock %}
        </div>
        
        <div class="footer">
            <p>This email was sent from {{ company_name or "Oracle Server" }}.</p>
            <p>If you didn't request this email, please ignore it or contact support.</p>
            <p>&copy; {{ current_year or "2025" }} {{ company_name or "Oracle Server" }}. All rights reserved.</p>
        </div>
    </div>
</body>
</html>`

const emailVerificationTemplate = `{% extends "base.html" %}

{% block content %}
<h2>Welcome to {{ company_name or "Oracle Server" }}!</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>Thank you for signing up! To complete your registration, please verify your email address by clicking the button below:</p>

<p style="text-align: center;">
    <a href="{{ verification_url }}" class="button">Verify Email Address</a>
</p>

<p>Or copy and paste this link into your browser:</p>
<p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{{ verification_url }}</p>

<div class="warning">
    <strong>Security Notice:</strong> This verification link will expire in 24 hours for security reasons.
</div>

<p>If you didn't create an account with us, please ignore this email.</p>

<p>Best regards,<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}`

const emailPasswordResetTemplate = `{% extends "base.html" %}

{% block content %}
<h2>Password Reset Request</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>We received a request to reset your password for your {{ company_name or "Oracle Server" }} account.</p>

<p>Click the button below to reset your password:</p>

<p style="text-align: center;">
    <a href="{{ reset_url }}" class="button">Reset Password</a>
</p>

<p>Or copy and paste this link into your browser:</p>
<p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 4px;">{{ reset_url }}</p>

<div class="warning">
    <strong>Security Notice:</strong> This reset link will expire in 1 hour for security reasons.
</div>

<p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>

<p>Best regards,<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}`

const emailPasswordChangedTemplate = `{% extends "base.html" %}

{% block content %}
<h2>Password Changed Successfully</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>This email confirms that your password for {{ company_name or "Oracle Server" }} has been successfully changed.</p>

<p><strong>Change Details:</strong></p>
<ul>
    <li>Date: {{ change_date or "Just now" }}</li>
    <li>IP Address: {{ ip_address or "Unknown" }}</li>
    <li>User Agent: {{ user_agent or "Unknown" }}</li>
</ul>

<div class="warning">
    <strong>Security Alert:</strong> If you didn't make this change, please contact our support team immediately.
</div>

<p>For your security, you may want to:</p>
<ul>
    <li>Review your recent account activity</li>
    <li>Enable two-factor authentication if available</li>
    <li>Use a unique, strong password</li>
</ul>

<p>Best regards,<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}`

const emailWelcomeTemplate = `{% extends "base.html" %}

{% block content %}
<h2>Welcome to {{ company_name or "Oracle Server" }}!</h2>

<p>Hello {{ user_name or "there" }},</p>

<p>Your email has been successfully verified and your account is now active!</p>

<p>Here are some things you can do to get started:</p>
<ul>
    <li>Complete your profile setup</li>
    <li>Explore the available features</li>
    <li>Join our community</li>
    <li>Contact support if you need help</li>
</ul>

<p style="text-align: center;">
    <a href="{{ dashboard_url or '#' }}" class="button">Get Started</a>
</p>

<p>If you have any questions, don't hesitate to reach out to our support team.</p>

<p>Welcome aboard!<br>The {{ company_name or "Oracle Server" }} Team</p>
{% endblock %}`
