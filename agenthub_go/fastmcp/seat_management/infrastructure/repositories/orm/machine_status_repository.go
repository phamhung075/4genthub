package orm

import (
	"context"
	"encoding/json"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	seatdb "agenthub/fastmcp/seat_management/infrastructure/database"
	"agenthub/fastmcp/task_management/infrastructure/database"
	baserepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// ORMMachineStatusRepository is the ORM MachineStatusRepository over machines, seat_status and
// machine_edges.
type ORMMachineStatusRepository struct {
	*baserepo.ORMRepository[seatdb.MachineORM]
}

var _ domainrepo.MachineStatusRepository = (*ORMMachineStatusRepository)(nil)

// NewORMMachineStatusRepository builds the repository over machines, seat_status and machine_edges.
func NewORMMachineStatusRepository(sessions *database.SessionManager) (*ORMMachineStatusRepository, error) {
	base, err := baserepo.NewORMRepository[seatdb.MachineORM]("machines", sessions)
	if err != nil {
		return nil, err
	}
	return &ORMMachineStatusRepository{ORMRepository: base}, nil
}

// ReplaceSnapshot upserts the machine and replaces its seat statuses, agent snapshot and edge set
// in one transaction.
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
			// The edge set is replaced wholesale too, like the seats and the agent snapshot: a
			// report that carries no edges leaves the machine with none, which is what the
			// seats-and-agents precedent does and what keeps a stale link from outliving the rig
			// it describes.
			if _, err := s.ExecContext(ctx,
				`DELETE FROM "machine_edges" WHERE "user_id" = $1 AND "machine_id" = $2`,
				userID, machine.MachineID,
			); err != nil {
				return err
			}
			for _, edge := range machine.Edges {
				if _, err := s.ExecContext(ctx,
					`INSERT INTO "machine_edges" ("user_id", "machine_id", "room", "from_seat", "to_seat", "kind") `+
						`VALUES ($1, $2, $3, $4, $5, $6)`,
					userID, machine.MachineID, edge.Room, edge.From, edge.To, edge.Kind,
				); err != nil {
					return err
				}
			}
			return nil
		})
	})
}

// List returns the user's machines with their seat statuses, agents and reported edges.
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
			`SELECT ss."machine_id", ss."room", ss."seat", ss."state", ss."runtime", ss."running_hash", COALESCE(latest."hash", ''), ss."detail", ss."redacted", ss."reported_at" `+
				`FROM "seat_status" AS ss `+
				`LEFT JOIN "rooms" AS r ON r."user_id" = ss."user_id" AND r."slug" = ss."room" `+
				`LEFT JOIN "seats" AS s ON s."user_id" = ss."user_id" AND s."room_id" = r."id" AND s."seat_key" = ss."seat" `+
				`LEFT JOIN LATERAL (SELECT rs."hash" FROM "resolved_seats" AS rs `+
				`WHERE rs."user_id" = ss."user_id" AND rs."seat_id" = s."id" `+
				`ORDER BY rs."created_at" DESC, rs."id" DESC LIMIT 1) AS latest ON TRUE `+
				`WHERE ss."user_id" = $1 ORDER BY ss."room", ss."seat"`, userID)
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
				&seat.RunningHash, &seat.ExpectedHash, &seat.Detail, &seat.Redacted, &seat.ReportedAt); err != nil {
				return err
			}
			if i, ok := index[machineID]; ok {
				machines[i].Seats = append(machines[i].Seats, seat)
			}
		}
		if err := seatRows.Err(); err != nil {
			return err
		}

		edgeRows, err := s.QueryContext(ctx,
			`SELECT "machine_id", "room", "from_seat", "to_seat", "kind" FROM "machine_edges" WHERE "user_id" = $1 `+
				`ORDER BY "room", "from_seat", "to_seat", "kind"`, userID)
		if err != nil {
			return err
		}
		defer edgeRows.Close()
		for edgeRows.Next() {
			var (
				machineID string
				edge      domainrepo.MachineEdge
			)
			if err := edgeRows.Scan(&machineID, &edge.Room, &edge.From, &edge.To, &edge.Kind); err != nil {
				return err
			}
			if i, ok := index[machineID]; ok {
				machines[i].Edges = append(machines[i].Edges, edge)
			}
		}
		return edgeRows.Err()
	})
	return machines, err
}

// DeleteSeatStatusForSeat removes one seat's reported statuses, on every machine, for the user.
func (r *ORMMachineStatusRepository) DeleteSeatStatusForSeat(ctx context.Context, userID, roomSlug, seatKey string) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM "seat_status" WHERE "user_id" = $1 AND "room" = $2 AND "seat" = $3`, userID, roomSlug, seatKey)
		return err
	})
}

// DeleteSeatStatusForRoom removes the room's reported seat statuses for the user.
func (r *ORMMachineStatusRepository) DeleteSeatStatusForRoom(ctx context.Context, userID, roomSlug string) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM "seat_status" WHERE "user_id" = $1 AND "room" = $2`, userID, roomSlug)
		return err
	})
}

// DeleteMachineEdgesForRoom removes the room's reported topology edges, on every machine, for the
// user. No foreign key cascades, so the room's deletion path calls this explicitly.
func (r *ORMMachineStatusRepository) DeleteMachineEdgesForRoom(ctx context.Context, userID, roomSlug string) error {
	return r.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx, `DELETE FROM "machine_edges" WHERE "user_id" = $1 AND "room" = $2`, userID, roomSlug)
		return err
	})
}
