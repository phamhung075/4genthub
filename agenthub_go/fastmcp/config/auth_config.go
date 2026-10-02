package config

import (
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ShouldEnforceAuthentication is always true: authentication is always required.
func ShouldEnforceAuthentication() bool { return true }

// ValidateSecurityRequirements reports the security status; getenv nil uses the process
// environment.
func ValidateSecurityRequirements(getenv func(string) string) *entities.OrderedMap[any] {
	if getenv == nil {
		getenv = os.Getenv
	}
	env := tmvo.PyLower(getenv("ENVIRONMENT"))
	issues := []string{}
	switch tmvo.PyLower(getenv("ALLOW_DEFAULT_USER")) {
	case "true", "1", "yes", "on":
		issues = append(issues, "ALLOW_DEFAULT_USER environment variable is set")
	}
	if env == "" {
		env = "unknown"
	}
	m := entities.NewOrderedMap[any]()
	m.Set("authentication_required", true)
	m.Set("legacy_config_issues", issues)
	m.Set("environment", env)
	m.Set("secure", len(issues) == 0)
	return m
}
