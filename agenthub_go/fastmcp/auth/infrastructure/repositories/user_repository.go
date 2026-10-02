// User Repository (Python auth/infrastructure/repositories/user_repository.py): user
// persistence over the users table. Python catches (and logs) read errors and returns the
// default; save and delete re-raise. The Python `metadata` column read bug (db_user.metadata
// resolves to SQLAlchemy's MetaData) has no Go representation, so the direct-construction
// methods decode the metadata column instead.

package repositories

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	authEntities "agenthub/fastmcp/auth/domain/entities"
	authdb "agenthub/fastmcp/auth/infrastructure/database"
	tmentities "agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	tmrepo "agenthub/fastmcp/task_management/infrastructure/repositories"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

// UserRepository is Python's UserRepository(session); the session maps to the SessionManager.
type UserRepository struct {
	*tmrepo.ORMRepository[authdb.User]
}

// authUUIDOrNil passes a uuid column value as an untyped nil or a plain string (the UUID
// bind processor does not accept a typed nil pointer).
func authUUIDOrNil(p *string) any {
	if p == nil {
		return nil
	}
	return *p
}

// NewUserRepository builds the repository over the users table.
func NewUserRepository(sessions *database.SessionManager) (*UserRepository, error) {
	base, err := tmrepo.NewORMRepository[authdb.User]("users", sessions)
	if err != nil {
		return nil, err
	}
	return &UserRepository{ORMRepository: base}, nil
}

// authUserRole converts a stored role string, raising like UserRole(role).
func authUserRole(s string) (authEntities.UserRole, error) {
	switch authEntities.UserRole(s) {
	case authEntities.UserRoleAdmin, authEntities.UserRoleUser, authEntities.UserRoleViewer, authEntities.UserRoleDeveloper:
		return authEntities.UserRole(s), nil
	}
	return "", tmvo.ValueErrorf("%s is not a valid UserRole", tmvo.PyRepr(s))
}

// authUserStatus converts a stored status string, raising like UserStatus(status).
func authUserStatus(s string) (authEntities.UserStatus, error) {
	switch authEntities.UserStatus(s) {
	case authEntities.UserStatusActive, authEntities.UserStatusInactive, authEntities.UserStatusSuspended, authEntities.UserStatusPendingVerification:
		return authEntities.UserStatus(s), nil
	}
	return "", tmvo.ValueErrorf("%s is not a valid UserStatus", tmvo.PyRepr(s))
}

// authUserJSONList decodes a JSON array column; empty/None is [].
func authUserJSONList(raw json.RawMessage) ([]any, error) {
	if len(raw) == 0 {
		return []any{}, nil
	}
	v, err := tmentities.DecodeJSON(raw)
	if err != nil {
		return nil, err
	}
	list, ok := v.([]any)
	if !ok {
		return nil, tmvo.TypeErrorf("expected a JSON array, got %s", tmvo.PyRepr(v))
	}
	return list, nil
}

// authUserJSONMap decodes a JSON object column; empty/None is {}.
func authUserJSONMap(raw json.RawMessage) (map[string]any, error) {
	if len(raw) == 0 {
		return map[string]any{}, nil
	}
	v, err := tmentities.DecodeJSON(raw)
	if err != nil {
		return nil, err
	}
	om, ok := v.(*tmentities.OrderedMap[any])
	if !ok {
		return nil, tmvo.TypeErrorf("expected a JSON object, got %s", tmvo.PyRepr(v))
	}
	out := map[string]any{}
	for _, k := range om.Keys() {
		val, _ := om.Get(k)
		out[k] = val
	}
	return out, nil
}

// authUserProjectIDs is `project_ids or []`, stringified like the domain field.
func authUserProjectIDs(raw json.RawMessage) ([]string, error) {
	list, err := authUserJSONList(raw)
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(list))
	for _, v := range list {
		if s, ok := v.(string); ok {
			out = append(out, s)
		} else {
			out = append(out, fmt.Sprint(v))
		}
	}
	return out, nil
}

// authUserRoles converts a decoded roles list (each a string) with UserRole validation.
func authUserRoles(list []any) ([]authEntities.UserRole, error) {
	out := make([]authEntities.UserRole, 0, len(list))
	for _, v := range list {
		s, ok := v.(string)
		if !ok {
			return nil, tmvo.TypeErrorf("roles must be a list of strings, got %s", tmvo.PyRepr(v))
		}
		r, err := authUserRole(s)
		if err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, nil
}

// authUserToDomain is UserModel.to_domain(): metadata is the dataclass default ({}).
func authUserToDomain(row *authdb.User) (*authEntities.User, error) {
	st, err := authUserStatus(row.Status)
	if err != nil {
		return nil, err
	}
	list, err := authUserJSONList(row.Roles)
	if err != nil {
		return nil, err
	}
	roles, err := authUserRoles(list)
	if err != nil {
		return nil, err
	}
	if len(roles) == 0 {
		roles = []authEntities.UserRole{authEntities.UserRoleUser}
	}
	projectIDs, err := authUserProjectIDs(row.ProjectIDs)
	if err != nil {
		return nil, err
	}
	id := row.ID
	u := authEntities.User{
		ID:                   &id,
		Email:                row.Email,
		Username:             row.Username,
		PasswordHash:         row.PasswordHash,
		FullName:             row.FullName,
		Status:               st,
		Roles:                roles,
		EmailVerified:        row.EmailVerified,
		EmailVerifiedAt:      row.EmailVerifiedAt,
		LastLoginAt:          row.LastLoginAt,
		FailedLoginAttempts:  int(row.FailedLoginAttempts),
		LockedUntil:          row.LockedUntil,
		PasswordChangedAt:    row.PasswordChangedAt,
		PasswordResetToken:   row.PasswordResetToken,
		PasswordResetExpires: row.PasswordResetExpires,
		RefreshTokenFamily:   row.RefreshTokenFamily,
		RefreshTokenVersion:  int(row.RefreshTokenVersion),
		CreatedBy:            row.CreatedBy,
		ProjectIDs:           projectIDs,
		DefaultProjectID:     row.DefaultProjectID,
	}
	u.CreatedAt, u.UpdatedAt = &row.CreatedAt, &row.UpdatedAt
	return authEntities.NewUser(u)
}

// authUserDirect is the direct DomainUser(...) construction shared by find_by_id /
// get_by_email / get_by_username: failed/refresh counters fall back to 0, empty roles stay
// empty and metadata is the decoded column (see the package comment).
func authUserDirect(row *authdb.User) (*authEntities.User, error) {
	st, err := authUserStatus(row.Status)
	if err != nil {
		return nil, err
	}
	list, err := authUserJSONList(row.Roles)
	if err != nil {
		return nil, err
	}
	roles, err := authUserRoles(list)
	if err != nil {
		return nil, err
	}
	if roles == nil {
		roles = []authEntities.UserRole{}
	}
	projectIDs, err := authUserProjectIDs(row.ProjectIDs)
	if err != nil {
		return nil, err
	}
	metadata, err := authUserJSONMap(row.MetadataJSON)
	if err != nil {
		return nil, err
	}
	id := row.ID
	failed := int(row.FailedLoginAttempts)
	refresh := int(row.RefreshTokenVersion)
	u := authEntities.User{
		ID:                   &id,
		Email:                row.Email,
		Username:             row.Username,
		PasswordHash:         row.PasswordHash,
		FullName:             row.FullName,
		Status:               st,
		Roles:                roles,
		EmailVerified:        row.EmailVerified,
		EmailVerifiedAt:      row.EmailVerifiedAt,
		LastLoginAt:          row.LastLoginAt,
		FailedLoginAttempts:  failed,
		LockedUntil:          row.LockedUntil,
		PasswordChangedAt:    row.PasswordChangedAt,
		PasswordResetToken:   row.PasswordResetToken,
		PasswordResetExpires: row.PasswordResetExpires,
		RefreshTokenFamily:   row.RefreshTokenFamily,
		RefreshTokenVersion:  refresh,
		CreatedBy:            row.CreatedBy,
		ProjectIDs:           projectIDs,
		DefaultProjectID:     row.DefaultProjectID,
		Metadata:             metadata,
	}
	u.CreatedAt, u.UpdatedAt = &row.CreatedAt, &row.UpdatedAt
	return authEntities.NewUser(u)
}

// authUserToDict is User.to_dict(): the sensitive fields and the mapped column metadata
// attribute (which Python hits instead of metadata_json) are excluded.
func authUserToDict(user *authEntities.User) tmrepo.Kwargs {
	roles := make([]string, len(user.Roles))
	for i, r := range user.Roles {
		roles[i] = string(r)
	}
	projectIDs := user.ProjectIDs
	if projectIDs == nil {
		projectIDs = []string{}
	}
	metadata := user.Metadata
	if metadata == nil {
		metadata = map[string]any{}
	}
	return tmrepo.NewKwargs(
		"id", authUUIDOrNil(user.ID),
		"email", user.Email,
		"username", user.Username,
		"full_name", user.FullName,
		"status", string(user.Status),
		"roles", roles,
		"email_verified", user.EmailVerified,
		"email_verified_at", user.EmailVerifiedAt,
		"last_login_at", user.LastLoginAt,
		"created_at", user.CreatedAt,
		"updated_at", user.UpdatedAt,
		"project_ids", projectIDs,
		"default_project_id", authUUIDOrNil(user.DefaultProjectID),
		"metadata", metadata,
	)
}

// authUserStatusValue is UserModel.from_domain's status conversion.
func authUserStatusValue(status authEntities.UserStatus) string {
	switch string(status) {
	case "PENDING_VERIFICATION":
		return "pending_verification"
	case "ACTIVE":
		return "active"
	case "INACTIVE":
		return "inactive"
	case "SUSPENDED":
		return "suspended"
	}
	return string(status)
}

// authUserFromDomain is UserModel.from_domain: metadata is not copied (the column keeps its
// {} default), timestamps fall back to now.
func authUserFromDomain(user *authEntities.User) (tmrepo.Kwargs, string) {
	id := ""
	if user.ID != nil && *user.ID != "" {
		id = *user.ID
	} else {
		id = tmvo.NewUUIDv4()
	}
	roles := make([]string, len(user.Roles))
	for i, r := range user.Roles {
		roles[i] = string(r)
	}
	projectIDs := user.ProjectIDs
	if projectIDs == nil {
		projectIDs = []string{}
	}
	now := database.TimestampNow()
	createdAt, updatedAt := user.CreatedAt, user.UpdatedAt
	if createdAt == nil {
		createdAt = &now
	}
	if updatedAt == nil {
		updatedAt = &now
	}
	return tmrepo.NewKwargs(
		"id", id,
		"email", user.Email,
		"username", user.Username,
		"password_hash", user.PasswordHash,
		"full_name", user.FullName,
		"status", authUserStatusValue(user.Status),
		"roles", roles,
		"email_verified", user.EmailVerified,
		"email_verified_at", user.EmailVerifiedAt,
		"last_login_at", user.LastLoginAt,
		"failed_login_attempts", user.FailedLoginAttempts,
		"locked_until", user.LockedUntil,
		"password_changed_at", user.PasswordChangedAt,
		"password_reset_token", user.PasswordResetToken,
		"password_reset_expires", user.PasswordResetExpires,
		"refresh_token_family", user.RefreshTokenFamily,
		"refresh_token_version", user.RefreshTokenVersion,
		"created_at", createdAt,
		"updated_at", updatedAt,
		"created_by", user.CreatedBy,
		"project_ids", projectIDs,
		"default_project_id", authUUIDOrNil(user.DefaultProjectID),
	), id
}

// Save is save: update an existing row (or create one when the id is unknown) and return a
// copy of the input carrying the id. Integrity errors propagate.
func (r *UserRepository) Save(ctx context.Context, user *authEntities.User) (*authEntities.User, error) {
	id := ""
	if user.ID != nil && *user.ID != "" {
		id = *user.ID
	}
	exists := false
	if id != "" {
		row, err := r.ORMRepository.GetByID(ctx, id)
		if err != nil {
			return nil, err
		}
		exists = row != nil
	}
	if exists {
		if _, err := r.ORMRepository.Update(ctx, id, authUserToDict(user)); err != nil {
			return nil, err
		}
	} else {
		kwargs, generated := authUserFromDomain(user)
		id = generated
		if _, err := r.ORMRepository.Create(ctx, kwargs); err != nil {
			return nil, err
		}
	}
	out := *user
	out.ID = &id
	return authEntities.NewUser(out)
}

// GetByID is get_by_id (to_domain); errors and conversion failures return nil.
func (r *UserRepository) GetByID(ctx context.Context, userID string) (*authEntities.User, error) {
	row, err := r.ORMRepository.GetByID(ctx, userID)
	if err != nil || row == nil {
		return nil, nil
	}
	u, err := authUserToDomain(row)
	if err != nil {
		return nil, nil
	}
	return u, nil
}

// FindByID is find_by_id (direct construction); errors return nil.
func (r *UserRepository) FindByID(ctx context.Context, userID string) (*authEntities.User, error) {
	row, err := r.ORMRepository.GetByID(ctx, userID)
	if err != nil || row == nil {
		return nil, nil
	}
	u, err := authUserDirect(row)
	if err != nil {
		return nil, nil
	}
	return u, nil
}

// GetByEmail is get_by_email: the lookup email is lowercased.
func (r *UserRepository) GetByEmail(ctx context.Context, email string) (*authEntities.User, error) {
	row, err := r.ORMRepository.FindOneBy(ctx, tmrepo.NewKwargs("email", tmvo.PyLower(email)))
	if err != nil || row == nil {
		return nil, nil
	}
	u, err := authUserDirect(row)
	if err != nil {
		return nil, nil
	}
	return u, nil
}

// GetByUsername is get_by_username (direct construction).
func (r *UserRepository) GetByUsername(ctx context.Context, username string) (*authEntities.User, error) {
	row, err := r.ORMRepository.FindOneBy(ctx, tmrepo.NewKwargs("username", username))
	if err != nil || row == nil {
		return nil, nil
	}
	u, err := authUserDirect(row)
	if err != nil {
		return nil, nil
	}
	return u, nil
}

// GetByResetToken is get_by_reset_token (to_domain).
func (r *UserRepository) GetByResetToken(ctx context.Context, resetToken string) (*authEntities.User, error) {
	row, err := r.ORMRepository.FindOneBy(ctx, tmrepo.NewKwargs("password_reset_token", resetToken))
	if err != nil || row == nil {
		return nil, nil
	}
	u, err := authUserToDomain(row)
	if err != nil {
		return nil, nil
	}
	return u, nil
}

// ListAll is list_all: optional status filter, offset then limit; errors return [].
func (r *UserRepository) ListAll(ctx context.Context, limit, offset int, status *string) ([]*authEntities.User, error) {
	filters := tmrepo.NewKwargs()
	if status != nil {
		filters.Set("status", *status)
	}
	rows, err := r.ORMRepository.FindBy(ctx, filters)
	if err != nil {
		return []*authEntities.User{}, nil
	}
	out := []*authEntities.User{}
	for _, row := range rows {
		u, err := authUserToDomain(row)
		if err != nil {
			return []*authEntities.User{}, nil
		}
		out = append(out, u)
	}
	if offset > 0 {
		if offset >= len(out) {
			return []*authEntities.User{}, nil
		}
		out = out[offset:]
	}
	if limit >= 0 && limit < len(out) {
		out = out[:limit]
	}
	return out, nil
}

// Delete is delete; a missing row returns false (Python raises on driver errors).
func (r *UserRepository) Delete(ctx context.Context, userID string) (bool, error) {
	return r.ORMRepository.Delete(ctx, userID)
}

// ExistsByEmail is exists_by_email (email lowercased); errors return false.
func (r *UserRepository) ExistsByEmail(ctx context.Context, email string) (bool, error) {
	n, err := r.ORMRepository.Count(ctx, tmrepo.NewKwargs("email", tmvo.PyLower(email)))
	if err != nil {
		return false, nil
	}
	return n > 0, nil
}

// ExistsByUsername is exists_by_username; errors return false.
func (r *UserRepository) ExistsByUsername(ctx context.Context, username string) (bool, error) {
	n, err := r.ORMRepository.Count(ctx, tmrepo.NewKwargs("username", username))
	if err != nil {
		return false, nil
	}
	return n > 0, nil
}

// authUserLike mirrors ILIKE for a pattern built as %query% (% and _ are wildcards).
func authUserLike(pattern, value string) bool {
	var b strings.Builder
	b.WriteString("(?is)^")
	for i := 0; i < len(pattern); i++ {
		switch pattern[i] {
		case '%':
			b.WriteString(".*")
		case '_':
			b.WriteString(".")
		default:
			b.WriteString(regexp.QuoteMeta(string(pattern[i])))
		}
	}
	b.WriteString("$")
	re, err := regexp.Compile(b.String())
	if err != nil {
		return false
	}
	return re.MatchString(value)
}

// Search is search: ILIKE over email, username and full_name, limited; errors return [].
func (r *UserRepository) Search(ctx context.Context, query string, limit int) ([]*authEntities.User, error) {
	rows, err := r.ORMRepository.FindBy(ctx, nil)
	if err != nil {
		return []*authEntities.User{}, nil
	}
	pattern := "%" + query + "%"
	out := []*authEntities.User{}
	for _, row := range rows {
		if !authUserLike(pattern, row.Email) && !authUserLike(pattern, row.Username) &&
			(row.FullName == nil || !authUserLike(pattern, *row.FullName)) {
			continue
		}
		u, err := authUserToDomain(row)
		if err != nil {
			return []*authEntities.User{}, nil
		}
		out = append(out, u)
		if limit >= 0 && len(out) >= limit {
			break
		}
	}
	return out, nil
}
