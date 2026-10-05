package services

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"math/big"
	"regexp"
	"strings"
	"unicode/utf8"

	"golang.org/x/crypto/bcrypt"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PasswordService hashes and verifies passwords with bcrypt.
const (
	DefaultRounds     = 12 // good balance between security and performance
	MinPasswordLength = 8
	MaxPasswordLength = 128

	lowercase   = "abcdefghijklmnopqrstuvwxyz"
	uppercase   = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	digits      = "0123456789"
	punctuation = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" // string.punctuation

	bcryptMaxBytes = 72
)

// errBcryptTooLong is bcrypt 5.x's ValueError text for passwords over 72 bytes.
const errBcryptTooLong = "password cannot be longer than 72 bytes, truncate manually if necessary (e.g. my_password[:72])"

// HashPassword hashes a password with bcrypt ($2b$, cost 12).
func HashPassword(password string) (string, error) {
	if err := validatePassword(password); err != nil {
		return "", err
	}
	if len(password) > bcryptMaxBytes {
		return "", &value_objects.ValueError{Msg: errBcryptTooLong}
	}
	h, err := bcrypt.GenerateFromPassword([]byte(password), DefaultRounds)
	if err != nil {
		return "", err
	}
	// x/crypto writes the $2a$ prefix; Python's bcrypt writes $2b$ (same algorithm).
	return "$2b$" + string(h[4:]), nil
}

// VerifyPassword reports whether password matches the hash; every failure (including a
// malformed hash or a password over 72 bytes) is false.
func VerifyPassword(password, hashed string) bool {
	if len(password) > bcryptMaxBytes {
		return false
	}
	if !validBcryptHash.MatchString(hashed) {
		return false
	}
	return bcrypt.CompareHashAndPassword([]byte(hashed), []byte(password)) == nil
}

// validBcryptHash is the stored-hash shape Python's bcrypt accepts: prefix 2a/2b/2x/2y, a
// two-digit cost 04-31, a 22-character salt whose last character is canonical (its low
// four bits are zero: . O e u) and 31 hash characters, exactly 60 bytes. x/crypto is more
// lenient (other prefixes, a '+' cost, trailing bytes, non-canonical salt).
var validBcryptHash = regexp.MustCompile(`^\$2[abxy]\$(?:0[4-9]|[12][0-9]|3[01])\$[./A-Za-z0-9]{21}[.Oeu][./A-Za-z0-9]{31}$`)

func validatePassword(password string) error {
	if password == "" {
		return &value_objects.ValueError{Msg: "Password cannot be empty"}
	}
	n := utf8.RuneCountInString(password)
	if n < MinPasswordLength {
		return &value_objects.ValueError{Msg: fmt.Sprintf("Password must be at least %d characters long", MinPasswordLength)}
	}
	if n > MaxPasswordLength {
		return &value_objects.ValueError{Msg: fmt.Sprintf("Password cannot exceed %d characters", MaxPasswordLength)}
	}
	return nil
}

// PasswordStrength is check_password_strength's analysis.
type PasswordStrength struct {
	Length       int
	HasUppercase bool
	HasLowercase bool
	HasDigit     bool
	HasSpecial   bool
	Strength     string // weak, medium, strong
	Score        int
	Suggestions  []string
}

// CheckPasswordStrength scores a password (Unicode-aware like str.isupper/islower/isdigit;
// special characters are ASCII punctuation).
func CheckPasswordStrength(password string) PasswordStrength {
	a := PasswordStrength{Length: utf8.RuneCountInString(password), Suggestions: []string{}}
	for _, c := range password {
		a.HasUppercase = a.HasUppercase || value_objects.PyIsUpper(c)
		a.HasLowercase = a.HasLowercase || value_objects.PyIsLower(c)
		a.HasDigit = a.HasDigit || value_objects.PyIsDigit(c)
		a.HasSpecial = a.HasSpecial || (c < 128 && strings.ContainsRune(punctuation, c))
	}
	score := 0
	for _, ok := range []bool{a.Length >= MinPasswordLength, a.Length >= 12, a.HasUppercase, a.HasLowercase, a.HasDigit, a.HasSpecial} {
		if ok {
			score++
		}
	}
	a.Score = score
	switch {
	case score <= 2:
		a.Strength = "weak"
	case score <= 4:
		a.Strength = "medium"
	default:
		a.Strength = "strong"
	}
	if !a.HasUppercase {
		a.Suggestions = append(a.Suggestions, "Add uppercase letters")
	}
	if !a.HasLowercase {
		a.Suggestions = append(a.Suggestions, "Add lowercase letters")
	}
	if !a.HasDigit {
		a.Suggestions = append(a.Suggestions, "Add numbers")
	}
	if !a.HasSpecial {
		a.Suggestions = append(a.Suggestions, "Add special characters")
	}
	if a.Length < 12 {
		a.Suggestions = append(a.Suggestions, "Use at least 12 characters for better security")
	}
	return a
}

// PasswordOptions are the character classes of GenerateSecurePassword.
type PasswordOptions struct {
	Length                                                            int
	IncludeUppercase, IncludeLowercase, IncludeDigits, IncludeSpecial bool
}

// DefaultPasswordOptions are the Python defaults (16 characters, every class).
func DefaultPasswordOptions() PasswordOptions { return PasswordOptions{16, true, true, true, true} }

func secureChoice(chars string, n int) (string, error) {
	var b strings.Builder
	max := big.NewInt(int64(len(chars)))
	for i := 0; i < n; i++ {
		idx, err := rand.Int(rand.Reader, max)
		if err != nil {
			return "", err
		}
		b.WriteByte(chars[idx.Int64()])
	}
	return b.String(), nil
}

// GenerateSecurePassword generates a random password; with every class selected it
// retries until each class is present.
func GenerateSecurePassword(o PasswordOptions) (string, error) {
	length := o.Length
	if length < MinPasswordLength {
		length = MinPasswordLength
	}
	if length > MaxPasswordLength {
		length = MaxPasswordLength
	}
	chars := ""
	if o.IncludeLowercase {
		chars += lowercase
	}
	if o.IncludeUppercase {
		chars += uppercase
	}
	if o.IncludeDigits {
		chars += digits
	}
	if o.IncludeSpecial {
		chars += punctuation
	}
	if chars == "" {
		chars = lowercase + uppercase + digits // fallback
	}
	password, err := secureChoice(chars, length)
	if err != nil {
		return "", err
	}
	if o.IncludeUppercase && o.IncludeLowercase && o.IncludeDigits && o.IncludeSpecial {
		for {
			a := CheckPasswordStrength(password)
			if a.HasUppercase && a.HasLowercase && a.HasDigit && a.HasSpecial {
				break
			}
			if password, err = secureChoice(chars, length); err != nil {
				return "", err
			}
		}
	}
	return password, nil
}

// GenerateResetToken is secrets.token_urlsafe(length): length random bytes, URL-safe
// base64 without padding.
func GenerateResetToken(length int) (string, error) {
	b := make([]byte, length)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(b), nil
}

// NeedsRehash reports whether a $2a$/$2b$ hash uses fewer rounds than DefaultRounds.
func NeedsRehash(hashed string) bool {
	if strings.HasPrefix(hashed, "$2b$") || strings.HasPrefix(hashed, "$2a$") {
		parts := strings.Split(hashed, "$")
		if len(parts) >= 3 {
			if n, ok := value_objects.PyParseInt(parts[2]); ok {
				return n.Cmp(big.NewInt(DefaultRounds)) < 0
			}
		}
	}
	return false
}
