package value_objects

import (
	"math/big"
	"strings"
	"unicode"
	"unicode/utf8"
)

// PyParseUUID mirrors uuid.UUID(str) and returns the canonical lowercase hyphenated
// form. CPython strips "urn:", "uuid:", surrounding braces and hyphens, requires 32
// characters and then parses them with int(hex, 16), so surrounding whitespace, a
// sign, a 0x prefix, single "_" separators and Unicode decimal digits are accepted
// as well (negative values fail the 128-bit range check).
func PyParseUUID(s string) (string, bool) {
	h := strings.ReplaceAll(s, "urn:", "")
	h = strings.ReplaceAll(h, "uuid:", "")
	h = strings.Trim(h, "{}")
	h = strings.ReplaceAll(h, "-", "")
	if utf8.RuneCountInString(h) != 32 {
		return "", false
	}
	n, ok := pyInt(h, 16)
	if !ok || n.Sign() < 0 {
		return "", false
	}
	hex := n.Text(16)
	hex = strings.Repeat("0", 32-len(hex)) + hex
	return hex[:8] + "-" + hex[8:12] + "-" + hex[12:16] + "-" + hex[16:20] + "-" + hex[20:], true
}

// decimalDigitValue is the value of a Unicode decimal digit (category Nd).
func decimalDigitValue(r rune) int {
	start := r
	for unicode.Is(unicode.Nd, start-1) {
		start--
	}
	return int(r-start) % 10
}

// pyInt mirrors int(s, base) for base 10 and 16: non-ASCII whitespace and decimal digits are
// normalised, ASCII whitespace is stripped from both ends, then an optional sign, an
// optional 0x prefix and hex digits with single underscores between digits.
func pyInt(s string, base int) (*big.Int, bool) {
	var out []byte
	for _, r := range s {
		switch {
		case r < 127:
			out = append(out, byte(r))
		case pyIsSpace(r):
			out = append(out, ' ')
		case unicode.Is(unicode.Nd, r):
			out = append(out, byte('0'+decimalDigitValue(r)))
		default:
			return nil, false
		}
	}
	t := strings.Trim(string(out), " \t\n\v\f\r")
	neg := false
	if t != "" && (t[0] == '+' || t[0] == '-') {
		neg = t[0] == '-'
		t = t[1:]
	}
	if base == 16 && len(t) >= 2 && t[0] == '0' && (t[1] == 'x' || t[1] == 'X') {
		t = t[2:]
		t = strings.TrimPrefix(t, "_")
	}
	if t == "" {
		return nil, false
	}
	var digits []byte
	prevUnderscore := true // a leading underscore is invalid
	for i := 0; i < len(t); i++ {
		c := t[i]
		switch {
		case c == '_':
			if prevUnderscore {
				return nil, false
			}
			prevUnderscore = true
		case c >= '0' && c <= '9', base == 16 && (c >= 'a' && c <= 'f' || c >= 'A' && c <= 'F'):
			digits = append(digits, c)
			prevUnderscore = false
		default:
			return nil, false
		}
	}
	// sys.get_int_max_str_digits(): decimal strings over 4300 digits are a ValueError.
	if base == 10 && len(digits) > 4300 {
		return nil, false
	}
	if prevUnderscore {
		return nil, false
	}
	n, ok := new(big.Int).SetString(string(digits), base)
	if !ok {
		return nil, false
	}
	if neg {
		n.Neg(n)
	}
	return n, true
}

// PyParseInt is int(s) (base 10): surrounding whitespace, a sign, single "_"
// separators and Unicode decimal digits are accepted.
func PyParseInt(s string) (*big.Int, bool) { return pyInt(s, 10) }
