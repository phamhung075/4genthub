package dtos

import "testing"

func TestConnectionRequestDefaults(t *testing.T) {
	if r := NewHealthCheckRequest(nil); !r.IncludeDetails {
		t.Fatalf("health check include_details = %v", r.IncludeDetails)
	}
	f := false
	if r := NewHealthCheckRequest(&f); r.IncludeDetails {
		t.Fatalf("health check override = %v", r.IncludeDetails)
	}
	if r := NewServerCapabilitiesRequest(nil); !r.IncludeDetails {
		t.Fatalf("capabilities include_details = %v", r.IncludeDetails)
	}
	if r := NewConnectionHealthRequest(nil, nil); !r.IncludeDetails || r.ConnectionID != nil {
		t.Fatalf("connection health = %+v", r)
	}
	if r := NewServerStatusRequest(nil); !r.IncludeDetails {
		t.Fatalf("server status include_details = %v", r.IncludeDetails)
	}
}

func TestConnectionResponseFields(t *testing.T) {
	r := &HealthCheckResponse{Success: true, Status: "ok", ServerName: "s", Version: "1", UptimeSeconds: 1.5}
	if r.Timestamp != 0 || r.Error != nil {
		t.Fatalf("health = %+v", r)
	}
}
