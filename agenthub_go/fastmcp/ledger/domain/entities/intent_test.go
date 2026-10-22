package entities

import (
	"testing"

	taskentities "agenthub/fastmcp/task_management/domain/entities"
)

// TestEvidenceSubmittedIsNotPushable pins the refusal direction: the evidence controller is the
// ledger's only evidence writer, and `evidence_submitted` is not a kind the intents route accepts.
// The batch gate is IsIntentKind (ledger_service.go), so this list IS the enforcement - a batch that
// carries the kind is refused with unsupported_kind, which a pg case drives end to end
// (evidence_intent_refused_pg_test.go). The constant must still exist and still name the table's
// token: it is the fact vocabulary's entry, and the client cannot be rewritten around a bare string.
func TestEvidenceSubmittedIsNotPushable(t *testing.T) {
	if got := string(IntentKindEvidenceSubmitted); got != "evidence_submitted" {
		t.Fatalf("the evidence kind must name the table's token, got %q", got)
	}
	if IsIntentKind(string(IntentKindEvidenceSubmitted)) {
		t.Fatal("evidence_submitted must not be a kind a client can push: evidence is not commutative, " +
			"so a fact intent would append an account of a head_sha that the evidence route's 409 owns")
	}
	// The classifying half is NOT what the refusal removes: the staleness query still needs the kind,
	// so a decision staged before a controller-written evidence row stays accepted.
	if !IntentKindEvidenceSubmitted.IsFact() {
		t.Fatal("evidence_submitted must stay a fact for HasNonFactAfter, or every decision staged " +
			"before an evidence row would answer stale_base_seq")
	}
}

// TestEveryPushableKindIsExactlyOneOfFactOrDecision is D9's own rule stated as a property over the
// kinds a client may actually push: an intent is a fact or a decision and never both, which is what
// makes "facts sync, decisions sequence" a complete rule rather than one with a case nobody wrote
// down. A kind that fell out of both lists would be an intent the service would append with no
// staleness check at all - a decision that skipped the rule - so this is not bookkeeping. It is a
// STRICT subset: evidence_submitted is a fact that is deliberately not pushable, pinned above.
func TestEveryPushableKindIsExactlyOneOfFactOrDecision(t *testing.T) {
	for _, k := range IntentKinds {
		if k.IsFact() == k.IsDecision() {
			t.Fatalf("kind %q must be exactly one of a fact or a decision: IsFact = %v, IsDecision = %v",
				k, k.IsFact(), k.IsDecision())
		}
	}
	for _, k := range DecisionKinds {
		if !IsIntentKind(string(k)) {
			t.Fatalf("the decision %q is not in the intent vocabulary", k)
		}
	}
	// The two lists are two and three, and the count is worth pinning: a decision added without a
	// thought would silently put every client that has not read the new contract at risk of a
	// refusal it cannot act on, and a fact added to the pushable list without one would append
	// observations the server's own rules never see.
	if len(DecisionKinds) != 2 || len(FactKinds) != 3 {
		t.Fatalf("the ledger names two decisions and three facts, got %d and %d", len(DecisionKinds), len(FactKinds))
	}
	if len(IntentKinds) != len(FactKinds)+len(DecisionKinds)-1 {
		t.Fatalf("the pushable list is every fact and decision but the server-written one: %d intents, %d facts + %d decisions",
			len(IntentKinds), len(FactKinds), len(DecisionKinds))
	}
}

// TestEveryIntentKindIsATableKind is the drift guard between this package and the table: an intent
// kind the CHECK constraint refuses would fail where the bytes land - inside a transaction, as a
// driver error - rather than as an answer the client can read, so the two vocabularies must agree
// here.
func TestEveryIntentKindIsATableKind(t *testing.T) {
	table := map[string]bool{}
	for _, k := range taskentities.TaskEventKindValues {
		table[string(k)] = true
	}
	for _, k := range IntentKinds {
		if !table[string(k)] {
			t.Fatalf("the intent kind %q is not in task_events' CHECK vocabulary %v", k, taskentities.TaskEventKindValues)
		}
	}
	for _, k := range FactKinds {
		if !table[string(k)] {
			t.Fatalf("the fact kind %q is not in task_events' CHECK vocabulary", k)
		}
	}
	for _, k := range DecisionKinds {
		if !table[string(k)] {
			t.Fatalf("the decision kind %q is not in task_events' CHECK vocabulary", k)
		}
	}
}

// TestTheServersOwnKindsAreNotIntents pins the boundary the other way: context_updated is in the
// table's vocabulary and is NOT something a client may push. A client that could send it would be
// claiming a context version it never read. The six kinds the handover ruling deleted are neither
// intents nor table kinds at all: they carry no writer, and a table that still accepted one would be
// widening a vocabulary nothing writes.
func TestTheServersOwnKindsAreNotIntents(t *testing.T) {
	// context_updated is the context path's write; evidence_submitted is the evidence controller's, and
	// the client's own kind list dropped it in the same change so an offline queue cannot hold one.
	for _, kind := range []string{"context_updated", "evidence_submitted", "planned", ""} {
		if IsIntentKind(kind) {
			t.Fatalf("%q must not be a kind a client can push", kind)
		}
	}
	table := map[string]bool{}
	for _, k := range taskentities.TaskEventKindValues {
		table[string(k)] = true
	}
	for _, kind := range []string{"assigned", "claimed", "delivered", "context_loaded", "escalated", "human_decision"} {
		if IsIntentKind(kind) {
			t.Fatalf("the deleted kind %q must not be a kind a client can push", kind)
		}
		if table[kind] {
			t.Fatalf("the deleted kind %q is still in task_events' vocabulary", kind)
		}
	}
	for _, k := range IntentKinds {
		if k.IsFact() || k.IsDecision() {
			continue
		}
		t.Fatalf("kind %q is in the intent vocabulary but neither a fact nor a decision", k)
	}
}

// TestFactKindStringsIsTheFactListAsTokens is what the staleness query receives: it is an argument
// to the repository rather than a second list there, so it must be exactly the fact vocabulary and
// must not be shared with the slice it was built from.
func TestFactKindStringsIsTheFactListAsTokens(t *testing.T) {
	got := FactKindStrings()
	if len(got) != len(FactKinds) {
		t.Fatalf("FactKindStrings = %v, want %d tokens", got, len(FactKinds))
	}
	for i, k := range FactKinds {
		if got[i] != string(k) {
			t.Fatalf("FactKindStrings[%d] = %q, want %q", i, got[i], k)
		}
	}
	// A caller must not be able to widen the rule by writing through the slice it was handed.
	got[0] = "mutated"
	if FactKinds[0] == IntentKind("mutated") {
		t.Fatal("FactKindStrings must return a copy, not the vocabulary's own backing array")
	}
}

// TestTheTwoAnswerShapesAreDisjoint is the wire contract in the domain's own terms: an acceptance
// carries the sequences the row took and no reason, a refusal carries the reason and the task seq
// and no sequence numbers. A single Answer type with a discriminator is what makes the encoded
// shapes disjoint by construction, and this pins that they stay so.
func TestTheTwoAnswerShapesAreDisjoint(t *testing.T) {
	accepted := Acceptance(41, 7)
	if !accepted.Accepted || accepted.UserSeq != 41 || accepted.Seq != 7 {
		t.Fatalf("Acceptance lost a field: %+v", accepted)
	}
	if accepted.Reason != "" || accepted.TaskSeq != 0 {
		t.Fatalf("an acceptance must carry no refusal fields: %+v", accepted)
	}

	refused := Refusal(ReasonStaleBaseSeq, 9)
	if refused.Accepted || refused.Reason != ReasonStaleBaseSeq || refused.TaskSeq != 9 {
		t.Fatalf("Refusal lost a field: %+v", refused)
	}
	if refused.UserSeq != 0 || refused.Seq != 0 {
		t.Fatalf("a refusal must carry no sequence numbers: %+v", refused)
	}
}
