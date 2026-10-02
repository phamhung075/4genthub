package value_objects

import (
	"encoding/json"
	"os"
	"testing"
)

type voCase struct {
	In  string `json:"in"`
	Out struct {
		Ok  string `json:"ok"`
		Exc string `json:"exc"`
		Msg string `json:"msg"`
	} `json:"out"`
}

func loadVO(t *testing.T, key string) []voCase {
	t.Helper()
	raw, err := os.ReadFile("../services/testdata/auth_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var f map[string]json.RawMessage
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	var cases []voCase
	if err := json.Unmarshal(f[key], &cases); err != nil {
		t.Fatal(err)
	}
	return cases
}

func TestEmailParity(t *testing.T) {
	for _, c := range loadVO(t, "email") {
		e, err := NewEmail(c.In)
		if c.Out.Exc != "" {
			if err == nil || err.Error() != c.Out.Msg {
				t.Errorf("%q: err %v, want %q", c.In, err, c.Out.Msg)
			}
			continue
		}
		if err != nil || e.Value != c.Out.Ok {
			t.Errorf("%q: got %q (%v), want %q", c.In, e.Value, err, c.Out.Ok)
		}
	}
}

func TestUserIdParity(t *testing.T) {
	for _, c := range loadVO(t, "user_id") {
		u, err := NewUserId(c.In)
		if c.Out.Exc != "" {
			if err == nil || err.Error() != c.Out.Msg {
				t.Errorf("%q: err %v, want %q", c.In, err, c.Out.Msg)
			}
			continue
		}
		if err != nil || u.Value != c.Out.Ok {
			t.Errorf("%q: got %q (%v), want %q", c.In, u.Value, err, c.Out.Ok)
		}
	}
}
