package utilities

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadEnv(t *testing.T) {
	tmpDir := t.TempDir()
	envPath := filepath.Join(tmpDir, ".env")

	content := `# Comment
KEY_ONE=val1
export KEY_TWO="val2"
KEY_THREE='val3'
`
	if err := os.WriteFile(envPath, []byte(content), 0o600); err != nil {
		t.Fatalf("failed to write test env: %v", err)
	}

	_ = os.Unsetenv("KEY_ONE")
	_ = os.Unsetenv("KEY_TWO")
	_ = os.Unsetenv("KEY_THREE")

	if err := LoadEnv(envPath); err != nil {
		t.Fatalf("LoadEnv failed: %v", err)
	}

	if os.Getenv("KEY_ONE") != "val1" {
		t.Errorf("KEY_ONE expected 'val1', got '%s'", os.Getenv("KEY_ONE"))
	}
	if os.Getenv("KEY_TWO") != "val2" {
		t.Errorf("KEY_TWO expected 'val2', got '%s'", os.Getenv("KEY_TWO"))
	}
	if os.Getenv("KEY_THREE") != "val3" {
		t.Errorf("KEY_THREE expected 'val3', got '%s'", os.Getenv("KEY_THREE"))
	}
}

func TestLoadEnvFillsEmptyAndKeepsNonEmpty(t *testing.T) {
	envPath := filepath.Join(t.TempDir(), ".env")
	if err := os.WriteFile(envPath, []byte("EMPTY_IN_ENV=from-file\nSET_IN_ENV=from-file\n"), 0o600); err != nil {
		t.Fatalf("failed to write test env: %v", err)
	}
	t.Setenv("EMPTY_IN_ENV", "")
	t.Setenv("SET_IN_ENV", "from-env")

	if err := LoadEnv(envPath); err != nil {
		t.Fatalf("LoadEnv failed: %v", err)
	}

	if got := os.Getenv("EMPTY_IN_ENV"); got != "from-file" {
		t.Errorf("EMPTY_IN_ENV expected 'from-file', got '%s'", got)
	}
	if got := os.Getenv("SET_IN_ENV"); got != "from-env" {
		t.Errorf("SET_IN_ENV expected 'from-env', got '%s'", got)
	}
}
