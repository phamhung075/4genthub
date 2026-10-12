package services

// The service's own contract, over a store that is nothing but a map: the validation ORDER of a
// click, and the ask's door - the bounds, the credential scan and the ported question limits that
// refuse a malformed ask before any row exists.
//
// WHY THIS FILE EXISTS BESIDE THE ROUTE TESTS: Create has no route yet (the ask route is S2), so
// nothing else reaches the door this task requires ("a malformed ask is refused at the door, never
// stored"). The route tests own the transport; this file owns the writer.

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/room_decisions/domain/decisions"
	"agenthub/fastmcp/room_decisions/domain/questions"
	"agenthub/fastmcp/room_decisions/domain/repositories"
)

var serviceTestNow = time.Date(2026, 10, 12, 20, 1, 2, 0, time.UTC)

// fakeRoomDecisionStore is an in-memory store that counts its writes, which is how every refusal is
// shown to have written nothing.
type fakeRoomDecisionStore struct {
	rows        []repositories.RoomDecision
	creates     int
	records     int
	lastState   decisions.State
	lastAnswers map[string]string
	// recordReturnsNil makes the store answer a write with no row, the race a guarded UPDATE losing
	// to a concurrent click produces.
	recordReturnsNil bool
}

func (f *fakeRoomDecisionStore) Create(_ context.Context, decision repositories.RoomDecision) (*repositories.RoomDecision, error) {
	f.creates++
	for _, row := range f.rows {
		if row.UserID == decision.UserID && row.IdempotencyKey == decision.IdempotencyKey {
			stored := row
			return &stored, nil
		}
	}
	if decision.ID == "" {
		decision.ID = "rd-0001"
	}
	f.rows = append(f.rows, decision)
	stored := decision
	return &stored, nil
}

func (f *fakeRoomDecisionStore) Get(_ context.Context, userID, roomID, id string) (*repositories.RoomDecision, error) {
	for _, row := range f.rows {
		if row.ID == id && row.UserID == userID && row.RoomID == roomID {
			stored := row
			return &stored, nil
		}
	}
	return nil, nil
}

func (f *fakeRoomDecisionStore) ListByRoom(_ context.Context, userID, roomID string) ([]repositories.RoomDecision, error) {
	out := []repositories.RoomDecision{}
	for _, row := range f.rows {
		if row.UserID == userID && row.RoomID == roomID {
			out = append(out, row)
		}
	}
	return out, nil
}

func (f *fakeRoomDecisionStore) RecordAnswer(_ context.Context, userID, roomID, id string, answers map[string]string, state decisions.State, answeredAt *time.Time) (*repositories.RoomDecision, error) {
	f.records++
	f.lastAnswers, f.lastState = answers, state
	if f.recordReturnsNil {
		return nil, nil
	}
	for index, row := range f.rows {
		if row.ID == id && row.UserID == userID && row.RoomID == roomID {
			row.Answers, row.State, row.AnsweredAt = answers, state, answeredAt
			f.rows[index] = row
			stored := row
			return &stored, nil
		}
	}
	return nil, nil
}

// storedDecision is one pending ask of user "owner" in room "room-1".
func storedDecision(state decisions.State, answers map[string]string) repositories.RoomDecision {
	return repositories.RoomDecision{
		ID:            "rd-1",
		UserID:        "owner",
		RoomID:        "room-1",
		RigName:       "4genthub-min",
		QitemID:       "qitem-1",
		AuthorSeatKey: "go-dev",
		Destination:   "human-operator@kernel",
		Questions: []questions.HumanQuestion{
			{ID: "q1", Question: "Ship it?", Options: []questions.HumanQuestionOption{
				{ID: "ship", Label: "Ship it"}, {ID: "wait", Label: "Wait"},
			}},
			{ID: "q2", Question: "Who reviews?", Options: []questions.HumanQuestionOption{
				{ID: "lead", Label: "The lead"}, {ID: "me", Label: "Me"},
			}},
		},
		Answers:        answers,
		State:          state,
		IdempotencyKey: "agenthub:decision:qitem-1",
		CreatedAt:      serviceTestNow,
	}
}

func askBody() json.RawMessage {
	return json.RawMessage(`[{"id":"q1","question":"Ship it?","options":[{"id":"ship","label":"Ship it"},{"id":"wait","label":"Wait"}]}]`)
}

// TestAnswerValidatesInTheContractsOrder pins the order and the token each failure carries. The
// replay step before the state check is the one the contract's idempotency clause forces: the click
// that completed the ask moved the row to answered, and a client retrying THAT click must not be
// told its click was too late.
func TestAnswerValidatesInTheContractsOrder(t *testing.T) {
	completed := serviceTestNow.Add(time.Minute)
	answered := storedDecision(decisions.StateAnswered, map[string]string{"q1": "ship", "q2": "lead"})
	answered.AnsweredAt = &completed

	cases := []struct {
		name       string
		row        repositories.RoomDecision
		id         string
		user       string
		input      RoomDecisionAnswerInput
		code       string
		wantWrites int
	}{
		{
			name: "a decision that is not in this room or tenant", row: storedDecision(decisions.StatePending, map[string]string{}),
			id: "rd-elsewhere", user: "owner", input: RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "ship"},
			code: CodeUnknownDecision,
		},
		{
			name: "an exact replay answers with the stored row and writes nothing",
			row:  answered, id: "rd-1", user: "owner", input: RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "ship"},
			code: "",
		},
		{
			name: "a question the ask does not carry", row: storedDecision(decisions.StatePending, map[string]string{}),
			id: "rd-1", user: "owner", input: RoomDecisionAnswerInput{QuestionID: "q9", OptionID: "ship"},
			code: CodeUnknownQuestion,
		},
		{
			name: "an option outside the stored options", row: storedDecision(decisions.StatePending, map[string]string{}),
			id: "rd-1", user: "owner", input: RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "rocket"},
			code: CodeUnknownOption,
		},
		{
			name: "a decision that is not pending", row: answered, id: "rd-1", user: "owner",
			input: RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "wait"}, code: decisions.RefusalCode(decisions.StateAnswered),
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			store := &fakeRoomDecisionStore{rows: []repositories.RoomDecision{tc.row}}
			service := NewRoomDecisionService(store)

			stored, err := service.Answer(context.Background(), tc.user, "room-1", tc.id, tc.input, serviceTestNow)
			if tc.code != "" {
				var rejection *RoomDecisionAnswerRejection
				if err == nil || !asAnswerRejection(err, &rejection) {
					t.Fatalf("err = %v, want a refusal with code %q", err, tc.code)
				}
				if rejection.Code != tc.code {
					t.Fatalf("code = %q, want %q", rejection.Code, tc.code)
				}
				if store.records != 0 {
					t.Fatalf("the refusal wrote %d time(s), want none", store.records)
				}
				return
			}
			if err != nil {
				t.Fatalf("Answer: %v", err)
			}
			if stored == nil || stored.ID != tc.row.ID {
				t.Fatalf("stored = %+v, want the row already there", stored)
			}
			if store.records != 0 {
				t.Fatalf("the replay wrote %d time(s), want none", store.records)
			}
		})
	}
}

// TestAnswerRecordsTheClickThatCompletesTheAsk covers the accepting path: a click on the first
// question leaves the ask pending, the click on the last one moves it to answered with the instant
// the route reported, and the answers map is the whole state rather than one row per click.
func TestAnswerRecordsTheClickThatCompletesTheAsk(t *testing.T) {
	store := &fakeRoomDecisionStore{rows: []repositories.RoomDecision{storedDecision(decisions.StatePending, map[string]string{})}}
	service := NewRoomDecisionService(store)

	stored, err := service.Answer(context.Background(), "owner", "room-1", "rd-1",
		RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "ship"}, serviceTestNow)
	if err != nil {
		t.Fatalf("first click: %v", err)
	}
	if stored.State != decisions.StatePending || stored.AnsweredAt != nil || stored.Answers["q1"] != "ship" {
		t.Fatalf("first click stored %+v, want pending with no answered_at", stored)
	}
	if stored.Complete() {
		t.Error("the ask is complete with a question unanswered")
	}

	completedAt := serviceTestNow.Add(30 * time.Second)
	stored, err = service.Answer(context.Background(), "owner", "room-1", "rd-1",
		RoomDecisionAnswerInput{QuestionID: "q2", OptionID: "lead"}, completedAt)
	if err != nil {
		t.Fatalf("completing click: %v", err)
	}
	if stored.State != decisions.StateAnswered || !stored.Complete() {
		t.Fatalf("completing click stored %+v, want answered and complete", stored)
	}
	if stored.AnsweredAt == nil || !stored.AnsweredAt.Equal(completedAt) {
		t.Fatalf("answered_at = %v, want the caller's clock %v", stored.AnsweredAt, completedAt)
	}
	if len(stored.Answers) != 2 || stored.Answers["q1"] != "ship" || stored.Answers["q2"] != "lead" {
		t.Fatalf("answers = %v, want both clicks", stored.Answers)
	}

	// A change of mind while the ask is still pending is applied: that is the daemon's own
	// recordHumanAnswer semantics and Slack's.
	pending := &fakeRoomDecisionStore{rows: []repositories.RoomDecision{storedDecision(decisions.StatePending, map[string]string{"q1": "ship"})}}
	changed, err := NewRoomDecisionService(pending).Answer(context.Background(), "owner", "room-1", "rd-1",
		RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "wait"}, serviceTestNow)
	if err != nil {
		t.Fatalf("changing a pending answer: %v", err)
	}
	if changed.Answers["q1"] != "wait" {
		t.Fatalf("answers = %v, want the changed option", changed.Answers)
	}
}

// TestAnswerReportsADecisionThatVanished covers the store's guarded write losing its row: the answer
// is the refusal the read at the top of the method would have given, not a nil dereference.
func TestAnswerReportsADecisionThatVanished(t *testing.T) {
	store := &fakeRoomDecisionStore{
		rows:             []repositories.RoomDecision{storedDecision(decisions.StatePending, map[string]string{})},
		recordReturnsNil: true,
	}
	_, err := NewRoomDecisionService(store).Answer(context.Background(), "owner", "room-1", "rd-1",
		RoomDecisionAnswerInput{QuestionID: "q1", OptionID: "ship"}, serviceTestNow)
	var rejection *RoomDecisionAnswerRejection
	if err == nil || !asAnswerRejection(err, &rejection) || rejection.Code != CodeUnknownDecision {
		t.Fatalf("err = %v, want %s", err, CodeUnknownDecision)
	}
}

// TestCreateRefusesAMalformedAskAtTheDoor is the ported-limits half of the writer: every case is a
// value the daemon's parseHumanQuestions refuses, and NOTHING is stored - the store's create count is
// the proof.
func TestCreateRefusesAMalformedAskAtTheDoor(t *testing.T) {
	longSummary := strings.Repeat("s", RoomDecisionMaxSummary+1)
	longDetail := strings.Repeat("d", RoomDecisionMaxDetail+1)
	cases := []struct {
		name   string
		ask    RoomDecisionAsk
		miss   string
		secret string
	}{
		{
			name: "no questions",
			ask:  RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "k", Questions: json.RawMessage(`[]`)},
			miss: "Ask 1 to 4 questions",
		},
		{
			name: "an option id outside the token rule",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "k",
				Questions: json.RawMessage(`[{"id":"q1","question":"a?","options":[{"id":"a b","label":"A"},{"id":"b","label":"B"}]}]`)},
			miss: "id must be 1-40 letters",
		},
		{
			name: "a question value that is not an array",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "k",
				Questions: json.RawMessage(`{"id":"q1"}`)},
			miss: "must be an array",
		},
		{
			name: "no idempotency key",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h",
				Questions: askBody()},
			miss: "idempotency_key is required",
		},
		{
			name: "no destination",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", IdempotencyKey: "k",
				Questions: askBody()},
			miss: "destination is required",
		},
		{
			name: "a summary over the bound",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "k",
				Summary: longSummary, Questions: askBody()},
			miss: "summary cannot exceed",
		},
		{
			name: "a detail over the bound",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "k",
				Detail: longDetail, Questions: askBody()},
			miss: "detail cannot exceed",
		},
		{
			name: "a credential in the detail",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "k",
				Detail: "use AKIAIOSFODNN7EXAMPLE to read the bucket", Questions: askBody()},
			secret: "detail",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			store := &fakeRoomDecisionStore{}
			_, err := NewRoomDecisionService(store).Create(context.Background(), "owner", "room-1", tc.ask, serviceTestNow)
			var rejection *RoomDecisionAskRejection
			if err == nil || !asAskRejection(err, &rejection) {
				t.Fatalf("err = %v, want a RoomDecisionAskRejection", err)
			}
			if tc.secret != "" {
				if rejection.SecretField != tc.secret || !strings.Contains(rejection.Message, "secret detected") {
					t.Fatalf("rejection = %+v, want the secret named for %q", rejection, tc.secret)
				}
				if strings.Contains(rejection.Message, "AKIAIOSFODNN7EXAMPLE") {
					t.Error("the refusal echoes the credential")
				}
			} else if !strings.Contains(rejection.Message, tc.miss) {
				t.Errorf("message = %q, want it to name %q", rejection.Message, tc.miss)
			}
			if store.creates != 0 {
				t.Errorf("a refused ask was stored %d time(s)", store.creates)
			}
		})
	}
}

// TestCreateStoresAValidAskAndCollapsesARedrive covers the accepting path and the durable-first
// redrive: the same ask's key twice leaves ONE row, and the second answer is the row the first
// attempt made rather than a second decision the human would be asked twice.
func TestCreateStoresAValidAskAndCollapsesARedrive(t *testing.T) {
	store := &fakeRoomDecisionStore{}
	service := NewRoomDecisionService(store)
	ask := RoomDecisionAsk{
		RigName:        "4genthub-min",
		QitemID:        "qitem-1",
		AuthorSeatKey:  "go-dev",
		Destination:    "human-operator@kernel",
		Summary:        "ship the cloud half first?",
		Detail:         "the panel needs the answer",
		IdempotencyKey: "agenthub:decision:qitem-1",
		Questions:      askBody(),
	}

	first, err := service.Create(context.Background(), "owner", "room-1", ask, serviceTestNow)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if first == nil || first.State != decisions.StatePending || len(first.Answers) != 0 {
		t.Fatalf("stored = %+v, want a pending ask with no answers", first)
	}
	if first.ID == "" || first.UserID != "owner" || first.RoomID != "room-1" {
		t.Fatalf("stored identity = %+v", first)
	}
	if len(first.Questions) != 1 || first.Questions[0].ID != "q1" || len(first.Questions[0].Options) != 2 {
		t.Fatalf("stored questions = %+v, want the parsed ask", first.Questions)
	}
	if !first.CreatedAt.Equal(serviceTestNow) {
		t.Errorf("created_at = %v, want the caller's clock", first.CreatedAt)
	}

	second, err := service.Create(context.Background(), "owner", "room-1", ask, serviceTestNow)
	if err != nil {
		t.Fatalf("redrive: %v", err)
	}
	if second.ID != first.ID {
		t.Fatalf("the redrive made a second row: %s then %s", first.ID, second.ID)
	}
	if len(store.rows) != 1 {
		t.Fatalf("rows = %d, want one ask mirrored once", len(store.rows))
	}
}

// TestListReturnsTheTenantsRoomScopedRows covers the read the route serves.
func TestListReturnsTheTenantsRoomScopedRows(t *testing.T) {
	mine := storedDecision(decisions.StatePending, map[string]string{})
	otherRoom := storedDecision(decisions.StatePending, map[string]string{})
	otherRoom.ID, otherRoom.RoomID = "rd-2", "room-2"
	otherTenant := storedDecision(decisions.StatePending, map[string]string{})
	otherTenant.ID, otherTenant.UserID = "rd-3", "stranger"

	store := &fakeRoomDecisionStore{rows: []repositories.RoomDecision{mine, otherRoom, otherTenant}}
	got, err := NewRoomDecisionService(store).List(context.Background(), "owner", "room-1")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(got) != 1 || got[0].ID != "rd-1" {
		t.Fatalf("List = %+v, want only the caller's row in this room", got)
	}
}

// asAnswerRejection and asAskRejection are errors.As for this file's two refusal types.
func asAnswerRejection(err error, target **RoomDecisionAnswerRejection) bool {
	rejection, ok := err.(*RoomDecisionAnswerRejection)
	if ok {
		*target = rejection
	}
	return ok
}

func asAskRejection(err error, target **RoomDecisionAskRejection) bool {
	rejection, ok := err.(*RoomDecisionAskRejection)
	if ok {
		*target = rejection
	}
	return ok
}
