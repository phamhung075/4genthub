package main

import (
	"bytes"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/commpolicy"
)

const (
	testRig       = "r"
	testMember    = "a"
	allowPolicy   = `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"delegates_to","Allow":true}]}`
	noLinkPolicy  = `{"Seat":"a"}`
	explicitDeny  = `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"delegates_to","Allow":false}]}`
	unknownIntent = "gossip"
)

type delivery struct {
	calls  int
	target string
	text   string
	code   int
}

// seatEnv installs identity and delivery stubs and returns the pins dir, the seat dir and the
// recorded delivery. policy "" writes no policy file.
func seatEnv(t *testing.T, policy string) (pins, seatDir string, got *delivery) {
	t.Helper()
	pins = t.TempDir()
	seatDir = filepath.Join(pins, testRig, testMember)
	if err := os.MkdirAll(seatDir, 0700); err != nil {
		t.Fatal(err)
	}
	if policy != "" {
		if err := os.WriteFile(filepath.Join(seatDir, "policy.json"), []byte(policy), 0600); err != nil {
			t.Fatal(err)
		}
	}
	got = &delivery{}
	oldIdentify, oldDeliver := identify, deliver
	identify = func() (identity, error) {
		return identity{Rig: testRig, Member: testMember, Peers: map[string]string{"b": "pod-b@r"}}, nil
	}
	deliver = func(target, text string, _, _ io.Writer) int {
		got.calls++
		got.target, got.text = target, text
		return got.code
	}
	t.Cleanup(func() { identify, deliver = oldIdentify, oldDeliver })
	return pins, seatDir, got
}

func send(pins string, args ...string) (code int, stdout, stderr string) {
	var out, errb bytes.Buffer
	code = run(append([]string{"send", "--pins", pins}, args...), &out, &errb)
	return code, out.String(), errb.String()
}

func auditRecords(t *testing.T, seatDir string) []commpolicy.AuditRecord {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(seatDir, "audit.jsonl"))
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		t.Fatal(err)
	}
	var records []commpolicy.AuditRecord
	for _, line := range strings.Split(strings.TrimSuffix(string(data), "\n"), "\n") {
		var r commpolicy.AuditRecord
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			t.Fatalf("audit line %q: %v", line, err)
		}
		records = append(records, r)
	}
	return records
}

func TestSendAllowedDelivers(t *testing.T) {
	pins, seatDir, got := seatEnv(t, allowPolicy)
	code, _, stderr := send(pins, "--to", "b", "--intent", "task", "--", "hello", "world")
	if code != 0 {
		t.Fatalf("exit = %d, want 0 (stderr %q)", code, stderr)
	}
	if got.calls != 1 || got.target != "pod-b@r" || got.text != "hello world" {
		t.Fatalf("delivery = %+v, want one call to pod-b@r with %q", got, "hello world")
	}
	records := auditRecords(t, seatDir)
	if len(records) != 1 || !records[0].Allowed || records[0].From != "a" || records[0].To != "b" || records[0].Intent != commpolicy.IntentTask {
		t.Fatalf("audit = %+v", records)
	}
	info, err := os.Stat(filepath.Join(seatDir, "audit.jsonl"))
	if err != nil || info.Mode().Perm() != 0600 {
		t.Fatalf("audit file mode = %v, %v, want 0600", info, err)
	}
}

func TestSendDeliveryExitCodePassesThrough(t *testing.T) {
	pins, _, got := seatEnv(t, allowPolicy)
	got.code = 7
	if code, _, _ := send(pins, "--to", "b", "--intent", "task", "--", "hi"); code != 7 {
		t.Fatalf("exit = %d, want 7", code)
	}
}

func TestSendDeniedWritesAuditAndSkipsDelivery(t *testing.T) {
	cases := []struct {
		name, policy, to, intent, reason string
	}{
		{"no link", noLinkPolicy, "b", "task", "no link"},
		{"wrong intent", allowPolicy, "b", "report", ""},
		{"explicit deny", explicitDeny, "b", "task", ""},
		{"unlinked recipient", allowPolicy, "c", "task", "no link"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			pins, seatDir, got := seatEnv(t, tc.policy)
			code, stdout, stderr := send(pins, "--to", tc.to, "--intent", tc.intent, "--", "hi")
			if code != 3 {
				t.Fatalf("exit = %d, want 3 (stderr %q)", code, stderr)
			}
			records := auditRecords(t, seatDir)
			if len(records) != 1 || records[0].Allowed || records[0].Reason == "" {
				t.Fatalf("audit = %+v, want one denied record with a reason", records)
			}
			if stderr != "denied: "+records[0].Reason+"\n" {
				t.Fatalf("stderr = %q, want denied: %s", stderr, records[0].Reason)
			}
			if tc.reason != "" && records[0].Reason != tc.reason {
				t.Fatalf("reason = %q, want %q", records[0].Reason, tc.reason)
			}
			if got.calls != 0 || stdout != "" {
				t.Fatalf("delivery ran on a denied send: %+v, stdout %q", got, stdout)
			}
		})
	}
}

func TestSendPolicyMissingOrCorruptFailsClosed(t *testing.T) {
	for name, policy := range map[string]string{"missing": "", "corrupt": `{"Seat":`} {
		t.Run(name, func(t *testing.T) {
			pins, seatDir, got := seatEnv(t, policy)
			code, _, stderr := send(pins, "--to", "b", "--intent", "task", "--", "hi")
			if code != 2 || stderr == "" {
				t.Fatalf("exit = %d, stderr %q, want 2 with a message", code, stderr)
			}
			if got.calls != 0 {
				t.Fatal("delivery ran without a usable policy")
			}
			if records := auditRecords(t, seatDir); len(records) != 0 {
				t.Fatalf("audit = %+v, want none", records)
			}
		})
	}
}

func TestSendUsageErrorsExit2(t *testing.T) {
	cases := map[string][]string{
		"no recipient":   {"--intent", "task", "--", "hi"},
		"no intent":      {"--to", "b", "--", "hi"},
		"no message":     {"--to", "b", "--intent", "task"},
		"unknown intent": {"--to", "b", "--intent", unknownIntent, "--", "hi"},
		"bad flag":       {"--bogus"},
	}
	for name, args := range cases {
		t.Run(name, func(t *testing.T) {
			pins, seatDir, got := seatEnv(t, allowPolicy)
			if code, _, stderr := send(pins, args...); code != 2 || stderr == "" {
				t.Fatalf("exit = %d, stderr %q, want 2 with a message", code, stderr)
			}
			if got.calls != 0 || len(auditRecords(t, seatDir)) != 0 {
				t.Fatal("a usage error must neither deliver nor audit")
			}
		})
	}
}

func TestSendIdentityFailureExits2(t *testing.T) {
	pins, _, got := seatEnv(t, allowPolicy)
	identify = func() (identity, error) { return identity{}, io.ErrUnexpectedEOF }
	if code, _, _ := send(pins, "--to", "b", "--intent", "task", "--", "hi"); code != 2 || got.calls != 0 {
		t.Fatalf("exit = %d, calls = %d, want 2 and no delivery", code, got.calls)
	}
}

// The policy may allow a recipient that is not in the rig roster: nothing is delivered.
func TestSendAllowedRecipientOutsideRosterFails(t *testing.T) {
	pins, seatDir, got := seatEnv(t, `{"Seat":"a","Links":[{"From":"a","To":"ghost","Kind":"delegates_to","Allow":true}]}`)
	code, _, stderr := send(pins, "--to", "ghost", "--intent", "task", "--", "hi")
	if code != 1 || !strings.Contains(stderr, "not a seat of rig") || got.calls != 0 {
		t.Fatalf("exit = %d, stderr %q, calls = %d, want 1, a roster message, no delivery", code, stderr, got.calls)
	}
	if records := auditRecords(t, seatDir); len(records) != 1 || !records[0].Allowed {
		t.Fatalf("audit = %+v, want the allowed decision recorded", records)
	}
}

// parseWhoami reads the roster the way rig whoami prints it: peers are keyed by member name
// and carry the full session name rig send needs.
func TestParseWhoamiRoster(t *testing.T) {
	who, err := parseWhoami([]byte(`{"identity":{"rigName":"scratchcomm","memberId":"alpha","sessionName":"scratchcomm-alpha@scratchcomm"},` +
		`"peers":[{"logicalId":"scratchcomm.beta","sessionName":"scratchcomm-beta@scratchcomm"}]}`))
	if err != nil {
		t.Fatal(err)
	}
	if who.Rig != "scratchcomm" || who.Member != "alpha" || len(who.Peers) != 1 || who.Peers["beta"] != "scratchcomm-beta@scratchcomm" {
		t.Fatalf("identity = %+v", who)
	}
	if _, err := parseWhoami([]byte(`{"identity":{}}`)); err == nil {
		t.Fatal("an identity without rig or member must fail")
	}
}

// In a multi-pod rig the pod is not the rig name: the member is what follows the first dot.
func TestParseWhoamiMultiPodRig(t *testing.T) {
	who, err := parseWhoami([]byte(`{"identity":{"rigName":"4genthub-go","memberId":"coder"},"peers":[` +
		`{"logicalId":"dev.reviewer","sessionName":"dev-reviewer@4genthub-go"},` +
		`{"logicalId":"agy.check","sessionName":"agy-check@4genthub-go"}]}`))
	if err != nil {
		t.Fatal(err)
	}
	if who.Peers["reviewer"] != "dev-reviewer@4genthub-go" || who.Peers["check"] != "agy-check@4genthub-go" || len(who.Peers) != 2 {
		t.Fatalf("peers = %v", who.Peers)
	}
}

func TestParseWhoamiDuplicateMemberIsAnError(t *testing.T) {
	_, err := parseWhoami([]byte(`{"identity":{"rigName":"r","memberId":"a"},"peers":[` +
		`{"logicalId":"agy.check","sessionName":"agy-check@r"},{"logicalId":"dev.check","sessionName":"dev-check@r"}]}`))
	if err == nil || !strings.Contains(err.Error(), "check") || !strings.Contains(err.Error(), "agy-check@r") || !strings.Contains(err.Error(), "dev-check@r") {
		t.Fatalf("err = %v, want the member and both sessions named", err)
	}
}

func TestSendAuditAppendsAcrossRuns(t *testing.T) {
	pins, seatDir, _ := seatEnv(t, allowPolicy)
	for i := 0; i < 2; i++ {
		if code, _, stderr := send(pins, "--to", "b", "--intent", "task", "--", "hi"); code != 0 {
			t.Fatalf("run %d exit = %d (stderr %q)", i, code, stderr)
		}
	}
	if got := auditRecords(t, seatDir); len(got) != 2 {
		t.Fatalf("audit lines = %d, want 2", len(got))
	}
}

func TestSendAuditFailureExits1WithoutDelivery(t *testing.T) {
	pins, seatDir, got := seatEnv(t, allowPolicy)
	if err := os.Mkdir(filepath.Join(seatDir, "audit.jsonl"), 0700); err != nil {
		t.Fatal(err)
	}
	if code, _, _ := send(pins, "--to", "b", "--intent", "task", "--", "hi"); code != 1 || got.calls != 0 {
		t.Fatalf("exit = %d, calls = %d, want 1 and no delivery", code, got.calls)
	}
}

func writeFile(t *testing.T, path, content string) string {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
	return path
}

func TestAuditScanFindsBypassAndSkipsKnownWrapper(t *testing.T) {
	dir := t.TempDir()
	observed := writeFile(t, filepath.Join(dir, "observed.txt"),
		"rig send b@r hi\nFOO=1 /usr/bin/rig queue y\nseatcheck send --to b --intent task -- hi\nrig status\n")

	var stdout, stderr bytes.Buffer
	code := run([]string{"audit-scan", "--known", "seatcheck", "--file", observed}, &stdout, &stderr)
	if code != 4 {
		t.Fatalf("exit = %d, want 4 (stderr %q)", code, stderr.String())
	}
	want := "bypass-suspected: rig send b@r hi\nbypass-suspected: FOO=1 /usr/bin/rig queue y\n"
	if stdout.String() != want {
		t.Fatalf("stdout = %q, want %q", stdout.String(), want)
	}
}

func TestAuditScanCleanExits0(t *testing.T) {
	dir := t.TempDir()
	observed := writeFile(t, filepath.Join(dir, "observed.txt"), "seatcheck send --to b --intent task -- hi\nrig status\n")

	var stdout, stderr bytes.Buffer
	code := run([]string{"audit-scan", "--known", "seatcheck", "--file", observed}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("exit = %d, want 0 (stderr %q)", code, stderr.String())
	}
	if stdout.Len() != 0 {
		t.Fatalf("stdout = %q, want empty", stdout.String())
	}
}
