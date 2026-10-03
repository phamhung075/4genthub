package repositories

import (
	"fmt"
	"regexp"
)

// namePattern is OpenRig's pod/member id rule. Room slugs (pod ids) and seat keys
// (member ids) are written together in a qualified edge reference as "pod.member",
// so a dot or any other punctuation outside the pattern is invalid.
var namePattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`)

var (
	moduleSlugPattern = regexp.MustCompile(`^[a-z][a-z0-9-]*$`)
	semverPattern     = regexp.MustCompile(`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`)
	modelPattern      = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$`)
)

// ValidateRuntime accepts the runtimes seatrenderer can render.
func ValidateRuntime(runtime string) error {
	if runtime != "claude-code" && runtime != "codex" {
		return fmt.Errorf("runtime %q must be \"claude-code\" or \"codex\"", runtime)
	}
	return nil
}

// ValidateModel accepts an empty model (the runtime default) or a model id.
func ValidateModel(model string) error {
	if model != "" && !modelPattern.MatchString(model) {
		return fmt.Errorf("model %q must be empty or match %s", model, modelPattern)
	}
	return nil
}

// ValidateModuleSlug checks slug against the module slug rule.
func ValidateModuleSlug(slug string) error {
	if !moduleSlugPattern.MatchString(slug) {
		return fmt.Errorf("module slug %q must match %s", slug, moduleSlugPattern)
	}
	return nil
}

// ValidateConcreteVersion requires a concrete semver x.y.z; aliases such as "latest" are rejected.
func ValidateConcreteVersion(version string) error {
	if !semverPattern.MatchString(version) {
		return fmt.Errorf("version %q must be a concrete semver x.y.z", version)
	}
	return nil
}

// ValidateName checks value against the OpenRig name rule; kind ("room slug" or
// "seat key") names the field in the error.
func ValidateName(kind, value string) error {
	if !namePattern.MatchString(value) {
		return fmt.Errorf("%s %q must match %s", kind, value, namePattern)
	}
	return nil
}
