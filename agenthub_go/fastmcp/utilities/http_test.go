package utilities

import (
	"net"
	"strconv"
	"testing"
)

func TestFindAvailablePortBindable(t *testing.T) {
	port, err := FindAvailablePort()
	if err != nil {
		t.Fatalf("FindAvailablePort: %v", err)
	}
	if port <= 0 || port > 65535 {
		t.Fatalf("port = %d, out of range", port)
	}
	l, err := net.Listen("tcp4", net.JoinHostPort("127.0.0.1", strconv.Itoa(port)))
	if err != nil {
		t.Fatalf("returned port not bindable: %v", err)
	}
	l.Close()
}
