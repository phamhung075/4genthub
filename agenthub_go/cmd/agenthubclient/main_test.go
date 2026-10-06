package main

import (
	"bytes"
	"errors"
	"strings"
	"testing"

	"agenthub/internal/clientcmd"
)

func rigMissing(t *testing.T) {
	t.Helper()
	previous := clientcmd.LookPath
	clientcmd.LookPath = func(string) (string, error) { return "", errors.New("not found") }
	t.Cleanup(func() { clientcmd.LookPath = previous })
}

// TestUnportedCommandRefusesRatherThanStubbing closes the hole a stub would leave: a command that
// exists in the Python client and not yet here must say exactly that and exit non-zero. A command that
// answered an empty success would be the "looks complete and is not" shape in a new place.
func TestUnportedCommandRefusesRatherThanStubbing(t *testing.T) {
	rigMissing(t)
	for _, args := range [][]string{
		{"feedback", "oops"},
		{"seatcheck", "send", "x", "y"},
		{"sync", "status", "4genthub-dev"},
		{"sync", "pull", "4genthub-dev", "alpha"},
	} {
		var out, errOut bytes.Buffer
		if code := run(args, &out, &errOut); code != clientcmd.ExitUnavailable {
			t.Errorf("%v: exit code = %d, want %d", args, code, clientcmd.ExitUnavailable)
		}
		if !strings.Contains(errOut.String(), "not ported") {
			t.Errorf("%v: message = %q, want it to say the command is not ported", args, errOut.String())
		}
		if out.Len() != 0 {
			t.Errorf("%v: stdout = %q, want nothing: a refused command does no partial work", args, out.String())
		}
	}
}

// TestBridgeIsRefusedByThePlatformMatrixBeforeItIsRefusedAsUnported: `bridge` is the one pending
// command that needs rig, so with no rig it must fail on the MATRIX - the reason a user can act on -
// rather than on the porting note.
func TestBridgeIsRefusedByThePlatformMatrixBeforeItIsRefusedAsUnported(t *testing.T) {
	rigMissing(t)
	var out, errOut bytes.Buffer
	if code := run([]string{"bridge", "once"}, &out, &errOut); code != clientcmd.ExitUnavailable {
		t.Fatalf("exit code = %d, want %d", code, clientcmd.ExitUnavailable)
	}
	if !strings.Contains(errOut.String(), "rig is not on PATH") {
		t.Errorf("message = %q, want the MATRIX's reason, not the porting note", errOut.String())
	}
}

// TestUsageAndVersionAreTheOnlyFreeCommands: no arguments is a usage error, an unknown command is a
// usage error, and the two commands that need nothing at all succeed.
func TestUsageAndVersionAreTheOnlyFreeCommands(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run(nil, &out, &errOut); code != clientcmd.ExitUsage {
		t.Errorf("no arguments: exit code = %d, want %d", code, clientcmd.ExitUsage)
	}
	if !strings.Contains(errOut.String(), "commands:") {
		t.Errorf("no arguments: stderr = %q, want the command list", errOut.String())
	}

	out.Reset()
	errOut.Reset()
	if code := run([]string{"nonsense"}, &out, &errOut); code != clientcmd.ExitUsage {
		t.Errorf("unknown command: exit code = %d, want %d", code, clientcmd.ExitUsage)
	}

	out.Reset()
	errOut.Reset()
	if code := run([]string{"version"}, &out, &errOut); code != clientcmd.ExitOK {
		t.Errorf("version: exit code = %d, want %d", code, clientcmd.ExitOK)
	}
	if !strings.Contains(out.String(), "agenthub-client "+clientVersion) {
		t.Errorf("version output = %q, want the client version", out.String())
	}
}

// TestSyncRefusesAnUnknownVerbAsUsageNotAsUnavailable: an unknown verb is the CALLER's error, and
// telling it apart from "not ported yet" is what keeps a typo from reading as a missing feature.
func TestSyncRefusesAnUnknownVerbAsUsageNotAsUnavailable(t *testing.T) {
	var out, errOut bytes.Buffer
	if code := run([]string{"sync", "nonsense"}, &out, &errOut); code != clientcmd.ExitUsage {
		t.Errorf("exit code = %d, want %d (a typo is not a missing feature)", code, clientcmd.ExitUsage)
	}
	if !strings.Contains(errOut.String(), "unknown verb") {
		t.Errorf("message = %q, want it to say the verb is unknown", errOut.String())
	}

	out.Reset()
	errOut.Reset()
	if code := run([]string{"sync"}, &out, &errOut); code != clientcmd.ExitUsage {
		t.Errorf("sync with no verb: exit code = %d, want %d", code, clientcmd.ExitUsage)
	}
}
