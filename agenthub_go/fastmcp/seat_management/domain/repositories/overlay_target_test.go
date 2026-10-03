package repositories

import "testing"

func TestOverlayValidateTarget(t *testing.T) {
	cases := []struct {
		name    string
		overlay Overlay
		ok      bool
	}{
		{"company", Overlay{Scope: ScopeCompany}, true},
		{"company with room", Overlay{Scope: ScopeCompany, RoomID: "r"}, false},
		{"room", Overlay{Scope: ScopeRoom, RoomID: "r"}, true},
		{"room with seat", Overlay{Scope: ScopeRoom, RoomID: "r", SeatID: "s"}, false},
		{"room without room", Overlay{Scope: ScopeRoom}, false},
		{"seat", Overlay{Scope: ScopeSeat, SeatID: "s"}, true},
		{"seat with room", Overlay{Scope: ScopeSeat, RoomID: "r", SeatID: "s"}, false},
		{"seat without seat", Overlay{Scope: ScopeSeat}, false},
		{"unknown scope", Overlay{Scope: "team"}, false},
	}
	for _, c := range cases {
		if err := c.overlay.ValidateTarget(); (err == nil) != c.ok {
			t.Errorf("%s: err = %v, want ok=%v", c.name, err, c.ok)
		}
	}
}
