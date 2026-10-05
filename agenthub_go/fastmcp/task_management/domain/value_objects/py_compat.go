package value_objects

import (
	"math"
	"math/big"
	"reflect"
	"strings"
	"time"
	"unicode"
)

// PyFloat converts a Python-number-like value (int kinds, float kinds, bool) to a
// float64; ok is false for anything else.
func PyFloat(v any) (float64, bool) {
	switch x := v.(type) {
	case bool:
		if x {
			return 1, true
		}
		return 0, true
	case *big.Int:
		// float(int) rounds to nearest; beyond float64 range Python raises OverflowError
		f, _ := new(big.Float).SetInt(x).Float64()
		return f, !math.IsInf(f, 0)
	}
	rv := reflect.ValueOf(v)
	switch rv.Kind() {
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return float64(rv.Int()), true
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return float64(rv.Uint()), true
	case reflect.Float32, reflect.Float64:
		return rv.Float(), true
	}
	return 0, false
}

// PyEqual is Python's == for JSON-like values: numbers (and bools) compare by
// value across int/float (1 == 1.0 == True), everything else structurally.
func PyEqual(a, b any) bool {
	fa, aok := PyFloat(a)
	fb, bok := PyFloat(b)
	if aok && bok {
		return fa == fb
	}
	if aok != bok {
		return false
	}
	return reflect.DeepEqual(a, b)
}

// PyLower is Python's str.lower: the full Unicode lowercase mapping, i.e. U+0130 becomes
// "i\u0307" (Go maps it to a single 'i') and Σ becomes the final sigma ς at the end of a
// word (Go always gives σ).
func PyLower(s string) string {
	rs := []rune(s)
	var b strings.Builder
	b.Grow(len(s))
	for i, r := range rs {
		switch r {
		case '\u0130':
			b.WriteString("i\u0307")
		case '\u03a3':
			if isFinalSigma(rs, i) {
				b.WriteRune('\u03c2')
			} else {
				b.WriteRune('\u03c3')
			}
		default:
			b.WriteRune(unicode.ToLower(r))
		}
	}
	return b.String()
}

// isCased is the Unicode Cased property (Lu, Ll, Lt, Other_Lowercase, Other_Uppercase).
func isCased(r rune) bool {
	return unicode.IsUpper(r) || unicode.IsLower(r) || unicode.IsTitle(r) ||
		unicode.Is(unicode.Other_Lowercase, r) || unicode.Is(unicode.Other_Uppercase, r)
}

// isCaseIgnorable is the Unicode Case_Ignorable property: Mn, Me, Cf, Lm, Sk plus the
// Word_Break MidLetter / MidNumLet / Single_Quote characters.
func isCaseIgnorable(r rune) bool {
	if unicode.In(r, unicode.Mn, unicode.Me, unicode.Cf, unicode.Lm, unicode.Sk) {
		return true
	}
	switch r {
	case '\'', '.', ':', '\u00b7', '\u0387', '\u055f', '\u05f4', '\u2018', '\u2019', '\u2024', '\u2027',
		'\ufe13', '\ufe52', '\ufe55', '\uff07', '\uff0e', '\uff1a':
		return true
	}
	return false
}

// isFinalSigma implements the Final_Sigma condition: preceded by a cased letter (skipping
// case-ignorable characters) and not followed by one.
func isFinalSigma(rs []rune, i int) bool {
	j := i - 1
	for j >= 0 && isCaseIgnorable(rs[j]) {
		j--
	}
	if j < 0 || !isCased(rs[j]) {
		return false
	}
	j = i + 1
	for j < len(rs) && isCaseIgnorable(rs[j]) {
		j++
	}
	return j == len(rs) || !isCased(rs[j])
}

// PySplit mirrors str.split() with no arguments: split on runs of whitespace, no empty items.
func PySplit(s string) []string {
	out := []string{}
	start := -1
	for i, r := range s {
		if pyIsSpace(r) {
			if start >= 0 {
				out = append(out, s[start:i])
				start = -1
			}
		} else if start < 0 {
			start = i
		}
	}
	if start >= 0 {
		out = append(out, s[start:])
	}
	return out
}

// PyIsSpace mirrors str.isspace for one code point (also the set matched by re's \s).
func PyIsSpace(r rune) bool { return pyIsSpace(r) }

// PySum mirrors Python 3.12+ sum() over floats: Neumaier compensated summation starting
// from int 0 (plain left-to-right float addition differs in the last bits).
func PySum(xs []float64) float64 {
	result, c := 0.0, 0.0
	for _, x := range xs {
		t := float64(result + x)
		if math.Abs(result) >= math.Abs(x) {
			c += float64(float64(result-t) + x)
		} else {
			c += float64(float64(x-t) + result)
		}
		result = t
	}
	if c != 0 && !math.IsInf(c, 0) && !math.IsNaN(c) {
		result += c
	}
	return result
}

// PyTruthy mirrors bool(x) for JSON-like values: None, False, 0, 0.0, "", and empty
// containers are falsy; everything else (including any other object) is truthy.
func PyTruthy(v any) bool {
	if v == nil {
		return false
	}
	rv := reflect.ValueOf(v)
	if rv.Kind() == reflect.Pointer && rv.IsNil() {
		return false // a nil *OrderedMap is Python's None
	}
	if o, ok := v.(OrderedAny); ok {
		return len(o.KeysAny()) > 0
	}
	switch rv.Kind() {
	case reflect.Bool:
		return rv.Bool()
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64:
		return rv.Int() != 0
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return rv.Uint() != 0
	case reflect.Float32, reflect.Float64:
		return rv.Float() != 0
	case reflect.String, reflect.Slice, reflect.Map, reflect.Array:
		return rv.Len() > 0
	case reflect.Pointer, reflect.Interface:
		return !rv.IsNil()
	}
	return true
}

// PyTotalSeconds is timedelta.total_seconds(): integer microseconds divided once by
// 10**6. time.Duration.Seconds() rounds twice and differs in the last bit.
func PyTotalSeconds(d time.Duration) float64 { return float64(d.Microseconds()) / 1e6 }

// PySqrtRat is the correctly rounded square root of an exact rational, like
// statistics._float_sqrt_of_frac (one rounding instead of rounding the variance first).
func PySqrtRat(r *big.Rat) float64 {
	if r.Sign() <= 0 {
		return 0
	}
	f := new(big.Float).SetPrec(300).SetRat(r)
	f.Sqrt(f)
	out, _ := f.Float64()
	return out
}
