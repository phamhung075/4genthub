package utils

import (
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

func withFixedNow(t *testing.T) {
	t.Helper()
	prev := now
	now = func() time.Time { return time.Date(2025, 1, 2, 3, 4, 5, 0, time.UTC) }
	t.Cleanup(func() { now = prev })
}

func mustGet(t *testing.T, d *entities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := d.Get(key)
	if !ok {
		t.Fatalf("missing key %q", key)
	}
	return v
}

func TestSuccess(t *testing.T) {
	withFixedNow(t)
	d := StandardResponseFormatter{}.Success(nil, nil)
	want := "status,message,data,timestamp,success"
	if got := join(d); got != want {
		t.Fatalf("keys: %s", got)
	}
	if mustGet(t, d, "status") != "success" || mustGet(t, d, "success") != true {
		t.Fatalf("values: %v", d)
	}
	if mustGet(t, d, "message") != "Operation completed successfully" {
		t.Fatalf("message: %v", mustGet(t, d, "message"))
	}
	if mustGet(t, d, "timestamp") != "2025-01-02T03:04:05+00:00" {
		t.Fatalf("timestamp: %v", mustGet(t, d, "timestamp"))
	}
	if mustGet(t, d, "data") != nil {
		t.Fatalf("data should be None: %v", mustGet(t, d, "data"))
	}
}

func TestErrorAndHelpers(t *testing.T) {
	withFixedNow(t)
	d := StandardResponseFormatter{}.Error(ErrorCodeValidation, "bad", nil)
	if mustGet(t, d, "error_code") != "VALIDATION_ERROR" || mustGet(t, d, "success") != false {
		t.Fatalf("error: %v", d)
	}
	details := mustGet(t, d, "details").(*entities.OrderedMap[any])
	if details.Len() != 0 {
		t.Fatalf("details should default to {}: %v", details)
	}

	notFound := StandardResponseFormatter{}.NotFound("Task", "")
	if mustGet(t, notFound, "message") != "Task not found" {
		t.Fatalf("not found: %v", mustGet(t, notFound, "message"))
	}
	nf := mustGet(t, notFound, "details").(*entities.OrderedMap[any])
	if mustGet(t, nf, "resource") != "Task" || mustGet(t, nf, "identifier") != "" {
		t.Fatalf("not found details: %v", nf)
	}

	withID := StandardResponseFormatter{}.NotFound("Task", "abc")
	if mustGet(t, withID, "message") != "Task not found with identifier: abc" {
		t.Fatalf("not found id: %v", mustGet(t, withID, "message"))
	}

	unauth := StandardResponseFormatter{}.Unauthorized(nil)
	if mustGet(t, unauth, "message") != "Authentication required" || mustGet(t, unauth, "error_code") != "UNAUTHORIZED" {
		t.Fatalf("unauthorized: %v", unauth)
	}
	forbidden := StandardResponseFormatter{}.Forbidden(nil)
	if mustGet(t, forbidden, "message") != "Access forbidden" || mustGet(t, forbidden, "error_code") != "FORBIDDEN" {
		t.Fatalf("forbidden: %v", forbidden)
	}

	ve := StandardResponseFormatter{}.ValidationError(map[string][]string{"name": {"required"}})
	ved := mustGet(t, ve, "details").(*entities.OrderedMap[any])
	errs := mustGet(t, ved, "validation_errors").(map[string][]string)
	if len(errs["name"]) != 1 || errs["name"][0] != "required" {
		t.Fatalf("validation errors: %v", errs)
	}
}

func TestWarning(t *testing.T) {
	withFixedNow(t)
	d := StandardResponseFormatter{}.Warning(nil, nil, nil)
	if mustGet(t, d, "status") != "warning" || mustGet(t, d, "success") != true {
		t.Fatalf("warning: %v", d)
	}
	w := mustGet(t, d, "warnings").([]string)
	if w == nil || len(w) != 0 {
		t.Fatalf("warnings default: %#v", w)
	}
	if mustGet(t, d, "message") != "Operation completed with warnings" {
		t.Fatalf("message: %v", mustGet(t, d, "message"))
	}
}

func TestPartial(t *testing.T) {
	withFixedNow(t)
	d := StandardResponseFormatter{}.Partial(nil, nil, 3, 4)
	progress := mustGet(t, d, "progress").(*entities.OrderedMap[any])
	pct := mustGet(t, progress, "percentage").(float64)
	if pct != 75.0 {
		t.Fatalf("percentage: %v", pct)
	}
	if mustGet(t, progress, "completed") != 3 || mustGet(t, progress, "total") != 4 {
		t.Fatalf("progress: %v", progress)
	}
	if mustGet(t, d, "status") != "partial" {
		t.Fatalf("status: %v", mustGet(t, d, "status"))
	}

	// total == 0 yields the int 0, not a float.
	zero := StandardResponseFormatter{}.Partial(nil, nil, 0, 0)
	zp := mustGet(t, zero, "progress").(*entities.OrderedMap[any])
	if v := mustGet(t, zp, "percentage"); v != 0 {
		t.Fatalf("zero percentage: %#v", v)
	}
}

func join(d *entities.OrderedMap[any]) string {
	keys := d.Keys()
	out := ""
	for i, k := range keys {
		if i > 0 {
			out += ","
		}
		out += k
	}
	return out
}
