// Email Token Repository (Python auth/infrastructure/repositories/email_token_repository.py):
// storage for email verification / password reset tokens. Python defines its model on a
// private declarative Base and create_all()s it in the constructor; here the table is
// declared with the shared metadata (CreateTables creates it) and the repository takes a
// SessionManager. Python swallows SQLAlchemyError and returns false / nil / [] / {}.

package repositories

import (
	"context"
	"sort"
	"time"

	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
	tmrepo "agenthub/fastmcp/task_management/infrastructure/repositories"
)

// EmailToken is the EmailToken dataclass.
type EmailToken struct {
	Token     string
	Email     string
	TokenType string
	TokenHash string
	ExpiresAt time.Time
	CreatedAt time.Time
	UsedAt    *time.Time
	IsUsed    bool
	Metadata  *tmentities.OrderedMap[any] // nil is Python's None
	UserID    *string
	IPAddress *string
	UserAgent *string
}

// EmailTokenModel is a row of email_tokens (EmailTokenModel).
type EmailTokenModel struct {
	Token         string     `db:"token"`
	Email         string     `db:"email"`
	TokenType     string     `db:"token_type"`
	TokenHash     string     `db:"token_hash"`
	ExpiresAt     time.Time  `db:"expires_at"`
	CreatedAt     time.Time  `db:"created_at"`
	UsedAt        *time.Time `db:"used_at"`
	IsUsed        bool       `db:"is_used"`
	TokenMetadata *string    `db:"token_metadata"`
	UserID        *string    `db:"user_id"`
	IPAddress     *string    `db:"ip_address"`
	UserAgent     *string    `db:"user_agent"`
}

var emailTokenDatabaseTables = []database.TableDef{
	{Name: "email_tokens", Model: "EmailTokenModel", Columns: []database.ColumnDef{
		{Name: "token", Attr: "token", GoField: "Token", SQLType: "VARCHAR", Nullable: false, PrimaryKey: true},
		{Name: "email", Attr: "email", GoField: "Email", SQLType: "VARCHAR", Nullable: false},
		{Name: "token_type", Attr: "token_type", GoField: "TokenType", SQLType: "VARCHAR", Nullable: false},
		{Name: "token_hash", Attr: "token_hash", GoField: "TokenHash", SQLType: "VARCHAR", Nullable: false},
		{Name: "expires_at", Attr: "expires_at", GoField: "ExpiresAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false},
		{Name: "created_at", Attr: "created_at", GoField: "CreatedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: false, Default: database.DefaultNowUTCNaive},
		{Name: "used_at", Attr: "used_at", GoField: "UsedAt", SQLType: "TIMESTAMP WITHOUT TIME ZONE", Nullable: true},
		{Name: "is_used", Attr: "is_used", GoField: "IsUsed", SQLType: "BOOLEAN", Nullable: true, Default: database.DefaultBool, DefaultValue: "false"},
		{Name: "token_metadata", Attr: "token_metadata", GoField: "TokenMetadata", SQLType: "TEXT", Nullable: true},
		{Name: "user_id", Attr: "user_id", GoField: "UserID", SQLType: "VARCHAR", Nullable: true},
		{Name: "ip_address", Attr: "ip_address", GoField: "IPAddress", SQLType: "VARCHAR", Nullable: true},
		{Name: "user_agent", Attr: "user_agent", GoField: "UserAgent", SQLType: "VARCHAR", Nullable: true},
	}, DDL: []string{
		"CREATE TABLE email_tokens (\n" +
			"\ttoken VARCHAR(255) NOT NULL,\n" +
			"\temail VARCHAR(255) NOT NULL,\n" +
			"\ttoken_type VARCHAR(50) NOT NULL,\n" +
			"\ttoken_hash VARCHAR(255) NOT NULL,\n" +
			"\texpires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tcreated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,\n" +
			"\tused_at TIMESTAMP WITHOUT TIME ZONE,\n" +
			"\tis_used BOOLEAN,\n" +
			"\ttoken_metadata TEXT,\n" +
			"\tuser_id VARCHAR(255),\n" +
			"\tip_address VARCHAR(45),\n" +
			"\tuser_agent VARCHAR(500),\n" +
			"\tPRIMARY KEY (token)\n" +
			")",
		"CREATE INDEX ix_email_tokens_email ON email_tokens (email)",
	}},
}

func init() { database.Tables = append(database.Tables, emailTokenDatabaseTables...) }

// EmailTokenRepository is Python's EmailTokenRepository.
type EmailTokenRepository struct {
	base *tmrepo.ORMRepository[EmailTokenModel]
}

// NewEmailTokenRepository builds the repository over email_tokens.
func NewEmailTokenRepository(sessions *database.SessionManager) (*EmailTokenRepository, error) {
	base, err := tmrepo.NewORMRepository[EmailTokenModel]("email_tokens", sessions)
	if err != nil {
		return nil, err
	}
	return &EmailTokenRepository{base: base}, nil
}

var emailTokenRepositoryInstance *EmailTokenRepository

// GetEmailTokenRepository is get_email_token_repository (the global instance).
func GetEmailTokenRepository(sessions *database.SessionManager) (*EmailTokenRepository, error) {
	if emailTokenRepositoryInstance == nil {
		r, err := NewEmailTokenRepository(sessions)
		if err != nil {
			return nil, err
		}
		emailTokenRepositoryInstance = r
	}
	return emailTokenRepositoryInstance, nil
}

// emailTokenFromModel is _model_to_token.
func emailTokenFromModel(row *EmailTokenModel) *EmailToken {
	var metadata *tmentities.OrderedMap[any]
	if row.TokenMetadata != nil {
		if v, err := tmentities.DecodeJSON([]byte(*row.TokenMetadata)); err == nil {
			if om, ok := v.(*tmentities.OrderedMap[any]); ok {
				metadata = om
			}
		}
	}
	return &EmailToken{
		Token: row.Token, Email: row.Email, TokenType: row.TokenType, TokenHash: row.TokenHash,
		ExpiresAt: row.ExpiresAt, CreatedAt: row.CreatedAt, UsedAt: row.UsedAt, IsUsed: row.IsUsed,
		Metadata: metadata, UserID: row.UserID, IPAddress: row.IPAddress, UserAgent: row.UserAgent,
	}
}

// emailTokenMetadataJSON is _token_to_model's metadata serialization: None for a falsy
// value or an unserializable one.
func emailTokenMetadataJSON(token *EmailToken) *string {
	if token.Metadata == nil || token.Metadata.Len() == 0 {
		return nil
	}
	s, err := tmvo.PyJSONDumps(token.Metadata, -1)
	if err != nil {
		return nil
	}
	return &s
}

// SaveToken is save_token; false on any database error.
func (r *EmailTokenRepository) SaveToken(ctx context.Context, token *EmailToken) (bool, error) {
	if _, err := r.base.Create(ctx, tmrepo.NewKwargs(
		"token", token.Token,
		"email", token.Email,
		"token_type", token.TokenType,
		"token_hash", token.TokenHash,
		"expires_at", token.ExpiresAt,
		"created_at", token.CreatedAt,
		"used_at", token.UsedAt,
		"is_used", token.IsUsed,
		"token_metadata", emailTokenMetadataJSON(token),
		"user_id", token.UserID,
		"ip_address", token.IPAddress,
		"user_agent", token.UserAgent,
	)); err != nil {
		return false, nil
	}
	return true, nil
}

// GetToken is get_token; nil when absent or on error.
func (r *EmailTokenRepository) GetToken(ctx context.Context, token string) (*EmailToken, error) {
	row, err := r.base.GetByID(ctx, token)
	if err != nil || row == nil {
		return nil, nil
	}
	return emailTokenFromModel(row), nil
}

// GetTokensByEmail is get_tokens_by_email; the result is ordered by created_at desc.
func (r *EmailTokenRepository) GetTokensByEmail(ctx context.Context, email string, tokenType *string, includeUsed bool) ([]*EmailToken, error) {
	filters := tmrepo.NewKwargs("email", email)
	if tokenType != nil {
		filters.Set("token_type", *tokenType)
	}
	if !includeUsed {
		filters.Set("is_used", false)
	}
	rows, err := r.base.FindBy(ctx, filters)
	if err != nil {
		return []*EmailToken{}, nil
	}
	sort.SliceStable(rows, func(i, j int) bool { return rows[i].CreatedAt.After(rows[j].CreatedAt) })
	out := make([]*EmailToken, 0, len(rows))
	for _, row := range rows {
		out = append(out, emailTokenFromModel(row))
	}
	return out, nil
}

// MarkTokenUsed is mark_token_used; true even when no row matches.
func (r *EmailTokenRepository) MarkTokenUsed(ctx context.Context, token string, usedAt *time.Time) (bool, error) {
	if usedAt == nil {
		now := time.Now().UTC()
		usedAt = &now
	}
	if _, err := r.base.Update(ctx, token, tmrepo.NewKwargs("is_used", true, "used_at", usedAt)); err != nil {
		return false, nil
	}
	return true, nil
}

// DeleteToken is delete_token.
func (r *EmailTokenRepository) DeleteToken(ctx context.Context, token string) (bool, error) {
	deleted, err := r.base.Delete(ctx, token)
	if err != nil {
		return false, nil
	}
	return deleted, nil
}

// CleanupExpiredTokens is cleanup_expired_tokens; the affected row count (0 on error).
func (r *EmailTokenRepository) CleanupExpiredTokens(ctx context.Context, olderThanDays int) (int, error) {
	now := time.Now().UTC()
	cutoff := now.AddDate(0, 0, -olderThanDays)
	n := 0
	err := r.base.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		res, err := s.ExecContext(ctx,
			"DELETE FROM email_tokens WHERE expires_at < $1 OR created_at < $2", now, cutoff)
		if err != nil {
			return err
		}
		affected, err := res.RowsAffected()
		if err != nil {
			return err
		}
		n = int(affected)
		return nil
	})
	if err != nil {
		return 0, nil
	}
	return n, nil
}

// ValidateToken is validate_token; it optionally marks the token used.
func (r *EmailTokenRepository) ValidateToken(ctx context.Context, token, email, tokenType string, markUsed bool) (*EmailToken, error) {
	row, err := r.base.FindOneBy(ctx, tmrepo.NewKwargs("token", token, "email", email, "token_type", tokenType))
	if err != nil || row == nil {
		return nil, nil
	}
	tokenObj := emailTokenFromModel(row)
	if tokenObj.IsUsed {
		return nil, nil
	}
	if tokenObj.ExpiresAt.Before(time.Now().UTC()) {
		return nil, nil
	}
	if markUsed {
		now := time.Now().UTC()
		if _, err := r.base.Update(ctx, token, tmrepo.NewKwargs("is_used", true, "used_at", now)); err != nil {
			return nil, nil
		}
		tokenObj.IsUsed = true
		tokenObj.UsedAt = &now
	}
	return tokenObj, nil
}

// GetTokenStats is get_token_stats; the counters plus the usage rate.
func (r *EmailTokenRepository) GetTokenStats(ctx context.Context) (*tmentities.OrderedMap[any], error) {
	out := tmentities.NewOrderedMap[any]()
	err := r.base.GetDBSession(ctx, func(ctx context.Context, s database.DBTX) error {
		var total, used, expired, verification, reset int64
		if err := s.QueryRowContext(ctx, `SELECT count(*) FROM email_tokens`).Scan(&total); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, `SELECT count(*) FROM email_tokens WHERE is_used = true`).Scan(&used); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, `SELECT count(*) FROM email_tokens WHERE expires_at < $1`, time.Now().UTC()).Scan(&expired); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, `SELECT count(*) FROM email_tokens WHERE token_type = 'verification'`).Scan(&verification); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, `SELECT count(*) FROM email_tokens WHERE token_type = 'password_reset'`).Scan(&reset); err != nil {
			return err
		}
		usageRate := 0.0
		if total > 0 {
			usageRate = float64(used) / float64(total) * 100
		}
		out.Set("total_tokens", total)
		out.Set("used_tokens", used)
		out.Set("expired_tokens", expired)
		out.Set("active_tokens", total-used-expired)
		out.Set("verification_tokens", verification)
		out.Set("reset_tokens", reset)
		out.Set("usage_rate", usageRate)
		return nil
	})
	if err != nil {
		return tmentities.NewOrderedMap[any](), nil
	}
	return out, nil
}
