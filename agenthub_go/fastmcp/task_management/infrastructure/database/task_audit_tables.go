package database

// taskAuditDatabaseTables is the task audit trail's table definition, HAND-WRITTEN rather than
// generated: models.go comes from the Python SQLAlchemy metadata and this table does not exist
// there. Precedents: task_event_tables.go in this package, seat_management's seat_tables.go.
//
// WHY IT IS NOT PART OF task_events. The ledger hangs off tasks.id and the delete cascade removes a
// deleted task's entries with it (task_repository.go's DeleteTask), while this trail exists for the
// opposite reason: the record a prune writes must OUTLIVE the row it describes, so task_id here is a
// plain id with NO foreign key and no cascade. Nothing in this schema deletes these rows except a
// human, and the lifecycle sweep explicitly does not.
//
// task_audit_records carries no reference to any other table, so its position in Tables relative to
// tasks does not matter for createAll's slice order (the one ordering constraint the ledger's table
// states).
var taskAuditDatabaseTables = []TableDef{
	{Name: "task_audit_records", Model: "TaskAuditRecord", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_id", Attr: "task_id", GoField: "TaskID", SQLType: "UUID", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR(64)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "kind", Attr: "kind", GoField: "Kind", SQLType: "VARCHAR(32)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "title", Attr: "title", GoField: "Title", SQLType: "VARCHAR", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR(32)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "priority", Attr: "priority", GoField: "Priority", SQLType: "VARCHAR(32)", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "completion_summary", Attr: "completion_summary", GoField: "CompletionSummary", SQLType: "TEXT", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "evidence", Attr: "evidence", GoField: "Evidence", SQLType: "JSONB", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "detail", Attr: "detail", GoField: "Detail", SQLType: "TEXT", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNowUTCNaive, DefaultValue: "", ServerDefault: "now()", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_created_at", Attr: "task_created_at", GoField: "TaskCreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_updated_at", Attr: "task_updated_at", GoField: "TaskUpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
		{Name: "task_completed_at", Attr: "task_completed_at", GoField: "TaskCompletedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true, PrimaryKey: false, Default: DefaultNone, DefaultValue: "", ServerDefault: "", ForeignKey: "", OnDelete: "", EnumName: ""},
	}, DDL: []string{
		// The kind vocabulary is a CHECK rather than a PostgreSQL enum type: extending a CHECK is one
		// DDL string, while the registry has no lifecycle for CREATE TYPE (the ledger's own reason).
		//
		// NO FOREIGN KEY ON task_id, which is the one thing a reader must not "fix": the delete
		// cascade would take the record with the task, and the record exists to survive exactly that.
		"CREATE TABLE task_audit_records (\n\tid UUID NOT NULL,\n\ttask_id UUID NOT NULL,\n\tuser_id VARCHAR(64) NOT NULL,\n\tkind VARCHAR(32) NOT NULL,\n\ttitle VARCHAR NOT NULL,\n\tstatus VARCHAR(32) NOT NULL,\n\tpriority VARCHAR(32) NOT NULL,\n\tcompletion_summary TEXT,\n\tevidence JSONB,\n\tdetail TEXT NOT NULL,\n\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n\ttask_created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\ttask_updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n\ttask_completed_at TIMESTAMP WITHOUT TIME ZONE,\n\tPRIMARY KEY (id),\n\tCONSTRAINT ck_task_audit_record_kind CHECK (kind IN ('escalated', 'blocked', 'pruned'))\n)",
		"CREATE INDEX idx_task_audit_record_task ON task_audit_records (task_id, created_at)",
	}},
}

func init() {
	Tables = append(Tables, taskAuditDatabaseTables...)
}
