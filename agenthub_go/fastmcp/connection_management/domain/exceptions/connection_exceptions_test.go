package exceptions

import (
	"errors"
	"testing"

	"agenthub/fastmcp/connection_management/domain/internal/testutil"
)

func TestConnectionExceptionsMatchPython(t *testing.T) {
	cases := testutil.Load(t, "testdata/exceptions_cases.json").([]any)
	build := map[string]func(a []any) error{
		"ServerNotFoundError":              func(a []any) error { return NewServerNotFoundError(a[0].(string)) },
		"ConnectionNotFoundError":          func(a []any) error { return NewConnectionNotFoundError(a[0].(string)) },
		"InvalidServerStatusError":         func(a []any) error { return NewInvalidServerStatusError(a[0].(string)) },
		"InvalidConnectionStatusError":     func(a []any) error { return NewInvalidConnectionStatusError(a[0].(string)) },
		"ServerHealthCheckFailedError":     func(a []any) error { return NewServerHealthCheckFailedError(a[0].(string)) },
		"ConnectionHealthCheckFailedError": func(a []any) error { return NewConnectionHealthCheckFailedError(a[0].(string), a[1].(string)) },
		"StatusBroadcastError":             func(a []any) error { return NewStatusBroadcastError(a[0].(string)) },
	}
	for _, c := range cases {
		row := c.([]any)
		err := build[row[0].(string)](row[1].([]any))
		if err.Error() != row[2].(string) {
			t.Fatalf("%v: %q want %q", row[0], err.Error(), row[2])
		}
		var base *ConnectionError
		if !errors.As(err, &base) {
			t.Fatalf("%v must be a ConnectionError", row[0])
		}
	}
}
