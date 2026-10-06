package orm

import (
	"context"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

const seatFeedbackReturning = `"id"::text, "user_id", "room", "seat", "session", "layer", "text", ` +
	`"machine_id", "created_at"`

// ORMSeatFeedbackRepository is the ORM SeatFeedbackRepository over seat_feedback.
type ORMSeatFeedbackRepository struct {
	*baserepo.ORMRepository[seatdb.SeatFeedbackORM]
}

var _ domainrepo.SeatFeedbackRepository = (*ORMSeatFeedbackRepository)(nil)

// NewORMSeatFeedbackRepository builds the repository over seat_feedback.
func NewORMSeatFeedbackRepository(sessions *database.SessionManager) (*ORMSeatFeedbackRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.SeatFeedbackORM]("seat_feedback", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMSeatFeedbackRepository{ORMRepository: base}, nil
}

// Create stores one report and returns the stored row. The id comes from the column default
// (uuid_generate_v4()); created_at is the caller's clock, not now() on the server, so the
// answer the route returns and the row it stored carry the same instant.
func (r *ORMSeatFeedbackRepository) Create(ctx context.Context, report domainrepo.SeatFeedback) (*domainrepo.SeatFeedback, error) {
	row := &seatdb.SeatFeedbackORM{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx,
			`INSERT INTO "seat_feedback" ("user_id", "room", "seat", "session", "layer", "text", "machine_id", "created_at") `+
				`VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING `+seatFeedbackReturning,
			report.UserID, report.Room, report.Seat, report.Session, report.Layer,
			report.Text, report.MachineID, report.CreatedAt,
		).Scan(&row.ID, &row.UserID, &row.Room, &row.Seat, &row.Session, &row.Layer,
			&row.Text, &row.MachineID, &row.CreatedAt)
	})
	if err != nil {
		return nil, err
	}
	out := seatFeedbackToDomain(row)
	return &out, nil
}

// List returns the user's reports newest first, the order the route groups without re-sorting.
// The id is the tiebreak so two reports written in the same instant still come back in a stable
// order.
func (r *ORMSeatFeedbackRepository) List(ctx context.Context, userID string) ([]domainrepo.SeatFeedback, error) {
	rows := []*seatdb.SeatFeedbackORM{}
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		cursor, err := s.QueryContext(ctx,
			`SELECT `+seatFeedbackReturning+` FROM "seat_feedback" WHERE "user_id" = $1 `+
				`ORDER BY "created_at" DESC, "id" DESC`,
			userID,
		)
		if err != nil {
			return err
		}
		defer func() { _ = cursor.Close() }()
		for cursor.Next() {
			row := &seatdb.SeatFeedbackORM{}
			if err := cursor.Scan(&row.ID, &row.UserID, &row.Room, &row.Seat, &row.Session,
				&row.Layer, &row.Text, &row.MachineID, &row.CreatedAt); err != nil {
				return err
			}
			rows = append(rows, row)
		}
		return cursor.Err()
	})
	if err != nil {
		return nil, err
	}
	out := make([]domainrepo.SeatFeedback, 0, len(rows))
	for _, row := range rows {
		out = append(out, seatFeedbackToDomain(row))
	}
	return out, nil
}

func seatFeedbackToDomain(row *seatdb.SeatFeedbackORM) domainrepo.SeatFeedback {
	return domainrepo.SeatFeedback{
		ID:        row.ID,
		UserID:    row.UserID,
		Room:      row.Room,
		Seat:      row.Seat,
		Session:   row.Session,
		Layer:     row.Layer,
		Text:      row.Text,
		MachineID: row.MachineID,
		CreatedAt: row.CreatedAt,
	}
}
