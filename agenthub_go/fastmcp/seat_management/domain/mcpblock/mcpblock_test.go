package mcpblock

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"
	"unicode/utf8"
)

const platformBlock = `{
  "name": "agenthub_http",
  "type": "http",
  "url": "${AGENTHUB_MCP_URL}",
  "headers": {"Accept": "application/json, text/event-stream", "Authorization": "Bearer ${AGENTHUB_TOKEN}"}
}`

func TestParseHTTP(t *testing.T) {
	server, err := Parse(platformBlock)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if server.Name != "agenthub_http" || server.Type != TypeHTTP || server.URL != PlatformURLPlaceholder {
		t.Fatalf("server = %+v", server)
	}
	if server.Headers["Authorization"] != "Bearer ${AGENTHUB_TOKEN}" {
		t.Fatalf("headers = %v", server.Headers)
	}
	resolved := server.WithPlatformURL("https://api.example.test/mcp")
	if resolved.URL != "https://api.example.test/mcp" {
		t.Fatalf("resolved url = %q", resolved.URL)
	}
	if resolved.Headers["Authorization"] != "Bearer ${AGENTHUB_TOKEN}" {
		t.Fatalf("substitution touched a client-expanded reference: %v", resolved.Headers)
	}
	fragment := resolved.Fragment()
	want := map[string]any{
		"type": "http",
		"url":  "https://api.example.test/mcp",
		"headers": map[string]string{
			"Accept":        "application/json, text/event-stream",
			"Authorization": "Bearer ${AGENTHUB_TOKEN}",
		},
	}
	if !reflect.DeepEqual(fragment, want) {
		t.Fatalf("fragment = %v", fragment)
	}
}

func TestParseStdio(t *testing.T) {
	server, err := Parse(`{"name":"sequential-thinking","type":"stdio","command":"npx","args":["-y","@modelcontextprotocol/server-sequential-thinking"],"env":{"EXA_API_KEY":"${EXA_API_KEY}"}}`)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if server.Command != "npx" || len(server.Args) != 2 || server.Env["EXA_API_KEY"] != "${EXA_API_KEY}" {
		t.Fatalf("server = %+v", server)
	}
	fragment := server.Fragment()
	if fragment["url"] != nil || fragment["command"] != "npx" || fragment["type"] != TypeStdio {
		t.Fatalf("fragment = %v", fragment)
	}
}

func TestParseErrors(t *testing.T) {
	cases := map[string]struct{ content, want string }{
		"not json":       {`not json`, "not one JSON value"},
		"two values":     {`{"name":"a","type":"http","url":"http://x"} {"name":"b"}`, "not one JSON value"},
		"not an object":  {`123`, "not a server object"},
		"unknown field":  {`{"name":"a","type":"http","url":"http://x","alwaysAllow":["t"]}`, "unknown field"},
		"no name":        {`{"type":"http","url":"http://x"}`, "field name is required"},
		"blank name":     {`{"name":"  ","type":"http","url":"http://x"}`, "field name is required"},
		"no type":        {`{"name":"a"}`, `field type must be "http" or "stdio"`},
		"bad type":       {`{"name":"a","type":"sse","url":"http://x"}`, `field type must be "http" or "stdio"`},
		"http no url":    {`{"name":"a","type":"http"}`, "field url is required"},
		"http command":   {`{"name":"a","type":"http","url":"http://x","command":"npx"}`, "not command, args or env"},
		"http env":       {`{"name":"a","type":"http","url":"http://x","env":{"A":"1"}}`, "not command, args or env"},
		"http bad url":   {`{"name":"a","type":"http","url":"ftp://x"}`, "url must be http(s)"},
		"stdio no cmd":   {`{"name":"a","type":"stdio"}`, "field command is required"},
		"stdio url":      {`{"name":"a","type":"stdio","command":"npx","url":"http://x"}`, "not url or headers"},
		"stdio headers":  {`{"name":"a","type":"stdio","command":"npx","headers":{"A":"1"}}`, "not url or headers"},
		"literal bearer": {`{"name":"a","type":"http","url":"http://x","headers":{"Authorization":"Bearer tok_0123456789abcdefghij"}}`, "credential-shaped"},
		"jwt":            {`{"name":"a","type":"http","url":"http://x","headers":{"Authorization":"eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnop"}}`, "credential-shaped"},
		"api key":        {`{"name":"a","type":"http","url":"http://x","headers":{"X-Key":"sk-abcdefghijklmnopqrstuvwx"}}`, "credential-shaped"},
		"private key":    {`{"name":"a","type":"stdio","command":"sh","args":["-----BEGIN RSA PRIVATE KEY-----"]}`, "credential-shaped"},
		"url credential": {`{"name":"a","type":"http","url":"https://user:hunter2@example.test/mcp"}`, "credential-shaped"},
	}
	for name, c := range cases {
		if _, err := Parse(c.content); err == nil || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want %q", name, err, c.want)
		}
	}
}

// A value that names an environment variable is not a secret: that is the whole point of the
// ${VAR} convention, so the scanner must not flag it.
func TestParseAcceptsEnvReferences(t *testing.T) {
	for name, content := range map[string]string{
		"token":   `{"name":"a","type":"http","url":"${AGENTHUB_MCP_URL}","headers":{"Authorization":"Bearer ${AGENTHUB_TOKEN}"}}`,
		"api key": `{"name":"a","type":"stdio","command":"npx","env":{"EXA_API_KEY":"${EXA_API_KEY}"}}`,
		"secret":  `{"name":"a","type":"stdio","command":"npx","env":{"AUTH_SECRET":"${AUTH_SECRET}"}}`,
	} {
		if _, err := Parse(content); err != nil {
			t.Errorf("%s: Parse(%s) = %v, want nil", name, content, err)
		}
	}
}

func TestCheckURLAcceptsClientExpandedReference(t *testing.T) {
	if err := CheckURL("${MY_SERVER_URL}"); err != nil {
		t.Fatalf("CheckURL(expanded ref) = %v, want nil", err)
	}
	if err := CheckURL("https://example.test/mcp"); err != nil {
		t.Fatalf("CheckURL(https) = %v, want nil", err)
	}
	if err := CheckURL(""); err != nil {
		t.Fatalf("CheckURL(empty) = %v, want nil", err)
	}
	if err := CheckURL("http://example.test/mcp"); err != nil {
		t.Fatalf("CheckURL(http) = %v, want nil", err)
	}
	if err := CheckURL("ftp://example.test"); err == nil {
		t.Fatal("CheckURL(ftp) = nil, want an error")
	}
}

func TestFragmentJSONShape(t *testing.T) {
	server, err := Parse(platformBlock)
	if err != nil {
		t.Fatal(err)
	}
	server = server.WithPlatformURL("https://api.example.test/mcp")
	encoded, err := json.Marshal(server.Fragment())
	if err != nil {
		t.Fatal(err)
	}
	want := `{"headers":{"Accept":"application/json, text/event-stream","Authorization":"Bearer ${AGENTHUB_TOKEN}"},"type":"http","url":"https://api.example.test/mcp"}`
	if string(encoded) != want {
		t.Fatalf("fragment = %s\nwant      %s", encoded, want)
	}
}

// TestSeatValueRoundTripsThroughItsOwnValidator is the invariant the writer and the reader share:
// whatever SeatValue produces, ValidateSeatValue accepts. The seat key with a separator inside it is
// the case that decides the split rule - a rule that refuses it would refuse a real identity, which
// is worse than the junk it was written to catch.
func TestSeatValueRoundTripsThroughItsOwnValidator(t *testing.T) {
	for _, tc := range []struct{ room, seat string }{
		{"alpha", "beta"},
		{"room-1", "seat.with.dots"},
		{"room1", "seat/key"},
		{"alpha", "/beta"},
		{"a", "b"},
	} {
		v := SeatValue(tc.room, tc.seat)
		if err := ValidateSeatValue(v); err != nil {
			t.Errorf("SeatValue(%q, %q) = %q, which its own validator refused: %v", tc.room, tc.seat, v, err)
		}
	}
}

// TestValidateSeatValueRefusesWhatCannotBeAnActorID pins the two refusals the MCP boundary needs: a
// value past VARCHAR(255), which used to roll back the caller's own write, and a value that names no
// seat. The width cases are the boundary itself - 255 and 256 - rather than "long" and "short",
// because the column's width is the number the rule is about.
func TestValidateSeatValueRefusesWhatCannotBeAnActorID(t *testing.T) {
	const room = "room"
	longest := SeatValue(room, strings.Repeat("s", SeatValueMaxLen-len(room)-1))
	if len(longest) != SeatValueMaxLen {
		t.Fatalf("the longest storable identity is %d bytes, want %d", len(longest), SeatValueMaxLen)
	}
	if err := ValidateSeatValue(longest); err != nil {
		t.Fatalf("the longest storable identity was refused: %v", err)
	}

	oneTooMany := SeatValue(room, strings.Repeat("s", SeatValueMaxLen-len(room)))
	if len(oneTooMany) != SeatValueMaxLen+1 {
		t.Fatalf("the overflow fixture is %d bytes, want %d", len(oneTooMany), SeatValueMaxLen+1)
	}
	err := ValidateSeatValue(oneTooMany)
	if err == nil {
		t.Fatal("a value past the actor id's width was accepted: it would fail the INSERT and roll back the caller's write")
	}
	if !strings.Contains(err.Error(), "256") {
		t.Errorf("the refusal does not say how long the value was: %v", err)
	}
	if len(err.Error()) > 200 {
		t.Errorf("the refusal is %d bytes: a hostile header must not inflate the message", len(err.Error()))
	}

	// The column counts CHARACTERS, not bytes: VARCHAR(255) in PostgreSQL admits 255 characters however
	// many bytes they take. A bound in bytes would refuse a legal identity made of two-byte characters -
	// the safe direction is still wrong, because a seat key with an accented letter is a real key.
	wide := SeatValue(room, strings.Repeat("é", SeatValueMaxLen-len(room)-1))
	if got := utf8.RuneCountInString(wide); got != SeatValueMaxLen {
		t.Fatalf("the wide fixture is %d characters, want %d", got, SeatValueMaxLen)
	}
	if len(wide) <= SeatValueMaxLen {
		t.Fatalf("the wide fixture is only %d bytes, so it cannot tell a character bound from a byte bound", len(wide))
	}
	if err := ValidateSeatValue(wide); err != nil {
		t.Errorf("%d CHARACTERS (%d bytes) was refused: actor_id counts characters, so this refuses a legal identity: %v",
			SeatValueMaxLen, len(wide), err)
	}

	wideOver := SeatValue(room, strings.Repeat("é", SeatValueMaxLen-len(room)))
	if got := utf8.RuneCountInString(wideOver); got != SeatValueMaxLen+1 {
		t.Fatalf("the wide overflow fixture is %d characters, want %d", got, SeatValueMaxLen+1)
	}
	err = ValidateSeatValue(wideOver)
	if err == nil {
		t.Errorf("%d characters was accepted: it is past the column's width", SeatValueMaxLen+1)
	} else if !strings.Contains(err.Error(), "256") {
		t.Errorf("the refusal does not name the length in the column's own unit: %v", err)
	}

	// The values that name no seat. `alpha//beta` is deliberately NOT here: it splits at the FIRST
	// separator into room `alpha` and seat `/beta`, and a key may contain one, so refusing it would
	// refuse a real identity - the round-trip case above pins that it is accepted.
	for _, bad := range []string{"", "alpha", "/beta", "alpha/"} {
		if err := ValidateSeatValue(bad); err == nil {
			t.Errorf("ValidateSeatValue(%q) accepted a value that names no seat", bad)
		}
	}
}
