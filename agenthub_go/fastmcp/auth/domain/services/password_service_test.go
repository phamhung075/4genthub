package services

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"
)

type authOut struct {
	Ok  json.RawMessage `json:"ok"`
	Exc string          `json:"exc"`
	Msg string          `json:"msg"`
}

type authFixture struct {
	Strength []struct {
		In  string  `json:"in"`
		Out authOut `json:"out"`
	} `json:"strength"`
	Verify []struct {
		Pw   string `json:"pw"`
		Hash string `json:"hash"`
		Out  bool   `json:"out"`
	} `json:"verify"`
	Hash []struct {
		In       string   `json:"in"`
		Validate *authOut `json:"validate"`
		Hashed   *struct {
			Ok       string `json:"ok"`
			Len      int    `json:"len"`
			Verifies bool   `json:"verifies"`
			Exc      string `json:"exc"`
			Msg      string `json:"msg"`
		} `json:"hashed"`
	} `json:"hash"`
	Rehash []struct {
		Hash string  `json:"hash"`
		Out  authOut `json:"out"`
	} `json:"rehash"`
}

func loadAuthFixture(t *testing.T) authFixture {
	t.Helper()
	raw, err := os.ReadFile("testdata/auth_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var f authFixture
	if err := json.Unmarshal(raw, &f); err != nil {
		t.Fatal(err)
	}
	return f
}

func TestCheckPasswordStrengthParity(t *testing.T) {
	for _, c := range loadAuthFixture(t).Strength {
		var want struct {
			Length       int      `json:"length"`
			HasUppercase bool     `json:"has_uppercase"`
			HasLowercase bool     `json:"has_lowercase"`
			HasDigit     bool     `json:"has_digit"`
			HasSpecial   bool     `json:"has_special"`
			Strength     string   `json:"strength"`
			Score        int      `json:"score"`
			Suggestions  []string `json:"suggestions"`
		}
		if err := json.Unmarshal(c.Out.Ok, &want); err != nil {
			t.Fatalf("%q: %v", c.In, err)
		}
		got := CheckPasswordStrength(c.In)
		if got.Length != want.Length || got.HasUppercase != want.HasUppercase || got.HasLowercase != want.HasLowercase ||
			got.HasDigit != want.HasDigit || got.HasSpecial != want.HasSpecial || got.Strength != want.Strength ||
			got.Score != want.Score || !reflect.DeepEqual(got.Suggestions, want.Suggestions) {
			t.Errorf("%q: got %+v want %+v", c.In, got, want)
		}
	}
}

func TestValidatePasswordParity(t *testing.T) {
	n := 0
	for _, c := range loadAuthFixture(t).Hash {
		if c.Validate == nil {
			continue
		}
		n++
		err := validatePassword(c.In)
		switch {
		case c.Validate.Exc == "" && err != nil:
			t.Errorf("%q: unexpected error %v", c.In, err)
		case c.Validate.Exc != "" && (err == nil || err.Error() != c.Validate.Msg):
			t.Errorf("%q: err %v, want %q", c.In, err, c.Validate.Msg)
		}
	}
	if n == 0 {
		t.Fatal("no validate cases")
	}
}

func TestHashPasswordParity(t *testing.T) {
	for _, c := range loadAuthFixture(t).Hash {
		if c.Hashed == nil {
			continue
		}
		h, err := HashPassword(c.In)
		if c.Hashed.Exc != "" {
			if err == nil || err.Error() != c.Hashed.Msg {
				t.Errorf("%q: err %v, want %q", c.In, err, c.Hashed.Msg)
			}
			continue
		}
		if err != nil {
			t.Fatalf("%q: %v", c.In, err)
		}
		if h[:7] != c.Hashed.Ok || len(h) != c.Hashed.Len || VerifyPassword(c.In, h) != c.Hashed.Verifies {
			t.Errorf("%q: bad hash %q", c.In, h)
		}
	}
}

func TestVerifyPasswordParity(t *testing.T) {
	for _, c := range loadAuthFixture(t).Verify {
		if got := VerifyPassword(c.Pw, c.Hash); got != c.Out {
			t.Errorf("verify(%q, %q) = %v, want %v", c.Pw, c.Hash, got, c.Out)
		}
	}
}

func TestNeedsRehashParity(t *testing.T) {
	for _, c := range loadAuthFixture(t).Rehash {
		if c.Out.Exc != "" {
			t.Fatalf("unexpected Python exception for %q: %s", c.Hash, c.Out.Exc)
		}
		var want bool
		_ = json.Unmarshal(c.Out.Ok, &want)
		if got := NeedsRehash(c.Hash); got != want {
			t.Errorf("needs_rehash(%q) = %v, want %v", c.Hash, got, want)
		}
	}
}
