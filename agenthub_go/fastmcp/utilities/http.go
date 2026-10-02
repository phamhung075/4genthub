package utilities

import "net"

// FindAvailablePort mirrors utilities.http.find_available_port: bind 127.0.0.1:0 and
// return the OS-assigned port. Python raises OSError on failure; Go returns the error.
func FindAvailablePort() (int, error) {
	l, err := net.Listen("tcp4", "127.0.0.1:0")
	if err != nil {
		return 0, err
	}
	defer l.Close()
	addr, ok := l.Addr().(*net.TCPAddr)
	if !ok {
		return 0, &net.AddrError{Err: "unexpected address type", Addr: l.Addr().String()}
	}
	return addr.Port, nil
}
