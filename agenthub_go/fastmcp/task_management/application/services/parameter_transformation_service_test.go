package services

import (
	"math"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func zpAParameterOrdered(t *testing.T, pairs ...any) *entities.OrderedMap[any] {
	t.Helper()
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(pairs); i += 2 {
		m.Set(pairs[i].(string), pairs[i+1])
	}
	return m
}

func TestParameterTransformationService_TransformStringToList(t *testing.T) {
	svc := ParameterTransformationService{}

	if got := svc.TransformStringToList(nil, "assignees"); got != nil {
		t.Fatalf("None = %v, want nil", got)
	}

	list := []any{"a", "b"}
	got := svc.TransformStringToList(list, "assignees")
	if len(got) != 2 || got[0] != "a" || got[1] != "b" {
		t.Fatalf("list = %v, want [a b]", got)
	}

	if got := svc.TransformStringToList("   ", "assignees"); got != nil {
		t.Fatalf("blank = %v, want nil", got)
	}

	got = svc.TransformStringToList(" a, b ,,c ", "assignees")
	if len(got) != 3 || got[0] != "a" || got[1] != "b" || got[2] != "c" {
		t.Fatalf("csv = %v, want [a b c]", got)
	}

	got = svc.TransformStringToList(" single ", "assignees")
	if len(got) != 1 || got[0] != "single" {
		t.Fatalf("single = %v, want [single]", got)
	}

	empty := []any{}
	got = svc.TransformStringToList(empty, "assignees")
	if got == nil || len(got) != 0 {
		t.Fatalf("empty list = %v, want non-nil empty", got)
	}

	if got := svc.TransformStringToList(123, "assignees"); got != nil {
		t.Fatalf("int = %v, want nil", got)
	}
}

func TestParameterTransformationService_TransformToInteger(t *testing.T) {
	svc := ParameterTransformationService{}

	if got := svc.TransformToInteger(nil, 9, "count"); got != 9 {
		t.Fatalf("None = %d, want 9", got)
	}
	if got := svc.TransformToInteger(5, 9, "count"); got != 5 {
		t.Fatalf("int = %d, want 5", got)
	}
	if got := svc.TransformToInteger(true, 9, "count"); got != 1 {
		t.Fatalf("true = %d, want 1", got)
	}
	if got := svc.TransformToInteger(false, 9, "count"); got != 0 {
		t.Fatalf("false = %d, want 0", got)
	}
	if got := svc.TransformToInteger(3.9, 9, "count"); got != 3 {
		t.Fatalf("3.9 = %d, want 3", got)
	}
	if got := svc.TransformToInteger(-3.9, 9, "count"); got != -3 {
		t.Fatalf("-3.9 = %d, want -3", got)
	}
	if got := svc.TransformToInteger("42", 9, "count"); got != 42 {
		t.Fatalf("\"42\" = %d, want 42", got)
	}
	if got := svc.TransformToInteger(" 1_000 ", 9, "count"); got != 1000 {
		t.Fatalf("\" 1_000 \" = %d, want 1000", got)
	}
	if got := svc.TransformToInteger("abc", 9, "count"); got != 9 {
		t.Fatalf("\"abc\" = %d, want 9", got)
	}
	if got := svc.TransformToInteger(math.NaN(), 9, "count"); got != 9 {
		t.Fatalf("NaN = %d, want 9", got)
	}
	if got := svc.TransformToInteger([]any{}, 9, "count"); got != 9 {
		t.Fatalf("list = %d, want 9", got)
	}
}

func TestParameterTransformationService_ValidateProgressPercentage(t *testing.T) {
	svc := ParameterTransformationService{}

	if value, errMsg := svc.ValidateProgressPercentage(nil); value != nil || errMsg != nil {
		t.Fatalf("None = (%v, %v), want (nil, nil)", value, errMsg)
	}

	value, errMsg := svc.ValidateProgressPercentage(50)
	if value == nil || *value != 50 || errMsg != nil {
		t.Fatalf("50 = (%v, %v), want (50, nil)", value, errMsg)
	}

	value, errMsg = svc.ValidateProgressPercentage("50")
	if value == nil || *value != 50 || errMsg != nil {
		t.Fatalf("\"50\" = (%v, %v), want (50, nil)", value, errMsg)
	}

	value, errMsg = svc.ValidateProgressPercentage(true)
	if value == nil || *value != 1 || errMsg != nil {
		t.Fatalf("true = (%v, %v), want (1, nil)", value, errMsg)
	}

	value, errMsg = svc.ValidateProgressPercentage(150)
	if value != nil || errMsg == nil {
		t.Fatalf("150 = (%v, %v), want (nil, error)", value, errMsg)
	}
	wantPrefix := "progress_percentage must be an integer between 0 and 100: "
	if !strings.HasPrefix(*errMsg, wantPrefix) {
		t.Fatalf("error = %q, want prefix %q", *errMsg, wantPrefix)
	}
	if *errMsg != wantPrefix+"Progress percentage must be between 0 and 100, got 150" {
		t.Fatalf("error = %q", *errMsg)
	}

	value, errMsg = svc.ValidateProgressPercentage(-1)
	if value != nil || errMsg == nil {
		t.Fatalf("-1 = (%v, %v), want (nil, error)", value, errMsg)
	}
}

func TestParameterTransformationService_TransformBooleanDefault(t *testing.T) {
	svc := ParameterTransformationService{}
	if got := svc.TransformBooleanDefault(nil, true); got != true {
		t.Fatalf("None = %v, want true", got)
	}
	yes := true
	no := false
	if got := svc.TransformBooleanDefault(&yes, false); got != true {
		t.Fatalf("&true = %v", got)
	}
	if got := svc.TransformBooleanDefault(&no, true); got != false {
		t.Fatalf("&false = %v", got)
	}
}

func TestParameterTransformationService_TransformMultipleFields(t *testing.T) {
	svc := ParameterTransformationService{}

	kwargs := zpAParameterOrdered(t,
		"assignees", " a, b , ",
		"count", "7",
		"progress", 150,
		"flag", nil,
		"ratio", "bad",
		"keep", "untouched",
	)
	configs := entities.NewOrderedMap[any]()
	configs.Set("assignees", zpAParameterOrdered(t, "type", "list"))
	configs.Set("count", zpAParameterOrdered(t, "type", "integer"))
	configs.Set("progress", zpAParameterOrdered(t, "type", "percentage"))
	configs.Set("flag", zpAParameterOrdered(t, "type", "boolean"))
	configs.Set("ratio", zpAParameterOrdered(t, "type", "integer", "default", 3))
	// A field not present in kwargs is skipped.
	configs.Set("missing", zpAParameterOrdered(t, "type", "list"))

	result := svc.TransformMultipleFields(kwargs, configs)

	assignees, _ := result.Get("assignees")
	list, ok := assignees.([]any)
	if !ok || len(list) != 2 || list[0] != "a" || list[1] != "b" {
		t.Fatalf("assignees = %v, want [a b]", assignees)
	}
	if v, _ := result.Get("count"); v != 7 {
		t.Fatalf("count = %v, want 7", v)
	}
	if v, ok := result.Get("progress"); !ok || v != nil {
		t.Fatalf("progress = %v, want nil", v)
	}
	errValue, _ := result.Get("progress_error")
	if errValue == nil || !strings.HasPrefix(errValue.(string), "progress_percentage must be an integer between 0 and 100: ") {
		t.Fatalf("progress_error = %v", errValue)
	}
	if v, _ := result.Get("flag"); v != false {
		t.Fatalf("flag = %v, want false", v)
	}
	if v, _ := result.Get("ratio"); v != 3 {
		t.Fatalf("ratio = %v, want 3", v)
	}
	if v, _ := result.Get("keep"); v != "untouched" {
		t.Fatalf("keep = %v, want untouched", v)
	}
	if result.Has("missing") {
		t.Fatalf("missing should be skipped")
	}
}

func TestParameterTransformationService_TransformMultipleFields_PercentageNone(t *testing.T) {
	svc := ParameterTransformationService{}
	kwargs := zpAParameterOrdered(t, "progress", nil)
	configs := entities.NewOrderedMap[any]()
	configs.Set("progress", zpAParameterOrdered(t, "type", "percentage"))

	result := svc.TransformMultipleFields(kwargs, configs)
	if v, ok := result.Get("progress"); !ok || v != nil {
		t.Fatalf("progress = %v, want nil", v)
	}
	if result.Has("progress_error") {
		t.Fatalf("progress_error should not be set")
	}
}
