package orm

import (
	"context"
	"encoding/json"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ORMMachineStatusRepository is the ORM MachineStatusRepository over machines and seat_status.
type ORMMachineStatusRepository struct {
	*baserepo.ORMRepository[seatdb.MachineORM]
}

var _ domainrepo.MachineStatusRepository = (*ORMMachineStatusRepository)(nil)

// NewORMMachineStatusRepository builds the repository over machines and seat_status.
func NewORMMachineStatusRepository(sessions *database.SessionManager) (*ORMMachineStatusRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.MachineORM]("machines", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMMachineStatusRepository{ORMRepository: base}, nil
}

// ReplaceSnapshot upserts the machine and replaces its seat statuses in one transaction.
func (r *ORMMachineStatusRepository) ReplaceSnapshot(ctx context.Context, userID string, machine domainrepo.Machine) error {
	agents, err := json.Marshal(machine.Agents)
	if err != nil {
		return err
	}
	return r.Transaction(ctx, func(ctx context.Context) error {
		return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
			if _, err := s.ExecContext(ctx,
				`INSERT INTO "machines" ("user_id", "machine_id", "last_seen", "agents") VALUES ($1, $2, $3, $4::jsonb) `+
					`ON CONFLICT ("user_id", "machine_id") DO UPDATE SET "last_seen" = EXCLUDED."last_seen", "agents" = EXCLUDED."agents"`,
				userID, machine.MachineID, machine.LastSeen, string(agents),
			); err != nil {
				return err
			}
			if _, err := s.ExecContext(ctx,
				`DELETE FROM "seat_status" WHERE "user_id" = $1 AND "machine_id" = $2`,
				userID, machine.MachineID,
			); err != nil {
				return err
			}
			for _, seat := range machine.Seats {
				if _, err := s.ExecContext(ctx,
					`INSERT INTO "seat_status" ("user_id", "machine_id", "room", "seat", "state", "runtime", "running_hash", "detail", "redacted", "reported_at") `+
						`VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
					userID, machine.MachineID, seat.Room, seat.Seat, seat.State, seat.Runtime,
					seat.RunningHash, seat.Detail, seat.Redacted, seat.ReportedAt,
				); err != nil {
					return err
				}
			}
			return nil
		})
	})
}

// List returns the user's machines with their seat statuses and agents.
func (r *ORMMachineStatusRepository) List(ctx context.Context, userID string) ([]domainrepo.Machine, error) {
	var machines []domainrepo.Machine
	err := r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		rows, err := s.QueryContext(ctx,
			`SELECT "machine_id", "last_seen", "agents" FROM "machines" WHERE "user_id" = $1 ORDER BY "machine_id"`, userID)
		if err != nil {
			return err
		}
		defer rows.Close()
		for rows.Next() {
			var (
				m      domainrepo.Machine
				agents []byte
			)
			if err := rows.Scan(&m.MachineID, &m.LastSeen, &agents); err != nil {
				return err
			}
			if err := json.Unmarshal(agents, &m.Agents); err != nil {
				return err
			}
			machines = append(machines, m)
		}
		if err := rows.Err(); err != nil {
			return err
		}

		seatRows, err := s.QueryContext(ctx,
			`SELECT "machine_id", "room", "seat", "state", "runtime", "running_hash", "detail", "redacted", "reported_at" `+
				`FROM "seat_status" WHERE "user_id" = $1 ORDER BY "room", "seat"`, userID)
		if err != nil {
			return err
		}
		defer seatRows.Close()
		index := make(map[string]int, len(machines))
		for i := range machines {
			index[machines[i].MachineID] = i
		}
		for seatRows.Next() {
			var (
				machineID string
				seat      domainrepo.SeatStatus
			)
			if err := seatRows.Scan(&machineID, &seat.Room, &seat.Seat, &seat.State, &seat.Runtime,
				&seat.RunningHash, &seat.Detail, &seat.Redacted, &seat.ReportedAt); err != nil {
				return err
			}
			if i, ok := index[machineID]; ok {
				machines[i].Seats = append(machines[i].Seats, seat)
			}
		}
		return seatRows.Err()
	})
	return machines, err
}

// DeleteSeatStatusForRoom removes the room's reported seat statuses for the user.
func (r *ORMMachineStatusRepository) DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM "seat_status" WHERE "user_id" = $1 AND "room" = $2`, userID, roomSlug)
		return err
	})
}
