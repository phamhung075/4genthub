package questions

// The ported limits, as a table: each case is one rule of the daemon's parseHumanQuestions, and the
// refusals are asserted to be refusals so a later loosening of the cloud's copy shows up here rather
// than on a human's panel. No database, no server: this is the vocabulary the ask is validated against.

import (
	"encoding/json"
	"errors"
	"strings"
	"testing"
)

// valid is one ask that must pass, reused as the base each negative case perturbs.
func valid() json.RawMessage {
	return json.RawMessage(`[
		{"id":"q1","question":"Ship the cloud half first?","options":[
			{"id":"ship","label":"Ship it","recommended":true},
			{"id":"wait","label":"Wait"}]},
		{"id":"q2","question":"Who reviews?","options":[{"id":"lead","label":"The lead"},{"id":"me","label":"Me"}]}
	]`)
}

func TestParseAcceptsTheDaemonsShapeAndDropsUnknownFields(t *testing.T) {
	// The two extra fields are what the daemon's parser drops rather than keeps: a stored question
	// that carried a field the panel would then render is a shape nobody agreed to.
	raw := json.RawMessage(`[{"id":"q1","question":"Ship it?","colour":"red","options":[
		{"id":"yes","label":"Yes","recommended":false,"icon":"x"},
		{"id":"no","label":"No"}]}]`)
	list, err := Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if len(list) != 1 || list[0].ID != "q1" || len(list[0].Options) != 2 {
		t.Fatalf("parsed = %+v, want one question with two options", list)
	}
	// recommended:false is not "recommended": the pointer is nil, and the JSON the cloud stores
	// therefore carries no recommended key at all.
	if list[0].Options[0].Recommended != nil {
		t.Errorf("recommended=false was kept: %+v", list[0].Options[0])
	}
	encoded, err := json.Marshal(list)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(encoded), "colour") || strings.Contains(string(encoded), "icon") ||
		strings.Contains(string(encoded), "recommended") {
		t.Errorf("the stored form carries fields the daemon drops: %s", encoded)
	}
}

func TestParseKeepsOneRecommendedPerQuestion(t *testing.T) {
	raw := json.RawMessage(`[{"id":"q1","question":"Ship it?","options":[
		{"id":"yes","label":"Yes","recommended":true},
		{"id":"no","label":"No"}]}]`)
	list, err := Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if list[0].Options[0].Recommended == nil || !*list[0].Options[0].Recommended {
		t.Errorf("the recommendation was lost: %+v", list[0].Options[0])
	}
}

func TestParseRefusesWhatTheDaemonRefuses(t *testing.T) {
	longText := strings.Repeat("x", MaxQuestionText+1)
	longLabel := strings.Repeat("y", MaxOptionLabel+1)
	fiveOptions := `[{"id":"a","label":"A"},{"id":"b","label":"B"},{"id":"c","label":"C"},{"id":"d","label":"D"},{"id":"e","label":"E"}]`
	cases := []struct {
		name string
		raw  string
		miss string
	}{
		{"empty value", ``, "must be an array"},
		{"not an array", `{"id":"q1"}`, "must be an array"},
		{"no questions", `[]`, "Ask 1 to 4 questions (got 0)"},
		{"too many questions", `[
			{"id":"q1","question":"a?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
			{"id":"q2","question":"b?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
			{"id":"q3","question":"c?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
			{"id":"q4","question":"d?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
			{"id":"q5","question":"e?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`,
			"Ask 1 to 4 questions (got 5)"},
		{"missing id", `[{"question":"a?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`, idRule},
		{"id with a space", `[{"id":"q 1","question":"a?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`, idRule},
		{"id too long", `[{"id":"` + strings.Repeat("q", 41) + `","question":"a?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`, idRule},
		{"duplicate question id", `[
			{"id":"q1","question":"a?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
			{"id":"q1","question":"b?","options":[{"id":"c","label":"C"},{"id":"d","label":"D"}]}]`,
			`duplicate question id "q1"`},
		{"empty question text", `[{"id":"q1","question":"   ","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`, "question text is required"},
		{"question text too long", `[{"id":"q1","question":"` + longText + `","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`, "over 500 characters"},
		{"one option", `[{"id":"q1","question":"a?","options":[{"id":"a","label":"A"}]}]`, "give 2 to 4 options (got 1)"},
		{"too many options", `[{"id":"q1","question":"a?","options":` + fiveOptions + `}]`, "give 2 to 4 options (got 5)"},
		{"duplicate option id", `[{"id":"q1","question":"a?","options":[{"id":"a","label":"A"},{"id":"a","label":"B"}]}]`, `duplicate option id "a"`},
		{"option without a label", `[{"id":"q1","question":"a?","options":[{"id":"a","label":"  "},{"id":"b","label":"B"}]}]`, "label is required"},
		{"option label over the button limit", `[{"id":"q1","question":"a?","options":[{"id":"a","label":"` + longLabel + `"},{"id":"b","label":"B"}]}]`, "Slack's 75-character button limit"},
		{"two recommendations", `[{"id":"q1","question":"a?","options":[
			{"id":"a","label":"A","recommended":true},{"id":"b","label":"B","recommended":true}]}]`, "at most one option as recommended"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			list, err := Parse(json.RawMessage(tc.raw))
			if err == nil {
				t.Fatalf("accepted a value the contract refuses: %+v", list)
			}
			var rejection *Rejection
			if !errors.As(err, &rejection) {
				t.Fatalf("refusal is not a *questions.Rejection: %T", err)
			}
			if !strings.Contains(rejection.Message, tc.miss) {
				t.Errorf("message = %q, want it to name %q", rejection.Message, tc.miss)
			}
		})
	}
}

func TestParseAcceptsTheMaximum(t *testing.T) {
	// The boundary itself, not only the refusals: four questions of four options each.
	raw := json.RawMessage(`[
		{"id":"q1","question":"a?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"},{"id":"c","label":"C"},{"id":"d","label":"D"}]},
		{"id":"q2","question":"b?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
		{"id":"q3","question":"c?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]},
		{"id":"q4","question":"d?","options":[{"id":"a","label":"A"},{"id":"b","label":"B"}]}]`)
	list, err := Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if len(list) != 4 || len(list[0].Options) != 4 {
		t.Fatalf("parsed = %d questions, %d options in the first", len(list), len(list[0].Options))
	}
	if len(valid()) == 0 {
		t.Fatal("unreachable")
	}
}

func TestFindAndOptionResolveAgainstTheStoredShape(t *testing.T) {
	list, err := Parse(valid())
	if err != nil {
		t.Fatal(err)
	}
	question, ok := Find(list, "q2")
	if !ok || question.ID != "q2" {
		t.Fatalf("Find(q2) = %+v, %v", question, ok)
	}
	if _, ok := Find(list, "q9"); ok {
		t.Error("Find(q9) found a question that is not there")
	}
	if option, ok := list[0].Option("ship"); !ok || option.Label != "Ship it" {
		t.Errorf("Option(ship) = %+v, %v", option, ok)
	}
	if _, ok := list[0].Option("rocket"); ok {
		t.Error("Option(rocket) found an option that is not in the question")
	}
}
