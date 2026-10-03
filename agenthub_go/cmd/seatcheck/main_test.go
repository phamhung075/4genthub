package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/commpolicy"
)

// TestMain doubles as the delivery helper: the test re-invokes this binary with
// GO_WANT_HELPER_PROCESS set.
func TestMain(m *testing.M) {
	if os.Getenv("GO_WANT_HELPER_PROCESS") == "1" {
		helperProcess()
		return
	}
	os.Exit(m.Run())
}

func helperProcess() {
	if path := os.Getenv("SEATCHECK_HELPER_ARGS"); path != "" {
		args := strings.Join(os.Args[1:], "\n") + "\n"
		if err := os.WriteFile(path, []byte(args), 0600); err != nil {
			os.Exit(98)
		}
	}
	code := 0
	if v := os.Getenv("SEATCHECK_HELPER_EXIT"); v != "" {
		parsed, err := strconv.Atoi(v)
		if err != nil {
			os.Exit(97)
		}
		code = parsed
	}
	os.Exit(code)
}

const allowPolicy = `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"delegates_to","Allow":true}]}`
const denyPolicy = `{"Seat":"a"}`

func writeFile(t *testing.T, path, content string) string {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
	return path
}

func auditLines(t *testing.T, path string) []string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read audit: %v", err)
	}
	text := strings.TrimSuffix(string(data), "\n")
	if text == "" {
		return nil
	}
	return strings.Split(text, "\n")
}

func readAudit(t *testing.T, path string) commpolicy.AuditRecord {
	t.Helper()
	lines := auditLines(t, path)
	if len(lines) != 1 {
		t.Fatalf("audit lines = %d, want 1", len(lines))
	}
	var record commpolicy.AuditRecord
	if err := json.Unmarshal([]byte(lines[0]), &record); err != nil {
		t.Fatalf("unmarshal audit line %q: %v", lines[0], err)
	}
	return record
}

func TestSendAllowedDryDecision(t *testing.T) {
	dir := t.TempDir()
	policyPath := writeFile(t, filepath.Join(dir, "policy.json"), allowPolicy)
	auditPath := filepath.Join(dir, "audit.jsonl")

	var stdout, stderr bytes.Buffer
	code := run([]string{"send", "--policy", policyPath, "--to", "b", "--intent", "task", "--audit", auditPath, "--", "hi"}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("exit = %d, want 0 (stderr %q)", code, stderr.String())
	}
	if stdout.String() != "allowed\n" {
		t.Fatalf("stdout = %q, want %q", stdout.String(), "allowed\n")
	}
	if stderr.Len() != 0 {
		t.Fatalf("stderr = %q, want empty", stderr.String())
	}
	record := readAudit(t, auditPath)
	if !record.Allowed || record.Reason != "allowed" || record.From != "a" || record.To != "b" || record.Intent != commpolicy.IntentTask {
		t.Fatalf("audit = %+v", record)
	}
	if record.PolicyHash != commpolicy.PolicyHash(commpolicy.Policy{Seat: "a", Links: []commpolicy.Link{{From: "a", To: "b", Kind: commpolicy.KindDelegatesTo, Allow: true}}}) {
		t.Fatalf("audit policy hash = %q", record.PolicyHash)
	}
}

func TestSendDeniedWritesAuditAndSkipsDeliver(t *testing.T) {
	dir := t.TempDir()
	policyPath := writeFile(t, filepath.Join(dir, "policy.json"), denyPolicy)
	auditPath := filepath.Join(dir, "audit.jsonl")
	argsFile := filepath.Join(dir, "args.txt")

	t.Setenv("GO_WANT_HELPER_PROCESS", "1")
	t.Setenv("SEATCHECK_HELPER_ARGS", argsFile)
	t.Setenv("SEATCHECK_HELPER_EXIT", "0")

	var stdout, stderr bytes.Buffer
	code := run([]string{"send", "--policy", policyPath, "--to", "b", "--intent", "task", "--audit", auditPath, "--deliver-cmd", os.Args[0], "--", "hi"}, &stdout, &stderr)
	if code != 3 {
		t.Fatalf("exit = %d, want 3", code)
	}
	if stderr.String() != "denied: no link\n" {
		t.Fatalf("stderr = %q, want %q", stderr.String(), "denied: no link\n")
	}
	if stdout.Len() != 0 {
		t.Fatalf("stdout = %q, want empty", stdout.String())
	}
	if _, err := os.Stat(argsFile); !os.IsNotExist(err) {
		t.Fatalf("delivery command ran on a denied send (args file err = %v)", err)
	}
	record := readAudit(t, auditPath)
	if record.Allowed || record.Reason != "no link" || record.To != "b" {
		t.Fatalf("audit = %+v", record)
	}
}

func TestSendAllowedDeliverReceivesArgsAndExitCode(t *testing.T) {
	dir := t.TempDir()
	policyPath := writeFile(t, filepath.Join(dir, "policy.json"), allowPolicy)
	auditPath := filepath.Join(dir, "audit.jsonl")
	argsFile := filepath.Join(dir, "args.txt")

	t.Setenv("GO_WANT_HELPER_PROCESS", "1")
	t.Setenv("SEATCHECK_HELPER_ARGS", argsFile)
	t.Setenv("SEATCHECK_HELPER_EXIT", "7")

	var stdout, stderr bytes.Buffer
	code := run([]string{"send", "--policy", policyPath, "--to", "b", "--intent", "task", "--audit", auditPath, "--deliver-cmd", os.Args[0], "--", "hello", "world"}, &stdout, &stderr)
	if code != 7 {
		t.Fatalf("exit = %d, want 7 (stderr %q)", code, stderr.String())
	}
	got, err := os.ReadFile(argsFile)
	if err != nil {
		t.Fatalf("read helper args: %v", err)
	}
	if string(got) != "b\nhello\nworld\n" {
		t.Fatalf("helper args = %q, want %q", string(got), "b\nhello\nworld\n")
	}
	if !readAudit(t, auditPath).Allowed {
		t.Fatal("audit recorded a denied send for an allowed one")
	}
}

func TestSendBadFlagExits2(t *testing.T) {
	dir := t.TempDir()
	policyPath := writeFile(t, filepath.Join(dir, "policy.json"), allowPolicy)
	auditPath := filepath.Join(dir, "audit.jsonl")

	var stdout, stderr bytes.Buffer
	code := run([]string{"send", "--policy", policyPath, "--to", "b", "--intent", "task", "--audit", auditPath, "--bogus"}, &stdout, &stderr)
	if code != 2 {
		t.Fatalf("exit = %d, want 2", code)
	}
	if stderr.Len() == 0 {
		t.Fatal("stderr empty, want a clear message")
	}
}

func TestSendMalformedPolicyExits2(t *testing.T) {
	dir := t.TempDir()
	policyPath := writeFile(t, filepath.Join(dir, "policy.json"), `{"Seat":`)
	auditPath := filepath.Join(dir, "audit.jsonl")

	var stdout, stderr bytes.Buffer
	code := run([]string{"send", "--policy", policyPath, "--to", "b", "--intent", "task", "--audit", auditPath, "--", "hi"}, &stdout, &stderr)
	if code != 2 {
		t.Fatalf("exit = %d, want 2", code)
	}
	if !strings.Contains(stderr.String(), "parse policy") {
		t.Fatalf("stderr = %q, want a parse policy message", stderr.String())
	}
}

func TestSendAuditAppendsAcrossRuns(t *testing.T) {
	dir := t.TempDir()
	policyPath := writeFile(t, filepath.Join(dir, "policy.json"), allowPolicy)
	auditPath := filepath.Join(dir, "audit.jsonl")

	for i := 0; i < 2; i++ {
		var stdout, stderr bytes.Buffer
		if code := run([]string{"send", "--policy", policyPath, "--to", "b", "--intent", "task", "--audit", auditPath, "--", "hi"}, &stdout, &stderr); code != 0 {
			t.Fatalf("run %d exit = %d (stderr %q)", i, code, stderr.String())
		}
	}
	if got := auditLines(t, auditPath); len(got) != 2 {
		t.Fatalf("audit lines = %d, want 2", len(got))
	}
}

func TestAuditScanFindsBypassAndSkipsKnownWrapper(t *testing.T) {
	dir := t.TempDir()
	observed := writeFile(t, filepath.Join(dir, "observed.txt"),
		"rig send x\nFOO=1 /usr/bin/rig queue y\nagenthub-send rig send z\nrig status\n")

	var stdout, stderr bytes.Buffer
	code := run([]string{"audit-scan", "--known", "agenthub-send", "--file", observed}, &stdout, &stderr)
	if code != 4 {
		t.Fatalf("exit = %d, want 4 (stderr %q)", code, stderr.String())
	}
	want := "bypass-suspected: rig send x\nbypass-suspected: FOO=1 /usr/bin/rig queue y\n"
	if stdout.String() != want {
		t.Fatalf("stdout = %q, want %q", stdout.String(), want)
	}
}

func TestAuditScanCleanExits0(t *testing.T) {
	dir := t.TempDir()
	observed := writeFile(t, filepath.Join(dir, "observed.txt"), "agenthub-send rig send z\nrig status\n")

	var stdout, stderr bytes.Buffer
	code := run([]string{"audit-scan", "--known", "agenthub-send", "--file", observed}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("exit = %d, want 0 (stderr %q)", code, stderr.String())
	}
	if stdout.Len() != 0 {
		t.Fatalf("stdout = %q, want empty", stdout.String())
	}
}
