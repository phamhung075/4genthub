package value_objects

import (
	"encoding/json"
	"os"
	"strings"
	"testing"
)

func TestPyParseUUIDMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/pyuuid_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases [][2]*string
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		got, ok := PyParseUUID(*c[0])
		switch {
		case c[1] == nil && ok:
			t.Fatalf("%q: Go accepts as %q, Python rejects", *c[0], got)
		case c[1] != nil && (!ok || got != *c[1]):
			t.Fatalf("%q: got %q ok=%v, Python %q", *c[0], got, ok, *c[1])
		}
	}
}

func TestPyParseIntMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/pyint_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases [][2]*string
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		n, ok := PyParseInt(*c[0])
		switch {
		case c[1] == nil && ok:
			t.Fatalf("%q: Go accepts as %s, Python rejects", *c[0], n)
		case c[1] != nil && (!ok || n.String() != *c[1]):
			t.Fatalf("%q: got %v ok=%v, Python %s", *c[0], n, ok, *c[1])
		}
	}
}

func TestPyParseIntDigitLimit(t *testing.T) {
	if _, ok := PyParseInt(strings.Repeat("9", 4300)); !ok {
		t.Error("4300 digits must parse")
	}
	if _, ok := PyParseInt(strings.Repeat("9", 4301)); ok {
		t.Error("4301 digits must fail (sys.int_info.default_max_str_digits)")
	}
}
