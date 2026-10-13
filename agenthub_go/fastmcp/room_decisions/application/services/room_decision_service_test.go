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
	"os"
	"path/filepath"
	"sort"
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
	pulls       int
	acks        int
	states      int
	lastState   decisions.State
	lastAnswers map[string]string
	// roomSlugs is what the rooms of these rows are called, the SLUG the pull hands out beside each
	// decision. A room it does not name falls back to the row's room id.
	roomSlugs map[string]string
	// recordReturnsNil makes the store answer a write with no row, the race a guarded UPDATE losing
	// to a concurrent click produces.
	recordReturnsNil bool
	// createReturnsNothing makes the mirror answer "not written, and no winner to read back": the one
	// state the service must turn into a 500 rather than a success envelope with no decision in it.
	createReturnsNothing bool
}

func (f *fakeRoomDecisionStore) Create(_ context.Context, decision repositories.RoomDecision) (*repositories.RoomDecision, bool, error) {
	f.creates++
	if f.createReturnsNothing {
		return nil, false, nil
	}
	// The dedupe is the EPISODE and not the key: the store's conflict target and its loser read are
	// both (user_id, qitem_id), so one routed item asked about by two tenants is two rows even when
	// the idempotency keys they derive are the same string.
	for _, row := range f.rows {
		if row.UserID == decision.UserID && row.QitemID == decision.QitemID {
			stored := row
			return &stored, false, nil
		}
	}
	if decision.ID == "" {
		decision.ID = "rd-0001"
	}
	f.rows = append(f.rows, decision)
	stored := decision
	return &stored, true, nil
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

func (f *fakeRoomDecisionStore) GetByID(_ context.Context, userID, id string) (*repositories.RoomDecision, error) {
	for _, row := range f.rows {
		if row.ID == id && row.UserID == userID {
			stored := row
			return &stored, nil
		}
	}
	return nil, nil
}

// ListAnswers is the pull over the slice: the answered, UNACKED rows of one rig, oldest first, after
// the cursor, each carrying the slug its room is known by here. The order, the cursor rule and the
// acked filter are the store's own - (answered_at, id) and acked_at IS NULL - so a case that resumes
// from a cursor exercises the same rule the SQL's comparison does.
func (f *fakeRoomDecisionStore) ListAnswers(_ context.Context, userID, rigName string, after *repositories.AnswerCursor, limit int) ([]repositories.AnswerDelivery, error) {
	f.pulls++
	out := []repositories.AnswerDelivery{}
	for _, row := range f.rows {
		if row.UserID != userID || row.RigName != rigName ||
			row.State != decisions.StateAnswered || row.AnsweredAt == nil || row.AckedAt != nil {
			continue
		}
		if !pullAfterCursor(row, after) {
			continue
		}
		slug := f.roomSlugs[row.RoomID]
		if slug == "" {
			slug = row.RoomID
		}
		out = append(out, repositories.AnswerDelivery{RoomDecision: row, RoomSlug: slug})
	}
	sort.Slice(out, func(i, j int) bool {
		left, right := *out[i].AnsweredAt, *out[j].AnsweredAt
		if !left.Equal(right) {
			return left.Before(right)
		}
		return out[i].ID < out[j].ID
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

// pullAfterCursor reports whether a row sorts after the cursor's position.
func pullAfterCursor(row repositories.RoomDecision, after *repositories.AnswerCursor) bool {
	if after == nil {
		return true
	}
	at := row.AnsweredAt.UTC()
	if at.Equal(after.AnsweredAt) {
		return row.ID > after.ID
	}
	return at.After(after.AnsweredAt)
}

// Acknowledge records a delivery the way the guarded UPDATE does: only a row still `answered` and
// unacked moves, BOTH outcomes set acked_at, and `applied` also closes the row as resolved. An id
// that is not there at all answers nil with false, which is the conflict the route reports.
func (f *fakeRoomDecisionStore) Acknowledge(_ context.Context, userID, id string, applied bool, at time.Time) (*repositories.RoomDecision, bool, error) {
	f.acks++
	for index, row := range f.rows {
		if row.ID != id || row.UserID != userID {
			continue
		}
		acked := false
		if row.State == decisions.StateAnswered && row.AckedAt == nil {
			utc := at.UTC()
			row.AckedAt = &utc
			if applied {
				row.State, row.ResolvedAt = decisions.StateResolved, &utc
			}
			f.rows[index] = row
			acked = true
		}
		stored := row
		return &stored, acked, nil
	}
	return nil, false, nil
}

// SetState writes the daemon's verdict, guarded on the row being open exactly as the UPDATE is.
func (f *fakeRoomDecisionStore) SetState(_ context.Context, userID, id string, state decisions.State, at time.Time) (*repositories.RoomDecision, error) {
	f.states++
	for index, row := range f.rows {
		if row.ID != id || row.UserID != userID {
			continue
		}
		if row.State == decisions.StatePending || row.State == decisions.StateAnswered {
			row.State = state
			if state == decisions.StateResolved {
				utc := at.UTC()
				row.ResolvedAt = &utc
			}
			f.rows[index] = row
		}
		stored := row
		return &stored, nil
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
			ask:  RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "agenthub:decision:q", Questions: json.RawMessage(`[]`)},
			miss: "Ask 1 to 4 questions",
		},
		{
			name: "an option id outside the token rule",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "agenthub:decision:q",
				Questions: json.RawMessage(`[{"id":"q1","question":"a?","options":[{"id":"a b","label":"A"},{"id":"b","label":"B"}]}]`)},
			miss: "id must be 1-40 letters",
		},
		{
			name: "a question value that is not an array",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "agenthub:decision:q",
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
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", IdempotencyKey: "agenthub:decision:q",
				Questions: askBody()},
			miss: "destination is required",
		},
		{
			name: "a summary over the bound",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "agenthub:decision:q",
				Summary: longSummary, Questions: askBody()},
			miss: "summary cannot exceed",
		},
		{
			name: "a detail over the bound",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "agenthub:decision:q",
				Detail: longDetail, Questions: askBody()},
			miss: "detail cannot exceed",
		},
		{
			name: "a key that does not derive from the qitem",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h",
				IdempotencyKey: "agenthub:decision:another-item", Questions: askBody()},
			miss: "idempotency_key must be agenthub:decision:<qitem_id>",
		},
		{
			name: "a credential in the detail",
			ask: RoomDecisionAsk{RigName: "r", QitemID: "q", AuthorSeatKey: "s", Destination: "h", IdempotencyKey: "agenthub:decision:q",
				Detail: "use AKIAIOSFODNN7EXAMPLE to read the bucket", Questions: askBody()},
			secret: "detail",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			store := &fakeRoomDecisionStore{}
			_, _, err := NewRoomDecisionService(store).Create(context.Background(), "owner", "room-1", tc.ask, serviceTestNow)
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

// TestCreateRefusesARowTheStoreNeitherWroteNorFound pins the guard on the state that must never reach
// the wire: a write that stored nothing AND could not read the winner back. The route answers 500 for
// it, never a success envelope with no decision - the shape that let one tenant's ask vanish. The
// store's loser path makes it unreachable by reading the same tuple the insert conflicted on.
func TestCreateRefusesARowTheStoreNeitherWroteNorFound(t *testing.T) {
	store := &fakeRoomDecisionStore{createReturnsNothing: true}
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

	stored, created, err := service.Create(context.Background(), "owner", "room-1", ask, serviceTestNow)
	if err == nil {
		t.Fatalf("Create returned no error for a write that stored nothing and found nothing (stored=%+v created=%v)", stored, created)
	}
	if stored != nil || created {
		t.Errorf("stored=%+v created=%v, want no row and no created flag beside the error", stored, created)
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

	first, created, err := service.Create(context.Background(), "owner", "room-1", ask, serviceTestNow)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if !created {
		t.Errorf("created = false, want true for the call that stored the row")
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

	second, createdAgain, err := service.Create(context.Background(), "owner", "room-1", ask, serviceTestNow)
	if err != nil {
		t.Fatalf("redrive: %v", err)
	}
	if createdAgain {
		t.Errorf("created = true on the redrive, want false: an earlier attempt stored it")
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

// ---------------------------------------------------------------------------------------------
// The answer leg: the pull, the ack and the state push.
// ---------------------------------------------------------------------------------------------

// answeredAt puts one fixture row into the state the pull hands out.
func answeredAt(row repositories.RoomDecision, at time.Time) repositories.RoomDecision {
	utc := at.UTC()
	row.State = decisions.StateAnswered
	row.AnsweredAt = &utc
	return row
}

// TestPullMintsTheShippedCursorAndRefusesOneItDidNot covers the answer leg's read: the page carries
// each delivery's room slug, the cursor is the shipped `<RFC3339Nano>|<uuid>` STRING rather than a
// second encoding of it, and the refusals are the contract's - a pull that names no machine, and a
// cursor this channel did not mint.
func TestPullMintsTheShippedCursorAndRefusesOneItDidNot(t *testing.T) {
	at := serviceTestNow.UTC()
	// The ids are UUIDs because the cursor's second half is validated as one: a row's id is the id the
	// store keyed it by, and the pull mints the position from it.
	first := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "ship"}), at)
	first.ID = "a1e0d3c2-3333-4333-8333-000000000001"
	second := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "wait"}), at.Add(time.Minute))
	second.ID = "a1e0d3c2-3333-4333-8333-000000000002"
	store := &fakeRoomDecisionStore{
		rows:      []repositories.RoomDecision{first, second},
		roomSlugs: map[string]string{"room-1": "alpha"},
	}
	// created_at sits FAR from answered_at on purpose: a cursor minted from the ask's created_at would
	// render another string, and this is the case that says which key this pull pages on.
	first.CreatedAt = at.Add(24 * time.Hour)
	second.CreatedAt = at.Add(48 * time.Hour)
	service := NewRoomDecisionService(store)
	ctx := context.Background()

	deliveries, cursor, err := service.Pull(ctx, "owner", "4genthub-min", "", 0)
	if err != nil {
		t.Fatalf("Pull: %v", err)
	}
	if len(deliveries) != 2 || deliveries[0].ID != first.ID || deliveries[1].ID != second.ID {
		t.Fatalf("deliveries = %+v, want both answered rows oldest first", deliveries)
	}
	if deliveries[0].RoomSlug != "alpha" {
		t.Errorf("RoomSlug = %q, want the room's slug beside the row", deliveries[0].RoomSlug)
	}
	if want := second.AnsweredAt.UTC().Format(time.RFC3339Nano) + "|" + second.ID; cursor != want {
		t.Fatalf("cursor = %q, want the last row's position %q", cursor, want)
	}

	// Resuming from that cursor hands over what follows it - here, nothing - rather than the page
	// again: the comparison is the store's own (answered_at, id).
	page, next, err := service.Pull(ctx, "owner", "4genthub-min", cursor, 0)
	if err != nil {
		t.Fatalf("resumed Pull: %v", err)
	}
	if len(page) != 0 || next != "" {
		t.Fatalf("resumed page = %+v (cursor %q), want nothing left", page, next)
	}

	var rejection *RoomDecisionAnswerRejection
	if _, _, err := service.Pull(ctx, "owner", "   ", "", 0); err == nil ||
		!asAnswerRejection(err, &rejection) || rejection.Code != CodeInvalidPull {
		t.Errorf("pull with no rig err = %v, want %s", err, CodeInvalidPull)
	}
	// A cursor this channel did not mint is refused in the contract's own words rather than treated
	// as a first page: a daemon resuming from a token it made up would be handed answers twice.
	if _, _, err := service.Pull(ctx, "owner", "4genthub-min", "not-a-cursor", 0); err == nil ||
		!asAnswerRejection(err, &rejection) || rejection.Code != CodeInvalidCursor ||
		rejection.Message != `after "not-a-cursor" must be a cursor this endpoint returned` {
		t.Errorf("bad cursor err = %v, want the pinned sentence", err)
	}

	// The page bounds have one home, which is the function the route's own tests page by.
	for _, tc := range []struct{ in, want int }{
		{0, RoomDecisionPullLimit},
		{-4, RoomDecisionPullLimit},
		{999, RoomDecisionMaxPullLimit},
		{3, 3},
	} {
		if got := ClampDecisionAnswerLimit(tc.in); got != tc.want {
			t.Errorf("ClampDecisionAnswerLimit(%d) = %d, want %d", tc.in, got, tc.want)
		}
	}
}

// TestAcknowledgeIsTheDeliveryRecordAndBothOutcomesSetIt covers the ack: `applied` is the only input
// that resolves a row, a DROPPED answer is acked all the same and keeps its state, and a second ack -
// or an id that was never there - is one conflict, because neither redelivers.
func TestAcknowledgeIsTheDeliveryRecordAndBothOutcomesSetIt(t *testing.T) {
	applied := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "ship"}), serviceTestNow)
	dropped := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "ship"}), serviceTestNow)
	dropped.ID = "rd-2"
	third := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "ship"}), serviceTestNow)
	third.ID = "rd-3"
	store := &fakeRoomDecisionStore{rows: []repositories.RoomDecision{applied, dropped, third}}
	service := NewRoomDecisionService(store)
	ctx := context.Background()
	at := serviceTestNow.Add(time.Minute)

	written, err := service.Acknowledge(ctx, "owner", "rd-1", RoomDecisionOutcomeApplied, "", at)
	if err != nil {
		t.Fatalf("applied ack: %v", err)
	}
	if written.State != decisions.StateResolved {
		t.Errorf("state = %q, want resolved: applied is the only input that resolves", written.State)
	}
	if written.AckedAt == nil || !written.AckedAt.Equal(at) || written.ResolvedAt == nil || !written.ResolvedAt.Equal(at) {
		t.Errorf("ack = %+v, want acked_at and resolved_at at the caller's clock", written)
	}

	droppedRow, err := service.Acknowledge(ctx, "owner", "rd-2", RoomDecisionOutcomeDropped, "state-done", at)
	if err != nil {
		t.Fatalf("dropped ack: %v", err)
	}
	if droppedRow.State != decisions.StateAnswered || droppedRow.AckedAt == nil {
		t.Errorf("dropped row = %+v, want the state kept and the delivery recorded", droppedRow)
	}

	// The state, not the id: a repeat and an id that is not there answer the same conflict.
	var rejection *RoomDecisionAnswerRejection
	for _, tc := range []struct{ name, id string }{
		{"the applied ack again", "rd-1"},
		{"the dropped ack again", "rd-2"},
		{"an id that was never here", "rd-9"},
	} {
		if _, err := service.Acknowledge(ctx, "owner", tc.id, RoomDecisionOutcomeApplied, "", at); err == nil ||
			!asAnswerRejection(err, &rejection) || rejection.Code != CodeNotAwaitingAck {
			t.Errorf("%s err = %v, want %s", tc.name, err, CodeNotAwaitingAck)
		}
	}

	// The malformed reports, none of which writes.
	for _, tc := range []struct{ name, outcome, reason string }{
		{"an outcome that is neither", "maybe", ""},
		{"a drop with no reason", RoomDecisionOutcomeDropped, ""},
		{"a drop with a reason nobody defined", RoomDecisionOutcomeDropped, "because"},
	} {
		if _, err := service.Acknowledge(ctx, "owner", "rd-3", tc.outcome, tc.reason, at); err == nil ||
			!asAnswerRejection(err, &rejection) || rejection.Code != CodeInvalidAck {
			t.Errorf("%s err = %v, want %s", tc.name, err, CodeInvalidAck)
		}
	}
	if store.rows[2].AckedAt != nil {
		t.Errorf("a refused ack recorded a delivery anyway: %+v", store.rows[2])
	}
}

// TestSetStateRefusesAConcludedRowWithItsOwnState covers the state push: a transition out of answered
// lands, and a push onto a decision that is already over is refused with `state-<state>` - naming the
// state the row is in rather than the one the caller asked for - because the contract pins that body.
func TestSetStateRefusesAConcludedRowWithItsOwnState(t *testing.T) {
	row := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "ship"}), serviceTestNow)
	other := answeredAt(storedDecision(decisions.StatePending, map[string]string{"q1": "ship"}), serviceTestNow)
	other.ID = "rd-2"
	store := &fakeRoomDecisionStore{rows: []repositories.RoomDecision{row, other}}
	service := NewRoomDecisionService(store)
	ctx := context.Background()

	written, err := service.SetState(ctx, "owner", "rd-1", decisions.StateSuperseded, serviceTestNow.Add(time.Minute))
	if err != nil {
		t.Fatalf("SetState: %v", err)
	}
	if written.State != decisions.StateSuperseded {
		t.Errorf("state = %q, want superseded", written.State)
	}
	if written.ResolvedAt != nil {
		t.Errorf("resolved_at = %v, want none: a superseded ask was never resolved", written.ResolvedAt)
	}

	var rejection *RoomDecisionAnswerRejection
	_, err = service.SetState(ctx, "owner", "rd-1", decisions.StateResolved, serviceTestNow.Add(2*time.Minute))
	if err == nil || !asAnswerRejection(err, &rejection) {
		t.Fatalf("push onto a concluded row err = %v, want a refusal", err)
	}
	if rejection.Code != "state-superseded" || rejection.Message != "state-superseded" {
		t.Errorf("refusal = %+v, want the bare state-<state> token in both halves", rejection)
	}

	// A state the daemon may not write is a malformed push, not a transition it got wrong.
	if _, err := service.SetState(ctx, "owner", "rd-2", decisions.StateAnswered, serviceTestNow); err == nil ||
		!asAnswerRejection(err, &rejection) || rejection.Code != CodeUnknownState {
		t.Errorf("push of a cloud-only state err = %v, want %s", err, CodeUnknownState)
	}
	// An id that is not there at all is the unknown decision.
	if _, err := service.SetState(ctx, "owner", "rd-9", decisions.StateResolved, serviceTestNow); err == nil ||
		!asAnswerRejection(err, &rejection) || rejection.Code != CodeUnknownDecision {
		t.Errorf("push onto an unknown id err = %v, want %s", err, CodeUnknownDecision)
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

type fakeDecisionEvaluator struct {
	selections map[string]DecisionChoiceSelection
	err        error
}

func (f *fakeDecisionEvaluator) SelectDecisionChoices(ctx context.Context, model string, summary, detail string, qs []questions.HumanQuestion) (map[string]DecisionChoiceSelection, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.selections, nil
}

func TestRoomDecisionServiceEvaluatorAutoSelectAndPending(t *testing.T) {
	ctx := context.Background()
	qsJSON := json.RawMessage(`[
		{
			"id": "q1",
			"question": "Which db?",
			"options": [
				{"id": "opt_pg", "label": "PostgreSQL"},
				{"id": "opt_sqlite", "label": "SQLite"}
			]
		}
	]`)

	ask := RoomDecisionAsk{
		RigName:        "rig-1",
		QitemID:        "qitem-1",
		AuthorSeatKey:  "seat-1",
		Destination:    "human",
		Summary:        "Database choice",
		Detail:         "Need decision on primary db",
		Questions:      qsJSON,
		IdempotencyKey: "agenthub:decision:qitem-1",
	}

	t.Run("auto_selects_when_confidence_gte_threshold", func(t *testing.T) {
		store := &fakeRoomDecisionStore{}
		eval := &fakeDecisionEvaluator{
			selections: map[string]DecisionChoiceSelection{
				"q1": {SelectedOptionID: "opt_pg", Confidence: 0.85},
			},
		}

		service := NewRoomDecisionService(store).WithEvaluator(eval, "jev-1.13.0", 0.8)
		row, created, err := service.Create(ctx, "owner", "room-1", ask, serviceTestNow)
		if err != nil || !created {
			t.Fatalf("Create err = %v, created = %v", err, created)
		}

		// Since confidence 0.85 >= 0.8, q1 should be auto-answered, and row marked Answered
		if row.State != decisions.StateAnswered {
			t.Errorf("row.State = %s, want %s (auto-answered)", row.State, decisions.StateAnswered)
		}
		if row.Answers["q1"] != "opt_pg" {
			t.Errorf("row.Answers[q1] = %s, want opt_pg", row.Answers["q1"])
		}
	})

	t.Run("leaves_pending_when_confidence_lt_threshold", func(t *testing.T) {
		store := &fakeRoomDecisionStore{}
		eval := &fakeDecisionEvaluator{
			selections: map[string]DecisionChoiceSelection{
				"q1": {SelectedOptionID: "opt_pg", Confidence: 0.75},
			},
		}

		service := NewRoomDecisionService(store).WithEvaluator(eval, "jev-1.13.0", 0.8)
		row, created, err := service.Create(ctx, "owner", "room-1", ask, serviceTestNow)
		if err != nil || !created {
			t.Fatalf("Create err = %v, created = %v", err, created)
		}

		// Confidence 0.75 < 0.8 -> remains pending for human review
		if row.State != decisions.StatePending {
			t.Errorf("row.State = %s, want %s (pending for human)", row.State, decisions.StatePending)
		}
		if len(row.Answers) != 0 {
			t.Errorf("row.Answers = %+v, want empty", row.Answers)
		}
	})

	t.Run("writes_benchmark_log_file", func(t *testing.T) {
		tempDir := t.TempDir()
		logFile := filepath.Join(tempDir, "test_jev_decisions.log")
		SetJevDecisionLogPath(logFile)
		defer SetJevDecisionLogPath("")

		store := &fakeRoomDecisionStore{}
		eval := &fakeDecisionEvaluator{
			selections: map[string]DecisionChoiceSelection{
				"q1": {SelectedOptionID: "opt_pg", Confidence: 0.95},
			},
		}

		service := NewRoomDecisionService(store).WithEvaluator(eval, "jev-1.13.0", 0.8)
		_, _, err := service.Create(ctx, "owner", "room-1", ask, serviceTestNow)
		if err != nil {
			t.Fatalf("Create err = %v", err)
		}

		data, err := os.ReadFile(logFile)
		if err != nil {
			t.Fatalf("failed to read log file: %v", err)
		}
		if !strings.Contains(string(data), `"model":"jev-1.13.0"`) || !strings.Contains(string(data), `"confidence_threshold":0.8`) {
			t.Errorf("log contents do not contain expected metrics: %s", string(data))
		}
	})
}
