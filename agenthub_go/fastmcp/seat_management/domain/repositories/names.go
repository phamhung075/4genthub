package repositories

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"unicode/utf8"

	"agenthub/fastmcp/seat_management/domain/resolver"
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
	return resolver.CheckRuntime(runtime)
}

// ValidateModel accepts an empty model (the runtime default) or a model id.
func ValidateModel(model string) error {
	if model != "" && !modelPattern.MatchString(model) {
		return fmt.Errorf("model %q must be empty or match %s", model, modelPattern)
	}
	return nil
}

// MaxRoomNameLength bounds a room's display name. The rooms.name column is unbounded TEXT, so
// this domain rule is the only limit.
const MaxRoomNameLength = 200

// ValidateRoomName requires a non-empty name of at most MaxRoomNameLength characters.
func ValidateRoomName(name string) error {
	if strings.TrimSpace(name) == "" || utf8.RuneCountInString(name) > MaxRoomNameLength {
		return fmt.Errorf("room name must be 1 to %d characters", MaxRoomNameLength)
	}
	return nil
}

// ValidateOccupant checks the runtime and model of a seat's occupant together. Claude models
// run only on the claude-code runtime; claude-code also takes aliases such as "sonnet", so the
// check is one-directional.
func ValidateOccupant(runtime, model string) error {
	if err := ValidateRuntime(runtime); err != nil {
		return err
	}
	if err := ValidateModel(model); err != nil {
		return err
	}
	if runtime == resolver.RuntimeCodex && strings.HasPrefix(model, "claude-") {
		return fmt.Errorf("model %q is a Claude model and cannot run on the codex runtime", model)
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

// ParseModuleRef parses "slug@version" into a ModuleRef with a valid slug and a concrete version.
func ParseModuleRef(ref string) (resolver.ModuleRef, error) {
	slug, version, found := strings.Cut(ref, "@")
	if !found {
		return resolver.ModuleRef{}, fmt.Errorf("module ref %q must be slug@version", ref)
	}
	if err := ValidateModuleSlug(slug); err != nil {
		return resolver.ModuleRef{}, err
	}
	if err := ValidateConcreteVersion(version); err != nil {
		return resolver.ModuleRef{}, err
	}
	return resolver.ModuleRef{Slug: slug, Version: version}, nil
}

// NextPatchVersion returns version with its patch number incremented.
func NextPatchVersion(version string) (string, error) {
	if err := ValidateConcreteVersion(version); err != nil {
		return "", err
	}
	parts := strings.Split(version, ".")
	patch, err := strconv.Atoi(parts[2])
	if err != nil {
		return "", fmt.Errorf("version %q: %w", version, err)
	}
	return parts[0] + "." + parts[1] + "." + strconv.Itoa(patch+1), nil
}
