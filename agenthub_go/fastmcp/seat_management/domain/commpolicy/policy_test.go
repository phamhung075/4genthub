package commpolicy

import (
	"strings"
	"testing"
)

func TestDecide(t *testing.T) {
	taskAllow := Link{From: "a", To: "b", Kind: KindDelegatesTo, Allow: true}
	taskDeny := Link{From: "a", To: "b", Kind: KindDelegatesTo, Allow: false}

	cases := []struct {
		name        string
		policy      Policy
		to          string
		intent      Intent
		wantAllowed bool
		wantReason  string
	}{
		{
			name:       "default deny with no links",
			policy:     Policy{Seat: "a"},
			to:         "b",
			intent:     IntentTask,
			wantReason: reasonNoLink,
		},
		{
			name:        "allow delegates to",
			policy:      Policy{Seat: "a", Links: []Link{taskAllow}},
			to:          "b",
			intent:      IntentTask,
			wantAllowed: true,
			wantReason:  reasonAllowed,
		},
		{
			name:       "explicit deny",
			policy:     Policy{Seat: "a", Links: []Link{taskDeny}},
			to:         "b",
			intent:     IntentTask,
			wantReason: reasonExplicitDeny,
		},
		{
			name:       "explicit deny wins over allow before it",
			policy:     Policy{Seat: "a", Links: []Link{taskAllow, taskDeny}},
			to:         "b",
			intent:     IntentTask,
			wantReason: reasonExplicitDeny,
		},
		{
			name:       "explicit deny wins over allow after it",
			policy:     Policy{Seat: "a", Links: []Link{taskDeny, taskAllow}},
			to:         "b",
			intent:     IntentTask,
			wantReason: reasonExplicitDeny,
		},
		{
			name:       "wrong kind",
			policy:     Policy{Seat: "a", Links: []Link{{From: "a", To: "b", Kind: KindConsults, Allow: true}}},
			to:         "b",
			intent:     IntentTask,
			wantReason: reasonNoLink,
		},
		{
			name:       "other seat's links ignored",
			policy:     Policy{Seat: "a", Links: []Link{{From: "x", To: "b", Kind: KindDelegatesTo, Allow: true}}},
			to:         "b",
			intent:     IntentTask,
			wantReason: reasonNoLink,
		},
		{
			name:       "link to another recipient ignored",
			policy:     Policy{Seat: "a", Links: []Link{taskAllow}},
			to:         "c",
			intent:     IntentTask,
			wantReason: reasonNoLink,
		},
		{
			name:       "self message denied",
			policy:     Policy{Seat: "a", Links: []Link{{From: "a", To: "a", Kind: KindDelegatesTo, Allow: true}}},
			to:         "a",
			intent:     IntentTask,
			wantReason: reasonSelfMessage,
		},
		{
			name:       "unknown intent denied",
			policy:     Policy{Seat: "a", Links: []Link{taskAllow}},
			to:         "b",
			intent:     Intent("shout"),
			wantReason: reasonUnknownIntent,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := Decide(tc.policy, tc.to, tc.intent)
			if got.Allowed != tc.wantAllowed {
				t.Fatalf("Allowed = %v, want %v", got.Allowed, tc.wantAllowed)
			}
			if got.Reason != tc.wantReason {
				t.Fatalf("Reason = %q, want %q", got.Reason, tc.wantReason)
			}
		})
	}
}

func TestDecideIntentKindMapping(t *testing.T) {
	pairs := []struct {
		intent Intent
		kind   LinkKind
	}{
		{IntentTask, KindDelegatesTo},
		{IntentEscalation, KindEscalatesTo},
		{IntentReport, KindReportsTo},
		{IntentQuestion, KindConsults},
		{IntentNotice, KindNotifies},
	}
	for _, pair := range pairs {
		policy := Policy{Seat: "a", Links: []Link{{From: "a", To: "b", Kind: pair.kind, Allow: true}}}
		if got := Decide(policy, "b", pair.intent); !got.Allowed || got.Reason != reasonAllowed {
			t.Fatalf("intent %q against kind %q = %+v, want allowed", pair.intent, pair.kind, got)
		}
	}
}

func TestDecideReturnsDecidingLink(t *testing.T) {
	allow := Link{From: "a", To: "b", Kind: KindNotifies, Allow: true}
	decision := Decide(Policy{Seat: "a", Links: []Link{allow}}, "b", IntentNotice)
	if decision.Link == nil || *decision.Link != allow {
		t.Fatalf("allowed decision link = %+v, want %+v", decision.Link, allow)
	}

	deny := Link{From: "a", To: "b", Kind: KindNotifies, Allow: false}
	decision = Decide(Policy{Seat: "a", Links: []Link{allow, deny}}, "b", IntentNotice)
	if decision.Link == nil || *decision.Link != deny {
		t.Fatalf("denied decision link = %+v, want %+v", decision.Link, deny)
	}

	if got := Decide(Policy{Seat: "a"}, "b", IntentNotice); got.Link != nil {
		t.Fatalf("no-link decision carried a link: %+v", got.Link)
	}
}

func TestParsePolicyValid(t *testing.T) {
	data := []byte(`{"Seat":"a","Links":[
		{"From":"a","To":"b","Kind":"delegates_to","Allow":true},
		{"From":"a","To":"c","Kind":"consults","Allow":false}
	]}`)
	policy, err := ParsePolicy(data)
	if err != nil {
		t.Fatalf("ParsePolicy: %v", err)
	}
	if policy.Seat != "a" || len(policy.Links) != 2 {
		t.Fatalf("unexpected policy: %+v", policy)
	}
	if policy.Links[0].Kind != KindDelegatesTo || !policy.Links[0].Allow {
		t.Fatalf("unexpected first link: %+v", policy.Links[0])
	}
}

func TestParsePolicyErrors(t *testing.T) {
	cases := map[string]string{
		"empty":                     ``,
		"malformed":                 `{"Seat":`,
		"missing seat":              `{"Links":[]}`,
		"empty seat":                `{"Seat":"","Links":[]}`,
		"unknown top field":         `{"Seat":"a","Bogus":1}`,
		"unknown link field":        `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"delegates_to","Allow":true,"Extra":1}]}`,
		"unknown link kind":         `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"shouts","Allow":true}]}`,
		"foreign link":              `{"Seat":"a","Links":[{"From":"x","To":"b","Kind":"delegates_to","Allow":true}]}`,
		"duplicate triple":          `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"delegates_to","Allow":true},{"From":"a","To":"b","Kind":"delegates_to","Allow":true}]}`,
		"duplicate differing allow": `{"Seat":"a","Links":[{"From":"a","To":"b","Kind":"delegates_to","Allow":true},{"From":"a","To":"b","Kind":"delegates_to","Allow":false}]}`,
		"trailing data":             `{"Seat":"a","Links":[]} extra`,
	}
	for name, data := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := ParsePolicy([]byte(data)); err == nil {
				t.Fatalf("ParsePolicy(%s) succeeded, want error", data)
			}
		})
	}
}

func TestParsePolicyAllowsNullAndEmptyLinks(t *testing.T) {
	for _, data := range []string{`{"Seat":"a","Links":null}`, `{"Seat":"a"}`, `{"Seat":"a","Links":[]}`} {
		policy, err := ParsePolicy([]byte(data))
		if err != nil {
			t.Fatalf("ParsePolicy(%s): %v", data, err)
		}
		if policy.Seat != "a" || len(policy.Links) != 0 {
			t.Fatalf("ParsePolicy(%s) = %+v", data, policy)
		}
	}
}

func TestPolicyHashOrderIndependent(t *testing.T) {
	first := Policy{Seat: "a", Links: []Link{
		{From: "a", To: "b", Kind: KindDelegatesTo, Allow: true},
		{From: "a", To: "c", Kind: KindReportsTo, Allow: true},
		{From: "a", To: "d", Kind: KindConsults, Allow: false},
	}}
	reversed := Policy{Seat: "a", Links: []Link{
		{From: "a", To: "d", Kind: KindConsults, Allow: false},
		{From: "a", To: "c", Kind: KindReportsTo, Allow: true},
		{From: "a", To: "b", Kind: KindDelegatesTo, Allow: true},
	}}
	if PolicyHash(first) != PolicyHash(reversed) {
		t.Fatalf("hash depends on link order: %s != %s", PolicyHash(first), PolicyHash(reversed))
	}
	if PolicyHash(first) != PolicyHash(first) {
		t.Fatal("hash is not deterministic")
	}
	hash := PolicyHash(first)
	if len(hash) != 64 || strings.ToLower(hash) != hash {
		t.Fatalf("hash %q is not lowercase hex", hash)
	}
}

func TestPolicyHashChanges(t *testing.T) {
	base := Policy{Seat: "a", Links: []Link{{From: "a", To: "b", Kind: KindDelegatesTo, Allow: true}}}

	changed := map[string]Policy{
		"seat":  {Seat: "z", Links: base.Links},
		"allow": {Seat: "a", Links: []Link{{From: "a", To: "b", Kind: KindDelegatesTo, Allow: false}}},
		"to":    {Seat: "a", Links: []Link{{From: "a", To: "c", Kind: KindDelegatesTo, Allow: true}}},
		"kind":  {Seat: "a", Links: []Link{{From: "a", To: "b", Kind: KindConsults, Allow: true}}},
		"extra": {Seat: "a", Links: append(base.Links, Link{From: "a", To: "z", Kind: KindNotifies, Allow: true})},
		"empty": {Seat: "a"},
	}
	baseHash := PolicyHash(base)
	for name, policy := range changed {
		if PolicyHash(policy) == baseHash {
			t.Fatalf("hash did not change for %s", name)
		}
	}
}

func TestBypassSuspected(t *testing.T) {
	known := []string{"agenthub-send"}
	cases := []struct {
		name     string
		observed string
		want     bool
	}{
		{"rig send", "rig send bob hello", true},
		{"rig queue", "rig queue bob", true},
		{"rig broadcast", "rig broadcast hello", true},
		{"tmux send-keys", "tmux send-keys -t s hello Enter", true},
		{"tmux paste-buffer", "tmux paste-buffer -t s", true},
		{"leading env", "FOO=1 rig send bob", true},
		{"multiple leading env", "FOO=1 BAR=2 /usr/bin/rig queue bob", true},
		{"env value with colon", "PATH=/usr/bin:/bin rig broadcast", true},
		{"leading path", "/usr/bin/rig send bob", true},
		{"collapsed spaces", "rig   send bob", true},
		{"known wrapper", "agenthub-send rig send bob", false},
		{"known wrapper with path", "/usr/local/bin/agenthub-send x", false},
		{"known wrapper after env", "FOO=1 agenthub-send x", false},
		{"rig status", "rig status", false},
		{"rig alone", "rig", false},
		{"tmux list-sessions", "tmux list-sessions", false},
		{"tmux alone", "tmux", false},
		{"prefix only", "echo rig send bob", false},
		{"empty", "", false},
		{"case sensitive", "RIG send bob", false},
		{"subcommand prefix", "rig sends bob", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := BypassSuspected(known, tc.observed); got != tc.want {
				t.Fatalf("BypassSuspected(%q) = %v, want %v", tc.observed, got, tc.want)
			}
		})
	}
}

func TestBypassSuspectedNilKnown(t *testing.T) {
	if !BypassSuspected(nil, "rig send bob") {
		t.Fatal("nil known list should still flag a direct rig send")
	}
}
