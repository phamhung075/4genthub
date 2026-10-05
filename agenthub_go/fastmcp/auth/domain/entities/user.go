package entities

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// UserStatus is the user account status.
type UserStatus string

const (
	UserStatusActive              UserStatus = "active"
	UserStatusInactive            UserStatus = "inactive"
	UserStatusSuspended           UserStatus = "suspended"
	UserStatusPendingVerification UserStatus = "pending_verification"
)

// UserRole is the role of a user in the system.
type UserRole string

const (
	UserRoleAdmin     UserRole = "admin"
	UserRoleUser      UserRole = "user"
	UserRoleViewer    UserRole = "viewer"
	UserRoleDeveloper UserRole = "developer"
)

// User is the domain entity with the authentication business logic.
type User struct {
	base.BaseTimestampEntity

	Email        string
	Username     string
	PasswordHash string // never a plain password

	ID       *string
	FullName *string
	Status   UserStatus
	Roles    []UserRole

	EmailVerified       bool
	EmailVerifiedAt     *time.Time
	LastLoginAt         *time.Time
	FailedLoginAttempts int
	LockedUntil         *time.Time

	PasswordChangedAt    *time.Time
	PasswordResetToken   *string
	PasswordResetExpires *time.Time

	RefreshTokenFamily  *string
	RefreshTokenVersion int

	CreatedBy *string

	ProjectIDs       []string
	DefaultProjectID *string

	Metadata map[string]any
}

func now() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// NewUser applies the dataclass defaults (status pending_verification, roles [user],
// empty project ids and metadata; a non-nil empty Roles stays empty), initializes the
// timestamps and validates.
func NewUser(u User) (*User, error) {
	s := u
	if s.Status == "" {
		s.Status = UserStatusPendingVerification
	}
	if s.Roles == nil {
		s.Roles = []UserRole{UserRoleUser}
	}
	if s.ProjectIDs == nil {
		s.ProjectIDs = []string{}
	}
	if s.Metadata == nil {
		s.Metadata = map[string]any{}
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

// GetEntityID is `str(id) if id else "user:<username>"`.
func (u *User) GetEntityID() string {
	if u.ID != nil && *u.ID != "" {
		return *u.ID
	}
	return "user:" + u.Username
}

// isValidEmail is the basic check: an @ and a dot in the part after the first @.
func isValidEmail(email string) bool {
	if !strings.Contains(email, "@") {
		return false
	}
	return strings.Contains(strings.Split(email, "@")[1], ".")
}

// ValidateEntity ensures the user invariants hold.
func (u *User) ValidateEntity() error {
	if !isValidEmail(u.Email) {
		return value_objects.ValueErrorf("Invalid email format: %s", u.Email)
	}
	if value_objects.PyStrip(u.Username) == "" {
		return value_objects.ValueErrorf("Username cannot be empty")
	}
	return nil
}

// IsActive: active status, verified email and not locked.
func (u *User) IsActive() bool {
	return u.Status == UserStatusActive && u.EmailVerified && !u.IsLocked()
}

// IsLocked: the account is temporarily locked.
func (u *User) IsLocked() bool {
	if u.LockedUntil == nil {
		return false
	}
	return now().Before(*u.LockedUntil)
}

// CanLogin: not locked and not suspended.
func (u *User) CanLogin() bool { return !u.IsLocked() && u.Status != UserStatusSuspended }

// RecordFailedLogin counts a failed attempt; the 5th locks the account for 30 minutes.
func (u *User) RecordFailedLogin() error {
	u.FailedLoginAttempts++
	if err := u.Touch("failed_login_recorded"); err != nil {
		return err
	}
	if u.FailedLoginAttempts >= 5 {
		t := now().Add(30 * time.Minute)
		u.LockedUntil = &t
	}
	return nil
}

// RecordSuccessfulLogin resets the failure counter and the lock.
func (u *User) RecordSuccessfulLogin() error {
	u.FailedLoginAttempts = 0
	u.LockedUntil = nil
	t := now()
	u.LastLoginAt = &t
	return u.Touch("login_successful")
}

// VerifyEmail marks the email as verified and activates a pending account.
func (u *User) VerifyEmail() error {
	u.EmailVerified = true
	t := now()
	u.EmailVerifiedAt = &t
	if u.Status == UserStatusPendingVerification {
		u.Status = UserStatusActive
	}
	return u.Touch("email_verified")
}

// InitiatePasswordReset stores the reset token (Python default expiry: 24 hours).
func (u *User) InitiatePasswordReset(token string, expiresInHours int) error {
	u.PasswordResetToken = &token
	t := now().Add(time.Duration(expiresInHours) * time.Hour)
	u.PasswordResetExpires = &t
	return u.Touch("password_reset_initiated")
}

// CompletePasswordReset sets the new hash and invalidates all refresh tokens.
func (u *User) CompletePasswordReset(newPasswordHash string) error {
	u.PasswordHash = newPasswordHash
	u.PasswordResetToken = nil
	u.PasswordResetExpires = nil
	t := now()
	u.PasswordChangedAt = &t
	u.RefreshTokenVersion++
	return u.Touch("password_reset_completed")
}

// ChangePassword sets the new hash and invalidates all refresh tokens.
func (u *User) ChangePassword(newPasswordHash string) error {
	u.PasswordHash = newPasswordHash
	t := now()
	u.PasswordChangedAt = &t
	u.RefreshTokenVersion++
	return u.Touch("password_changed")
}

func (u *User) HasRole(role UserRole) bool {
	for _, r := range u.Roles {
		if r == role {
			return true
		}
	}
	return false
}

func (u *User) AddRole(role UserRole) error {
	if u.HasRole(role) {
		return nil
	}
	u.Roles = append(u.Roles, role)
	return u.Touch("role_added")
}

func (u *User) RemoveRole(role UserRole) error {
	for i, r := range u.Roles {
		if r == role {
			u.Roles = append(u.Roles[:i:i], u.Roles[i+1:]...)
			return u.Touch("role_removed")
		}
	}
	return nil
}

func (u *User) Suspend() error {
	u.Status = UserStatusSuspended
	return u.Touch("account_suspended")
}

func (u *User) Activate() error {
	u.Status = UserStatusActive
	return u.Touch("account_activated")
}

func (u *User) Deactivate() error {
	u.Status = UserStatusInactive
	return u.Touch("account_deactivated")
}

func isoOrNil(t *time.Time) any {
	if t == nil {
		return nil
	}
	return value_objects.IsoFormat(*t)
}

// ToDict excludes sensitive data (password hash, tokens, security fields).
func (u *User) ToDict() *entities.OrderedMap[any] {
	roles := make([]any, len(u.Roles))
	for i, r := range u.Roles {
		roles[i] = string(r)
	}
	d := entities.NewOrderedMap[any]()
	var id, fullName, defaultProject any
	if u.ID != nil {
		id = *u.ID
	}
	if u.FullName != nil {
		fullName = *u.FullName
	}
	if u.DefaultProjectID != nil {
		defaultProject = *u.DefaultProjectID
	}
	d.Set("id", id)
	d.Set("email", u.Email)
	d.Set("username", u.Username)
	d.Set("full_name", fullName)
	d.Set("status", string(u.Status))
	d.Set("roles", roles)
	d.Set("email_verified", u.EmailVerified)
	d.Set("email_verified_at", isoOrNil(u.EmailVerifiedAt))
	d.Set("last_login_at", isoOrNil(u.LastLoginAt))
	d.Set("created_at", isoOrNil(u.CreatedAt))
	d.Set("updated_at", isoOrNil(u.UpdatedAt))
	d.Set("project_ids", u.ProjectIDs)
	d.Set("default_project_id", defaultProject)
	d.Set("metadata", u.Metadata)
	return d
}

var userFields = map[string]bool{
	"email": true, "username": true, "password_hash": true, "id": true, "full_name": true, "status": true,
	"roles": true, "email_verified": true, "email_verified_at": true, "last_login_at": true,
	"failed_login_attempts": true, "locked_until": true, "password_changed_at": true,
	"password_reset_token": true, "password_reset_expires": true, "refresh_token_family": true,
	"refresh_token_version": true, "created_by": true, "project_ids": true, "default_project_id": true,
	"metadata": true, "created_at": true, "updated_at": true,
}

func typeMismatch(field, want string) error {
	return value_objects.TypeErrorf("User field %s must be %s", field, want)
}

// UserFromDict is User.from_dict: ISO date strings and the status / role strings are
// parsed, then the user is built from the remaining fields (an unknown key is a
// TypeError like Python's unexpected keyword argument).
func UserFromDict(data map[string]any) (*User, error) {
	var unknown []string
	for k := range data {
		if !userFields[k] {
			unknown = append(unknown, k)
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, value_objects.TypeErrorf("User.__init__() got an unexpected keyword argument '%s'", unknown[0])
	}

	var u User
	str := func(k string, dst *string) error {
		if v, ok := data[k]; ok {
			s, isStr := v.(string)
			if !isStr {
				return typeMismatch(k, "a string")
			}
			*dst = s
		}
		return nil
	}
	optStr := func(k string, dst **string) error {
		if v, ok := data[k]; ok && v != nil {
			s, isStr := v.(string)
			if !isStr {
				return typeMismatch(k, "a string")
			}
			*dst = &s
		}
		return nil
	}
	optTime := func(k string, dst **time.Time) error {
		v, ok := data[k]
		if !ok || !value_objects.PyTruthy(v) {
			return nil
		}
		switch x := v.(type) {
		case string:
			t, err := value_objects.ParseISO(x)
			if err != nil {
				return err
			}
			*dst = &t
		case time.Time:
			*dst = &x
		default:
			return typeMismatch(k, "a datetime or ISO string")
		}
		return nil
	}
	intField := func(k string, dst *int) error {
		if v, ok := data[k]; ok {
			switch n := v.(type) {
			case int:
				*dst = n
			case int64:
				*dst = int(n)
			case float64:
				*dst = int(n)
			default:
				return typeMismatch(k, "an integer")
			}
		}
		return nil
	}
	for _, step := range []error{
		str("email", &u.Email), str("username", &u.Username), str("password_hash", &u.PasswordHash),
		optStr("id", &u.ID), optStr("full_name", &u.FullName),
		optStr("password_reset_token", &u.PasswordResetToken), optStr("refresh_token_family", &u.RefreshTokenFamily),
		optStr("created_by", &u.CreatedBy), optStr("default_project_id", &u.DefaultProjectID),
		optTime("email_verified_at", &u.EmailVerifiedAt), optTime("last_login_at", &u.LastLoginAt),
		optTime("locked_until", &u.LockedUntil), optTime("password_changed_at", &u.PasswordChangedAt),
		optTime("password_reset_expires", &u.PasswordResetExpires),
		optTime("created_at", &u.CreatedAt), optTime("updated_at", &u.UpdatedAt),
		intField("failed_login_attempts", &u.FailedLoginAttempts), intField("refresh_token_version", &u.RefreshTokenVersion),
	} {
		if step != nil {
			return nil, step
		}
	}
	if v, ok := data["email_verified"]; ok {
		u.EmailVerified = value_objects.PyTruthy(v)
	}
	if v, ok := data["status"]; ok {
		s, isStr := v.(string)
		if !isStr {
			return nil, typeMismatch("status", "a string")
		}
		switch UserStatus(s) {
		case UserStatusActive, UserStatusInactive, UserStatusSuspended, UserStatusPendingVerification:
			u.Status = UserStatus(s)
		default:
			return nil, value_objects.ValueErrorf("%s is not a valid UserStatus", value_objects.PyRepr(s))
		}
	}
	if v, ok := data["roles"]; ok {
		list, isList := v.([]any)
		if !isList {
			return nil, typeMismatch("roles", "a list")
		}
		u.Roles = []UserRole{}
		for _, r := range list {
			s, isStr := r.(string)
			if !isStr {
				return nil, typeMismatch("roles", "a list of strings")
			}
			switch UserRole(s) {
			case UserRoleAdmin, UserRoleUser, UserRoleViewer, UserRoleDeveloper:
				u.Roles = append(u.Roles, UserRole(s))
			default:
				return nil, value_objects.ValueErrorf("%s is not a valid UserRole", value_objects.PyRepr(s))
			}
		}
	}
	if v, ok := data["project_ids"]; ok {
		list, isList := v.([]any)
		if !isList {
			return nil, typeMismatch("project_ids", "a list")
		}
		u.ProjectIDs = []string{}
		for _, p := range list {
			u.ProjectIDs = append(u.ProjectIDs, fmt.Sprint(p))
		}
	}
	if v, ok := data["metadata"]; ok {
		m, isMap := v.(map[string]any)
		if !isMap {
			return nil, typeMismatch("metadata", "a dict")
		}
		u.Metadata = m
	}
	return NewUser(u)
}
