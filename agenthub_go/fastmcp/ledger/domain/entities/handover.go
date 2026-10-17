package entities

// The handover payload's closed key set, ruled by the architect seat on task 31b72a0d
// (docs/RULING-handover-decision-record.md): a seat's decision record lands as ONE `handover`
// ledger entry, its keys are exactly the brief's keys, every fact cites evidence, and the server
// refuses a payload that breaks the shape or a fact whose evidence it can check and finds false.
//
// THE SHAPE IS A REFUSAL, NOT A CONVENTION. The measured failure mode of this platform is
// conventions that nothing enforces, and a record written free-form is the history the resume brief
// exists to replace. An unknown key is refused rather than kept "for later": the key set widens
// only by a change to this file.
//
// WHAT THE LEDGER VERIFIES AND WHAT IT DOES NOT. It verifies shape and SAME-TASK identity for
// `evt:` refs - both are rows in this same table, so the check costs one query and catches a fact
// citing another task's entry. It does NOT verify a `qitem:` row or a `sha:` object: those live in
// stores this transaction cannot read, and a rule that pretended to check them would pass anything.
// The ledger refuses shape and the truth it can see, never the truth it cannot.

import (
	"encoding/json"
	"regexp"
	"strings"
	"unicode/utf8"
)

// Handover payload limits. HandoverMaxPayloadBytes is a PRODUCT DEFAULT like the resume brief's
// token budget: the refusal names the size and the limit, and the server never truncates - a
// truncated decision record is the silent degradation this ledger exists to prevent.
const (
	HandoverMaxPayloadBytes    = 2048
	HandoverMaxNextActionRunes = 200
	HandoverMaxFacts           = 8
	HandoverMinFacts           = 1
	HandoverMaxClaimRunes      = 160
	HandoverMaxConstraints     = 8
)

// The `decision` enum, whose values say whether the work continues and, when it does not, why.
const (
	HandoverDecisionContinue = "continue"
	HandoverDecisionBlocked  = "blocked"
	HandoverDecisionDone     = "done"
	HandoverDecisionEscalate = "escalate"
)

// The refusal tokens this payload adds to the ledger's vocabulary (intent.go). They are stable
// tokens rather than prose, for the reason the other reasons give: a client branches on them.
const (
	// ReasonHandoverMalformed: the payload is not an object with exactly the ruled keys, a key is
	// missing or unknown, a value has the wrong type, `decision` is outside the enum, `next_action`
	// is over its cap or carries a newline, `blocked_on` is present when it must not be or absent
	// when it must, or the payload serializes over its byte cap.
	ReasonHandoverMalformed = "handover_malformed"
	// ReasonHandoverFactWithoutEvidence: a `facts` item has no `evidence` string, its evidence
	// matches none of the four ref grammars, or its `evt:` ref does not resolve to an entry of THIS
	// task.
	ReasonHandoverFactWithoutEvidence = "handover_fact_without_evidence"
)

// handoverKeys is the payload's whole key set: exactly these, no more.
var handoverKeys = map[string]bool{
	"decision":    true,
	"next_action": true,
	"facts":       true,
	"constraints": true,
	"blocked_on":  true,
}

// canonicalUUID matches the canonical UUID spelling the ledger stores (task_events.id and
// tasks.id are UUID columns written from PyParseUUID's canonical form). The ref grammars say
// `<uuid>`, so the looser forms PyParseUUID accepts for input (urn:, braces, undashed) are NOT
// refs: a ref is a citation a reader can paste into the API, and that spelling is the canonical one.
var canonicalUUID = regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

// shaRef matches `sha:<7..40 lowercase hex>`, the spelling `git rev-parse --short`/full prints.
var shaRef = regexp.MustCompile(`^[0-9a-f]{7,40}$`)

// HandoverEventResolver answers whether an `evt:` ref names an entry OF THE TASK the handover is
// about. The ledger implementation asks task_events for (user, task, id), which is the same table
// the entry is appended to, so the answer is exact rather than inferred.
type HandoverEventResolver func(eventID string) (bool, error)

// ValidateHandoverPayload checks one handover payload against the ruled shape and returns the
// refusal reason - "" when the payload is acceptable - or an error when the evt: lookups fail.
//
// The resolver is called ONLY for `evt:` refs, after the rest of the shape has passed: a malformed
// payload costs no query, and a ref the ledger cannot resolve is a refusal, never a pass.
func ValidateHandoverPayload(payload any, resolveEvent HandoverEventResolver) (string, error) {
	object, ok := payload.(map[string]any)
	if !ok {
		return ReasonHandoverMalformed, nil
	}
	encoded, err := json.Marshal(object)
	if err != nil {
		return ReasonHandoverMalformed, nil
	}
	if len(encoded) > HandoverMaxPayloadBytes {
		return ReasonHandoverMalformed, nil
	}
	for key := range object {
		if !handoverKeys[key] {
			return ReasonHandoverMalformed, nil
		}
	}

	decision, ok := object["decision"].(string)
	if !ok || !isHandoverDecision(decision) {
		return ReasonHandoverMalformed, nil
	}

	// next_action is required unless the decision is done. When done, an omitted key is legal; a
	// key that IS present still has to hold a legal value, so the two shapes cannot drift.
	if raw, present := object["next_action"]; present || decision != HandoverDecisionDone {
		next, ok := raw.(string)
		if !ok || strings.ContainsAny(next, "\r\n") || utf8.RuneCountInString(next) > HandoverMaxNextActionRunes {
			return ReasonHandoverMalformed, nil
		}
	}

	// blocked_on is required exactly when the decision is blocked or escalate, and is the queue
	// row's id VERBATIM - the daemon's `qitem-…` spelling, never a `qitem:` scheme (that scheme is
	// for evidence refs, where the grammar names it).
	rawBlocked, hasBlocked := object["blocked_on"]
	if decision == HandoverDecisionBlocked || decision == HandoverDecisionEscalate {
		blocked, ok := rawBlocked.(string)
		if !ok || !isQueueRowID(blocked) {
			return ReasonHandoverMalformed, nil
		}
	} else if hasBlocked {
		return ReasonHandoverMalformed, nil
	}

	rawFacts, ok := object["facts"].([]any)
	if !ok || len(rawFacts) < HandoverMinFacts || len(rawFacts) > HandoverMaxFacts {
		return ReasonHandoverMalformed, nil
	}
	for _, raw := range rawFacts {
		item, ok := raw.(map[string]any)
		if !ok {
			return ReasonHandoverMalformed, nil
		}
		for key := range item {
			if key != "claim" && key != "evidence" {
				return ReasonHandoverMalformed, nil
			}
		}
		claim, ok := item["claim"].(string)
		if !ok || utf8.RuneCountInString(claim) > HandoverMaxClaimRunes {
			return ReasonHandoverMalformed, nil
		}
		// A fact WITHOUT an evidence string is the ruling's own case, and it has its own token:
		// shape is legal, the citation is what is missing.
		evidence, ok := item["evidence"].(string)
		if !ok || evidence == "" {
			return ReasonHandoverFactWithoutEvidence, nil
		}
		if !isEvidenceRef(evidence) {
			return ReasonHandoverFactWithoutEvidence, nil
		}
		if eventID, isEvent := eventRefID(evidence); isEvent {
			found, err := resolveEvent(eventID)
			if err != nil {
				return "", err
			}
			if !found {
				return ReasonHandoverFactWithoutEvidence, nil
			}
		}
	}

	if raw, present := object["constraints"]; present {
		list, ok := raw.([]any)
		if !ok || len(list) > HandoverMaxConstraints {
			return ReasonHandoverMalformed, nil
		}
		for _, c := range list {
			ref, ok := c.(string)
			if !ok || !isConstraintRef(ref) {
				return ReasonHandoverMalformed, nil
			}
		}
	}

	return "", nil
}

func isHandoverDecision(s string) bool {
	switch s {
	case HandoverDecisionContinue, HandoverDecisionBlocked, HandoverDecisionDone, HandoverDecisionEscalate:
		return true
	}
	return false
}

// isQueueRowID reports whether s is a queue row id as the daemon prints it: the `qitem-` prefix
// and a non-empty, whitespace-free body. The body's own shape (the daemon's timestamp + suffix) is
// the daemon's to tighten; the ledger only refuses what cannot be a row id at all.
func isQueueRowID(s string) bool {
	rest, ok := strings.CutPrefix(s, "qitem-")
	return ok && rest != "" && !strings.ContainsAny(s, " \t\r\n")
}

// isEvidenceRef reports whether s matches exactly one of the four evidence grammars.
func isEvidenceRef(s string) bool {
	if _, isEvent := eventRefID(s); isEvent {
		return true
	}
	if rest, ok := strings.CutPrefix(s, "sha:"); ok {
		return shaRef.MatchString(rest)
	}
	if rest, ok := strings.CutPrefix(s, "qitem:"); ok {
		return isQueueRowID(rest)
	}
	if rest, ok := strings.CutPrefix(s, "task:"); ok {
		return canonicalUUID.MatchString(rest)
	}
	return false
}

// eventRefID returns the uuid an `evt:` ref names and whether s is one.
func eventRefID(s string) (string, bool) {
	rest, ok := strings.CutPrefix(s, "evt:")
	if !ok || !canonicalUUID.MatchString(rest) {
		return "", false
	}
	return rest, true
}

// isConstraintRef reports whether s is a constraint reference: a context or task uuid. These are
// the two levels a decision record may name, and both live in the task's own context store.
func isConstraintRef(s string) bool {
	if rest, ok := strings.CutPrefix(s, "context:"); ok {
		return canonicalUUID.MatchString(rest)
	}
	if rest, ok := strings.CutPrefix(s, "task:"); ok {
		return canonicalUUID.MatchString(rest)
	}
	return false
}
