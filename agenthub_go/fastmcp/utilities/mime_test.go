package utilities

import (
	"encoding/json"
	"os"
	"testing"
)

func TestGuessTypeParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/mime_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		In   string
		Type *string
		Enc  *string
		Err  bool
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	str := func(p *string) string {
		if p == nil {
			return "<nil>"
		}
		return *p
	}
	for _, c := range cases {
		typ, enc, err := GuessType(c.In)
		if c.Err {
			if err == nil {
				t.Errorf("%q: want error", c.In)
			}
			continue
		}
		if err != nil || str(typ) != str(c.Type) || str(enc) != str(c.Enc) {
			t.Errorf("%q: got %s/%s (%v) want %s/%s", c.In, str(typ), str(enc), err, str(c.Type), str(c.Enc))
		}
	}
}
