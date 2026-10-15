// Package decisions holds the room-decision vocabulary: the state a cloud decision row is in.
//
// The state list is the single source of truth for three things that must not drift apart: the
// CHECK constraint on room_decisions.state, the route's refusal code `state-<state>`, and the
// `state` the answer response reports. TestRoomDecisionStateCheckMatchesDomain
// (seat_management/infrastructure/database) checks BOTH DDL copies against this list, the same way
// TestSeatFeedbackLayerCheckMatchesDomain checks seat_feedback.layer against domain/feedback.
//
// WHO MOVES A ROW BETWEEN THESE STATES. The cloud never decides a decision is finished: it records
// the human's click and reports `complete`. Only the daemon's own apply-ack or state push produces
// `resolved` (the decision was applied to the local queue) or `superseded` (it was answered
// somewhere else first, typically Slack). That is why `answered` is not the end state: it means
// "every question has an answer, and the room has not been told yet".
package decisions

import "fmt"

// State is where one mirrored decision is in its life.
type State string

const (
	// StatePending is an ask that still has at least one unanswered question. A click is accepted
	// only while the row is in this state.
	StatePending State = "pending"
	// StateAnswered means every question has an answer and the daemon has not applied it yet -
	// "awaiting the room". A further click is refused with state-answered.
	StateAnswered State = "answered"
	// StateResolved means the daemon applied the answers to the local queue row and closed it.
	// Only a daemon apply-ack or state push produces this.
	StateResolved State = "resolved"
	// StateSuperseded means the ask was answered somewhere else first, so this row's answers are
	// stale and must not be applied. Only a daemon state push produces this.
	StateSuperseded State = "superseded"
)

// States is the closed set, in lifecycle order. The order is the order the CHECK lists, and it is
// the order a reader expects a pending ask to move through, so it is part of the contract.
var States = []State{
	StatePending,
	StateAnswered,
	StateResolved,
	StateSuperseded,
}

// Valid reports whether s is one of States.
func (s State) Valid() bool {
	for _, known := range States {
		if s == known {
			return true
		}
	}
	return false
}

// ParseState validates a state read back from the database or supplied by a caller.
func ParseState(raw string) (State, error) {
	state := State(raw)
	if !state.Valid() {
		return "", fmt.Errorf("state %q is not one of %s", raw, List())
	}
	return state, nil
}

// List is the accepted set as one comma-separated string, for error text.
func List() string {
	out := ""
	for i, state := range States {
		if i > 0 {
			out += ", "
		}
		out += string(state)
	}
	return out
}

// RefusalCode is the token the answer route answers a refused click with: `state-<state>` for a
// decision that is not pending. It is built here so the route and the tests spell it the same way.
func RefusalCode(s State) string {
	return "state-" + string(s)
}
