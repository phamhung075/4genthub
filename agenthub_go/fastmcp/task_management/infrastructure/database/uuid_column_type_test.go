package database_test

import (
	"errors"
	"os"
	"testing"

	"agenthub/fastmcp/task_management/domain"
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

type obj = *entities.OrderedMap[any]

func field(v any, k string) any { x, _ := v.(obj).Get(k); return x }

func load(t *testing.T) obj {
	raw, err := os.ReadFile("testdata/uuid_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	v, err := entities.DecodeJSON(raw)
	if err != nil {
		t.Fatal(err)
	}
	return v.(obj)
}

// result renders {"ok": v} / {"exc": type, "msg": text}; TypeError and ValueError keep their text.
func result(v any, err error) any {
	m := entities.NewOrderedMap[any]()
	if err == nil {
		m.Set("ok", v)
		return m
	}
	var te *tmvo.TypeError
	switch {
	case errors.As(err, &te):
		m.Set("exc", "TypeError")
	default:
		m.Set("exc", "ValueError")
	}
	m.Set("msg", err.Error())
	return m
}

func canon(t *testing.T, v any) string {
	s, err := tmvo.PyJSONDumps(v, -1)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

type valueObject struct{ tmvo.EntityId }

func TestUnifiedUUIDParity(t *testing.T) {
	for i, c := range field(load(t), "bind").([]any) {
		kind := field(c, "kind").(string)
		var got any
		switch kind {
		case "normalize":
			s, err := database.NormalizeUserIDToUUID(field(c, "value").(string))
			got = result(s, err)
			if g, w := canon(t, got), canon(t, field(c, "norm")); g != w {
				t.Fatalf("case %d normalize %q: got %s want %s", i, field(c, "value"), g, w)
			}
			continue
		case "str":
			v, err := database.UnifiedUUIDBindParam(field(c, "value"), field(c, "dialect").(string))
			got = result(v, err)
		case "vo":
			v, err := database.UnifiedUUIDBindParam(valueObject{tmvo.EntityId{Value: field(c, "value").(string)}}, field(c, "dialect").(string))
			got = result(v, err)
		default:
			v, err := database.UnifiedUUIDBindParam(field(c, "value"), "postgresql")
			got = result(v, err)
		}
		if g, w := canon(t, got), canon(t, field(c, "bind")); g != w {
			t.Fatalf("case %d %s %q (%v): got %s want %s", i, kind, field(c, "value"), field(c, "dialect"), g, w)
		}
	}
}

func TestUuid5Parity(t *testing.T) {
	for _, c := range field(load(t), "uuid5").([]any) {
		if got, want := database.Uuid5(database.UserIDNamespace, field(c, "name").(string)), field(c, "uuid5"); got != want {
			t.Errorf("uuid5(%q) = %s, want %v", field(c, "name"), got, want)
		}
	}
}

func TestInitRegistersNormalizer(t *testing.T) {
	if err := domain.AssertUserIDNormalizerRegistered(); err != nil {
		t.Fatal(err)
	}
	id := "test-user-123"
	got, err := domain.ValidateUserID(&id, "")
	if err != nil || got != database.Uuid5(database.UserIDNamespace, id) {
		t.Fatalf("ValidateUserID = %q, %v", got, err)
	}
}
