// Command seatcheck checks a pinned communication policy before a seat sends a
// message, and records the outcome. It is what a seat runs instead of calling
// `rig send` directly.
package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"agenthub/fastmcp/seat_management/domain/commpolicy"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprintln(stderr, "usage: seatcheck <send|audit-scan> ...")
		return 2
	}
	switch args[0] {
	case "send":
		return runSend(args[1:], stdout, stderr)
	case "audit-scan":
		return runAuditScan(args[1:], stdout, stderr)
	default:
		fmt.Fprintf(stderr, "seatcheck: unknown subcommand %q\n", args[0])
		return 2
	}
}

var intents = map[string]commpolicy.Intent{
	"task":       commpolicy.IntentTask,
	"escalation": commpolicy.IntentEscalation,
	"report":     commpolicy.IntentReport,
	"question":   commpolicy.IntentQuestion,
	"notice":     commpolicy.IntentNotice,
}

// defaultPinsDir is where scripts/openrig_seat_sync.py writes the pinned seat directories
// (its DEFAULT_OUT), relative to the home directory.
const defaultPinsDir = ".openrig/agenthub-seats"

// Package-level seams, replaced by tests.
var (
	// identify returns who the calling seat is.
	identify = rigWhoami
	// deliver sends text to the session named target and returns the exit code.
	deliver = rigSend
)

func runSend(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("send", flag.ContinueOnError)
	fs.SetOutput(stderr)
	to := fs.String("to", "", "recipient seat")
	intentName := fs.String("intent", "", "message intent")
	pins := fs.String("pins", "", "pinned seats directory (default ~/"+defaultPinsDir+")")
	fs.Usage = func() {
		fmt.Fprintln(stderr, "usage: seatcheck send --to <seat> --intent <task|escalation|report|question|notice> -- <message words...>")
	}
	if err := fs.Parse(args); err != nil {
		return 2
	}
	words := fs.Args()
	if *to == "" || *intentName == "" || len(words) == 0 {
		fmt.Fprintln(stderr, "seatcheck send: --to, --intent and a message are required")
		return 2
	}
	intent, ok := intents[*intentName]
	if !ok {
		fmt.Fprintf(stderr, "seatcheck send: unknown intent %q\n", *intentName)
		return 2
	}
	if *pins == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			fmt.Fprintf(stderr, "seatcheck send: home directory: %v\n", err)
			return 2
		}
		*pins = filepath.Join(home, defaultPinsDir)
	}
	who, err := identify()
	if err != nil {
		fmt.Fprintf(stderr, "seatcheck send: identity: %v\n", err)
		return 2
	}
	seatDir := filepath.Join(*pins, who.Rig, who.Member)

	data, err := os.ReadFile(filepath.Join(seatDir, "policy.json"))
	if err != nil {
		fmt.Fprintf(stderr, "seatcheck send: read policy: %v\n", err)
		return 2
	}
	policy, err := commpolicy.ParsePolicy(data)
	if err != nil {
		fmt.Fprintf(stderr, "seatcheck send: parse policy: %v\n", err)
		return 2
	}

	decision := commpolicy.Decide(policy, *to, intent)
	record := commpolicy.AuditRecord{
		At:         time.Now().UTC(),
		From:       policy.Seat,
		To:         *to,
		Intent:     intent,
		Allowed:    decision.Allowed,
		Reason:     decision.Reason,
		PolicyHash: commpolicy.PolicyHash(policy),
	}
	if err := appendAudit(filepath.Join(seatDir, "audit.jsonl"), record); err != nil {
		fmt.Fprintf(stderr, "seatcheck send: audit: %v\n", err)
		return 1
	}
	if !decision.Allowed {
		fmt.Fprintf(stderr, "denied: %s\n", decision.Reason)
		return 3
	}
	// The audit line above records the policy decision only; a recipient the roster does not
	// list fails here, after an allowed decision.
	// rig send resolves only full session names (<pod>-<member>@<rig>), which the roster of
	// rig whoami carries.
	session, ok := who.Peers[*to]
	if !ok {
		fmt.Fprintf(stderr, "seatcheck send: %q is not a seat of rig %q\n", *to, who.Rig)
		return 1
	}
	return deliver(session, strings.Join(words, " "), stdout, stderr)
}

// identity is the calling seat: its rig, its member name and the session name of every other
// member of the rig, keyed by member name.
type identity struct {
	Rig, Member string
	Peers       map[string]string
}

// rigWhoami reads the calling seat's identity from `rig whoami --json`.
func rigWhoami() (identity, error) {
	out, err := exec.Command("rig", "whoami", "--json").Output()
	if err != nil {
		return identity{}, fmt.Errorf("rig whoami: %w", err)
	}
	return parseWhoami(out)
}

func parseWhoami(data []byte) (identity, error) {
	var who struct {
		Identity struct {
			RigName  string `json:"rigName"`
			MemberID string `json:"memberId"`
		} `json:"identity"`
		Peers []struct {
			LogicalID   string `json:"logicalId"`
			SessionName string `json:"sessionName"`
		} `json:"peers"`
	}
	if err := json.Unmarshal(data, &who); err != nil {
		return identity{}, fmt.Errorf("parse rig whoami: %w", err)
	}
	rig, member := who.Identity.RigName, who.Identity.MemberID
	if rig == "" || member == "" {
		return identity{}, errors.New("rig whoami returned no rig or member")
	}
	// A logical id is <pod>.<member>; the member is the part after the first dot (the pod is not
	// always the rig name). A member name is unique in a rig, so a repeat is an error, not a
	// silent last-one-wins.
	peers := make(map[string]string, len(who.Peers))
	for _, p := range who.Peers {
		_, name, ok := strings.Cut(p.LogicalID, ".")
		if !ok || name == "" || p.SessionName == "" {
			continue
		}
		if previous, dup := peers[name]; dup {
			return identity{}, fmt.Errorf("member %q is in two pods of rig %q: %s and %s", name, rig, previous, p.SessionName)
		}
		peers[name] = p.SessionName
	}
	return identity{Rig: rig, Member: member, Peers: peers}, nil
}

func appendAudit(path string, record commpolicy.AuditRecord) error {
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0600)
	if err != nil {
		return err
	}
	defer f.Close()
	line, err := json.Marshal(record)
	if err != nil {
		return err
	}
	_, err = f.Write(append(line, '\n'))
	return err
}

// rigSend delivers text to target with `rig send`; its exit code is passed through.
func rigSend(target, text string, stdout, stderr io.Writer) int {
	cmd := exec.Command("rig", "send", target, text)
	cmd.Stdin = os.Stdin
	cmd.Stdout = stdout
	cmd.Stderr = stderr
	if err := cmd.Run(); err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			return exitErr.ExitCode()
		}
		fmt.Fprintf(stderr, "seatcheck send: deliver: %v\n", err)
		return 1
	}
	return 0
}

func runAuditScan(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("audit-scan", flag.ContinueOnError)
	fs.SetOutput(stderr)
	known := fs.String("known", "", "comma separated wrapper command names")
	file := fs.String("file", "", "file of observed command lines, one per line")
	fs.Usage = func() {
		fmt.Fprintln(stderr, "usage: seatcheck audit-scan --known <wrapper names comma separated> --file <path to a text file of observed command lines, one per line>")
	}
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *file == "" {
		fmt.Fprintln(stderr, "seatcheck audit-scan: --file is required")
		return 2
	}

	var names []string
	for _, name := range strings.Split(*known, ",") {
		if name = strings.TrimSpace(name); name != "" {
			names = append(names, name)
		}
	}

	data, err := os.ReadFile(*file)
	if err != nil {
		fmt.Fprintf(stderr, "seatcheck audit-scan: read file: %v\n", err)
		return 2
	}
	found := false
	for _, line := range strings.Split(string(data), "\n") {
		if line == "" {
			continue
		}
		if commpolicy.BypassSuspected(names, line) {
			fmt.Fprintf(stdout, "bypass-suspected: %s\n", line)
			found = true
		}
	}
	if found {
		return 4
	}
	return 0
}
