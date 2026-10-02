package value_objects

import (
	"fmt"
	"regexp"
	"strings"
	"unicode/utf8"

	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// emailPattern is Email.EMAIL_PATTERN (simplified but effective).
var emailPattern = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

// Email is the validated, normalized (lower-cased, stripped) email value object.
type Email struct{ Value string }

// NewEmail validates and normalizes value (dataclass __post_init__).
func NewEmail(value string) (Email, error) {
	if value == "" {
		return Email{}, &tmvo.ValueError{Msg: "Email cannot be empty"}
	}
	v := tmvo.PyStrip(tmvo.PyLower(value))
	invalid := &tmvo.ValueError{Msg: fmt.Sprintf("Invalid email format: %s", v)}
	if !emailPattern.MatchString(v) {
		return Email{}, invalid
	}
	if strings.Contains(v, "..") || strings.Contains(v, "@.") {
		return Email{}, invalid
	}
	if utf8.RuneCountInString(v) > 254 { // max email length per RFC
		return Email{}, &tmvo.ValueError{Msg: "Email address too long"}
	}
	return Email{v}, nil
}

// EmailFromString is Email.from_string.
func EmailFromString(email string) (Email, error) { return NewEmail(email) }

// GetDomain is the part after the @.
func (e Email) GetDomain() string { return strings.SplitN(e.Value, "@", 2)[1] }

// GetLocalPart is the part before the @.
func (e Email) GetLocalPart() string { return strings.SplitN(e.Value, "@", 2)[0] }

func (e Email) String() string { return e.Value }
