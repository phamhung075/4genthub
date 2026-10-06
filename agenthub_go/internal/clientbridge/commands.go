package clientbridge

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"agenthub/fastmcp/seat_management/domain/secretscan"
	"agenthub/internal/clientcmd"
)

// Commands is what the dispatcher appends: one verb, `bridge`.
//
// The Python bridge was four top-level commands (run, once, register, install-service); the Go client
// has one verb per package, so the four are sub-verbs here. Registering is an append in main.go by the
// dispatcher's owner, never an edit of this package's own file into theirs.
func Commands() []clientcmd.Command {
	return []clientcmd.Command{bridgeCommand{}}
}

type bridgeCommand struct{}

func (bridgeCommand) Name() string    { return "bridge" }
func (bridgeCommand) Summary() string { return "report this machine and its rigs to the cloud" }

// NeedsRig is true because run and once read `rig ps`; register and install-service ignore the tool
// they are handed, which is cheaper than a second verb.
func (bridgeCommand) NeedsRig() bool { return true }

func (c bridgeCommand) Run(ctx context.Context, rig *clientcmd.Rig, args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		bridgeUsage(stderr)
		return clientcmd.ExitUsage
	}
	switch args[0] {
	case "run":
		return bridgeRun(ctx, rig, args[1:], stdout, stderr, false)
	case "once":
		return bridgeOnce(ctx, rig, args[1:], stdout, stderr)
	case "register":
		return bridgeRegister(args[1:], stdout, stderr)
	case "install-service":
		return bridgeInstallService(stdout, stderr)
	case "help", "-h", "--help":
		bridgeUsage(stdout)
		return clientcmd.ExitOK
	default:
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge: unknown subcommand %q\n", args[0])
		bridgeUsage(stderr)
		return clientcmd.ExitUsage
	}
}

func bridgeUsage(w io.Writer) {
	_, _ = io.WriteString(w, "agenthub-client bridge <subcommand>\n\n"+
		"  run [--interval SECONDS] [--machine-id ID] [--once]   report on a loop (default 20s)\n"+
		"  once [--print] [--machine-id ID]                      report once; --print dumps the payload\n"+
		"  register [--machine-id ID] [--env-file PATH]          issue this machine's token\n"+
		"  install-service                                       print the systemd unit\n")
}

// bridgeFlags is the small parser these sub-verbs need. The Python used argparse; here a flag is
// either `--name value` or `--name`, and a bare value is a usage error rather than silently ignored.
func bridgeFlags(args []string, accepted map[string]bool, switches map[string]bool) (map[string]string, map[string]bool, error) {
	values := map[string]string{}
	set := map[string]bool{}
	for i := 0; i < len(args); i++ {
		name := args[i]
		if !strings.HasPrefix(name, "--") {
			return nil, nil, fmt.Errorf("unexpected argument %q", name)
		}
		name = strings.TrimPrefix(name, "--")
		if switches[name] {
			set[name] = true
			continue
		}
		if !accepted[name] {
			return nil, nil, fmt.Errorf("unknown flag --%s", name)
		}
		if i+1 >= len(args) {
			return nil, nil, fmt.Errorf("--%s needs a value", name)
		}
		i++
		values[name] = args[i]
	}
	return values, set, nil
}

func machineIDFrom(values map[string]string) (string, error) {
	if id := values["machine-id"]; id != "" {
		if !namePattern.MatchString(id) {
			return "", fmt.Errorf("invalid machine id %q", id)
		}
		return id, nil
	}
	host, err := os.Hostname()
	if err != nil {
		host = ""
	}
	return SanitizeMachineID(host), nil
}

func bridgeRun(ctx context.Context, rig *clientcmd.Rig, args []string, stdout, stderr io.Writer, onceOnly bool) int {
	values, switches, err := bridgeFlags(args,
		map[string]bool{"interval": true, "machine-id": true}, map[string]bool{"once": true})
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge run: %v\n", err)
		return clientcmd.ExitUsage
	}
	id, err := machineIDFrom(values)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge run: %v\n", err)
		return clientcmd.ExitUsage
	}
	interval := DefaultInterval
	if raw := values["interval"]; raw != "" {
		if _, err := fmt.Sscanf(raw, "%f", &interval); err != nil || interval <= 0 {
			_, _ = io.WriteString(stderr, "agenthub-client bridge run: --interval must be a positive number\n")
			return clientcmd.ExitUsage
		}
	}
	send, err := senderFromEnv()
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge run: %v\n", err)
		return clientcmd.ExitUsage
	}
	bridge := NewBridge(id, time.Duration(interval*float64(time.Second)), send,
		secretscan.KnownValuesFromEnv(os.Environ()), defaultPinsDir(), DefaultStatePath(), noteTo(stderr))
	_, _ = fmt.Fprintf(stderr, "agenthub-client bridge: reporting as %s\n", id)
	return bridge.Run(ctx, rig, onceOnly || switches["once"])
}

// bridgeOnce reports a single cycle. --print builds the payload and dumps it WITHOUT sending, which is
// the instrument the parity test uses against the Python bridge: the dump carries local_record, the
// report does not, and the difference is exactly the four-versus-five fields.
func bridgeOnce(ctx context.Context, rig *clientcmd.Rig, args []string, stdout, stderr io.Writer) int {
	values, switches, err := bridgeFlags(args, map[string]bool{"machine-id": true}, map[string]bool{"print": true})
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge once: %v\n", err)
		return clientcmd.ExitUsage
	}
	id, err := machineIDFrom(values)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge once: %v\n", err)
		return clientcmd.ExitUsage
	}
	known := secretscan.KnownValuesFromEnv(os.Environ())
	if switches["print"] {
		bridge := NewBridge(id, time.Duration(DefaultInterval*float64(time.Second)), nil,
			known, defaultPinsDir(), DefaultStatePath(), noteTo(stderr))
		payload := bridge.BuildPayload(rig)
		payload.LocalRecord = bridge.LocalRecord(payload.Seats)
		encoded, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			_, _ = fmt.Fprintf(stderr, "agenthub-client bridge once: cannot encode the payload: %v\n", err)
			return clientcmd.ExitRemote
		}
		_, _ = fmt.Fprintf(stdout, "%s\n", encoded)
		return clientcmd.ExitOK
	}
	send, err := senderFromEnv()
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge once: %v\n", err)
		return clientcmd.ExitUsage
	}
	bridge := NewBridge(id, time.Duration(DefaultInterval*float64(time.Second)), send,
		known, defaultPinsDir(), DefaultStatePath(), noteTo(stderr))
	return bridge.Run(ctx, rig, true)
}

// bridgeRegister issues this machine's token with the USER credential and stores it where the service
// unit reads it, at mode 0600. The token is never printed: the line names the file instead.
func bridgeRegister(args []string, stdout, stderr io.Writer) int {
	values, _, err := bridgeFlags(args, map[string]bool{"machine-id": true, "env-file": true}, nil)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge register: %v\n", err)
		return clientcmd.ExitUsage
	}
	baseURL, userToken := os.Getenv("AGENTHUB_URL"), os.Getenv("AGENTHUB_TOKEN")
	if baseURL == "" || userToken == "" {
		_, _ = io.WriteString(stderr,
			"agenthub-client bridge register: AGENTHUB_URL and AGENTHUB_TOKEN (the user token) must be set "+
				"to register a machine\n")
		return clientcmd.ExitUsage
	}
	id, err := machineIDFrom(values)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge register: %v\n", err)
		return clientcmd.ExitUsage
	}
	token, err := registerMachine(baseURL, userToken, id)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge: %v\n", err)
		return clientcmd.ExitRemote
	}
	envFile := values["env-file"]
	if envFile == "" {
		envFile = DefaultEnvFile()
	}
	if err := writeEnvFile(envFile, baseURL, token); err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge: %v\n", err)
		return clientcmd.ExitRemote
	}
	_, _ = fmt.Fprintf(stdout, "registered machine %q; its token is in %s (mode 0600, not printed). "+
		"Run the bridge with --machine-id %q so the token and the report agree.\n", id, envFile, id)
	return clientcmd.ExitOK
}

// bridgeInstallService prints the systemd unit. The Python unit named a Python interpreter and a
// script; this one names THE BINARY ITSELF and the sub-verb, which is the whole point of the
// consolidation: one artefact on the machine, no interpreter to be present.
func bridgeInstallService(stdout, stderr io.Writer) int {
	binary, err := os.Executable()
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "agenthub-client bridge install-service: cannot resolve this binary: %v\n", err)
		return clientcmd.ExitRemote
	}
	_, _ = fmt.Fprintf(stdout, `[Unit]
Description=4genthub OpenRig status bridge
After=network-online.target

[Service]
EnvironmentFile=%%h/.config/agenthub-bridge.env
ExecStart=%s bridge run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
`, binary)
	return clientcmd.ExitOK
}

// noteTo turns a writer into the bridge's note sink: every line is prefixed and flushed, so an
// operator reading the journal sees the same sentences the Python printed.
func noteTo(stderr io.Writer) func(string) {
	return func(message string) {
		_, _ = fmt.Fprintf(stderr, "openrig-bridge: %s\n", message)
	}
}

// senderFromEnv builds the sender from the machine credential. A missing one is a usage error naming
// the register verb, because a bridge without a token cannot report and must not start quietly.
func senderFromEnv() (Sender, error) {
	baseURL, token := os.Getenv("AGENTHUB_URL"), os.Getenv("AGENTHUB_MACHINE_TOKEN")
	if baseURL == "" || token == "" {
		return nil, fmt.Errorf("AGENTHUB_URL and AGENTHUB_MACHINE_TOKEN must be set; run " +
			"`agenthub-client bridge register` once (it needs AGENTHUB_TOKEN, the user token) to issue " +
			"this machine's token")
	}
	client := &http.Client{Timeout: SendTimeout}
	endpoint := strings.TrimRight(baseURL, "/") + statusPath
	return func(body []byte) (int, []byte) {
		request, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(body))
		if err != nil {
			return 0, []byte(err.Error())
		}
		request.Header.Set("Authorization", "Bearer "+token)
		request.Header.Set("Content-Type", "application/json")
		response, err := client.Do(request)
		if err != nil {
			return 0, []byte(err.Error())
		}
		defer func() { _ = response.Body.Close() }()
		// The body is read on an error status too: it is small and bounded, and a caller naming what
		// the server said is better than a bare code.
		answer, _ := io.ReadAll(io.LimitReader(response.Body, MaxResponseSize))
		return response.StatusCode, answer
	}, nil
}

// registerMachine posts the machine id with the USER credential and returns the issued token. The
// token is never logged: a non-2xx answer or a body without a token is a loud failure.
func registerMachine(baseURL, userToken, machineID string) (string, error) {
	body, err := json.Marshal(map[string]string{"machine_id": machineID})
	if err != nil {
		return "", fmt.Errorf("cannot encode the registration: %w", err)
	}
	request, err := http.NewRequest(http.MethodPost, strings.TrimRight(baseURL, "/")+registerPath, bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("machine registration failed: %w", err)
	}
	request.Header.Set("Authorization", "Bearer "+userToken)
	request.Header.Set("Content-Type", "application/json")
	response, err := (&http.Client{Timeout: SendTimeout}).Do(request)
	if err != nil {
		return "", fmt.Errorf("machine registration failed: %w", err)
	}
	defer func() { _ = response.Body.Close() }()
	answer, _ := io.ReadAll(io.LimitReader(response.Body, MaxResponseSize))
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return "", fmt.Errorf("machine registration refused: HTTP %d", response.StatusCode)
	}
	var issued struct {
		Token string `json:"token"`
	}
	if err := json.Unmarshal(answer, &issued); err != nil {
		return "", fmt.Errorf("machine registration returned no JSON token")
	}
	if issued.Token == "" {
		return "", fmt.Errorf("machine registration returned no token")
	}
	return issued.Token, nil
}

// writeEnvFile writes AGENTHUB_URL and AGENTHUB_MACHINE_TOKEN into path at mode 0600, preserving every
// other line, so an existing file keeps whatever else it held. The mode is set explicitly after the
// write because O_CREAT's mode is masked by the umask.
func writeEnvFile(path, baseURL, machineToken string) error {
	kept := []string{}
	if existing, err := os.ReadFile(path); err == nil {
		for _, line := range strings.Split(string(existing), "\n") {
			name, _, _ := strings.Cut(line, "=")
			if strings.TrimSpace(name) == "AGENTHUB_URL" || strings.TrimSpace(name) == "AGENTHUB_MACHINE_TOKEN" {
				continue
			}
			if line != "" {
				kept = append(kept, line)
			}
		}
	}
	kept = append(kept, "AGENTHUB_URL="+baseURL, "AGENTHUB_MACHINE_TOKEN="+machineToken)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return fmt.Errorf("cannot write %s: %w", path, err)
	}
	if err := os.WriteFile(path, []byte(strings.Join(kept, "\n")+"\n"), 0o600); err != nil {
		return fmt.Errorf("cannot write %s: %w", path, err)
	}
	if err := os.Chmod(path, 0o600); err != nil {
		return fmt.Errorf("cannot set the mode of %s: %w", path, err)
	}
	return nil
}

// The three locations the Python client used, named here so a test can point them at a scratch tree.
func defaultPinsDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = ""
	}
	return filepath.Join(home, ".openrig", "agenthub-seats")
}

// DefaultStatePath is the sync record the bridge keeps beside the pins.
func DefaultStatePath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = ""
	}
	return filepath.Join(home, ".openrig", "bridge-sync.json")
}

// DefaultEnvFile is where register stores the machine credential, and where the service unit reads
// it (EnvironmentFile=%h/.config/agenthub-bridge.env).
func DefaultEnvFile() string {
	home, err := os.UserHomeDir()
	if err != nil {
		home = ""
	}
	return filepath.Join(home, ".config", "agenthub-bridge.env")
}
