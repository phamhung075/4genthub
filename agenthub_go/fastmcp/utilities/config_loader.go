package utilities

import (
	"bufio"
	"os"
	"path/filepath"
	"strings"
)

// DefaultEnvPath returns the machine-level path to the 4genthub configuration file (~/.config/4genthub/.env).
func DefaultEnvPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".config", "4genthub", ".env"), nil
}

// LoadEnv reads KEY=VALUE lines from the specified file and sets each variable
// that is NOT already in the environment. An existing value in os.Environ() wins.
// If the file does not exist, it silently succeeds without error.
func LoadEnv(path string) error {
	file, err := os.Open(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		name, value, found := strings.Cut(line, "=")
		if !found {
			continue
		}
		name = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(name), "export "))
		value = unquoteEnv(strings.TrimSpace(value))
		if name == "" {
			continue
		}
		if _, exists := os.LookupEnv(name); exists {
			continue
		}
		_ = os.Setenv(name, value)
	}
	return scanner.Err()
}

// LoadDefaultEnv loads the machine-level ~/.config/4genthub/.env first, then local .env if present.
func LoadDefaultEnv() {
	if defaultPath, err := DefaultEnvPath(); err == nil {
		_ = LoadEnv(defaultPath)
	}
	_ = LoadEnv(".env")
}

// ResolveConfigVar returns the value of the first matching environment variable,
// loading ~/.config/4genthub/.env if not already set.
func ResolveConfigVar(names ...string) string {
	for _, name := range names {
		if val := os.Getenv(name); val != "" {
			return val
		}
	}
	LoadDefaultEnv()
	for _, name := range names {
		if val := os.Getenv(name); val != "" {
			return val
		}
	}
	return ""
}

func unquoteEnv(value string) string {
	if len(value) >= 2 && (value[0] == '"' || value[0] == '\'') && value[len(value)-1] == value[0] {
		return value[1 : len(value)-1]
	}
	return value
}
