package database

// taskEventDatabaseTables is the task-event ledger's table definition, HAND-WRITTEN rather than
// generated: models.go comes from the Python SQLAlchemy metadata and this table does not exist
// there. The architect ruled this route for O1a, so nothing here edits models.go, gen_models.py or
// agenthub_main.
//
// Precedents for the shape: seat_management/infrastructure/database/seat_tables.go and auth's
// email_token_repository.go.
//
// WHY APPENDING IN init() IS ORDER-SAFE: package-level variables are initialised before any init()
// function runs, so Tables already contains tasks by the time this runs, and task_events' foreign
// key is therefore ordered after the table it references.
var taskEventDatabaseTables = []TableDef{
	{Name: "task_events", Model: "TaskEvent", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "tasks.id", OnDelete: "", EnumName: ""},
		{Name: "subtask_id", Attr: "subtask_id", GoField: "SubtaskID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR(64)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "seq", Attr: "seq", GoField: "Seq", SQLType: "INTEGER", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_seq", Attr: "user_seq", GoField: "UserSeq", SQLType: "BIGINT", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "client_event_id", Attr: "client_event_id", GoField: "ClientEventID", SQLType: "UUID", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "kind", Attr: "kind", GoField: "Kind", SQLType: "VARCHAR(32)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "actor_kind", Attr: "actor_kind", GoField: "ActorKind", SQLType: "VARCHAR(16)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "actor_id", Attr: "actor_id", GoField: "ActorID", SQLType: "VARCHAR(255)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "payload", Attr: "payload", GoField: "Payload", SQLType: "JSONB", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNowUTCNaive, DefaultValue: "", ServerDefault: "now()", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		// The two closed vocabularies are CHECK constraints rather than PostgreSQL enum types:
		// extending a CHECK is one DDL string, while the registry has no lifecycle for CREATE TYPE.
		// Precedent: ck_modules_kind in seat_tables.go.
		//
		// uq_task_event_seq is the belt to the advisory lock's brace in the repository - if the lock
		// were ever bypassed, a duplicate sequence fails loudly instead of overwriting an event.
		// The same holds for the two per-user uniques below, and they are the pair the cursor and
		// the outbox need: uq_task_event_user_seq keeps the read cursor (user_seq) from repeating,
		// and uq_task_event_client_event makes "a resent client_event_id lands once" a property of
		// the table rather than a rule a caller must remember.
		// No CASCADE on the foreign key, by this schema's design: the application layer cascades.
		"CREATE TABLE task_events (\n\tid UUID NOT NULL,\n\ttask_id UUID NOT NULL,\n\tsubtask_id UUID,\n\tuser_id VARCHAR(64) NOT NULL,\n\tseq INTEGER NOT NULL,\n\tuser_seq BIGINT NOT NULL,\n\tclient_event_id UUID,\n\tkind VARCHAR(32) NOT NULL,\n\tactor_kind VARCHAR(16) NOT NULL,\n\tactor_id VARCHAR(255) NOT NULL,\n\tpayload JSONB,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n\tPRIMARY KEY (id),\n\tCONSTRAINT uq_task_event_seq UNIQUE (task_id, seq),\n\tCONSTRAINT uq_task_event_user_seq UNIQUE (user_id, user_seq),\n\tCONSTRAINT uq_task_event_client_event UNIQUE (user_id, client_event_id),\n\tCONSTRAINT ck_task_event_kind CHECK (kind IN ('assigned', 'claimed', 'delivered', 'context_loaded', 'progress', 'status_changed', 'evidence_submitted', 'gate_verdict', 'escalated', 'human_decision', 'handover', 'context_updated')),\n\tCONSTRAINT ck_task_event_actor_kind CHECK (actor_kind IN ('seat', 'client', 'gate', 'human')),\n\tFOREIGN KEY(task_id) REFERENCES tasks (id)\n)",
		"CREATE INDEX idx_task_event_task_seq ON task_events (task_id, seq)",
	}},
}

func init() {
	Tables = append(Tables, taskEventDatabaseTables...)
}
