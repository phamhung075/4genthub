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

func runSend(args []string, stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("send", flag.ContinueOnError)
	fs.SetOutput(stderr)
	policyPath := fs.String("policy", "", "path to the pinned policy JSON")
	to := fs.String("to", "", "recipient seat")
	intentName := fs.String("intent", "", "message intent")
	auditPath := fs.String("audit", "", "path to the audit JSONL file")
	deliverCmd := fs.String("deliver-cmd", "", "program to run when the send is allowed")
	fs.Usage = func() {
		fmt.Fprintln(stderr, "usage: seatcheck send --policy <policy.json> --to <seat> --intent <task|escalation|report|question|notice> --audit <audit.jsonl> [--deliver-cmd <path>] -- <message words...>")
	}
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *policyPath == "" || *to == "" || *intentName == "" || *auditPath == "" {
		fmt.Fprintln(stderr, "seatcheck send: --policy, --to, --intent and --audit are required")
		return 2
	}
	intent, ok := intents[*intentName]
	if !ok {
		fmt.Fprintf(stderr, "seatcheck send: unknown intent %q\n", *intentName)
		return 2
	}

	data, err := os.ReadFile(*policyPath)
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
	if err := appendAudit(*auditPath, record); err != nil {
		fmt.Fprintf(stderr, "seatcheck send: audit: %v\n", err)
		return 1
	}
	if !decision.Allowed {
		fmt.Fprintf(stderr, "denied: %s\n", decision.Reason)
		return 3
	}
	if *deliverCmd == "" {
		fmt.Fprintln(stdout, "allowed")
		return 0
	}
	return deliver(*deliverCmd, *to, fs.Args(), stdout, stderr)
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

func deliver(program, to string, words []string, stdout, stderr io.Writer) int {
	cmd := exec.Command(program, append([]string{to}, words...)...)
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
