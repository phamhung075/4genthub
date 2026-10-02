package infrastructure

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// emailTemplateFixture holds the Jinja2-rendered outputs recorded from the Python
// templates; see testdata/email_templates.json.
type emailTemplateFixture struct {
	Comment  string            `json:"comment"`
	Expected map[string]string `json:"expected"`
}

func loadEmailTemplateFixture(t *testing.T) emailTemplateFixture {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("testdata", "email_templates.json"))
	if err != nil {
		t.Fatalf("read fixture: %v", err)
	}
	var fixture emailTemplateFixture
	if err := json.Unmarshal(raw, &fixture); err != nil {
		t.Fatalf("unmarshal fixture: %v", err)
	}
	return fixture
}

func TestEmailTemplateBuiltinsMatchJinja2(t *testing.T) {
	fixture := loadEmailTemplateFixture(t)
	tmp := t.TempDir()
	engine := NewEmailTemplateEngine(&tmp)

	cases := []struct {
		template string
		context  map[string]any
	}{
		{"verification.html", map[string]any{
			"user_name":        "Alice & Bob",
			"verification_url": "http://localhost:3800/auth/verify?token=a&email=x",
			"company_name":     "Oracle Server",
			"current_year":     2025,
		}},
		{"password_reset.html", map[string]any{
			"user_name":    nil,
			"reset_url":    "http://x/reset",
			"company_name": "Oracle Server",
			"current_year": 2025,
		}},
		{"password_changed.html", map[string]any{
			"user_name":    "Alice",
			"change_date":  "2025-01-02 03:04:05 UTC",
			"ip_address":   "1.2.3.4",
			"user_agent":   "ua",
			"company_name": "Oracle Server",
			"current_year": 2025,
		}},
		{"welcome.html", map[string]any{
			"user_name":    "Alice",
			"company_name": "Oracle Server",
			"current_year": 2025,
		}},
	}
	for _, tc := range cases {
		got, err := engine.RenderTemplate(tc.template, tc.context)
		if err != nil {
			t.Fatalf("RenderTemplate(%s): %v", tc.template, err)
		}
		want, ok := fixture.Expected[tc.template]
		if !ok {
			t.Fatalf("fixture missing %s", tc.template)
		}
		if got != want {
			t.Fatalf("%s mismatch\n--- got ---\n%s\n--- want ---\n%s", tc.template, got, want)
		}
	}
}

func TestEmailTemplateDefaultsWrittenAndFileOverrideWins(t *testing.T) {
	tmp := t.TempDir()
	engine := NewEmailTemplateEngine(&tmp)
	for _, name := range []string{"base.html", "verification.html", "password_reset.html", "password_changed.html", "welcome.html"} {
		if _, err := os.Stat(filepath.Join(tmp, name)); err != nil {
			t.Fatalf("default template %s not written: %v", name, err)
		}
	}

	custom := "Hello {{ user_name or \"there\" }} <{{ company_name }}>"
	if err := os.WriteFile(filepath.Join(tmp, "welcome.html"), []byte(custom), 0o644); err != nil {
		t.Fatal(err)
	}
	got, err := engine.RenderTemplate("welcome.html", map[string]any{"user_name": "Bob", "company_name": "A&B"})
	if err != nil {
		t.Fatal(err)
	}
	if got != "Hello Bob <A&amp;B>" {
		t.Fatalf("file override not used/escaped: %q", got)
	}
}

func TestEmailTemplateMissingReturnsError(t *testing.T) {
	engine := NewEmailTemplateEngine(new(string))
	if _, err := engine.RenderTemplate("nope.html", nil); err == nil {
		t.Fatal("expected TemplateNotFound error")
	}
}

func TestTokenManagerHashMatchesPythonFormula(t *testing.T) {
	var tm TokenManager
	tokenData := tm.GenerateVerificationToken("a@b.com", "verification")
	token, _ := tokenData.Get("token")
	hash, _ := tokenData.Get("hash")
	email, _ := tokenData.Get("email")
	tokenType, _ := tokenData.Get("type")
	if !tm.ValidateToken(token.(string), email.(string), hash.(string), tokenType.(string)) {
		t.Fatal("ValidateToken rejected its own token")
	}
	if tm.ValidateToken(token.(string), email.(string), "deadbeef", tokenType.(string)) {
		t.Fatal("ValidateToken accepted a wrong hash")
	}
	if tokenData.GetAny("expires_at") == nil || tokenData.GetAny("created_at") == nil {
		t.Fatal("token metadata missing timestamps")
	}
	if len(tm.GenerateToken(32)) != 43 {
		t.Fatalf("token_urlsafe(32) length = %d, want 43", len(tm.GenerateToken(32)))
	}
}

func TestEmailConfigFromEnvAndValidation(t *testing.T) {
	t.Setenv("SMTP_HOST", "mail.example.com")
	t.Setenv("SMTP_PORT", "2525")
	t.Setenv("SMTP_USERNAME", "user")
	t.Setenv("SMTP_PASSWORD", "pass")
	t.Setenv("SMTP_FROM", "no-reply@example.com")
	t.Setenv("SMTP_FROM_NAME", "Example")
	t.Setenv("SMTP_TLS", "yes")
	t.Setenv("SMTP_SECURE", "1")
	t.Setenv("SMTP_REQUIRE_TLS", "false")
	t.Setenv("SMTP_AUTH", "true")
	t.Setenv("SMTP_CONNECTION_TIMEOUT", "1234")
	t.Setenv("SMTP_GREETING_TIMEOUT", "2345")
	t.Setenv("SMTP_SOCKET_TIMEOUT", "3456")

	cfg, err := loadEmailConfigFromEnv()
	if err != nil {
		t.Fatal(err)
	}
	if cfg.SMTPHost != "mail.example.com" || cfg.SMTPPort != 2525 {
		t.Fatalf("host/port = %q/%d", cfg.SMTPHost, cfg.SMTPPort)
	}
	if !cfg.SMTPTLS || !cfg.SMTPSecure || cfg.SMTPRequireTLS || !cfg.SMTPAuth {
		t.Fatalf("tls flags = %+v", cfg)
	}
	if cfg.ConnectionTimeout != 1234 || cfg.GreetingTimeout != 2345 || cfg.SocketTimeout != 3456 {
		t.Fatalf("timeouts = %+v", cfg)
	}

	missing := NewEmailConfig("host", 587, "", "pass", "from", "name")
	svc := &SMTPEmailService{Config: missing}
	if err := svc.validateConfig(); err == nil || err.Error() != "SMTP_USERNAME is required" {
		t.Fatalf("validateConfig = %v", err)
	}
}

func TestSendEmailRendersTemplateBeforeSMTPFailure(t *testing.T) {
	fixture := loadEmailTemplateFixture(t)
	tmp := t.TempDir()
	cfg := NewEmailConfig("127.0.0.1", 1, "user", "pass", "from@example.com", "Sender")
	cfg.ConnectionTimeout = 1000
	service := &SMTPEmailService{
		Config:         cfg,
		TemplateEngine: NewEmailTemplateEngine(&tmp),
		TokenManager:   TokenManager{},
	}
	name := "verification.html"
	message := &EmailMessage{
		ToEmail:  "a@b.com",
		Subject:  "Verify your email address",
		Template: &name,
		TemplateData: map[string]any{
			"user_name":        "Alice & Bob",
			"verification_url": "http://localhost:3800/auth/verify?token=a&email=x",
			"company_name":     "Oracle Server",
			"current_year":     2025,
		},
	}
	result := service.SendEmail(context.Background(), message)
	if result.Success {
		t.Fatal("expected SMTP failure")
	}
	if message.HTMLBody != fixture.Expected[name] {
		t.Fatalf("HTMLBody not rendered from template\n--- got ---\n%s", message.HTMLBody)
	}
}
