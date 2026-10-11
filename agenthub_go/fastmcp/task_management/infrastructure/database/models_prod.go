// Production tables that the generated models.go does not cover. The columns and types are
// transcribed from the authoritative production DDL, the embedded
// fastmcp/task_management/infrastructure/database/init_schema_postgresql.sql
// (plus applied_migrations, which that file does not carry), and follow the row-struct
// / ColumnDef conventions of models.go: json.RawMessage for JSONB, string for UUID, time.Time
// for timestamps and pointers for nullable columns.
//
// CORRECTION 2026-10-10: an earlier version of this comment said applied_migrations was "created by
// the Python migration runner". That was false, and is measured false - no code in this tree ever
// created the table, and the Python runner's own ledger was schema_migrations (that tree was removed
// in a50929c6). The rows are written by migration_runner.go's Runner today.
//
// These tables are intentionally not appended to Tables here. The three
// user_id foreign keys (token_transactions, user_api_tokens, user_sessions) reference the users
// table, which the auth package registers. Registering these definitions from the base package
// would duplicate table metadata and mis-order CREATE TABLE against its dependencies.
package database

import (
	"encoding/json"
	"time"
)

// AgentImportHistory is a row of agent_import_history.
type AgentImportHistory struct {
	ID                 string    `db:"id"`
	ImporterUserID     string    `db:"importer_user_id"`
	SourceInstanceID   string    `db:"source_instance_id"`
	ImportedInstanceID string    `db:"imported_instance_id"`
	ImportedAt         time.Time `db:"imported_at"`
	ShareToken         *string   `db:"share_token"`
}

// AppliedMigration is a row of applied_migrations, the migration ledger: migration_runner.go's
// Runner records one row when it applies a migration, so a row exists exactly when that migration
// applied. success and error_message are never written - a step that fails rolls back and records
// nothing at all.
type AppliedMigration struct {
	ID            int64      `db:"id"`
	MigrationName string     `db:"migration_name"`
	AppliedAt     *time.Time `db:"applied_at"`
	Success       *bool      `db:"success"`
	ErrorMessage  *string    `db:"error_message"`
}

// TokenTransaction is a row of token_transactions.
type TokenTransaction struct {
	ID                string          `db:"id"`
	UserID            string          `db:"user_id"`
	OperationType     string          `db:"operation_type"`
	TokensDeducted    int64           `db:"tokens_deducted"`
	BalanceBefore     int64           `db:"balance_before"`
	BalanceAfter      int64           `db:"balance_after"`
	OperationMetadata json.RawMessage `db:"operation_metadata"`
	CreatedAt         time.Time       `db:"created_at"`
}

// UserAgentConfigurationMd is a row of user_agent_configurations_md.
type UserAgentConfigurationMd struct {
	ID                string    `db:"id"`
	InstanceID        string    `db:"instance_id"`
	ConfigurationType string    `db:"configuration_type"`
	ContentMarkdown   string    `db:"content_markdown"`
	CreatedAt         time.Time `db:"created_at"`
	UpdatedAt         time.Time `db:"updated_at"`
}

// UserAPIToken is a row of user_api_tokens.
type UserAPIToken struct {
	ID         string          `db:"id"`
	UserID     string          `db:"user_id"`
	TokenHash  string          `db:"token_hash"`
	TokenCost  int64           `db:"token_cost"`
	Name       string          `db:"name"`
	Scopes     json.RawMessage `db:"scopes"`
	IsActive   bool            `db:"is_active"`
	ExpiresAt  *time.Time      `db:"expires_at"`
	LastUsedAt *time.Time      `db:"last_used_at"`
	CreatedAt  time.Time       `db:"created_at"`
	UpdatedAt  time.Time       `db:"updated_at"`
	RevokedAt  *time.Time      `db:"revoked_at"`
}

// UserSession is a row of user_sessions.
type UserSession struct {
	ID           string          `db:"id"`
	UserID       string          `db:"user_id"`
	SessionToken string          `db:"session_token"`
	RefreshToken *string         `db:"refresh_token"`
	IPAddress    *string         `db:"ip_address"`
	UserAgent    *string         `db:"user_agent"`
	DeviceInfo   json.RawMessage `db:"device_info"`
	CreatedAt    time.Time       `db:"created_at"`
	LastActivity time.Time       `db:"last_activity"`
	ExpiresAt    time.Time       `db:"expires_at"`
	RevokedAt    *time.Time      `db:"revoked_at"`
	IsActive     bool            `db:"is_active"`
}

// ProductionTables lists the six production tables that the generated models.go does not
// cover, in production column order. The DB column types match init_schema_postgresql.sql;
// SQLType is the column-type token the repositories package dispatches on, so JSONB is
// reported as JSON (the same convention as models.go) even though the DDL declares JSONB.
var ProductionTables = []TableDef{
	{Name: "agent_import_history", Model: "AgentImportHistory", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4},
		{Name: "importer_user_id", Attr: "importer_user_id", GoField: "ImporterUserID", SQLType: "UUID", Nullable: false},
		{Name: "source_instance_id", Attr: "source_instance_id", GoField: "SourceInstanceID", SQLType: "UUID", Nullable: false},
		{Name: "imported_instance_id", Attr: "imported_instance_id", GoField: "ImportedInstanceID", SQLType: "UUID", Nullable: false},
		{Name: "imported_at", Attr: "imported_at", GoField: "ImportedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "share_token", Attr: "share_token", GoField: "ShareToken", SQLType: "VARCHAR", Nullable: true},
	}, DDL: []string{
		"CREATE TABLE agent_import_history (\n" +
			"\tid UUID NOT NULL,\n" +
			"\timporter_user_id UUID NOT NULL,\n" +
			"\tsource_instance_id UUID NOT NULL,\n" +
			"\timported_instance_id UUID NOT NULL,\n" +
			"\timported_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tshare_token VARCHAR(64),\n" +
			"\tPRIMARY KEY (id)\n" +
			")",
		"CREATE INDEX idx_import_history_date ON agent_import_history (imported_at)",
		"CREATE INDEX idx_import_history_importer ON agent_import_history (importer_user_id)",
		"CREATE INDEX idx_import_history_source ON agent_import_history (source_instance_id)",
	}},
	{Name: "applied_migrations", Model: "AppliedMigration", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "INTEGER", Nullable: false, PrimaryKey: true},
		{Name: "migration_name", Attr: "migration_name", GoField: "MigrationName", SQLType: "VARCHAR", Nullable: false},
		{Name: "applied_at", Attr: "applied_at", GoField: "AppliedAt", SQLType: "TIMESTAMP WITH TIME ZONE", Nullable: true, Default: DefaultNowUTC, ServerDefault: "CURRENT_TIMESTAMP"},
		{Name: "success", Attr: "success", GoField: "Success", SQLType: "BOOLEAN", Nullable: true, Default: DefaultBool, DefaultValue: "true", ServerDefault: "true"},
		{Name: "error_message", Attr: "error_message", GoField: "ErrorMessage", SQLType: "TEXT", Nullable: true},
	}, DDL: []string{
		"CREATE TABLE applied_migrations (\n" +
			"\tid SERIAL NOT NULL,\n" +
			"\tmigration_name VARCHAR(255) NOT NULL,\n" +
			"\tapplied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,\n" +
			"\tsuccess BOOLEAN DEFAULT true,\n" +
			"\terror_message TEXT,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT applied_migrations_migration_name_key UNIQUE (migration_name)\n" +
			")",
	}},
	{Name: "token_transactions", Model: "TokenTransaction", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "UUID", Nullable: false, ForeignKey: "users.id"},
		{Name: "operation_type", Attr: "operation_type", GoField: "OperationType", SQLType: "VARCHAR", Nullable: false},
		{Name: "tokens_deducted", Attr: "tokens_deducted", GoField: "TokensDeducted", SQLType: "INTEGER", Nullable: false},
		{Name: "balance_before", Attr: "balance_before", GoField: "BalanceBefore", SQLType: "INTEGER", Nullable: false},
		{Name: "balance_after", Attr: "balance_after", GoField: "BalanceAfter", SQLType: "INTEGER", Nullable: false},
		{Name: "operation_metadata", Attr: "operation_metadata", GoField: "OperationMetadata", SQLType: "JSON", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
	}, DDL: []string{
		"CREATE TABLE token_transactions (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id UUID NOT NULL,\n" +
			"\toperation_type VARCHAR(100) NOT NULL,\n" +
			"\ttokens_deducted INTEGER NOT NULL,\n" +
			"\tbalance_before INTEGER NOT NULL,\n" +
			"\tbalance_after INTEGER NOT NULL,\n" +
			"\toperation_metadata JSONB NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tFOREIGN KEY(user_id) REFERENCES users (id)\n" +
			")",
		"CREATE INDEX ix_token_transactions_created_at ON token_transactions (created_at)",
		"CREATE INDEX ix_token_transactions_operation_type ON token_transactions (operation_type)",
		"CREATE INDEX ix_token_transactions_user_created ON token_transactions (user_id, created_at)",
		"CREATE INDEX ix_token_transactions_user_id ON token_transactions (user_id)",
	}},
	{Name: "user_agent_configurations_md", Model: "UserAgentConfigurationMd", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4},
		{Name: "instance_id", Attr: "instance_id", GoField: "InstanceID", SQLType: "UUID", Nullable: false},
		{Name: "configuration_type", Attr: "configuration_type", GoField: "ConfigurationType", SQLType: "VARCHAR", Nullable: false},
		{Name: "content_markdown", Attr: "content_markdown", GoField: "ContentMarkdown", SQLType: "TEXT", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
	}, DDL: []string{
		"CREATE TABLE user_agent_configurations_md (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tinstance_id UUID NOT NULL,\n" +
			"\tconfiguration_type VARCHAR(50) NOT NULL,\n" +
			"\tcontent_markdown TEXT NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT user_agent_configurations_md_instance_type_key UNIQUE (instance_id, configuration_type)\n" +
			")",
		"CREATE INDEX idx_configurations_md_instance ON user_agent_configurations_md (instance_id, configuration_type)",
	}},
	{Name: "user_api_tokens", Model: "UserAPIToken", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "UUID", Nullable: false, ForeignKey: "users.id"},
		{Name: "token_hash", Attr: "token_hash", GoField: "TokenHash", SQLType: "VARCHAR", Nullable: false},
		{Name: "token_cost", Attr: "token_cost", GoField: "TokenCost", SQLType: "INTEGER", Nullable: false},
		{Name: "name", Attr: "name", GoField: "Name", SQLType: "VARCHAR", Nullable: false},
		{Name: "scopes", Attr: "scopes", GoField: "Scopes", SQLType: "JSON", Nullable: false},
		{Name: "is_active", Attr: "is_active", GoField: "IsActive", SQLType: "BOOLEAN", Nullable: false},
		{Name: "expires_at", Attr: "expires_at", GoField: "ExpiresAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "last_used_at", Attr: "last_used_at", GoField: "LastUsedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "revoked_at", Attr: "revoked_at", GoField: "RevokedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
	}, DDL: []string{
		"CREATE TABLE user_api_tokens (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id UUID NOT NULL,\n" +
			"\ttoken_hash VARCHAR(255) NOT NULL,\n" +
			"\ttoken_cost INTEGER NOT NULL,\n" +
			"\tname VARCHAR(100) NOT NULL,\n" +
			"\tscopes JSONB NOT NULL,\n" +
			"\tis_active BOOLEAN NOT NULL,\n" +
			"\texpires_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tlast_used_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tupdated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\trevoked_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT user_api_tokens_token_hash_key UNIQUE (token_hash),\n" +
			"\tFOREIGN KEY(user_id) REFERENCES users (id)\n" +
			")",
		"CREATE INDEX ix_user_api_tokens_expires_at ON user_api_tokens (expires_at)",
		"CREATE INDEX ix_user_api_tokens_is_active ON user_api_tokens (is_active)",
		"CREATE INDEX ix_user_api_tokens_user_id ON user_api_tokens (user_id)",
	}},
	{Name: "user_sessions", Model: "UserSession", Columns: []ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "UUID", Nullable: false, ForeignKey: "users.id"},
		{Name: "session_token", Attr: "session_token", GoField: "SessionToken", SQLType: "VARCHAR", Nullable: false},
		{Name: "refresh_token", Attr: "refresh_token", GoField: "RefreshToken", SQLType: "VARCHAR", Nullable: true},
		{Name: "ip_address", Attr: "ip_address", GoField: "IPAddress", SQLType: "VARCHAR", Nullable: true},
		{Name: "user_agent", Attr: "user_agent", GoField: "UserAgent", SQLType: "TEXT", Nullable: true},
		{Name: "device_info", Attr: "device_info", GoField: "DeviceInfo", SQLType: "JSON", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "last_activity", Attr: "last_activity", GoField: "LastActivity", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "expires_at", Attr: "expires_at", GoField: "ExpiresAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false},
		{Name: "revoked_at", Attr: "revoked_at", GoField: "RevokedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "is_active", Attr: "is_active", GoField: "IsActive", SQLType: "BOOLEAN", Nullable: false},
	}, DDL: []string{
		"CREATE TABLE user_sessions (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id UUID NOT NULL,\n" +
			"\tsession_token VARCHAR(255) NOT NULL,\n" +
			"\trefresh_token VARCHAR(255),\n" +
			"\tip_address VARCHAR(45),\n" +
			"\tuser_agent TEXT,\n" +
			"\tdevice_info JSONB NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tlast_activity TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\texpires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\trevoked_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tis_active BOOLEAN NOT NULL,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tCONSTRAINT user_sessions_refresh_token_key UNIQUE (refresh_token),\n" +
			"\tCONSTRAINT user_sessions_session_token_key UNIQUE (session_token),\n" +
			"\tFOREIGN KEY(user_id) REFERENCES users (id)\n" +
			")",
		"CREATE INDEX ix_user_sessions_is_active ON user_sessions (is_active)",
		"CREATE INDEX ix_user_sessions_refresh_token ON user_sessions (refresh_token)",
		"CREATE INDEX ix_user_sessions_session_token ON user_sessions (session_token)",
		"CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id)",
	}},
}
