package metrics

import (
	"reflect"
	"testing"
)

func resetMetrics() {
	wsMetricsMu.Lock()
	defer wsMetricsMu.Unlock()
	wsConnectionGauge = map[string]float64{"active": 0, "authenticated": 0, "unauthenticated": 0}
	wsMessageQueueSize = map[string]float64{}
	wsMessageQueueMaxSize = map[string]float64{}
	wsMessageRetriesTotal = map[string]float64{}
	wsMessageDeliveryCount = map[string]float64{}
	wsMessageDeliverySum = map[string]float64{}
	wsBroadcastDurationCount = map[string]float64{}
	wsBroadcastDurationSum = map[string]float64{}
}

func TestUpdateConnectionCount(t *testing.T) {
	resetMetrics()
	UpdateConnectionCount(3, 2, 1)
	if wsConnectionGauge["active"] != 3 || wsConnectionGauge["authenticated"] != 2 || wsConnectionGauge["unauthenticated"] != 1 {
		t.Fatalf("gauge = %v", wsConnectionGauge)
	}
}

func TestUpdateQueueSizeTracksMax(t *testing.T) {
	resetMetrics()
	UpdateQueueSize("user-1", 5)
	UpdateQueueSize("user-1", 3)
	UpdateQueueSize("user-1", 10)
	if wsMessageQueueSize["user-1"] != 10 {
		t.Errorf("size = %v", wsMessageQueueSize["user-1"])
	}
	if wsMessageQueueMaxSize["user-1"] != 10 {
		t.Errorf("max = %v", wsMessageQueueMaxSize["user-1"])
	}
	ClearQueueMetrics("user-1")
	if wsMessageQueueSize["user-1"] != 0 {
		t.Errorf("cleared size = %v", wsMessageQueueSize["user-1"])
	}
}

func TestGetMetricsSummary(t *testing.T) {
	resetMetrics()
	UpdateConnectionCount(3, 2, 1)
	RecordRetryAttempt(true, 1)
	RecordRetryAttempt(true, 1)
	RecordRetryAttempt(false, 2)

	summary := GetMetricsSummary()
	wantKeys := []string{"active_connections", "authenticated_connections", "total_retries"}
	if !reflect.DeepEqual(summary.Keys(), wantKeys) {
		t.Fatalf("keys = %v, want %v", summary.Keys(), wantKeys)
	}
	if v, _ := summary.Get("active_connections"); v != float64(3) {
		t.Errorf("active_connections = %v", v)
	}
	if v, _ := summary.Get("authenticated_connections"); v != float64(2) {
		t.Errorf("authenticated_connections = %v", v)
	}
	if v, _ := summary.Get("total_retries"); v != float64(3) {
		t.Errorf("total_retries = %v", v)
	}
}

func TestTrackBroadcastDuration(t *testing.T) {
	resetMetrics()
	stop := TrackBroadcastDuration("created", "task")
	stop()
	if wsBroadcastDurationCount["created\x00task"] != 1 {
		t.Errorf("count = %v", wsBroadcastDurationCount["created\x00task"])
	}
	if wsBroadcastDurationSum["created\x00task"] < 0 {
		t.Errorf("sum = %v", wsBroadcastDurationSum["created\x00task"])
	}
}
