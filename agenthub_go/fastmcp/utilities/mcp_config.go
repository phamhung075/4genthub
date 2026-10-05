package utilities

import (
	"net/netip"
	"regexp"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Transport type literals.
const (
	TransportStreamableHTTP = "streamable-http"
	TransportSSE            = "sse"
)

// InferTransportTypeFromURL mirrors infer_transport_type_from_url. Python parses the URL
// and searches /sse(/|\?|&|$) in the path (so ? and & can only appear inside a raw path).
func InferTransportTypeFromURL(url string) (string, error) {
	if !strings.HasPrefix(url, "http") {
		return "", value_objects.ValueErrorf("Invalid URL: %s", url)
	}
	path, err := pyURLPath(url)
	if err != nil {
		return "", err
	}
	for i := 0; ; {
		j := strings.Index(path[i:], "/sse")
		if j < 0 {
			return TransportStreamableHTTP, nil
		}
		k := i + j + len("/sse")
		if k == len(path) || path[k] == '/' || path[k] == '?' || path[k] == '&' {
			return TransportSSE, nil
		}
		i += j + 1
	}
}

// StdioMCPServer mirrors StdioMCPServer.
type StdioMCPServer struct {
	Command   string
	Args      []string
	Env       *entities.OrderedMap[any]
	Cwd       *string
	Transport string
}

// RemoteMCPServer mirrors RemoteMCPServer.
type RemoteMCPServer struct {
	URL       string
	Headers   *entities.OrderedMap[string]
	Transport *string
	Auth      any
}

// MCPConfig mirrors MCPConfig; MCPServers values are *StdioMCPServer or *RemoteMCPServer.
type MCPConfig struct {
	MCPServers *entities.OrderedMap[any]
}

// MCPConfigFromDict mirrors the from_dict classmethod. It resolves each server entry to
// StdioMCPServer (has command) or RemoteMCPServer (has url); pydantic validation error
// text is not reproduced (see the module report).
func MCPConfigFromDict(config *entities.OrderedMap[any]) (*MCPConfig, error) {
	serversVal := any(config)
	if v, ok := config.Get("mcpServers"); ok {
		serversVal = v
	}
	servers, isMap := serversVal.(*entities.OrderedMap[any])
	if !isMap {
		return nil, value_objects.TypeErrorf("Input should be a valid dictionary")
	}
	out := entities.NewOrderedMap[any]()
	for _, name := range servers.Keys() {
		raw, _ := servers.Get(name)
		entry, isEntryMap := raw.(*entities.OrderedMap[any])
		if !isEntryMap {
			return nil, value_objects.TypeErrorf("Input should be a valid dictionary")
		}
		hasCommand, hasURL := entry.Has("command"), entry.Has("url")
		switch {
		case hasCommand && !hasURL:
			server, err := parseStdioMCPServer(entry)
			if err != nil {
				return nil, err
			}
			out.Set(name, server)
		case hasURL && !hasCommand:
			server, err := parseRemoteMCPServer(entry)
			if err != nil {
				return nil, err
			}
			out.Set(name, server)
		default:
			return nil, value_objects.TypeErrorf("Input should be a valid StdioMCPServer or RemoteMCPServer")
		}
	}
	return &MCPConfig{MCPServers: out}, nil
}

func parseStdioMCPServer(entry *entities.OrderedMap[any]) (*StdioMCPServer, error) {
	for _, key := range entry.Keys() {
		switch key {
		case "command", "args", "env", "cwd", "transport":
		default:
			return nil, value_objects.TypeErrorf("Unexpected keyword argument %s", key)
		}
	}
	commandVal, _ := entry.Get("command")
	command, isStr := commandVal.(string)
	if !isStr {
		return nil, value_objects.TypeErrorf("Input should be a valid string")
	}
	server := &StdioMCPServer{Command: command, Args: []string{}, Env: entities.NewOrderedMap[any](), Transport: "stdio"}

	if v, ok := entry.Get("args"); ok {
		list, isList := v.([]any)
		if !isList {
			return nil, value_objects.TypeErrorf("Input should be a valid list")
		}
		for _, item := range list {
			s, isItemStr := item.(string)
			if !isItemStr {
				return nil, value_objects.TypeErrorf("Input should be a valid string")
			}
			server.Args = append(server.Args, s)
		}
	}
	if v, ok := entry.Get("env"); ok {
		m, isEnvMap := v.(*entities.OrderedMap[any])
		if !isEnvMap {
			return nil, value_objects.TypeErrorf("Input should be a valid dictionary")
		}
		server.Env = m
	}
	if v, ok := entry.Get("cwd"); ok && v != nil {
		s, isCwdStr := v.(string)
		if !isCwdStr {
			return nil, value_objects.TypeErrorf("Input should be a valid string")
		}
		server.Cwd = &s
	}
	if v, ok := entry.Get("transport"); ok {
		s, isTransportStr := v.(string)
		if !isTransportStr || s != "stdio" {
			return nil, value_objects.TypeErrorf("Input should be 'stdio'")
		}
	}
	return server, nil
}

func parseRemoteMCPServer(entry *entities.OrderedMap[any]) (*RemoteMCPServer, error) {
	for _, key := range entry.Keys() {
		switch key {
		case "url", "headers", "transport", "auth":
		default:
			return nil, value_objects.TypeErrorf("Unexpected keyword argument %s", key)
		}
	}
	urlVal, _ := entry.Get("url")
	url, isStr := urlVal.(string)
	if !isStr {
		return nil, value_objects.TypeErrorf("Input should be a valid string")
	}
	server := &RemoteMCPServer{URL: url, Headers: entities.NewOrderedMap[string]()}

	if v, ok := entry.Get("headers"); ok {
		m, isHeadersMap := v.(*entities.OrderedMap[string])
		if !isHeadersMap {
			anyMap, isAnyMap := v.(*entities.OrderedMap[any])
			if !isAnyMap {
				return nil, value_objects.TypeErrorf("Input should be a valid dictionary")
			}
			headers := entities.NewOrderedMap[string]()
			for _, key := range anyMap.Keys() {
				val, _ := anyMap.Get(key)
				s, isHeaderStr := val.(string)
				if !isHeaderStr {
					return nil, value_objects.TypeErrorf("Input should be a valid string")
				}
				headers.Set(key, s)
			}
			server.Headers = headers
		} else {
			server.Headers = m
		}
	}
	if v, ok := entry.Get("transport"); ok && v != nil {
		s, isTransportStr := v.(string)
		if !isTransportStr || (s != TransportStreamableHTTP && s != TransportSSE) {
			return nil, value_objects.TypeErrorf("Input should be 'streamable-http' or 'sse'")
		}
		server.Transport = &s
	}
	if v, ok := entry.Get("auth"); ok && v != nil {
		if _, isAuthStr := v.(string); !isAuthStr {
			return nil, value_objects.TypeErrorf("Input should be a valid string")
		}
		server.Auth = v
	}
	return server, nil
}

var (
	ipvFutureRe  = regexp.MustCompile(`^v[a-fA-F0-9]+\..+$`)
	urlSchemeSet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-."
)

// pyURLPath returns urllib.parse.urlparse(url).path (CPython 3.14), including its
// leniency and its ValueErrors for malformed bracketed hosts. Unicode-normalisation
// checks of the netloc (_checknetloc) are not ported.
func pyURLPath(url string) (string, error) {
	_, path, err := pyURLSchemePath(url)
	return path, err
}

// pyURLSchemePath returns the scheme and path of urllib.parse.urlparse(url).
func pyURLSchemePath(url string) (string, string, error) {
	// strip leading C0 control chars and spaces, then remove tab, CR and LF everywhere
	i := 0
	for i < len(url) && url[i] <= 0x20 {
		i++
	}
	url = strings.NewReplacer("\t", "", "\r", "", "\n", "").Replace(url[i:])

	scheme := ""
	if c := strings.IndexByte(url, ':'); c > 0 && ((url[0] >= 'a' && url[0] <= 'z') || (url[0] >= 'A' && url[0] <= 'Z')) {
		valid := true
		for j := 0; j < c; j++ {
			if !strings.ContainsRune(urlSchemeSet, rune(url[j])) {
				valid = false
				break
			}
		}
		if valid {
			scheme, url = strings.ToLower(url[:c]), url[c+1:]
		}
	}
	if strings.HasPrefix(url, "//") {
		delim := len(url)
		for _, ch := range "/?#" {
			if w := strings.IndexRune(url[2:], ch); w >= 0 && w+2 < delim {
				delim = w + 2
			}
		}
		netloc := url[2:delim]
		url = url[delim:]
		hasOpen, hasClose := strings.Contains(netloc, "["), strings.Contains(netloc, "]")
		if hasOpen != hasClose {
			return "", "", value_objects.ValueErrorf("Invalid IPv6 URL")
		}
		if hasOpen {
			if err := checkBracketedNetloc(netloc); err != nil {
				return "", "", err
			}
		}
	}
	if h := strings.IndexByte(url, '#'); h >= 0 {
		url = url[:h]
	}
	if q := strings.IndexByte(url, '?'); q >= 0 {
		url = url[:q]
	}
	// urlparse splits ";params" off the last path segment for the schemes in uses_params
	if (scheme == "" || scheme == "http" || scheme == "https") && strings.Contains(url, ";") {
		from := 0
		if strings.Contains(url, "/") {
			from = strings.LastIndex(url, "/")
		}
		if p := strings.IndexByte(url[from:], ';'); p >= 0 {
			url = url[:from+p]
		}
	}
	return scheme, url, nil
}

// checkBracketedNetloc mirrors urllib.parse._check_bracketed_netloc / _check_bracketed_host.
func checkBracketedNetloc(netloc string) error {
	hostAndPort := netloc[strings.LastIndex(netloc, "@")+1:]
	var hostname string
	if open := strings.Index(hostAndPort, "["); open >= 0 {
		if open > 0 {
			return value_objects.ValueErrorf("Invalid IPv6 URL")
		}
		bracketed := hostAndPort[open+1:]
		port := ""
		if c := strings.Index(bracketed, "]"); c >= 0 {
			hostname, port = bracketed[:c], bracketed[c+1:]
		} else {
			hostname = bracketed
		}
		if port != "" && !strings.HasPrefix(port, ":") {
			return value_objects.ValueErrorf("Invalid IPv6 URL")
		}
	} else {
		hostname = strings.SplitN(hostAndPort, ":", 2)[0]
	}
	if strings.HasPrefix(hostname, "v") {
		if !ipvFutureRe.MatchString(hostname) {
			return value_objects.ValueErrorf("IPvFuture address is invalid")
		}
		return nil
	}
	addr, err := netip.ParseAddr(hostname)
	if err == nil && strings.Contains(addr.Zone(), "%") {
		err = value_objects.ValueErrorf("invalid scope id")
	}
	if err != nil {
		return value_objects.ValueErrorf("%s does not appear to be an IPv4 or IPv6 address", value_objects.PyRepr(hostname))
	}
	if addr.Is4() {
		return value_objects.ValueErrorf("An IPv4 address cannot be in brackets")
	}
	return nil
}
