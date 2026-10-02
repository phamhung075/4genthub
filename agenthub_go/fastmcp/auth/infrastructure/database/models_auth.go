// Row structs and table metadata for auth/infrastructure/database/models.py. The
// generated task_management database/models.go does not include the auth tables, so they
// are declared here in the model's own package and registered into the shared Tables
// registry (the base ORM repository resolves tables by name there).
package database

import (
	"encoding/json"
	"time"

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"
)

// User is a row of users (auth models.User).
type User struct {
	ID                   string          `db:"id"`
	Email                string          `db:"email"`
	Username             string          `db:"username"`
	PasswordHash         string          `db:"password_hash"`
	FullName             *string         `db:"full_name"`
	Status               string          `db:"status"`
	Roles                json.RawMessage `db:"roles"`
	EmailVerified        bool            `db:"email_verified"`
	EmailVerifiedAt      *time.Time      `db:"email_verified_at"`
	LastLoginAt          *time.Time      `db:"last_login_at"`
	FailedLoginAttempts  int64           `db:"failed_login_attempts"`
	LockedUntil          *time.Time      `db:"locked_until"`
	PasswordChangedAt    *time.Time      `db:"password_changed_at"`
	PasswordResetToken   *string         `db:"password_reset_token"`
	PasswordResetExpires *time.Time      `db:"password_reset_expires"`
	RefreshTokenFamily   *string         `db:"refresh_token_family"`
	RefreshTokenVersion  int64           `db:"refresh_token_version"`
	CreatedAt            time.Time       `db:"created_at"`
	UpdatedAt            time.Time       `db:"updated_at"`
	CreatedBy            *string         `db:"created_by"`
	ProjectIDs           json.RawMessage `db:"project_ids"`
	DefaultProjectID     *string         `db:"default_project_id"`
	MetadataJSON         json.RawMessage `db:"metadata"`
}

// UserTokenBalance is a row of user_token_balances (auth models.UserTokenBalance).
type UserTokenBalance struct {
	ID                      string     `db:"id"`
	UserID                  string     `db:"user_id"`
	AvailableTokens         int64      `db:"available_tokens"`
	MonthlyQuota            int64      `db:"monthly_quota"`
	LastResetAt             *time.Time `db:"last_reset_at"`
	NextResetAt             *time.Time `db:"next_reset_at"`
	TokensConsumedToday     int64      `db:"tokens_consumed_today"`
	TokensConsumedThisMonth int64      `db:"tokens_consumed_this_month"`
	TotalTokensConsumed     int64      `db:"total_tokens_consumed"`
	CreatedAt               time.Time  `db:"created_at"`
	UpdatedAt               time.Time  `db:"updated_at"`
}

// authDatabaseTables mirrors the SQLAlchemy metadata of the auth models.
var authDatabaseTables = []taskdb.TableDef{
	{Name: "users", Model: "User", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true},
		{Name: "email", Attr: "email", GoField: "Email", SQLType: "VARCHAR", Nullable: false},
		{Name: "username", Attr: "username", GoField: "Username", SQLType: "VARCHAR", Nullable: false},
		{Name: "password_hash", Attr: "password_hash", GoField: "PasswordHash", SQLType: "VARCHAR", Nullable: false},
		{Name: "full_name", Attr: "full_name", GoField: "FullName", SQLType: "VARCHAR", Nullable: true},
		{Name: "status", Attr: "status", GoField: "Status", SQLType: "VARCHAR", Nullable: false, Default: taskdb.DefaultString, DefaultValue: "\"pending_verification\""},
		{Name: "roles", Attr: "roles", GoField: "Roles", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyList},
		{Name: "email_verified", Attr: "email_verified", GoField: "EmailVerified", SQLType: "BOOLEAN", Nullable: false, Default: taskdb.DefaultBool, DefaultValue: "false"},
		{Name: "email_verified_at", Attr: "email_verified_at", GoField: "EmailVerifiedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "last_login_at", Attr: "last_login_at", GoField: "LastLoginAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "failed_login_attempts", Attr: "failed_login_attempts", GoField: "FailedLoginAttempts", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
		{Name: "locked_until", Attr: "locked_until", GoField: "LockedUntil", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "password_changed_at", Attr: "password_changed_at", GoField: "PasswordChangedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "password_reset_token", Attr: "password_reset_token", GoField: "PasswordResetToken", SQLType: "VARCHAR", Nullable: true},
		{Name: "password_reset_expires", Attr: "password_reset_expires", GoField: "PasswordResetExpires", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "refresh_token_family", Attr: "refresh_token_family", GoField: "RefreshTokenFamily", SQLType: "VARCHAR", Nullable: true},
		{Name: "refresh_token_version", Attr: "refresh_token_version", GoField: "RefreshTokenVersion", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "created_by", Attr: "created_by", GoField: "CreatedBy", SQLType: "VARCHAR", Nullable: true},
		{Name: "project_ids", Attr: "project_ids", GoField: "ProjectIDs", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyList},
		{Name: "default_project_id", Attr: "default_project_id", GoField: "DefaultProjectID", SQLType: "UUID", Nullable: true},
		{Name: "metadata", Attr: "metadata_json", GoField: "MetadataJSON", SQLType: "JSON", Nullable: false, Default: taskdb.DefaultEmptyDict},
	}, DDL: []string{
		"CREATE TABLE users (\n" +
			"\tid UUID NOT NULL,\n" +
			"\temail VARCHAR(254) NOT NULL,\n" +
			"\tusername VARCHAR(150) NOT NULL,\n" +
			"\tpassword_hash VARCHAR(255) NOT NULL,\n" +
			"\tfull_name VARCHAR(255),\n" +
			"\tstatus VARCHAR(50) NOT NULL,\n" +
			"\troles JSON NOT NULL,\n" +
			"\temail_verified BOOLEAN NOT NULL,\n" +
			"\temail_verified_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tlast_login_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tfailed_login_attempts INTEGER NOT NULL,\n" +
			"\tlocked_until TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tpassword_changed_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tpassword_reset_token VARCHAR(255),\n" +
			"\tpassword_reset_expires TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\trefresh_token_family VARCHAR(255),\n" +
			"\trefresh_token_version INTEGER NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n" +
			"\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n" +
			"\tcreated_by VARCHAR(255),\n" +
			"\tproject_ids JSON NOT NULL,\n" +
			"\tdefault_project_id UUID,\n" +
			"\tmetadata JSON NOT NULL,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tUNIQUE (email),\n" +
			"\tUNIQUE (username),\n" +
			"\tUNIQUE (password_reset_token),\n" +
			"\tCONSTRAINT check_email_not_empty CHECK (length(email) > 0),\n" +
			"\tCONSTRAINT check_username_not_empty CHECK (length(username) > 0)\n" +
			")",
		"CREATE INDEX ix_users_email ON users (email)",
		"CREATE INDEX ix_users_username ON users (username)",
		"CREATE INDEX ix_users_status ON users (status)",
		"CREATE INDEX ix_users_password_reset_token ON users (password_reset_token)",
		"CREATE INDEX ix_users_refresh_token_family ON users (refresh_token_family)",
	}},
	{Name: "user_token_balances", Model: "UserTokenBalance", Columns: []taskdb.ColumnDef{
		{Name: "id", Attr: "id", GoField: "ID", SQLType: "UUID", Nullable: false, PrimaryKey: true, Default: taskdb.DefaultUUIDv4},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "UUID", Nullable: false, ForeignKey: "users.id", OnDelete: "CASCADE"},
		{Name: "available_tokens", Attr: "available_tokens", GoField: "AvailableTokens", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
		{Name: "monthly_quota", Attr: "monthly_quota", GoField: "MonthlyQuota", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "10000"},
		{Name: "last_reset_at", Attr: "last_reset_at", GoField: "LastResetAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "next_reset_at", Attr: "next_reset_at", GoField: "NextResetAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "tokens_consumed_today", Attr: "tokens_consumed_today", GoField: "TokensConsumedToday", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
		{Name: "tokens_consumed_this_month", Attr: "tokens_consumed_this_month", GoField: "TokensConsumedThisMonth", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
		{Name: "total_tokens_consumed", Attr: "total_tokens_consumed", GoField: "TotalTokensConsumed", SQLType: "INTEGER", Nullable: false, Default: taskdb.DefaultInt, DefaultValue: "0"},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTCNaive, ServerDefault: "now()"},
		{Name: "updated_at", Attr: "updated_at", GoField: "UpdatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: taskdb.DefaultNowUTCNaive, ServerDefault: "now()"},
	}, DDL: []string{
		"CREATE TABLE user_token_balances (\n" +
			"\tid UUID NOT NULL,\n" +
			"\tuser_id UUID NOT NULL,\n" +
			"\tavailable_tokens INTEGER NOT NULL,\n" +
			"\tmonthly_quota INTEGER NOT NULL,\n" +
			"\tlast_reset_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tnext_reset_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\ttokens_consumed_today INTEGER NOT NULL,\n" +
			"\ttokens_consumed_this_month INTEGER NOT NULL,\n" +
			"\ttotal_tokens_consumed INTEGER NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n" +
			"\tupdated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,\n" +
			"\tPRIMARY KEY (id),\n" +
			"\tUNIQUE (user_id),\n" +
			"\tCONSTRAINT check_available_tokens_non_negative CHECK (available_tokens >= 0),\n" +
			"\tCONSTRAINT check_monthly_quota_non_negative CHECK (monthly_quota >= 0),\n" +
			"\tFOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n" +
			")",
		"CREATE INDEX ix_user_token_balances_user_id ON user_token_balances (user_id)",
	}},
}

func init() { taskdb.Tables = append(taskdb.Tables, authDatabaseTables...) }
