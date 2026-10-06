package config

import (
	"bufio"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"

	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// Methods the factory allows.
var corsMethods = []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"}

// GetAllowedOrigins reads CORS_ORIGINS (comma separated); "*" anywhere collapses to
// ["*"], and the default is ["*"] for MCP compatibility.
func GetAllowedOrigins(getenv func(string) string) []string {
	if getenv == nil {
		getenv = os.Getenv
	}
	raw := getenv("CORS_ORIGINS")
	if raw == "" {
		return []string{"*"}
	}
	origins := []string{}
	for _, o := range strings.Split(raw, ",") {
		if s := tmvo.PyStrip(o); s != "" {
			origins = append(origins, s)
		}
	}
	for _, o := range origins {
		if o == "*" {
			return []string{"*"}
		}
	}
	return origins
}

// CORSOptions mirror Starlette's CORSMiddleware arguments (allow_origin_regex is unused by
// the factory and not ported).
type CORSOptions struct {
	AllowOrigins     []string
	AllowMethods     []string
	AllowHeaders     []string
	AllowCredentials bool
	ExposeHeaders    []string
	MaxAge           int
}

var allMethods = []string{"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}
var safelistedHeaders = []string{"Accept", "Accept-Language", "Content-Language", "Content-Type"}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

// NewCORSMiddleware ports starlette.middleware.cors.CORSMiddleware.
func NewCORSMiddleware(o CORSOptions) func(http.Handler) http.Handler {
	methods := o.AllowMethods
	if contains(methods, "*") {
		methods = allMethods
	}
	allowAllOrigins := contains(o.AllowOrigins, "*")
	allowAllHeaders := contains(o.AllowHeaders, "*")
	preflightExplicitOrigin := !allowAllOrigins || o.AllowCredentials

	// Simple (non-preflight) responses never carry the bare wildcard together with
	// credentials: browsers reject "Access-Control-Allow-Origin: *" +
	// "Access-Control-Allow-Credentials: true" (see the Fetch CORS protocol). A
	// credentialed response echoes the concrete origin in apply below, and a
	// non-allowlisted origin gets no Access-Control-Allow-Origin and no
	// Access-Control-Allow-Credentials at all.

	preflight := map[string]string{}
	if preflightExplicitOrigin {
		preflight["Vary"] = "Origin"
	} else {
		preflight["Access-Control-Allow-Origin"] = "*"
	}
	preflight["Access-Control-Allow-Methods"] = strings.Join(methods, ", ")
	preflight["Access-Control-Max-Age"] = strconv.Itoa(o.MaxAge)
	headerSet := map[string]struct{}{}
	for _, h := range append(append([]string{}, safelistedHeaders...), o.AllowHeaders...) {
		headerSet[h] = struct{}{}
	}
	sortedHeaders := make([]string, 0, len(headerSet))
	for h := range headerSet {
		sortedHeaders = append(sortedHeaders, h)
	}
	sort.Strings(sortedHeaders)
	if !allowAllHeaders {
		preflight["Access-Control-Allow-Headers"] = strings.Join(sortedHeaders, ", ")
	}
	if o.AllowCredentials {
		preflight["Access-Control-Allow-Credentials"] = "true"
	}
	lowerAllowed := make([]string, len(sortedHeaders))
	for i, h := range sortedHeaders {
		lowerAllowed[i] = strings.ToLower(h)
	}

	isAllowed := func(origin string) bool { return allowAllOrigins || contains(o.AllowOrigins, origin) }
	explicit := func(h http.Header, origin string) {
		h.Set("Access-Control-Allow-Origin", origin)
		if cur := h.Get("Vary"); cur != "" {
			h.Set("Vary", cur+", Origin")
		} else {
			h.Set("Vary", "Origin")
		}
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin, hasOrigin := r.Header["Origin"]
			if !hasOrigin {
				next.ServeHTTP(w, r)
				return
			}
			requestedOrigin := origin[0]
			// Starlette detects a preflight by the header's presence, even when empty.
			if _, isPreflight := r.Header["Access-Control-Request-Method"]; r.Method == http.MethodOptions && isPreflight {
				headers := map[string]string{}
				for k, v := range preflight {
					headers[k] = v
				}
				var failures []string
				if isAllowed(requestedOrigin) {
					if preflightExplicitOrigin {
						headers["Access-Control-Allow-Origin"] = requestedOrigin
					}
				} else {
					failures = append(failures, "origin")
				}
				if !contains(methods, r.Header.Get("Access-Control-Request-Method")) {
					failures = append(failures, "method")
				}
				if reqHeaders, ok := r.Header["Access-Control-Request-Headers"]; ok {
					if allowAllHeaders {
						headers["Access-Control-Allow-Headers"] = reqHeaders[0]
					} else {
						for _, h := range strings.Split(strings.ToLower(reqHeaders[0]), ",") {
							if !contains(lowerAllowed, tmvo.PyStrip(h)) {
								failures = append(failures, "headers")
								break
							}
						}
					}
				}
				for k, v := range headers {
					w.Header().Set(k, v)
				}
				w.Header().Set("Content-Type", "text/plain; charset=utf-8")
				body, status := "OK", http.StatusOK
				if len(failures) > 0 {
					body, status = "Disallowed CORS "+strings.Join(failures, ", "), http.StatusBadRequest
				}
				w.Header().Set("Content-Length", strconv.Itoa(len(body)))
				w.WriteHeader(status)
				_, _ = w.Write([]byte(body))
				return
			}
			cw := &corsWriter{ResponseWriter: w, apply: func(h http.Header) {
				if !isAllowed(requestedOrigin) {
					// Non-allowlisted origin: grant nothing - neither
					// Access-Control-Allow-Origin nor Access-Control-Allow-Credentials - so
					// the browser blocks the call. The request is still processed (CORS is
					// browser-enforced; non-browser clients that send an Origin header keep
					// working); we only record the rejected origin so the silent fallback is
					// visible to an operator.
					slog.Warn("CORS: request from non-allowlisted origin",
						"origin", requestedOrigin, "method", r.Method, "path", r.URL.Path)
					return
				}
				_, hasCookie := r.Header["Cookie"]
				if allowAllOrigins && !o.AllowCredentials && !hasCookie {
					// Wildcard without credentials: the bare "*" is safe here, the browser
					// will not send credentials alongside it.
					h.Set("Access-Control-Allow-Origin", "*")
				} else {
					// Credentialed (or explicit-list) response: echo the concrete origin
					// rather than "*", and add Vary: Origin so a cache cannot serve one
					// origin's response to a different origin.
					explicit(h, requestedOrigin)
					if o.AllowCredentials {
						h.Set("Access-Control-Allow-Credentials", "true")
					}
				}
				if len(o.ExposeHeaders) > 0 {
					h.Set("Access-Control-Expose-Headers", strings.Join(o.ExposeHeaders, ", "))
				}
			}}
			next.ServeHTTP(cw, r)
			cw.start() // handlers that write nothing still get the CORS headers (Starlette adds them on response start)
		})
	}
}

// corsWriter adds the simple-response headers when the response starts.
type corsWriter struct {
	http.ResponseWriter
	apply   func(http.Header)
	started bool
}

func (c *corsWriter) start() {
	if !c.started {
		c.started = true
		c.apply(c.Header())
	}
}

func (c *corsWriter) WriteHeader(status int) { c.start(); c.ResponseWriter.WriteHeader(status) }
func (c *corsWriter) Write(b []byte) (int, error) {
	c.start()
	return c.ResponseWriter.Write(b)
}
func (c *corsWriter) Flush() {
	c.start()
	if f, ok := c.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

func (c *corsWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	c.start()
	if hj, ok := c.ResponseWriter.(http.Hijacker); ok {
		return hj.Hijack()
	}
	return nil, nil, fmt.Errorf("underlying ResponseWriter does not support hijacking")
}

// ConfigureCORS wraps a handler with the CORS middleware. Custom origins (when non-empty)
// override the environment; a wildcard origin forces credentials off.
func ConfigureCORS(next http.Handler, allowCredentials bool, customOrigins []string, getenv func(string) string) http.Handler {
	origins := customOrigins
	if len(origins) == 0 {
		origins = GetAllowedOrigins(getenv)
	}
	if contains(origins, "*") {
		allowCredentials = false
	}
	return NewCORSMiddleware(CORSOptions{AllowOrigins: origins, AllowCredentials: allowCredentials,
		AllowMethods: corsMethods, AllowHeaders: []string{"*"}, ExposeHeaders: []string{"*"}, MaxAge: 600})(next)
}

// GetCORSConfig returns the CORS configuration for status endpoints (allow_credentials is
// always reported as true, even when a wildcard disables it at runtime).
func GetCORSConfig(getenv func(string) string) *entities.OrderedMap[any] {
	if getenv == nil {
		getenv = os.Getenv
	}
	envVar := "not set"
	if v, ok := os.LookupEnv("CORS_ORIGINS"); ok {
		envVar = v
	}
	m := entities.NewOrderedMap[any]()
	m.Set("allowed_origins", GetAllowedOrigins(getenv))
	m.Set("allow_credentials", true)
	m.Set("allow_methods", corsMethods)
	m.Set("allow_headers", []string{"*"})
	m.Set("expose_headers", []string{"*"})
	m.Set("max_age", 600)
	m.Set("environment_variable", envVar)
	return m
}
