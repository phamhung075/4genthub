package entities

import (
	"agenthub/fastmcp/task_management/domain/value_objects"
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"regexp"
	"strings"
	"testing"
)

var isoRe = regexp.MustCompile(`^\d{4}-\d\d-\d\dT`)

// norm replaces clock-derived timestamps (Python's real clock) by a placeholder; the
// fixtures use 1999 for every date they provide.
func norm(v any) any {
	switch x := v.(type) {
	case string:
		if isoRe.MatchString(x) && !strings.HasPrefix(x, "1999-") {
			return "<ts>"
		}
	case map[string]any:
		for k := range x {
			x[k] = norm(x[k])
		}
	case []any:
		for i := range x {
			x[i] = norm(x[i])
		}
	}
	return v
}

func dump(t *testing.T, u *User) any {
	t.Helper()
	b, err := jsonOf(u)
	if err != nil {
		t.Fatal(err)
	}
	var d map[string]any
	if err := json.Unmarshal(b, &d); err != nil {
		t.Fatal(err)
	}
	d["__failed"] = float64(u.FailedLoginAttempts)
	d["__locked"] = u.IsLocked()
	d["__rtv"] = float64(u.RefreshTokenVersion)
	d["__hash"] = u.PasswordHash
	if u.PasswordResetToken != nil {
		d["__reset_token"] = *u.PasswordResetToken
	} else {
		d["__reset_token"] = nil
	}
	d["__reset_exp"] = u.PasswordResetExpires != nil
	d["__pwchg"] = u.PasswordChangedAt != nil
	d["__locked_until"] = u.LockedUntil != nil
	d["__active"] = u.IsActive()
	d["__can_login"] = u.CanLogin()
	d["__entity_id"] = u.GetEntityID()
	var has []any
	for _, r := range []UserRole{UserRoleAdmin, UserRoleUser, UserRoleViewer, UserRoleDeveloper} {
		has = append(has, u.HasRole(r))
	}
	d["__roles_has"] = has
	return norm(d)
}

func jsonOf(u *User) ([]byte, error) {
	s, err := pyDumps(u.ToDict())
	return []byte(s), err
}

func TestUserParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/user_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var fx struct {
		Specs map[string]map[string]any `json:"specs"`
		Cases []struct {
			Spec  string                     `json:"spec"`
			Ops   [][]any                    `json:"ops"`
			Init  *struct{ Exc, Msg string } `json:"init"`
			Steps []any                      `json:"steps"`
		} `json:"cases"`
	}
	if err := json.Unmarshal(raw, &fx); err != nil {
		t.Fatal(err)
	}
	for ci, c := range fx.Cases {
		label := fmt.Sprintf("#%d %s %v", ci, c.Spec, c.Ops)
		spec := map[string]any{}
		for k, v := range fx.Specs[c.Spec] {
			spec[k] = v
		}
		u, err := UserFromDict(spec)
		if c.Init != nil {
			if err == nil || err.Error() != c.Init.Msg {
				t.Errorf("%s: init err %v, want %q", label, err, c.Init.Msg)
			}
			continue
		}
		if err != nil {
			t.Fatalf("%s: %v", label, err)
		}
		check := func(step int) {
			got := dump(t, u)
			var want any = c.Steps[step]
			if !reflect.DeepEqual(got, want) {
				t.Errorf("%s step %d:\n got  %v\n want %v", label, step, got, want)
			}
		}
		check(0)
		for i, op := range c.Ops {
			var err error
			switch op[0].(string) {
			case "fail":
				err = u.RecordFailedLogin()
			case "success":
				err = u.RecordSuccessfulLogin()
			case "verify":
				err = u.VerifyEmail()
			case "reset":
				err = u.InitiatePasswordReset(op[1].(string), int(op[2].(float64)))
			case "complete":
				err = u.CompletePasswordReset(op[1].(string))
			case "change":
				err = u.ChangePassword(op[1].(string))
			case "add":
				err = u.AddRole(UserRole(op[1].(string)))
			case "remove":
				err = u.RemoveRole(UserRole(op[1].(string)))
			case "suspend":
				err = u.Suspend()
			case "activate":
				err = u.Activate()
			case "deactivate":
				err = u.Deactivate()
			}
			if err != nil {
				t.Fatalf("%s op %v: %v", label, op, err)
			}
			check(i + 1)
		}
	}
}

func pyDumps(v any) (string, error) { return value_objects.PyJSONDumps(v, -1) }
