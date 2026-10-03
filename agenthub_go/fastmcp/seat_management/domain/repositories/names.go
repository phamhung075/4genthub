package repositories

import (
	"fmt"
	"regexp"
)

// namePattern is OpenRig's pod/member id rule. Room slugs (pod ids) and seat keys
// (member ids) are written together in a qualified edge reference as "pod.member",
// so a dot or any other punctuation outside the pattern is invalid.
var namePattern = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`)

// ValidateName checks value against the OpenRig name rule; kind ("room slug" or
// "seat key") names the field in the error.
func ValidateName(kind, value string) error {
	if !namePattern.MatchString(value) {
		return fmt.Errorf("%s %q must match %s", kind, value, namePattern)
	}
	return nil
}
