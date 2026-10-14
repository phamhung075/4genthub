package services

// room_decision_ladder.go is the two lower tiers of the decision ladder (seat, lead). The owner tier
// is Create: a question that reaches the owner becomes a row the owner answers on the dashboard.
//
// Evaluate is stateless. It stores nothing, because a seat or lead that decides for itself needs no
// row, and a question that escalates is re-asked one tier up by the caller, carrying the
// recommended option this returns. Every outcome is appended to the Jev decision log with its tier.

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"agenthub/fastmcp/room_decisions/domain/decisions"
	"agenthub/fastmcp/room_decisions/domain/questions"
	"agenthub/fastmcp/seat_management/domain/secretscan"
)

// LadderQuestionResult is what one question came to: Jev's pick and confidence, and the option the
// asker recommended (empty when none was marked).
type LadderQuestionResult struct {
	QuestionID  string  `json:"question_id"`
	OptionID    string  `json:"option_id,omitempty"`
	Confidence  float64 `json:"confidence"`
	Recommended string  `json:"recommended,omitempty"`
}

// LadderOutcome is one step of the ladder. Decided means this tier answers and Answers holds one
// option per question. Otherwise EscalateTo is the next tier and Reason says why.
type LadderOutcome struct {
	Tier       decisions.Tier         `json:"tier"`
	Decided    bool                   `json:"decided"`
	Answers    map[string]string      `json:"answers,omitempty"`
	EscalateTo decisions.Tier         `json:"escalate_to,omitempty"`
	Reason     string                 `json:"reason,omitempty"`
	Questions  []LadderQuestionResult `json:"questions"`
}

// Evaluate runs one ladder step for a seat or lead.
func (s *RoomDecisionService) Evaluate(ctx context.Context, tier decisions.Tier, category decisions.Category, summary, detail string, rawQuestions json.RawMessage, now time.Time) (*LadderOutcome, error) {
	next, ok := tier.Next()
	if !ok || tier == decisions.TierOwner {
		return nil, &RoomDecisionAskRejection{Message: "tier must be seat or lead: the owner answers on the dashboard"}
	}
	summary = strings.TrimSpace(summary)
	detail = strings.TrimSpace(detail)
	for _, field := range []struct{ name, value string }{{"summary", summary}, {"detail", detail}} {
		if secretscan.Contains(field.value) {
			return nil, &RoomDecisionAskRejection{Message: field.name + " contains what looks like a credential", SecretField: field.name}
		}
	}
	parsed, err := questions.Parse(rawQuestions)
	if err != nil {
		return nil, &RoomDecisionAskRejection{Message: err.Error()}
	}

	outcome := &LadderOutcome{Tier: tier, Questions: make([]LadderQuestionResult, 0, len(parsed))}
	for _, q := range parsed {
		result := LadderQuestionResult{QuestionID: q.ID}
		for _, option := range q.Options {
			if option.Recommended != nil && *option.Recommended {
				result.Recommended = option.ID
			}
		}
		outcome.Questions = append(outcome.Questions, result)
	}

	var choices map[string]DecisionChoiceSelection
	var evalErr error
	switch {
	case s.ownerOnly.Has(category):
		// Decided by code, not by the model: no Jev call, and the owner is reached from any tier.
		next = decisions.TierOwner
		outcome.EscalateTo = next
		outcome.Reason = "owner-only category: " + string(category)
	case s.evaluator == nil:
		return nil, fmt.Errorf("decision ladder: no evaluator is configured")
	default:
		choices, evalErr = s.evaluator.SelectDecisionChoices(ctx, s.evaluatorModel, summary, detail, parsed)
		outcome.Decided = evalErr == nil && len(parsed) > 0
		outcome.Answers = map[string]string{}
		for i, q := range parsed {
			sel, found := choices[q.ID]
			outcome.Questions[i].OptionID = sel.SelectedOptionID
			outcome.Questions[i].Confidence = sel.Confidence
			if !found || sel.SelectedOptionID == "" || sel.Confidence < s.confidenceThreshold {
				outcome.Decided = false
				continue
			}
			outcome.Answers[q.ID] = sel.SelectedOptionID
		}
		if outcome.Decided {
			break
		}
		outcome.Answers = nil
		outcome.EscalateTo = next
		outcome.Reason = fmt.Sprintf("confidence below %.2f", s.confidenceThreshold)
		if evalErr != nil {
			outcome.Reason = "evaluator error: " + evalErr.Error()
		}
	}

	entry := JevDecisionLogEntry{
		Timestamp:           now.UTC(),
		Model:               s.evaluatorModel,
		ConfidenceThreshold: s.confidenceThreshold,
		Summary:             summary,
		Detail:              detail,
		Choices:             choices,
		AutoAnswered:        outcome.Decided,
		Tier:                tier,
		Category:            category,
		Outcome:             "decided",
	}
	if !outcome.Decided {
		entry.Outcome = "escalated-to-" + string(outcome.EscalateTo)
	}
	if evalErr != nil {
		entry.Error = evalErr.Error()
	}
	appendJevDecisionLog(entry)
	return outcome, nil
}
