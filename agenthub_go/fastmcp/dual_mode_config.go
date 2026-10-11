// Package fastmcp ports the top-level modules of the Python fastmcp package.
package fastmcp

import (
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// Runtime modes.
const (
	RuntimeHTTP  = "http"
	RuntimeStdio = "stdio"
)

// ModeEnv is the process state the mode detection reads, injectable for tests.
type ModeEnv struct {
	Getenv func(string) (string, bool)
	Exists func(path string) bool
	Cwd    string
}

// DefaultModeEnv reads the real process state.
func DefaultModeEnv() ModeEnv {
	cwd, _ := os.Getwd()
	return ModeEnv{Getenv: os.LookupEnv, Exists: func(p string) bool { _, err := os.Stat(p); return err == nil }, Cwd: cwd}
}

// DualModeConfig adapts to the runtime environment: stdio (local) or HTTP (Docker).
type DualModeConfig struct {
	RuntimeMode string
	ProjectRoot string
	env         ModeEnv
}

// NewDualModeConfig detects the runtime mode and project root.
func NewDualModeConfig(env ModeEnv) *DualModeConfig {
	c := &DualModeConfig{env: env}
	c.RuntimeMode = c.detectRuntimeMode()
	c.ProjectRoot = c.getProjectRoot()
	return c
}

func (c *DualModeConfig) has(key string) bool { _, ok := c.env.Getenv(key); return ok }

func (c *DualModeConfig) detectRuntimeMode() string {
	if c.has("CURSOR_RULES_DIR") || c.env.Exists("/.dockerenv") {
		return RuntimeHTTP
	}
	if v, _ := c.env.Getenv("FASTMCP_TRANSPORT"); v == "streamable-http" {
		return RuntimeHTTP
	}
	if c.env.Exists("/app") && !c.env.Exists("/home") {
		return RuntimeHTTP
	}
	return RuntimeStdio
}

// withParents is [current] + list(current.parents).
func withParents(current string) []string {
	out := []string{current}
	for p := current; utilities.PyParent(p) != p; {
		p = utilities.PyParent(p)
		out = append(out, p)
	}
	return out
}

func (c *DualModeConfig) getProjectRoot() string {
	if c.RuntimeMode == RuntimeHTTP {
		return "/app"
	}
	current := utilities.PyPath(c.env.Cwd)
	for _, p := range withParents(current) {
		if c.env.Exists(utilities.PyJoin(p, ".git")) {
			return p
		}
	}
	for _, p := range withParents(current) {
		for _, ind := range []string{"pyproject.toml", "src", "agenthub_go"} {
			if c.env.Exists(utilities.PyJoin(p, ind)) {
				return p
			}
		}
	}
	return current
}

// GetRulesDirectory returns the rules directory for the detected mode.
func (c *DualModeConfig) GetRulesDirectory() string {
	if c.RuntimeMode == RuntimeHTTP {
		if v, ok := c.env.Getenv("CURSOR_RULES_DIR"); ok {
			return utilities.PyPath(v)
		}
		return "/data/rules"
	}
	return utilities.PyJoin(c.ProjectRoot, "00_RULES")
}

func (c *DualModeConfig) GetDataDirectory() string {
	if c.RuntimeMode == RuntimeHTTP {
		return "/data"
	}
	return utilities.PyJoin(c.ProjectRoot, "data")
}

func (c *DualModeConfig) GetConfigDirectory() string {
	if c.RuntimeMode == RuntimeHTTP {
		return "/app/config"
	}
	return utilities.PyJoin(c.ProjectRoot, "config")
}

func (c *DualModeConfig) GetLogsDirectory() string {
	if v, ok := c.env.Getenv("LOG_DIR"); ok {
		return utilities.PyPath(v)
	}
	if c.RuntimeMode == RuntimeHTTP {
		return "/app/logs"
	}
	return utilities.PyJoin(c.ProjectRoot, "logs")
}

// GetEnvironmentConfig returns the environment-specific configuration.
func (c *DualModeConfig) GetEnvironmentConfig() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("runtime_mode", c.RuntimeMode)
	m.Set("project_root", c.ProjectRoot)
	m.Set("rules_directory", c.GetRulesDirectory())
	m.Set("data_directory", c.GetDataDirectory())
	m.Set("config_directory", c.GetConfigDirectory())
	m.Set("logs_directory", c.GetLogsDirectory())
	if c.RuntimeMode == RuntimeHTTP {
		auth, ok := c.env.Getenv("AUTH_ENABLED")
		if !ok {
			auth = "true"
		}
		m.Set("transport", "streamable-http")
		m.Set("host", "0.0.0.0")
		m.Set("port", 8000)
		m.Set("container_mode", true)
		m.Set("auth_enabled", tmvo.PyLower(auth) == "true")
	} else {
		m.Set("transport", "stdio")
		m.Set("container_mode", false)
		m.Set("auth_enabled", false)
	}
	return m
}

// ResolvePath resolves a path against a base directory type ("project", "rules", "data",
// "config", "logs"; anything else is "project"); absolute paths are returned as they are.
func (c *DualModeConfig) ResolvePath(path, baseType string) string {
	if utilities.PyIsAbs(path) {
		return utilities.PyPath(path)
	}
	base := c.ProjectRoot
	switch baseType {
	case "rules":
		base = c.GetRulesDirectory()
	case "data":
		base = c.GetDataDirectory()
	case "config":
		base = c.GetConfigDirectory()
	case "logs":
		base = c.GetLogsDirectory()
	}
	return utilities.PyJoin(base, path)
}

// DualMode is the process-wide instance, detected once at startup (Python: at import).
var DualMode = NewDualModeConfig(DefaultModeEnv())

func GetRuntimeMode() string    { return DualMode.RuntimeMode }
func GetRulesDirectory() string { return DualMode.GetRulesDirectory() }
func GetDataDirectory() string  { return DualMode.GetDataDirectory() }
func ResolvePath(path, baseType string) string {
	return DualMode.ResolvePath(path, baseType)
}
func IsHTTPMode() bool  { return DualMode.RuntimeMode == RuntimeHTTP }
func IsStdioMode() bool { return DualMode.RuntimeMode == RuntimeStdio }
