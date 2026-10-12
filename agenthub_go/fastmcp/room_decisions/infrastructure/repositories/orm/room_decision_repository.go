// Package orm is the room-decision store over room_decisions, on the base repository the seat
// tables use. Every statement is tenant-scoped by the user id it is given, and every statement that
// names a decision names its room as well, so a decision id from one room can never be answered
// through another.
package orm

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"time"

	"agenthub/fastmcp/room_decisions/domain/decisions"
	"agenthub/fastmcp/room_decisions/domain/questions"
	domainrepo "agenthub/fastmcp/room_decisions/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// roomDecisionReturning is the column list every read and write here shares, in DDL order, with the
// UUID columns cast so they arrive as text.
const roomDecisionReturning = `"id"::text, "user_id", "room_id"::text, "rig_name", "qitem_id", ` +
	`"author_seat_key", "destination", "summary", "detail", "questions", "answers", "state", ` +
	`"idempotency_key", "created_at", "answered_at", "resolved_at"`

// ORMRoomDecisionRepository is the ORM RoomDecisionRepository over room_decisions.
type ORMRoomDecisionRepository struct {
	*baserepo.ORMRepository[seatdb.RoomDecisionORM]
}

var _ domainrepo.RoomDecisionRepository = (*ORMRoomDecisionRepository)(nil)

// NewORMRoomDecisionRepository builds the repository over room_decisions.
func NewORMRoomDecisionRepository(sessions *database.SessionManager) (*ORMRoomDecisionRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.RoomDecisionORM]("room_decisions", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMRoomDecisionRepository{ORMRepository: base}, nil
}

// Create stores one mirrored ask and returns the stored row.
//
// The id is generated HERE rather than left to the column default, the choice the base repository
// makes for taskdb.DefaultUUIDv4: the table's runtime DDL has no DEFAULT on id, because createAll
// (the path a fresh database takes) does not create the uuid-ossp extension. created_at is the
// caller's clock, so the row and the answer carrying it agree.
//
// ON CONFLICT DO NOTHING on the ask's own key is what makes the mirror durable-first: the key is the
// daemon's decisionId, so a redrive after a lost answer must collapse onto the row it already made
// rather than author a second decision the human would be asked twice. Losing that statement means
// the other attempt stored the row, so the row is read back and returned - a create whose intent is
// "make sure this ask is mirrored" answers with the row either way.
func (r *ORMRoomDecisionRepository) Create(ctx context.Context, decision domainrepo.RoomDecision) (*domainrepo.RoomDecision, error) {
	questionsJSON, err := encodeRoomDecisionQuestions(decision.Questions)
	if err != nil {
		return nil, err
	}
	answersJSON, err := encodeRoomDecisionAnswers(decision.Answers)
	if err != nil {
		return nil, err
	}
	id := decision.ID
	if id == "" {
		id = value_objects.NewUUIDv4()
	}

	var (
		stored *seatdb.RoomDecisionORM
		won    bool
	)
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := scanRoomDecision(s.QueryRowContext(ctx,
			`INSERT INTO "room_decisions" ("id", "user_id", "room_id", "rig_name", "qitem_id", "author_seat_key", `+
				`"destination", "summary", "detail", "questions", "answers", "state", "idempotency_key", `+
				`"created_at", "answered_at", "resolved_at") `+
				`VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12, $13, $14, `+
				`NULL, NULL) ON CONFLICT ("idempotency_key") DO NOTHING RETURNING `+roomDecisionReturning,
			id, decision.UserID, decision.RoomID, decision.RigName, decision.QitemID, decision.AuthorSeatKey,
			decision.Destination, nullableText(decision.Summary), nullableText(decision.Detail),
			questionsJSON, answersJSON, string(decision.State), decision.IdempotencyKey, decision.CreatedAt.UTC()))
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		stored, won = row, true
		return nil
	})
	if err != nil {
		return nil, err
	}
	if won {
		return roomDecisionToDomain(stored)
	}
	return r.getByIdempotencyKey(ctx, decision.UserID, decision.IdempotencyKey)
}

// Get returns one decision of this tenant and room, or nil when there is none. A decision id that
// is not a UUID cannot name a row, so it is a miss rather than an error: the route answers 404 for
// it, exactly as it does for a UUID that is simply not there.
func (r *ORMRoomDecisionRepository) Get(ctx context.Context, userID, roomID, id string) (*domainrepo.RoomDecision, error) {
	idParam, roomParam, ok := roomDecisionKeys(id, roomID)
	if !ok {
		return nil, nil
	}
	var row *seatdb.RoomDecisionORM
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		got, err := scanRoomDecision(s.QueryRowContext(ctx,
			`SELECT `+roomDecisionReturning+` FROM "room_decisions" `+
				`WHERE "user_id" = $1 AND "room_id" = $2 AND "id" = $3`,
			userID, roomParam, idParam))
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		row = got
		return nil
	})
	if err != nil || row == nil {
		return nil, err
	}
	return roomDecisionToDomain(row)
}

// ListByRoom returns this tenant's decisions for one room, newest first. The id is the tiebreak so
// two rows written in the same instant still come back in a stable order.
//
// The scope is the CALLER'S user id and not the room owner's: a room shared with a team is visible
// to its members, and a decision is addressed to the room's human, so a viewer's read is empty
// rather than another tenant's row.
func (r *ORMRoomDecisionRepository) ListByRoom(ctx context.Context, userID, roomID string) ([]domainrepo.RoomDecision, error) {
	_, roomParam, ok := roomDecisionKeys("", roomID)
	if !ok {
		return nil, nil
	}
	rows := []*seatdb.RoomDecisionORM{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		cursor, err := s.QueryContext(ctx,
			`SELECT `+roomDecisionReturning+` FROM "room_decisions" `+
				`WHERE "user_id" = $1 AND "room_id" = $2 ORDER BY "created_at" DESC, "id" DESC`,
			userID, roomParam)
		if err != nil {
			return err
		}
		defer func() { _ = cursor.Close() }()
		for cursor.Next() {
			row, err := scanRoomDecision(cursor)
			if err != nil {
				return err
			}
			rows = append(rows, row)
		}
		return cursor.Err()
	})
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.RoomDecision, 0, len(rows))
	for _, row := range rows {
		decision, err := roomDecisionToDomain(row)
		if err != nil {
			return nil, err
		}
		out = append(out, *decision)
	}
	return out, nil
}

// RecordAnswer writes one applied click: the answers map as a whole, the state, and the answered-at
// instant when the click completed the ask.
//
// THE WRITE IS GUARDED ON THE ROW STILL BEING PENDING, so two clicks that raced cannot both land:
// the second one matches nothing and the row is returned unchanged. That is also what a repeated
// click does - it changes no column and inserts nothing - because the answers map is the row's
// whole answer state rather than one row per click.
func (r *ORMRoomDecisionRepository) RecordAnswer(ctx context.Context, userID, roomID, id string, answers map[string]string, state decisions.State, answeredAt *time.Time) (*domainrepo.RoomDecision, error) {
	idParam, roomParam, ok := roomDecisionKeys(id, roomID)
	if !ok {
		return nil, nil
	}
	answersJSON, err := encodeRoomDecisionAnswers(answers)
	if err != nil {
		return nil, err
	}
	var stored *seatdb.RoomDecisionORM
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := scanRoomDecision(s.QueryRowContext(ctx,
			`UPDATE "room_decisions" SET "answers" = $1::jsonb, "state" = $2, "answered_at" = $3 `+
				`WHERE "user_id" = $4 AND "room_id" = $5 AND "id" = $6 AND "state" = 'pending' `+
				`RETURNING `+roomDecisionReturning,
			answersJSON, string(state), answeredAt, userID, roomParam, idParam))
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		stored = row
		return nil
	})
	if err != nil {
		return nil, err
	}
	if stored != nil {
		return roomDecisionToDomain(stored)
	}
	// The guarded write matched nothing: a click landed between this call's read and its write, or
	// the row is gone. The row as it now stands is the answer either way, so it is read back rather
	// than reported as a failure - the click that won is the one the caller will see.
	return r.Get(ctx, userID, roomID, id)
}

// getByIdempotencyKey is the redrive lookup: the ask's own key, which is unique across the table.
func (r *ORMRoomDecisionRepository) getByIdempotencyKey(ctx context.Context, userID, key string) (*domainrepo.RoomDecision, error) {
	var row *seatdb.RoomDecisionORM
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		got, err := scanRoomDecision(s.QueryRowContext(ctx,
			`SELECT `+roomDecisionReturning+` FROM "room_decisions" `+
				`WHERE "user_id" = $1 AND "idempotency_key" = $2`,
			userID, key))
		if errors.Is(err, sql.ErrNoRows) {
			return nil
		}
		if err != nil {
			return err
		}
		row = got
		return nil
	})
	if err != nil || row == nil {
		return nil, err
	}
	return roomDecisionToDomain(row)
}

// roomDecisionKeys turns an id and a room id into bind parameters. A value that is not a UUID names
// no row, and false says so; the empty id is allowed for the calls that only need the room.
func roomDecisionKeys(id, roomID string) (idParam, roomParam any, ok bool) {
	roomParam, err := database.UnifiedUUIDBindParam(roomID, database.DialectPostgres)
	if err != nil {
		return nil, nil, false
	}
	if id == "" {
		return nil, roomParam, true
	}
	idParam, err = database.UnifiedUUIDBindParam(id, database.DialectPostgres)
	if err != nil {
		return nil, nil, false
	}
	return idParam, roomParam, true
}

// scanRoomDecision reads one row, turning the two JSONB columns into raw JSON and leaving the
// nullable text and instants as pointers.
func scanRoomDecision(row interface{ Scan(...any) error }) (*seatdb.RoomDecisionORM, error) {
	out := &seatdb.RoomDecisionORM{}
	var questionsRaw, answersRaw []byte
	if err := row.Scan(&out.ID, &out.UserID, &out.RoomID, &out.RigName, &out.QitemID, &out.AuthorSeatKey,
		&out.Destination, &out.Summary, &out.Detail, &questionsRaw, &answersRaw, &out.State,
		&out.IdempotencyKey, &out.CreatedAt, &out.AnsweredAt, &out.ResolvedAt); err != nil {
		return nil, err
	}
	out.Questions = json.RawMessage(questionsRaw)
	out.Answers = json.RawMessage(answersRaw)
	return out, nil
}

// roomDecisionToDomain decodes a row into the entity. A state outside the vocabulary is an error
// rather than a guess: the DDL CHECK should make it unreachable, and a row nobody can place is not
// something to hand a caller as a decision.
func roomDecisionToDomain(row *seatdb.RoomDecisionORM) (*domainrepo.RoomDecision, error) {
	state, err := decisions.ParseState(row.State)
	if err != nil {
		return nil, err
	}
	var parsed []questions.HumanQuestion
	if len(row.Questions) > 0 {
		if err := json.Unmarshal(row.Questions, &parsed); err != nil {
			return nil, err
		}
	}
	answers := map[string]string{}
	if len(row.Answers) > 0 {
		if err := json.Unmarshal(row.Answers, &answers); err != nil {
			return nil, err
		}
	}
	out := &domainrepo.RoomDecision{
		ID:             row.ID,
		UserID:         row.UserID,
		RoomID:         row.RoomID,
		RigName:        row.RigName,
		QitemID:        row.QitemID,
		AuthorSeatKey:  row.AuthorSeatKey,
		Destination:    row.Destination,
		Questions:      parsed,
		Answers:        answers,
		State:          state,
		IdempotencyKey: row.IdempotencyKey,
		CreatedAt:      row.CreatedAt.UTC(),
		AnsweredAt:     utcPtr(row.AnsweredAt),
		ResolvedAt:     utcPtr(row.ResolvedAt),
	}
	if row.Summary != nil {
		out.Summary = *row.Summary
	}
	if row.Detail != nil {
		out.Detail = *row.Detail
	}
	return out, nil
}

// encodeRoomDecisionQuestions stores the validated question list as the JSONB the panel reads.
func encodeRoomDecisionQuestions(list []questions.HumanQuestion) (string, error) {
	if list == nil {
		list = []questions.HumanQuestion{}
	}
	raw, err := json.Marshal(list)
	if err != nil {
		return "", err
	}
	return string(raw), nil
}

// encodeRoomDecisionAnswers stores the answers map, `questionId -> optionId`, as JSONB. A nil map
// is `{}` rather than `null`, which is both the column's default and what the panel reads.
func encodeRoomDecisionAnswers(answers map[string]string) (string, error) {
	if answers == nil {
		answers = map[string]string{}
	}
	raw, err := json.Marshal(answers)
	if err != nil {
		return "", err
	}
	return string(raw), nil
}

// nullableText keeps "no summary" and "no detail" as NULL rather than as an empty string: the
// column is nullable for exactly that reason.
func nullableText(value string) any {
	if value == "" {
		return nil
	}
	return value
}

// utcPtr normalises a nullable instant to UTC, so a row read back compares equal to a clock.
func utcPtr(at *time.Time) *time.Time {
	if at == nil {
		return nil
	}
	utc := at.UTC()
	return &utc
}
