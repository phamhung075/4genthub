package value_objects

import (
	"encoding/json"
	"os"
	"strconv"
	"testing"
	"unicode"
)

type pyreprCases struct {
	Ranges [][2]int          `json:"ranges"`
	Reprs  map[string]string `json:"reprs"`
	Mixed  map[string]string `json:"mixed"`
}

func loadPyreprCases(t *testing.T) pyreprCases {
	raw, err := os.ReadFile("testdata/pyrepr_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var c pyreprCases
	if err := json.Unmarshal(raw, &c); err != nil {
		t.Fatal(err)
	}
	return c
}

// Python 3.14 (Unicode 16.0) is the reference. Go's tables are Unicode 15.0, so a code point
// assigned only in 16.0 is escaped by Go but printed by Python; that skew is the only allowed
// difference, and it must stay a one-way "Go escapes more" set.
func TestPyReprEveryCodePoint(t *testing.T) {
	c := loadPyreprCases(t)
	nonPrintable := make([]bool, 0x110000)
	for _, r := range c.Ranges {
		for cp := r[0]; cp <= r[1]; cp++ {
			nonPrintable[cp] = true
		}
	}
	skew := map[int]bool{}
	for cp := 0; cp < 0x110000; cp++ {
		if cp == 0x27 || cp == 0x22 || cp == 0x5c || (cp >= 0xd800 && cp <= 0xdfff) {
			continue // quoting/backslash cases are covered by the samples below; surrogates cannot occur in Go strings
		}
		s := string(rune(cp))
		got := pyQuote(s)
		raw := got == "'"+s+"'"
		switch {
		case nonPrintable[cp] && cp != 0x09 && cp != 0x0a && cp != 0x0d && raw:
			t.Fatalf("U+%04X is non-printable in Python but printed raw", cp)
		case !nonPrintable[cp] && !raw:
			if unicode.IsPrint(rune(cp)) {
				t.Fatalf("U+%04X is printable in both but escaped: %s", cp, got)
			}
			skew[cp] = true
		}
	}
	t.Logf("Unicode 16.0 skew: %d code points escaped by Go but printable in Python", len(skew))
	// Pinned so that a Go toolchain upgrade (newer Unicode tables) forces a review of this skew.
	if len(skew) != 5812 {
		t.Fatalf("skew changed to %d (was 5812 with Go's Unicode 15.0 tables)", len(skew))
	}
	for k, want := range c.Reprs {
		cp, _ := strconv.Atoi(k)
		if skew[cp] {
			continue
		}
		if got := PyRepr(string(rune(cp))); got != want {
			t.Errorf("U+%04X: got %s want %s", cp, got, want)
		}
	}
	for in, want := range c.Mixed {
		if got := PyRepr(in); got != want {
			t.Errorf("%q: got %s want %s", in, got, want)
		}
	}
}
