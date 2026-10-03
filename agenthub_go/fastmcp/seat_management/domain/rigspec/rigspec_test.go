package rigspec

import (
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

type parsedRig struct {
	Version string `yaml:"version"`
	Name    string `yaml:"name"`
	Pods    []struct {
		ID      string `yaml:"id"`
		Label   string `yaml:"label"`
		Members []struct {
			ID       string `yaml:"id"`
			AgentRef string `yaml:"agent_ref"`
			Profile  string `yaml:"profile"`
			Runtime  string `yaml:"runtime"`
			Model    string `yaml:"model"`
			Cwd      string `yaml:"cwd"`
		} `yaml:"members"`
		Edges []struct {
			Kind string `yaml:"kind"`
			From string `yaml:"from"`
			To   string `yaml:"to"`
		} `yaml:"edges"`
	} `yaml:"pods"`
	Edges []struct {
		Kind string `yaml:"kind"`
		From string `yaml:"from"`
		To   string `yaml:"to"`
	} `yaml:"edges"`
}

func parseRig(t *testing.T, yamlText string) parsedRig {
	t.Helper()
	var parsed parsedRig
	if err := yaml.Unmarshal([]byte(yamlText), &parsed); err != nil {
		t.Fatalf("parse rendered rig.yaml: %v\n%s", err, yamlText)
	}
	return parsed
}

func TestRenderRoomRendersPodMembersAndEdges(t *testing.T) {
	out, err := RenderRoom("dev", "Development",
		[]Seat{
			{Key: "lead", Runtime: "claude-code"},
			{Key: "dev", Runtime: "codex", Model: "gpt-5"},
			{Key: "qa", Runtime: "claude-code"},
		},
		[]Edge{
			{Kind: "delegates_to", From: "lead", To: "dev"},
			{Kind: "delegates_to", From: "dev", To: "qa"},
			{Kind: "can_observe", From: "lead", To: "qa"},
		})
	if err != nil {
		t.Fatalf("RenderRoom: %v", err)
	}

	if !strings.Contains(out, "version: \"0.2\"") {
		t.Fatalf("version is not quoted 0.2:\n%s", out)
	}
	if !strings.Contains(out, "\nedges: []\n") {
		t.Fatalf("top-level edges are not an empty list:\n%s", out)
	}

	parsed := parseRig(t, out)
	if parsed.Version != "0.2" || parsed.Name != "dev" {
		t.Fatalf("version/name = %q/%q, want 0.2/dev", parsed.Version, parsed.Name)
	}
	if len(parsed.Pods) != 1 {
		t.Fatalf("pods = %d, want 1", len(parsed.Pods))
	}
	pod := parsed.Pods[0]
	if pod.ID != "dev" || pod.Label != "Development" {
		t.Fatalf("pod id/label = %q/%q", pod.ID, pod.Label)
	}

	memberIDs := make([]string, len(pod.Members))
	for i, m := range pod.Members {
		memberIDs[i] = m.ID
	}
	if want := []string{"dev", "lead", "qa"}; !reflect.DeepEqual(memberIDs, want) {
		t.Fatalf("member ids = %v, want %v", memberIDs, want)
	}
	lead := pod.Members[1]
	if lead.AgentRef != "local:agents/lead" || lead.Profile != "default" || lead.Runtime != "claude-code" || lead.Cwd != "." || lead.Model != "" {
		t.Fatalf("lead member = %+v", lead)
	}
	if pod.Members[0].Model != "gpt-5" {
		t.Fatalf("dev model = %q, want gpt-5", pod.Members[0].Model)
	}
	if got := strings.Count(out, "model:"); got != 1 {
		t.Fatalf("model key rendered %d times, want only the non-empty one:\n%s", got, out)
	}

	wantEdges := []struct{ Kind, From, To string }{
		{"can_observe", "lead", "qa"},
		{"delegates_to", "dev", "qa"},
		{"delegates_to", "lead", "dev"},
	}
	if len(pod.Edges) != len(wantEdges) {
		t.Fatalf("pod edges = %+v", pod.Edges)
	}
	for i, want := range wantEdges {
		got := pod.Edges[i]
		if got.Kind != want.Kind || got.From != want.From || got.To != want.To {
			t.Fatalf("pod edge %d = %+v, want %+v", i, got, want)
		}
	}
	if len(parsed.Edges) != 0 {
		t.Fatalf("top-level edges = %+v, want empty", parsed.Edges)
	}
}

func TestRenderRoomDeterministic(t *testing.T) {
	first, err := RenderRoom("dev", "Development",
		[]Seat{{Key: "lead", Runtime: "claude-code"}, {Key: "dev", Runtime: "codex"}, {Key: "qa", Runtime: "claude-code"}},
		[]Edge{{Kind: "delegates_to", From: "lead", To: "dev"}, {Kind: "can_observe", From: "lead", To: "qa"}})
	if err != nil {
		t.Fatalf("first RenderRoom: %v", err)
	}
	second, err := RenderRoom("dev", "Development",
		[]Seat{{Key: "qa", Runtime: "claude-code"}, {Key: "dev", Runtime: "codex"}, {Key: "lead", Runtime: "claude-code"}},
		[]Edge{{Kind: "can_observe", From: "lead", To: "qa"}, {Kind: "delegates_to", From: "lead", To: "dev"}})
	if err != nil {
		t.Fatalf("second RenderRoom: %v", err)
	}
	if first != second {
		t.Fatalf("rendering the same room in different input order differs:\n--- first ---\n%s\n--- second ---\n%s", first, second)
	}
}

func TestRenderRoomRejectsInvalidInput(t *testing.T) {
	seats := []Seat{{Key: "lead", Runtime: "claude-code"}, {Key: "dev", Runtime: "codex"}}
	cases := []struct {
		name     string
		roomSlug string
		roomName string
		seats    []Seat
		edges    []Edge
		want     string
	}{
		{"bad room slug", "bad.slug", "Dev", seats, nil, "room slug"},
		{"empty room name", "dev", "", seats, nil, "room name is required"},
		{"no seats", "dev", "Dev", nil, nil, "has no seats"},
		{"bad seat key", "dev", "Dev", []Seat{{Key: "bad.key", Runtime: "claude-code"}}, nil, "seats[0] key"},
		{"duplicate seat", "dev", "Dev", []Seat{{Key: "lead", Runtime: "codex"}, {Key: "lead", Runtime: "codex"}}, nil, "duplicate seat key"},
		{"bad runtime", "dev", "Dev", []Seat{{Key: "lead", Runtime: "python"}}, nil, "runtime"},
		{"bad edge kind", "dev", "Dev", seats, []Edge{{Kind: "reports_to", From: "lead", To: "dev"}}, "kind"},
		{"unknown from", "dev", "Dev", seats, []Edge{{Kind: "delegates_to", From: "ghost", To: "dev"}}, "from"},
		{"unknown to", "dev", "Dev", seats, []Edge{{Kind: "delegates_to", From: "lead", To: "ghost"}}, "to"},
		{"self edge", "dev", "Dev", seats, []Edge{{Kind: "delegates_to", From: "lead", To: "lead"}}, "same seat"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			out, err := RenderRoom(c.roomSlug, c.roomName, c.seats, c.edges)
			if err == nil {
				t.Fatalf("RenderRoom succeeded, want error containing %q:\n%s", c.want, out)
			}
			if !strings.Contains(err.Error(), c.want) {
				t.Fatalf("error = %v, want it to contain %q", err, c.want)
			}
		})
	}
}

func writeAgentDir(t *testing.T, root, key, runtime string) {
	t.Helper()
	dir := filepath.Join(root, "agents", key)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatalf("mkdir %s: %v", dir, err)
	}
	content := "name: " + key + "\nversion: \"1\"\ndefaults:\n  runtime: " + runtime + "\nprofiles:\n  default: {}\n"
	if err := os.WriteFile(filepath.Join(dir, "agent.yaml"), []byte(content), 0o644); err != nil {
		t.Fatalf("write agent.yaml: %v", err)
	}
}

// TestRenderRoomRigCLI validates a rendered room with the real rig CLI. OpenRig's
// validate/preflight endpoints need a running daemon, so a missing daemon skips
// rather than fails (same seam as the seatrenderer test).
func TestRenderRoomRigCLI(t *testing.T) {
	rigPath, err := exec.LookPath("rig")
	if err != nil {
		t.Skip("rig binary not on PATH")
	}

	dir := t.TempDir()
	seats := []Seat{
		{Key: "lead", Runtime: "claude-code"},
		{Key: "dev", Runtime: "codex"},
		{Key: "qa", Runtime: "claude-code"},
	}
	edges := []Edge{
		{Kind: "delegates_to", From: "lead", To: "dev"},
		{Kind: "delegates_to", From: "dev", To: "qa"},
		{Kind: "can_observe", From: "lead", To: "qa"},
	}
	rendered, err := RenderRoom("dev", "Development", seats, edges)
	if err != nil {
		t.Fatalf("RenderRoom: %v", err)
	}
	rigFile := filepath.Join(dir, "rig.yaml")
	if err := os.WriteFile(rigFile, []byte(rendered), 0o644); err != nil {
		t.Fatalf("write rig.yaml: %v", err)
	}
	for _, seat := range seats {
		writeAgentDir(t, dir, seat.Key, seat.Runtime)
	}

	validateOut, err := exec.Command(rigPath, "spec", "validate", rigFile).CombinedOutput()
	if err != nil && strings.Contains(string(validateOut), "Daemon not running") {
		t.Skipf("rig validate needs a running OpenRig daemon: %s", strings.TrimSpace(string(validateOut)))
	}
	if err != nil {
		t.Fatalf("rig spec validate failed: %v\n%s", err, validateOut)
	}
	if !strings.Contains(string(validateOut), "Rig spec valid") {
		t.Fatalf("unexpected rig spec validate output:\n%s", validateOut)
	}
	t.Logf("rig spec validate: %s", strings.TrimSpace(string(validateOut)))

	preflightOut, err := exec.Command(rigPath, "spec", "preflight", rigFile).CombinedOutput()
	if err != nil && strings.Contains(string(preflightOut), "Daemon not running") {
		t.Skipf("rig preflight needs a running OpenRig daemon: %s", strings.TrimSpace(string(preflightOut)))
	}
	if err != nil {
		t.Fatalf("rig spec preflight failed: %v\n%s", err, preflightOut)
	}
	if strings.Contains(string(preflightOut), "Preflight errors:") {
		t.Fatalf("rig spec preflight reported errors:\n%s", preflightOut)
	}
	t.Logf("rig spec preflight: %s", strings.TrimSpace(string(preflightOut)))
}
