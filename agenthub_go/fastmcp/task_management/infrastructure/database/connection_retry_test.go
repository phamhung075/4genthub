package database_test

import (
	"encoding/json"
	"errors"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

type retryCases struct {
	Retry []struct {
		Kind string
		Msg  string
		Want bool
	}
	Delay []struct {
		Max     int
		Init    float64
		Maxd    float64
		Base    float64
		Attempt int
		Want    float64
	}
}

func TestRetryParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/retry_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var c retryCases
	if err := json.Unmarshal(raw, &c); err != nil {
		t.Fatal(err)
	}
	for _, r := range c.Retry {
		var e error
		switch r.Kind {
		case "op", "psy":
			e = &database.OperationalError{Msg: r.Msg}
		case "pool":
			e = &database.PoolTimeoutError{Msg: r.Msg}
		default:
			e = errors.New(r.Msg)
		}
		if got := database.IsRetryableError(e); got != r.Want {
			t.Errorf("%s %q: got %v want %v", r.Kind, r.Msg, got, r.Want)
		}
	}
	for _, d := range c.Delay {
		cfg := database.ConnectionRetryConfig{MaxRetries: d.Max, InitialDelay: d.Init, MaxDelay: d.Maxd, ExponentialBase: d.Base}
		if got := database.CalculateDelay(d.Attempt, cfg, nil); got != d.Want {
			t.Errorf("delay %v: got %v want %v", d, got, d.Want)
		}
	}
}

func TestWithConnectionRetry(t *testing.T) {
	var slept []time.Duration
	calls := 0
	cfg := database.ConnectionRetryConfig{MaxRetries: 3, InitialDelay: 1, MaxDelay: 30, ExponentialBase: 2}
	v, err := database.WithConnectionRetry(cfg, func(d time.Duration) { slept = append(slept, d) }, func() (int, error) {
		calls++
		if calls < 3 {
			return 0, &database.OperationalError{Msg: "connection refused"}
		}
		return 7, nil
	})
	if err != nil || v != 7 || len(slept) != 2 || slept[0] != time.Second || slept[1] != 2*time.Second {
		t.Fatalf("v=%d err=%v slept=%v", v, err, slept)
	}
	calls = 0
	_, err = database.WithConnectionRetry(cfg, func(time.Duration) {}, func() (int, error) { calls++; return 0, errors.New("boom") })
	if err == nil || calls != 1 {
		t.Fatalf("non-retryable: calls=%d err=%v", calls, err)
	}
	calls = 0
	_, err = database.WithConnectionRetry(cfg, func(time.Duration) {}, func() (int, error) { calls++; return 0, &database.OperationalError{Msg: "timeout"} })
	if err == nil || calls != 4 {
		t.Fatalf("exhausted: calls=%d err=%v", calls, err)
	}
}
