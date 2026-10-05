package rigspec

import (
	"fmt"
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
			{Key: "lead", Runtime: "claude-code", PermissionPolicy: "standard"},
			{Key: "dev", Runtime: "codex", Model: "gpt-5", PermissionPolicy: "standard"},
			{Key: "qa", Runtime: "claude-code", PermissionPolicy: "standard"},
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
		[]Seat{{Key: "lead", Runtime: "claude-code", PermissionPolicy: "standard"}, {Key: "dev", Runtime: "codex", PermissionPolicy: "standard"}, {Key: "qa", Runtime: "claude-code", PermissionPolicy: "standard"}},
		[]Edge{{Kind: "delegates_to", From: "lead", To: "dev"}, {Kind: "can_observe", From: "lead", To: "qa"}})
	if err != nil {
		t.Fatalf("first RenderRoom: %v", err)
	}
	second, err := RenderRoom("dev", "Development",
		[]Seat{{Key: "qa", Runtime: "claude-code", PermissionPolicy: "standard"}, {Key: "dev", Runtime: "codex", PermissionPolicy: "standard"}, {Key: "lead", Runtime: "claude-code", PermissionPolicy: "standard"}},
		[]Edge{{Kind: "can_observe", From: "lead", To: "qa"}, {Kind: "delegates_to", From: "lead", To: "dev"}})
	if err != nil {
		t.Fatalf("second RenderRoom: %v", err)
	}
	if first != second {
		t.Fatalf("rendering the same room in different input order differs:\n--- first ---\n%s\n--- second ---\n%s", first, second)
	}
}

func TestRenderRoomRejectsInvalidInput(t *testing.T) {
	seats := []Seat{{Key: "lead", Runtime: "claude-code", PermissionPolicy: "standard"}, {Key: "dev", Runtime: "codex", PermissionPolicy: "standard"}}
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
		{"bad seat key", "dev", "Dev", []Seat{{Key: "bad.key", Runtime: "claude-code", PermissionPolicy: "standard"}}, nil, "seats[0] key"},
		{"duplicate seat", "dev", "Dev", []Seat{{Key: "lead", Runtime: "codex", PermissionPolicy: "standard"}, {Key: "lead", Runtime: "codex", PermissionPolicy: "standard"}}, nil, "duplicate seat key"},
		{"bad runtime", "dev", "Dev", []Seat{{Key: "lead", Runtime: "python", PermissionPolicy: "standard"}}, nil, "runtime"},
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
	for _, policy := range []string{"locked", "standard", "yolo", "none"} {
		t.Run("policy="+policy, func(t *testing.T) { validateRoomWithRig(t, rigPath, policy) })
	}
}

func validateRoomWithRig(t *testing.T, rigPath, policy string) {
	t.Helper()

	dir := t.TempDir()
	seats := []Seat{
		{Key: "lead", Runtime: "claude-code", PermissionPolicy: policy},
		{Key: "dev", Runtime: "codex", PermissionPolicy: policy},
		{Key: "qa", Runtime: "claude-code", PermissionPolicy: policy},
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
	if strings.Count(rendered, "permission_policy: "+permissionPolicyValue(policy)) != len(seats) {
		t.Fatalf("rendered spec does not carry %s on every member:\n%s", policy, rendered)
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

func TestFindLaunchCycle(t *testing.T) {
	edge := func(kind, from, to string) Edge { return Edge{Kind: kind, From: from, To: to} }
	cases := []struct {
		name  string
		edges []Edge
		want  string
	}{
		{"none", nil, ""},
		{"self loop", []Edge{edge("delegates_to", "a", "a")}, "a>a"},
		{"self loop spawned_by", []Edge{edge("spawned_by", "a", "a")}, "a>a"},
		{"chain", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "c")}, ""},
		{"opposite delegates_to", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "a")}, "a>b>a"},
		{"three seats", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "c"), edge("delegates_to", "c", "a")}, "a>b>c>a"},
		{"spawned_by is the reverse order", []Edge{edge("spawned_by", "a", "b"), edge("spawned_by", "b", "c"), edge("spawned_by", "c", "a")}, "a>c>b>a"},
		{"delegates_to and spawned_by together", []Edge{edge("delegates_to", "a", "b"), edge("spawned_by", "a", "b")}, "a>b>a"},
		{"spawned_by parent and delegates_to child agree", []Edge{edge("delegates_to", "a", "b"), edge("spawned_by", "b", "a")}, ""},
		{"descriptive kinds are not counted", []Edge{edge("collaborates_with", "a", "b"), edge("collaborates_with", "b", "a"), edge("escalates_to", "a", "b"), edge("escalates_to", "b", "a"), edge("can_observe", "a", "b"), edge("can_observe", "b", "a")}, ""},
		{"cycle behind a tail", []Edge{edge("delegates_to", "a", "b"), edge("delegates_to", "b", "c"), edge("delegates_to", "c", "b")}, "b>c>b"},
	}
	for _, c := range cases {
		if got := strings.Join(FindLaunchCycle(c.edges), ">"); got != c.want {
			t.Errorf("%s: cycle = %q, want %q", c.name, got, c.want)
		}
	}
}

func TestRenderRoomMemberPermissionPolicy(t *testing.T) {
	out, err := RenderRoom("dev", "Development",
		[]Seat{
			{Key: "alice", Runtime: "claude-code", PermissionPolicy: "yolo"},
			{Key: "bob", Runtime: "claude-code", PermissionPolicy: "standard"},
			{Key: "carol", Runtime: "claude-code", PermissionPolicy: "standard"},
			{Key: "dave", Runtime: "claude-code", PermissionPolicy: "none"},
		}, nil)
	if err != nil {
		t.Fatalf("RenderRoom: %v", err)
	}

	var doc map[string]any
	if err := yaml.Unmarshal([]byte(out), &doc); err != nil {
		t.Fatalf("parse rendered rig.yaml: %v\n%s", err, out)
	}
	if _, present := doc["permission_policy"]; present {
		t.Fatalf("rig-level permission_policy rendered:\n%s", out)
	}
	pods, ok := doc["pods"].([]any)
	if !ok || len(pods) != 1 {
		t.Fatalf("pods = %#v, want exactly one pod", doc["pods"])
	}
	members, ok := pods[0].(map[string]any)["members"].([]any)
	if !ok || len(members) != 4 {
		t.Fatalf("members = %#v, want four", pods[0])
	}
	byID := make(map[string]map[string]any, len(members))
	for _, raw := range members {
		member := raw.(map[string]any)
		id, _ := member["id"].(string)
		byID[id] = member
	}
	for id, want := range map[string]string{"alice": "builtin:yolo", "bob": "builtin:standard", "dave": "none"} {
		if got, _ := byID[id]["permission_policy"].(string); got != want {
			t.Errorf("%s permission_policy = %#v, want %q", id, byID[id]["permission_policy"], want)
		}
	}
	if got, _ := byID["carol"]["permission_policy"].(string); got != "builtin:standard" {
		t.Errorf("carol permission_policy = %#v, want builtin:standard", byID["carol"]["permission_policy"])
	}
}

func TestRenderRoomRejectsInvalidMemberPolicy(t *testing.T) {
	for _, bad := range []string{"", "bypass", "builtin:yolo", "Yolo"} {
		out, err := RenderRoom("dev", "Development", []Seat{{Key: "alice", Runtime: "claude-code", PermissionPolicy: bad}}, nil)
		if err == nil {
			t.Fatalf("member policy %q rendered, want an error:\n%s", bad, out)
		}
		if !strings.Contains(err.Error(), `seat "alice"`) || !strings.Contains(err.Error(), "permission policy") {
			t.Errorf("member policy %q error = %v, want the seat and the policy named", bad, err)
		}
	}
}

func TestRenderRoomMemberPolicyIsDeterministic(t *testing.T) {
	seats := []Seat{
		{Key: "bob", Runtime: "codex", PermissionPolicy: "standard"},
		{Key: "alice", Runtime: "claude-code", PermissionPolicy: "yolo"},
		{Key: "dave", Runtime: "claude-code", PermissionPolicy: "none"},
		{Key: "carol", Runtime: "claude-code", PermissionPolicy: "standard"},
	}
	first, err := RenderRoom("dev", "Development", seats, nil)
	if err != nil {
		t.Fatal(err)
	}
	reversed := []Seat{seats[3], seats[2], seats[1], seats[0]}
	second, err := RenderRoom("dev", "Development", reversed, nil)
	if err != nil {
		t.Fatal(err)
	}
	if first != second {
		t.Fatalf("input order changed the output:\n%s\n---\n%s", first, second)
	}
}

func TestRenderRoomPermissionPolicyPerSeat(t *testing.T) {
	seats := []Seat{{Key: "lead", Runtime: "claude-code", PermissionPolicy: "standard"}}
	cases := map[string]string{
		"locked":   "permission_policy: builtin:locked",
		"standard": "permission_policy: builtin:standard",
		"open":     "permission_policy: builtin:open",
		"yolo":     "permission_policy: builtin:yolo",
		"none":     "permission_policy: none",
	}
	for policy, line := range cases {
		seats[0].PermissionPolicy = policy
		out, err := RenderRoom("dev", "Development", seats, nil)
		if err != nil {
			t.Fatalf("RenderRoom(%s): %v", policy, err)
		}
		if strings.Count(out, "permission_policy") != 1 || !strings.Contains(out, line+"\n") {
			t.Errorf("policy %s: want exactly %q:\n%s", policy, line, out)
		}
		if nameAt, polAt := strings.Index(out, "\nname: dev\n"), strings.Index(out, line); polAt < nameAt || strings.Index(out, "\npods:\n") > polAt {
			t.Errorf("policy %s: the line must sit inside the member, after pods:\n%s", policy, out)
		}
	}
}

// rigValidate runs `rig spec validate` on a rig.yaml with two agent dirs (a, b) beside it and
// returns its output and whether it exited 0. A missing binary or daemon skips the test.
func rigValidate(t *testing.T, rigYAML string) (string, bool) {
	t.Helper()
	rigPath, err := exec.LookPath("rig")
	if err != nil {
		t.Skip("rig binary not on PATH")
	}
	dir := t.TempDir()
	writeAgentDir(t, dir, "a", "claude-code")
	writeAgentDir(t, dir, "b", "claude-code")
	file := filepath.Join(dir, "rig.yaml")
	if err := os.WriteFile(file, []byte(rigYAML), 0o644); err != nil {
		t.Fatalf("write rig.yaml: %v", err)
	}
	out, err := exec.Command(rigPath, "spec", "validate", file).CombinedOutput()
	if err != nil && strings.Contains(string(out), "Daemon not running") {
		t.Skipf("rig validate needs a running OpenRig daemon: %s", strings.TrimSpace(string(out)))
	}
	return string(out), err == nil
}

const twoMemberRig = `version: "0.2"
name: t
pods:
  - id: t
    label: T
    members:
      - {id: a, agent_ref: "local:agents/a", profile: default, runtime: claude-code, cwd: .}
      - {id: %s, agent_ref: "local:agents/b", profile: default, runtime: claude-code, cwd: .}
    edges:
      - {kind: %s, from: a, to: %s}
edges: []
`

// The invalid specs OpenRig's validator rejects (bad edge kind, unknown member, duplicate member
// id) are rejected by RenderRoom for the same cause; the OpenRig repo ships no invalid rig
// fixtures (packages/test-system/scenarios holds only valid stubs), so these are written here.
func TestRenderRoomRejectsWhatRigValidateRejects(t *testing.T) {
	seats := []Seat{{Key: "a", Runtime: "claude-code", PermissionPolicy: "standard"}, {Key: "b", Runtime: "claude-code", PermissionPolicy: "standard"}}
	cases := []struct {
		name      string
		rigYAML   string
		rigWant   string
		seats     []Seat
		edges     []Edge
		renderErr string
	}{
		{"edge kind", fmt.Sprintf(twoMemberRig, "b", "reports_to", "b"), "must be one of delegates_to", seats, []Edge{{Kind: "reports_to", From: "a", To: "b"}}, "kind"},
		{"unknown member", fmt.Sprintf(twoMemberRig, "b", "delegates_to", "ghost"), `member "ghost" not found`, seats, []Edge{{Kind: "delegates_to", From: "a", To: "ghost"}}, "to"},
		{"duplicate member id", fmt.Sprintf(twoMemberRig, "a", "delegates_to", "a"), `duplicate member id "a"`, []Seat{seats[0], seats[0]}, nil, "duplicate seat key"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			out, ok := rigValidate(t, c.rigYAML)
			if ok || !strings.Contains(out, "Rig spec invalid") || !strings.Contains(out, c.rigWant) {
				t.Fatalf("rig spec validate did not reject for %q (ok=%v):\n%s", c.rigWant, ok, out)
			}
			if _, err := RenderRoom("t", "T", c.seats, c.edges); err == nil || !strings.Contains(err.Error(), c.renderErr) {
				t.Fatalf("RenderRoom error = %v, want it to contain %q", err, c.renderErr)
			}
		})
	}
}

// `rig spec validate` accepts a delegates_to cycle (OpenRig only rejects it when the rig is
// brought up), so the cycle rule lives in FindLaunchCycle and is applied when a link is saved.
func TestLaunchCycleIsNotCaughtByRigValidate(t *testing.T) {
	cycle := fmt.Sprintf(twoMemberRig, "b", "delegates_to", "b")
	cycle = strings.Replace(cycle, "      - {kind: delegates_to, from: a, to: b}\n", "      - {kind: delegates_to, from: a, to: b}\n      - {kind: delegates_to, from: b, to: a}\n", 1)

	out, ok := rigValidate(t, cycle)
	if !ok || !strings.Contains(out, "Rig spec valid") {
		t.Fatalf("rig spec validate rejected a cycle (the premise of this test changed):\n%s", out)
	}
	got := FindLaunchCycle([]Edge{{Kind: "delegates_to", From: "a", To: "b"}, {Kind: "delegates_to", From: "b", To: "a"}})
	if strings.Join(got, ">") != "a>b>a" {
		t.Fatalf("FindLaunchCycle = %v, want a>b>a", got)
	}
}
