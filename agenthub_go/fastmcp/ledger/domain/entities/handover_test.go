package entities

import (
	"errors"
	"strings"
	"testing"
)

// handoverEvent resolves every evt: ref to "found" unless the test overrides it, so a case that is
// about SHAPE does not have to invent a ledger.
func handoverEvent(found bool) HandoverEventResolver {
	return func(string) (bool, error) { return found, nil }
}

// handoverFact builds one facts item.
func handoverFact(claim, evidence string) map[string]any {
	return map[string]any{"claim": claim, "evidence": evidence}
}

// TestValidateHandoverPayloadAcceptsTheRuledShapes covers one payload per decision value, each with
// the keys its decision requires and no others.
func TestValidateHandoverPayloadAcceptsTheRuledShapes(t *testing.T) {
	const taskID = "aaaaaaaa-0000-0000-0000-000000000001"
	const entryID = "bbbbbbbb-0000-0000-0000-000000000002"
	cases := map[string]map[string]any{
		"continue": {
			"decision":    "continue",
			"next_action": "write the red tests, then the parse",
			"facts": []any{
				handoverFact("the parse is red", "evt:"+entryID),
				handoverFact("the tip is clean", "sha:8e706e18"),
				handoverFact("the row is on the rail", "qitem:qitem-20261017135334-23c60c9d9518"),
				handoverFact("the task is 2/8", "task:"+taskID),
			},
			"constraints": []any{"context:" + taskID, "task:" + taskID},
		},
		"done": {
			"decision": "done",
			"facts":    []any{handoverFact("the branch is green", "sha:8e706e18")},
		},
		"blocked": {
			"decision":    "blocked",
			"next_action": "wait for the owner's call",
			"facts":       []any{handoverFact("the row is waiting", "qitem:qitem-20261017135334-23c60c9d9518")},
			"blocked_on":  "qitem-20261017135334-23c60c9d9518",
		},
		"escalate": {
			"decision":    "escalate",
			"next_action": "ask the owner which store owns the fact",
			"facts":       []any{handoverFact("two stores disagree", "task:"+taskID)},
			"blocked_on":  "qitem-20261017135334-23c60c9d9518",
		},
	}
	for name, payload := range cases {
		t.Run(name, func(t *testing.T) {
			reason, err := ValidateHandoverPayload(payload, handoverEvent(true))
			if err != nil {
				t.Fatalf("validation returned an error: %v", err)
			}
			if reason != "" {
				t.Fatalf("a ruled shape was refused: %q", reason)
			}
		})
	}
}

// TestValidateHandoverPayloadRefusesMalformedShape is the malformed token's territory: keys, types,
// the enum, next_action's cap and newline, blocked_on's presence rule, and the serialized byte cap.
func TestValidateHandoverPayloadRefusesMalformedShape(t *testing.T) {
	valid := func() map[string]any {
		return map[string]any{
			"decision":    "continue",
			"next_action": "go",
			"facts":       []any{handoverFact("a fact", "sha:8e706e18")},
		}
	}
	cases := map[string]any{
		"not an object":             "decision=continue",
		"nil payload":               nil,
		"unknown key":               with(valid(), "owner", "me"),
		"missing decision":          without(valid(), "decision"),
		"decision outside enum":     with(valid(), "decision", "maybe"),
		"decision wrong type":       with(valid(), "decision", 1),
		"next_action missing":       without(valid(), "next_action"),
		"next_action wrong type":    with(valid(), "next_action", true),
		"next_action newline":       with(valid(), "next_action", "line one\nline two"),
		"next_action over the cap":  with(valid(), "next_action", strings.Repeat("x", 201)),
		"facts missing":             without(valid(), "facts"),
		"facts wrong type":          with(valid(), "facts", "one fact"),
		"facts empty":               with(valid(), "facts", []any{}),
		"facts over the cap":        with(valid(), "facts", nineFacts()),
		"fact not an object":        with(valid(), "facts", []any{"a fact"}),
		"fact unknown key":          with(valid(), "facts", []any{with(handoverFact("a", "sha:8e706e18"), "source", "x")}),
		"claim wrong type":          with(valid(), "facts", []any{with(handoverFact("a", "sha:8e706e18"), "claim", 3)}),
		"claim over the cap":        with(valid(), "facts", []any{handoverFact(strings.Repeat("c", 161), "sha:8e706e18")}),
		"blocked_on when continue":  with(valid(), "blocked_on", "qitem-20261017135334-23c60c9d9518"),
		"blocked_on with scheme":    with(with(valid(), "decision", "blocked"), "blocked_on", "qitem:qitem-20261017135334-23c60c9d9518"),
		"constraints wrong type":    with(valid(), "constraints", "context:aaaaaaaa-0000-0000-0000-000000000001"),
		"constraints over the cap":  with(valid(), "constraints", nineConstraints()),
		"constraint unknown scheme": with(valid(), "constraints", []any{"sha:8e706e18"}),
		"constraint bad uuid":       with(valid(), "constraints", []any{"context:not-a-uuid"}),
	}
	for name, payload := range cases {
		t.Run(name, func(t *testing.T) {
			reason, err := ValidateHandoverPayload(payload, handoverEvent(true))
			if err != nil {
				t.Fatalf("validation returned an error: %v", err)
			}
			if reason != ReasonHandoverMalformed {
				t.Fatalf("reason = %q, want %q", reason, ReasonHandoverMalformed)
			}
		})
	}
}

// TestValidateHandoverPayloadRefusesAFactWithoutEvidence is the second token: an absent or
// ungrammatical evidence string, and an evt: ref that resolves outside this task.
func TestValidateHandoverPayloadRefusesAFactWithoutEvidence(t *testing.T) {
	withEvidence := func(evidence any) map[string]any {
		return map[string]any{
			"decision":    "continue",
			"next_action": "go",
			"facts":       []any{map[string]any{"claim": "a fact", "evidence": evidence}},
		}
	}
	cases := map[string]any{
		"evidence missing":    map[string]any{"claim": "a fact"},
		"evidence empty":      "",
		"evidence wrong type": 7,
		"sha too short":       "sha:abc123",
		"sha uppercase":       "sha:8E706E18",
		"sha not hex":         "sha:zzzzzzz",
		"evt not a uuid":      "evt:task-1",
		"task not a uuid":     "task:2",
		"qitem without id":    "qitem:",
		"unknown scheme":      "row:qitem-20261017135334-23c60c9d9518",
		"evt of another task": "evt:cccccccc-0000-0000-0000-000000000003",
	}
	for name, evidence := range cases {
		t.Run(name, func(t *testing.T) {
			// Every evt: in the last case resolves FALSE - the ledger holds the entry, but on a
			// different task - and every other case never reaches the resolver.
			reason, err := ValidateHandoverPayload(withEvidence(evidence), handoverEvent(false))
			if err != nil {
				t.Fatalf("validation returned an error: %v", err)
			}
			if reason != ReasonHandoverFactWithoutEvidence {
				t.Fatalf("reason = %q, want %q", reason, ReasonHandoverFactWithoutEvidence)
			}
		})
	}
}

// TestValidateHandoverPayloadPropagatesAResolverFailure pins that a ledger read failure is an ERROR,
// never a refusal: a handover must not be refused because the check could not run.
func TestValidateHandoverPayloadPropagatesAResolverFailure(t *testing.T) {
	want := errors.New("ledger read failed")
	payload := map[string]any{
		"decision":    "continue",
		"next_action": "go",
		"facts":       []any{handoverFact("a fact", "evt:bbbbbbbb-0000-0000-0000-000000000002")},
	}
	_, err := ValidateHandoverPayload(payload, func(string) (bool, error) { return false, want })
	if !errors.Is(err, want) {
		t.Fatalf("err = %v, want the resolver's error", err)
	}
}

// TestValidateHandoverPayloadEnforcesTheSerializedCap pins the 2048-byte cap on the payload AS
// SERIALIZED: eight claims at the legal 160-char limit, eight constraint refs and a 200-char
// next_action are each legal alone and together over it, which is the size the refusal names.
func TestValidateHandoverPayloadEnforcesTheSerializedCap(t *testing.T) {
	facts := make([]any, 0, HandoverMaxFacts)
	for i := 0; i < HandoverMaxFacts; i++ {
		facts = append(facts, handoverFact(strings.Repeat("c", 160), "task:aaaaaaaa-0000-0000-0000-000000000001"))
	}
	constraints := make([]any, 0, HandoverMaxConstraints)
	for i := 0; i < HandoverMaxConstraints; i++ {
		constraints = append(constraints, "context:aaaaaaaa-0000-0000-0000-000000000001")
	}
	payload := map[string]any{
		"decision":    "continue",
		"next_action": strings.Repeat("n", 200),
		"facts":       facts,
		"constraints": constraints,
	}
	reason, err := ValidateHandoverPayload(payload, handoverEvent(true))
	if err != nil {
		t.Fatal(err)
	}
	if reason != ReasonHandoverMalformed {
		t.Fatalf("a payload over %d serialized bytes must be refused, got %q", HandoverMaxPayloadBytes, reason)
	}
}

func with(payload map[string]any, key string, value any) map[string]any {
	payload[key] = value
	return payload
}

func without(payload map[string]any, key string) map[string]any {
	delete(payload, key)
	return payload
}

func nineFacts() []any {
	facts := make([]any, 0, HandoverMaxFacts+1)
	for i := 0; i < HandoverMaxFacts+1; i++ {
		facts = append(facts, handoverFact("a fact", "sha:8e706e18"))
	}
	return facts
}

func nineConstraints() []any {
	constraints := make([]any, 0, HandoverMaxConstraints+1)
	for i := 0; i < HandoverMaxConstraints+1; i++ {
		constraints = append(constraints, "context:aaaaaaaa-0000-0000-0000-000000000001")
	}
	return constraints
}
