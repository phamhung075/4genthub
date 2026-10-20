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
const roomDecisionReturning = `"id"::text, "user_id", "room_id"::text, "room_name", "qitem_id", ` +
	`"author_seat_key", "destination", "summary", "detail", "questions", "answers", "state", ` +
	`"idempotency_key", "created_at", "answered_at", "resolved_at", "acked_at"`

// roomDecisionRoomSlug is the pull's ONE extra column: the slug of the room a row belongs to. It is a
// scalar subquery rather than a join so the shared list above stays unqualified and there is no second
// column list to keep in step with the DDL. A pull reads a page of rows that each name one room, so the
// subquery costs one primary-key lookup per row.
const roomDecisionRoomSlug = `(SELECT "slug" FROM "rooms" WHERE "rooms"."id" = "room_decisions"."room_id")`

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
// ON CONFLICT DO NOTHING on the EPISODE is what makes the mirror durable-first: the tuple is
// (user_id, qitem_id), which is the SAME tuple the loser path reads back, so a redrive after a lost
// answer collapses onto the row it already made rather than author a second decision the human would
// be asked twice. The key is NOT the dedupe, because a key alone is global: one routed item asked
// about by two tenants is two asks, and a globally unique key would make the second tenant's insert
// no-op and then read that key back inside its own scope, where the row does not exist. Losing the
// statement means the other attempt stored the row, so the row is read back and returned - a create
// whose intent is "make sure this ask is mirrored" answers with the row either way, and the second
// return value is that distinction: true when THIS call stored the row, false when an earlier attempt
// already had - the wire's `created`, which is how the daemon learns its redrive did not author a
// second ask.
func (r *ORMRoomDecisionRepository) Create(ctx context.Context, decision domainrepo.RoomDecision) (*domainrepo.RoomDecision, bool, error) {
	questionsJSON, err := encodeRoomDecisionQuestions(decision.Questions)
	if err != nil {
		return nil, false, err
	}
	answersJSON, err := encodeRoomDecisionAnswers(decision.Answers)
	if err != nil {
		return nil, false, err
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
			`INSERT INTO "room_decisions" ("id", "user_id", "room_id", "room_name", "qitem_id", "author_seat_key", `+
				`"destination", "summary", "detail", "questions", "answers", "state", "idempotency_key", `+
				`"created_at", "answered_at", "resolved_at", "acked_at") `+
				`VALUES ($1::uuid, $2, $3::uuid, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12, $13, $14, `+
				`NULL, NULL, NULL) ON CONFLICT ("user_id", "qitem_id") DO NOTHING RETURNING `+roomDecisionReturning,
			id, decision.UserID, decision.RoomID, decision.RoomName, decision.QitemID, decision.AuthorSeatKey,
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
		return nil, false, err
	}
	if won {
		created, err := roomDecisionToDomain(stored)
		return created, true, err
	}
	existing, err := r.getByUserQitem(ctx, decision.UserID, decision.QitemID)
	return existing, false, err
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

// GetByID returns one decision of this tenant without naming a room. The answer leg arrives with the
// decision id the pull handed out and nothing else - a daemon does not know which rooms its own asks
// were filed in, because the cloud resolved that from a slug at ask time. A decision id that is not
// a UUID names no row, so it is a miss rather than an error, exactly as in Get.
func (r *ORMRoomDecisionRepository) GetByID(ctx context.Context, userID, id string) (*domainrepo.RoomDecision, error) {
	idParam, err := database.UnifiedUUIDBindParam(id, database.DialectPostgres)
	if err != nil {
		return nil, nil
	}
	var row *seatdb.RoomDecisionORM
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		got, err := scanRoomDecision(s.QueryRowContext(ctx,
			`SELECT `+roomDecisionReturning+` FROM "room_decisions" `+
				`WHERE "user_id" = $1 AND "id" = $2`,
			userID, idParam))
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

// ListAnswers returns this tenant's answered-but-unacknowledged decisions, oldest first,
// starting after the cursor, each carrying the SLUG of the room it belongs to. It is the pull the
// daemon drives.
//
// THE ROW COMPARISON `("answered_at", "id") > ($3, $4)` IS THE CURSOR: answered_at orders and the id
// breaks ties, so two answers stored in the same instant are handed over in a stable order and a
// resumed pull neither repeats nor skips one - a cursor that named only the instant would do one of
// those. A nil cursor is the first page, and the casts are there because a nil bind carries no type
// of its own. answered_at is never NULL for a row this filter returns: the answer contract sets it in
// the same statement that moves a row to `answered`.
//
// acked_at IS NULL is the delivery half of the filter and `state = 'answered'` the work half: a row
// the daemon has acked is never handed out again, and a pending ask is still being answered in the
// panel. The room is in the filter because the ack is destructive - a daemon that pulled another room's
// answers could not apply them (its local queue has no such row) and its ack would close a decision
// nobody applied.
func (r *ORMRoomDecisionRepository) ListAnswers(ctx context.Context, userID string, after *domainrepo.AnswerCursor, limit int) ([]domainrepo.AnswerDelivery, error) {
	var afterAt, afterID any
	if after != nil && after.ID != "" {
		idParam, err := database.UnifiedUUIDBindParam(after.ID, database.DialectPostgres)
		if err != nil {
			return nil, nil
		}
		afterAt, afterID = after.AnsweredAt.UTC(), idParam
	}
	type deliveryRow struct {
		orm  *seatdb.RoomDecisionORM
		slug string
	}
	rows := []deliveryRow{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		cursor, err := s.QueryContext(ctx,
			`SELECT `+roomDecisionReturning+`, `+roomDecisionRoomSlug+` FROM "room_decisions" `+
				`WHERE "user_id" = $1 AND "state" = 'answered' AND "acked_at" IS NULL `+
				`AND ($2::timestamptz IS NULL OR ("answered_at", "id") > ($2::timestamptz, $3::uuid)) `+
				`ORDER BY "answered_at" ASC, "id" ASC LIMIT $4`,
			userID, afterAt, afterID, limit)
		if err != nil {
			return err
		}
		defer func() { _ = cursor.Close() }()
		for cursor.Next() {
			row, slug, err := scanRoomDecisionDelivery(cursor)
			if err != nil {
				return err
			}
			rows = append(rows, deliveryRow{orm: row, slug: slug})
		}
		return cursor.Err()
	})
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.AnswerDelivery, 0, len(rows))
	for _, row := range rows {
		decision, err := roomDecisionToDomain(row.orm)
		if err != nil {
			return nil, err
		}
		out = append(out, domainrepo.AnswerDelivery{RoomDecision: *decision, RoomSlug: row.slug})
	}
	return out, nil
}

// Acknowledge records what the daemon did with one answer and stops the pull handing it out again.
//
// THE WRITE IS GUARDED ON THE ROW BEING `answered` AND UNACKED, which is what makes an ack idempotent
// and what keeps it from re-opening a closed row: a second ack, an ack of a row the daemon already
// pushed as superseded, and an ack of an ask that is still being answered all match nothing. `applied`
// is the only input that also closes the row as resolved - the cloud records the daemon's report and
// never concludes by itself - while BOTH outcomes set acked_at, so a dropped answer is delivered once
// and never retried.
//
// When nothing matches, the row is read back and returned as it stands, so the caller can name what it
// found, and the bool is false: this call did not ack it. A row that is not there at all comes back
// nil with false.
func (r *ORMRoomDecisionRepository) Acknowledge(ctx context.Context, userID, id string, applied bool, at time.Time) (*domainrepo.RoomDecision, bool, error) {
	idParam, err := database.UnifiedUUIDBindParam(id, database.DialectPostgres)
	if err != nil {
		return nil, false, nil
	}
	var stored *seatdb.RoomDecisionORM
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := scanRoomDecision(s.QueryRowContext(ctx,
			`UPDATE "room_decisions" SET "acked_at" = $3::timestamptz, `+
				`"state" = CASE WHEN $4::boolean THEN 'resolved' ELSE "state" END, `+
				`"resolved_at" = CASE WHEN $4::boolean THEN $3::timestamptz ELSE "resolved_at" END `+
				`WHERE "user_id" = $1 AND "id" = $2 AND "state" = 'answered' AND "acked_at" IS NULL `+
				`RETURNING `+roomDecisionReturning,
			userID, idParam, at.UTC(), applied))
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
		return nil, false, err
	}
	if stored != nil {
		decision, err := roomDecisionToDomain(stored)
		return decision, err == nil, err
	}
	existing, err := r.GetByID(ctx, userID, id)
	return existing, false, err
}

// SetState writes the daemon's own verdict about one mirrored ask that never became an apply.
//
// It is guarded on the row being OPEN (`pending` or `answered`): a state push is a report about a
// decision, so a row the daemon has already concluded is left exactly as it stands rather than being
// told a second story about itself - and that is also what makes a repeated push a no-op. resolved_at
// is set only for `resolved`: a superseded ask was never resolved, and an instant there would be a
// claim nobody made.
func (r *ORMRoomDecisionRepository) SetState(ctx context.Context, userID, id string, state decisions.State, at time.Time) (*domainrepo.RoomDecision, error) {
	idParam, err := database.UnifiedUUIDBindParam(id, database.DialectPostgres)
	if err != nil {
		return nil, nil
	}
	var stored *seatdb.RoomDecisionORM
	err = r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		row, err := scanRoomDecision(s.QueryRowContext(ctx,
			`UPDATE "room_decisions" `+
				`SET "state" = $3, `+
				`"resolved_at" = CASE WHEN $3 = 'resolved' THEN $4::timestamptz ELSE "resolved_at" END `+
				`WHERE "user_id" = $1 AND "id" = $2 AND "state" IN ('pending', 'answered') `+
				`RETURNING `+roomDecisionReturning,
			userID, idParam, string(state), at.UTC()))
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
	return r.GetByID(ctx, userID, id)
}

// getByUserQitem is the loser path of a redrive: the EPISODE the conflict was decided on, read in the
// same scope the insert conflicted in. Reading by idempotency_key instead would be a different scope
// than the conflict target - the misreading that let one tenant's ask vanish - so the two must name
// the same tuple.
func (r *ORMRoomDecisionRepository) getByUserQitem(ctx context.Context, userID, qitemID string) (*domainrepo.RoomDecision, error) {
	var row *seatdb.RoomDecisionORM
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		got, err := scanRoomDecision(s.QueryRowContext(ctx,
			`SELECT `+roomDecisionReturning+` FROM "room_decisions" `+
				`WHERE "user_id" = $1 AND "qitem_id" = $2`,
			userID, qitemID))
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

// scanRoomDecisionInto reads one row's decision columns into out, plus any extra destinations the
// caller's statement appends - the pull's room slug is the one such column today. There is ONE column
// list, here, because the DDL order is what makes it right and two lists would drift.
func scanRoomDecisionInto(row interface{ Scan(...any) error }, out *seatdb.RoomDecisionORM, extra ...any) error {
	var questionsRaw, answersRaw []byte
	dest := []any{&out.ID, &out.UserID, &out.RoomID, &out.RoomName, &out.QitemID, &out.AuthorSeatKey,
		&out.Destination, &out.Summary, &out.Detail, &questionsRaw, &answersRaw, &out.State,
		&out.IdempotencyKey, &out.CreatedAt, &out.AnsweredAt, &out.ResolvedAt, &out.AckedAt}
	if err := row.Scan(append(dest, extra...)...); err != nil {
		return err
	}
	out.Questions = json.RawMessage(questionsRaw)
	out.Answers = json.RawMessage(answersRaw)
	return nil
}

// scanRoomDecision reads one row, turning the two JSONB columns into raw JSON and leaving the
// nullable text and instants as pointers.
func scanRoomDecision(row interface{ Scan(...any) error }) (*seatdb.RoomDecisionORM, error) {
	out := &seatdb.RoomDecisionORM{}
	if err := scanRoomDecisionInto(row, out); err != nil {
		return nil, err
	}
	return out, nil
}

// scanRoomDecisionDelivery reads one pull row: the decision's own columns and, last, the slug of the
// room the row belongs to.
func scanRoomDecisionDelivery(row interface{ Scan(...any) error }) (*seatdb.RoomDecisionORM, string, error) {
	out := &seatdb.RoomDecisionORM{}
	var slug string
	if err := scanRoomDecisionInto(row, out, &slug); err != nil {
		return nil, "", err
	}
	return out, slug, nil
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
		RoomName:        row.RoomName,
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
		AckedAt:        utcPtr(row.AckedAt),
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
