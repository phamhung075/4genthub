// Package questions holds the shape and the CLOSED LIMITS of the structured questions a decision
// may carry: 1-4 questions, each with 2-4 options the human can click.
//
// THE LIMITS ARE THE DAEMON'S, PORTED RATHER THAN RE-INVENTED. The authority is
// packages/daemon/src/domain/human-questions.ts in the OpenRig repository: parseHumanQuestions
// there is what a local queue row is validated against before a decision is ever authored, and a
// cloud that accepted a wider shape would store an ask the daemon refuses to author - or, worse,
// accept one the daemon cannot apply. The constants below carry the daemon's values and the daemon's
// rules, including that extra fields are dropped rather than kept and that at most one option per
// question may be marked recommended.
//
// WHY THE CLOUD VALIDATES AT ALL, given the daemon already does: the cloud row is a projection, and
// a projection that accepts what the authority rejects is a second, weaker contract. The task's
// wording is "refused at the door, never stored": a malformed ask is rejected before any row exists.
//
// WHAT IS DELIBERATELY NOT PORTED: the typed-reply variant of an answer. A whole thread reply is
// placed by the daemon against its own queue row; the cloud only ever records a CLICK on one option,
// so its answers map is questionId -> optionId and nothing else.
package questions

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"unicode/utf8"
)

// The daemon's limits, values and comments alike (MAX_HUMAN_QUESTIONS, MIN_OPTIONS, MAX_OPTIONS,
// MAX_OPTION_LABEL, MAX_QUESTION_TEXT in human-questions.ts).
const (
	// MaxHumanQuestions is how many questions one ask may carry.
	MaxHumanQuestions = 4
	// MinOptions and MaxOptions bound one question's options.
	MinOptions = 2
	MaxOptions = 4
	// MaxOptionLabel is the Slack Block Kit button limit: an option's plain_text is at most 75
	// characters, and the daemon's message builder truncates to it.
	MaxOptionLabel = 75
	// MaxQuestionText bounds one question's own text.
	MaxQuestionText = 500
)

// idPattern is the daemon's ID_PATTERN. An id is what an answer is recorded against, so it is a
// token rather than prose: letters, digits, "-" and "_", 1 to 40 of them.
var idPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{1,40}$`)

// idRule is the daemon's ID_RULE, so a refusal reads the same on both sides.
const idRule = `id must be 1-40 letters, digits, "-" or "_".`

// HumanQuestionOption is one clickable option. Recommended is a pointer because "not set" and
// "false" are the same thing to a reader, and the field is dropped when absent.
type HumanQuestionOption struct {
	ID          string `json:"id"`
	Label       string `json:"label"`
	Recommended *bool  `json:"recommended,omitempty"`
}

// HumanQuestion is one question of an ask, with 2-4 options.
type HumanQuestion struct {
	ID       string                `json:"id"`
	Question string                `json:"question"`
	Options  []HumanQuestionOption `json:"options"`
}

// Rejection is a questions value the contract refuses. It carries the daemon's own message, because
// the author of the ask is the same person on both sides and two vocabularies for one rule would be
// a bug of its own.
type Rejection struct {
	Message string
}

func (e *Rejection) Error() string { return e.Message }

// Parse validates an authored questions value and returns a normalized copy: only known fields are
// kept, exactly as the daemon's parseHumanQuestions does. A malformed value is refused whole - one
// bad question rejects the ask rather than being dropped from it, because a silently shortened ask
// is a decision nobody agreed to.
func Parse(value json.RawMessage) ([]HumanQuestion, error) {
	if len(value) == 0 {
		return nil, &Rejection{Message: "humanQuestions must be an array of questions."}
	}
	var raw []json.RawMessage
	if err := json.Unmarshal(value, &raw); err != nil {
		return nil, &Rejection{Message: "humanQuestions must be an array of questions."}
	}
	if len(raw) < 1 || len(raw) > MaxHumanQuestions {
		return nil, &Rejection{Message: fmt.Sprintf("Ask 1 to %d questions (got %d).", MaxHumanQuestions, len(raw))}
	}

	questionIDs := map[string]bool{}
	out := make([]HumanQuestion, 0, len(raw))
	for index, item := range raw {
		where := fmt.Sprintf("question %d", index+1)
		var q struct {
			ID       *string `json:"id"`
			Question *string `json:"question"`
			Options  *[]struct {
				ID          *string `json:"id"`
				Label       *string `json:"label"`
				Recommended *bool   `json:"recommended"`
			} `json:"options"`
		}
		if err := json.Unmarshal(item, &q); err != nil {
			return nil, &Rejection{Message: fmt.Sprintf("%s: %s", where, idRule)}
		}
		if q.ID == nil || !idPattern.MatchString(*q.ID) {
			return nil, &Rejection{Message: fmt.Sprintf("%s: %s", where, idRule)}
		}
		if questionIDs[*q.ID] {
			return nil, &Rejection{Message: fmt.Sprintf("%s: duplicate question id %q.", where, *q.ID)}
		}
		questionIDs[*q.ID] = true
		if q.Question == nil || strings.TrimSpace(*q.Question) == "" {
			return nil, &Rejection{Message: fmt.Sprintf("%s: question text is required.", where)}
		}
		text := *q.Question
		if utf8.RuneCountInString(text) > MaxQuestionText {
			return nil, &Rejection{Message: fmt.Sprintf("%s: question text is over %d characters.", where, MaxQuestionText)}
		}
		if q.Options == nil || len(*q.Options) < MinOptions || len(*q.Options) > MaxOptions {
			got := 0
			if q.Options != nil {
				got = len(*q.Options)
			}
			return nil, &Rejection{Message: fmt.Sprintf("%s: give %d to %d options (got %d).", where, MinOptions, MaxOptions, got)}
		}

		optionIDs := map[string]bool{}
		options := make([]HumanQuestionOption, 0, len(*q.Options))
		recommended := 0
		for optionIndex, rawOption := range *q.Options {
			optionWhere := fmt.Sprintf("%s option %d", where, optionIndex+1)
			if rawOption.ID == nil || !idPattern.MatchString(*rawOption.ID) {
				return nil, &Rejection{Message: fmt.Sprintf("%s: %s", optionWhere, idRule)}
			}
			if optionIDs[*rawOption.ID] {
				return nil, &Rejection{Message: fmt.Sprintf("%s: duplicate option id %q.", optionWhere, *rawOption.ID)}
			}
			optionIDs[*rawOption.ID] = true
			if rawOption.Label == nil || strings.TrimSpace(*rawOption.Label) == "" {
				return nil, &Rejection{Message: fmt.Sprintf("%s: label is required.", optionWhere)}
			}
			if utf8.RuneCountInString(*rawOption.Label) > MaxOptionLabel {
				return nil, &Rejection{Message: fmt.Sprintf("%s: label is over Slack's %d-character button limit.", optionWhere, MaxOptionLabel)}
			}
			option := HumanQuestionOption{ID: *rawOption.ID, Label: *rawOption.Label}
			if rawOption.Recommended != nil && *rawOption.Recommended {
				recommended++
				option.Recommended = rawOption.Recommended
			}
			options = append(options, option)
		}
		if recommended > 1 {
			return nil, &Rejection{Message: fmt.Sprintf("%s: mark at most one option as recommended.", where)}
		}

		out = append(out, HumanQuestion{ID: *q.ID, Question: text, Options: options})
	}
	return out, nil
}

// Option returns the option with the id, and whether it is in the question at all. An answer is
// validated against this rather than against the client's copy of the options: the stored options
// are the only vocabulary a click may use.
func (q HumanQuestion) Option(optionID string) (HumanQuestionOption, bool) {
	for _, option := range q.Options {
		if option.ID == optionID {
			return option, true
		}
	}
	return HumanQuestionOption{}, false
}

// Find returns the question with the id.
func Find(list []HumanQuestion, questionID string) (HumanQuestion, bool) {
	for _, question := range list {
		if question.ID == questionID {
			return question, true
		}
	}
	return HumanQuestion{}, false
}
