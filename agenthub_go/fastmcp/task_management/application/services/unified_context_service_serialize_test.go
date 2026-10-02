package services

import (
	"testing"
	"time"
)

func TestSerializeForJSONDatetimeUsesPythonStr(t *testing.T) {
	s := &UnifiedContextService{}
	ts := time.Date(2026, 10, 2, 15, 0, 0, 123000, time.UTC)
	if got := s.serializeForJSON(ts); got != "2026-10-02 15:00:00.000123+00:00" {
		t.Fatalf("got %v", got)
	}
}
