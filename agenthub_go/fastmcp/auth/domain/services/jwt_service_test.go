package services

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

type jwtCase struct {
	Op    string          `json:"op"`
	Name  string          `json:"name"`
	Token string          `json:"token"`
	Type  string          `json:"type"`
	Aud   string          `json:"aud"`
	Now   string          `json:"now"`
	Key   string          `json:"key"`
	Head  string          `json:"header"`
	Out   json.RawMessage `json:"out"`
}

// norm round-trips a value through JSON so numbers compare uniformly.
func norm(t *testing.T, v any) any {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	var out any
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatal(err)
	}
	return out
}

func rawAny(t *testing.T, r json.RawMessage) any {
	t.Helper()
	var out any
	if err := json.Unmarshal(r, &out); err != nil {
		t.Fatal(err)
	}
	return out
}

func newTestService(t *testing.T, key, now string) *JWTService {
	t.Helper()
	s, err := NewJWTService(key, "agenthub")
	if err != nil {
		t.Fatal(err)
	}
	ts, err := time.Parse(time.RFC3339Nano, now)
	if err != nil {
		t.Fatal(err)
	}
	s.Now = func() time.Time { return ts }
	n := 0
	s.TokenHex = func(b int) string {
		n++
		return strings.Repeat(fmt.Sprintf("%02d", n), b)
	}
	return s
}

const testKey = "unit-test-secret-key-0123456789abcdef"

func isoPy(ts time.Time) string {
	if ts.Nanosecond() == 0 {
		return ts.UTC().Format("2006-01-02T15:04:05") + "+00:00"
	}
	return ts.UTC().Format("2006-01-02T15:04:05.000000") + "+00:00"
}

func TestJWTParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/jwt_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []jwtCase
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	creates := 0
	for i, c := range cases {
		label := fmt.Sprintf("#%d %s/%s/%s/%s", i, c.Op, c.Name, c.Type, c.Aud)
		want := rawAny(t, c.Out)
		var got any
		switch c.Op {
		case "access", "access_aud", "access_roles_none", "refresh", "refresh_fam", "reset", "gen", "gen_aud":
			s := newTestService(t, testKey, c.Now)
			creates++
			var tok string
			var fam string
			var err error
			switch c.Op {
			case "access":
				tok, err = s.CreateAccessToken("u1", "a@b.c", []string{"user", "admin"}, nil, DefaultAudience)
			case "access_aud":
				extra := entities.NewOrderedMap[any]()
				extra.Set("extra", int64(1))
				extra.Set("iss", "other")
				extra.Set("z", []any{int64(1), int64(2)})
				tok, err = s.CreateAccessToken("üser", "é@b.c", []string{}, extra, "custom")
			case "access_roles_none":
				tok, err = s.CreateAccessToken("u1", "a@b.c", nil, nil, DefaultAudience)
			case "refresh":
				tok, fam, err = s.CreateRefreshToken("u1", "", 0)
			case "refresh_fam":
				tok, fam, err = s.CreateRefreshToken("u1", "fam-1", 7)
			case "reset":
				tok, err = s.CreateResetToken("u1", "a@b.c")
			case "gen":
				tok, err = s.GenerateToken("u1", []string{"read", "write"}, 30, "tid-1", DefaultAudience)
			case "gen_aud":
				tok, err = s.GenerateToken("u1", []string{}, 1, "tid-2", "other-aud")
			}
			if err != nil {
				t.Fatalf("%s: %v", label, err)
			}
			if strings.HasPrefix(c.Op, "refresh") {
				got = []any{tok, fam}
			} else {
				got = tok
			}
		case "verify":
			s := newTestService(t, testKey, c.Now)
			p := s.VerifyToken(c.Token, c.Type, c.Aud)
			if p == nil {
				got = nil
			} else {
				got = norm(t, p)
			}
		case "expiry":
			s := newTestService(t, testKey, c.Now)
			if ts, ok := s.GetTokenExpiry(c.Token); ok {
				got = isoPy(ts)
			}
		case "expired":
			got = newTestService(t, testKey, c.Now).IsTokenExpired(c.Token)
		case "refresh_flow":
			s := newTestService(t, testKey, c.Now)
			a, r, ok, err := s.RefreshAccessToken(c.Token)
			switch {
			case err != nil:
				w, _ := want.(map[string]any)
				if w == nil || w["__exc__"] != "TypeError" {
					t.Errorf("%s: unexpected error %v, want %v", label, err, want)
				}
				continue
			case ok:
				got = []any{a, r}
			}
		case "header":
			s := newTestService(t, testKey, "2026-10-01T12:00:00Z")
			if tok, ok := s.ExtractTokenFromHeader(c.Head); ok {
				got = tok
			}
		case "badkey":
			s, _ := NewJWTService(c.Key, "agenthub")
			_, err := s.CreateAccessToken("u", "e", []string{}, nil, DefaultAudience)
			w := want.(map[string]any)
			if err == nil || err.Error() != w["msg"] {
				t.Errorf("%s: err %v, want %v", label, err, w["msg"])
			}
			continue
		case "badkey_verify":
			s, _ := NewJWTService(c.Key, "agenthub")
			if p := s.VerifyToken(c.Token, "access", ""); p != nil {
				got = norm(t, p)
			}
		case "emptykey":
			_, err := NewJWTService("", "x")
			w := want.(map[string]any)
			if err == nil || err.Error() != w["msg"] {
				t.Errorf("%s: err %v, want %v", label, err, w["msg"])
			}
			continue
		default:
			t.Fatalf("unknown op %s", c.Op)
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("%s:\n got  %v\n want %v", label, got, want)
		}
	}
	if creates != 8 {
		t.Fatalf("expected 8 create cases, ran %d", creates)
	}
}

// TestB64urlDecodeCPythonParity compares b64urlDecode with PyJWT's base64url_decode on
// 6000 random segments with garbage characters, stray '=' and odd lengths (padding uses
// the raw length, garbage is discarded, data after a completing pad is ignored, a
// dangling quad is an error).
func TestB64urlDecodeCPythonParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/b64_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		In  string  `json:"in"`
		Out *string `json:"out"`
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	bad := 0
	for _, c := range cases {
		got, err := b64urlDecode([]byte(c.In))
		switch {
		case c.Out == nil && err == nil:
			bad++
			t.Errorf("%q: Python rejects, Go decodes %x", c.In, got)
		case c.Out != nil && err != nil:
			bad++
			t.Errorf("%q: Python decodes %s, Go rejects", c.In, *c.Out)
		case c.Out != nil && hex.EncodeToString(got) != *c.Out:
			bad++
			t.Errorf("%q: got %x want %s", c.In, got, *c.Out)
		}
		if bad > 15 {
			t.FailNow()
		}
	}
}

func TestBcryptHashStrictness(t *testing.T) {
	h, err := HashPassword("secret-pass")
	if err != nil {
		t.Fatal(err)
	}
	if !VerifyPassword("secret-pass", h) {
		t.Fatal("valid hash rejected")
	}
	for _, bad := range []string{h + "\n", h + "x", "$2c" + h[3:], "$2" + h[3:], "$2B" + h[3:], h[:2] + "b " + h[4:], h[:4] + "+4" + h[6:], h[:4] + "03" + h[6:], h[:4] + "32" + h[6:]} {
		if VerifyPassword("secret-pass", bad) {
			t.Errorf("lenient hash accepted: %q", bad)
		}
	}
}

func TestB64FalseHeaderRejected(t *testing.T) {
	s := newTestService(t, testKey, "2026-10-01T12:00:00Z")
	enc := func(b string) string { return b64urlEncode([]byte(b)) }
	si := enc(`{"alg":"HS256","typ":"JWT","b64":false}`) + "." + enc(`{"sub":"u","exp":4102444800}`)
	key, _ := s.hmacKey()
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(si))
	tok := si + "." + b64urlEncode(mac.Sum(nil))
	if p := s.VerifyToken(tok, "access", ""); p != nil {
		t.Errorf("b64:false header accepted: %v", p)
	}
	if _, ok := s.GetTokenExpiry(tok); ok {
		t.Error("GetTokenExpiry accepted a b64:false header")
	}
}
