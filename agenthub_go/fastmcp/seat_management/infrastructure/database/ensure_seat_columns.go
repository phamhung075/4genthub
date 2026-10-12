package database

// Seat-system columns that postdate their table, applied to an EXISTING schema by the boot's
// single DDL path (DatabaseConfig.CreateTables, reached only under AUTO_MIGRATE=true).
//
// WHY THIS EXISTS AT ALL: createAll creates a table only when it is absent, so
// rooms.team_id — the NEXT_GEN D5 sharing column — would never reach a database whose rooms
// table already exists. That is production, and every dev database created before this change:
// the sharing feature would be inert there while the schema file and the ORM both claim the
// column, which is the class of gap already recorded against ck_modules_kind. The column and its
// index ship together on BOTH paths: this one for an existing table, and the rooms TableDef in
// seat_tables.go for a fresh one.
//
// The engine here is always PostgreSQL (the same note as ensure_ai_columns.go), so ADD COLUMN IF
// NOT EXISTS is the idempotency, and the FOREIGN KEY the column carries is declared in the
// column type so the migrated schema matches the created one.

import (
	"context"
	"database/sql"

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// seatColumn is one column that must exist on an existing table, with the index over it. indexCols
// is the index's own column list; empty means "the column this entry is about", which is the shape
// every single-column index here has.
type seatColumn struct {
	table, name, typ, index, indexCols string
}

// indexColumns is the list the index is built over.
func (c seatColumn) indexColumns() string {
	if c.indexCols != "" {
		return c.indexCols
	}
	return c.name
}

// seatColumns is the register of seat-system columns added after their table. The type is spelled
// exactly as the rooms TableDef types it, so the migrated and the created schema agree.
var seatColumns = []seatColumn{
	{
		table: "rooms",
		name:  "team_id",
		typ:   "UUID REFERENCES teams (id)",
		index: "ix_rooms_team_id",
	},
	{
		// The answer leg's delivery marker. S1's room_decisions predates it, and the pull selects on
		// it, so a database created before this change must gain it - and gain it WITH its index,
		// which is composite (the pull filters one machine's answered, unacked rows), hence the
		// explicit column list rather than the column alone.
		table:     "room_decisions",
		name:      "acked_at",
		typ:       "TIMESTAMP WITH TIME ZONE",
		index:     "ix_room_decisions_user_rig_state_acked",
		indexCols: "user_id, rig_name, state, acked_at",
	},
}

// EnsureSeatColumnsExist adds the missing columns and their indexes in one transaction. It is
// registered into taskdb.ColumnEnsurers by init below. A second run is a no-op.
func EnsureSeatColumnsExist(ctx context.Context, db *sql.DB) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	for _, c := range seatColumns {
		if _, err := tx.ExecContext(ctx,
			"ALTER TABLE "+c.table+" ADD COLUMN IF NOT EXISTS "+c.name+" "+c.typ); err != nil {
			_ = tx.Rollback()
			return err
		}
		if c.index == "" {
			continue
		}
		if _, err := tx.ExecContext(ctx,
			"CREATE INDEX IF NOT EXISTS "+c.index+" ON "+c.table+" ("+c.indexColumns()+")"); err != nil {
			_ = tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func init() { taskdb.ColumnEnsurers = append(taskdb.ColumnEnsurers, EnsureSeatColumnsExist) }
